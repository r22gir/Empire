"""templates/b2_renderers.py — Phase B2 vector drawing renderer.

HOTFIX B2 (2026-07-24) — replaces the textual "Geometry Preview"
panel with a real scaled line drawing per product family. The
founder live-verified the B1 textual preview as "very poor
result — a data sheet, not a drawing". The vector renderer is
the priority.

HOTFIX B2b (2026-07-24) — coordinate-system fix.

  Pre-fix: the B2 renderer used raw inch values (e.g. 0.5, 7.0)
  for canvas operations, but ReportLab's Canvas default unit is
  POINTS (1/72 inch), not inches. Result: every element was
  drawn at coords 0.5/72 to 7.0/72 — all crammed at the bottom-
  left corner of the page (the founder's "BLANK page with all
  content collapsed" symptom). ReportLab does not auto-convert.

  Post-fix: a single helper `_P(inches)` multiplies the inches
  value by `reportlab.lib.units.inch` (= 72 points) at the call
  site, so every c.rect / c.line / c.drawString / c.circle
  receives points. Constants stay in inches; the conversion is
  applied at the boundary.

Per Empire Drawing Standard v1.0:

  - Required views: drawn from GeometryResult.views (REAL lines,
    not bbox text)
  - Plan view mandatory for non-rectangular footprints
  - Side elevation / section always
  - Title block (right column, every sheet)
  - LAYOUT MATH lines (Rule 3: segments + gaps = overall)
  - NOTES / ASSUMPTIONS — CONFIRM (Rule 1: every inferred value)
  - Dimension strings with WITNESS LINES + extension ticks

Phase B2 scope: Roman Shades family only. The remaining 5
families (drapery, valance, cornice, bench/banquette,
headboard_channel) land in B2 follow-on commits per the rollout
plan in the commit message.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib import colors

if TYPE_CHECKING:
    from app.services.drawing.templates.base import (
        GeometryResult, MathLine, GeometryFamilyResult,
    )


# ── Drawing area (landscape letter) ──────────────────────────────
#   All constants are in INCHES. Every Canvas call uses _P() to
#   convert to points (the Canvas default unit).

PAGE_W_IN = 11.0
PAGE_H_IN = 8.5
DRAWING_X_IN = 0.5
DRAWING_Y_IN = 0.5
DRAWING_W_IN = 6.0
DRAWING_H_IN = 5.5
TITLE_X_IN = 7.0
TITLE_Y_IN = 0.5
TITLE_W_IN = 3.5
TITLE_H_IN = 7.5


def _P(inches: float) -> float:
    """Convert a measurement in inches to the Canvas default unit
    (points). This is the boundary function — every Canvas call in
    this module routes through _P() so coordinate-system errors
    can't creep in."""
    return inches * inch


def _fmt_in(value: float) -> str:
    """Format inches as text. 1/16" granularity per B1 contract.
    NOT a Canvas coord — this is text content."""
    sixteenths = round(value * 16)
    whole = sixteenths // 16
    rem = sixteenths - whole * 16
    if rem == 0:
        return f'{whole}"' if whole else '0"'
    from math import gcd
    g = gcd(rem, 16)
    n = rem // g
    d = 16 // g
    if whole:
        return f'{whole}-{n}/{d}"'
    return f'{n}/{d}"'


