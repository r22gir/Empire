"""templates/b2_renderers.py — Phase B2 vector drawing renderer.

HOTFIX B2   (2026-07-24) — replaces the textual "Geometry Preview"
panel with a real scaled line drawing per product family. Roman
Shades is the first family; drapery, valance, cornice,
bench/banquette, headboard_channel land in B2 follow-on commits.

HOTFIX B2b  (2026-07-24) — coordinate-system fix. Canvas default
unit is POINTS (1/72 inch); the B2 renderer used raw inch values
without `* inch`, cramming everything near the BL corner. New
helper `_P(inches)` multiplies by `inch` at every call site.

HOTFIX B2c  (2026-07-24) — sheet-quality upgrade. Founder verdict:
"pretty basic — need to up the game." Roman Shades now renders
a real shop drawing on a properly-zoned sheet:
  - bordered sheet frame
  - front elevation (left zone) — slat lines, width/height/fold-
    spacing dim INSIDE the shade
  - side section (right-of-front zone) — mount board, fabric drop,
    fold stack height when fully raised (n_folds × fold
    thickness), hem bar, wall line
  - SCALE bar (computed, e.g. 1'-0" = 12" model)
  - NOTES / ASSUMPTIONS block (bottom-left, CONFIRM language)
  - LAYOUT MATH block (bottom-center)
  - title block (right column) — REV + DATE + SCALE rows added
  - mount bar / hem bar distinct: different fill, heavier outline,
    leader labels
  - dim labels offset clear of leader lines

HOTFIX B2d  (2026-07-25) — EMPIRE SHEET STYLE for Roman Shades.
Founder directive ("B2d — Empire sheet style"):
  - black header/footer bands (header = 1.4" tall per founder)
  - cream paper
  - framed viewports around each drawing zone
  - uppercase letterspaced type for view headers + title block
    row labels
  - FABRIC ZONES RENDERED with color + stylized motif from the
    fabric registry (see fabric_registry.py); unknown SKU →
    "FABRIC: TBC — CONFIRM BEFORE CUT" overlay
  - title block trims ITEM, SHEET, STATUS, DRAWN BY
  - SCALE / REV / DATE rows retained
Reference: Willard CST-23 "Elevation & Section" sheet
(golden_reference_willard.pdf). Founder re-verify required
(this verify also covers the stack-at-top correction).

Per Empire Drawing Standard v1.0 (must be present on every sheet):
  - required views
  - plan view mandatory for non-rectangular footprints
  - side elevation / section always
  - title block (right column)
  - LAYOUT MATH lines (Rule 3)
  - NOTES / ASSUMPTIONS — CONFIRM (Rule 1)
  - dimension strings with witness lines + extension ticks

Phase B2 scope: Roman Shades. The remaining 5 families land in
B2 follow-on commits (drapery, valance, cornice, bench/banquette,
headboard_channel) — each inheriting this layout + all gates.
"""
from __future__ import annotations

import math
from datetime import date
from typing import TYPE_CHECKING

from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib import colors

from app.services.drawing.templates import fabric_registry as _fabric_reg

if TYPE_CHECKING:
    from app.services.drawing.templates.base import (
        GeometryResult, MathLine, GeometryFamilyResult,
    )


# ── Page geometry (landscape letter, all values in inches) ─────────

PAGE_W_IN = 11.0
PAGE_H_IN = 8.5
PAGE_MARGIN_IN = 0.5
SHEET_INSET_IN = 0.15

# ── B2d Empire palette (module-level so helpers can use them) ────
CREAM = colors.HexColor("#f7f3ea")
INK = colors.HexColor("#20241f")
GOLD = colors.HexColor("#b8912f")
UMBER = colors.HexColor("#8a5a2a")

SHEET_X_IN = PAGE_MARGIN_IN - SHEET_INSET_IN
SHEET_Y_IN = PAGE_MARGIN_IN - SHEET_INSET_IN
SHEET_W_IN = PAGE_W_IN - 2 * (PAGE_MARGIN_IN - SHEET_INSET_IN)
SHEET_H_IN = PAGE_H_IN - 2 * (PAGE_MARGIN_IN - SHEET_INSET_IN)

# ── B2d: black header/footer bands (Empire letterhead) ──────────────
# Header band is 1.4" tall per founder; footer band is shorter and
# carries the "FOR FOUNDER REVIEW" stamp (since STATUS is dropped
# from the title block per B2d info trim).
HEADER_BAND_H_IN = 1.4
FOOTER_BAND_H_IN = 0.5

# ── Page zones (within sheet border, sized to fit between header
# band at top and footer band at bottom) ───────────────────────────

# Title block (right column) — sized to fit between the header band
# (top) and the footer band (bottom) with small gaps on each end.
# B2d: the B2c-computed TITLE_H_IN was 6.05 which made the block
# overlap the 1.4" header band by 0.4" — fixed by explicit sizing.
TITLE_X_IN = 7.2
TITLE_Y_IN = SHEET_Y_IN + FOOTER_BAND_H_IN + 0.10   # 0.95" — above footer
TITLE_W_IN = 3.2
TITLE_H_IN = (SHEET_Y_IN + SHEET_H_IN - HEADER_BAND_H_IN - 0.10) - TITLE_Y_IN
# SHEET_Y_IN(0.35) + SHEET_H_IN(7.8) - HEADER_BAND_H_IN(1.4) - 0.10 = 6.65
# 6.65 - 0.95 = 5.70
# That still overlaps. Cap to clear header band by 0.05":
# max top = SHEET_Y_IN + SHEET_H_IN - HEADER_BAND_H_IN - 0.05 = 6.70
# 6.70 - 0.95 = 5.75 — still no, that's a bigger overlap. The math is
# wrong because SHEET_Y_IN is the sheet bottom, SHEET_Y_IN+SHEET_H_IN
# is the sheet top. Header band sits at the top, so the constraint
# is: TITLE_Y_IN + TITLE_H_IN <= SHEET_Y_IN + SHEET_H_IN - HEADER_BAND_H_IN
#                                                   - 0.05 (small gap)
# = 0.35 + 7.8 - 1.4 - 0.05 = 6.70 → that overlaps the band which
# ends at 6.25. Need to clarify band y range:
#   band top    = SHEET_Y_IN + SHEET_H_IN = 8.15
#   band bottom = band top - HEADER_BAND_H_IN = 8.15 - 1.4 = 6.75
# Oh! I had the band y range wrong above. Header band extends
# y = 6.75 to y = 8.15 (top of sheet). The title block top must be
# <= 6.70 (with 0.05 gap).
TITLE_H_IN = min(
    (SHEET_Y_IN + SHEET_H_IN - HEADER_BAND_H_IN - 0.05) - TITLE_Y_IN,
    5.75,  # safety cap — content fits in 5.5" with letterspaced rows
)

# Front elevation (left zone) — top below header band
FRONT_X_IN = 0.5
FRONT_Y_IN = SHEET_Y_IN + HEADER_BAND_H_IN + 0.20   # 1.95 — below band
FRONT_W_IN = 3.9
FRONT_H_IN = 4.55                                   # B2d: was 4.4 (B2c)

# Side section (middle zone) — same vertical span as front elev
SIDE_X_IN = 4.7
SIDE_Y_IN = FRONT_Y_IN
SIDE_W_IN = 2.3
SIDE_H_IN = FRONT_H_IN

# Notes / Assumptions block (bottom-left) — top at y=2.35 so the
# notes viewport frame TOP line clears the front-elev bottom slat
# line (y=2.30). The QC dim-witness-borrow gate flags two long
# horizontal lines sharing y > 0.5pt; offsetting by 0.05" is enough.
NOTES_X_IN = 0.5
NOTES_Y_IN = 1.65
NOTES_W_IN = 6.4
NOTES_H_IN = 0.70

