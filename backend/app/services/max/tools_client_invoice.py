"""Max tool: produce_client_invoice — Square share-link + PDF + Outlook draft.

Registered into TOOL_REGISTRY on import. Never sends.
"""
from __future__ import annotations

import os

from app.services.max.tool_executor import ToolResult, tool

_T = "produce_client_invoice"


def _find_invoice(params: dict) -> dict | None:
    from app.db.database import get_db
    from app.db.database import dict_row

    inv = params.get("invoice_id") or params.get("invoice") or params.get("invoice_number")
    qid = params.get("quote_id") or params.get("quote")
    with get_db() as conn:
        row = None
        if inv:
            row = conn.execute(
                "SELECT * FROM invoices WHERE id = ? OR invoice_number = ?", (inv, inv)
            ).fetchone()
        elif qid:
            row = conn.execute(
                """SELECT i.* FROM invoices i LEFT JOIN quotes_v2 q ON q.id = i.quote_id
                   WHERE i.quote_id = ? OR q.quote_number = ?
                   ORDER BY i.created_at DESC LIMIT 1""",
                (qid, qid),
            ).fetchone()
        if not row:
            return None
        data = dict_row(row)
        try:
            from app.routers.finance import _enrich_invoice
            data = _enrich_invoice(data)
        except Exception:
            import json
            if isinstance(data.get("line_items"), str):
                try:
                    data["line_items"] = json.loads(data["line_items"])
                except Exception:
                    data["line_items"] = []
        if not data.get("client_email") and data.get("customer_id"):
            cust = conn.execute(
                "SELECT name, email FROM customers WHERE id = ?", (data["customer_id"],)
            ).fetchone()
            if cust:
                data.setdefault("client_name", cust[0])
                data["client_email"] = data.get("client_email") or cust[1]
        return data


def _square_client(biz, log):
    from app.services.client_invoice.square import SquareInvoiceClient
    return SquareInvoiceClient(
        access_token=biz.square_token(),
        location_id=biz.square_location(),
        log=log,
    )


def _outlook_client(biz, log):
    from app.services.client_invoice.outlook_draft import OutlookDraftClient
    from app.services.max import outlook_reader as orx

    token_file = os.getenv(biz.outlook_token_env) or None
    tok = orx.load_token(token_file)
    if not tok or not tok.get("access_token"):
        # Fall back to the default Outlook token file (same mailbox /me).
        tok = orx.load_token()
    access = (tok or {}).get("access_token") or ""
    return OutlookDraftClient(
        access_token=access,
        mailbox=biz.outlook_mailbox,
        log=log,
    )


@tool(_T)
def _produce_client_invoice(params: dict, desk=None) -> ToolResult:
    """Square Share-link invoice + existing PDF + Outlook DRAFT. Never sends."""
    params = params or {}
    try:
        from app.services.max.founder_session import is_family_edition
        if is_family_edition():
            return ToolResult(tool=_T, success=False,
                              error="Client invoices are not available in this edition.")
    except Exception:
        pass

    inv = _find_invoice(params)
    if not inv:
        return ToolResult(tool=_T, success=False,
                          error="Give invoice_id (or INV number) or quote_id (or EST number).")

    from app.services.client_invoice.business import resolve_invoice_business
    from app.services.client_invoice.produce import preview_client_invoice, produce_client_invoice

    biz_key = params.get("business") or params.get("business_id") or params.get("billed_by")
    explicit = {"id": biz_key, "name": params.get("business_name") or biz_key} if biz_key else None
    confirm = str(params.get("confirm") or "").lower() in ("1", "true", "yes")
    if not confirm:
        preview = preview_client_invoice(inv, business=explicit)
        return ToolResult(tool=_T, success=True, result=preview)

    log: list = []
    try:
        biz = resolve_invoice_business(inv, explicit=explicit)
        square = _square_client(biz, log)
        outlook = _outlook_client(biz, log)
        result = produce_client_invoice(
            inv, business=biz, square_client=square, outlook_client=outlook,
            persist=True, confirm=True, log=log,
        )
    except Exception as exc:  # noqa: BLE001
        return ToolResult(tool=_T, success=False, result={"log": log, "sent": False},
                          error=f"{type(exc).__name__}: {exc}")

    # Never return raw PDF bytes to the chat layer.
    result.pop("pdf_bytes", None)
    result["pdf"] = f"/api/v1/finance/invoices/{inv.get('id')}/pdf" if inv.get("id") else None
    return ToolResult(tool=_T, success=True, result=result)


CLIENT_INVOICE_TOOLS_DOC = """
### Client invoice (Square share-link + Outlook draft)
- **produce_client_invoice** — When Rafael asks for a client invoice: create a Square invoice with
  delivery **Share link** only (Square must never email or text the client), build the existing
  invoice PDF for that business (gold PAY HERE button + QR under the total), and create an Outlook
  DRAFT reply in the client's existing thread with the PDF attached. NEVER sends. Preview first
  (no confirm); after yes, call again with confirm=true.
  `{"tool": "produce_client_invoice", "invoice_number": "INV-2026-100"}`
  `{"tool": "produce_client_invoice", "invoice_number": "INV-2026-100", "confirm": true}`
  Branding and Square/Outlook mailboxes come from business config (Empire, Nelma's, others) —
  never hardcoded to one shop. Client lines use fractions and V###-Color codes, never fabric brands.
  Report the pay link and that the Outlook item is a draft. Rafael sends himself.
"""
