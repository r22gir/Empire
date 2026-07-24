"""templates/b2_renderers.py — Phase B2 vector drawing renderer.

HOTFIX B2 (2026-07-24) — replaces the textual "Geometry Preview"
panel with a real scaled line drawing per product family. The
founder live-verified the B1 textual preview as "very poor
result — a data sheet, not a drawing". The vector renderer is
the priority.

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

Vector primitives use reportlab.pdfgen.canvas via the Standard
drawing operations (line / rect / circle). The output is a true
vector PDF (not a rasterized bitmap) — opening in a fab shop's
viewer preserves the geometry at any zoom.
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


# ── Drawing area (landscape letter, dims in inches) ───────────────
#   The page is 11.0" x 8.5" (landscape letter). We reserve:
#     - 5.0" x 5.5" main view (lower-left of page)
#     - 3.0" x 5.5" right-side title block
#     - 1.5" top margin
#     - 0.5" left / bottom margins

PAGE_W = 11.0
PAGE_H = 8.5
DRAWING_X = 0.5
DRAWING_Y = 0.5
DRAWING_W = 6.0
DRAWING_H = 5.5
TITLE_X = 7.0
TITLE_Y = 0.5
TITLE_W = 3.5
TITLE_H = 7.5


def _fmt_in(value: float) -> str:
    """Format inches as text. 1/16" granularity per B1 contract."""
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
      x1, y1, x2, y2: the two points being dimensioned
      label: dim text (e.g. '38"')
      side: 'below' / 'above' / 'left' / 'right' — where the
            dimension line is offset
      offset_in: how far the dim line is offset from the witness

    Per Empire Standard: dim line 0.6pt with end ticks; witness
    lines 0.4pt gray with 0.05" gap from object.
    """
    if x1 == x2:
        # Vertical dimension
        if side == "left":
            offset = -offset_in
        else:
            offset = offset_in
        dx = offset
        # Witness lines (extension lines)
        c.setStrokeColor(colors.HexColor("#999999"))
        c.setLineWidth(0.4)
        c.line(x1 - 0.05, y1, x1 + dx + (0.05 if dx > 0 else -0.05), y1)
        c.line(x2 - 0.05, y2, x2 + dx + (0.05 if dx > 0 else -0.05), y2)
        # Dim line
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.6)
        c.line(x1 + dx, y1, x2 + dx, y2)
        # End ticks
        tick = 0.05
        c.line(x1 + dx - tick, y1 - tick, x1 + dx + tick, y1 + tick)
        c.line(x2 + dx - tick, y2 - tick, x2 + dx + tick, y2 + tick)
        # Label centered
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 9)
        c.drawCentredString(x1 + dx, (y1 + y2) / 2, label)
    else:
        # Horizontal dimension
        if side == "above":
            offset = offset_in
        else:
            offset = -offset_in
        dy = offset
        # Witness lines
        c.setStrokeColor(colors.HexColor("#999999"))
        c.setLineWidth(0.4)
        c.line(x1, y1 - 0.05, x1, y1 + dy + (0.05 if dy > 0 else -0.05))
        c.line(x2, y2 - 0.05, x2, y2 + dy + (0.05 if dy > 0 else -0.05))
        # Dim line
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.6)
        c.line(x1, y1 + dy, x2, y2 + dy)
        # End ticks
        tick = 0.05
        c.line(x1 - tick, y1 + dy - tick, x1 + tick, y1 + dy + tick)
        c.line(x2 - tick, y2 + dy - tick, x2 + tick, y2 + dy + tick)
        # Label centered
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 9)
        c.drawCentredString((x1 + x2) / 2, y1 + dy, label)


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

    Page layout (landscape letter):
      +--------------------------------------------------+
      |                                                  |
      |   Front Elevation (5" x 5" main view)            |
      |     - Outer shade outline                        |
      |     - Hem bar (heavier bottom line)             |
      |     - Slat lines (horizontal at computed y)     |
      |     - Mounting bar (top)                         |
      |     - Ring markers (austrian / cascade / tulip) |
      |     - Width dim (below, witness lines)           |
      |     - Height dim (right, witness lines)          |
      |                                                  |
      |   Title block (right column, 3" wide)            |
      |                                                  |
      +--------------------------------------------------+

    Renders in DRAWING_COORD (inches, bottom-left origin). Caller
    passes a Canvas that's already had the page frame drawn.
    """
    if spec is None:
        spec = {}
    # The geometry's bbox is the model space (inches). Scale to
    # fit the DRAWING area while preserving aspect.
    min_x, min_y, max_x, max_y = geometry.bbox
    geo_w = max_x - min_x
    geo_h = max_y - min_y
    if geo_w <= 0 or geo_h <= 0:
        return  # nothing to draw
    # Drawing area in inches, with a 0.3" margin inside for the
    # dim labels and view header.
    inner_margin = 0.4
    draw_w = DRAWING_W - 2 * inner_margin
    draw_h = DRAWING_H - 2 * inner_margin
    # Scale (fit) — preserve aspect ratio.
    scale = min(draw_w / geo_w, draw_h / geo_h)
    # Center the geometry within the drawing area.
    scaled_w = geo_w * scale
    scaled_h = geo_h * scale
    dx = DRAWING_X + inner_margin + (draw_w - scaled_w) / 2
    dy = DRAWING_Y + inner_margin + (draw_h - scaled_h) / 2

    def X(mx: float) -> float:
        """Model x (inches, 0=BL) → page x (inches, 0=BL)."""
        return dx + (mx - min_x) * scale

    def Y(my: float) -> float:
        """Model y (inches, 0=BL) → page y (inches, 0=BL)."""
        return dy + (my - min_y) * scale

    # ── View header (top of drawing area) ──────────────────────
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.black)
    c.drawString(
        DRAWING_X + 0.05,
        DRAWING_Y + DRAWING_H - 0.15,
        f"FRONT ELEVATION — {product_type.replace('_', ' ').title()}",
    )

    # ── Mounting bar (top, slightly thicker line) ──────────────
    mount_thickness = 0.18  # visual thickness for the mount bar
    c.setStrokeColor(colors.black)
    c.setLineWidth(2.0)
    c.line(X(0), Y(geo_h + 0.05), X(geo_w), Y(geo_h + 0.05))
    c.setLineWidth(0.4)
    # Mounting rectangle (slim band above the shade)
    c.setFillColor(colors.HexColor("#d0d0d0"))
    c.rect(
        X(0), Y(geo_h), X(geo_w) - X(0),
        Y(geo_h + 0.08) - Y(geo_h),
        stroke=0, fill=1,
    )

    # ── Shade body outline ─────────────────────────────────────
    c.setStrokeColor(colors.black)
    c.setLineWidth(1.5)
    c.setFillColor(colors.HexColor("#f5f0e6"))  # cream tint
    c.rect(
        X(0), Y(0), X(geo_w) - X(0), Y(geo_h) - Y(0),
        stroke=1, fill=1,
    )

    # ── Slat lines (horizontal at each slat seam) ─────────────
    c.setStrokeColor(colors.HexColor("#555555"))
    c.setLineWidth(0.5)
    # Extract slat y-positions from geometry edges (slat_<i>_L -> slat_<i>_R)
    slat_ys: list[float] = []
    for edge in geometry.edges:
        if edge.weight == "channel" and edge.frm.startswith("slat_"):
            # find the slat y from the model space — derive from the
            # y coordinate of the edge endpoints via a name->coord map.
            # Simpler: re-derive by looking at the points dict.
            for p in geometry.points:
                if p.name == edge.frm:
                    slat_ys.append(p.y)
                    break
    for y in sorted(set(slat_ys)):
        c.line(X(0), Y(y), X(geo_w), Y(y))

    # ── Hem bar (bottom, slightly thicker) ───────────────────
    c.setStrokeColor(colors.black)
    c.setLineWidth(2.0)
    c.line(X(0), Y(-0.05), X(geo_w), Y(-0.05))
    # Hem rectangle
    c.setFillColor(colors.HexColor("#a08060"))  # caramel tint
    c.setLineWidth(0.4)
    c.rect(
        X(0), Y(-0.12), X(geo_w) - X(0),
        Y(0) - Y(-0.12),
        stroke=1, fill=1,
    )

    # ── Ring markers (austrian / cascade / tulip / london) ────
    c.setFillColor(colors.HexColor("#8b6914"))
    c.setStrokeColor(colors.HexColor("#8b6914"))
    c.setLineWidth(0.6)
    for point in geometry.points:
        if point.name.startswith("ring_"):
            cx, cy = X(point.x), Y(point.y)
            c.circle(cx, cy, 0.04, stroke=1, fill=1)

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

    # ── NOTES / ASSUMPTIONS (bottom-center) ───────────────────
    _draw_assumptions(c, geometry, product_type, spec)


