"""Orchestrate Max's client invoice: Square share-link → PDF → Outlook draft.

Uses the existing invoice PDF renderer. Never sends.
"""
from __future__ import annotations

import logging
from typing import Optional

from app.services.client_invoice.business import InvoiceBusiness, resolve_invoice_business
from app.services.client_invoice.client_copy import money, sanitize_line_items
from app.services.client_invoice.cover_email import cover_email_html, cover_email_text
from app.services.client_invoice.outlook_draft import OutlookDraftClient, OutlookDraftError
from app.services.client_invoice.square import SquareInvoiceClient, SquareInvoiceError

logger = logging.getLogger("max.client_invoice")


def _first_name(invoice: dict, customer: dict | None) -> str:
    raw = invoice.get("client_name") or (customer or {}).get("name") or "there"
    return str(raw).split("·")[0].split(",")[0].strip().split()[0] or "there"


def _client_email(invoice: dict, customer: dict | None) -> str:
    return str(invoice.get("client_email") or (customer or {}).get("email") or "").strip()


def _due(invoice: dict) -> str | None:
    raw = invoice.get("due_date")
    if not raw:
        return None
    return str(raw)[:10]


def preview_client_invoice(
    invoice: dict,
    *,
    customer: Optional[dict] = None,
    business: InvoiceBusiness | dict | None = None,
) -> dict:
    biz = resolve_invoice_business(invoice, explicit=business)
    lines = sanitize_line_items(invoice.get("line_items") or [])
    total = float(invoice.get("balance_due") if invoice.get("balance_due") is not None else invoice.get("total") or 0)
    return {
        "needs_confirmation": True,
        "sent": False,
        "business": biz.public_dict(),
        "invoice_number": invoice.get("invoice_number"),
        "client": invoice.get("client_name") or (customer or {}).get("name"),
        "client_email": _client_email(invoice, customer),
        "lines": [{"description": it.get("description"), "amount": it.get("total") or it.get("amount")} for it in lines],
        "total": total,
        "message": (
            f"Ready to create a Square Share-link invoice and an Outlook DRAFT reply for "
            f"{invoice.get('invoice_number')} ({biz.name}, {money(total)}). "
            "Square will not email or text the client. Nothing is sent."
        ),
    }


def persist_square_link(invoice_id: str, square_invoice_id: str, public_url: str) -> None:
    from app.db.database import get_db

    cols = {
        "square_invoice_id": "TEXT",
        "square_pay_url": "TEXT",
        "square_delivery_method": "TEXT",
    }
    with get_db() as conn:
        have = {r[1] for r in conn.execute("PRAGMA table_info(invoices)")}
        for col, ctype in cols.items():
            if col not in have:
                try:
                    conn.execute(f"ALTER TABLE invoices ADD COLUMN {col} {ctype}")
                except Exception:
                    pass
        conn.execute(
            """UPDATE invoices
               SET square_invoice_id = ?, square_pay_url = ?, square_delivery_method = 'SHARE_MANUALLY',
                   payment_status = 'link_ready'
               WHERE id = ?""",
            (square_invoice_id, public_url, invoice_id),
        )


def produce_client_invoice(
    invoice: dict,
    *,
    customer: Optional[dict] = None,
    business: InvoiceBusiness | dict | None = None,
    square_client: Optional[SquareInvoiceClient] = None,
    outlook_client: Optional[OutlookDraftClient] = None,
    persist: bool = False,
    confirm: bool = True,
    log: Optional[list] = None,
    is_woodcraft: bool = False,
) -> dict:
    """Run the Max invoice path. confirm=False previews only. Never sends."""
    log = log if log is not None else []
    if not confirm:
        preview = preview_client_invoice(invoice, customer=customer, business=business)
        preview["log"] = list(log)
        return preview

    biz = resolve_invoice_business(invoice, explicit=business)
    lines = sanitize_line_items(invoice.get("line_items") or [])
    total = float(invoice.get("balance_due") if invoice.get("balance_due") is not None else invoice.get("total") or 0)
    email = _client_email(invoice, customer)
    if not email:
        raise ValueError("Client email is required for the Outlook draft (Square still uses Share link only).")

    if square_client is None:
        raise SquareInvoiceError("A Square client must be injected (tests) or configured for this business")
    if outlook_client is None:
        raise OutlookDraftError("An Outlook draft client must be injected (tests) or configured for this business")

    square = square_client.create_share_link_invoice(
        invoice_number=str(invoice.get("invoice_number") or invoice.get("id") or "INV"),
        client_name=str(invoice.get("client_name") or (customer or {}).get("name") or "Client"),
        client_email=email,
        line_items=lines,
        total=total,
        due_date=_due(invoice),
        idempotency_key=str(invoice.get("id") or invoice.get("invoice_number") or ""),
    )
    pay_url = square["public_url"]

    inv = dict(invoice)
    inv["line_items"] = lines
    inv["square_pay_url"] = pay_url
    inv["pay_url"] = pay_url
    inv["payment_status"] = inv.get("payment_status") or "link_ready"
    if not inv.get("invoice_stage"):
        inv["invoice_stage"] = "final"
    inv["business_name"] = biz.name
    inv["business_phone"] = biz.phone
    inv["business_email"] = biz.email
    inv["business_address"] = biz.address
    inv["business_website"] = biz.website
    inv["business_tagline"] = biz.tagline
    inv["billed_by"] = biz.name
    if inv.get("balance_due") is None:
        inv["balance_due"] = total

    if persist and inv.get("id"):
        persist_square_link(str(inv["id"]), square["square_invoice_id"], pay_url)

    from app.services.invoice_pdf_service import generate_client_invoice_pdf_bytes

    pdf_bytes = generate_client_invoice_pdf_bytes(
        inv, customer=customer, is_woodcraft=is_woodcraft,
    )
    pdf_name = f"Invoice-{inv.get('invoice_number') or 'draft'}.pdf"

    first = _first_name(inv, customer)
    body_text = cover_email_text(
        client_first=first, business_name=biz.name, lines=lines, pay_url=pay_url,
    )
    body_html = cover_email_html(
        client_first=first, business_name=biz.name, lines=lines, pay_url=pay_url,
    )
    thread = outlook_client.find_thread_message(email)
    draft = outlook_client.create_draft_reply(
        body_html=body_html,
        subject=f"Invoice {inv.get('invoice_number')}",
        to_email=email,
        pdf_bytes=pdf_bytes,
        pdf_name=pdf_name,
        reply_to_id=(thread or {}).get("id"),
    )

    return {
        "sent": False,
        "status": "draft",
        "business": biz.public_dict(),
        "invoice_number": inv.get("invoice_number"),
        "invoice_id": inv.get("id"),
        "square": {
            "invoice_id": square["square_invoice_id"],
            "delivery_method": square["delivery_method"],
            "delivery_label": "Share link",
            "public_url": pay_url,
        },
        "pay_url": pay_url,
        "outlook": {
            "draft_id": draft["draft_id"],
            "is_draft": True,
            "sent": False,
            "thread_found": draft["thread_found"],
            "conversation_id": draft.get("conversation_id"),
        },
        "cover_email": body_text,
        "pdf_name": pdf_name,
        "pdf_bytes": pdf_bytes,
        "log": list(log),
        "message": (
            f"Square Share-link invoice ready ({pay_url}). "
            f"Outlook DRAFT {'reply' if draft['thread_found'] else 'message'} "
            f"{draft['draft_id']} has the PDF attached. Not sent."
        ),
    }
