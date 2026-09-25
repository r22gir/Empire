"""Upholstery-on-existing-shell banquette sheets (U / L).

Acceptance: Marleys EST-2026-272 — plan / elev / iso / mockup / materials
with PATTERN BACK vs PLAIN SEAT called out (McLean / gold-standard vibe).

This is NOT the millwork/CNC bench_renderer. No wood frame, ribs,
dados, or 24" auto-slice cushion heroes. Plan = shell outline + seat
cushion footprint; elevation = shell height vs net back on 2" foam;
iso = cushion volumes; mockup = client color view; materials = fabric + ply.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, black, white, Color

NAVY = HexColor("#1a365d")
GOLD = HexColor("#b8860b")
GRAY = HexColor("#4a5568")
SHELL = HexColor("#2c5282")
CUSH = HexColor("#c05621")
PROV = HexColor("#c53030")
LT_BLUE = HexColor("#ebf4ff")
LT_PEACH = HexColor("#feebc8")
LT_FOAM = HexColor("#fbd38d")
# Client mockup placeholders (COM TBD)
PATTERN_BACK = HexColor("#8b5a2b")      # warm basketweave-ish brown
PATTERN_BACK_DK = HexColor("#6b4423")
PLAIN_SEAT = HexColor("#d9cbb0")        # plain taupe / cream
PLAIN_SEAT_DK = HexColor("#c4b498")
LT_GRAY = HexColor("#edf2f7")
MED_GRAY = HexColor("#cbd5e0")

# Empire yardage defaults (drawing/yardage.py)
FABRIC_WIDTH_DEFAULT = 54.0
WASTE_FABRIC = 1.15          # 15%
WASTE_PLY = 1.15             # 15% cutting waste on 1/2" ply
PLY_SHEET_SF = 32.0          # 4x8 sheet
PLY_THICKNESS = 0.5

COS30 = math.cos(math.radians(30))
SIN30 = math.sin(math.radians(30))


@dataclass
class UShellSpec:
    """U banquette upholstery-on-shell dims — ALL INCHES."""
    back_outer: float = 249.75
    arm_left: float = 41.25       # wing LENGTH along room (not thickness)
    arm_right: float = 52.0       # wing LENGTH — asymmetric, do NOT max()
    seat_depth: float = 16.25     # cushion depth / wing THICKNESS
    shell_height: float = 30.25
    net_back_height: float = 26.75  # sits ON seat foam; = shell - 3.5 board/foam/Dacron
    seat_foam: float = 2.0
    board_stack: float = 3.5

    @property
    def developed_outer_in(self) -> float:
        return self.back_outer + self.arm_left + self.arm_right

    @property
    def developed_outer_lf(self) -> float:
        return self.developed_outer_in / 12.0

    @property
    def footprint_width(self) -> float:
        return self.back_outer + 2 * self.seat_depth

    @property
    def back_sf(self) -> float:
        return self.developed_outer_lf * (self.net_back_height / 12.0)

    @property
    def seat_sf(self) -> float:
        return self.developed_outer_lf * (self.seat_depth / 12.0)


@dataclass
class LShellSpec:
    """L banquette — ALL INCHES. Depth/height provisional vs U."""
    leg_short: float = 48.875
    leg_long: float = 107.75
    seat_depth: float = 19.0
    shell_height: float = 30.0
    seat_height: float = 18.0
    net_back_height: float = 26.75  # match U / quote L-B 29.09; 0 → shell-3.5
    seat_foam: float = 2.0
    provisional: bool = True

    @property
    def developed_outer_in(self) -> float:
        return self.leg_short + self.leg_long

    @property
    def developed_outer_lf(self) -> float:
        return self.developed_outer_in / 12.0

    @property
    def net_back(self) -> float:
        if self.net_back_height > 0:
            return self.net_back_height
        return max(self.shell_height - 3.5, 0)

    @property
    def back_sf(self) -> float:
        return self.developed_outer_lf * (self.net_back / 12.0)

    @property
    def seat_sf(self) -> float:
        return self.developed_outer_lf * (self.seat_depth / 12.0)


@dataclass
class SheetMeta:
    quote_num: str = "EST-2026-272"
    job: str = "Marley's Hyattsville — U+L Banquette Upholstery"
    note: str = (
        "Existing shells on site. Cushion footprint + shell outline only — not wood frame. "
        "PATTERN fabric = BACKS only; PLAIN fabric = SEATS."
    )
    client: str = "Dave Romero / Marley's Hyattsville"
    rev: str = "B"
    drawn_by: str = "MAX AI / Empire Workroom"
    date_str: str = ""

    def __post_init__(self):
        if not self.date_str:
            self.date_str = datetime.now().strftime("%m/%d/%Y")


@dataclass
class MaterialsTakeoff:
    fabric_width_in: float
    waste_fabric: float
    waste_ply: float
    pattern_back_sf: float
    plain_seat_sf: float
    pattern_yards_raw: float
    plain_yards_raw: float
    pattern_yards_order: float
    plain_yards_order: float
    ply_back_sf: float
    ply_seat_sf: float
    ply_total_sf: float
    ply_with_waste_sf: float
    ply_sheets: int
    assumptions: list
    formulas: list


def compute_materials(
    u: UShellSpec,
    L: LShellSpec,
    fabric_width_in: float = FABRIC_WIDTH_DEFAULT,
    waste_fabric: float = WASTE_FABRIC,
    waste_ply: float = WASTE_PLY,
) -> MaterialsTakeoff:
    """Face-area fabric yards + 1/2\" plywood takeoff. Explicit assumptions."""
    pattern_sf = u.back_sf + L.back_sf
    plain_sf = u.seat_sf + L.seat_sf

    # yards = (sf * 144 * waste) / (fabric_width * 36) = sf * 4 * waste / fabric_width
    def yards(sf: float) -> float:
        return (sf * 4.0 * waste_fabric) / fabric_width_in

    pat_raw = yards(pattern_sf)
    pln_raw = yards(plain_sf)
    # Order qty: round up to next 0.25 yd (shop-friendly)
    def ceil_quarter(y: float) -> float:
        return math.ceil(y * 4.0) / 4.0

    ply_back = pattern_sf  # backer boards match net-back face area
    ply_seat = plain_sf    # seat decks match seat face area
    ply_tot = ply_back + ply_seat
    ply_w = ply_tot * waste_ply
    sheets = int(math.ceil(ply_w / PLY_SHEET_SF))

    assumptions = [
        f'Fabric width ASSUMED {fabric_width_in:.0f}" (Empire drawing/yardage.py default; provenance=pending until COM confirmed).',
        f"Fabric waste {round((waste_fabric - 1) * 100)}% (WASTE_UPHOLSTERY) — covers seams, wrap, pattern match on backs.",
        "PATTERN fabric covers BACK faces only (U-B + L-B). Seat is PLAIN — do not order pattern for seats.",
        "PLAIN fabric covers SEAT faces only (U-S + L-S).",
        "Face-area method: yards = (SF × 144 × waste) / (width × 36). No railroad continuous-strip used for order qty.",
        "Alt railroad check (info only): if goods railroaded and net-back ≤ usable width, strip yards ≈ developed_in/36 × waste — usually HIGHER than face-area; face-area is order basis.",
        f'1/2" plywood: backer boards under back cushions = net_back_h × developed_run (same SF as backs); seat decks = seat_depth × developed_run (same SF as seats).',
        f"Plywood waste {round((waste_ply - 1) * 100)}% for cuts/kerf/grain. Sheet size 4'×8' = {PLY_SHEET_SF:.0f} sf.",
        "L depth/height still PROVISIONAL — ply/fabric for L will change when locked to U.",
        "Quote L seats SF 17.67 implies 16.25\" depth; this geometry uses provisional 19\" → higher seat SF. Confirm before ordering fabric/ply.",
        "COM / Nelma fabric TBD — placeholder colors on mockup only. No mill/SKU on this rev.",
    ]
    formulas = [
        f"U developed outer = {u.back_outer:.2f} + {u.arm_left:.2f} + {u.arm_right:.2f} = {u.developed_outer_in:.2f}\" = {u.developed_outer_lf:.2f} lf",
        f"U-B SF = {u.developed_outer_lf:.2f} lf × ({u.net_back_height:.2f}\"/12) = {u.back_sf:.2f} sf",
        f"U-S SF = {u.developed_outer_lf:.2f} lf × ({u.seat_depth:.2f}\"/12) = {u.seat_sf:.2f} sf",
        f"L developed outer = {L.leg_short:.3f} + {L.leg_long:.3f} = {L.developed_outer_in:.3f}\" = {L.developed_outer_lf:.2f} lf",
        f"L-B SF = {L.developed_outer_lf:.2f} lf × ({L.net_back:.2f}\"/12) = {L.back_sf:.2f} sf  [prov.]",
        f"L-S SF = {L.developed_outer_lf:.2f} lf × ({L.seat_depth:.2f}\"/12) = {L.seat_sf:.2f} sf  [prov.]",
        f"PATTERN yards = ({pattern_sf:.2f} sf × 4 × {waste_fabric:.2f}) / {fabric_width_in:.0f}\" = {pat_raw:.2f} yd → order {ceil_quarter(pat_raw):.2f} yd",
        f"PLAIN yards = ({plain_sf:.2f} sf × 4 × {waste_fabric:.2f}) / {fabric_width_in:.0f}\" = {pln_raw:.2f} yd → order {ceil_quarter(pln_raw):.2f} yd",
        f"Ply SF = backs {ply_back:.2f} + seats {ply_seat:.2f} = {ply_tot:.2f}; ×{waste_ply:.2f} = {ply_w:.2f} sf → {sheets} sheet(s) 4×8 1/2\"",
    ]
    return MaterialsTakeoff(
        fabric_width_in=fabric_width_in,
        waste_fabric=waste_fabric,
        waste_ply=waste_ply,
        pattern_back_sf=round(pattern_sf, 2),
        plain_seat_sf=round(plain_sf, 2),
        pattern_yards_raw=round(pat_raw, 2),
        plain_yards_raw=round(pln_raw, 2),
        pattern_yards_order=ceil_quarter(pat_raw),
        plain_yards_order=ceil_quarter(pln_raw),
        ply_back_sf=round(ply_back, 2),
        ply_seat_sf=round(ply_seat, 2),
        ply_total_sf=round(ply_tot, 2),
        ply_with_waste_sf=round(ply_w, 2),
        ply_sheets=sheets,
        assumptions=assumptions,
        formulas=formulas,
    )


