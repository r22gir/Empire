"""Max tool: job_invoice_ledger — job-aware invoices (estimate -> invoices -> payments).

Registered into tool_executor.TOOL_REGISTRY on import (same pattern as tools_files).
Preview is the default and writes nothing. action=create_final writes ONE draft
final invoice (no email, no Stripe link); earlier open invoices of the job are
marked superseded so their balance is not billed twice.
"""
from __future__ import annotations

from app.services.max.tool_executor import ToolResult, tool

_T = "job_invoice_ledger"


def _resolve_invoice_id(conn, params: dict) -> str | None:
    inv = params.get("invoice_id") or params.get("invoice")
    if inv:
        row = conn.execute("SELECT id FROM invoices WHERE id = ? OR invoice_number = ?", (inv, inv)).fetchone()
        return row[0] if row else None
    qid = params.get("quote_id") or params.get("quote")
    if qid:
        row = conn.execute(
            """SELECT i.id FROM invoices i LEFT JOIN quotes_v2 q ON q.id = i.quote_id
               WHERE (i.quote_id = ? OR i.source_id = ? OR q.quote_number = ?)
                 AND lower(COALESCE(i.status,'')) NOT IN ('cancelled','canceled','void','voided')
               ORDER BY i.created_at DESC LIMIT 1""", (qid, qid, qid)).fetchone()
        return row[0] if row else None
    return None


@tool(_T)
def _job_invoice_ledger(params: dict, desk=None) -> ToolResult:
    params = params or {}
    action = str(params.get("action") or "preview").strip().lower()
    try:
        from app.db.database import get_db
        from app.services import job_ledger as jl
        with get_db() as conn:
            inv_id = _resolve_invoice_id(conn, params)
            if not inv_id:
                return ToolResult(tool=_T, success=False,
                                  error="Give invoice_id (or INV number) or quote_id (or EST number) of the job.")
            ledger = jl.job_ledger(conn, inv_id)
            if action in ("ledger", "history"):
                return ToolResult(tool=_T, success=True, result=ledger)
            settlement = jl.build_final_settlement(conn, inv_id)
            if action in ("create_final", "final", "create"):
                made = jl.create_final_invoice(conn, inv_id)
                inv = made["invoice"]
                return ToolResult(tool=_T, success=True, result={
                    "created": True, "invoice_id": inv["id"], "invoice_number": inv["invoice_number"],
                    "status": inv["status"], "total": inv["total"], "balance_due": inv["balance_due"],
                    "settlement": settlement,
                    "pdf": f"/api/v1/finance/invoices/{inv['id']}/pdf",
                    "note": "Draft only. Not emailed. Make the Stripe balance link with the invoice pay-link flow when Rafael says so.",
                })
            return ToolResult(tool=_T, success=True, result={"preview": True, "settlement": settlement,
                                                             "ledger": ledger})
    except Exception as exc:  # noqa: BLE001
        return ToolResult(tool=_T, success=False, error=f"{type(exc).__name__}: {exc}")


JOB_LEDGER_TOOLS_DOC = """
### Job ledger (invoices that apply earlier payments)
- **job_invoice_ledger** — Use this, NOT a hand-rebuilt invoice, whenever an invoice must apply an earlier deposit,
  an earlier invoice payment or a change order. It links estimate -> invoices -> payments for the job (same quote,
  same job, change-order credit reference) and reads the ONE payments table (manual entries and Stripe).
  action: "preview" (default, writes nothing): contract total, every payment received as a credit line, balance due.
  action: "ledger": every invoice of the job with paid amounts. action: "create_final": writes one DRAFT final
  invoice (contract lines, 'Payments & credits applied' section, balance due) and marks earlier open invoices
  superseded so nothing is billed twice. Never emails, never makes a Stripe link.
  `{"tool": "job_invoice_ledger", "quote_id": "EST-2026-299"}`
  `{"tool": "job_invoice_ledger", "invoice_id": "INV-2026-124", "action": "create_final"}`
  Report the numbers from the result only: contract total, each credit (date, invoice, amount), balance due.
"""