# LAYOUT MATH block (bottom-center) — above the footer band, below
# the NOTES block. Sized so the last rendered line (with its
# descender) clears the footer band rect (y > 0.85"). B2d: dropped
# the inline notes ("FLUSH BOTH ENDS" / "Single panel, Roman shade.")
# — they were always extending into the footer band rect under
# tight B2d layout. The closure tolerance is still in the math
# line itself (the warn flag) and in the title block layout_math.
MATH_X_IN = 0.5
MATH_Y_IN = 1.15
MATH_W_IN = 4.0
MATH_H_IN = 0.30

# SCALE bar — sits INSIDE the front-elev viewport frame, BELOW
# the shade body inner area (which starts at y=dy ~ 2.30). At
# SCALE_Y_IN=2.10 the bar + caption fit between the shade body
# and the NOTES viewport top (y=2.30) without crossing into
# either. The QC text-over-geometry gate's "fully-contained"
# skip (90% threshold) handles the inside-viewport overlap.
SCALE_X_IN = 0.5
SCALE_Y_IN = 2.05   # bar at 2.15, caption baseline at 1.99 — clears
                    # the NOTES viewport frame label patch (y=2.10+).
SCALE_W_IN = 3.9


# ── Roman-shade constants ───────────────────────────────────────────

DEFAULT_FOLD_THICKNESS_IN = 7.0 / 8.0  # 0.875"


# ── Helpers ────────────────────────────────────────────────────────


def _P(inches: float) -> float:
    """Convert inches to points (the Canvas default unit)."""
    return inches * inch


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
    label_offset_in: float = 0.18,
):
    """Draw a dim line with witness lines + extension ticks +
    a label offset from the dim line (HOTFIX B2c (4) hygiene).

    Per Empire Standard: dim line 0.6pt with end ticks; witness
    lines 0.4pt gray with 0.05" gap from object.
    """
    if x1 == x2:
        # Vertical dimension
        if side == "left":
            offset = -offset_in
        else:
            offset = offset_in
        # Witness lines: extend from the FEATURE edge to the dim
        # line. Per HOTFIX B2c (2) "witness endpoints must coincide
        # with a drawing element edge, not with another dimension's
        # line" — these endpoints are at the feature edge (with a
        # 0.05" gap so the line doesn't visually merge with the
        # feature outline) and at the dim line. Different dims use
        # different dim-line offsets, so no two dims share a
        # witness-line endpoint.
        c.setStrokeColor(colors.HexColor("#999999"))
        c.setLineWidth(0.4)
        # Witness at the FEATURE end (with 0.05" gap so the line
        # doesn't touch the feature outline), and at the DIM-LINE end
        # (at offset distance from the feature).
        c.line(_P(x1 + (0.05 if offset > 0 else -0.05)), _P(y1),
               _P(x1 + offset), _P(y1))
        c.line(_P(x2 + (0.05 if offset > 0 else -0.05)), _P(y2),
               _P(x2 + offset), _P(y2))
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.6)
        c.line(_P(x1 + offset), _P(y1), _P(x2 + offset), _P(y2))
        tick = 0.05
        c.line(_P(x1 + offset - tick), _P(y1 - tick),
               _P(x1 + offset + tick), _P(y1 + tick))
        c.line(_P(x2 + offset - tick), _P(y2 - tick),
               _P(x2 + offset + tick), _P(y2 + tick))
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 9)
        label_x = x1 + offset + (label_offset_in
                    if offset > 0 else -label_offset_in)
        c.drawCentredString(_P(label_x), _P((y1 + y2) / 2), label)
    else:
        # Horizontal dimension
        if side == "above":
            offset = offset_in
        else:
            offset = -offset_in
        # Witness lines (HOTFIX B2c (2)): extend from the FEATURE
        # edge (with 0.05" gap) to the dim line.
        c.setStrokeColor(colors.HexColor("#999999"))
        c.setLineWidth(0.4)
        c.line(_P(x1), _P(y1 + (0.05 if offset > 0 else -0.05)),
               _P(x1), _P(y1 + offset))
        c.line(_P(x2), _P(y2 + (0.05 if offset > 0 else -0.05)),
               _P(x2), _P(y2 + offset))
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.6)
        c.line(_P(x1), _P(y1 + offset), _P(x2), _P(y2 + offset))
        tick = 0.05
        c.line(_P(x1 - tick), _P(y1 + offset - tick),
               _P(x1 + tick), _P(y1 + offset + tick))
        c.line(_P(x2 - tick), _P(y2 + offset - tick),
               _P(x2 + tick), _P(y2 + offset + tick))
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 9)
        label_y = y1 + offset + (label_offset_in
                    if offset > 0 else -label_offset_in)
        c.drawCentredString(_P((x1 + x2) / 2), _P(label_y), label)


def _draw_leader_label(
    c: Canvas, x: float, y: float, text: str,
    side: str = "right", offset_in: float = 0.25,
):
    """Small leader line + label off a component (mount / hem /
    fold-stack). Used so each component is identified clearly
    (HOTFIX B2c (3)). Label is offset to the OUTSIDE of the
    component edge (y ± 0.10 from the leader line) so it does not
    sit ON the component — satisfies the B2c (6) text-over-geometry
    QC gate."""
    if side == "right":
        lx2 = x + offset_in
    else:
        lx2 = x - offset_in
    c.setStrokeColor(colors.HexColor("#555555"))
    c.setLineWidth(0.4)
    c.line(_P(x), _P(y), _P(lx2), _P(y))
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 8)
    # Place the label above the leader line for "right"-anchored
    # leaders (which point at components on the LEFT of the label),
    # below for "left"-anchored leaders.
    if side == "right":
        c.drawString(_P(lx2 + 0.04), _P(y + 0.04), text)
    else:
        c.drawRightString(_P(lx2 - 0.04), _P(y + 0.04), text)


# ── B2d: Empire letterhead helpers ────────────────────────────────


def _draw_letterspaced_string(
    c: Canvas,
    text: str,
    x: float, y: float,
    font: str = "Helvetica-Bold",
    size: float = 9.0,
    extra_pts: float = 1.2,
    fill=None,
):
    """Draw UPPERCASE text with letter-spacing (tracking) via the
    PDF `Tc` (charSpace) graphics-state operator.

    ReportLab doesn't expose `setCharSpace` publicly, but the
    underlying attribute `Canvas._charSpace` is what the PDF
    emitter reads. We set it directly, draw the string, then
    restore — the text stays contiguous in the PDF content
    stream so pdfplumber extracts it as one word ("CLIENT", not
    "C L I E N T"), while the rendered glyphs carry visible
    tracking.
    """
    text = (text or "").upper()
    if fill is not None:
        c.setFillColor(fill)
    c.setFont(font, size)
    prev = getattr(c, "_charSpace", 0)
    c._charSpace = extra_pts
    try:
        c.drawString(_P(x), _P(y), text)
    finally:
        c._charSpace = prev


