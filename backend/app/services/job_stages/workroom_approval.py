"""3-page workroom approval document. Internal only. Never sent to the client."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib.colors import black, white
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from app.services.job_stages.catalog import WORKROOM_MARKUP

PAGE_W, PAGE_H = letter
INK = black
MARGIN = 0.55 * inch


def _money(value: Any) -> str:
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def _draw_header(c: canvas.Canvas, title: str, subtitle: str) -> None:
    c.setFillColor(INK)
    c.setFont("Times-Bold", 22)
    c.drawString(MARGIN, PAGE_H - 0.7 * inch, title.upper())
    c.setFont("Times-Bold", 13)
    c.drawString(MARGIN, PAGE_H - 0.95 * inch, subtitle)
    c.setStrokeColor(INK)
    c.setLineWidth(2.2)
    c.line(MARGIN, PAGE_H - 1.08 * inch, PAGE_W - MARGIN, PAGE_H - 1.08 * inch)


def _price_rows(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for line in lines or []:
        qty = float(line.get("qty") or line.get("quantity") or 1)
        unit_price = float(line.get("unit_price") or line.get("base") or 0)
        base = round(qty * unit_price, 2)
        markup = round(base * WORKROOM_MARKUP, 2)
        client_total = round(base + markup, 2)
        rows.append({
            "unit": line.get("unit") or line.get("description") or "Item",
            "unit_price": unit_price,
            "qty": qty,
            "base": base,
            "markup": markup,
            "client_total": client_total,
        })
    return rows


def render_workroom_approval_pdf(packet: dict[str, Any]) -> bytes:
    """p1 measurements + prices, p2 elevation, p3 site photo. Big bold black."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setPageCompression(0)
    client = packet.get("client_name") or "Client"
    area = packet.get("area") or packet.get("room") or "Area"
    job_label = packet.get("job_number") or packet.get("title") or ""

    # ── Page 1: measurements, prices, terms, confirm ──
    _draw_header(c, "Workroom Approval", f"{client}  ·  {area}  ·  {job_label}")
    y = PAGE_H - 1.4 * inch
    c.setFont("Times-Bold", 16)
    c.drawString(MARGIN, y, "MEASUREMENTS")
    y -= 22
    c.setFont("Times-Bold", 12)
    measurements = packet.get("measurements") or {}
    if isinstance(measurements, dict) and measurements:
        for key, value in measurements.items():
            c.drawString(MARGIN, y, f"{str(key).upper()}:  {value}")
            y -= 18
    else:
        for line in packet.get("measurement_lines") or ["No measurements recorded."]:
            c.drawString(MARGIN, y, str(line))
            y -= 18

    y -= 10
    c.setFont("Times-Bold", 16)
    c.drawString(MARGIN, y, "PROPOSED PRICES")
    y -= 24
    headers = ("UNIT", "UNIT PRICE", "QTY", "BASE", "+20%", "CLIENT TOTAL")
    widths = (1.7 * inch, 1.15 * inch, 0.7 * inch, 1.05 * inch, 1.05 * inch, 1.4 * inch)
    x = MARGIN
    c.setFont("Times-Bold", 10)
    for header, width in zip(headers, widths):
        c.drawString(x, y, header)
        x += width
    y -= 6
    c.setLineWidth(1.6)
    c.line(MARGIN, y, PAGE_W - MARGIN, y)
    y -= 18
    c.setFont("Times-Bold", 12)
    totals = {"base": 0.0, "markup": 0.0, "client_total": 0.0}
    for row in _price_rows(packet.get("lines") or []):
        x = MARGIN
        values = (
            str(row["unit"])[:22],
            _money(row["unit_price"]),
            f"{row['qty']:g}",
            _money(row["base"]),
            _money(row["markup"]),
            _money(row["client_total"]),
        )
        for value, width in zip(values, widths):
            c.drawString(x, y, value)
            x += width
        totals["base"] += row["base"]
        totals["markup"] += row["markup"]
        totals["client_total"] += row["client_total"]
        y -= 18
    y -= 6
    c.setLineWidth(1.6)
    c.line(MARGIN, y + 12, PAGE_W - MARGIN, y + 12)
    c.setFont("Times-Bold", 13)
    c.drawString(MARGIN, y - 4, "TOTAL")
    c.drawString(MARGIN + 4.6 * inch, y - 4, _money(totals["base"]))
    c.drawString(MARGIN + 5.65 * inch, y - 4, _money(totals["markup"]))
    c.drawRightString(PAGE_W - MARGIN, y - 4, _money(totals["client_total"]))

    y = 2.6 * inch
    c.setFont("Times-Bold", 16)
    c.drawString(MARGIN, y, "TERMS")
    y -= 20
    c.setFont("Times-Bold", 11)
    terms = packet.get("terms") or (
        "Internal workroom document. Not a client estimate. "
        "No estimate may go to the client until this page is approved. "
        "Prices show base cost, +20% markup, and client total. "
        "Nothing is sent from this document."
    )
    for line in _wrap(terms, 88):
        c.drawString(MARGIN, y, line)
        y -= 15

    y = 1.35 * inch
    c.setFont("Times-Bold", 16)
    c.drawString(MARGIN, y, "CONFIRM")
    y -= 28
    c.setStrokeColor(INK)
    c.setLineWidth(2)
    c.rect(MARGIN, y - 8, PAGE_W - 2 * MARGIN, 28, fill=0, stroke=1)
    c.setFont("Times-Bold", 12)
    c.drawString(MARGIN + 10, y + 2, "WORKROOM APPROVED BY: ______________________   DATE: ____________")
    c.setFont("Times-Bold", 8)
    c.drawString(MARGIN, 0.4 * inch, "PAGE 1 OF 3  ·  INTERNAL  ·  DO NOT SEND TO CLIENT")
    c.showPage()

    # ── Page 2: full-page elevation ──
    _draw_header(c, "Elevation", f"{client}  ·  {area}")
    frame_bottom = 0.7 * inch
    frame_top = PAGE_H - 1.25 * inch
    c.setLineWidth(2.4)
    c.rect(MARGIN, frame_bottom, PAGE_W - 2 * MARGIN, frame_top - frame_bottom, fill=0, stroke=1)
    elevation = packet.get("elevation_path") or packet.get("elevation")
    drawn = False
    if elevation and Path(str(elevation)).is_file():
        try:
            c.drawImage(
                str(elevation),
                MARGIN + 8,
                frame_bottom + 8,
                width=PAGE_W - 2 * MARGIN - 16,
                height=frame_top - frame_bottom - 16,
                preserveAspectRatio=True,
                anchor="c",
                mask="auto",
            )
            drawn = True
        except Exception:
            drawn = False
    if not drawn:
        c.setFont("Times-Bold", 18)
        c.drawCentredString(PAGE_W / 2, PAGE_H / 2 + 10, "FULL-PAGE ELEVATION")
        c.setFont("Times-Bold", 12)
        c.drawCentredString(
            PAGE_W / 2,
            PAGE_H / 2 - 16,
            "Gold-template drawing with full dimensions belongs here.",
        )
    c.setFont("Times-Bold", 8)
    c.drawString(MARGIN, 0.4 * inch, "PAGE 2 OF 3  ·  INTERNAL  ·  DO NOT SEND TO CLIENT")
    c.showPage()

    # ── Page 3: site photo ──
    _draw_header(c, "Site Photo", f"{client}  ·  {area}")
    frame_bottom = 0.7 * inch
    frame_top = PAGE_H - 1.25 * inch
    c.setLineWidth(2.4)
    c.setFillColor(white)
    c.rect(MARGIN, frame_bottom, PAGE_W - 2 * MARGIN, frame_top - frame_bottom, fill=1, stroke=1)
    c.setFillColor(INK)
    photo = packet.get("site_photo_path") or packet.get("site_photo")
    drawn = False
    if photo and Path(str(photo)).is_file():
        try:
            c.drawImage(
                str(photo),
                MARGIN + 8,
                frame_bottom + 8,
                width=PAGE_W - 2 * MARGIN - 16,
                height=frame_top - frame_bottom - 16,
                preserveAspectRatio=True,
                anchor="c",
                mask="auto",
            )
            drawn = True
        except Exception:
            drawn = False
    if not drawn:
        c.setFont("Times-Bold", 18)
        c.drawCentredString(PAGE_W / 2, PAGE_H / 2 + 10, "SITE PHOTO")
        c.setFont("Times-Bold", 12)
        c.drawCentredString(PAGE_W / 2, PAGE_H / 2 - 16, "Field photo from the prelim info sheet.")
    c.setFont("Times-Bold", 8)
    c.drawString(MARGIN, 0.4 * inch, "PAGE 3 OF 3  ·  INTERNAL  ·  DO NOT SEND TO CLIENT")
    c.save()
    return buf.getvalue()


def _wrap(text: str, width: int) -> list[str]:
    words = str(text).split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if len(trial) > width and current:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines or [""]
