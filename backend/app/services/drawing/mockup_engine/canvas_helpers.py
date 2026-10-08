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
    """Format decimal inches as fractions (e.g. 249.75 -> 249 3/4", 26.75 -> 26 3/4", 18.0 -> 18")."""
    if val is None:
        return ""
    val_f = float(val)
    sixteenths = round(val_f * 16)
    whole = sixteenths // 16
    rem = sixteenths - whole * 16
    if rem == 0:
        return f'{whole}"' if whole else '0"'
    from math import gcd
    g = gcd(rem, 16)
    n = rem // g
    d = 16 // g
    if whole:
        return f'{whole} {n}/{d}"'
    return f'{n}/{d}"'


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
    address: str = "5124 Frolich Ln, Hyattsville, MD 20781",
    contact_info: str = "(703) 213-6484 · workroom.empirebox.store",
    client_name: str = "",
    client_address: str = "",
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
    c.rect(0, h - 48, w, 48, stroke=0, fill=1)

    c.setFillColor(WHITE)
    c.setFont("Times-Bold", 17)
    c.drawString(24, h - 31, company)

    # Shift tagline/locale right if company name is long (e.g. WOODCRAFT BY EMPIRE)
    comp_width = c.stringWidth(company, "Times-Bold", 17)
    tagline_x = max(222, 24 + comp_width + 16)

    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(tagline_x, h - 16, tagline)

    # Empire brand address and contact (pulled from business config)
    c.setFillColor(HexColor("#DDDDDD"))
    c.setFont("Helvetica", 6.8)
    c.drawString(tagline_x, h - 28, address)
    c.drawString(tagline_x, h - 40, contact_info)

    # Client/job info block (if provided)
    if client_name:
        client_str = f"CLIENT: {client_name}"
        if client_address:
            client_str += f" · {client_address}"
        c.setFillColor(HexColor("#C0B298"))
        c.setFont("Helvetica-Bold", 7.0)
        c.drawRightString(w - 24, h - 13, client_str)

    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(w - 24, h - 25, doc_kind)

    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawRightString(w - 24, h - 37, quote_tag)

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
    c.drawString(24, 9, footer_text or f"{company} · {address} · drawn from quoted dimensions")
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
    col_width: float = 180.0,
) -> None:
    """Draw legend and schedule block with proper column formatting."""
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
            # Cleanly truncate/fit label within column
            lbl = k
            if len(lbl) > 28:
                lbl = lbl[:26] + ".."
            c.drawString(lx, yy, lbl)
            c.drawRightString(lx + col_width, yy, format_in(v))
            yy -= 11
    else:
        yy = ly - 40

    if notes:
        c.setFillColor(MUT)
        c.setFont("Helvetica", 6.5)
        for n in notes:
            c.drawString(lx, yy - 6, n)
            yy -= 9


def draw_casework_legend(
    c: canvas.Canvas,
    lx: float,
    ly: float,
    wood_species: str,
    wood_finish: str,
    boxes: list,
    materials: list = None,
    notes: list[str] = None,
    col_width: float = 230.0,
) -> None:
    """Draw legend and carcass schedule specifically for casework and millwork."""
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(INK)
    c.drawString(lx, ly, "CASEWORK & MILLWORK SPECIFICATION")

    # Wood finish swatch
    c.setFillColor(WOOD_FILL)
    c.setStrokeColor(WOOD_DARK)
    c.setLineWidth(0.5)
    c.rect(lx, ly - 16, 18, 8, stroke=1, fill=1)
    c.setFillColor(INK)
    c.setFont("Helvetica", 7)
    c.drawString(lx + 24, ly - 15, f"{wood_species} · {wood_finish}")

    # Carcass boxes schedule
    c.setFont("Helvetica-Bold", 8)
    c.drawString(lx, ly - 40, "CARCASS BOXES & BAYS")
    c.setFont("Helvetica", 7)
    yy = ly - 54
    for b in boxes:
        b_name = getattr(b, "name", "Bay")
        b_w = getattr(b, "width_in", 0.0)
        b_h = getattr(b, "height_in", 0.0)
        b_d = getattr(b, "depth_in", 0.0)
        sh = getattr(b, "shelves", 0)
        dr = getattr(b, "drawers", 0)
        doors = getattr(b, "doors", 0)

        details = []
        if dr > 0: details.append(f"{dr} drws")
        if doors > 0: details.append(f"{doors} drs")
        if sh > 0: details.append(f"{sh} shlvs")
        if not details: details.append("open")
        det_str = ", ".join(details)

        lbl = f"{b_name} ({det_str})"
        if len(lbl) > 36:
            lbl = lbl[:34] + ".."
        dim_str = f"{format_in(b_w)} x {format_in(b_h)} x {format_in(b_d)}"

        c.drawString(lx, yy, lbl)
        c.drawRightString(lx + col_width, yy, dim_str)
        yy -= 11

    # Materials / hardware
    if materials:
        yy -= 4
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(lx, yy, "PRIMARY MATERIALS")
        yy -= 11
        c.setFont("Helvetica", 6.5)
        for m in materials[:3]:
            m_name = m.get("name") if isinstance(m, dict) else str(m)
            m_qty = m.get("quantity", "") if isinstance(m, dict) else ""
            m_unit = m.get("unit", "") if isinstance(m, dict) else ""
            c.drawString(lx, yy, f"• {m_name}")
            if m_qty:
                c.drawRightString(lx + col_width, yy, f"{m_qty} {m_unit}")
            yy -= 9

    if notes:
        yy -= 4
        c.setFillColor(MUT)
        c.setFont("Helvetica", 6.5)
        for n in notes:
            c.drawString(lx, yy - 4, n)
            yy -= 9