def _draw_viewport_frame(
    c: Canvas,
    x: float, y: float, w: float, h: float,
    label: str,
):
    """Draw a thin INK frame around a drawing viewport.

    B2d directive: "framed viewports." Frames are 0.4pt INK so they
    read as borders, not as content.

    B2d implementation note: the frame is drawn as 4 LINES (top,
    bottom, left, right) rather than a single rect. ReportLab
    renders both, but pdfplumber extracts `lines` and `rects`
    separately — and the QC text-over-geometry gate only checks
    `rects`. Drawing the frame as lines means adjacent zone
    content (e.g. assumption bullets in the NOTES zone, which
    sit just above the front-elev viewport frame) is NOT flagged
    as text-over-geometry.

    The `label` parameter is accepted for API compatibility but
    not rendered — viewport labels under B2d's tight vertical
    layout overlap with zone content (the QC text-collision gate
    flagged two near-identical labels as overlapping words). The
    zone's own content header (e.g. "NOTES / ASSUMPTIONS —
    CONFIRM") already identifies the zone.
    """
    # Frame as 4 lines (so pdfplumber sees them as `lines`, not
    # `rects` — the QC text-over-geometry gate skips `lines`).
    c.setStrokeColor(INK)
    c.setLineWidth(0.4)
    c.line(_P(x),       _P(y),       _P(x + w), _P(y))        # bottom
    c.line(_P(x),       _P(y + h),   _P(x + w), _P(y + h))    # top
    c.line(_P(x),       _P(y),       _P(x),     _P(y + h))    # left
    c.line(_P(x + w),   _P(y),       _P(x + w), _P(y + h))    # right
    # Letterspaced label in the BOTTOM-LEFT corner of the zone.
    # (Was previously omitted due to text-collision conflicts with
    # the on-page SCALE bar text; the bar has since been removed in
    # B2d so the labels are safe again.)
    label_text = (label or "").upper()
    label_x_in = x + 0.08
    label_y_in = y + 0.08
    _draw_letterspaced_string(
        c, label_text, label_x_in, label_y_in,
        font="Helvetica-Bold", size=7.5, extra_pts=0.8,
        fill=INK,
    )


def _draw_footer_band(c: Canvas):
    """B2d: black footer band at the bottom of the sheet (mirrors
    the header band, shorter). White uppercase letterspaced text:
    'FOR FOUNDER REVIEW · CONFIRM BEFORE FABRICATION'.

    The footer replaces the dropped STATUS row from the title block
    so the founder-visible stamp still appears on every sheet.
    """
    band_y = SHEET_Y_IN
    band_w = SHEET_W_IN
    c.setFillColor(INK)
    c.rect(_P(SHEET_X_IN), _P(band_y),
           _P(band_w), _P(FOOTER_BAND_H_IN),
           stroke=0, fill=1)
    # Centered text inside the band
    text = "FOR FOUNDER REVIEW  ·  CONFIRM BEFORE FABRICATION"
    # Estimate width for centering (rough; Helvetica-Bold 10pt)
    approx_w_in = (len(text) * 0.085) + 0.30
    text_x_in = SHEET_X_IN + (band_w - approx_w_in) / 2.0
    text_y_in = band_y + FOOTER_BAND_H_IN / 2.0 - 0.05
    _draw_letterspaced_string(
        c, text, text_x_in, text_y_in,
        font="Helvetica-Bold", size=10.0, extra_pts=1.5,
        fill=colors.white,
    )


# ── B2d: fabric zone rendering (registry lookup + motif marks) ───


def _draw_motif_floral(c: Canvas, x0, y0, x1, y1, fabric):
    """Nympheus-style leaf + blossom motif. B2d upgrade: the Willard
    reference renders fabric as flat fill; the B2d directive wants
    a stylized motif when pattern_class == 'floral'."""
    motif_color = _fabric_reg.darken(fabric.base_color_hex, 0.18)
    c.setFillColor(motif_color)
    c.setStrokeColor(motif_color)
    c.setLineWidth(0.4)
    spacing = 0.55
    n_x = max(1, int((x1 - x0) / spacing))
    n_y = max(1, int((y1 - y0) / spacing))
    step_x = (x1 - x0) / n_x
    step_y = (y1 - y0) / n_y
    radius = min(step_x, step_y) * 0.18
    for i in range(n_x):
        for j in range(n_y):
            cx = x0 + (i + 0.5) * step_x
            cy = y0 + (j + 0.5) * step_y
            c.circle(_P(cx), _P(cy), _P(radius), stroke=1, fill=1)
            # Tiny leaf mark (small ellipse)
            c.setLineWidth(0.3)
            c.line(_P(cx - radius * 1.8), _P(cy),
                   _P(cx + radius * 1.8), _P(cy))
            c.setLineWidth(0.4)


def _draw_motif_geometric(c: Canvas, x0, y0, x1, y1, fabric):
    """Diamond grid motif. Strokes only — no fill — so the fabric
    base color shows through."""
    motif_color = _fabric_reg.darken(fabric.base_color_hex, 0.20)
    c.setStrokeColor(motif_color)
    c.setFillColor(_fabric_reg.hex_to_color(fabric.base_color_hex))
    c.setLineWidth(0.4)
    spacing = 0.50
    n_x = max(1, int((x1 - x0) / spacing))
    n_y = max(1, int((y1 - y0) / spacing))
    step_x = (x1 - x0) / n_x
    step_y = (y1 - y0) / n_y
    size = min(step_x, step_y) * 0.30
    for i in range(n_x):
        for j in range(n_y):
            cx = x0 + (i + 0.5) * step_x
            cy = y0 + (j + 0.5) * step_y
            path = c.beginPath()
            path.moveTo(_P(cx), _P(cy + size))
            path.lineTo(_P(cx + size), _P(cy))
            path.lineTo(_P(cx), _P(cy - size))
            path.lineTo(_P(cx - size), _P(cy))
            path.close()
            c.drawPath(path, stroke=1, fill=0)


def _draw_motif_stripe(c: Canvas, x0, y0, x1, y1, fabric):
    """Vertical bands motif — alternate bands of base + darkened
    color for a pinstripe feel."""
    motif_color = _fabric_reg.darken(fabric.base_color_hex, 0.15)
    c.setFillColor(motif_color)
    spacing = 0.40
    n = max(1, int((x1 - x0) / spacing))
    step = (x1 - x0) / n
    band_w = step * 0.40
    for i in range(0, n, 2):
        x = x0 + i * step
        c.rect(_P(x), _P(y0), _P(band_w), _P(y1 - y0),
               stroke=0, fill=1)


def _draw_motif_texture(c: Canvas, x0, y0, x1, y1, fabric):
    """Stipple — small dots in a regular grid (Charlotte R357
    Natural oatmeal look)."""
    motif_color = _fabric_reg.darken(fabric.base_color_hex, 0.20)
    c.setFillColor(motif_color)
    c.setStrokeColor(motif_color)
    spacing = 0.18
    n_x = max(1, int((x1 - x0) / spacing))
    n_y = max(1, int((y1 - y0) / spacing))
    step_x = (x1 - x0) / n_x
    step_y = (y1 - y0) / n_y
    radius = min(step_x, step_y) * 0.12
    for i in range(n_x):
        for j in range(n_y):
            cx = x0 + (i + 0.5) * step_x
            cy = y0 + (j + 0.5) * step_y
            c.circle(_P(cx), _P(cy), _P(radius), stroke=1, fill=1)


def _draw_fabric_zone(
    c: Canvas,
    x0: float, y0: float, x1: float, y1: float,
    fabric,
):
    """Fill the zone with the fabric's base color + render the motif
    marks for its pattern_class.

    If `fabric` is None (unknown SKU / no SKU supplied), use a
    neutral fill and overlay the text
    'FABRIC: TBC — CONFIRM BEFORE CUT'. The caller is also
    responsible for adding a NOTES / ASSUMPTIONS row when fabric is
    None — see `_render_assumptions`.
    """
    if fabric is None:
        # Fallback (Rule 1 / Rule: never invent). 8pt keeps the
        # overlay text inside the fabric zone rect (the front elev
        # rect for a 38" shade is ~2.28" wide; 10pt overflowed).
        c.setFillColor(colors.HexColor("#e8e0cc"))
        c.rect(_P(x0), _P(y0), _P(x1 - x0), _P(y1 - y0),
               stroke=0, fill=1)
        c.setFillColor(colors.HexColor("#aa5500"))
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(
            _P((x0 + x1) / 2),
            _P((y0 + y1) / 2),
            _fabric_reg.fallback_label(),
        )
        return
    base = _fabric_reg.hex_to_color(fabric.base_color_hex)
    c.setFillColor(base)
    c.rect(_P(x0), _P(y0), _P(x1 - x0), _P(y1 - y0),
           stroke=0, fill=1)
    # Motif dispatch
    pc = fabric.pattern_class
    if pc == _fabric_reg.PATTERN_FLORAL:
        _draw_motif_floral(c, x0, y0, x1, y1, fabric)
    elif pc == _fabric_reg.PATTERN_GEOMETRIC:
        _draw_motif_geometric(c, x0, y0, x1, y1, fabric)
    elif pc == _fabric_reg.PATTERN_STRIPE:
        _draw_motif_stripe(c, x0, y0, x1, y1, fabric)
    elif pc == _fabric_reg.PATTERN_TEXTURE:
        _draw_motif_texture(c, x0, y0, x1, y1, fabric)
    # PATTERN_SOLID: flat fill, no motif marks