def _iso(x, y, z, ox, oy, s):
    """3D (x=width, y=depth, z=height) → 2D isometric screen coords."""
    return (
        ox + (x * COS30 - y * COS30) * s,
        oy - (x * SIN30 + y * SIN30) * s - z * s,
    )


def _poly_fill(c, pts, fill, stroke, lw=1.0):
    if len(pts) < 2:
        return
    p = c.beginPath()
    p.moveTo(pts[0][0], pts[0][1])
    for pt in pts[1:]:
        p.lineTo(pt[0], pt[1])
    p.close()
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(lw)
    c.drawPath(p, fill=1, stroke=1)


def _title_block(c, w, h, sheet, sheet_title, meta: SheetMeta, total_sheets: int):
    """McLean-ish dense title block: company, job, client, rev, date, sheet X of N."""
    tb_h = 1.05 * inch
    tb_y = 0.28 * inch
    c.setStrokeColor(NAVY)
    c.setLineWidth(1.4)
    c.setFillColor(white)
    c.rect(0.35 * inch, tb_y, w - 0.7 * inch, tb_h, fill=1, stroke=1)
    # Gold accent bar
    c.setFillColor(GOLD)
    c.rect(0.35 * inch, tb_y, 0.14 * inch, tb_h, fill=1, stroke=0)
    # Divider columns
    c.setStrokeColor(MED_GRAY)
    c.setLineWidth(0.5)
    col1 = 3.6 * inch
    col2 = 7.0 * inch
    c.line(col1, tb_y, col1, tb_y + tb_h)
    c.line(col2, tb_y, col2, tb_y + tb_h)

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(0.6 * inch, tb_y + 0.78 * inch, "EMPIRE WORKROOM")
    c.setFont("Helvetica", 7)
    c.setFillColor(GRAY)
    c.drawString(0.6 * inch, tb_y + 0.58 * inch, meta.job[:62])
    c.drawString(0.6 * inch, tb_y + 0.40 * inch, f"Client: {meta.client[:48]}")
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(0.6 * inch, tb_y + 0.18 * inch, "FOR DISCUSSION — NOT FOR CONSTRUCTION")

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(col1 + 0.12 * inch, tb_y + 0.78 * inch, sheet_title)
    c.setFont("Helvetica", 7)
    c.setFillColor(GRAY)
    c.drawString(col1 + 0.12 * inch, tb_y + 0.55 * inch, meta.note[:58])
    c.drawString(col1 + 0.12 * inch, tb_y + 0.35 * inch, f"Drawn: {meta.drawn_by}")
    c.drawString(col1 + 0.12 * inch, tb_y + 0.18 * inch, f"Rev {meta.rev}  ·  {meta.date_str}")

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(w - 0.5 * inch, tb_y + 0.72 * inch, meta.quote_num)
    c.setFont("Helvetica", 8)
    c.setFillColor(GRAY)
    c.drawRightString(w - 0.5 * inch, tb_y + 0.48 * inch, f"Sheet {sheet} of {total_sheets}")
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(CUSH)
    c.drawRightString(w - 0.5 * inch, tb_y + 0.22 * inch, "PATTERN BACK / PLAIN SEAT")