def _draw_witness_dimension(
    c: Canvas,
    x1: float, y1: float, x2: float, y2: float,
    label: str, side: str = "below",
    offset_in: float = 0.35,
):
    """Draw a dimension line with witness lines + extension ticks.

    Args:
      c: reportlab canvas
      x1, y1, x2, y2: the two points being dimensioned (in INCHES)
      label: dim text (e.g. '38"')
      side: 'below' / 'above' / 'left' / 'right' — where the
            dimension line is offset
      offset_in: how far the dim line is offset from the witness
                 (in INCHES)

    Per Empire Standard: dim line 0.6pt with end ticks; witness
    lines 0.4pt gray with 0.05" gap from object.
    """
    if x1 == x2:
        # Vertical dimension
        if side == "left":
            offset = -offset_in
        else:
            offset = offset_in
        # Witness lines (extension lines) — small gap (0.05") from object
        c.setStrokeColor(colors.HexColor("#999999"))
        c.setLineWidth(0.4)
        c.line(_P(x1 - 0.05), _P(y1),
               _P(x1 + (0.05 if offset > 0 else -0.05)), _P(y1))
        c.line(_P(x2 - 0.05), _P(y2),
               _P(x2 + (0.05 if offset > 0 else -0.05)), _P(y2))
        # Dim line
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.6)
        c.line(_P(x1 + offset), _P(y1), _P(x2 + offset), _P(y2))
        # End ticks (at 45° cross)
        tick = 0.05
        c.line(_P(x1 + offset - tick), _P(y1 - tick),
               _P(x1 + offset + tick), _P(y1 + tick))
        c.line(_P(x2 + offset - tick), _P(y2 - tick),
               _P(x2 + offset + tick), _P(y2 + tick))
        # Label centered (label is a string, not a coord)
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 9)
        c.drawCentredString(_P(x1 + offset), _P((y1 + y2) / 2), label)
    else:
        # Horizontal dimension
        if side == "above":
            offset = offset_in
        else:
            offset = -offset_in
        # Witness lines
        c.setStrokeColor(colors.HexColor("#999999"))
        c.setLineWidth(0.4)
        c.line(_P(x1), _P(y1 - 0.05),
               _P(x1), _P(y1 + (0.05 if offset > 0 else -0.05)))
        c.line(_P(x2), _P(y2 - 0.05),
               _P(x2), _P(y2 + (0.05 if offset > 0 else -0.05)))
        # Dim line
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.6)
        c.line(_P(x1), _P(y1 + offset), _P(x2), _P(y2 + offset))
        # End ticks
        tick = 0.05
        c.line(_P(x1 - tick), _P(y1 + offset - tick),
               _P(x1 + tick), _P(y1 + offset + tick))
        c.line(_P(x2 - tick), _P(y2 + offset - tick),
               _P(x2 + tick), _P(y2 + offset + tick))
        # Label
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 9)
        c.drawCentredString(_P((x1 + x2) / 2), _P(y1 + offset), label)