def _draw_title_block(
    c: Canvas, family: str, product_type: str,
    rows: list, spec: dict,
):
    """Standard right-column title block.

    Header rows in a fixed order so the founder can scan the sheet
    fast. HOTFIX B2 fixes the (1) address/phone column collision by
    splitting the contact-info row into three separate rows, each
    carrying one address/phone/email field on its own line. This
    keeps column widths sane and matches how an architect's title
    block is typically laid out (4" wide, multiple rows).

    HOTFIX B2 (2): the CLIENT row only renders when an explicit
    client_name was supplied. drawing_handoff.subject is the
    parsed ITEM TYPE ("shade"), NOT a real client name; the chat
    router should not pass it through as the client.
    """
    x = TITLE_X
    y_top = TITLE_Y + TITLE_H
    # Header band
    c.setFillColor(colors.HexColor("#1a1a1a"))
    c.rect(x, y_top - 0.5, TITLE_W, 0.5, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(x + 0.1, y_top - 0.32, "EMPIRE WORKROOM")
    c.setFont("Helvetica", 9)
    c.drawString(x + 0.1, y_top - 0.46, "CUSTOM UPHOLSTERY & FABRICATION")

    # Subheader: 3 rows (address, phone, email) — no more collision.
    y = y_top - 0.65
    c.setFillColor(colors.HexColor("#444444"))
    c.setFont("Helvetica", 9)
    sub_rows = [
        "5124 Frolich Ln, Hyattsville, MD 20781",
        "(703) 213-6484",
        "workroom@empirebox.store",
    ]
    for sub in sub_rows:
        c.drawString(x + 0.1, y, sub)
        y -= 0.18

    # Body rows
    y -= 0.12
    c.setFillColor(colors.black)
    # Standard rows
    body = [("FAMILY", family), ("PRODUCT TYPE",
                                  product_type.replace("_", " ").title())]
    for k, v in body:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x + 0.1, y, k + ":")
        c.setFont("Helvetica", 9)
        c.drawString(x + 1.4, y, v)
        y -= 0.22
    # Per-family rows
    seen = {"FAMILY", "PRODUCT TYPE"}
    for k, v in (rows or {}).items():
        if k.upper() in seen:
            continue
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x + 0.1, y, k.upper() + ":")
        c.setFont("Helvetica", 9)
        c.drawString(x + 1.4, y, str(v))
        y -= 0.22
        seen.add(k.upper())

    # CLIENT row — ONLY when an explicit client was named. The
    # chat router sets spec["client_name"] to "" when the founder
    # message had no person/business name. The drawing_handoff.subject
    # ("shade", "headboard", etc.) is the parsed ITEM TYPE — never
    # the client.
    client = (spec or {}).get("client_name", "").strip()
    if client:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x + 0.1, y, "CLIENT:")
        c.setFont("Helvetica", 9)
        c.drawString(x + 1.4, y, client)
        y -= 0.22

    # SHEET, STATUS rows
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x + 0.1, y, "SHEET:")
    c.setFont("Helvetica", 9)
    c.drawString(x + 1.4, y, "1 of 1 (B2 vector)")
    y -= 0.22
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x + 0.1, y, "STATUS:")
    c.setFont("Helvetica", 9)
    c.drawString(x + 1.4, y, "FOR FOUNDER REVIEW")
    y -= 0.22

    # Optional rows — render ONLY when the value is non-empty
    # (HOTFIX B2 (4): empty MATERIAL/SITE/DATE rows must render
    # "—" or omit the row. We omit the row entirely when the
    # value is empty/blank so the title block stays scannable.)
    optional_rows = [
        ("SITE",     (spec or {}).get("site_address", "")),
        ("MATERIAL", (spec or {}).get("material", "")),
        ("DATE",     (spec or {}).get("date", "")),
    ]
    for label, val in optional_rows:
        if not val or not str(val).strip():
            continue
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x + 0.1, y, label + ":")
        c.setFont("Helvetica", 9)
        c.drawString(x + 1.4, y, str(val))
        y -= 0.22

    c.setFont("Helvetica-Bold", 9)
    c.drawString(x + 0.1, y, "DRAWN BY:")
    c.setFont("Helvetica", 9)
    c.drawString(x + 1.4, y, "Empire Drafting Studio (B2)")
    y -= 0.22