def _page_header(c, w, h, title, subtitle: str = ""):
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(0.45 * inch, h - 0.38 * inch, title)
    if subtitle:
        c.setFont("Helvetica", 8)
        c.setFillColor(GRAY)
        c.drawString(0.45 * inch, h - 0.55 * inch, subtitle)
        line_y = h - 0.62 * inch
    else:
        line_y = h - 0.48 * inch
    c.setStrokeColor(GOLD)
    c.setLineWidth(2)
    c.line(0.45 * inch, line_y, w - 0.45 * inch, line_y)
    return line_y - 0.15 * inch


def _legend(c, x, y, items):
    """Compact color legend. items = [(color, label), ...]"""
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(NAVY)
    c.drawString(x, y + 12, "LEGEND")
    yy = y
    for col, lab in items:
        c.setFillColor(col)
        c.rect(x, yy, 10, 8, fill=1, stroke=0)
        c.setStrokeColor(GRAY)
        c.setLineWidth(0.4)
        c.rect(x, yy, 10, 8, fill=0, stroke=1)
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 6.5)
        c.drawString(x + 14, yy + 1, lab)
        yy -= 12


def _dim_h(c, x1, x2, y, label, color=GRAY):
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(0.6)
    c.line(x1, y, x2, y)
    c.line(x1, y - 4, x1, y + 4)
    c.line(x2, y - 4, x2, y + 4)
    c.setFont("Helvetica", 7)
    c.drawCentredString((x1 + x2) / 2, y + 5, label)


def _dim_v(c, x, y1, y2, label, color=GRAY):
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(0.6)
    c.line(x, y1, x, y2)
    c.line(x - 4, y1, x + 4, y1)
    c.line(x - 4, y2, x + 4, y2)
    c.saveState()
    c.translate(x - 6, (y1 + y2) / 2)
    c.rotate(90)
    c.setFont("Helvetica", 7)
    c.drawCentredString(0, 0, label)
    c.restoreState()


def _draw_u_plan(c, ox, oy, scale, u: UShellSpec, colored: bool = False):
    s = scale
    W, AL, AR, D = u.back_outer, u.arm_left, u.arm_right, u.seat_depth

    def sx(x):
        return ox + x * s

    def sy(y_from_back):
        return oy - y_from_back * s

    # Shell band
    shell_fill = LT_BLUE if not colored else HexColor("#a0aec0")
    c.setFillColor(shell_fill)
    path = c.beginPath()
    path.moveTo(sx(0), sy(AL))
    path.lineTo(sx(0), sy(0))
    path.lineTo(sx(W), sy(0))
    path.lineTo(sx(W), sy(AR))
    path.lineTo(sx(W - D), sy(AR))
    path.lineTo(sx(W - D), sy(D))
    path.lineTo(sx(D), sy(D))
    path.lineTo(sx(D), sy(AL))
    path.close()
    c.drawPath(path, fill=1, stroke=0)

    if colored:
        # Pattern back band (outer ring portion toward wall)
        c.setFillColor(PATTERN_BACK)
        # Approximate back strip along outer U
        bp = c.beginPath()
        bp.moveTo(sx(0), sy(AL))
        bp.lineTo(sx(0), sy(0))
        bp.lineTo(sx(W), sy(0))
        bp.lineTo(sx(W), sy(AR))
        bp.lineTo(sx(W - 2), sy(AR))
        bp.lineTo(sx(W - 2), sy(2))
        bp.lineTo(sx(2), sy(2))
        bp.lineTo(sx(2), sy(AL))
        bp.close()
        c.drawPath(bp, fill=1, stroke=0)
        # Plain seat footprint
        c.setFillColor(PLAIN_SEAT)
        sp = c.beginPath()
        sp.moveTo(sx(2), sy(AL))
        sp.lineTo(sx(2), sy(D))
        sp.lineTo(sx(W - 2), sy(D))
        sp.lineTo(sx(W - 2), sy(AR))
        sp.lineTo(sx(W - D), sy(AR))
        sp.lineTo(sx(W - D), sy(D))
        sp.lineTo(sx(D), sy(D))
        sp.lineTo(sx(D), sy(AL))
        sp.close()
        c.drawPath(sp, fill=1, stroke=0)

    c.setStrokeColor(SHELL)
    c.setLineWidth(1.8)
    c.line(sx(0), sy(AL), sx(0), sy(0))
    c.line(sx(0), sy(0), sx(W), sy(0))
    c.line(sx(W), sy(0), sx(W), sy(AR))

    c.setStrokeColor(CUSH if not colored else PLAIN_SEAT_DK)
    c.setLineWidth(1.2)
    c.setDash(4, 3)
    c.line(sx(D), sy(AL), sx(D), sy(D))
    c.line(sx(D), sy(D), sx(W - D), sy(D))
    c.line(sx(W - D), sy(D), sx(W - D), sy(AR))
    c.setDash()

    c.setStrokeColor(GRAY)
    c.setDash(2, 2)
    c.line(sx(0), sy(AL), sx(D), sy(AL))
    c.line(sx(W - D), sy(AR), sx(W), sy(AR))
    c.setDash()

    _dim_h(c, sx(0), sx(W), sy(0) + 14, f'{W:.2f}" back outer')
    _dim_v(c, sx(0) - 14, sy(0), sy(AL), f'{AL:.2f}" L arm')
    _dim_v(c, sx(W) + 14, sy(0), sy(AR), f'{AR:.2f}" R arm')
    _dim_h(c, sx(0), sx(D), sy(D) - 12, f'{D:.2f}" seat', CUSH)

    c.setFillColor(SHELL)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(sx(W / 2), sy(D / 2) - 4, "SHELL / WALL")
    if colored:
        c.setFillColor(PATTERN_BACK_DK)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(sx(W / 2), sy(4), "PATTERN BACK")
        c.setFillColor(HexColor("#5c4a32"))
        c.drawCentredString(sx(W / 2), sy(min(AL, AR) * 0.55 + D), "PLAIN SEAT")
    else:
        c.setFillColor(CUSH)
        c.drawCentredString(sx(W / 2), sy(min(AL, AR) * 0.55 + D), "SEAT CUSHION FOOTPRINT")
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 7)
    c.drawString(sx(D) + 4, sy(AL) - 10, "miter @ corners")

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(
        sx(0), sy(max(AL, AR)) - 28,
        f'Developed outer run (upholstery): {u.developed_outer_in:.2f}" = '
        f'{u.developed_outer_lf:.2f} lf   (back {W:.2f} + L {AL:.2f} + R {AR:.2f})',
    )
    c.setFont("Helvetica", 7)
    c.setFillColor(GRAY)
    c.drawString(
        sx(0), sy(max(AL, AR)) - 40,
        f'Booth footprint width (plan): {u.footprint_width:.2f}" = back + 2×seat_depth — NOT the lf takeoff.',
    )


