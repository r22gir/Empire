"""Upholstery-on-existing-shell banquette sheets (U / L).

Acceptance target: Marleys_EST-2026-272_UPHOLSTERY_CORRECT.pdf
(Empire Workroom gold preview — 4 sheets).

This is NOT the millwork/CNC bench_renderer. No wood frame, ribs,
dados, or 24" auto-slice cushion heroes. Plan = shell outline + seat
cushion footprint; elevation = shell height vs net back on 2" foam;
schedule = run + SF.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, black, white

NAVY = HexColor("#1a365d")
GOLD = HexColor("#b8860b")
GRAY = HexColor("#4a5568")
SHELL = HexColor("#2c5282")
CUSH = HexColor("#c05621")
PROV = HexColor("#c53030")
LT_BLUE = HexColor("#ebf4ff")
LT_PEACH = HexColor("#feebc8")
LT_FOAM = HexColor("#fbd38d")


@dataclass
class UShellSpec:
    """U banquette upholstery-on-shell dims — ALL INCHES."""
    back_outer: float = 249.75
    arm_left: float = 41.25       # wing LENGTH along room (not thickness)
    arm_right: float = 52.0       # wing LENGTH — asymmetric, do NOT max()
    seat_depth: float = 16.25     # cushion depth / wing THICKNESS
    shell_height: float = 30.25
    net_back_height: float = 26.75  # sits ON seat foam; = shell - 3.5 board stack
    seat_foam: float = 2.0
    board_stack: float = 3.5      # plywood+foam+Dacron deducted from shell → net back

    @property
    def developed_outer_in(self) -> float:
        """Developed outer run for upholstery takeoff (not footprint width)."""
        return self.back_outer + self.arm_left + self.arm_right

    @property
    def developed_outer_lf(self) -> float:
        return self.developed_outer_in / 12.0

    @property
    def footprint_width(self) -> float:
        """Booth plan footprint = back + 2*seat_depth (wing thickness each side)."""
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
    seat_depth: float = 19.0       # provisional
    shell_height: float = 30.0     # provisional
    seat_height: float = 18.0      # provisional AFF
    net_back_height: float = 0.0   # if 0 → shell_height - seat foam stack approx
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
        # provisional: shell - seat AFF is NOT correct for upholstery;
        # use shell - 3.5 like U when no explicit net given, flagged provisional
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
        "Existing shells on site. Draw cushion footprint + shell outline only — not wood frame."
    )
    client: str = "Dave Romero / Marley's Hyattsville"


def _title_block(c, w, h, sheet, sheet_title, meta: SheetMeta):
    c.setStrokeColor(NAVY)
    c.setLineWidth(1.5)
    c.rect(0.4 * inch, 0.35 * inch, w - 0.8 * inch, 0.95 * inch)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(0.55 * inch, 1.05 * inch, "EMPIRE WORKROOM  |  MAX")
    c.setFont("Helvetica", 8)
    c.setFillColor(GRAY)
    c.drawString(0.55 * inch, 0.85 * inch, meta.job)
    c.drawString(0.55 * inch, 0.68 * inch, meta.note)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(w - 0.55 * inch, 1.05 * inch, meta.quote_num)
    c.setFont("Helvetica", 8)
    c.setFillColor(GRAY)
    c.drawRightString(w - 0.55 * inch, 0.85 * inch, sheet_title)
    c.drawRightString(w - 0.55 * inch, 0.68 * inch, sheet)
    c.setFillColor(GOLD)
    c.rect(0.4 * inch, 0.35 * inch, 0.12 * inch, 0.95 * inch, fill=1, stroke=0)


def _page_header(c, w, h, title):
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(0.5 * inch, h - 0.45 * inch, title)
    c.setStrokeColor(GOLD)
    c.setLineWidth(2)
    c.line(0.5 * inch, h - 0.55 * inch, w - 0.5 * inch, h - 0.55 * inch)


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


def _draw_u_plan(c, ox, oy, scale, u: UShellSpec):
    """Asymmetric U plan. Opening toward bottom. Arms are LENGTHS not max()'d."""
    s = scale
    W, AL, AR, D = u.back_outer, u.arm_left, u.arm_right, u.seat_depth

    def sx(x):
        return ox + x * s

    def sy(y_from_back):
        return oy - y_from_back * s

    # Fill shell band
    c.setFillColor(LT_BLUE)
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

    # Outer shell stroke
    c.setStrokeColor(SHELL)
    c.setLineWidth(1.8)
    c.line(sx(0), sy(AL), sx(0), sy(0))
    c.line(sx(0), sy(0), sx(W), sy(0))
    c.line(sx(W), sy(0), sx(W), sy(AR))

    # Seat cushion footprint (dashed)
    c.setStrokeColor(CUSH)
    c.setLineWidth(1.2)
    c.setDash(4, 3)
    c.line(sx(D), sy(AL), sx(D), sy(D))
    c.line(sx(D), sy(D), sx(W - D), sy(D))
    c.line(sx(W - D), sy(D), sx(W - D), sy(AR))
    c.setDash()

    # Front lips
    c.setStrokeColor(GRAY)
    c.setDash(2, 2)
    c.line(sx(0), sy(AL), sx(D), sy(AL))
    c.line(sx(W - D), sy(AR), sx(W), sy(AR))
    c.setDash()

    # Dims — BOTH arms, never collapse to max
    _dim_h(c, sx(0), sx(W), sy(0) + 14, f'{W:.2f}" back outer')
    _dim_v(c, sx(0) - 14, sy(0), sy(AL), f'{AL:.2f}" L arm')
    _dim_v(c, sx(W) + 14, sy(0), sy(AR), f'{AR:.2f}" R arm')
    _dim_h(c, sx(0), sx(D), sy(D) - 12, f'{D:.2f}" seat', CUSH)

    # Labels
    c.setFillColor(SHELL)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(sx(W / 2), sy(D / 2) - 4, "SHELL / WALL")
    c.setFillColor(CUSH)
    c.drawCentredString(sx(W / 2), sy(min(AL, AR) * 0.55 + D), "SEAT CUSHION FOOTPRINT")
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 7)
    c.drawString(sx(D) + 4, sy(AL) - 10, "miter @ corners")

    # Developed run callout (upholstery takeoff — NOT footprint 282")
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9)
    run_txt = (
        f'Developed outer run (upholstery): {u.developed_outer_in:.2f}" = '
        f'{u.developed_outer_lf:.2f} lf   '
        f'(back {W:.2f} + L {AL:.2f} + R {AR:.2f})'
    )
    c.drawString(sx(0), sy(max(AL, AR)) - 28, run_txt)
    c.setFont("Helvetica", 7)
    c.setFillColor(GRAY)
    c.drawString(
        sx(0), sy(max(AL, AR)) - 40,
        f'Booth footprint width (plan): {u.footprint_width:.2f}" = back + 2×seat_depth — NOT the lf takeoff.',
    )


