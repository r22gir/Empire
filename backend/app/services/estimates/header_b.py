"""Header option B: dark band, brand and sub-line, contact row, right-hand meta.

Used by the portrait estimate and the landscape presentation. The
founder's name is never drawn. The website is the public workroom host.
"""
from __future__ import annotations

from reportlab.lib.colors import HexColor, white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from app.config.workroom_billing import (
    BILLED_BY_NELMA,
    WorkroomBilling,
    get_workroom_billing,
)
from app.services.drawing.max_sheet_chrome import GOLD, INK, PAPER

BAND = HexColor("#16191c")
CREAM = HexColor("#f4efe2")
MUTE_BAND = HexColor("#a49b88")

_READY = False


def body_fonts() -> tuple[str, str, str, str]:
    global _READY
    names = {
        "DejaVuSerif-Bold": "DejaVuSerif-Bold.ttf",
        "DejaVuSans": "DejaVuSans.ttf",
        "DejaVuSans-Bold": "DejaVuSans-Bold.ttf",
        "DejaVuSansMono": "DejaVuSansMono.ttf",
    }
    if not _READY:
        from pathlib import Path
        folder = Path("/usr/share/fonts/truetype/dejavu")
        for name, fn in names.items():
            path = folder / fn
            if path.is_file():
                try:
                    pdfmetrics.registerFont(TTFont(name, str(path)))
                except Exception:
                    pass
        _READY = True

    def pick(preferred: str, fallback: str) -> str:
        try:
            pdfmetrics.getFont(preferred)
            return preferred
        except Exception:
            return fallback

    return (
        pick("DejaVuSerif-Bold", "Times-Bold"),
        pick("DejaVuSans", "Helvetica"),
        pick("DejaVuSans-Bold", "Helvetica-Bold"),
        pick("DejaVuSansMono", "Courier"),
    )


def billing_for(quote: dict | None) -> WorkroomBilling:
    return get_workroom_billing((quote or {}).get("billed_by"))


def brand_lines(bill: WorkroomBilling) -> tuple[str, str]:
    if bill.billed_by == BILLED_BY_NELMA:
        return bill.name, f"by Empire · {bill.tagline}"
    return bill.name, bill.tagline


def _icon(c: Canvas, kind: str, x: float, y: float) -> None:
    c.setStrokeColor(GOLD)
    c.setFillColor(GOLD)
    c.setLineWidth(0.7)
    if kind == "pin":
        c.circle(x + 4, y + 5, 2.2, stroke=1, fill=0)
        c.line(x + 4, y + 2.8, x + 4, y)
    elif kind == "phone":
        c.roundRect(x + 2.2, y, 3.6, 6.2, 0.8, stroke=1, fill=0)
    elif kind == "mail":
        c.rect(x + 0.6, y + 1.2, 7, 4.6, stroke=1, fill=0)
        c.line(x + 0.6, y + 5.8, x + 4.1, y + 3.2)
        c.line(x + 7.6, y + 5.8, x + 4.1, y + 3.2)
    else:
        c.circle(x + 4, y + 3.2, 3.0, stroke=1, fill=0)
        c.line(x + 1.2, y + 3.2, x + 6.8, y + 3.2)


def paint_header_b(
    c: Canvas,
    bill: WorkroomBilling,
    *,
    page_w: float,
    page_h: float,
    right_lines: list[tuple[str, float, object]],
    band_h: float = 78.0,
) -> float:
    """Paint the band. Returns the y where body content starts."""
    serif, sans, sans_b, _mono = body_fonts()
    name, sub = brand_lines(bill)
    c.setFillColor(PAPER)
    c.rect(0, 0, page_w, page_h, fill=1, stroke=0)
    top = page_h - band_h
    c.setFillColor(BAND)
    c.rect(0, top, page_w, band_h, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.rect(0, top - 2.2, page_w, 2.2, fill=1, stroke=0)

    c.setFillColor(CREAM)
    c.setFont(serif, 15)
    c.drawString(28, page_h - 24, name)
    c.setFillColor(GOLD)
    c.setFont(sans, 7.5)
    c.drawString(28, page_h - 38, sub)

    contacts = (
        ("pin", bill.address),
        ("phone", bill.phone),
        ("mail", bill.email),
        ("web", bill.website),
    )
    x = 28.0
    y = page_h - 62
    c.setFillColor(MUTE_BAND)
    c.setFont(sans, 6.4)
    for kind, text in contacts:
        _icon(c, kind, x, y - 1)
        c.setFillColor(CREAM)
        c.drawString(x + 12, y, text)
        x += c.stringWidth(text, sans, 6.4) + 22
        if x > page_w * 0.62:
            x = 28.0
            y -= 12

    cursor_y = page_h - 22
    for text, size, color in right_lines:
        c.setFillColor(color)
        c.setFont(sans_b if size >= 9 else sans, size)
        c.drawRightString(page_w - 28, cursor_y, text)
        cursor_y -= size + 4
    return top - 14


def paint_footer(c: Canvas, bill: WorkroomBilling, *, page_w: float, left: str, right: str) -> None:
    _serif, sans, sans_b, _mono = body_fonts()
    name, sub = brand_lines(bill)
    c.setFillColor(BAND)
    c.rect(0, 0, page_w, 28, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.rect(0, 28, page_w, 1.6, fill=1, stroke=0)
    c.setFillColor(MUTE_BAND)
    c.setFont(sans, 6)
    c.drawString(28, 12, f"{name} · {sub}")
    c.setFillColor(CREAM)
    c.setFont(sans_b, 6.5)
    c.drawRightString(page_w - 28, 12, right)
    c.setFillColor(GOLD)
    c.setFont(sans, 6)
    c.drawCentredString(page_w / 2, 12, left)


def money(value: float) -> str:
    return f"${float(value):,.2f}"