def _draw_u_elev(c, ox, oy, scale_h, width_pts, u: UShellSpec, colored: bool = False):
    s = scale_h
    H = u.shell_height * s
    NET = u.net_back_height * s
    FOAM = u.seat_foam * s

    c.setFillColor(LT_BLUE)
    c.setStrokeColor(SHELL)
    c.setLineWidth(1.5)
    c.rect(ox, oy, width_pts, H, fill=1, stroke=1)

    back_fill = PATTERN_BACK if colored else LT_PEACH
    back_stroke = PATTERN_BACK_DK if colored else CUSH
    c.setFillColor(back_fill)
    c.setStrokeColor(back_stroke)
    c.rect(ox + 2, oy + FOAM, width_pts - 4, NET, fill=1, stroke=1)

    seat_fill = PLAIN_SEAT if colored else LT_FOAM
    c.setFillColor(seat_fill)
    c.setStrokeColor(PLAIN_SEAT_DK if colored else CUSH)
    c.rect(ox + 8, oy, width_pts - 16, FOAM, fill=1, stroke=1)

    _dim_v(c, ox - 12, oy, oy + H, f'{u.shell_height:.2f}" shell')
    _dim_v(c, ox + width_pts + 12, oy + FOAM, oy + FOAM + NET, f'{u.net_back_height:.2f}" net back')

    c.setFillColor(white if colored else GRAY)
    c.setFont("Helvetica-Bold" if colored else "Helvetica", 8 if colored else 7)
    if colored:
        c.setFillColor(white)
        c.drawCentredString(ox + width_pts / 2, oy + FOAM + NET / 2, "PATTERN BACK")
        c.setFillColor(HexColor("#5c4a32"))
        c.drawCentredString(ox + width_pts / 2, oy + FOAM / 2 - 2, "PLAIN SEAT")
    else:
        c.setFillColor(GRAY)
        c.drawString(ox + 10, oy + FOAM / 2 - 3, f'{u.seat_foam:.1f}" foam + Dacron (seat)')
        c.drawString(
            ox + 10, oy + FOAM + NET - 12,
            f'{u.board_stack:.1f}" board/foam/Dacron deducted → net back (sits ON seat)',
        )
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(ox + 10, oy + H + 8, "UPHOLSTERY ON EXISTING SHELL — not a wood frame section")


def _draw_l_plan(c, ox, oy, scale, L: LShellSpec, colored: bool = False):
    s = scale
    A, B, D = L.leg_short, L.leg_long, L.seat_depth

    def sx(x):
        return ox + x * s

    def sy(y):
        return oy - y * s

    outer = [(0, 0), (B, 0), (B, D), (D, D), (D, A), (0, A)]
    c.setFillColor(PATTERN_BACK if colored else LT_BLUE)
    c.setStrokeColor(SHELL)
    c.setLineWidth(1.8)
    path = c.beginPath()
    path.moveTo(sx(0), sy(0))
    for p in outer[1:]:
        path.lineTo(sx(p[0]), sy(p[1]))
    path.close()
    c.drawPath(path, fill=1, stroke=1)

    if colored:
        c.setFillColor(PLAIN_SEAT)
        # Seat band inset by ~nothing — show seat footprint region
        c.setStrokeColor(PLAIN_SEAT_DK)
        c.setLineWidth(1.0)
        # Fill approximate seat zone
        sp = c.beginPath()
        sp.moveTo(sx(1), sy(1))
        sp.lineTo(sx(B - 1), sy(1))
        sp.lineTo(sx(B - 1), sy(D - 1))
        sp.lineTo(sx(D - 1), sy(D - 1))
        sp.lineTo(sx(D - 1), sy(A - 1))
        sp.lineTo(sx(1), sy(A - 1))
        sp.close()
        c.drawPath(sp, fill=1, stroke=0)

    c.setStrokeColor(CUSH if not colored else PLAIN_SEAT_DK)
    c.setLineWidth(1.2)
    c.setDash(4, 3)
    c.line(sx(D), sy(D), sx(B - D), sy(D))
    c.line(sx(D), sy(D), sx(D), sy(A - D))
    c.setDash()

    _dim_h(c, sx(0), sx(B), sy(0) + 14, f'{B:.3f}" long leg')
    _dim_v(c, sx(0) - 14, sy(0), sy(A), f'{A:.3f}" short leg')
    _dim_h(c, sx(B - D), sx(B), sy(D / 2), f'{D:.1f}"', PROV)

    c.setFillColor(PROV)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(sx(B / 3), sy(A / 2), "L DEPTH / HEIGHT PROVISIONAL")
    if colored:
        c.setFillColor(PATTERN_BACK_DK)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(sx(B / 2), sy(D / 2) - 2, "PATTERN BACK")
        c.setFillColor(HexColor("#5c4a32"))
        c.drawString(sx(D) + 6, sy(D) + 8, "PLAIN SEAT")
    else:
        c.setFillColor(SHELL)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(sx(B / 2), sy(D / 2) - 2, "SHELL")
        c.setFillColor(CUSH)
        c.drawString(sx(D) + 6, sy(D) + 8, "seat footprint")

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(
        sx(0), sy(A) - 22,
        f'Developed outer run: {L.developed_outer_in:.3f}" = {L.developed_outer_lf:.2f} lf',
    )