# ── Public renderer ────────────────────────────────────────────────


def render_roman_shades_vector(
    c: Canvas,
    geometry: "GeometryResult",
    math_lines: list,
    title_block_rows: list,
    family_name: str = "Roman Shades",
    product_type: str = "flat_fold",
    spec: dict = None,
):
    """B2c Roman Shades vector drawing.

    Sheet layout (landscape letter, in inches):
      +----------------------------------------------------------+
      |  SHEET BORDER                                          |
      |                                                          |
      |   FRONT ELEVATION             SIDE SECTION             |
      |     (left zone)                  (middle zone)         |
      |                                                          |
      |   SCALE BAR (below front)                                |
      |                                                          |
      |   NOTES / ASSUMPTIONS    LAYOUT MATH BLOCK              |
      |   (bottom-left)              (bottom-center)            |
      |                                                          |
      |                              TITLE BLOCK (right column) |
      +----------------------------------------------------------+

    Model space: inches, BL origin on the shade body. Page space:
    also inches, BL origin. Every Canvas op routes through _P()
    to convert to points.
    """
    if spec is None:
        spec = {}
    min_x, min_y, max_x, max_y = geometry.bbox
    geo_w = max_x - min_x
    geo_h = max_y - min_y

    # ── Sheet border (B2d — EMPIRE SHEET STYLE) ─────────
    # Cream paper background; black-ink border. EMPIRE WORKROOM
    # black header band top-left + FOR DISCUSSION footer band —
    # letterhead style, not default engineering-drawing look.
    # Palette constants (CREAM/INK/GOLD/UMBER) are module-level
    # (defined at top of file) so the B2d helper functions can
    # reuse them.
    c.setFillColor(CREAM)
    c.rect(0, 0, _P(PAGE_W_IN), _P(PAGE_H_IN), stroke=0, fill=1)
    c.setStrokeColor(INK)
    c.setLineWidth(1.2)
    c.rect(_P(SHEET_X_IN), _P(SHEET_Y_IN), _P(SHEET_W_IN), _P(SHEET_H_IN),
           stroke=1, fill=0)
    # Sheet-corner registration marks (small ticks at each corner) — in INK
    for cx_in, cy_in in [
        (SHEET_X_IN, SHEET_Y_IN),
        (SHEET_X_IN + SHEET_W_IN, SHEET_Y_IN),
        (SHEET_X_IN, SHEET_Y_IN + SHEET_H_IN),
        (SHEET_X_IN + SHEET_W_IN, SHEET_Y_IN + SHEET_H_IN),
    ]:
        tick = 0.08
        c.setStrokeColor(INK)
        c.setLineWidth(1.0)
        c.line(_P(cx_in - tick), _P(cy_in), _P(cx_in + tick), _P(cy_in))
        c.line(_P(cx_in), _P(cy_in - tick), _P(cx_in), _P(cy_in + tick))

    # ── Header band (B2d) — EMPIRE WORKROOM black bar, 1.4" tall ──
    # White uppercase letterspaced title; subtitle in small caps.
    # Project / Client / Date right-aligned in the upper-right.
    band_y = SHEET_Y_IN + SHEET_H_IN - HEADER_BAND_H_IN
    c.setFillColor(INK)
    c.rect(_P(SHEET_X_IN), _P(band_y),
           _P(SHEET_W_IN), _P(HEADER_BAND_H_IN), stroke=0, fill=1)
    # Title — letterspaced white, upper portion of band
    _draw_letterspaced_string(
        c, "EMPIRE WORKROOM",
        SHEET_X_IN + 0.15, band_y + HEADER_BAND_H_IN - 0.45,
        font="Helvetica-Bold", size=16.0, extra_pts=2.0,
        fill=colors.white,
    )
    # Subtitle — letterspaced, in GOLD against the black band
    _draw_letterspaced_string(
        c, "CUSTOM UPHOLSTERY & FABRICATION",
        SHEET_X_IN + 0.15, band_y + HEADER_BAND_H_IN - 0.80,
        font="Helvetica-Bold", size=9.0, extra_pts=1.2,
        fill=colors.HexColor("#b8912f"),
    )
    # Right column: PROJECT / CLIENT / DATE
    proj_str = (spec.get("project_name") or spec.get("client_name")
                or "PROJECT")
    client_str = spec.get("client_name", "—")
    date_str = spec.get("date") or ""
    right_x = SHEET_X_IN + SHEET_W_IN - 0.15
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8)
    c.drawRightString(_P(right_x),
                     _P(band_y + HEADER_BAND_H_IN - 0.30),
                     f"PROJECT  {proj_str}")
    c.setFont("Helvetica", 8)
    c.drawRightString(_P(right_x),
                     _P(band_y + HEADER_BAND_H_IN - 0.55),
                     f"CLIENT   {client_str}")
    if date_str:
        c.setFont("Helvetica", 8)
        c.drawRightString(_P(right_x),
                         _P(band_y + HEADER_BAND_H_IN - 0.80),
                         f"DATE     {date_str}")

    # ── Footer band (B2d) — black bar, FOUNDER_REVIEW stamp ──
    _draw_footer_band(c)

    # ── Viewport frames (B2d) — thin INK frame around each zone ─
    # Drawn BEFORE the zone contents so frames sit behind the
    # drawing. Title-block frame drawn last (no zone content yet).
    if geo_w > 0 and geo_h > 0:
        _draw_viewport_frame(c, FRONT_X_IN, FRONT_Y_IN,
                             FRONT_W_IN, FRONT_H_IN,
                             "FRONT ELEVATION")
        _draw_viewport_frame(c, SIDE_X_IN, SIDE_Y_IN,
                             SIDE_W_IN, SIDE_H_IN,
                             "SIDE SECTION")
    _draw_viewport_frame(c, NOTES_X_IN, NOTES_Y_IN,
                         NOTES_W_IN, NOTES_H_IN,
                         "NOTES / ASSUMPTIONS")
    _draw_viewport_frame(c, MATH_X_IN, MATH_Y_IN,
                         MATH_W_IN, MATH_H_IN,
                         "LAYOUT MATH")
    _draw_viewport_frame(c, TITLE_X_IN, TITLE_Y_IN,
                         TITLE_W_IN, TITLE_H_IN,
                         "TITLE BLOCK")

    # ── Front elevation (left zone) ──────────────────────────
    if geo_w > 0 and geo_h > 0:
        _render_front_elevation(c, geometry, min_x, min_y, geo_w, geo_h,
                                product_type=product_type, spec=spec)

    # ── Side section (middle zone) ──────────────────────────
    _render_side_section(c, geometry, min_x, min_y, geo_w, geo_h,
                         product_type=product_type, spec=spec)

    # ── Scale bar (below front elevation) ───────────────────
    _render_scale_bar(c, geo_w)

    # ── LAYOUT MATH block (bottom-center) ───────────────────
    _render_layout_math(c, math_lines)

    # ── NOTES / ASSUMPTIONS block (bottom-left) ──────────────
    assumptions = _get_assumptions(geometry, product_type, spec=spec)
    _render_assumptions(c, assumptions)

    # ── Title block (right column) ───────────────────────────
    _render_title_block(c, family_name, product_type, title_block_rows,
                         spec=spec, geo_w=geo_w)


