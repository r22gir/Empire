"""Empire Workroom house-format sheets.

Cream paper, ink type, gold rules. Quote estimates, shop tickets, idea
sheets, and measurement reports all render through this module so they
share one visual system instead of drifting into separate styles.

Inch sizes print as fractions (48.5 -> 48 1/2"), which is how the
workroom marks a tape.
"""
from __future__ import annotations

import html
import json
import logging
import math
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# House palette — the quote letterhead already used these values.
CREAM = "#f5f3ef"
INK = "#2c2416"
INK_TEXT = "#1a1a2e"
GOLD = "#b8960c"
MUTED = "#888888"
RULE = "#e8e4dd"

_BRAND_PATH = Path(__file__).resolve().parent.parent / "config" / "business.json"


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def format_inches(value: Any) -> str:
    """Decimal inches to a shop fraction. 48.5 -> 48 1/2\".

    Non-numeric text is returned unchanged (already a fraction, a note).
    Empty values become an em dash.
    """
    if value is None:
        return "—"
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return "—"
        if "/" in text or text.endswith('"') or text.endswith("″"):
            if text.endswith('"') or text.endswith("″"):
                return text
            return f'{text}"'
        try:
            number = float(text)
        except ValueError:
            return text
    else:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return "—"

    if math.isnan(number) or math.isinf(number):
        return "—"

    sign = "-" if number < 0 else ""
    number = abs(number)
    whole = int(math.floor(number + 1e-9))
    sixteenths = int(round((number - whole) * 16))
    if sixteenths == 16:
        whole += 1
        sixteenths = 0
    if sixteenths <= 0:
        return f'{sign}{whole}"'

    divisor = math.gcd(sixteenths, 16)
    num, den = sixteenths // divisor, 16 // divisor
    frac = f"{num}/{den}"
    if whole:
        return f'{sign}{whole} {frac}"'
    return f'{sign}{frac}"'


def size_label(width: Any = None, height: Any = None, depth: Any = None) -> str:
    """W × H × D, skipping blanks and zeros."""
    parts = []
    for raw, tag in ((width, "W"), (height, "H"), (depth, "D")):
        if raw in (None, "", 0, 0.0, "0", "0.0"):
            continue
        parts.append(f"{format_inches(raw)} {tag}")
    return " × ".join(parts) if parts else "—"


def load_workroom_brand() -> dict:
    brand = {
        "business_name": "Empire Workroom",
        "business_tagline": "Custom Window Treatments & Upholstery",
        "business_phone": "(703) 213-6484",
        "business_email": "workroom@empirebox.store",
        "business_address": "5124 Frolich Ln, Hyattsville, MD 20781",
        "business_website": "studio.empirebox.store",
    }
    try:
        loaded = json.loads(_BRAND_PATH.read_text())
        if isinstance(loaded, dict):
            brand.update({k: v for k, v in loaded.items() if v})
    except Exception:
        logger.debug("business.json unavailable; using house defaults")
    return brand


def house_css() -> str:
    """Shared sheet CSS. Callers embed this inside a <style> block."""
    return f"""
  @page {{ size: letter; margin: 0.5in 0.6in; }}
  body {{
    font-family: 'Helvetica Neue', Arial, sans-serif;
    color: #222;
    max-width: 800px;
    margin: 0 auto;
    padding: 0;
    font-size: 12px;
    line-height: 1.45;
    background: {CREAM};
  }}
  h1 {{ color: {INK_TEXT}; margin: 0; font-size: 28px; letter-spacing: -0.5px; }}
  h3 {{ page-break-after: avoid; color: {GOLD}; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 8px; }}
  th {{
    background: {INK};
    color: {GOLD};
    padding: 8px 6px;
    text-align: left;
    font-size: 0.78em;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
  td {{ font-size: 0.85em; }}
"""


