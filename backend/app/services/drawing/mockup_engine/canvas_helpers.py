"""Shared ReportLab canvas drawing helpers for parametric mockups."""
from __future__ import annotations

import math
from typing import Tuple
from reportlab.lib.colors import HexColor, Color
from reportlab.pdfgen import canvas

# Palette defaults
INK = HexColor("#1F2420")
MUT = HexColor("#6B6F68")
GOLD = HexColor("#B8892E")
PAPER = HexColor("#F7F3EC")
WHITE = HexColor("#FFFFFF")
GRAY_LINE = HexColor("#CCCCCC")
WOOD_FILL = HexColor("#A67B5B")
WOOD_DARK = HexColor("#5E3D28")


def format_in(val: float) -> str:
    """Format decimal inches cleanly (e.g. 249.75 -> 249.75", 18.0 -> 18")."""
    s = f"{val:.3f}".rstrip("0").rstrip(".")
    return s + '"'


def draw_chrome(
    c: canvas.Canvas,
    w: float,
    h: float,
    title: str,
    subtitle: str,
    page: int,
    total: int,
    company: str = "EMPIRE WORKROOM",
    tagline: str = "CUSTOM UPHOLSTERY & FABRICATION",
    locale: str = "Hyattsville MD",
    doc_kind: str = "ILLUSTRATION",
    quote_tag: str = "EST-2026-000 · NOT SENT",
    footer_text: str = "",
    date_str: str = "2026-10-08",
) -> None:
    """Draw professional top and bottom chrome bands adhering to the Empire Drawing Standard."""
    # Paper background
    c.setFillColor(PAPER)
    c.rect(0, 0, w, h, stroke=0, fill=1)

    # Top band
    c.setFillColor(INK)
    c.rect(0, h - 46, w, 46, stroke=0, fill=1)

    c.setFillColor(WHITE)
    c.setFont("Times-Bold", 17)
    c.drawString(24, h - 30, company)

    # Shift tagline/locale right if company name is long (e.g. WOODCRAFT BY EMPIRE)
    comp_width = c.stringWidth(company, "Times-Bold", 17)
    tagline_x = max(222, 24 + comp_width + 16)

    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(tagline_x, h - 22, tagline)

    c.setFillColor(HexColor("#DDDDDD"))
    c.setFont("Helvetica", 7.5)
    c.drawString(tagline_x, h - 34, locale)

    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(w - 24, h - 22, doc_kind)

    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawRightString(w - 24, h - 34, quote_tag)

    # Page title / subtitle
    c.setFillColor(INK)
    c.setFont("Times-Bold", 15)
    c.drawString(24, h - 70, title)

    c.setFillColor(MUT)
    c.setFont("Times-Italic", 9)
    c.drawString(24, h - 84, subtitle)

    # Bottom band
    c.setFillColor(INK)
    c.rect(0, 0, w, 24, stroke=0, fill=1)

    c.setFillColor(HexColor("#BBBBBB"))
    c.setFont("Helvetica", 7)
    c.drawString(24, 9, footer_text or f"{company} · drawn from quoted dimensions")
    c.drawRightString(w - 24, 9, f"PAGE {page} / {total} · {date_str} · NOT SENT")


def draw_scale_bar(c: canvas.Canvas, x: float, y: float, s: float, label: str) -> None:
    """Draw architectural alternating 4-ft scale bar."""
    c.setStrokeColor(INK)
    c.setLineWidth(0.6)
    for i in range(4):  # 4 ft, alternating
        c.setFillColor(INK if i % 2 == 0 else PAPER)
        c.rect(x + i * 12 * s, y, 12 * s, 4, stroke=1, fill=1)

    c.setFillColor(INK)
    c.setFont("Helvetica", 6.5)
    for i in range(5):
        c.drawCentredString(x + i * 12 * s, y + 7, f"{i}'")

    c.setFont("Helvetica-Bold", 7)
    c.drawString(x + 48 * s + 8, y, f"SCALE {label}")


def dim_h(c: canvas.Canvas, x1: float, x2: float, y: float, text: str, size: float = 7.0) -> None:
    """Draw horizontal dimension line with ticks and centered label."""
    c.setStrokeColor(MUT)
    c.setLineWidth(0.5)
    c.line(x1, y, x2, y)
    for xx in (x1, x2):
        c.line(xx, y - 3, xx, y + 3)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", size)
    c.drawCentredString((x1 + x2) / 2, y + 3, text)


def dim_v(
    c: canvas.Canvas,
    x: float,
    y1: float,
    y2: float,
    text: str,
    size: float = 7.0,
    right: bool = True,
) -> None:
    """Draw vertical dimension line with ticks and rotated label."""
    c.setStrokeColor(MUT)
    c.setLineWidth(0.5)
    c.line(x, y1, x, y2)
    for yy in (y1, y2):
        c.line(x - 3, yy, x + 3, yy)
    c.saveState()
    c.translate(x + (4 if right else -4), (y1 + y2) / 2)
    c.rotate(90)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", size)
    c.drawCentredString(0, -size if right else 2, text)
    c.restoreState()


def draw_legend(
    c: canvas.Canvas,
    lx: float,
    ly: float,
    back_color: Color,
    seat_color: Color,
    back_label: str,
    seat_label: str,
    runs: list[Tuple[str, float]],
    notes: list[str] = None,
) -> None:
    """Draw legend and schedule block."""
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(INK)
    c.drawString(lx, ly, "LEGEND")

    # Back swatch
    c.setFillColor(back_color)
    c.setStrokeColor(INK)
    c.setLineWidth(0.5)
    c.rect(lx, ly - 16, 18, 8, stroke=1, fill=1)
    c.setFillColor(INK)
    c.setFont("Helvetica", 7)
    c.drawString(lx + 24, ly - 15, back_label)

    # Seat swatch
    c.setFillColor(seat_color)
    c.rect(lx, ly - 30, 18, 8, stroke=1, fill=1)
    c.setFillColor(INK)
    c.drawString(lx + 24, ly - 29, seat_label)

    # Schedule
    if runs:
        c.setFont("Helvetica-Bold", 8)
        c.drawString(lx, ly - 52, "QUOTED RUNS (seat = back length)")
        c.setFont("Helvetica", 7.5)
        yy = ly - 66
        for k, v in runs:
            c.drawString(lx, yy, k)
            c.drawRightString(lx + 120, yy, format_in(v))
            yy -= 11
    else:
        yy = ly - 40

    if notes:
        c.setFillColor(MUT)
        c.setFont("Helvetica", 6.5)
        for n in notes:
            c.drawString(lx, yy - 6, n)
            yy -= 9
