"""House email body: one item and amount per line, business signature only."""
from __future__ import annotations

from app.services.invoice_pdf_service import client_visible_line_description
from app.services.max.email_template import render_house_email


def amount_lines(line_items: list[dict], total: float) -> str:
    """Plain body the house renderer turns into one row per amount."""
    rows: list[str] = []
    for item in line_items:
        desc = client_visible_line_description(item) or item.get("description") or "Item"
        amount = item.get("amount", item.get("final_price", item.get("total", 0)))
        try:
            amount_f = float(amount or 0)
        except (TypeError, ValueError):
            amount_f = 0.0
        rows.append(f"{desc}: ${amount_f:,.2f}")
    rows.append(f"Total: ${float(total or 0):,.2f}")
    return "\n".join(rows)


def render_draft_email(
    *,
    line_items: list[dict],
    total: float,
    recipient_name: str | None,
    billed_by: str | None,
    intro: str = "Here is the draft for your review.",
) -> dict:
    body = intro.strip() + "\n\n" + amount_lines(line_items, total)
    rendered = render_house_email(body, recipient_name=recipient_name, billed_by=billed_by)
    return {
        "plain_text": rendered.plain_text,
        "html": rendered.html,
        "sent": False,
    }
