"""Short casual cover email for an invoice draft. Never sent from here."""
from __future__ import annotations

from html import escape

from app.services.client_invoice.client_copy import client_line_text, line_amount, money


def cover_email_text(
    *,
    client_first: str,
    business_name: str,
    lines: list[dict],
    pay_url: str,
) -> str:
    first = (client_first or "there").split()[0]
    rows = []
    for it in lines or []:
        rows.append(f"{client_line_text(it)} — {money(line_amount(it))}")
    if not rows:
        rows.append("Invoice attached")
    body = [
        f"Hi {first} —",
        "",
        *rows,
        "",
        f"Pay here: {pay_url}",
        "",
        "Invoice attached.",
        "",
        f"— {business_name}",
    ]
    return "\n".join(body)


def cover_email_html(
    *,
    client_first: str,
    business_name: str,
    lines: list[dict],
    pay_url: str,
) -> str:
    text = cover_email_text(
        client_first=client_first, business_name=business_name, lines=lines, pay_url=pay_url,
    )
    parts = []
    for line in text.split("\n"):
        if line.startswith("Pay here: "):
            url = escape(line[10:], quote=True)
            parts.append(f'Pay here: <a href="{url}">{escape(line[10:], quote=False)}</a>')
        else:
            parts.append(escape(line, quote=False) if line else "&nbsp;")
    return "<p>" + "<br>".join(parts) + "</p>"