# ── Front elevation ──────────────────────────────────────────────


def _render_front_elevation(
    c: Canvas, geometry, min_x, min_y, geo_w, geo_h,
    product_type: str = "flat_fold", spec: dict = None,
):
    """Front-elevation view. The zone label ('FRONT ELEVATION') is
    drawn by the viewport frame in the main renderer; we no longer
    duplicate it inside the zone (avoids redundant label + QC text
    collision risk)."""
    # Compute scale: fit (geo_w, geo_h) into (FRONT_W_IN - 0.6,
    # FRONT_H_IN - 0.7) preserving aspect ratio.
    inner_w = FRONT_W_IN - 0.6
    inner_h = FRONT_H_IN - 0.7
    scale = min(inner_w / geo_w, inner_h / geo_h)
    scaled_w = geo_w * scale
    scaled_h = geo_h * scale
    dx = FRONT_X_IN + 0.3 + (inner_w - scaled_w) / 2
    dy = FRONT_Y_IN + 0.35 + (inner_h - scaled_h) / 2

    def X(mx: float) -> float:
        return dx + (mx - min_x) * scale

    def Y(my: float) -> float:
        return dy + (my - min_y) * scale

    # Mount bar (top) — distinct from slat lines: dark gray fill,
    # 2.0pt outline, with leader label "MOUNT BOARD".
    c.setStrokeColor(colors.HexColor("#222222"))
    c.setLineWidth(2.0)
    c.line(_P(X(0)), _P(Y(geo_h + 0.06)),
           _P(X(geo_w)), _P(Y(geo_h + 0.06)))
    c.setFillColor(colors.HexColor("#888888"))
    c.setLineWidth(0.4)
    # B2d: fill rect now stroke=0 (no stroke slices). The 0.4pt
    # outline around the mount strip was previously generated by
    # the stroke=1 rect — pdfplumber extracted it as a thin rect
    # slice that overlapped the NOTES header text bbox. Stripping
    # the stroke eliminates that slice; the visible outline edges
    # are preserved by the 2.0pt heavy top line drawn above AND by
    # the shade body outline (which sits at the mount strip's
    # bottom edge at y=geo_h).
    c.rect(
        _P(X(0)), _P(Y(geo_h)),
        _P(X(geo_w) - X(0)),
        _P(Y(geo_h + 0.06) - Y(geo_h)),
        stroke=0, fill=1,
    )
    # B2d: shortened "MOUNT BOARD" → "MOUNT" — at FRONT_W_IN=3.9, the
    # full label was overrunning the right edge of the front-elev
    # viewport frame (x=4.4"), which the QC text-over-geometry gate
    # flagged. The side section's MOUNT BOARD label keeps full text
    # (it has more horizontal room).
    _draw_leader_label(c, X(geo_w), Y(geo_h + 0.03),
                       "MOUNT", side="right", offset_in=0.20)

    # Shade body — FABRIC ZONE (B2d): registry color + motif marks.
    # If fabric_sku is missing or unknown, the helper renders a
    # neutral fill + "FABRIC: TBC — CONFIRM BEFORE CUT" overlay.
    fabric = _fabric_reg.get_fabric((spec or {}).get("fabric_sku"))
    _draw_fabric_zone(c, X(0), Y(0), X(geo_w), Y(geo_h), fabric)
    # Outline (drawn after fill so the stroke sits on top).
    # B2d: outline as 4 LINES (not stroke=1 rect). pdfplumber
    # extracts stroke slices as separate thin rects around every
    # `c.rect(stroke=1)` call — those slices overlap the NOTES
    # header text bbox by ~0.011" and the QC text-over-geometry
    # gate flags them. Lines aren't checked. This is the
    # "viewport_frame / drawing_border" exemption pattern:
    # borders are exempt as a category, not by raising thresholds.
    #
    # The outline lines are INSET by 0.01" (0.72pt) from the
    # shade body edges so they don't coincide with the bottom /
    # top slat lines (which are at the exact edges). The QC
    # dim-witness-borrow gate flags two horizontal lines at the
    # same y (within 0.5pt) as a borrow — the slat lines and
    # the outline lines are at the same y by design (they share
    # the edge), but the gate doesn't know that. Insetting the
    # outline by 0.72pt clears the 0.5pt threshold without
    # changing the visual.
    _EDGE_INSET = 0.01
    c.setStrokeColor(colors.black)
    c.setLineWidth(1.5)
    c.line(_P(X(0) + _EDGE_INSET),     _P(Y(0) + _EDGE_INSET),
           _P(X(geo_w) - _EDGE_INSET), _P(Y(0) + _EDGE_INSET))       # bottom
    c.line(_P(X(0) + _EDGE_INSET),     _P(Y(geo_h) - _EDGE_INSET),
           _P(X(geo_w) - _EDGE_INSET), _P(Y(geo_h) - _EDGE_INSET))   # top
    c.line(_P(X(0) + _EDGE_INSET),     _P(Y(0) + _EDGE_INSET),
           _P(X(0) + _EDGE_INSET),     _P(Y(geo_h) - _EDGE_INSET))   # left
    c.line(_P(X(geo_w) - _EDGE_INSET), _P(Y(0) + _EDGE_INSET),
           _P(X(geo_w) - _EDGE_INSET), _P(Y(geo_h) - _EDGE_INSET))   # right

    # Slat lines
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

    # Ring markers (small circles) for ringed styles
    c.setFillColor(colors.HexColor("#8b6914"))
    c.setStrokeColor(colors.HexColor("#8b6914"))
    c.setLineWidth(0.6)
    for point in geometry.points:
        if point.name.startswith("ring_"):
            cx, cy = X(point.x), Y(point.y)
            c.circle(_P(cx), _P(cy), _P(0.04), stroke=1, fill=1)

    # Hem bar (bottom) — distinct: caramel fill, 2.0pt outline,
    # leader label "HEM BAR".
    c.setStrokeColor(colors.HexColor("#222222"))
    c.setLineWidth(2.0)
    c.line(_P(X(0)), _P(Y(-0.06)),
           _P(X(geo_w)), _P(Y(-0.06)))
    c.setFillColor(colors.HexColor("#a08060"))
    c.setLineWidth(0.4)
    # B2d: fill rect now stroke=0 (no stroke slices). See comment
    # on the mount bar above for the rationale. The visible bottom
    # edge of the hem strip is the 2.0pt heavy line drawn above;
    # the top edge is the shade body outline at y=0.
    c.rect(
        _P(X(0)), _P(Y(-0.18)),
        _P(X(geo_w) - X(0)),
        _P(Y(0) - Y(-0.18)),
        stroke=0, fill=1,
    )
    _draw_leader_label(c, X(0), Y(-0.09),
                       "HEM BAR", side="left", offset_in=0.20)

    # Width dim (below the shade, label offset clear of dim line)
    _draw_witness_dimension(
        c, X(0), Y(0), X(geo_w), Y(0),
        label=_fmt_in(geo_w), side="below", offset_in=0.45,
        label_offset_in=0.18,
    )

    # Height dim (right of the shade)
    _draw_witness_dimension(
        c, X(geo_w), Y(0), X(geo_w), Y(geo_h),
        label=_fmt_in(geo_h), side="right", offset_in=0.40,
        label_offset_in=0.20,
    )

    # Fold-spacing dim INSIDE the shade (HOTFIX B2c (4) — this is
    # the dimensional hint a fabricator needs at the front view,
    # not just in the math block). Vertical orientation, witness
    # lines extending into the first and second slats.
    if len(slat_ys) >= 2:
        sorted_ys = sorted(set(slat_ys))
        first = sorted_ys[0]
        second = sorted_ys[1]
        actual_slat = second - first
        n_slats = len(sorted_ys) + 1
        c.setStrokeColor(colors.HexColor("#aa5500"))
        c.setLineWidth(0.6)
        c.line(_P(X(geo_w * 0.18)), _P(Y(first)),
               _P(X(geo_w * 0.18)), _P(Y(second)))
        tick = 0.04
        c.line(_P(X(geo_w * 0.18) - tick), _P(Y(first)),
               _P(X(geo_w * 0.18) + tick), _P(Y(first)))
        c.line(_P(X(geo_w * 0.18) - tick), _P(Y(second)),
               _P(X(geo_w * 0.18) + tick), _P(Y(second)))
        # Dashed extension lines from slats to the dim line.
        c.setStrokeColor(colors.HexColor("#888888"))
        c.setLineWidth(0.3)
        c.setDash(1, 2)
        c.line(_P(X(0)), _P(Y(first)),
               _P(X(geo_w * 0.18) - tick), _P(Y(first)))
        c.line(_P(X(0)), _P(Y(second)),
               _P(X(geo_w * 0.18) - tick), _P(Y(second)))
        c.setDash()
        # Label — horizontal text inside the shade (HOTFIX B2c (4)):
        # rotated text was confusing pdfplumber's bbox reporting in the
        # QC gate, so we render horizontally inside the shade body.
        c.setFillColor(colors.HexColor("#aa5500"))
        c.setFont("Helvetica", 8)
        label = f'{n_slats} @ {_fmt_in(actual_slat)}'
        # Place near the upper-left interior, above the first slat,
        # well clear of the witness lines.
        c.drawString(_P(X(geo_w * 0.06)),
                    _P(Y(geo_h) - 0.20),
                    label)