def sheet_header(
    *,
    badge: str,
    number: str,
    meta_lines: list[tuple[str, str]] | None = None,
    biz_name: str = "",
    tagline: str = "",
    contact_html: str = "",
    logo_html: str = "",
) -> str:
    brand = load_workroom_brand()
    name = biz_name or brand["business_name"]
    line = tagline or brand["business_tagline"]
    meta = ""
    for label, value in meta_lines or []:
        if value is None:
            continue
        meta += (
            f'<p style="margin:3px 0;color:#666;font-size:0.82em">'
            f"{esc(label)}: {esc(value)}</p>"
        )
    contact = contact_html or _default_contact_html(brand)
    logo = logo_html or ""
    return f"""
<div style="border-bottom:3px solid {GOLD};padding-bottom:14px;margin-bottom:16px">
  <div style="display:flex;justify-content:space-between;align-items:flex-start">
    <div>
      {logo}
      <h1>{esc(name)}</h1>
      <p style="margin:4px 0 0;color:#888;font-size:0.85em">{esc(line)}</p>
      <p style="margin:6px 0 0;line-height:1.6">{contact}</p>
    </div>
    <div style="text-align:right;padding-top:4px">
      <div style="background:{INK};color:{GOLD};padding:8px 16px;border-radius:6px;font-weight:700;font-size:1.1em;letter-spacing:1px;display:inline-block;margin-bottom:8px">{esc(badge)}</div>
      <p style="margin:3px 0;color:#333;font-size:0.9em;font-weight:600">{esc(number)}</p>
      {meta}
    </div>
  </div>
</div>"""


def _default_contact_html(brand: dict) -> str:
    lines = [
        brand.get("business_phone"),
        brand.get("business_email"),
        brand.get("business_address"),
        brand.get("business_website"),
    ]
    return "<br>".join(
        f'<span style="font-size:0.82em;color:#555">{esc(line)}</span>'
        for line in lines
        if line
    )


def sheet_footer(biz_name: str, tagline: str, number: str, date: str, note: str = "") -> str:
    extra = f'<p style="margin:2px 0 0;color:#aaa;font-size:0.68em">{esc(note)}</p>' if note else ""
    return f"""
<div style="margin-top:28px;padding-top:12px;border-top:1px solid #e8e4dd;text-align:center">
  <p style="margin:0;color:#aaa;font-size:0.72em">{esc(biz_name)} &middot; {esc(tagline)}</p>
  <p style="margin:2px 0 0;color:#ccc;font-size:0.65em">{esc(number)} &middot; {esc(date)}</p>
  {extra}
</div>"""


def acceptance_block(biz_name: str, lead: str | None = None) -> str:
    text = lead or (
        f"By signing below, I accept this estimate and authorize {biz_name} "
        "to proceed with the work described above."
    )
    return f"""
<div style="margin-top:36px;padding:24px 20px;border:2px solid {GOLD};border-radius:10px;page-break-inside:avoid">
  <p style="margin:0 0 12px;font-size:0.78em;text-transform:uppercase;letter-spacing:0.5px;color:{GOLD};font-weight:700">Acceptance</p>
  <p style="margin:0 0 20px;font-size:0.85em;color:#555">{esc(text)}</p>
  <div style="display:flex;gap:40px;margin-top:16px">
    <div style="flex:1">
      <div style="border-bottom:1px solid #333;height:40px"></div>
      <p style="margin:6px 0 0;font-size:0.78em;color:#888">Client Signature</p>
    </div>
    <div style="width:160px">
      <div style="border-bottom:1px solid #333;height:40px"></div>
      <p style="margin:6px 0 0;font-size:0.78em;color:#888">Date</p>
    </div>
  </div>
</div>"""


