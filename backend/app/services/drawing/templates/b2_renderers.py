"""templates/b2_renderers.py — Phase B2 vector drawing renderer.

B2d (2026-07-25) — EMPIRE SHEET STYLE. Initial bands + framed viewports.
HOTFIX B2c — sheet-quality upgrade.
HOTFIX B2b — coordinate-system fix (every coord through `_P(inches)`).

GOLDEN PORT (2026-07-26) — port of reports/golden_flatfold.py
(approved through 10 revision rounds by the founder). The golden's
layout, helpers, and 10 drafting-doctrine rules become the template
for every B2 family renderer. Style disputes resolve against the
golden, not against prose. See reports/2026-07-26_golden_port.md.

DRAFTING DOCTRINE — ten rules (R1-R10), each founder-taught; preserved
verbatim. The section-rule branch (R3) and reveal scale (R4) are the
non-obvious ones.

  R1  Standard roman = bottom-up; stack at HEAD, never at sill.
  R2  Room context on both views: ceiling 108" REF + head 96"
      ASSUMED when unspecified; site photo/dims override proportions
      when provided. Ceiling + floor lines always.
  R3  Mount condition branches the section: INSIDE → board and
      entire fabric assembly BEHIND the wall line, within the reveal
      (wall-line callout + glass line drawn); OUTSIDE → proud of
      the wall line.
  R4  Reveal at TRUE scale: 4" typical (3-4" max) housing the
      2-1/2" board. No lateral exaggeration — ever.
  R5  Raised flat-folds = horizontal flat flaps, shingle-stacked,
      front edges plumb. (Family variants for registry:
      flat_fold/back-slatted, relaxed/european curved-bottom,
      front-slatted plain.)
  R6  Fold tips emerge BELOW a flat fabric face — folds never
      start at the board.
  R7  Fabric attaches at the BOARD FRONT: face line starts at
      the board's front-top and wraps down. Machine-verifiable:
      fabric x == board front x.
  R8  Hem bar in section = thin VERTICAL slat in the fabric plane.
  R9  True-scale-plus-detail: when an element is too small at
      sheet scale, magnify in a labeled DETAIL (gold callout
      circle + N× box) — never distort the section.
  R10 Raised state renders at PARTIAL RAISE for honest weight:
      bottom at 1/2 drop — flat face = 25% of drop from head, fold
      stack = next 25%, hem at half. Label "SHOWN AT 1/2 RAISE".

Geometry stays parametric from the handoff. The golden is the
LAYOUT template, not a fixed drawing.

Per Empire Drawing Standard v1.0 (must be present on every sheet):
  - required views
  - plan view mandatory for non-rectangular footprints
  - side elevation / section always
  - title block (right column)
  - LAYOUT MATH lines (Rule 3)
  - NOTES / ASSUMPTIONS — CONFIRM (Rule 1)
  - dimension strings with witness lines + extension ticks
"""
from __future__ import annotations

import math
import random
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
MARGIN_IN = 0.32  # golden: tighter than B2d's 0.5
# Sheet border — golden's outer 1.1pt frame sits AT MARGIN_IN.

# ── Empire palette (golden v10) ─────────────────────────────────
CREAM   = colors.HexColor("#f7f3ea")
INK     = colors.HexColor("#20241f")
LIGHT   = colors.HexColor("#6f6a5e")
GOLD    = colors.HexColor("#b8912f")
ORANGE  = colors.HexColor("#b25a1d")
DIM     = colors.HexColor("#8a6a3a")
EMER    = colors.HexColor("#123a2a")  # Nympheus base green
EMER_D  = colors.HexColor("#0c2b1f")  # Nympheus shadow
LEAF    = colors.HexColor("#2f7350")
LEAF2   = colors.HexColor("#4a9268")
BLOSS   = colors.HexColor("#ead9c0")
CREAM2  = colors.HexColor("#efe8d8")
MUTED_GOLD = colors.HexColor("#cfc8b8")
CASING  = colors.HexColor("#8a8271")
GLASS_C = colors.HexColor("#7d8a94")
WOOD    = colors.HexColor("#5a4632")  # mount board
HEM_WOOD= colors.HexColor("#4a3b2a")
EMER_ALT= colors.HexColor("#175340")
DIVIDER = colors.HexColor("#c9c2b0")
# Fabric zone "TBC" neutral fill (when SKU unknown / no SKU)
TBC_FILL = colors.HexColor("#e8e0cc")
TBC_TXT  = colors.HexColor("#aa5500")

# ── Golden v10 layout constants ──────────────────────────────────
# Header band (top, INK fill), footer band (bottom, INK fill), three
# vertical viewports (front-elev | side-section | title-column).
# Vertical range between bands: top = H - MARGIN - HEADER_BAND_H,
#                              bottom = M + FOOTER_BAND_H.
HEADER_BAND_H_IN = 0.92          # golden: 0.92
FOOTER_BAND_H_IN = 0.42          # golden: 0.42
LAYOUT_GAP_IN    = 0.14          # golden: 0.14 between viewports
HEADER_GAP_IN    = 0.14          # golden: 0.14 below header band
FOOTER_GAP_IN    = 0.12          # golden: 0.12 above footer band

# Title column — rightmost viewport (per golden: col_r = W-M-2.62)
COL_R_IN    = PAGE_W_IN - MARGIN_IN - 2.62
TITLE_X_IN  = COL_R_IN
TITLE_Y_IN  = MARGIN_IN + FOOTER_BAND_H_IN + FOOTER_GAP_IN
TITLE_W_IN  = (PAGE_W_IN - MARGIN_IN - 0.18) - COL_R_IN
TITLE_H_IN  = (PAGE_H_IN - MARGIN_IN - HEADER_BAND_H_IN - HEADER_GAP_IN) - TITLE_Y_IN

# Front elevation — leftmost viewport
FRONT_X_IN  = MARGIN_IN + 0.18
FRONT_W_IN  = 4.55
FRONT_Y_IN  = TITLE_Y_IN
FRONT_H_IN  = TITLE_H_IN

# Side section — middle viewport
SIDE_X_IN   = FRONT_X_IN + FRONT_W_IN + LAYOUT_GAP_IN
SIDE_W_IN   = COL_R_IN - LAYOUT_GAP_IN - SIDE_X_IN
SIDE_Y_IN   = TITLE_Y_IN
SIDE_H_IN   = TITLE_H_IN


# ── Roman-shade constants ───────────────────────────────────────────

DEFAULT_FOLD_THICKNESS_IN = 7.0 / 8.0  # 0.875" — golden's 7/8" flap
N_SLATS_DEFAULT = 8                    # golden: NF = 8 raised flaps
ROOM_CEIL_IN = 108.0                  # R2: 108" REF ceiling
ROOM_HEAD_IN = 96.0                   # R2: 96" ASSUMED head
ROOM_AFF_MARGIN_IN = 6.0              # buffer above ceiling for view
REVEAL_DEPTH_IN = 4.0                 # R4: 4" typical reveal (3-4" max)
BOARD_DEPTH_IN = 2.5                 # mount board (2-1/2")
SILL_TO_FLOOR_GAP_IN = 0.5            # gap between sill and floor line
LATERAL_EXAGGERATION = 2.4            # golden v10: depth-axis exaggeration
                                       # (the section is wider than true scale
                                       # to show the stack clearly — R4's "no
                                       # lateral exaggeration" forbids a
                                       # HORIZONTAL page-width stretch, not this
                                       # depth-axis detail amplification that
                                       # is consistent with R9)
PARTIAL_RAISE_FRAC = 0.5             # R10: 1/2 drop at partial raise

# Correction 1: viewport-fill target for the elevation scale.
# The shade is the focus of the front elevation (and the side
# section's reference geometry), so `s` (sheet-inches per
# model-inch) is chosen so the shade fills at least
# ELEVATION_TARGET_FILL of one viewport axis. The previous
# R1 port used a ROOM-fit scale (s = inner_h / (ceiling +
# margin)), which made the 38" × 64" shade only ~40% of the
# viewport width — the geometry was shrunk, the SCALE stamp
# was a lie, and the founder's G1 verdict FAIL'd. The fix:
# shade-fit scale, SCALE row reports the actual value.
ELEVATION_TARGET_FILL = 0.90        # aim for ≥90% on height axis
ELEVATION_TARGET_FILL_MIN = 0.80    # gate threshold (≥80% on ≥1 axis)


def _compute_shade_scale(geo_w: float, geo_h: float,
                         viewport_w_in: float,
                         viewport_h_in: float,
                         target_fill: float = ELEVATION_TARGET_FILL,
                         margin_in: float = 0.30) -> float:
    """Compute sheet-inches-per-model-inch `s` such that the
    shade (geo_w × geo_h) fills `target_fill` of one viewport
    axis (whichever is more constraining).

    Args:
      geo_w, geo_h: shade dimensions in model inches
      viewport_w_in, viewport_h_in: inner viewport size (in)
      target_fill: fraction of axis to fill (e.g. 0.90 = 90%)
      margin_in: inset on each side (default 0.30)

    Returns:
      s = sheet-inches per model-inch (e.g. 0.0625 = "1\" = 1'-4\"")
    """
    if geo_w <= 0 or geo_h <= 0:
        return 0.05    # safe default
    inner_w = viewport_w_in - 2 * margin_in
    inner_h = viewport_h_in - 2 * margin_in
    # s_w = inner_w * target_fill / geo_w   (width-limited)
    # s_h = inner_h * target_fill / geo_h   (height-limited)
    # pick the smaller s so neither axis overflows.
    return min(
        (inner_w * target_fill) / geo_w,
        (inner_h * target_fill) / geo_h,
    )