def _draw_box_iso(c, ox, oy, s, sx, sy, w, d, z0, z1, fill, stroke, lw=1.0):
    """Draw a rectangular prism in isometric from z0 to z1."""
    # Top face
    top = [
        _iso(sx, sy, z1, ox, oy, s),
        _iso(sx + w, sy, z1, ox, oy, s),
        _iso(sx + w, sy + d, z1, ox, oy, s),
        _iso(sx, sy + d, z1, ox, oy, s),
    ]
    # Front face (low y)
    front = [
        _iso(sx, sy, z0, ox, oy, s),
        _iso(sx + w, sy, z0, ox, oy, s),
        _iso(sx + w, sy, z1, ox, oy, s),
        _iso(sx, sy, z1, ox, oy, s),
    ]
    # Right face
    right = [
        _iso(sx + w, sy, z0, ox, oy, s),
        _iso(sx + w, sy + d, z0, ox, oy, s),
        _iso(sx + w, sy + d, z1, ox, oy, s),
        _iso(sx + w, sy, z1, ox, oy, s),
    ]
    # Draw back-to-front-ish: right, front, top
    _poly_fill(c, right, Color(fill.red * 0.85, fill.green * 0.85, fill.blue * 0.85), stroke, lw)
    _poly_fill(c, front, fill, stroke, lw)
    _poly_fill(c, top, Color(min(1, fill.red * 1.12), min(1, fill.green * 1.12), min(1, fill.blue * 1.12)), stroke, lw)


def _auto_iso_scale(dims, area_w, area_h, margin=40):
    mx, my, mz = dims
    corners = [_iso(x, y, z, 0, 0, 1) for x in (0, mx) for y in (0, my) for z in (0, mz)]
    xs = [p[0] for p in corners]
    ys = [p[1] for p in corners]
    raw_w = max(xs) - min(xs) or 1
    raw_h = max(ys) - min(ys) or 1
    scale = min((area_w - margin * 2) / raw_w, (area_h - margin * 2) / raw_h)
    corners2 = [_iso(x, y, z, 0, 0, scale) for x in (0, mx) for y in (0, my) for z in (0, mz)]
    xs2 = [p[0] for p in corners2]
    ys2 = [p[1] for p in corners2]
    ox = area_w / 2 - (min(xs2) + max(xs2)) / 2
    oy = area_h / 2 - (min(ys2) + max(ys2)) / 2 + margin / 2
    return scale, ox, oy


def _draw_u_iso(c, origin_x, origin_y, area_w, area_h, u: UShellSpec, colored: bool = True):
    """Isometric U cushions — asymmetric arms. Seat plain, back pattern."""
    AL, AR, D = u.arm_left, u.arm_right, u.seat_depth
    W = u.back_outer
    side_max = max(AL, AR)
    total_w = W + 2 * D
    seat_h = u.seat_foam
    back_h = u.net_back_height
    total_h = seat_h + back_h

    scale, ox, oy = _auto_iso_scale((total_w, side_max, total_h), area_w, area_h)
    ox += origin_x
    oy += origin_y

    seat_fill = PLAIN_SEAT if colored else LT_FOAM
    back_fill = PATTERN_BACK if colored else LT_PEACH
    stroke = NAVY

    # Left wing seat + back (arm length AL along y; thickness D along x)
    # Align wings so back is at y = side_max - ... actually back runs at far y
    # Place: left wing from y=0 toward opening; back at y=side_max-D
    # Left arm length AL: if AL < side_max, offset so both meet the back
    left_y0 = side_max - AL
    right_y0 = side_max - AR

    # LEFT seat
    _draw_box_iso(c, ox, oy, scale, 0, left_y0, D, AL, 0, seat_h, seat_fill, stroke)
    # LEFT back (along outer x=0 edge, thin strip toward outside — use depth ~2.5" visual for back thickness)
    bt = min(3.0, D * 0.2)
    _draw_box_iso(c, ox, oy, scale, 0, left_y0, bt, AL, seat_h, total_h, back_fill, stroke)

    # CENTER back seat
    _draw_box_iso(c, ox, oy, scale, D, side_max - D, W, D, 0, seat_h, seat_fill, stroke)
    # CENTER back cushion
    _draw_box_iso(c, ox, oy, scale, D, side_max - bt, W, bt, seat_h, total_h, back_fill, stroke)

    # RIGHT seat
    _draw_box_iso(c, ox, oy, scale, D + W, right_y0, D, AR, 0, seat_h, seat_fill, stroke)
    # RIGHT back
    _draw_box_iso(c, ox, oy, scale, D + W + D - bt, right_y0, bt, AR, seat_h, total_h, back_fill, stroke)

    # Dim callouts
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 8)
    p1 = _iso(D + W / 2, side_max, total_h + 2, ox, oy, scale)
    c.drawCentredString(p1[0], p1[1] + 8, f'back {W:.2f}"')
    pL = _iso(0, left_y0 + AL / 2, total_h, ox, oy, scale)
    c.drawString(pL[0] - 60, pL[1], f'L arm {AL:.2f}"')
    pR = _iso(total_w, right_y0 + AR / 2, total_h, ox, oy, scale)
    c.drawString(pR[0] + 8, pR[1], f'R arm {AR:.2f}"')
    pH = _iso(total_w + 4, side_max, seat_h + back_h / 2, ox, oy, scale)
    c.setFillColor(PATTERN_BACK_DK)
    c.drawString(pH[0] + 4, pH[1], f'net back {back_h:.2f}"')
    pS = _iso(total_w + 4, 0, seat_h / 2, ox, oy, scale)
    c.setFillColor(HexColor("#5c4a32"))
    c.drawString(pS[0] + 4, pS[1], f'seat foam {seat_h:.1f}"')

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(origin_x + 10, origin_y + area_h - 12,
                 f'ISO U — developed run {u.developed_outer_in:.2f}" = {u.developed_outer_lf:.2f} lf')