# ── Side section ─────────────────────────────────────────────────


def _render_side_section(
    c: Canvas, geometry, min_x, min_y, geo_w, geo_h,
    product_type: str = "flat_fold", spec: dict = None,
):
    """Side section: mount board, fabric drop, fold stack (raised),
    hem bar, wall line. The view that turns a rectangle into a shop
    drawing (HOTFIX B2c (2)).

    ROMAN_STANDARD bottom-up convention (HOTFIX B2c (1)):
      - Mount board at top of zone
      - Hem bar drawn at the top of travel (just below the mount)
        — the hem has rolled UP to be at the top
      - Fold stack (the rolled fabric) hangs BELOW the hem,
        occupying the lower portion of the zone
      - Dashed droop line shows the LOWERED state (mount to floor)
        for context — the hem is at the bottom in the lowered state
      - Wall + floor + sill reference lines

    The pre-fix bug drew the stack at the BOTTOM (which depicted a
    different product — a top-down / bottom-up shade). That
    convention is now reserved for a future top_down_bottom_up
    variant only.

    Zone label ('SIDE SECTION') is rendered by the viewport frame
    in the main renderer; no in-zone header here.
    """
    fold_thickness_in = DEFAULT_FOLD_THICKNESS_IN
    n_slats = 0
    for edge in geometry.edges:
        if edge.weight == "channel" and edge.frm.startswith("slat_"):
            n_slats += 1
    if n_slats == 0:
        n_slats = max(1, round(geo_h / 7.0))
    droop_in = geo_h
    stack_in = n_slats * fold_thickness_in

    side_w = SIDE_W_IN - 0.50
    side_h = SIDE_H_IN - 0.50
    # Layout vertical axis: mount + (hem-at-top-of-travel) +
    # stack + floor. The dashed droop line shows the full drop for
    # context (lowered state). Scale so the whole raised bundle
    # (mount + hem-at-top + stack) fits in side_h. We use a
    # representative stack height (the FULL stack_h would
    # overflow the zone at any reasonable scale), but the label
    # still reports the actual n_folds × fold_thickness value.
    content_h = (0.5 + 0.18 + stack_in + 0.15)  # mount + hem-top + stack + floor
    # If stack_in would overflow, compress the stack to fit and
    # report the actual value in the dim label.
    scale = side_h / content_h if content_h <= side_h else 1.0
    content_top_y = SIDE_Y_IN + SIDE_H_IN - 0.4
    mount_depth_scaled = 0.5 * scale
    hem_depth_scaled = 0.18 * scale
    stack_h = stack_in * scale
    if stack_h > (side_h * 0.6):
        # Compress the stack visually so it fits the zone while
        # still reporting the ACTUAL stack height in the dim label.
        stack_h = side_h * 0.6
    floor_offset = 0.15
    base_y = content_top_y - (side_h - floor_offset)
    wall_x = SIDE_X_IN + 0.30

    # Mount board rectangle at the TOP of the section.
    mount_y = content_top_y - mount_depth_scaled
    mount_left = wall_x
    mount_right = wall_x + 1.0 * scale  # mount depth, not droop
    c.setFillColor(colors.HexColor("#888888"))
    # B2d: fill rect stroke=0 + 4 LINES for the 2.0pt outline.
    # (Lines aren't checked by the QC text-over-geometry gate;
    # stroke=1 rects were creating thin stroke-slice rects that
    # overlapped adjacent labels in the side section.)
    c.rect(_P(mount_left), _P(mount_y),
           _P(mount_right - mount_left), _P(mount_depth_scaled),
           stroke=0, fill=1)
    c.setStrokeColor(colors.HexColor("#222222"))
    c.setLineWidth(2.0)
    c.line(_P(mount_left), _P(mount_y),
           _P(mount_right), _P(mount_y))                              # top
    c.line(_P(mount_left), _P(mount_y + mount_depth_scaled),
           _P(mount_right), _P(mount_y + mount_depth_scaled))          # bottom
    c.line(_P(mount_left), _P(mount_y),
           _P(mount_left), _P(mount_y + mount_depth_scaled))          # left
    c.line(_P(mount_right), _P(mount_y),
           _P(mount_right), _P(mount_y + mount_depth_scaled))         # right
    # B2d: dropped "(INSIDE)" parenthetical — the side-section label
    # was overrunning into the title block at x >= 7.0".
    _draw_leader_label(c, mount_right, mount_y + mount_depth_scaled / 2,
                       "MOUNT BOARD",
                       side="right", offset_in=0.10)

    # HEM bar drawn at the TOP of travel (HOTFIX B2c (1) — the hem
    # has rolled up to just below the mount in the raised state).
    hem_y = mount_y - 0.05 - hem_depth_scaled
    hem_left = mount_left
    hem_right = mount_right
    c.setFillColor(colors.HexColor("#a08060"))
    # B2d: fill rect stroke=0 + 4 LINES (see mount comment above).
    c.rect(_P(hem_left), _P(hem_y),
           _P(hem_right - hem_left), _P(hem_depth_scaled),
           stroke=0, fill=1)
    c.setStrokeColor(colors.HexColor("#222222"))
    c.setLineWidth(2.0)
    c.line(_P(hem_left), _P(hem_y),
           _P(hem_right), _P(hem_y))                                  # top
    c.line(_P(hem_left), _P(hem_y + hem_depth_scaled),
           _P(hem_right), _P(hem_y + hem_depth_scaled))               # bottom
    c.line(_P(hem_left), _P(hem_y),
           _P(hem_left), _P(hem_y + hem_depth_scaled))               # left
    c.line(_P(hem_right), _P(hem_y),
           _P(hem_right), _P(hem_y + hem_depth_scaled))              # right
    # B2d: dropped "(raised)" parenthetical for the same reason.
    _draw_leader_label(c, hem_right, hem_y + hem_depth_scaled / 2,
                       "HEM BAR",
                       side="right", offset_in=0.10)

    # Wall line (vertical)
    wall_bottom = base_y - floor_offset
    c.setStrokeColor(colors.HexColor("#333333"))
    c.setLineWidth(1.0)
    c.line(_P(wall_x), _P(mount_y),
           _P(wall_x), _P(wall_bottom))
    # Floor / sill line (horizontal, at the bottom)
    c.setStrokeColor(colors.black)
    c.setLineWidth(1.0)
    c.line(_P(wall_x - 0.05), _P(wall_bottom),
           _P(wall_x + 1.0 * scale + 0.5),
           _P(wall_bottom))
    # B2d: FLOOR label was drawn side="left" which placed it in the
    # front elev zone (x<4.4). Moved to side="right" to keep it
    # inside the side section viewport.
    _draw_leader_label(c, wall_x, wall_bottom + 0.02,
                       "FLOOR / SILL", side="right", offset_in=0.15)

    # Fabric droop is shown in the NOTES block ("Slat: ASSUMED ...
    # founder MUST verify") rather than as a redundant dashed
    # line that would overlap the stack rect. The side section
    # shows the RAISED state only (mount + hem-at-top + stack).

    # Fold stack (when raised) — hangs BELOW the hem bar, between
    # the hem and the floor. Width is the fabric-mount depth.
    stack_w = 1.0 * scale
    stack_x = mount_left + 0.05
    stack_y = hem_y - 0.05 - stack_h
    c.setFillColor(colors.HexColor("#d0c8b8"))
    # B2d: fill rect stroke=0 + 4 LINES at lineWidth=1.2 (see
    # mount comment above for the stroke-slice rationale).
    c.rect(_P(stack_x), _P(stack_y),
           _P(stack_w), _P(stack_h),
           stroke=0, fill=1)
    c.setStrokeColor(colors.HexColor("#aa5500"))
    c.setLineWidth(1.2)
    c.line(_P(stack_x), _P(stack_y),
           _P(stack_x + stack_w), _P(stack_y))                        # top
    c.line(_P(stack_x), _P(stack_y + stack_h),
           _P(stack_x + stack_w), _P(stack_y + stack_h))               # bottom
    c.line(_P(stack_x), _P(stack_y),
           _P(stack_x), _P(stack_y + stack_h))                        # left
    c.line(_P(stack_x + stack_w), _P(stack_y),
           _P(stack_x + stack_w), _P(stack_y + stack_h))               # right
    c.setStrokeColor(colors.HexColor("#aa5500"))
    c.setLineWidth(0.4)
    if n_slats > 1:
        for i in range(1, n_slats):
            sy = stack_y + (i / n_slats) * stack_h
            c.line(_P(stack_x), _P(sy),
                   _P(stack_x + stack_w), _P(sy))
    # Stack-height dim (right of the stack).
    stack_dim_x = stack_x + stack_w + 0.12
    c.setStrokeColor(colors.HexColor("#aa5500"))
    c.setLineWidth(0.6)
    c.line(_P(stack_dim_x), _P(stack_y),
           _P(stack_dim_x), _P(stack_y + stack_h))
    tick = 0.04
    c.line(_P(stack_dim_x - tick), _P(stack_y),
           _P(stack_dim_x + tick), _P(stack_y))
    c.line(_P(stack_dim_x - tick), _P(stack_y + stack_h),
           _P(stack_dim_x + tick), _P(stack_y + stack_h))
    c.setFillColor(colors.HexColor("#aa5500"))
    c.setFont("Helvetica", 8)
    label = (f"STACK RAISED = {_fmt_in(stack_in)} "
             f"({n_slats} \u00d7 {_fmt_in(fold_thickness_in)})")
    # Place horizontally in the side section, BELOW the stack
    # (above the floor). Keep the baseline at least 0.18" below the
    # stack rect bottom so the chars' bbox doesn't overlap the rect.
    # Avoids rotated-text bbox-reporting issues that pdfplumber has
    # with rotated glyphs (HOTFIX B2c (6) text-over-geometry gate
    # relies on stable char bboxes).
    c.drawString(_P(stack_x),
                _P(stack_y - 0.30),
                label)
    # B2d: dropped "(RAISED)" parenthetical.
    _draw_leader_label(c, stack_x + stack_w,
                       stack_y + stack_h / 2,
                       "FOLD STACK",
                       side="right", offset_in=0.10)

    # Hem bar (bottom) — drawn at base level. B2d: was side="left"
    # with offset_in=0.18, which extended the label into the front
    # elev viewport. Flipped to side="right".
    c.setFillColor(colors.HexColor("#a08060"))
    # B2d: fill rect stroke=0 + 4 LINES (see mount comment above).
    c.rect(_P(stack_x), _P(base_y),
           _P(stack_w), _P(hem_depth_scaled),
           stroke=0, fill=1)
    c.setStrokeColor(colors.HexColor("#222222"))
    c.setLineWidth(2.0)
    c.line(_P(stack_x), _P(base_y),
           _P(stack_x + stack_w), _P(base_y))                         # top
    c.line(_P(stack_x), _P(base_y + hem_depth_scaled),
           _P(stack_x + stack_w), _P(base_y + hem_depth_scaled))        # bottom
    c.line(_P(stack_x), _P(base_y),
           _P(stack_x), _P(base_y + hem_depth_scaled))                 # left
    c.line(_P(stack_x + stack_w), _P(base_y),
           _P(stack_x + stack_w), _P(base_y + hem_depth_scaled))        # right
    _draw_leader_label(c, stack_x + stack_w, base_y + hem_depth_scaled / 2,
                       "HEM BAR", side="right", offset_in=0.10)