def _draw_u_elev(c, ox, oy, scale_h, width_pts, u: UShellSpec):
    """Shell silhouette vs net back ON 2\" foam — not seat_h+back_h wood stack."""
    s = scale_h
    H = u.shell_height * s
    NET = u.net_back_height * s
    FOAM = u.seat_foam * s

    # Shell
    c.setFillColor(LT_BLUE)
    c.setStrokeColor(SHELL)
    c.setLineWidth(1.5)
    c.rect(ox, oy, width_pts, H, fill=1, stroke=1)

    # Net back upholstery (sits on seat)
    c.setFillColor(LT_PEACH)
    c.setStrokeColor(CUSH)
    c.rect(ox + 2, oy + FOAM, width_pts - 4, NET, fill=1, stroke=1)

    # Seat foam band
    c.setFillColor(LT_FOAM)
    c.rect(ox + 8, oy, width_pts - 16, FOAM, fill=1, stroke=1)

    _dim_v(c, ox - 12, oy, oy + H, f'{u.shell_height:.2f}" shell')
    _dim_v(c, ox + width_pts + 12, oy + FOAM, oy + FOAM + NET, f'{u.net_back_height:.2f}" net back')

    c.setFillColor(GRAY)
    c.setFont("Helvetica", 7)
    c.drawString(ox + 10, oy + FOAM / 2 - 3, f'{u.seat_foam:.1f}" foam + Dacron (seat)')
    c.drawString(
        ox + 10, oy + FOAM + NET - 12,
        f'{u.board_stack:.1f}" board/foam/Dacron deducted → net back (sits ON seat)',
    )
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(ox + 10, oy + H + 8, "UPHOLSTERY ON EXISTING SHELL — not a wood frame section")


def _draw_l_plan(c, ox, oy, scale, L: LShellSpec):
    s = scale
    A, B, D = L.leg_short, L.leg_long, L.seat_depth

    def sx(x):
        return ox + x * s

    def sy(y):
        return oy - y * s

    # Outer L polygon: long along +x, short along +y from corner
    outer = [(0, 0), (B, 0), (B, D), (D, D), (D, A), (0, A)]
    c.setFillColor(LT_BLUE)
    c.setStrokeColor(SHELL)
    c.setLineWidth(1.8)
    path = c.beginPath()
    path.moveTo(sx(0), sy(0))
    for p in outer[1:]:
        path.lineTo(sx(p[0]), sy(p[1]))
    path.close()
    c.drawPath(path, fill=1, stroke=1)

    # Seat footprint dashed
    c.setStrokeColor(CUSH)
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