def render_roman_shades_vector(
    c: Canvas,
    geometry: "GeometryResult",
    math_lines: list,
    title_block_rows: list,
    family_name: str = "Roman Shades",
    product_type: str = "flat_fold",
    spec: dict = None,
):
    """B2 vector drawing for the Roman Shades family.

    Page layout (landscape letter, in inches):
      +--------------------------------------------------+
      |                                                  |
      |   Front Elevation (6" x 5.5" main view)           |
      |     - Outer shade outline                        |
      |     - Hem bar (heavier bottom line)             |
      |     - Slat lines (horizontal at computed y)     |
      |     - Mounting bar (top)                         |
      |     - Ring markers (austrian / cascade / tulip) |
      |     - Width dim (below, witness lines)           |
      |     - Height dim (right, witness lines)          |
      |                                                  |
      |   Title block (right column, 3.5" wide)          |
      |                                                  |
      +--------------------------------------------------+

    All Canvas ops route through _P() (inches -> points). The
    shape-and-bbox gate (≥40% page-coverage, ≤20% overlap) is
    enforced by the QC helper in tests/test_drawing_vector_b2.py
    — the B2 doctrine says: tests that verify a weaker property
    than the requirement are a defect class.

    The MODEL COORDINATE SPACE for the geometry is inches, with
    origin at the bottom-left of the shade body. The PAGE
    COORDINATE SPACE is inches, with origin at the bottom-left of
    the page (after we _P()-convert to points for the Canvas).
    The transform `X(mx) = dx + (mx - min_x) * scale` is
    dimensionless (multiplying inches by a unitless scale gives
    inches), so the result is still in inches and must be
    _P()-converted at the call site.
    """
    if spec is None:
        spec = {}
    min_x, min_y, max_x, max_y = geometry.bbox
    geo_w = max_x - min_x
    geo_h = max_y - min_y
    if geo_w <= 0 or geo_h <= 0:
        return
    inner_margin = 0.4
    draw_w = DRAWING_W_IN - 2 * inner_margin
    draw_h = DRAWING_H_IN - 2 * inner_margin
    scale = min(draw_w / geo_w, draw_h / geo_h)
    scaled_w = geo_w * scale
    scaled_h = geo_h * scale
    dx = DRAWING_X_IN + inner_margin + (draw_w - scaled_w) / 2
    dy = DRAWING_Y_IN + inner_margin + (draw_h - scaled_h) / 2

    def X(mx: float) -> float:
        return dx + (mx - min_x) * scale

    def Y(my: float) -> float:
        return dy + (my - min_y) * scale

    # ── View header (top of drawing area) ──────────────────────
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.black)
    c.drawString(
        _P(DRAWING_X_IN + 0.05),
        _P(DRAWING_Y_IN + DRAWING_H_IN - 0.15),
        f"FRONT ELEVATION — {product_type.replace('_', ' ').title()}",
    )

    # ── Mounting bar (top, slightly thicker line) ──────────────
    c.setStrokeColor(colors.black)
    c.setLineWidth(2.0)
    c.line(_P(X(0)), _P(Y(geo_h + 0.05)),
           _P(X(geo_w)), _P(Y(geo_h + 0.05)))
    c.setLineWidth(0.4)
    c.setFillColor(colors.HexColor("#d0d0d0"))
    c.rect(
        _P(X(0)), _P(Y(geo_h)),
        _P(X(geo_w) - X(0)),
        _P(Y(geo_h + 0.08) - Y(geo_h)),
        stroke=0, fill=1,
    )

    # ── Shade body outline ─────────────────────────────────────
    c.setStrokeColor(colors.black)
    c.setLineWidth(1.5)
    c.setFillColor(colors.HexColor("#f5f0e6"))
    c.rect(
        _P(X(0)), _P(Y(0)),
        _P(X(geo_w) - X(0)),
        _P(Y(geo_h) - Y(0)),
        stroke=1, fill=1,
    )

    # ── Slat lines (horizontal at each slat seam) ─────────────
    c.setStrokeColor(colors.HexColor("#555555"))
    c.setLineWidth(0.5)
    slat_ys: list[float] = []
    for edge in geometry.edges:
        if edge.weight == "channel" and edge.frm.startswith("slat_"):
            for p in geometry.points:
                if p.name == edge.frm:
                    slat_ys.append(p.y)
                    break
    for y in sorted(set(slat_ys)):
        c.line(_P(X(0)), _P(Y(y)), _P(X(geo_w)), _P(Y(y)))

    # ── Hem bar (bottom, slightly thicker) ───────────────────
    c.setStrokeColor(colors.black)
    c.setLineWidth(2.0)
    c.line(_P(X(0)), _P(Y(-0.05)),
           _P(X(geo_w)), _P(Y(-0.05)))
    c.setFillColor(colors.HexColor("#a08060"))
    c.setLineWidth(0.4)
    c.rect(
        _P(X(0)), _P(Y(-0.12)),
        _P(X(geo_w) - X(0)),
        _P(Y(0) - Y(-0.12)),
        stroke=1, fill=1,
    )

    # ── Ring markers (austrian / cascade / tulip / london) ────
    c.setFillColor(colors.HexColor("#8b6914"))
    c.setStrokeColor(colors.HexColor("#8b6914"))
    c.setLineWidth(0.6)
    for point in geometry.points:
        if point.name.startswith("ring_"):
            cx, cy = X(point.x), Y(point.y)
            c.circle(_P(cx), _P(cy), _P(0.04), stroke=1, fill=1)

    # ── Width dimension (below the shade) ────────────────────
    _draw_witness_dimension(
        c,
        X(0), Y(0), X(geo_w), Y(0),
        label=_fmt_in(geo_w),
        side="below",
        offset_in=0.45,
    )

    # ── Height dimension (right of the shade) ─────────────────
    _draw_witness_dimension(
        c,
        X(geo_w), Y(0), X(geo_w), Y(geo_h),
        label=_fmt_in(geo_h),
        side="right",
        offset_in=0.35,
    )

    # ── Title block (right column) ─────────────────────────────
    _draw_title_block(c, family_name, product_type, title_block_rows, spec)

    # ── LAYOUT MATH block (bottom-left) ──────────────────────
    _draw_layout_math(c, math_lines)