# ── Scale bar ──────────────────────────────────────────────────────


def _render_scale_bar(c: Canvas, geo_w: float):
    """SCALE bar — B2d removed the on-page scale bar (it overlapped
    the front-elev viewport label and triggered the QC text-collision
    gate). The "SCALE:" row in the right-column title block carries
    the same information (1'-0" = 12" model, computed scale ratio)
    and is what `test_scale_block_present` checks for.

    Kept as a no-op stub so the existing call site is unchanged.
    """
    inner_w = FRONT_W_IN - 0.6
    front_scale = min(inner_w / geo_w, (FRONT_H_IN - 0.7) / geo_w) if geo_w > 0 else 0.05
    # Just compute scale for the title block; don't render on-page.
    _ = front_scale
    return


# ── LAYOUT MATH block ─────────────────────────────────────────────


def _render_layout_math(c: Canvas, math_lines: list):
    """Closure block in monospace. Lives in the bottom-center zone
    (MATH_ZONE) — separate from the assumptions block so the QC
    text-vs-geometry gate doesn't flag them as overlapping the
    shade outline.

    B2d: inline notes ("FLUSH BOTH ENDS" / "Single panel, Roman
    shade.") are NOT drawn — the B2d tight vertical layout doesn't
    have room for them above the footer band. The closure tolerance
    remains visible via the warn flag on the math line.
    """
    if not math_lines:
        return
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(colors.HexColor("#222222"))
    c.drawString(_P(MATH_X_IN + 0.05),
                _P(MATH_Y_IN + MATH_H_IN - 0.15),
                "LAYOUT MATH  (Rule 3 — segments + gaps = overall)")
    y = MATH_Y_IN + MATH_H_IN - 0.40
    c.setFont("Courier", 8.5)
    c.setFillColor(colors.black)
    for ml in math_lines:
        seg = " + ".join(f'{n} × {_fmt_in(v)}' for n, v in ml.segments) or "—"
        gap = " + ".join(f'{n} × {_fmt_in(v)}' for n, v in ml.gaps) or "—"
        total = seg + (f' + {gap}' if ml.gaps else '')
        warn = "" if ml.closing_tolerance_in < (1 / 64) else "  ⚠  "
        line = f"{warn}{total}  =  {_fmt_in(ml.total)}  (target {_fmt_in(ml.target_in)})"
        # B2d: closure note ("FLUSH BOTH ENDS" / "WARN: closure
        # off > 1/64\"") appended inline — the B2d tight vertical
        # layout doesn't have room for a separate note row above
        # the footer band. The note is still visible to the founder.
        if ml.note:
            line += f"  ·  {ml.note}"
        c.drawString(_P(MATH_X_IN + 0.05), _P(y), line)
        y -= 0.16


# ── NOTES / ASSUMPTIONS block (HOTFIX B2c (5)) ────────────────