def _draw_l_iso(c, origin_x, origin_y, area_w, area_h, L: LShellSpec, colored: bool = True):
    A, B, D = L.leg_short, L.leg_long, L.seat_depth
    seat_h = L.seat_foam
    back_h = L.net_back
    total_h = seat_h + back_h
    scale, ox, oy = _auto_iso_scale((B, A, total_h), area_w, area_h)
    ox += origin_x
    oy += origin_y

    seat_fill = PLAIN_SEAT if colored else LT_FOAM
    back_fill = PATTERN_BACK if colored else LT_PEACH
    stroke = NAVY
    bt = min(3.0, D * 0.2)

    # Long leg along +x at y = A - D
    _draw_box_iso(c, ox, oy, scale, 0, A - D, B, D, 0, seat_h, seat_fill, stroke)
    _draw_box_iso(c, ox, oy, scale, 0, A - bt, B, bt, seat_h, total_h, back_fill, stroke)
    # Short leg along +y at x = 0..D (corner shared — draw remaining vertical run)
    _draw_box_iso(c, ox, oy, scale, 0, 0, D, A - D, 0, seat_h, seat_fill, stroke)
    _draw_box_iso(c, ox, oy, scale, 0, 0, bt, A - D, seat_h, total_h, back_fill, stroke)

    c.setFillColor(PROV)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(origin_x + 10, origin_y + 8, "L ISO — DEPTH / HEIGHT PROVISIONAL")
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(
        origin_x + 10, origin_y + area_h - 12,
        f'ISO L — developed run {L.developed_outer_in:.3f}" = {L.developed_outer_lf:.2f} lf',
    )
    c.setFont("Helvetica", 7)
    c.setFillColor(GRAY)
    c.drawString(
        origin_x + 10, origin_y + area_h - 24,
        f'legs {L.leg_short:.3f}" + {L.leg_long:.3f}"; depth {L.seat_depth:.1f}"; shell {L.shell_height:.1f}"',
    )


def _key_dims_panel(c, x, y, u: UShellSpec, L: LShellSpec):
    c.setFillColor(LT_GRAY)
    c.setStrokeColor(NAVY)
    c.setLineWidth(0.8)
    c.roundRect(x, y - 1.55 * inch, 3.4 * inch, 1.65 * inch, 4, fill=1, stroke=1)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x + 8, y, "KEY DIMENSIONS (LOCKED)")
    c.setFont("Helvetica", 7)
    c.setFillColor(GRAY)
    lines = [
        f'U back outer {u.back_outer:.2f}"  |  L arm {u.arm_left:.2f}"  |  R arm {u.arm_right:.2f}"',
        f'U seat depth {u.seat_depth:.2f}"  |  shell H {u.shell_height:.2f}"  |  net back {u.net_back_height:.2f}"',
        f'U developed {u.developed_outer_in:.2f}" = {u.developed_outer_lf:.2f} lf  |  foam {u.seat_foam:.1f}"',
        f'L legs {L.leg_short:.3f}" + {L.leg_long:.3f}"  |  depth {L.seat_depth:.1f}" PROV',
        f'L shell {L.shell_height:.1f}" PROV  |  seat H {L.seat_height:.1f}" AFF PROV',
        "PATTERN fabric = BACKS only · PLAIN fabric = SEATS",
    ]
    yy = y - 14
    for ln in lines:
        c.drawString(x + 8, yy, ln)
        yy -= 11


# ── Sheet builders ────────────────────────────────────────────────