def wrap_document(title: str, body_html: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{esc(title)}</title>
<style>{house_css()}</style></head><body>
{body_html}
</body></html>"""


def render_pdf(html_doc: str) -> bytes:
    from weasyprint import HTML as WeasyHTML

    return WeasyHTML(string=html_doc).write_pdf()


def _client_card(quote: dict) -> str:
    name = quote.get("customer_name") or "Customer"
    bits = [f'<p style="margin:0;font-weight:700;font-size:1.05em;color:{INK_TEXT}">{esc(name)}</p>']
    for key in ("customer_email", "customer_phone", "customer_address"):
        if quote.get(key):
            bits.append(f'<p style="margin:3px 0 0;color:#555;font-size:0.88em">{esc(quote[key])}</p>')
    project = quote.get("project_name") or quote.get("title") or ""
    project_card = ""
    if project:
        desc = quote.get("project_description") or quote.get("description") or ""
        project_card = f"""
  <div style="flex:1;padding:14px 18px;background:#fffdf7;border-radius:8px;border:1px solid #f0e6c0">
    <p style="margin:0 0 6px;font-size:0.75em;text-transform:uppercase;letter-spacing:0.5px;color:#999;font-weight:600">Project</p>
    <p style="margin:0;font-weight:600;color:{INK_TEXT}">{esc(project)}</p>
    {f'<p style="margin:4px 0 0;color:#777;font-size:0.82em">{esc(desc)}</p>' if desc else ''}
  </div>"""
    return f"""
<div style="display:flex;gap:16px;margin-bottom:16px">
  <div style="flex:1;padding:14px 18px;background:#fffdf7;border-radius:8px;border:1px solid {RULE}">
    <p style="margin:0 0 6px;font-size:0.75em;text-transform:uppercase;letter-spacing:0.5px;color:#999;font-weight:600">Prepared For</p>
    {''.join(bits)}
  </div>
  {project_card}
</div>"""


def _plain_number(value: Any, places: int) -> str:
    try:
        return f"{float(value or 0):.{places}f}"
    except (TypeError, ValueError):
        return "0"


def _money(value: Any) -> str:
    try:
        return f"${float(value or 0):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def collect_spec_rows(quote: dict) -> list[dict]:
    """Flatten rooms, windows, upholstery, and line items into sheet rows."""
    rows: list[dict] = []
    for room in quote.get("rooms") or []:
        room_name = room.get("name") or "Room"
        for window in room.get("windows") or []:
            rows.append({
                "room": room_name,
                "name": window.get("name") or "Window",
                "size": size_label(window.get("width"), window.get("height"), window.get("depth")),
                "detail": window.get("treatmentType") or window.get("treatment_type") or "",
                "fabric": window.get("fabric_name") or window.get("fabricColor") or window.get("fabricType") or "",
                "qty": window.get("quantity") or 1,
                "notes": window.get("notes") or "",
                "lining": window.get("liningType") or "",
                "hardware": window.get("hardwareType") or "",
                "price": window.get("price"),
            })
        for piece in room.get("upholstery") or []:
            rows.append({
                "room": room_name,
                "name": piece.get("name") or "Piece",
                "size": size_label(piece.get("width"), piece.get("height"), piece.get("depth")),
                "detail": piece.get("furnitureType") or "Upholstery",
                "fabric": piece.get("fabricType") or "",
                "qty": piece.get("quantity") or 1,
                "notes": piece.get("notes") or "",
                "lining": "",
                "hardware": "",
                "price": piece.get("price"),
            })
        for item in room.get("items") or []:
            dims = item.get("dimensions") if isinstance(item.get("dimensions"), dict) else {}
            rows.append({
                "room": room_name,
                "name": (item.get("type") or item.get("name") or "Item").replace("_", " ").title(),
                "size": size_label(
                    dims.get("width", item.get("width")),
                    dims.get("height", item.get("height")),
                    dims.get("depth", item.get("depth")),
                ),
                "detail": item.get("treatmentType") or item.get("unit") or "",
                "fabric": item.get("fabric_name") or "",
                "qty": item.get("quantity") or 1,
                "notes": item.get("notes") or "",
                "lining": "",
                "hardware": "",
                "price": item.get("amount") or item.get("rate"),
            })
    if rows:
        return rows
    for item in quote.get("line_items") or []:
        rows.append({
            "room": item.get("room") or "General",
            "name": item.get("description") or item.get("item_type") or "Item",
            "size": size_label(item.get("width"), item.get("height"), item.get("depth")),
            "detail": " — ".join(
                p for p in (item.get("item_type"), item.get("item_style")) if p
            ),
            "fabric": item.get("fabric_name") or "",
            "qty": item.get("quantity") or 1,
            "notes": item.get("notes") or "",
            "lining": "",
            "hardware": "",
            "price": item.get("subtotal") or item.get("amount") or item.get("unit_price"),
        })
    return rows


def _spec_table(rows: list[dict], *, show_price: bool) -> str:
    if not rows:
        return '<p style="color:#888;font-size:0.9em">No pieces on this sheet yet. Sizes will appear as rooms are added.</p>'
    price_head = '<th style="text-align:right">Amount</th>' if show_price else ""
    body = ""
    for row in rows:
        extras = []
        if row.get("lining"):
            extras.append(f"Lining: {row['lining']}")
        if row.get("hardware"):
            extras.append(f"Hardware: {row['hardware']}")
        if row.get("notes"):
            extras.append(str(row["notes"]))
        extra_html = ""
        if extras:
            extra_html = (
                '<br><span style="color:#777;font-size:0.85em">'
                + esc(" · ".join(extras))
                + "</span>"
            )
        price_cell = ""
        if show_price:
            price_cell = (
                f'<td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:right">'
                f'{_money(row.get("price"))}</td>'
            )
        body += f"""<tr>
          <td style="padding:6px 8px;border-bottom:1px solid #eee">{esc(row.get("room"))}</td>
          <td style="padding:6px 8px;border-bottom:1px solid #eee">{esc(row.get("name"))}{extra_html}</td>
          <td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:center">{esc(row.get("size"))}</td>
          <td style="padding:6px 8px;border-bottom:1px solid #eee">{esc(row.get("detail"))}</td>
          <td style="padding:6px 8px;border-bottom:1px solid #eee">{esc(row.get("fabric") or "—")}</td>
          <td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:center">{esc(row.get("qty"))}</td>
          {price_cell}
        </tr>"""
    return f"""<table><thead><tr>
      <th>Room</th><th>Piece</th><th>Size</th><th>Detail</th><th>Fabric</th><th>Qty</th>{price_head}
    </tr></thead><tbody>{body}</tbody></table>"""


def _line_items_table(items: list) -> str:
    if not items:
        return ""
    body = ""
    for idx, item in enumerate(items, 1):
        desc_parts = []
        desc = item.get("description") or item.get("item_type") or "Item"
        desc_parts.append(f"<b>{esc(desc)}</b>")
        if item.get("room"):
            desc_parts.append(f"Room: {esc(item['room'])}")
        if item.get("item_type") and item.get("item_style"):
            desc_parts.append(f"{esc(item['item_type'])} — {esc(item['item_style'])}")
        if item.get("width") or item.get("height"):
            desc_parts.append(
                "Size: "
                + esc(size_label(item.get("width"), item.get("height"), item.get("depth")))
            )
        if item.get("fabric_name"):
            desc_parts.append(f"Fabric: {esc(item['fabric_name'])}")
        qty = item.get("quantity", 1) or 1
        unit_price = float(item.get("unit_price") or item.get("rate") or 0)
        subtotal = float(item.get("subtotal") or item.get("amount") or 0)
        if subtotal == 0:
            subtotal = round(float(qty) * unit_price, 2)
        body += f"""<tr>
          <td style="padding:6px 8px;border-bottom:1px solid #eee">{idx}</td>
          <td style="padding:6px 8px;border-bottom:1px solid #eee">{'<br/>'.join(desc_parts)}</td>
          <td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:center">{esc(qty)}</td>
          <td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:right">{_money(unit_price)}</td>
          <td style="padding:6px 8px;border-bottom:1px solid #eee;text-align:right">{_money(subtotal)}</td>
        </tr>"""
    return f"""<table><thead><tr>
      <th>#</th><th>Description</th><th>Qty</th><th style="text-align:right">Unit</th><th style="text-align:right">Amount</th>
    </tr></thead><tbody>{body}</tbody></table>"""


def _totals_block(quote: dict) -> str:
    subtotal = float(quote.get("subtotal") or 0)
    discount = float(quote.get("discount_amount") or 0)
    tax_rate = float(quote.get("tax_rate") or 0)
    tax_amount = float(quote.get("tax_amount") or 0)
    total = float(quote.get("total") or 0)
    if total == 0 and subtotal:
        total = subtotal - discount + tax_amount
    rows = f"""<tr><td style="padding:6px 8px;text-align:right;color:#666">Subtotal</td>
      <td style="padding:6px 8px;text-align:right;color:#666">{_money(subtotal)}</td></tr>"""
    if discount:
        rows += f"""<tr><td style="padding:6px 8px;text-align:right;color:#c00">Discount</td>
          <td style="padding:6px 8px;text-align:right;color:#c00">-{_money(discount)}</td></tr>"""
    if tax_rate or tax_amount:
        rows += f"""<tr><td style="padding:6px 8px;text-align:right;color:#666">Tax ({tax_rate * 100:.1f}%)</td>
          <td style="padding:6px 8px;text-align:right;color:#666">{_money(tax_amount)}</td></tr>"""
    rows += f"""<tr><td style="padding:12px 8px;text-align:right;border-top:3px solid {GOLD}"><strong style="color:{INK_TEXT}">Total</strong></td>
      <td style="padding:12px 8px;text-align:right;border-top:3px solid {GOLD}"><strong style="color:{GOLD}">{_money(total)}</strong></td></tr>"""
    deposit = quote.get("deposit") or {}
    deposit_amount = deposit.get("deposit_amount") if isinstance(deposit, dict) else None
    if not deposit_amount:
        deposit_amount = quote.get("deposit_required")
    if deposit_amount:
        pct = deposit.get("deposit_percent", quote.get("deposit_percent", "")) if isinstance(deposit, dict) else quote.get("deposit_percent", "")
        label = f"Deposit ({pct}%)" if pct else "Deposit"
        rows += f"""<tr><td style="padding:6px 8px;text-align:right">{esc(label)}</td>
          <td style="padding:6px 8px;text-align:right"><strong>{_money(deposit_amount)}</strong></td></tr>"""
    return f'<table style="margin-top:12px;width:280px;margin-left:auto"><tbody>{rows}</tbody></table>'


def _date_of(quote: dict) -> str:
    created = quote.get("created_at") or ""
    return str(created)[:10]


def render_estimate(quote: dict) -> str:
    """Client estimate in the house format. Works for SQL line items and drafts."""
    brand = load_workroom_brand()
    number = quote.get("quote_number") or "DRAFT"
    created = _date_of(quote)
    expires = str(quote.get("expires_at") or "")[:10]
    meta = [("Date", created or "Draft")]
    if expires:
        meta.append(("Valid until", expires))
    items = quote.get("line_items") or []
    spec_rows = collect_spec_rows(quote)
    # Prefer the priced line-item table when the quote has been calculated.
    pieces = _line_items_table(items) if items else _spec_table(spec_rows, show_price=True)
    if items and spec_rows and quote.get("rooms"):
        pieces = _spec_table(spec_rows, show_price=False) + _line_items_table(items)
    notes = quote.get("notes") or ""
    terms = quote.get("terms") or quote.get("payment_terms") or (
        "50% deposit required to begin fabrication. Balance due upon installation. "
        "All sales final once fabric is cut. Estimate valid for 30 days."
    )
    body = f"""
{sheet_header(
    badge="ESTIMATE",
    number=number,
    meta_lines=meta,
    biz_name=quote.get("business_name") or brand["business_name"],
    tagline=brand["business_tagline"],
)}
{_client_card(quote)}
{pieces}
{_totals_block(quote) if (items or quote.get("total") or quote.get("subtotal")) else '<p style="color:#888;font-size:0.85em">Pricing is filled in when the quote is generated. Sizes above are the working measure.</p>'}
<div style="margin-top:24px;padding:16px 20px;border:1px solid #ddd;border-radius:8px;background:#fffdf7">
  <p style="margin:0 0 8px;font-size:0.78em;text-transform:uppercase;letter-spacing:0.5px;color:#999;font-weight:600">Terms &amp; Conditions</p>
  <p style="margin:0;font-size:0.88em;color:#555;line-height:1.6">{esc(terms)}</p>
</div>
{f'<div style="margin-top:10px;padding:12px 16px;background:#fffdf7;border-radius:8px;font-size:0.88em;color:#666"><strong>Notes:</strong> {esc(notes)}</div>' if notes else ''}
{acceptance_block(quote.get("business_name") or brand["business_name"])}
{sheet_footer(quote.get("business_name") or brand["business_name"], brand["business_tagline"], f"Estimate {number}", created or "draft")}
"""
    return wrap_document(str(number), body)


def render_shop_ticket(quote: dict) -> str:
    """Shop copy of the same job: fractional sizes, cut notes, no new visual system."""
    brand = load_workroom_brand()
    number = quote.get("quote_number") or "DRAFT"
    created = _date_of(quote)
    rows = collect_spec_rows(quote)
    body = f"""
{sheet_header(
    badge="SHOP",
    number=number,
    meta_lines=[("Date", created or "Draft"), ("Copy", "Shop")],
    biz_name=quote.get("business_name") or brand["business_name"],
    tagline=brand["business_tagline"],
)}
{_client_card(quote)}
<p style="margin:0 0 10px;font-size:0.82em;color:#666">Shop copy. Verify the field measure before fabric is cut. Sizes are in inches.</p>
{_spec_table(rows, show_price=False)}
{acceptance_block(
    quote.get("business_name") or brand["business_name"],
    "Shop lead confirms the sizes above match the field measure before cutting.",
)}
{sheet_footer(
    quote.get("business_name") or brand["business_name"],
    brand["business_tagline"],
    f"Shop {number}",
    created or "draft",
    note="Verify field measure before cut",
)}
"""
    return wrap_document(f"Shop {number}", body)


def render_idea_sheet(data: dict) -> str:
    """One-page idea / note in the same house letterhead."""
    brand = load_workroom_brand()
    title = data.get("title") or data.get("project_name") or "Idea"
    notes = data.get("notes") or data.get("description") or data.get("project_description") or ""
    customer = data.get("customer_name") or ""
    body = f"""
{sheet_header(
    badge="IDEA",
    number=data.get("quote_number") or "NOTE",
    meta_lines=[("For", customer)] if customer else [],
    biz_name=brand["business_name"],
    tagline=brand["business_tagline"],
)}
<div style="padding:16px 18px;background:#fffdf7;border:1px solid #f0e6c0;border-radius:8px">
  <p style="margin:0 0 8px;font-size:1.15em;font-weight:700;color:{INK_TEXT}">{esc(title)}</p>
  <p style="margin:0;font-size:0.95em;color:#444;line-height:1.6;white-space:pre-wrap">{esc(notes) or "—"}</p>
</div>
{sheet_footer(brand["business_name"], brand["business_tagline"], "Idea", _date_of(data) or "draft")}
"""
    return wrap_document(str(title), body)


def render_measurements(file_name: str, measurements: list, screenshot_data: str = "") -> str:
    """3D / photo measurement report on the house sheet. Inches are fractions."""
    brand = load_workroom_brand()
    rows = ""
    for i, measure in enumerate(measurements or []):
        inches = measure.get("distance_in", measure.get("inches"))
        rows += f"""<tr>
          <td style="padding:8px;border-bottom:1px solid #eee;text-align:center;font-weight:700;color:{GOLD}">#{esc(measure.get("id", i + 1))}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;text-align:right">{esc(format_inches(inches))}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;text-align:right">{_plain_number(measure.get("distance_ft"), 2)} ft</td>
          <td style="padding:8px;border-bottom:1px solid #eee;text-align:right">{_plain_number(measure.get("distance_m"), 3)} m</td>
        </tr>"""
    table = f"""<table><thead><tr>
      <th>#</th><th style="text-align:right">Inches</th><th style="text-align:right">Feet</th><th style="text-align:right">Meters</th>
    </tr></thead><tbody>{rows}</tbody></table>""" if rows else '<p style="color:#888">No measurements taken.</p>'
    image = ""
    if screenshot_data:
        src = screenshot_data
        if not src.startswith("data:"):
            src = "data:image/png;base64," + src
        image = f'<img src="{src}" alt="Measurement view" style="width:100%;border:1px solid {RULE};border-radius:8px;margin:8px 0" />'
    from datetime import datetime

    today = datetime.now().strftime("%B %d, %Y")
    body = f"""
{sheet_header(
    badge="MEASURE",
    number=file_name or "Scan",
    meta_lines=[("Date", today)],
    biz_name=brand["business_name"],
    tagline=brand["business_tagline"],
)}
{image}
{table}
{sheet_footer(brand["business_name"], brand["business_tagline"], file_name or "Scan", today)}
"""
    return wrap_document(file_name or "Measurements", body)
