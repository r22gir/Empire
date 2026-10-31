"""Willard-layout estimate: client + INTERNAL copies. Never auto-sends."""
from __future__ import annotations

from collections import defaultdict
from io import BytesIO
from typing import Any

from reportlab.lib.colors import black, HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from app.services.job_stages.catalog import WORKROOM_MARKUP
from app.services.job_stages.gate import assert_client_estimate_allowed

PAGE_W, PAGE_H = letter
INK = black
GOLD = HexColor("#b8912f")
HAIR = HexColor("#20241f")
CATEGORY_ORDER = ("Labor", "Materials", "Install")
CATEGORY_ALIASES = {
    "labor": "Labor",
    "labour": "Labor",
    "materials": "Materials",
    "material": "Materials",
    "fabric": "Materials",
    "install": "Install",
    "installation": "Install",
    "installs": "Install",
}


def _money(value: Any) -> str:
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def normalize_category(raw: str | None) -> str:
    key = (raw or "").strip().lower()
    return CATEGORY_ALIASES.get(key, "Labor" if not key else raw.title())


def group_willard_lines(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group by area, then Labor / Materials / Install inside each area."""
    areas: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: {name: [] for name in CATEGORY_ORDER}
    )
    for line in lines or []:
        area = (line.get("area") or line.get("room") or "General").strip() or "General"
        category = normalize_category(line.get("category") or line.get("group"))
        if category not in CATEGORY_ORDER:
            category = "Labor"
        qty = float(line.get("qty") or line.get("quantity") or 1)
        unit_price = float(line.get("unit_price") or line.get("base") or line.get("rate") or 0)
        base = round(qty * unit_price, 2)
        markup = round(base * WORKROOM_MARKUP, 2)
        client_total = round(base + markup, 2)
        areas[area][category].append({
            "description": line.get("description") or line.get("unit") or "Item",
            "qty": qty,
            "unit": line.get("unit") or "ea",
            "unit_price": unit_price,
            "base": base,
            "markup": markup,
            "client_total": client_total,
        })
    grouped = []
    for area, buckets in areas.items():
        area_base = sum(item["base"] for cat in CATEGORY_ORDER for item in buckets[cat])
        area_client = sum(item["client_total"] for cat in CATEGORY_ORDER for item in buckets[cat])
        grouped.append({
            "area": area,
            "categories": [
                {"name": name, "lines": buckets[name]}
                for name in CATEGORY_ORDER
                if buckets[name]
            ],
            "base": round(area_base, 2),
            "client_total": round(area_client, 2),
        })
    return grouped


def _draw_qr_box(c: canvas.Canvas, x: float, y: float, size: float, url: str) -> None:
    try:
        import qrcode
        from reportlab.lib.utils import ImageReader

        qr = qrcode.QRCode(box_size=4, border=1)
        qr.add_data(url or "https://squareup.com/pay")
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        c.drawImage(ImageReader(buf), x, y, width=size, height=size, mask="auto")
        return
    except Exception:
        pass
    c.setStrokeColor(INK)
    c.setLineWidth(1.6)
    c.rect(x, y, size, size, fill=0, stroke=1)
    c.setFont("Times-Bold", 8)
    c.drawCentredString(x + size / 2, y + size / 2 - 4, "SQUARE QR")


def render_willard_estimate_pdf(packet: dict[str, Any], *, internal: bool) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setPageCompression(0)
    client = packet.get("client_name") or "Client"
    title = "INTERNAL ESTIMATE" if internal else "ESTIMATE"
    c.setFillColor(INK)
    c.setFont("Times-Bold", 22)
    c.drawString(0.6 * inch, PAGE_H - 0.65 * inch, title)
    c.setFillColor(GOLD)
    c.rect(0.6 * inch, PAGE_H - 0.78 * inch, 2.4 * inch, 4, fill=1, stroke=0)
    c.setFillColor(INK)
    c.setFont("Times-Bold", 11)
    c.drawString(0.6 * inch, PAGE_H - 1.05 * inch, f"{client}  ·  {packet.get('area') or packet.get('job_number') or ''}")
    c.setFont("Times-Roman", 9)
    c.drawString(0.6 * inch, PAGE_H - 1.22 * inch, "Willard layout  ·  grouped by area  ·  Labor / Materials / Install")

    y = PAGE_H - 1.55 * inch
    grand_base = 0.0
    grand_client = 0.0
    for area in group_willard_lines(packet.get("lines") or []):
        c.setFont("Times-Bold", 13)
        c.drawString(0.6 * inch, y, area["area"].upper())
        y -= 16
        for bucket in area["categories"]:
            c.setFont("Times-Bold", 11)
            c.drawString(0.7 * inch, y, bucket["name"])
            y -= 14
            c.setFont("Times-Roman", 9)
            for line in bucket["lines"]:
                amount = line["base"] if internal else line["client_total"]
                c.drawString(0.85 * inch, y, f"{line['description'][:62]}")
                c.drawRightString(7.7 * inch, y, f"{line['qty']:g} {line['unit']}")
                c.drawRightString(PAGE_W - 0.6 * inch, y, _money(amount))
                y -= 12
                if y < 1.8 * inch:
                    c.showPage()
                    y = PAGE_H - 0.8 * inch
        if internal:
            c.setFont("Times-Bold", 9)
            c.drawString(0.7 * inch, y, f"Area base {_money(area['base'])}   +20% {_money(area['client_total'] - area['base'])}   client {_money(area['client_total'])}")
        y -= 18
        grand_base += area["base"]
        grand_client += area["client_total"]

    y -= 8
    c.setStrokeColor(HAIR)
    c.line(0.6 * inch, y, PAGE_W - 0.6 * inch, y)
    y -= 18
    c.setFont("Times-Bold", 13)
    if internal:
        c.drawString(0.6 * inch, y, f"BASE {_money(grand_base)}")
        c.drawString(3.2 * inch, y, f"+20% {_money(grand_client - grand_base)}")
        c.drawRightString(PAGE_W - 0.6 * inch, y, f"CLIENT TOTAL {_money(grand_client)}")
    else:
        c.drawRightString(PAGE_W - 0.6 * inch, y, f"TOTAL {_money(grand_client)}")

    terms = packet.get("terms") or (
        "50% deposit to begin. Balance due on install. "
        "This estimate is valid for 30 days."
    )
    y -= 36
    c.setFont("Times-Bold", 11)
    c.drawString(0.6 * inch, y, "TERMS")
    y -= 14
    c.setFont("Times-Roman", 9)
    for chunk in terms.split(". "):
        text = chunk if chunk.endswith(".") else f"{chunk}."
        c.drawString(0.6 * inch, y, text[:110])
        y -= 12

    if not internal:
        pay_url = packet.get("square_pay_url") or "Pay deposit online: [Square payment link]"
        y -= 10
        c.setFont("Times-Bold", 11)
        c.drawString(0.6 * inch, y, "SQUARE PAY")
        y -= 14
        c.setFont("Times-Roman", 9)
        c.drawString(0.6 * inch, y, str(pay_url)[:90])
        _draw_qr_box(c, PAGE_W - 2.1 * inch, 0.55 * inch, 1.35 * inch, str(pay_url))
        c.setFont("Times-Bold", 8)
        c.drawRightString(PAGE_W - 0.6 * inch, 0.4 * inch, "Scan to pay")

    c.setFont("Times-Bold", 8)
    label = "INTERNAL COPY — BASE + MARKUP  ·  NOT FOR CLIENT" if internal else "CLIENT COPY"
    c.drawString(0.6 * inch, 0.4 * inch, label)
    c.save()
    return buf.getvalue()


def generate_estimate_copies(job_id: str, packet: dict[str, Any]) -> dict[str, Any]:
    """Client copy is gated. Internal copy is generated only after the same gate.

    The founder rule is: no client estimate generation until stage 4 is
    approved. The pair is produced together after that approval.
    """
    gate = assert_client_estimate_allowed(job_id)
    client_pdf = render_willard_estimate_pdf(packet, internal=False)
    internal_pdf = render_willard_estimate_pdf(packet, internal=True)
    return {
        "job_id": job_id,
        "gate": gate,
        "client_pdf": client_pdf,
        "internal_pdf": internal_pdf,
        "sent": False,
        "layout": "willard",
        "grouping": "area/Labor/Materials/Install",
    }