def render_upholstery_shell_pdf(
    *,
    out_path: str | Path,
    u: Optional[UShellSpec] = None,
    L: Optional[LShellSpec] = None,
    meta: Optional[SheetMeta] = None,
    include_u: bool = True,
    include_l: bool = True,
    fabric_width_in: float = FABRIC_WIDTH_DEFAULT,
) -> dict:
    """Write expanded upholstery-on-shell PDF (plan/elev/iso/mockup/materials)."""
    u = u or UShellSpec()
    L = L or LShellSpec()
    meta = meta or SheetMeta()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    mats = compute_materials(u, L, fabric_width_in=fabric_width_in)

    # Sheet roster
    roster = []
    if include_u:
        roster += ["U Plan", "U Elevation", "U Isometric"]
    if include_l:
        roster += ["L Plan", "L Isometric"]
    roster += ["Client Mockup", "Cushion Schedule", "Materials"]
    total = len(roster)
    sheets_done = []

    c = canvas.Canvas(str(out_path), pagesize=landscape(letter))
    w, h = landscape(letter)
    si = 0

    def finish(title_short):
        nonlocal si
        si += 1
        _title_block(c, w, h, str(si), title_short, meta, total)
        c.showPage()
        sheets_done.append(title_short)

    # ── U Plan ──
    if include_u:
        _page_header(
            c, w, h,
            "U BANQUETTE — PLAN",
            "Upholstery on existing shell · asymmetric arms · developed outer run is the lf takeoff",
        )
        scale = (8.6 * inch) / u.back_outer
        _draw_u_plan(c, 0.85 * inch, h - 1.25 * inch, scale, u)
        _legend(c, w - 2.4 * inch, h - 1.3 * inch, [
            (LT_BLUE, "Shell / wall outline"),
            (CUSH, "Seat cushion footprint"),
            (NAVY, "Developed run callout"),
        ])
        _key_dims_panel(c, w - 3.9 * inch, 2.7 * inch, u, L)
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 7.5)
        c.drawString(
            0.45 * inch, 1.50 * inch,
            "Blue = shell/wall. Orange dashed = seat footprint. Opening toward bottom. BOTH arms drawn (never max). Units: inches.",
        )
        finish("U Plan")

        # ── U Elevation ──
        _page_header(
            c, w, h,
            "U BANQUETTE — ELEVATION (height stack)",
            f'Net back {u.net_back_height}" = shell {u.shell_height}" − {u.board_stack}" board/foam/Dacron · sits ON {u.seat_foam}" foam',
        )
        _draw_u_elev(c, 1.1 * inch, 2.15 * inch, 8.2, 7.5 * inch, u)
        _legend(c, 9.2 * inch, 5.5 * inch, [
            (LT_BLUE, "Existing shell"),
            (LT_PEACH, "Net back upholstery"),
            (LT_FOAM, "Seat foam + Dacron"),
        ])
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 8)
        c.drawString(
            0.45 * inch, 1.50 * inch,
            "Shows shell height vs finished net back ON seat foam. Not a wood-frame section. Pattern fabric wraps the back face only.",
        )
        finish("U Elevation")

        # ── U Isometric ──
        _page_header(
            c, w, h,
            "U BANQUETTE — ISOMETRIC",
            "30° isometric · PATTERN BACK (brown) vs PLAIN SEAT (taupe) · placeholder COM colors",
        )
        _draw_u_iso(c, 0.6 * inch, 1.55 * inch, w - 1.2 * inch, h - 3.2 * inch, u, colored=True)
        _legend(c, 0.5 * inch, h - 1.1 * inch, [
            (PATTERN_BACK, "PATTERN BACK (COM TBD)"),
            (PLAIN_SEAT, "PLAIN SEAT (COM TBD)"),
        ])
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 7.5)
        c.drawString(
            0.45 * inch, 1.48 * inch,
            "Isometric is for client/shop orientation. Back thickness exaggerated (~3\") for readability. Arms remain asymmetric (41.25 / 52).",
        )
        finish("U Isometric")

    if include_l:
        # ── L Plan ──
        _page_header(
            c, w, h,
            "L BANQUETTE — PLAN (provisional depth/height)",
            "Lock L depth/height to U before fabrication · developed run labeled",
        )
        scale_l = (7.2 * inch) / L.leg_long
        _draw_l_plan(c, 1.1 * inch, h - 1.3 * inch, scale_l, L)
        _legend(c, w - 2.5 * inch, h - 1.3 * inch, [
            (LT_BLUE, "Shell outline"),
            (CUSH, "Seat footprint"),
            (PROV, "Provisional flag"),
        ])
        c.setFillColor(PROV)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(
            0.45 * inch, 1.50 * inch,
            f'PROVISIONAL: L depth {L.seat_depth}" / height {L.shell_height}" / seat {L.seat_height}" AFF — lock to U before fab.',
        )
        finish("L Plan")

        # ── L Isometric ──
        _page_header(
            c, w, h,
            "L BANQUETTE — ISOMETRIC (provisional)",
            "30° isometric · PATTERN BACK vs PLAIN SEAT · depth/height flagged provisional",
        )
        _draw_l_iso(c, 0.6 * inch, 1.55 * inch, w - 1.2 * inch, h - 3.2 * inch, L, colored=True)
        _legend(c, 0.5 * inch, h - 1.1 * inch, [
            (PATTERN_BACK, "PATTERN BACK (COM TBD)"),
            (PLAIN_SEAT, "PLAIN SEAT (COM TBD)"),
            (PROV, "Provisional geometry"),
        ])
        finish("L Isometric")

    # ── Client Mockup ──
    _page_header(
        c, w, h,
        "CLIENT MOCKUP — PATTERN BACK / PLAIN SEAT",
        "Placeholder fabric colors for client review · COM / Nelma TBD — not mill-matched",
    )
    # U plan colored (left) + elev colored (right)
    scale_m = (5.8 * inch) / u.back_outer
    _draw_u_plan(c, 0.55 * inch, h - 1.35 * inch, scale_m, u, colored=True)
    _draw_u_elev(c, 7.3 * inch, 3.4 * inch, 5.5, 3.2 * inch, u, colored=True)
    # Small L plan colored bottom
    scale_lm = (3.8 * inch) / L.leg_long
    _draw_l_plan(c, 0.55 * inch, 3.35 * inch, scale_lm, L, colored=True)

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(7.3 * inch, 3.1 * inch, "COLOR KEY")
    c.setFont("Helvetica", 7.5)
    c.setFillColor(PATTERN_BACK_DK)
    c.drawString(7.3 * inch, 2.85 * inch, "■ PATTERN BACK — fabric on backs only")
    c.setFillColor(HexColor("#5c4a32"))
    c.drawString(7.3 * inch, 2.65 * inch, "■ PLAIN SEAT — plain fabric on seats")
    c.setFillColor(GRAY)
    c.drawString(7.3 * inch, 2.40 * inch, "Placeholders until COM confirmed.")
    c.drawString(7.3 * inch, 2.22 * inch, "Do not use for mill color approval.")
    finish("Client Mockup")

    # ── Cushion Schedule ──
    _page_header(
        c, w, h,
        f"CUSHION SCHEDULE — {meta.quote_num}",
        "By run + SF · no 24\" auto-slice · PATTERN = backs · PLAIN = seats",
    )
    rows = [
        ("Mark", "Location", "Fabric", "Run", "H / Depth", "SF", "Notes"),
        (
            "U-B", "U backs", "PATTERN",
            f'{u.developed_outer_in:.2f}" ({u.developed_outer_lf:.2f} lf)',
            f'{u.net_back_height:.2f}" net',
            f"{u.back_sf:.2f}",
            "Arms in developed run",
        ),
        (
            "U-S", "U seats", "PLAIN",
            f'{u.developed_outer_lf:.2f} lf',
            f'{u.seat_depth:.2f}" × {u.seat_foam:.1f}" foam',
            f"{u.seat_sf:.2f}",
            "Shop splits sew/handle",
        ),
        (
            "L-B", "L backs", "PATTERN",
            f'{L.developed_outer_lf:.2f} lf',
            f'{L.net_back:.2f}" prov.',
            f"{L.back_sf:.2f}",
            "Lock height to U",
        ),
        (
            "L-S", "L seats", "PLAIN",
            f'{L.developed_outer_lf:.2f} lf',
            f'{L.seat_depth:.1f}" prov.',
            f"{L.seat_sf:.2f}",
            "Lock depth to U",
        ),
    ]
    y = h - 1.05 * inch
    col_x = [0.45, 1.05, 2.15, 3.15, 5.55, 7.15, 8.0]
    # header bar
    c.setFillColor(NAVY)
    c.rect(0.4 * inch, y - 0.06 * inch, w - 0.8 * inch, 0.28 * inch, fill=1, stroke=0)
    for i, row in enumerate(rows):
        if i == 0:
            c.setFillColor(white)
            c.setFont("Helvetica-Bold", 8)
        else:
            c.setFillColor(LT_GRAY if i % 2 == 0 else white)
            c.rect(0.4 * inch, y - 0.08 * inch, w - 0.8 * inch, 0.26 * inch, fill=1, stroke=0)
            c.setFillColor(black)
            c.setFont("Helvetica", 7.5)
            # fabric column color hint
        for j, cell in enumerate(row):
            if i > 0 and j == 2:
                c.setFillColor(PATTERN_BACK_DK if cell == "PATTERN" else HexColor("#5c4a32"))
                c.setFont("Helvetica-Bold", 7.5)
            elif i > 0:
                c.setFillColor(black)
                c.setFont("Helvetica", 7.5)
            c.drawString(col_x[j] * inch, y, str(cell))
        y -= 0.28 * inch

    y -= 0.1 * inch
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 8)
    for n in [
        "Rates on quote: backs $85/sf (PATTERN labor), seats $45/sf (PLAIN labor). Fabric COM TBD — $0 on quote.",
        "Do NOT auto-slice every 24\" into cushion count. Schedule is by run + SF.",
        "No wood ribs, dados, CNC nests, or frame cut list on this set — upholstery on existing shells only.",
        f"U developed outer run {u.developed_outer_lf:.2f} lf is the takeoff (not footprint width {u.footprint_width:.2f}\").",
    ]:
        c.drawString(0.45 * inch, y, "• " + n)
        y -= 0.20 * inch
    finish("Cushion Schedule")

    # ── Materials ──
    _page_header(
        c, w, h,
        "MATERIALS TAKEOFF — FABRIC + 1/2\" PLYWOOD",
        f'Fabric width {mats.fabric_width_in:.0f}" assumed · waste fabric {round((mats.waste_fabric-1)*100)}% · ply waste {round((mats.waste_ply-1)*100)}%',
    )
    # Summary cards
    def card(x, y, title, lines, accent):
        c.setFillColor(white)
        c.setStrokeColor(accent)
        c.setLineWidth(1.5)
        c.roundRect(x, y, 3.3 * inch, 1.55 * inch, 5, fill=1, stroke=1)
        c.setFillColor(accent)
        c.rect(x, y + 1.35 * inch, 3.3 * inch, 0.2 * inch, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(x + 8, y + 1.40 * inch, title)
        c.setFillColor(NAVY)
        c.setFont("Helvetica", 7.5)
        yy = y + 1.15 * inch
        for ln in lines:
            c.drawString(x + 8, yy, ln)
            yy -= 0.16 * inch

    card(
        0.45 * inch, h - 2.85 * inch, "PATTERN FABRIC (BACKS ONLY)",
        [
            f"U-B {u.back_sf:.2f} + L-B {L.back_sf:.2f} = {mats.pattern_back_sf:.2f} sf",
            f"Yards (w/ {round((mats.waste_fabric-1)*100)}% waste): {mats.pattern_yards_raw:.2f} yd",
            f"ORDER QTY: {mats.pattern_yards_order:.2f} yd  @ {mats.fabric_width_in:.0f}\" goods",
            "Do NOT use on seats.",
            "COM / mill / SKU: TBD",
        ],
        PATTERN_BACK_DK,
    )
    card(
        3.95 * inch, h - 2.85 * inch, "PLAIN FABRIC (SEATS ONLY)",
        [
            f"U-S {u.seat_sf:.2f} + L-S {L.seat_sf:.2f} = {mats.plain_seat_sf:.2f} sf",
            f"Yards (w/ {round((mats.waste_fabric-1)*100)}% waste): {mats.plain_yards_raw:.2f} yd",
            f"ORDER QTY: {mats.plain_yards_order:.2f} yd  @ {mats.fabric_width_in:.0f}\" goods",
            "Do NOT use on backs.",
            "COM / mill / SKU: TBD",
        ],
        HexColor("#8a7355"),
    )
    card(
        7.45 * inch, h - 2.85 * inch, '1/2" PLYWOOD',
        [
            f"Backer boards (backs): {mats.ply_back_sf:.2f} sf",
            f"Seat decks (seats): {mats.ply_seat_sf:.2f} sf",
            f"Total face: {mats.ply_total_sf:.2f} sf",
            f"With {round((mats.waste_ply-1)*100)}% waste: {mats.ply_with_waste_sf:.2f} sf",
            f"SHEETS 4×8: {mats.ply_sheets}  (1/2\" ACX/shop)",
        ],
        NAVY,
    )

    # Formulas
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(0.45 * inch, h - 3.15 * inch, "FORMULAS (audit)")
    c.setFont("Helvetica", 7)
    c.setFillColor(GRAY)
    yy = h - 3.35 * inch
    for fml in mats.formulas:
        c.drawString(0.5 * inch, yy, "• " + fml)
        yy -= 0.14 * inch

    # Assumptions box
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(0.45 * inch, yy - 0.08 * inch, "ASSUMPTIONS — Rafael: correct these if shop practice differs")
    yy -= 0.26 * inch
    c.setFont("Helvetica", 6.5)
    c.setFillColor(GRAY)
    for a in mats.assumptions:
        # wrap long lines
        text = "• " + a
        if len(text) > 145:
            c.drawString(0.5 * inch, yy, text[:145])
            yy -= 0.12 * inch
            c.drawString(0.65 * inch, yy, text[145:])
        else:
            c.drawString(0.5 * inch, yy, text)
        yy -= 0.12 * inch

    finish("Materials")

    c.save()
    return {
        "pdf_path": str(out_path),
        "size_bytes": out_path.stat().st_size,
        "sheets": sheets_done,
        "sheet_count": len(sheets_done),
        "product_type": "upholstery_on_shell",
        "true_ul_polyline": True,
        "units": "inches",
        "u": {
            "back_outer": u.back_outer,
            "arm_left": u.arm_left,
            "arm_right": u.arm_right,
            "seat_depth": u.seat_depth,
            "shell_height": u.shell_height,
            "net_back_height": u.net_back_height,
            "seat_foam": u.seat_foam,
            "developed_outer_in": u.developed_outer_in,
            "developed_outer_lf": round(u.developed_outer_lf, 2),
            "footprint_width": u.footprint_width,
            "back_sf": round(u.back_sf, 2),
            "seat_sf": round(u.seat_sf, 2),
        },
        "l": {
            "leg_short": L.leg_short,
            "leg_long": L.leg_long,
            "seat_depth": L.seat_depth,
            "shell_height": L.shell_height,
            "developed_outer_in": L.developed_outer_in,
            "developed_outer_lf": round(L.developed_outer_lf, 2),
            "back_sf": round(L.back_sf, 2),
            "seat_sf": round(L.seat_sf, 2),
            "provisional": L.provisional,
        },
        "materials": {
            "fabric_width_in": mats.fabric_width_in,
            "waste_fabric_pct": round((mats.waste_fabric - 1) * 100),
            "pattern_back_sf": mats.pattern_back_sf,
            "plain_seat_sf": mats.plain_seat_sf,
            "pattern_yards_raw": mats.pattern_yards_raw,
            "plain_yards_raw": mats.plain_yards_raw,
            "pattern_yards_order": mats.pattern_yards_order,
            "plain_yards_order": mats.plain_yards_order,
            "ply_back_sf": mats.ply_back_sf,
            "ply_seat_sf": mats.ply_seat_sf,
            "ply_total_sf": mats.ply_total_sf,
            "ply_with_waste_sf": mats.ply_with_waste_sf,
            "ply_sheets_4x8": mats.ply_sheets,
            "assumptions": mats.assumptions,
            "formulas": mats.formulas,
        },
        "drawing_engine": "drawing.upholstery_shell_renderer",
        "no_24in_autoslice": True,
        "asymmetric_arms": True,
        "has_isometric": True,
        "has_client_mockup": True,
        "has_materials": True,
        "pattern_backs_only": True,
        "plain_seats_only": True,
    }