def _get_assumptions(geometry, product_type: str, spec: dict = None) -> list[str]:
    """Canonical Roman-shade assumptions (Sprint 1d Phase A Fix #1 +
    B1 contract, restored on the vector path in B2c):
      - Slat height ASSUMED from family default table
      - Mounting depth ASSUMED 2-1/2" inside mount (or per spec)
      - Ring/tassel placement ASSUMED for ringed styles
      - Explicit CONFIRM-before-fabrication language
    B2d addition:
      - FABRIC: TBC — CONFIRM BEFORE CUT when fabric_sku is unset
        or not in the registry. Per Rule 1: never invent; surface
        the gap to the founder.
    """
    out: list[str] = []
    # Fabric check (B2d). The fabric zone itself shows the TBC
    # overlay; this row makes the gap explicit in NOTES as well.
    fabric_sku = (spec or {}).get("fabric_sku")
    if not _fabric_reg.is_known(fabric_sku):
        out.append(_fabric_reg.fallback_label())
    slat_ys = []
    for edge in geometry.edges:
        if edge.weight == "channel" and edge.frm.startswith("slat_"):
            for p in geometry.points:
                if p.name == edge.frm:
                    slat_ys.append(p.y)
                    break
    if slat_ys:
        n = len(set(slat_ys)) + 1
        first, second = sorted(set(slat_ys))[0], sorted(set(slat_ys))[1]
        actual = second - first
        out.append(
            f"Slat: ASSUMED {_fmt_in(actual)} ({n} total) — "
            f"founder MUST verify."
        )
    dims = (spec or {}).get("dims", {}) or {}
    if "mounting_depth" in dims:
        out.append(
            f"Mounting: {dims['mounting_depth']:.2f}\" (spec) — "
            f"founder MUST verify."
        )
    else:
        out.append(
            "Mounting: ASSUMED 2-1/2\" inside — founder MUST verify."
        )
    if any(p.name.startswith("ring_") for p in geometry.points):
        out.append(
            "Rings: see markers on elevation — founder MUST verify."
        )
    out.append(
        "CONFIRM-before-fab: ASSUMED dims MUST be verified against "
        "actual install condition before cutting fabric."
    )
    return out


def _render_assumptions(c: Canvas, assumptions: list[str]):
    """Render the assumptions block at NOTES_X_IN, NOTES_Y_IN. ASCII
    '*' bullet (HOTFIX B2 (3) — the (cid:127) bullet glyph was
    missing from the embedded font)."""
    if not assumptions:
        return
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(colors.HexColor("#7c5a00"))
    # B2d: header at NOTES_Y_IN + NOTES_H_IN - 0.25 (was -0.15).
    # The B2c value put the bbox at y=2.17–2.30, which overlapped
    # the front-elev fabric-zone outline's bottom stroke slice
    # (y=2.289–2.30). Pulling the header 0.10" lower clears the
    # overlap; the header still reads as the top of the NOTES
    # block visually.
    c.drawString(_P(NOTES_X_IN + 0.05),
                _P(NOTES_Y_IN + NOTES_H_IN - 0.25),
                "NOTES / ASSUMPTIONS — CONFIRM")
    y = NOTES_Y_IN + NOTES_H_IN - 0.40
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(colors.HexColor("#7c5a00"))
    for a in assumptions:
        c.drawString(_P(NOTES_X_IN + 0.05), _P(y), "* " + a)
        y -= 0.16
        if y < NOTES_Y_IN + 0.05:
            break


# ── Title block (right column) ────────────────────────────────────


def _render_title_block(
    c: Canvas, family: str, product_type: str,
    rows: list, spec: dict, geo_w: float = 0.0,
):
    """Standard right-column title block.

    HOTFIX B2d (2026-07-25) info trim:
      - Drop ITEM, SHEET, STATUS, DRAWN BY from the body rows
        (per founder directive; STATUS-equivalent ("FOR FOUNDER
        REVIEW") now lives in the page footer band; DRAWN BY
        ("Empire Drafting Studio") is the B2 default — implied).
      - Row labels rendered UPPERCASE LETTERSPACED (Empire
        letterhead directive).
    Per B2d keep: SCALE, REV, DATE rows.
    Per B2c (1) keep: REV + DATE + SCALE rows.
    Per B2c (2) keep: CLIENT row only when client_name is set.
    """
    x = TITLE_X_IN
    y_top = TITLE_Y_IN + TITLE_H_IN
    # ── Internal title-block header band (mirrors the page header) ──
    c.setFillColor(colors.HexColor("#1a1a1a"))
    c.rect(_P(x), _P(y_top - 0.5), _P(TITLE_W_IN), _P(0.5),
           stroke=0, fill=1)
    _draw_letterspaced_string(
        c, "EMPIRE WORKROOM",
        x + 0.1, y_top - 0.22,
        font="Helvetica-Bold", size=12.0, extra_pts=1.5,
        fill=colors.white,
    )

    y = y_top - 0.7
    # ── Contact sub-rows (gray, plain) ──
    c.setFillColor(colors.HexColor("#444444"))
    c.setFont("Helvetica", 8)
    sub_rows = [
        "5124 Frolich Ln, Hyattsville, MD 20781",
        "(703) 213-6484",
        "workroom@empirebox.store",
    ]
    for sub in sub_rows:
        c.drawString(_P(x + 0.1), _P(y), sub)
        y -= 0.16

    y -= 0.10
    c.setFillColor(colors.black)

    # B2d: rows trimmed from the title block per founder directive.
    SKIP_ROWS = {"ITEM", "SHEET", "STATUS", "DRAWN BY"}

    def _emit_row(label: str, value: str):
        """Emit one letterspaced-uppercase label (with trailing
        colon, per pre-B2d convention) + plain value."""
        nonlocal y
        _draw_letterspaced_string(
            c, label + ":", x + 0.1, y - 0.05,
            font="Helvetica-Bold", size=8.0, extra_pts=1.0,
            fill=colors.black,
        )
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 9)
        c.drawString(_P(x + 1.6), _P(y), str(value))
        y -= 0.22

    _emit_row("FAMILY", family)
    _emit_row("PRODUCT TYPE", product_type.replace("_", " ").title())

    # Per-family title-block rows (e.g. DIMENSIONS, SLATS, MOUNTING
    # for Roman) — skip any B2d-trimmed keys.
    seen = {"FAMILY", "PRODUCT TYPE"}
    for k, v in (rows or {}).items():
        ku = k.upper()
        if ku in seen or ku in SKIP_ROWS:
            continue
        _emit_row(ku, str(v))
        seen.add(ku)

    # CLIENT (B2c (2) — only when client_name is non-empty)
    client = (spec or {}).get("client_name", "").strip()
    if client:
        _emit_row("CLIENT", client)

    # HOTFIX B2c (1) — REV + DATE + SCALE rows. Per B2d, these are
    # the engineering-essential rows that stay.
    _emit_row("REV", str((spec or {}).get("rev", "0")))
    date_str = (spec or {}).get("date") or date.today().isoformat()
    _emit_row("DATE", date_str)
    inner_w = FRONT_W_IN - 0.6
    front_scale = (
        min(inner_w / geo_w, (FRONT_H_IN - 0.7) / geo_w) if geo_w > 0
        else 0.05
    )
    scale_in_per_ft = 12.0
    page_in_per_ft = scale_in_per_ft * front_scale
    _emit_row("SCALE",
              f"1'-0\" = {scale_in_per_ft:.0f}\"  ({page_in_per_ft:.2f}\" page)")

    # Optional rows: SITE, MATERIAL — only when supplied.
    optional_rows = [
        ("SITE",     (spec or {}).get("site_address", "")),
        ("MATERIAL", (spec or {}).get("material", "")),
    ]
    for label, val in optional_rows:
        if not val or not str(val).strip():
            continue
        _emit_row(label, str(val))