def render_upholstery_shell_pdf(
    *,
    out_path: str | Path,
    u: Optional[UShellSpec] = None,
    L: Optional[LShellSpec] = None,
    meta: Optional[SheetMeta] = None,
    include_u: bool = True,
    include_l: bool = True,
) -> dict:
    """Write 4-sheet (or fewer) upholstery-on-shell PDF. Returns summary dict."""
    u = u or UShellSpec()
    L = L or LShellSpec()
    meta = meta or SheetMeta()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(out_path), pagesize=landscape(letter))
    w, h = landscape(letter)
    sheets = []

    if include_u:
        # Sheet 1 — U Plan
        _page_header(c, w, h, "U BANQUETTE — PLAN (upholstery on existing shell)")
        scale = (9.0 * inch) / u.back_outer
        _draw_u_plan(c, 0.9 * inch, h - 1.1 * inch, scale, u)
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 8)
        c.drawString(
            0.5 * inch, 1.55 * inch,
            "Blue = shell/wall outline. Orange dashed = seat cushion footprint. "
            "Opening toward bottom. Units: inches. BOTH arms drawn (asymmetric).",
        )
        _title_block(c, w, h, "Sheet 1 of 4", "U Plan", meta)
        c.showPage()
        sheets.append("U Plan")

        # Sheet 2 — U Elevation
        _page_header(c, w, h, "U BANQUETTE — ELEVATION (height stack)")
        _draw_u_elev(c, 1.2 * inch, 2.2 * inch, 8.5, 8 * inch, u)
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 8)
        c.drawString(
            0.5 * inch, 1.55 * inch,
            "Shows shell height vs finished net back ON seat foam. Not a frame section. "
            f"Net back {u.net_back_height}\" = shell {u.shell_height}\" − {u.board_stack}\" board stack.",
        )
        _title_block(c, w, h, "Sheet 2 of 4", "U Elevation", meta)
        c.showPage()
        sheets.append("U Elevation")

    if include_l:
        # Sheet 3 — L Plan
        _page_header(c, w, h, "L BANQUETTE — PLAN (provisional depth/height)")
        scale_l = (7.5 * inch) / L.leg_long
        _draw_l_plan(c, 1.2 * inch, h - 1.2 * inch, scale_l, L)
        c.setFillColor(PROV)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(
            0.5 * inch, 1.55 * inch,
            f'PROVISIONAL: L depth {L.seat_depth}" / height {L.shell_height}" / seat {L.seat_height}" — lock to U before fab.',
        )
        _title_block(c, w, h, "Sheet 3 of 4", "L Plan", meta)
        c.showPage()
        sheets.append("L Plan")

    # Sheet 4 — Cushion schedule by run + SF (never 24" auto-slice hero)
    _page_header(c, w, h, f"CUSHION SCHEDULE — {meta.quote_num}")
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 10)
    rows = [
        ("Mark", "Location", "Run (in)", "Height/Depth", "SF (quote)", "Notes"),
        (
            "U-B", "U pattern backs",
            f'{u.developed_outer_in:.2f}" outer (= {u.developed_outer_lf:.2f} lf)',
            f'{u.net_back_height:.2f}" net',
            f"{u.back_sf:.2f}",
            "Arms included in developed outer run",
        ),
        (
            "U-S", "U seat cushions",
            f'{u.developed_outer_lf:.2f} lf seat run',
            f'{u.seat_depth:.2f}" × {u.seat_foam:.1f}" foam',
            f"{u.seat_sf:.2f}",
            "Split for sew/handle as shop decides",
        ),
        (
            "L-B", "L pattern backs",
            f'{L.leg_short:.3f}" + {L.leg_long:.3f}" (= {L.developed_outer_lf:.2f} lf)',
            f'{L.shell_height:.1f}" prov.',
            f"{L.back_sf:.2f}",
            "Lock height to U",
        ),
        (
            "L-S", "L seat cushions",
            f'{L.developed_outer_lf:.2f} lf',
            f'{L.seat_depth:.1f}" prov.',
            f"{L.seat_sf:.2f}",
            "Lock depth to U",
        ),
    ]
    y = h - 1.0 * inch
    col_x = [0.5, 1.2, 3.2, 6.0, 7.4, 8.3]
    for i, row in enumerate(rows):
        c.setFont("Helvetica-Bold" if i == 0 else "Helvetica", 7 if i else 8)
        c.setFillColor(NAVY if i == 0 else black)
        for j, cell in enumerate(row):
            c.drawString(col_x[j] * inch, y, str(cell))
        y -= 0.28 * inch
        if i == 0:
            c.setStrokeColor(GOLD)
            c.line(0.5 * inch, y + 0.12 * inch, w - 0.5 * inch, y + 0.12 * inch)

    c.setFillColor(GRAY)
    c.setFont("Helvetica", 8)
    y -= 0.15 * inch
    for n in [
        "Rates locked on quote: backs $85/sf, seats $45/sf. Fabric COM/Nelma TBD — $0 on quote.",
        "Do NOT auto-slice every 24\" into cushion count on the drawing. Schedule is by run + SF.",
        "No wood ribs, dados, CNC nests, or frame cut list on this set.",
        "Upholstery on existing shells. Developed outer run is the lf takeoff (U≈28.58 lf), not footprint width.",
    ]:
        c.drawString(0.5 * inch, y, "• " + n)
        y -= 0.22 * inch
    _title_block(c, w, h, "Sheet 4 of 4", "Cushion Schedule", meta)
    c.showPage()
    sheets.append("Cushion Schedule")

    c.save()
    return {
        "pdf_path": str(out_path),
        "size_bytes": out_path.stat().st_size,
        "sheets": sheets,
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
        "drawing_engine": "drawing.upholstery_shell_renderer",
        "no_24in_autoslice": True,
        "asymmetric_arms": True,
    }