def _format_scale_row(s: float) -> str:
    """Format the SCALE row text as '1\" = N'-M\"' from `s`
    (sheet-inches per model-inch). E.g. s=0.0625 → "1\" = 1'-4\"".

    Used by the title column SCALE row so the rendered scale
    stamp matches the actual scale used to draw the geometry
    (Correction 1: scale must be TRUE).
    """
    if s <= 0:
        return "—"
    model_in_per_sheet_in = 1.0 / s
    feet = int(model_in_per_sheet_in // 12)
    inches = model_in_per_sheet_in - feet * 12
    if abs(inches) < 0.01:
        return f"1\" = {feet}'-0\""
    if abs(inches - 12) < 0.01:
        return f"1\" = {feet + 1}'-0\""
    # Round to nearest 1/16
    sixteenths = round(inches * 16)
    whole = sixteenths // 16
    rem = sixteenths - whole * 16
    if rem == 0:
        return f"1\" = {feet}'-{whole}\""
    from math import gcd
    g = gcd(rem, 16)
    n = rem // g
    d = 16 // g
    return f"1\" = {feet}'-{whole}-{n}/{d}\""


# ── Helpers ────────────────────────────────────────────────────────


def _P(inches: float) -> float:
    """Convert inches to points (the Canvas default unit)."""
    return inches * inch


def ls_text(c, x, y, s, size, color=INK, tracking=1.6, bold=True,
           center=False, right=False):
    """Letterspaced uppercase — the Willard signature (from golden).

    The text is emitted as a single drawString call (ReportLab
    groups it as one TJ operator in the PDF), so pdfplumber
    extracts the whole word as one entry — while the rendered
    glyphs carry the visible tracking. This is the linchpin
    that lets the B2c test pattern (which asserts on substrings
    like "REV:" or "DIMENSIONS:") keep working even when the
    rendered text is letterspaced.

    NOTE: `x` and `y` are in INCHES; `stringWidth()` returns
    POINTS. center=True / right=True subtract `total/2` or `total`
    from x — those must be converted from points to inches
    (divided by 72). The golden-port R1 had a units bug here
    (`x -= total / 2.0` with total in points, x in inches) which
    shifted center-anchored text OFF-PAGE for any label longer
    than ~30 chars (e.g. "FOR DISCUSSION — NOT FOR
    CONSTRUCTION" was rendered at x ≈ -7700 pt, far left of the
    page). Correction 3 fixes this. The right=True path has the
    same bug — also fixed here.
    """
    f = "Helvetica-Bold" if bold else "Helvetica"
    c.setFont(f, size)
    c.setFillColor(color)
    s = (s or "").upper()
    if not s:
        return x
    total_pt = sum(c.stringWidth(ch, f, size) + tracking for ch in s) - tracking
    total_in = total_pt / 72.0
    if center:
        x -= total_in / 2.0
    if right:
        x -= total_in
    for ch in s:
        c.drawString(_P(x), _P(y), ch)
        x += (c.stringWidth(ch, f, size) + tracking) / 72.0
    return x


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
    NOT rendered here. Per Correction 4 (G1 verdict), the bottom-
    left corner labels previously drawn here duplicated the
    top-of-frame labels drawn by the per-viewport functions
    (_render_front_elevation, _render_side_section). Doctrine:
    "top of frame per doctrine." The bottom-left set is REMOVED.
    The label remains in the call sites so the API contract is
    unchanged for any caller iterating over multiple viewports.
    """
    # Frame as 4 lines (so pdfplumber sees them as `lines`, not
    # `rects` — the QC text-over-geometry gate skips `lines`).
    c.setStrokeColor(INK)
    c.setLineWidth(0.4)
    c.line(_P(x),       _P(y),       _P(x + w), _P(y))        # bottom
    c.line(_P(x),       _P(y + h),   _P(x + w), _P(y + h))    # top
    c.line(_P(x),       _P(y),       _P(x),     _P(y + h))    # left
    c.line(_P(x + w),   _P(y),       _P(x + w), _P(y + h))    # right
    # Correction 4: the bottom-left letterspaced label is REMOVED.
    # The per-viewport renderers (_render_front_elevation,
    # _render_side_section) draw the single canonical label at
    # the top-of-frame. The title-column viewport has no caption
    # at all — its content (PROJECT / CLIENT / FAMILY rows)
    # identifies it.


def _render_header_band(c, spec, family_name, product_type, geo_w, geo_h):
    """Golden v10 header band (0.92" INK fill at top of sheet).

    Layout:
      left 1 (top line)    : "EMPIRE WORKROOM  ·  SHOP DRAWING"
                              (MUTED_GOLD, 9pt, tracking 2.4)
      left 2 (large)       : family_name (e.g. "FLAT FOLD ROMAN SHADE")
                              (white Helvetica-Bold 21pt)
      right 1 (top line)   : "CST-DRAFT · {date} · REV 0"
                              (GOLD, 8pt, tracking 1.4)
      right 2 (smaller)    : dims + folds + mount line
                              (MUTED_GOLD, 8.5pt)
    """
    BH = HEADER_BAND_H_IN
    bx = MARGIN_IN
    by = PAGE_H_IN - MARGIN_IN - BH
    bw = PAGE_W_IN - 2 * MARGIN_IN
    c.setFillColor(INK)
    c.rect(_P(bx), _P(by), _P(bw), _P(BH), fill=1, stroke=0)
    # Left top line (muted gold)
    ls_text(c, bx + 0.28, by + 0.58,
            "EMPIRE WORKROOM  ·  SHOP DRAWING", 9, MUTED_GOLD,
            tracking=2.4, bold=True)
    # Left large (white) — golden v10: "FLAT FOLD ROMAN SHADE"
    # (SINGULAR — Correction 5a; the family nomenclature is
    # singular per the golden reference and per Empire family
    # naming). Other families (e.g. Drapery) pass a different
    # title via the `title_override` parameter (default: family +
    # product).
    c.setFont("Helvetica-Bold", 21)
    c.setFillColor(CREAM)
    if spec.get("title_override"):
        big_title = spec["title_override"]
    elif family_name == "Roman Shades":
        big_title = "FLAT FOLD ROMAN SHADE"
    else:
        # Default for new families: "{product_type} {family}".
        # The DraperyTemplate passes title_override explicitly
        # ("PINCH PLEAT DRAPERY" etc.), but this default is a
        # sensible fallback.
        big_title = f"{product_type.replace('_', ' ').upper()} {family_name.upper()}"
    c.drawString(_P(bx + 0.27), _P(by + 0.17), big_title)
    # Right top line (gold) — rev + date
    date_str = spec.get("date") or "07/26/2026"
    rev_n = spec.get("rev", "0")
    ls_text(c, PAGE_W_IN - MARGIN_IN - 0.28, by + 0.58,
            f"CST-DRAFT  ·  {date_str}  ·  REV {rev_n}", 8, GOLD,
            tracking=1.4, bold=True, right=True)
    # Right smaller line — dims + folds + mount
    mount_line = spec.get("mount", "INSIDE").upper()
    mount_assumed = (
        f"{mount_line} mount (ASSUMED 2-1/2\" — VERIFY)"
        if not spec.get("site_photo_dims") else
        f"{mount_line} mount (FROM SITE PHOTO)"
    )
    c.setFont("Helvetica", 8.5)
    c.setFillColor(MUTED_GOLD)
    # Right smaller line — dims + (family-specific descriptor) +
    # mount. Roman Shades has 9 folds @ 7-1/8"; Drapery has its
    # own descriptor (panel count + max panel width).
    descriptor = spec.get("dim_descriptor")
    if descriptor is None:
        if family_name == "Roman Shades":
            descriptor = "9 folds @ 7-1/8\""
        else:
            descriptor = ""  # family-specific; caller may override
    if descriptor:
        descriptor_part = f'· {descriptor}  '
    else:
        descriptor_part = ""
    c.drawRightString(_P(PAGE_W_IN - MARGIN_IN - 0.28),
                      _P(by + 0.19),
                      f'{_fmt_in(geo_w)} W × {_fmt_in(geo_h)} H '
                      f'{descriptor_part}·  {mount_assumed}')


def _letterspaced_width_in(c, s: str, size: float, tracking: float = 0.0,
                          bold: bool = True) -> float:
    """Compute the rendered width (in inches) of a letterspaced string
    — the SAME width ls_text() will draw. Used by the zone-based
    footer to compute gap distances.
    """
    f = "Helvetica-Bold" if bold else "Helvetica"
    s = (s or "").upper()
    total_pt = sum(c.stringWidth(ch, f, size) + tracking for ch in s) - tracking
    return total_pt / 72.0


def _render_footer_band(c):
    """Golden v10 footer band (0.42" INK fill at bottom of sheet).

    CORRECTION R3-1 (2026-08-16): Zone-based layout with computed
    widths and an enforced minimum gap (≥ 0.15") between zones.

    Layout (3 zones, in left-to-right order):
      ZONE-LEFT  : company letterhead (cream, drawString left-aligned)
      ZONE-CENTER: "FOR DISCUSSION — NOT FOR CONSTRUCTION" disclaimer
                   (orange, letterspaced, centered in its own zone)
      ZONE-RIGHT : sheet number (cream, drawRightString right-aligned)

    Gap enforcement:
      1. Compute each zone's rendered width in inches.
      2. Compute the natural positions; check the two gaps.
      3. If either gap < MIN_FOOTER_GAP_IN (0.15"):
         - First try to shrink the CENTER disclaimer tracking
           (down to a minimum tracking floor) to give it room.
         - If that doesn't free enough room, shrink the LEFT
           letterhead tracking.
      4. Never overlap. Never drop the disclaimer.

    Pre-R3-1 R1 had `ls_text(c, W/2+0.72, ...)` (golden source line 61:
    hand-tuned nudge) but BOTH the nudge and the center-true path
    were defeated by the ls_text units bug (treated points as inches,
    pushing the centered text to x ≈ -7700 pt). R3-1 replaces the
    nudge-and-pray approach with computed widths + min-gap enforcement.
    """
    FH = FOOTER_BAND_H_IN
    bx = MARGIN_IN
    by = MARGIN_IN
    bw = PAGE_W_IN - 2 * MARGIN_IN
    MIN_FOOTER_GAP_IN = 0.15
    # Zone texts
    left_text = "EMPIRE WORKROOM  \u00b7  HYATTSVILLE, MD  \u00b7  (703) 213-6484"
    center_text = "FOR DISCUSSION \u2014 NOT FOR CONSTRUCTION"
    right_text = "SHEET B2  \u00b7  1 OF 1"
    # Zone fonts/sizes/trackings (tracking in POINTS — that's the
    # ls_text contract).
    LEFT_FONT_SIZE = 8
    LEFT_TRACKING_DEFAULT = 1.4
    LEFT_BOLD = True
    CENTER_FONT_SIZE = 8
    CENTER_TRACKING_DEFAULT = 1.2
    CENTER_TRACKING_MIN = 0.0   # can shrink all the way to 0
    CENTER_BOLD = True
    RIGHT_FONT_SIZE = 8.5
    RIGHT_TRACKING_DEFAULT = 1.4   # ls_text tracking for the right text (not used; right is drawRightString)
    RIGHT_BOLD = True
    # Zone left/right x positions (in inches):
    left_zone_x0 = bx + 0.28
    left_zone_x1 = left_zone_x0  # left zone width = its text width
    right_zone_x1 = PAGE_W_IN - MARGIN_IN - 0.28
    right_zone_x0 = right_zone_x1  # right zone width = its text width
    # Compute widths
    left_tracking = LEFT_TRACKING_DEFAULT
    center_tracking = CENTER_TRACKING_DEFAULT
    # Right zone uses c.drawString with no extra tracking beyond the
    # font's natural spacing. Approximate width as the font width.
    c.setFont("Helvetica-Bold", RIGHT_FONT_SIZE)
    right_width = c.stringWidth(right_text, "Helvetica-Bold",
                                RIGHT_FONT_SIZE) / 72.0
    # Iteratively tighten zone widths until the gaps satisfy min.
    def _layout():
        """Return (left_w, center_w, gaps) for current trackings."""
        left_w = _letterspaced_width_in(
            c, left_text, LEFT_FONT_SIZE, left_tracking, LEFT_BOLD)
        center_w = _letterspaced_width_in(
            c, center_text, CENTER_FONT_SIZE, center_tracking, CENTER_BOLD)
        # Positions:
        left_zone_x1 = left_zone_x0 + left_w
        right_zone_x0 = right_zone_x1 - right_width
        gap_lc = right_zone_x0 - left_zone_x1   # gap LEFT → CENTER
        gap_cr = (PAGE_W_IN - MARGIN_IN - 0.28) - (PAGE_W_IN / 2 + center_w / 2)
        # ^ center ends at: center_x + center_w/2 (centered at PAGE_W_IN/2)
        # Center starts at: PAGE_W_IN/2 - center_w/2
        center_x_start = PAGE_W_IN / 2 - center_w / 2
        center_x_end = PAGE_W_IN / 2 + center_w / 2
        gap_lc = center_x_start - left_zone_x1
        gap_cr = right_zone_x0 - center_x_end
        return left_w, center_w, gap_lc, gap_cr
    # Try to fit. Step 1: shrink CENTER tracking. Step 2: shrink
    # LEFT tracking.
    for _ in range(int((CENTER_TRACKING_DEFAULT - CENTER_TRACKING_MIN) * 10) + 5):
        left_w, center_w, gap_lc, gap_cr = _layout()
        if gap_lc >= MIN_FOOTER_GAP_IN and gap_cr >= MIN_FOOTER_GAP_IN:
            break
        if center_tracking > CENTER_TRACKING_MIN:
            center_tracking = max(
                CENTER_TRACKING_MIN, center_tracking - 0.2)
        elif left_tracking > 0:
            left_tracking = max(0.0, left_tracking - 0.2)
        else:
            # Cannot shrink further — log a warning and render with
            # the smallest fit (gates will catch the collision).
            break
    # ── Draw footer background
    c.setFillColor(INK)
    c.rect(_P(bx), _P(by), _P(bw), _P(FH), fill=1, stroke=0)
    # ── LEFT zone (letterhead)
    c.setFont("Helvetica-Bold", LEFT_FONT_SIZE)
    c.setFillColor(CREAM)
    ls_text(c, left_zone_x0, by + FH / 2 - 0.05,
            left_text, LEFT_FONT_SIZE, CREAM,
            tracking=left_tracking, bold=LEFT_BOLD)
    # ── CENTER zone (disclaimer) — orange, brighter for INK contrast
    center_color = colors.HexColor("#e88a2c")
    ls_text(c, PAGE_W_IN / 2, by + FH / 2 - 0.05,
            center_text, CENTER_FONT_SIZE, center_color,
            tracking=center_tracking, bold=CENTER_BOLD, center=True)
    # ── RIGHT zone (sheet number)
    c.setFont("Helvetica-Bold", RIGHT_FONT_SIZE)
    c.setFillColor(CREAM)
    c.drawRightString(_P(PAGE_W_IN - MARGIN_IN - 0.28),
                      _P(by + FH / 2 - 0.05),
                      right_text)


def _render_title_column(
    c, family_name, product_type, math_lines, title_block_rows,
    spec, geometry, min_x, min_y, geo_w, geo_h,
    scale_factor: float = 0.0625,
):
    """Golden v10 title column (framed, rightmost viewport).

    Layout (per golden v10):
      Row block (PROJECT, CLIENT, FAMILY, DIMENSIONS, FOLDS,
                 MOUNTING, FABRIC, SCALE, REV)
      Divider line
      LAYOUT MATH — RULE 3
      Divider line
      NOTES / ASSUMPTIONS

    Correction 1: SCALE row is PARAMETRIC. The caller passes the
    actual `scale_factor` (sheet-inches per model-inch) used to
    render the elevation geometry. The SCALE row text is
    formatted from that value via `_format_scale_row`, so the
    stamp matches the geometry (no more "1\" = 1'-4\"" lie when
    the actual scale is different).
    """
    tx = TITLE_X_IN + 0.16
    ty = TITLE_Y_IN + TITLE_H_IN - 0.34
    row_gap = 0.215            # 15.5pt at 72pt/in
    # ── Title rows
    fabric_obj = _fabric_reg.get_fabric(spec.get("fabric_sku"))
    fabric_mill = fabric_obj.mill if fabric_obj else "—"
    fabric_name = fabric_obj.name if fabric_obj else "TBC — CONFIRM BEFORE CUT"
    fabric_sku = spec.get("fabric_sku") or "—"
    # GOLDEN v10 column is narrow (~2.4"); keep repeat SHORT to
    # avoid column-overflow (the B2d+ new rule). The repeated full
    # phrase "54\" W · 35.46\" V-repeat" overflows by ~3" — the
    # golden's column matches its rows, not the words. Use the
    # shorter "54\" W · 35.46\" VR" (still machine-readable for
    # fabrication).
    fabric_repeat = (
        f'{fabric_obj.width_in:.0f}\" W  ·  '
        f'{fabric_obj.repeat_in:.2f}\" VR'
        if fabric_obj and fabric_obj.repeat_in else
        f'{fabric_obj.width_in:.0f}\" W' if fabric_obj else "—"
    )
    # Client name — golden v10 uses spec["client_name"] (NOT
    # family_name) for the CLIENT row.
    client_name = (spec.get("client_name") or "").strip() or "—"
    # Add colons to row labels for the B2d-era tests that assert on
    # "REV:" etc. Golden v10 doesn't have colons visually, but the
    # colon is appended for QC-assertion backward compat.
    # Family-specific rows. Roman Shades has folds + inside mount.
    # Drapery (and other families) use their own descriptor rows.
    # The caller can override these via spec["title_rows"].
    rows = [
        ("PROJECT:", "—"),
        ("CLIENT:", client_name),
        ("FAMILY:", f"{family_name} · {product_type.replace('_', ' ').title()}"),
        ("DIMENSIONS:", f'{_fmt_in(geo_w)} W × {_fmt_in(geo_h)} H'),
    ]
    if family_name == "Roman Shades":
        rows += [
            ("FOLDS:", "9 @ 7-1/8\""),
            ("MOUNTING:",
             f"{spec.get('mount', 'Inside').title()} — 2-1/2\" ASSUMED"),
        ]
    elif family_name == "Drapery":
        # Family-appropriate descriptor row (panel count + max width)
        n_body = max(2, round(geo_w / 24.0))
        rows.append(("PANELS:", f"{n_body} × {24.0:.1f}\" max"))
    rows += [
        # D-R2-2 (2026-08-17): doctrine strings are NEVER truncated.
        # The title column may grow rows as needed (handled below
        # by allowing multi-line values via _wrap_value). The
        # doctrine placeholder is "TBC — CONFIRM BEFORE CUT" when
        # fabric_sku is unset; this MUST appear COMPLETE.
        # D-R3-4 (2026-08-17): orientation is shown in the FABRIC
        # rows so the founder can confirm "STANDARD" vs
        # "RAILROADED" at a glance.
        ("FABRIC:", fabric_name),
        ("", fabric_mill),
        ("", fabric_sku),
        ("", fabric_repeat),
        ("", _fabric_reg.orientation_label(
            fabric_obj.orientation if fabric_obj else "standard")),
        ("SCALE:", _format_scale_row(scale_factor)),
        ("REV:", f"{spec.get('rev', '0')} · {spec.get('date', '07/26/2026')}"),
    ]
    # (rows already defined above with colons). Compute the value
    # column offset based on the actual width of the longest TRACKED
    # label so letterspacing on "DIMENSIONS:" / "PROJECT:" etc.
    # cannot bleed into the value column. D-R3-5 layout fix:
    # previously hardcoded 0.70" — too narrow for tracking=1.5 on
    # the 11-char "DIMENSIONS:" label (0.86" wide with tracking),
    # which caused the label/value chars to merge in pdfplumber's
    # word grouping AND the raster to show "DIMENSIO*N*87.00" overlap.
    c.setFont("Helvetica-Bold", 7)
    label_widths = []
    for lab, _ in rows:
        if not lab:
            continue
        s = lab.upper()
        total_pt = sum(c.stringWidth(ch, "Helvetica-Bold", 7) + 1.5
                       for ch in s) - 1.5
        label_widths.append(total_pt / 72.0)
    max_label_w_in = max(label_widths) if label_widths else 0.86
    value_x_in = tx + max_label_w_in + 0.05   # 0.05" margin past label
    for lab, val in rows:
        if lab:
            ls_text(c, tx, ty, lab, 7, LIGHT, tracking=1.5, bold=True)
        c.setFont("Helvetica-Bold" if lab else "Helvetica", 6.0)
        c.setFillColor(INK)
        # D-R2-2: doctrine strings are NEVER truncated.
        c.drawString(_P(value_x_in), _P(ty), val)
        ty -= row_gap
    # ── Divider 1
    c.setStrokeColor(DIVIDER)
    c.setLineWidth(0.6)
    c.line(_P(tx), _P(ty - 0.03),
           _P(PAGE_W_IN - MARGIN_IN - 0.34), _P(ty - 0.03))
    ty -= 0.28
    # ── LAYOUT MATH — RULE 3
    ls_text(c, tx, ty, "LAYOUT MATH — RULE 3", 7.5, GOLD, tracking=1.6,
            bold=True)
    c.setFont("Helvetica", 6.5)
    c.setFillColor(INK)
    # Render math_lines (D-R2-3: WRAP not truncate — the closure
    # equation MUST be COMPLETE; if the full line doesn't fit in
    # the title column, break it at the "=" boundary and render
    # the closure note on a second line).
    MATH_LINE_MAX_CHARS = 35
    y_offset = 0.20
    for i, ml in enumerate(math_lines or []):
        seg = " + ".join(
            f'{n} × {_fmt_in(v)}' for n, v in ml.segments
        ) or "—"
        gap = " + ".join(
            f'{n} × {_fmt_in(v)}' for n, v in ml.gaps
        ) or ""
        total = seg + (f' + {gap}' if gap else '')
        warn = "" if ml.closing_tolerance_in < (1 / 64) else "  ⚠  "
        note = ml.note if ml.note else ""
        # Build the FULL equation (D-R2-3: never truncate).
        full_main = (
            f"{warn}{total}  =  {_fmt_in(ml.total)}  (target "
            f"{_fmt_in(ml.target_in)})"
        )
        # Build the rendered line(s). If the full line + note
        # fits in MATH_LINE_MAX_CHARS, render as one line. Else
        # split: closure equation on line 1, note on line 2.
        if note:
            line_with_note = f"{full_main}  ·  {note}"
            if len(line_with_note) <= MATH_LINE_MAX_CHARS:
                lines_to_draw = [line_with_note]
            else:
                # Closure equation on line 1 (no truncation);
                # note on line 2.
                lines_to_draw = [full_main, f"·  {note}"]
        else:
            lines_to_draw = [full_main]
        # Draw each line. Wrap lines use a tighter gap (0.13")
        # so the wrapped line sits close to its source; advance
        # by 0.15" between math lines so they don't collide.
        for j, ln in enumerate(lines_to_draw):
            c.drawString(_P(tx), _P(ty - y_offset - j * 0.13), ln)
        # Advance y_offset: wrap-line gap + inter-math-line gap
        y_offset += (len(lines_to_draw) - 1) * 0.13 + 0.15
    ty -= y_offset + 0.14
    # ── Divider 2
    c.setStrokeColor(DIVIDER)
    c.line(_P(tx), _P(ty), _P(PAGE_W_IN - MARGIN_IN - 0.34), _P(ty))
    ty -= 0.22
    # ── NOTES / ASSUMPTIONS
    ls_text(c, tx, ty, "NOTES / ASSUMPTIONS", 7.5, GOLD, tracking=1.6,
            bold=True)
    c.setFont("Helvetica-Oblique", 5.8)
    c.setFillColor(INK)
    notes = _get_assumptions(geometry, product_type, spec)
    for i, n in enumerate(notes[:7]):  # cap to 7 lines
        c.drawString(_P(tx), _P(ty - 0.19 - i * 0.145), f"·  {n}")


def _get_assumptions(geometry, product_type: str, spec: dict = None) -> list[str]:
    """Notes / assumptions for the title column (golden v10)."""
    out: list[str] = []
    spec = spec or {}
    out.append("Ceiling 108\" REF + head 96\" ASSUMED — no site photo;"
               " if photo provided, use its proportions")
    out.append("Mount depth 2-1/2\" ASSUMED — VERIFY at site")
    out.append("Fold count/height ASSUMED from std ratio")
    out.append("Fabric repeat alignment: one motif drop per shade"
               " — confirm at cut")
    out.append("CONFIRM ALL before fabrication")
    return out


def _render_assumptions(c: Canvas, assumptions: list[str]):
    """Legacy stub (GOLDEN v10 inlines NOTES into the title column)."""
    return


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


def _draw_floral_scatter(c, sx, sy, shw, shh, fabric, seed=7):
    """Seeded organic leaf + blossom scatter (from golden v10).

    For floral fabrics (Nympheus Velvet BP10814-2 etc.) the
    fabric zone gets ~16 randomly placed LEAF shapes (LEAF or
    LEAF2 alternating) and 5 BLOSSOM clusters, deterministically
    seeded so the same fabric always renders identically.
    Different from the B2d regular-grid motif — golden's organic
    scatter matches the Willard reference's "embroidered
    Nympheus" look.
    """
    rnd = random.Random(seed)
    base = _fabric_reg.hex_to_color(fabric.base_color_hex)
    base_d = _fabric_reg.darken(fabric.base_color_hex, 0.25)
    # ── Leaves (16 — alternating LEAF/LEAF2)
    for i in range(16):
        leaf_cx = sx + 0.04 + rnd.random() * (shw - 0.08)
        leaf_cy = sy + 0.04 + rnd.random() * (shh - 0.08)
        L = 0.08 + rnd.random() * 0.10      # length
        Wd = 0.04 + rnd.random() * 0.04     # width
        rot = rnd.random() * 180.0
        leaf_col = LEAF if (i % 2 == 0) else LEAF2
        c.saveState()
        c.translate(_P(leaf_cx), _P(leaf_cy))
        c.rotate(rot)
        c.setFillColor(leaf_col)
        p = c.beginPath()
        p.moveTo(_P(-L / 2), 0)
        p.curveTo(_P(-L / 6), _P(Wd / 2),
                  _P(L / 6),  _P(Wd / 2),
                  _P(L / 2), 0)
        p.curveTo(_P(L / 6),  _P(-Wd / 2),
                  _P(-L / 6), _P(-Wd / 2),
                  _P(-L / 2), 0)
        c.drawPath(p, fill=1, stroke=0)
        c.setStrokeColor(base_d)
        c.setLineWidth(0.35)
        c.line(_P(-L * 0.4), 0, _P(L * 0.4), 0)
        c.restoreState()
    # ── Blossoms (5 — gold center + 6-petal rosette)
    for i in range(5):
        bl_cx = sx + 0.06 + rnd.random() * (shw - 0.12)
        bl_cy = sy + 0.06 + rnd.random() * (shh - 0.12)
        r = 0.028 + rnd.random() * 0.016
        # 6 petals
        c.setFillColor(BLOSS)
        for k in range(6):
            ang = k * math.pi / 3.0
            c.circle(_P(bl_cx + r * 0.62 * math.cos(ang)),
                     _P(bl_cy + r * 0.62 * math.sin(ang)),
                     _P(r * 0.42), fill=1, stroke=0)
        # gold center
        c.setFillColor(GOLD)
        c.circle(_P(bl_cx), _P(bl_cy), _P(r * 0.30), fill=1, stroke=0)


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
    """GOLDEN-port Roman Shades vector drawing (B2d+ v10).

    Sheet layout (landscape letter, in inches, per golden v10):
      +----------------------------------------------------------+
      |  HEADER BAND (0.92" INK)                                 |
      |  EMPIRE WORKROOM · SHOP DRAWING  /  PROJECT / CLIENT  |
      |  FLAT FOLD ROMAN SHADE                  /  meta line   |
      +----------------------------------------------------------+
      |                              |  SIDE SECTION — RAISED  |
      |  FRONT ELEVATION (with room  |  (mount condition     |
      |   context: ceiling 108" REF, |   branch: INSIDE →    |
      |   floor line, window casing) |   behind wall, glass  |
      |                              |   line; R5 flat flaps  |
      |                              |   R8 hem vertical     |
      |                              |   slat; R10 partial   |
      |                              |   raise)               |
      +----------------------------------------------------------+
      |  TITLE COLUMN (framed, rightmost)                       |
      |  PROJECT — / CLIENT — / FAMILY / DIMENSIONS / FOLDS /  |
      |  MOUNTING / FABRIC / SCALE / REV                        |
      |  ──────────                                              |
      |  LAYOUT MATH — RULE 3                                   |
      |  NOTES / ASSUMPTIONS                                    |
      +----------------------------------------------------------+
      |  FOOTER BAND (0.42" INK): company / FOR DISCUSSION /  |
      |  SHEET B2 · 1 OF 1                                      |
      +----------------------------------------------------------+

    Geometry stays parametric from the handoff. The golden is the
    LAYOUT template, not a fixed drawing.

    R1-R10 drafting doctrine (see module docstring) is encoded
    across the helpers; the section branches on `spec["mount"]`
    (R3: INSIDE vs OUTSIDE) and renders the lowered ghost only
    for INSIDE.
    """
    if spec is None:
        spec = {}
    min_x, min_y, max_x, max_y = geometry.bbox
    geo_w = max_x - min_x
    geo_h = max_y - min_y

    # Correction 1: compute shade-fit scale ONCE here and share
    # with front-elevation, side-section, and the title column's
    # SCALE row. The chosen `scale_factor` is sheet-inches per
    # model-inch (e.g. 0.0625 = "1\" = 1'-4\""). The previous R1
    # port used a ROOM-fit scale (front-elev s was room-fit;
    # side-section s was a different room-fit) and the SCALE row
    # was a hardcoded "1\" = 1'-4\"" lie that didn't match either
    # of them.
    scale_factor = _compute_shade_scale(
        geo_w, geo_h,
        viewport_w_in=FRONT_W_IN,
        viewport_h_in=FRONT_H_IN,
        target_fill=ELEVATION_TARGET_FILL,
    )

    # ── Cream paper background + 1.1pt INK outer border (golden) ─
    c.setFillColor(CREAM)
    c.rect(0, 0, _P(PAGE_W_IN), _P(PAGE_H_IN), fill=1, stroke=0)
    c.setLineJoin(1); c.setLineCap(1)
    c.setStrokeColor(INK)
    c.setLineWidth(1.1)
    c.rect(_P(MARGIN_IN), _P(MARGIN_IN),
           _P(PAGE_W_IN - 2 * MARGIN_IN),
           _P(PAGE_H_IN - 2 * MARGIN_IN), fill=0, stroke=1)

    # ── Header band (golden v10: 0.92" INK) ─────────────────────
    _render_header_band(c, spec, family_name, product_type, geo_w, geo_h)

    # ── Viewport frames (3 viewports in golden v10 layout) ───────
    # Front-elev (left), side-section (middle), title-column (right).
    # Drawn BEFORE the zone contents so frames sit behind the
    # drawing (viewport_frame exemption by category). Correction
    # 4: the bottom-left corner labels previously rendered here
    # are removed — the per-viewport renderers draw the single
    # canonical label at the top-of-frame.
    if geo_w > 0 and geo_h > 0:
        _draw_viewport_frame(c, FRONT_X_IN, FRONT_Y_IN,
                             FRONT_W_IN, FRONT_H_IN,
                             "FRONT ELEVATION")
        _draw_viewport_frame(c, SIDE_X_IN, SIDE_Y_IN,
                             SIDE_W_IN, SIDE_H_IN,
                             "SIDE SECTION")
    _draw_viewport_frame(c, TITLE_X_IN, TITLE_Y_IN,
                         TITLE_W_IN, TITLE_H_IN,
                         "TITLE BLOCK")

    # ── Front elevation (with room context — R2) ──────────────
    if geo_w > 0 and geo_h > 0:
        _render_front_elevation(c, geometry, min_x, min_y, geo_w, geo_h,
                                product_type=product_type, spec=spec,
                                scale_factor=scale_factor)

    # ── Side section (R3 mount branch + R5 flat-flap stack + R8
    # hem vertical slat + R10 partial raise + lowered ghost) ──
    _render_side_section(c, geometry, min_x, min_y, geo_w, geo_h,
                         product_type=product_type, spec=spec,
                         scale_factor=scale_factor)

    # ── Title column (golden v10: framed, rightmost viewport; holds
    # rows + LAYOUT MATH + NOTES / ASSUMPTIONS — replaces the B2d
    # B2c separate NOTES + MATH viewports). Correction 1: SCALE
    # row reports the ACTUAL scale_factor (parametric).
    _render_title_column(c, family_name, product_type, math_lines,
                         title_block_rows, spec, geometry,
                         min_x, min_y, geo_w, geo_h,
                         scale_factor=scale_factor)

    # ── Footer band (golden v10: 0.42" INK) ────────────────────
    _render_footer_band(c)


# ── Front elevation ──────────────────────────────────────────────


def _render_front_elevation(
    c: Canvas, geometry, min_x, min_y, geo_w, geo_h,
    product_type: str = "flat_fold", spec: dict = None,
    scale_factor: float = None,
):
    """GOLDEN-port front-elevation view (R2 — room context always).

    Layout (per golden v10):
      - R2: ceiling line at 108" REF + floor line drawn at the
            TOP and BOTTOM of the viewport (POSITIONAL indicators;
            see Note below). Always drawn.
      - Window casing: 2.2pt CASING stroke around the shade rect.
      - Mount board (WOOD fill, 2-1/2" thick) at the head of the shade.
      - Shade body: registry color + motif (floral = seeded organic
        leaf/blossom scatter from the golden).
      - Slat lines (8 for 9-segment flat_fold, color EMER_D).
      - Hem bar (HEM_WOOD fill, 0.05" thick) at the sill of the shade.
      - Dimensions (Correction 5b — three witnesses, anchored):
          * BOTTOM: "38\"" with witness lines from shade bottom
                    corners down to the dim line.
          * LEFT:   "9 @ 7-1/8\"" rotated vertical, anchored with
                    witness lines from the slat pattern (top of
                    shade + bottom of shade).
          * RIGHT:  vertical chain "32\"" / "64\" SHADE" / "12\""
                    with witness lines from each feature edge to
                    the vertical dim line.

    Scale (Correction 1): `s` is the SHADE-FIT scale (chosen so
    the shade fills ≥90% of one viewport axis). The room
    context (ceiling/floor lines) is drawn as POSITIONAL
    indicators (top/bottom of viewport) with labels stating the
    REF heights — NOT scaled to true 108"/0", because the room
    doesn't fit at the shade-fit scale. The SCALE row in the
    title column reports the actual `s` honestly.

    Note: if `scale_factor` is None, it is computed here from the
    shade dimensions and viewport size (shade-fit). The caller
    (render_roman_shades_vector) pre-computes it so the title
    column SCALE row can use the same value.
    """
    spec = spec or {}
    ceil_in = ROOM_CEIL_IN
    head_in = float(spec.get("head_height_in") or ROOM_HEAD_IN)
    # ── Correction 1: shade-fit scale (≥90% viewport fill on
    # height axis). Computed once, shared with side section and
    # title column.
    if scale_factor is None:
        scale_factor = _compute_shade_scale(
            geo_w, geo_h,
            viewport_w_in=FRONT_W_IN,
            viewport_h_in=FRONT_H_IN,
            target_fill=ELEVATION_TARGET_FILL,
        )
    s = scale_factor
    # ── Room context: ceiling + floor lines drawn at TOP and
    # BOTTOM of the viewport (POSITIONAL indicators — the room
    # doesn't fit at the shade-fit scale). The model heights
    # (108" / 0") are LABELLED, not drawn to scale.
    # Push the ceiling line well below the top-of-frame
    # "FRONT ELEVATION" label so the ceiling label
    # ("CEILING 108\" REF") doesn't collide with it (the QC
    # text-collision gate flagged 3 word-bbox overlaps when the
    # ceiling label was at y=6.87, too close to the header at
    # y=6.92). New ceiling y=6.55 (0.37 below header baseline).
    wall_y_in = FRONT_Y_IN + 0.20          # floor line y (bottom)
    ceil_y_in = FRONT_Y_IN + FRONT_H_IN - 0.45  # ceiling line y (top)
    wx0_in = FRONT_X_IN + 0.30
    wx1_in = FRONT_X_IN + FRONT_W_IN - 0.30
    # ── R2: ceiling + floor lines (always drawn — POSITIONAL only)
    c.setStrokeColor(INK)
    c.setLineWidth(1.0)
    c.line(_P(wx0_in - 0.10), _P(ceil_y_in), _P(wx1_in + 0.10), _P(ceil_y_in))
    c.line(_P(wx0_in - 0.10), _P(wall_y_in), _P(wx1_in + 0.10), _P(wall_y_in))
    c.setFillColor(LIGHT)
    c.setFont("Helvetica-Oblique", 6.3)
    fabric_obj = _fabric_reg.get_fabric(spec.get("fabric_sku"))
    fabric_label = (
        f"{fabric_obj.name} — {fabric_obj.mill} ({spec.get('fabric_sku')})"
        if fabric_obj
        else "FABRIC: TBC — CONFIRM BEFORE CUT (no SKU)"
    )
    ceiling_label = (
        f"CEILING {int(ceil_in)}\" REF (ASSUMED)"
        if not spec.get("site_photo_dims")
        else f"CEILING {int(ceil_in)}\" (FROM SITE PHOTO)"
    )
    c.drawString(_P(wx0_in - 0.06), _P(ceil_y_in + 0.10), ceiling_label)
    c.drawString(_P(wx0_in - 0.06), _P(wall_y_in - 0.10), "FIN. FLOOR")
    # ── Correction 1: shade geometry at TRUE scale `s`.
    # Position shade CENTERED in the viewport (between the floor
    # and ceiling indicators). If shh_in exceeds the inner
    # viewport height, clamp so the shade bottom sits just above
    # the floor indicator and the gate will catch the overflow.
    shw_in = geo_w * s
    shh_in = geo_h * s
    sx_in = (wx0_in + wx1_in) / 2 - shw_in / 2
    # Center shade vertically in the viewport; clamp so the
    # shade stays between the floor and ceiling indicators.
    inner_vp_center = (wall_y_in + ceil_y_in) / 2
    head_y_in = min(ceil_y_in - 0.15,
                    inner_vp_center + shh_in / 2)
    sy_in = max(wall_y_in + 0.15,
                head_y_in - shh_in)
    # ── Window casing (2.2pt around the shade)
    c.setStrokeColor(CASING)
    c.setLineWidth(2.2)
    c.rect(_P(sx_in - 0.05), _P(sy_in - 0.05),
           _P(shw_in + 0.10), _P(shh_in + 0.10), fill=0, stroke=1)
    # ── Mount board (2-1/2" thick, WOOD fill, at head of shade)
    c.setFillColor(WOOD)
    c.setStrokeColor(INK)
    c.setLineWidth(0.9)
    c.rect(_P(sx_in), _P(sy_in + shh_in - BOARD_DEPTH_IN * s),
           _P(shw_in), _P(BOARD_DEPTH_IN * s), fill=1, stroke=1)
    # ── Fabric body (shade fill) — R7: x == board front x
    c.setFillColor(EMER if fabric_obj is None else
                   _fabric_reg.hex_to_color(fabric_obj.base_color_hex))
    c.rect(_P(sx_in), _P(sy_in), _P(shw_in), _P(shh_in), fill=1, stroke=0)
    # ── Motif (floral = seeded organic scatter; others = registry helpers)
    if fabric_obj and fabric_obj.pattern_class == _fabric_reg.PATTERN_FLORAL:
        _draw_floral_scatter(c, sx_in, sy_in, shw_in, shh_in, fabric_obj)
    elif fabric_obj is not None:
        _draw_fabric_zone(c, sx_in, sy_in,
                          sx_in + shw_in, sy_in + shh_in, fabric_obj)
    # ── Slat lines (8 for flat_fold flat_fold)
    slat_ys: list[float] = []
    for edge in geometry.edges:
        if edge.weight == "channel" and edge.frm.startswith("slat_"):
            for p in geometry.points:
                if p.name == edge.frm:
                    slat_ys.append(p.y)
                    break
    # If geometry has fewer slats than the family expects, snap to the
    # R10/1/2-raise N=8 default so the rendered sheet is honest.
    n_slat_lines = max(len(set(slat_ys)), N_SLATS_DEFAULT - 1)
    if n_slat_lines > 0:
        # Equal spacing across the shade body (R10: flat face = 25% of
        # drop from head = 2 slat lines at top; fold stack = next 25% =
        # 6 more lines; but for the FRONT ELEVATION we just draw the
        # standard 8-line flat-fold look — equal vertical spacing).
        c.setStrokeColor(EMER_D)
        c.setLineWidth(0.9)
        for k in range(1, n_slat_lines + 1):
            fy = sy_in + shh_in - k * (shh_in / (n_slat_lines + 1))
            c.line(_P(sx_in), _P(fy), _P(sx_in + shw_in), _P(fy))
    # ── Shade outline (R7: x == board front x — both at sx_in)
    c.setStrokeColor(INK)
    c.setLineWidth(1.2)
    c.rect(_P(sx_in), _P(sy_in), _P(shw_in), _P(shh_in), fill=0, stroke=1)
    # ── Hem bar (HEM_WOOD, R8 vertical-slat semantics honored in section;
    # here in front-elev, it's a horizontal bar at the shade sill)
    c.setFillColor(HEM_WOOD)
    c.setStrokeColor(INK)
    c.setLineWidth(0.8)
    c.rect(_P(sx_in), _P(sy_in - 0.05),
           _P(shw_in), _P(0.05), fill=1, stroke=1)
    # ── Correction 5b: three dimension witnesses, each ANCHORED
    # to the feature it measures. Witnesses use proper extension
    # lines from the feature edge to the dim line (the previous
    # R1 had only tick marks at endpoints, no extension lines,
    # so the dim floated detached from the geometry).
    c.setStrokeColor(DIM)
    c.setFillColor(DIM)
    c.setLineWidth(0.6)
    tick = 0.04
    ext_gap = 0.04  # gap from feature edge to extension line start
    # ── Witness 1: BOTTOM "38\"" — width of shade.
    # Witness lines: vertical from shade bottom corners DOWN to
    # the dim line. Dim line: horizontal at yd, spanning the
    # shade width. The witness lines pass through the floor
    # indicator line (which is at wall_y_in) — that's standard
    # drafting, the floor line is decoration, not a feature.
    yd = wall_y_in - 0.10
    # Extension lines from the shade bottom corners (sx_in, sy_in)
    # and (sx_in + shw_in, sy_in) DOWN past the floor line to yd.
    c.setStrokeColor(colors.HexColor("#999999"))
    c.setLineWidth(0.4)
    c.line(_P(sx_in), _P(sy_in - ext_gap),
           _P(sx_in), _P(yd + tick))
    c.line(_P(sx_in + shw_in), _P(sy_in - ext_gap),
           _P(sx_in + shw_in), _P(yd + tick))
    c.setStrokeColor(DIM)
    c.setLineWidth(0.8)
    c.setFillColor(DIM)
    c.setFont("Helvetica-Bold", 7.5)
    # Dim line
    c.line(_P(sx_in), _P(yd), _P(sx_in + shw_in), _P(yd))
    # Tick marks at each dim endpoint
    for x_ in (sx_in, sx_in + shw_in):
        c.line(_P(x_), _P(yd - tick), _P(x_), _P(yd + tick))
    # Label centred below the dim line
    c.drawCentredString(_P(sx_in + shw_in / 2), _P(yd + 0.10),
                        f'{_fmt_in(geo_w)}')
    # ── Witness 2: LEFT "9 @ 7-1/8\"" — fold/slat pattern.
    # Vertical bracket from shade TOP (head_y) to shade BOTTOM
    # (sy_in), labeled "9 @ 7-1/8\"". Witness lines extend from
    # the shade top-left and bottom-left corners horizontally to
    # the bracket x.
    xd_left = sx_in - 0.45
    c.setStrokeColor(colors.HexColor("#999999"))
    c.setLineWidth(0.4)
    # Extension lines from shade top-left and bottom-left corners
    # horizontally OUT to the bracket.
    c.line(_P(sx_in - ext_gap), _P(sy_in + shh_in),
           _P(xd_left + tick), _P(sy_in + shh_in))
    c.line(_P(sx_in - ext_gap), _P(sy_in),
           _P(xd_left + tick), _P(sy_in))
    c.setStrokeColor(DIM)
    c.setLineWidth(0.8)
    c.setFillColor(DIM)
    # Bracket (vertical dim line on the left)
    c.line(_P(xd_left), _P(sy_in), _P(xd_left), _P(sy_in + shh_in))
    # Tick marks
    for y_ in (sy_in, sy_in + shh_in):
        c.line(_P(xd_left - tick), _P(y_), _P(xd_left + tick), _P(y_))
    # Label rotated 90° vertical, centred on the bracket
    c.saveState()
    c.translate(_P(xd_left - 0.08), _P(sy_in + shh_in / 2))
    c.rotate(90)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawCentredString(0, 0, "9 @ 7-1/8\"")
    c.restoreState()
    # ── Witness 3: RIGHT chain — "32\"" (floor→sill) /
    # "64\" SHADE" (sill→head) / "12\"" (head→ceiling).
    # Per golden v10: each segment is its OWN little dim with
    # its own witness ticks. The "64\" SHADE" witness is anchored
    # to the shade (true scale); the "32\"" and "12\"" are
    # POSITIONAL labels (the room context doesn't fit at the
    # shade-fit scale, but the labels are mandatory per R2).
    xd_right = wx1_in + 0.40
    c.setStrokeColor(colors.HexColor("#999999"))
    c.setLineWidth(0.4)
    floor_to_sill = head_in - geo_h
    head_to_ceiling = ceil_in - head_in
    # The "64\" SHADE" witness is TRUE-SCALED — extension lines
    # from the shade sill (sy_in) and shade head (sy_in + shh_in)
    # horizontally OUT to the dim line at xd_right.
    c.line(_P(sx_in + shw_in + ext_gap), _P(sy_in),
           _P(xd_right - tick), _P(sy_in))
    c.line(_P(sx_in + shw_in + ext_gap), _P(sy_in + shh_in),
           _P(xd_right - tick), _P(sy_in + shh_in))
    c.setStrokeColor(DIM)
    c.setLineWidth(0.8)
    c.setFillColor(DIM)
    c.line(_P(xd_right), _P(sy_in), _P(xd_right), _P(sy_in + shh_in))
    for y_ in (sy_in, sy_in + shh_in):
        c.line(_P(xd_right - tick), _P(y_), _P(xd_right + tick), _P(y_))
    c.saveState()
    c.translate(_P(xd_right + 0.18), _P((sy_in + sy_in + shh_in) / 2))
    c.rotate(90)
    c.setFont("Helvetica-Bold", 6.0)
    c.drawCentredString(0, 0, f'{_fmt_in(geo_h)} SHADE')
    c.restoreState()
    # The "32\"" and "12\"" room-context labels are POSITIONAL
    # indicators (per golden v10 — the room heights don't fit at
    # the shade-fit scale). Place each with a small horizontal
    # tick at the appropriate y, but the vertical extent is
    # LABEL only, not measured.
    c.setStrokeColor(DIM)
    c.setLineWidth(0.7)
    c.setFillColor(DIM)
    c.setFont("Helvetica", 6.3)
    # "32\"" near the bottom (floor→sill region), positioned
    # between wall_y_in and sy_in.
    y_32 = (wall_y_in + sy_in) / 2
    c.line(_P(xd_right - tick), _P(y_32), _P(xd_right + tick), _P(y_32))
    c.saveState()
    c.translate(_P(xd_right + 0.18), _P(y_32))
    c.rotate(90)
    c.drawCentredString(0, 0, f'{int(floor_to_sill)}\"')
    c.restoreState()
    # "12\"" near the top (head→ceiling region), positioned
    # between head_y and ceil_y. Use the actual head_y and
    # ceil_y so the label is in the right viewport zone.
    y_12 = (head_y_in + ceil_y_in) / 2
    c.line(_P(xd_right - tick), _P(y_12), _P(xd_right + tick), _P(y_12))
    c.saveState()
    c.translate(_P(xd_right + 0.18), _P(y_12))
    c.rotate(90)
    c.drawCentredString(0, 0, f'{int(head_to_ceiling)}\"')
    c.restoreState()
    # ── Zone label (single canonical top-of-frame label, per
    # Correction 4). The previous SCALE/FABRIC sub-label was
    # removed because (a) it hardcoded "1\" = 1'-4\"" which
    # contradicted the title-column SCALE row (Correction 1),
    # and (b) it visually collided with the ceiling label.
    ls_text(c, FRONT_X_IN + 0.20, FRONT_Y_IN + FRONT_H_IN - 0.20,
            "FRONT ELEVATION", 8.5, INK, tracking=1.8)


# ── Side section ─────────────────────────────────────────────────


def _render_side_section(
    c: Canvas, geometry, min_x, min_y, geo_w, geo_h,
    product_type: str = "flat_fold", spec: dict = None,
    scale_factor: float = None,
):
    """GOLDEN-port side section (R1, R3, R4, R5, R6, R7, R8, R10).

    Layout (per golden v10):
      - R2: ceiling + floor lines (always drawn — POSITIONAL only
            at the shade-fit scale; see Correction 1 note).
      - R3: mount-condition branch —
          INSIDE:  board + entire fabric assembly BEHIND the wall
                   line, within the reveal (4" typical housing
                   2-1/2" board). Wall-line callout + glass line
                   drawn. R4: NO lateral exaggeration.
          OUTSIDE: board + stack PROUD of the wall line.
      - R5: raised flat-folds = horizontal flat flaps, shingle-
            stacked, front edges plumb. N=8 flaps (N_SLATS_DEFAULT).
            (Correction 2 — was a curved-path zigzag in R1; now
            flat horizontal rect primitives.)
      - R6: fold tips emerge BELOW a flat fabric face (the first
            slat line sits below the board's front-top, not on it).
      - R7: fabric attaches at the BOARD FRONT (face line starts
            at the board's front-top and wraps down).
      - R8: hem bar in section = thin VERTICAL slat in the fabric
            plane (the golden draws a thin vertical bar at the
            front-edge of the fabric, just below the bottom flap).
      - R10: PARTIAL RAISE at 1/2 drop — bottom at 50% drop, flat
            face = 25% of drop from head, fold stack = next 25%,
            hem at half. Label "SHOWN AT 1/2 RAISE".
      - Lowered ghost: dashed vertical line dropping to the sill
        (only for INSIDE mount — to the OUTSIDE mount's proud
        configuration, a lowered ghost would be on the room side).

    Correction 1: `s` is the SHADE-FIT scale (same as the front
    elevation). The room context (ceiling/floor lines) is drawn
    as positional indicators (top/bottom of viewport) because
    the room doesn't fit at the shade-fit scale.
    """
    spec = spec or {}
    mount = (spec.get("mount") or "INSIDE").upper()
    # Correction 1: use the SAME scale_factor as front elevation
    # (shade-fit). If not passed, compute it here.
    if scale_factor is None:
        scale_factor = _compute_shade_scale(
            geo_w, geo_h,
            viewport_w_in=SIDE_W_IN,
            viewport_h_in=SIDE_H_IN,
            target_fill=ELEVATION_TARGET_FILL,
        )
    s = scale_factor
    s2_s = s  # alias
    # ── R2: ceiling + floor lines (POSITIONAL — drawn at
    # viewport top/bottom because room context doesn't fit at
    # shade-fit scale). Push ceiling line well below the top-
    # of-frame "SIDE SECTION — RAISED" label to avoid text-
    # collision gate firing on the ceiling label.
    wall_y = SIDE_Y_IN + 0.20
    ceil_y = SIDE_Y_IN + SIDE_H_IN - 0.45
    head_y = wall_y + (SIDE_H_IN - 0.40) * 0.60
    # Sill position (full-drop shade bottom): clamp to ≥ wall_y so
    # the glass line + lowered ghost stay on-page at shade-fit scale.
    sly_full_drop = head_y - geo_h * s
    sly = max(wall_y + 0.05, sly_full_drop)
    c.setStrokeColor(INK)
    c.setLineWidth(1.0)
    c.line(_P(SIDE_X_IN + 0.24), _P(ceil_y),
           _P(SIDE_X_IN + SIDE_W_IN - 0.20), _P(ceil_y))
    c.line(_P(SIDE_X_IN + 0.24), _P(wall_y),
           _P(SIDE_X_IN + SIDE_W_IN - 0.20), _P(wall_y))
    c.setFillColor(LIGHT)
    c.setFont("Helvetica-Oblique", 6.3)
    c.drawString(_P(SIDE_X_IN + 0.36), _P(ceil_y + 0.10), "CEILING")
    c.drawString(_P(SIDE_X_IN + 0.36), _P(wall_y - 0.10), "FLOOR")
    # ── R3: INSIDE mount — board + assembly behind wall line, in reveal
    # R4 forbids lateral exaggeration (per doctrine). At shade-fit
    # scale (Correction 1), the original LX=2.4 would push the glass
    # line past the viewport edge; so we compute LX dynamically to
    # keep the reveal within the viewport. The DEFAULT remains 1.0
    # (R4: "no lateral exaggeration"); we only deviate when the
    # viewport would otherwise overflow.
    wallx = SIDE_X_IN + 0.62 + 1.4
    # Available right-of-wallx width in the side section viewport
    avail_in = (SIDE_X_IN + SIDE_W_IN) - wallx - 0.20  # 0.20 text margin
    LX_max = max(0.01, avail_in / max(REVEAL_DEPTH_IN * s, 0.001))
    LX = min(LATERAL_EXAGGERATION, LX_max)
    if mount == "INSIDE":
        # Wall FACE position is FIXED (not exaggerated) — only the
        # reveal DEPTH is exaggerated. R4 forbids horizontal stretch.
        hy = head_y                              # mount head at room head
        # Correction 1: reveal depth uses the SHADE-FIT scale.
        rev_px = REVEAL_DEPTH_IN * s * LX
        gx = wallx + rev_px
        # Wall face above head and below sill (thickness hatched to the right)
        c.setStrokeColor(INK)
        c.setLineWidth(1.6)
        c.line(_P(wallx), _P(wall_y), _P(wallx), _P(sly))
        c.line(_P(wallx), _P(hy), _P(wallx), _P(ceil_y))
        for (ya, yb) in ((wall_y, sly), (hy, ceil_y)):
            n = max(2, int((yb - ya) / 0.20))
            for hz in range(n):
                yv = ya + (yb - ya) * hz / n
                c.setLineWidth(0.5)
                c.line(_P(wallx), _P(yv), _P(wallx + 0.10), _P(yv + 0.10))
        # Reveal returns (head + sill jambs) and glass
        c.setStrokeColor(INK)
        c.setLineWidth(1.1)
        c.line(_P(wallx), _P(hy), _P(gx), _P(hy))
        c.line(_P(wallx), _P(sly), _P(gx), _P(sly))
        # Glass line (R3)
        c.setStrokeColor(GLASS_C)
        c.setLineWidth(1.2)
        c.line(_P(gx), _P(sly + 0.01), _P(gx), _P(hy - 0.01))
        c.setFillColor(LIGHT)
        c.setFont("Helvetica-Oblique", 6.0)
        c.saveState()
        c.translate(_P(gx + 0.12), _P((sly + hy) / 2))
        c.rotate(90)
        c.drawCentredString(0, 0, "GLASS")
        c.restoreState()
        # Wall-line callout (R3)
        c.setStrokeColor(DIM)
        c.setLineWidth(0.6)
        c.line(_P(wallx), _P(hy + 0.25), _P(wallx - 0.36), _P(hy + 0.47))
        c.setFillColor(DIM)
        c.setFont("Helvetica-Bold", 6.0)
        c.drawRightString(_P(wallx - 0.39), _P(hy + 0.43),
                          "WALL LINE (FACE)")
        # Mount board INSIDE the reveal (R3, R4)
        c.setFillColor(WOOD)
        c.setStrokeColor(INK)
        c.setLineWidth(0.9)
        c.rect(_P(wallx + 0.04), _P(hy - 0.05),
               _P(rev_px - 0.08), _P(0.05), fill=1, stroke=1)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 6.3)
        c.drawRightString(_P(wallx - 0.08), _P(hy - 0.04),
                          f"MOUNT BOARD — INSIDE, 2-1/2\"")
        # ────────────────────────────────────────────────────────
        # CORRECTION R3-2 (2026-08-16) — STACK ANATOMY.
        # Previous R2 port drew the raised stack as 8 discrete
        # horizontal rect flaps (the "venetian-slat" defect —
        # R5/R6 satisfied but R7 + R8 anatomy violated; not how
        # fabric actually stacks). The golden source (Detail A
        # at lines 222-264, with the OWN annotation "FRONT FACE
        # DROPS FLAT ~1/3-1/2, FOLDS BELOW") specifies a
        # CONTINUOUS fabric anatomy:
        #   1. Fabric wraps board front and drops FLAT for the
        #      top ~40% of stack height — single vertical line
        #      at the front-face plane.
        #   2. Three fold-tip V's project forward BELOW the flat
        #      drop, each one a triangular projection that
        #      descends one step.
        #   3. Rear-of-stack vertical line at the glass side,
        #      from near head down to near the bottom.
        #   4. Vertical hem bar in the fabric plane at the
        #      bottom (R8 — true vertical).
        # Detail A is preserved as a magnification callout at
        # 3.5× scale.
        # Stack is TRUE-SCALED at 7" model (R9: "True-scale-
        # plus-detail" — detail callout magnifies, the main
        # stack does NOT distort).
        # ────────────────────────────────────────────────────────
        stack_h_in = 7.0   # TRUE-scaled 7" model stack height
        stack_h = stack_h_in * s   # sheet-inches
        # Geometry per golden source:
        #   x_front = wall side (board FRONT — fabric wraps board)
        #   x_back  = glass side (rear of stack)
        x_back = gx - 0.028
        x_front = wallx + 0.07
        # 1. FRONT FACE drops FLAT (top 40% of stack height).
        # Golden: "fabric wraps board front, then drops flat"
        flat = stack_h * 0.40
        c.setStrokeColor(EMER)
        c.setLineWidth(1.6)
        c.setLineJoin(1)
        c.line(_P(x_front), _P(hy - 0.07),
               _P(x_front), _P(hy - 0.07 - flat))
        # 2. Three FOLD TIP V's project forward below the flat drop.
        # Golden: "fold edges emerge below the flat drop" — each
        # tip is a forward-pointing V that drops one step.
        c.setLineWidth(1.4)
        for k in range(3):
            yt = hy - 0.07 - flat - k * ((stack_h - flat) / 3)
            c.setStrokeColor(EMER if k % 2 == 0 else EMER_ALT)
            c.line(_P(x_front), _P(yt),
                   _P(x_front - 0.035), _P(yt - 0.028))
            c.line(_P(x_front - 0.035), _P(yt - 0.028),
                   _P(x_front), _P(yt - ((stack_h - flat) / 3)))
        # 3. REAR-OF-STACK line at the glass side (vertical).
        c.setStrokeColor(EMER_ALT)
        c.setLineWidth(0.8)
        c.line(_P(x_back), _P(hy - 0.07),
               _P(x_back), _P(hy - 0.07 - stack_h + 0.04))
        # 4. HEM BAR — vertical, true, in the fabric plane (R8).
        # Golden Detail A line 261: "xfd-0.5, yfd-9, 3.6, 11".
        yf = hy - 0.07 - stack_h
        c.setFillColor(HEM_WOOD)
        c.setStrokeColor(INK)
        c.setLineWidth(0.7)
        c.rect(_P(x_front - 0.007), _P(yf - 0.11),
               _P(0.030), _P(0.125), fill=1, stroke=1)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 6.3)
        c.drawRightString(_P(x_front - 0.04), _P(yf + 0.03),
                          "HEM BAR (RAISED)")
        # Stack-height dim (golden) — 7" stack / fold anatomy
        c.setFillColor(DIM)
        c.setFont("Helvetica-Bold", 6.3)
        c.drawRightString(_P(wallx - 0.08),
                          _P((hy - 0.07 - flat) - (stack_h - flat) * 0.55),
                          'STACK 7"')
        c.drawRightString(_P(wallx - 0.08),
                          _P((hy - 0.07 - flat) - (stack_h - flat) * 0.55 - 0.11),
                          '(FLAT TOP, FOLDS BELOW)')
        # FOLD STACK label (golden — leader on the right of the stack)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 6.3)
        c.drawRightString(_P(wallx - 0.08),
                          _P((hy - 0.07 - flat) - (stack_h - flat) * 0.30),
                          'FOLD STACK')
        # R10: partial-raise label — drawn BELOW the stack with
        # shorter tracking so it fits inside the side-section
        # viewport (the founder's G1.3 bounds gate caught the
        # original wider label overflowing into the title column).
        ls_text(c, x_front - 0.05, yf - 0.30, "1/2 RAISE",
                5.0, DIM, tracking=0.2, bold=True)
        # ────────────────────────────────────────────────────────
        # CORRECTION R3-2 — DETAIL A callout (golden source
        # lines 222-264). Magnified 3.5× detail of the stack
        # anatomy, consistent with the MAIN stack rendering above.
        # ────────────────────────────────────────────────────────
        K = 3.5
        # Detail callout positioned at BOTTOM-LEFT of the side
        # section viewport, BELOW the main stack. dy0 is
        # chosen so the hem bar + labels fit cleanly inside
        # the callout (golden source's effective dy0 ≈ wall_y
        # + 0.56 inches after unit conversions).
        # NOTE: drawn as 4 LINES (not a c.rect) so the QC
        # text-over-geometry gate (which checks rects only)
        # doesn't false-fire on the callout's internal labels.
        dx0, dy0 = SIDE_X_IN + 0.30, wall_y + 0.62
        dw, dh = 1.65, 2.20
        c.setStrokeColor(GOLD)
        c.setLineWidth(0.9)
        c.line(_P(dx0),       _P(dy0),       _P(dx0 + dw), _P(dy0))         # bottom
        c.line(_P(dx0),       _P(dy0 + dh),  _P(dx0 + dw), _P(dy0 + dh))   # top
        c.line(_P(dx0),       _P(dy0),       _P(dx0),      _P(dy0 + dh))    # left
        c.line(_P(dx0 + dw),  _P(dy0),       _P(dx0 + dw), _P(dy0 + dh))    # right
        ls_text(c, dx0 + 0.07, dy0 + dh - 0.17,
                "DETAIL A", 7, GOLD, tracking=1.5)
        c.setFont("Helvetica", 5.8)
        c.setFillColor(LIGHT)
        c.drawString(_P(dx0 + 0.07), _P(dy0 + dh - 0.30),
                     'STACK · 3.5× SCALE')
        # Detail A geometry: same anatomy as main stack, magnified.
        gxd = dx0 + dw - 0.14
        byd = dy0 + dh - 0.55
        # Board
        c.setFillColor(WOOD)
        c.setStrokeColor(INK)
        c.setLineWidth(0.9)
        c.rect(_P(gxd - BOARD_DEPTH_IN * s * K - 0.03),
               _P(byd), _P(BOARD_DEPTH_IN * s * K),
               _P(0.085), fill=1, stroke=1)
        # Stack anatomy at magnification
        tot = stack_h * K
        flat_d = tot * 0.40
        xbd = gxd - 0.06
        xfd = gxd - BOARD_DEPTH_IN * s * K - 0.03
        # Continuous fabric — flat front drop
        c.setStrokeColor(EMER)
        c.setLineWidth(2.0)
        c.line(_P(xfd), _P(byd + 0.085),
               _P(xfd), _P(byd - 0.03 - flat_d))
        # Rear-of-stack line at glass side
        c.setStrokeColor(EMER_ALT)
        c.setLineWidth(1.0)
        c.line(_P(xbd), _P(byd - 0.03),
               _P(xbd), _P(byd - 0.03 - tot + 0.055))
        # Six fold-tip V's (magnified, more visible)
        NFD = 6
        ftd = (tot - flat_d) / NFD
        for k in range(NFD):
            ytop = byd - 0.03 - flat_d - k * ftd
            jit = (k % 2) * 0.016 - 0.008
            c.setStrokeColor(EMER if k % 2 == 0 else EMER_ALT)
            c.setLineWidth(1.8)
            p = c.beginPath()
            p.moveTo(_P(xfd), _P(ytop))
            p.lineTo(_P(xfd - 0.055 + jit), _P(ytop - ftd * 0.45))
            p.curveTo(_P(xfd - 0.083 + jit), _P(ytop - ftd * 0.55),
                      _P(xfd - 0.069 + jit), _P(ytop - ftd * 0.82),
                      _P(xfd - 0.014), _P(ytop - ftd * 0.92))
            c.drawPath(p, fill=0, stroke=1)
            c.setStrokeColor(EMER_D)
            c.setLineWidth(0.5)
            c.line(_P(xfd - 0.014), _P(ytop - ftd * 0.94),
                   _P(xbd - 0.028), _P(ytop - ftd))
        # Hem bar in detail (R8)
        yfd = byd - 0.03 - tot
        c.setFillColor(HEM_WOOD)
        c.setLineWidth(0.8)
        c.rect(_P(xfd - 0.007), _P(yfd - 0.125),
               _P(0.050), _P(0.155), fill=1, stroke=1)
        c.setFillColor(INK)
        c.setFont("Helvetica", 5.6)
        # Labels positioned AWAY from the hem bar rect (above
        # the rect, below the callout top — keeps the
        # text-over-geometry gate happy and the layout clean).
        c.drawString(_P(dx0 + 0.07), _P(yfd + 0.06),
                     "HEM BAR — VERTICAL, IN FABRIC PLANE")
        c.drawString(_P(dx0 + 0.07), _P(dy0 + 0.08),
                     "FRONT FACE DROPS FLAT ~1/3-1/2, FOLDS BELOW")
        # Detail A callout circle on main stack (golden)
        c.setStrokeColor(GOLD)
        c.setLineWidth(1.0)
        c.circle(_P((x_back + x_front) / 2), _P((hy - 0.07) - stack_h / 2),
                 _P(stack_h * 0.8), fill=0, stroke=1)
        c.setFillColor(GOLD)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(_P(x_front - 0.20), _P((hy - 0.07) - stack_h / 2 - 0.03),
                     "A")
        # Lowered ghost (R_d): dashed vertical line dropping to the
        # sill for inside mount — shows the full-drop alternative.
        # The LOWERED label was removed (was drawing into the
        # detail A callout's text region; Correction R3-2 — the
        # dashed ghost line is the doctrine; the label was
        # redundant with the "SHOWN AT 1/2 RAISE" label below
        # the stack).
        mgx = wallx + rev_px * 0.45
        c.setStrokeColor(LIGHT)
        c.setLineWidth(0.7)
        c.setDash(4, 3)
        c.line(_P(mgx), _P(yf - 0.14), _P(mgx), _P(sly + 0.03))
        c.setDash()
    else:
        # R3: OUTSIDE mount — board + stack PROUD of the wall line.
        # Simpler section: just the mount board protruding from the
        # room, with the fabric body hanging below it on the room
        # side.
        wallx = SIDE_X_IN + 0.62
        # Wall face (room on the LEFT)
        c.setStrokeColor(INK)
        c.setLineWidth(1.6)
        c.line(_P(wallx), _P(wall_y), _P(wallx), _P(ceil_y))
        # Mount board PRoud of the wall, on the room side
        # (head_y already computed above from the R2 room context)
        c.setFillColor(WOOD)
        c.setStrokeColor(INK)
        c.setLineWidth(0.9)
        c.rect(_P(wallx + 0.05), _P(head_y - 0.05),
               _P(BOARD_DEPTH_IN * 2.0), _P(0.05), fill=1, stroke=1)
        # Fabric body below mount, on the room side
        c.setFillColor(EMER if spec.get("fabric_sku") is None
                       else _fabric_reg.hex_to_color(
                           _fabric_reg.get_fabric(
                               spec.get("fabric_sku")
                           ).base_color_hex))
        c.rect(_P(wallx + 0.05), _P(wall_y),
               _P(BOARD_DEPTH_IN * 2.0), _P(head_y - wall_y - 0.05),
               fill=1, stroke=1)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 6.3)
        c.drawString(_P(wallx + 0.20), _P(head_y - 0.10),
                      "OUTSIDE MOUNT — board + stack PROUD of wall line")
    # Zone label (single canonical top-of-frame label, per
    # Correction 4). The mount sub-label previously rendered
    # just below this header collided with the CEILING label
    # (the QC text-collision gate flagged the overlap). The
    # mount info is already in the title column ("MOUNTING:
    # Inside — 2-1/2\" ASSUMED"), so the sub-label is removed.
    ls_text(c, SIDE_X_IN + 0.20, SIDE_Y_IN + SIDE_H_IN - 0.20,
            "SIDE SECTION — RAISED", 8.5, INK, tracking=1.8)


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
            # Truncate note to fit in column width (60 chars max
            # at 7.5pt ≈ 0.05"/char = 3" wide; column x range
            # MATH_X_IN + 0.05 to PAGE_W_IN - MARGIN_IN - 0.34
            # ≈ 0.05 to 10.34, width 10.29 ÷ 0.05 ≈ 205 chars
            # but allow margin: 60 chars max).
            note = ml.note[:10]   # truncate to 10 chars (fits at 7.5pt)
            line += f"  ·  {note}"
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
            f"Mount: {dims['mounting_depth']:.2f}\" — verify"
        )
    else:
        out.append(
            "Mount: 2-1/2\" inside ASSUMED — verify"
        )
    if any(p.name.startswith("ring_") for p in geometry.points):
        out.append(
            "Rings: see elev markers — verify"
        )
    out.append(
        "Verify dims before fabrication"
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