def _draw_title_block(
    c: Canvas, family: str, product_type: str,
    rows: list, spec: dict,
):
    """Standard right-column title block.

    Header rows in a fixed order so the founder can scan the sheet
    fast. HOTFIX B2 (1) fixes the address/phone column collision by
    splitting the contact-info row into three separate rows. This
    keeps column widths sane and matches how an architect's title
    block is typically laid out.

    HOTFIX B2 (2): the CLIENT row only renders when an explicit
    client_name was supplied. drawing_handoff.subject is the
    parsed ITEM TYPE, NOT a real client name; the chat router
    should not pass it through as the client.
    """
    x = TITLE_X_IN
    y_top = TITLE_Y_IN + TITLE_H_IN
    # Header band (dark) — solid filled rect. Spans y=[y_top-0.5, y_top].
    c.setFillColor(colors.HexColor("#1a1a1a"))
    c.rect(_P(x), _P(y_top - 0.5), _P(TITLE_W_IN), _P(0.5),
           stroke=0, fill=1)
    # EMPIRE (centered vertically in the band, y_top - 0.18)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(_P(x + 0.1), _P(y_top - 0.18), "EMPIRE WORKROOM")
    # CUSTOM (BELOW the band, not inside it; y_top - 0.65 → 7.35).
    c.setFont("Helvetica", 9)
    c.drawString(_P(x + 0.1), _P(y_top - 0.65),
                "CUSTOM UPHOLSTERY & FABRICATION")

    # Subheader: 3 separate rows (address, phone, email). Start at
    # y=7.10 (below the CUSTOM line at 7.35) with 0.18" spacing.
    y = y_top - 1.0  # 7.0
    c.setFillColor(colors.HexColor("#444444"))
    c.setFont("Helvetica", 9)
    sub_rows = [
        "5124 Frolich Ln, Hyattsville, MD 20781",
        "(703) 213-6484",
        "workroom@empirebox.store",
    ]
    for sub in sub_rows:
        c.drawString(_P(x + 0.1), _P(y), sub)
        y -= 0.18

    # Body rows
    y -= 0.12
    c.setFillColor(colors.black)
    body = [("FAMILY", family),
            ("PRODUCT TYPE", product_type.replace("_", " ").title())]
    for k, v in body:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(_P(x + 0.1), _P(y), k + ":")
        c.setFont("Helvetica", 9)
        c.drawString(_P(x + 1.4), _P(y), v)
        y -= 0.22
    seen = {"FAMILY", "PRODUCT TYPE"}
    for k, v in (rows or {}).items():
        if k.upper() in seen:
            continue
        c.setFont("Helvetica-Bold", 9)
        c.drawString(_P(x + 0.1), _P(y), k.upper() + ":")
        c.setFont("Helvetica", 9)
        c.drawString(_P(x + 1.4), _P(y), str(v))
        y -= 0.22
        seen.add(k.upper())

    # CLIENT row — ONLY when an explicit client was named.
    client = (spec or {}).get("client_name", "").strip()
    if client:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(_P(x + 0.1), _P(y), "CLIENT:")
        c.setFont("Helvetica", 9)
        c.drawString(_P(x + 1.4), _P(y), client)
        y -= 0.22

    # SHEET, STATUS
    c.setFont("Helvetica-Bold", 9)
    c.drawString(_P(x + 0.1), _P(y), "SHEET:")
    c.setFont("Helvetica", 9)
    c.drawString(_P(x + 1.4), _P(y), "1 of 1 (B2 vector)")
    y -= 0.22
    c.setFont("Helvetica-Bold", 9)
    c.drawString(_P(x + 0.1), _P(y), "STATUS:")
    c.setFont("Helvetica", 9)
    c.drawString(_P(x + 1.4), _P(y), "FOR FOUNDER REVIEW")
    y -= 0.22

    # Optional rows — render ONLY when the value is non-empty
    optional_rows = [
        ("SITE",     (spec or {}).get("site_address", "")),
        ("MATERIAL", (spec or {}).get("material", "")),
        ("DATE",     (spec or {}).get("date", "")),
    ]
    for label, val in optional_rows:
        if not val or not str(val).strip():
            continue
        c.setFont("Helvetica-Bold", 9)
        c.drawString(_P(x + 0.1), _P(y), label + ":")
        c.setFont("Helvetica", 9)
        c.drawString(_P(x + 1.4), _P(y), str(val))
        y -= 0.22

    c.setFont("Helvetica-Bold", 9)
    c.drawString(_P(x + 0.1), _P(y), "DRAWN BY:")
    c.setFont("Helvetica", 9)
    c.drawString(_P(x + 1.4), _P(y), "Empire Drafting Studio (B2)")
    y -= 0.22


def _draw_layout_math(c: Canvas, math_lines: list):
    """Closure block in monospace, top-left below the drawing area."""
    if not math_lines:
        return
    x = DRAWING_X_IN + 0.1
    y = DRAWING_Y_IN + 0.6
    c.setFont("Helvetica-Bold", 9)
    c.drawString(_P(x), _P(y), "LAYOUT MATH (Rule 3 — segments + gaps = overall):")
    y -= 0.18
    c.setFont("Courier", 8.5)
    for ml in math_lines:
        seg = " + ".join(f'{n} × {_fmt_in(v)}' for n, v in ml.segments) or "—"
        gap = " + ".join(f'{n} × {_fmt_in(v)}' for n, v in ml.gaps) or "—"
        total = seg + (f' + {gap}' if ml.gaps else '')
        warn = "" if ml.closing_tolerance_in < (1 / 64) else "  ⚠  "
        line = f"{warn}{total}  =  {_fmt_in(ml.total)}  (target {_fmt_in(ml.target_in)})"
        c.drawString(_P(x), _P(y), line)
        y -= 0.16
        if ml.note:
            c.setFont("Helvetica-Oblique", 7.5)
            c.drawString(_P(x), _P(y), "  " + ml.note)
            c.setFont("Courier", 8.5)
            y -= 0.16