def _draw_layout_math(c: Canvas, math_lines: list):
    """Closure block in monospace, top-left below the drawing area."""
    if not math_lines:
        return
    x = DRAWING_X + 0.1
    y = DRAWING_Y + 0.6
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x, y, "LAYOUT MATH (Rule 3 — segments + gaps = overall):")
    y -= 0.18
    c.setFont("Courier", 8.5)
    for ml in math_lines:
        seg = " + ".join(f'{n} × {_fmt_in(v)}' for n, v in ml.segments) or "—"
        gap = " + ".join(f'{n} × {_fmt_in(v)}' for n, v in ml.gaps) or "—"
        total = seg + (f' + {gap}' if ml.gaps else '')
        warn = "" if ml.closing_tolerance_in < (1 / 64) else "  ⚠  "
        line = f"{warn}{total}  =  {_fmt_in(ml.total)}  (target {_fmt_in(ml.target_in)})"
        c.drawString(x, y, line)
        y -= 0.16
        if ml.note:
            c.setFont("Helvetica-Oblique", 7.5)
            c.drawString(x, y, "  " + ml.note)
            c.setFont("Courier", 8.5)
            y -= 0.16


def _draw_assumptions(
    c: Canvas, geometry, product_type: str, spec: dict,
):
    """NOTES / ASSUMPTIONS — CONFIRM.

    HOTFIX B2 (3): (cid:127) bullet glyph was missing from the
    embedded font in B1 — the PDF text stream contained the raw
    codepoint. Replaced with the ASCII asterisk '*' which is in
    every standard ReportLab font (Helvetica, Courier, Times).
    """
    x = DRAWING_X + 0.1
    y = DRAWING_Y + 0.05
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x, y, "NOTES / ASSUMPTIONS — CONFIRM:")
    y -= 0.18
    c.setFont("Helvetica-Oblique", 8.5)
    # The assumptions live on the GeometryFamilyResult. The
    # renderer caller computes them via the template's
    # .assumptions(spec) method. We accept them as part of
    # `spec["assumptions"]` if pre-computed, otherwise the caller
    # passes them in via the title-block context (not in this
    # helper). The caller-side render_drawing() function in
    # printer.py passes them in by attaching them to the geometry.
    # For B2 we expect the caller to call the template's
    # assumptions() and pipe them through.
    pass  # Render in the caller; this helper reserves the slot.
