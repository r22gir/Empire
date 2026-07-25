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
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib import colors

if TYPE_CHECKING:
    from app.services.drawing.templates.base import (
        GeometryResult, MathLine, GeometryFamilyResult,
    )


# ── Page geometry (landscape letter, all values in inches) ─────────

PAGE_W_IN = 11.0
PAGE_H_IN = 8.5
PAGE_MARGIN_IN = 0.5
SHEET_INSET_IN = 0.15

SHEET_X_IN = PAGE_MARGIN_IN - SHEET_INSET_IN
SHEET_Y_IN = PAGE_MARGIN_IN - SHEET_INSET_IN
SHEET_W_IN = PAGE_W_IN - 2 * (PAGE_MARGIN_IN - SHEET_INSET_IN)
SHEET_H_IN = PAGE_H_IN - 2 * (PAGE_MARGIN_IN - SHEET_INSET_IN)

# ── Page zones (within sheet border) ────────────────────────────────

# Title block (right column)
TITLE_X_IN = 7.2
TITLE_Y_IN = 0.5
TITLE_W_IN = 3.2
TITLE_H_IN = 7.5

# Front elevation (left zone, top)
FRONT_X_IN = 0.5
FRONT_Y_IN = 2.3
FRONT_W_IN = 3.9
FRONT_H_IN = 4.4

# Side section (middle zone)
SIDE_X_IN = 4.7
SIDE_Y_IN = 2.3
SIDE_W_IN = 2.3
SIDE_H_IN = 4.4

# Notes / Assumptions block (bottom-left)
NOTES_X_IN = 0.5
NOTES_Y_IN = 1.4
NOTES_W_IN = 6.4
NOTES_H_IN = 0.55

# LAYOUT MATH block (bottom-center)
MATH_X_IN = 0.5
MATH_Y_IN = 0.5
MATH_W_IN = 4.0
MATH_H_IN = 0.8

# SCALE bar (below front elevation)
SCALE_X_IN = 0.5
SCALE_Y_IN = 2.0
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

    # ── Sheet border ─────────────────────────────────────────
    c.setStrokeColor(colors.HexColor("#222222"))
    c.setLineWidth(0.8)
    c.rect(_P(SHEET_X_IN), _P(SHEET_Y_IN), _P(SHEET_W_IN), _P(SHEET_H_IN),
           stroke=1, fill=0)
    # Sheet-corner registration marks (small ticks at each corner)
    for cx_in, cy_in in [
        (SHEET_X_IN, SHEET_Y_IN),
        (SHEET_X_IN + SHEET_W_IN, SHEET_Y_IN),
        (SHEET_X_IN, SHEET_Y_IN + SHEET_H_IN),
        (SHEET_X_IN + SHEET_W_IN, SHEET_Y_IN + SHEET_H_IN),
    ]:
        tick = 0.08
        c.setStrokeColor(colors.HexColor("#222222"))
        c.setLineWidth(1.0)
        c.line(_P(cx_in - tick), _P(cy_in), _P(cx_in + tick), _P(cy_in))
        c.line(_P(cx_in), _P(cy_in - tick), _P(cx_in), _P(cy_in + tick))

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
    """Front-elevation view."""
    # View header (top of zone)
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.black)
    c.drawString(
        _P(FRONT_X_IN + 0.05), _P(FRONT_Y_IN + FRONT_H_IN - 0.18),
        f"FRONT ELEVATION — {product_type.replace('_', ' ').title()}",
    )

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
    c.rect(
        _P(X(0)), _P(Y(geo_h)),
        _P(X(geo_w) - X(0)),
        _P(Y(geo_h + 0.06) - Y(geo_h)),
        stroke=1, fill=1,
    )
    _draw_leader_label(c, X(geo_w), Y(geo_h + 0.03),
                       "MOUNT BOARD", side="right", offset_in=0.20)

    # Shade body outline
    c.setStrokeColor(colors.black)
    c.setLineWidth(1.5)
    c.setFillColor(colors.HexColor("#f5f0e6"))
    c.rect(
        _P(X(0)), _P(Y(0)),
        _P(X(geo_w) - X(0)),
        _P(Y(geo_h) - Y(0)),
        stroke=1, fill=1,
    )

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
    c.rect(
        _P(X(0)), _P(Y(-0.18)),
        _P(X(geo_w) - X(0)),
        _P(Y(0) - Y(-0.18)),
        stroke=1, fill=1,
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
    """
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.black)
    c.drawString(
        _P(SIDE_X_IN + 0.05), _P(SIDE_Y_IN + SIDE_H_IN - 0.18),
        "SIDE SECTION",
    )

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
    c.setStrokeColor(colors.HexColor("#222222"))
    c.setLineWidth(2.0)
    c.rect(_P(mount_left), _P(mount_y),
           _P(mount_right - mount_left), _P(mount_depth_scaled),
           stroke=1, fill=1)
    _draw_leader_label(c, mount_right, mount_y + mount_depth_scaled / 2,
                       "MOUNT BOARD (INSIDE)",
                       side="right", offset_in=0.15)

    # HEM bar drawn at the TOP of travel (HOTFIX B2c (1) — the hem
    # has rolled up to just below the mount in the raised state).
    hem_y = mount_y - 0.05 - hem_depth_scaled
    hem_left = mount_left
    hem_right = mount_right
    c.setFillColor(colors.HexColor("#a08060"))
    c.setStrokeColor(colors.HexColor("#222222"))
    c.setLineWidth(2.0)
    c.rect(_P(hem_left), _P(hem_y),
           _P(hem_right - hem_left), _P(hem_depth_scaled),
           stroke=1, fill=1)
    _draw_leader_label(c, hem_right, hem_y + hem_depth_scaled / 2,
                       "HEM BAR (raised)",
                       side="right", offset_in=0.15)

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
    _draw_leader_label(c, wall_x, wall_bottom + 0.02,
                       "FLOOR / SILL", side="left", offset_in=0.18)

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
    c.setStrokeColor(colors.HexColor("#aa5500"))
    c.setLineWidth(1.2)
    c.rect(_P(stack_x), _P(stack_y),
           _P(stack_w), _P(stack_h),
           stroke=1, fill=1)
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
    _draw_leader_label(c, stack_x + stack_w,
                       stack_y + stack_h / 2,
                       "FOLD STACK (RAISED)",
                       side="right", offset_in=0.18)

    # Hem bar
    c.setFillColor(colors.HexColor("#a08060"))
    c.setStrokeColor(colors.HexColor("#222222"))
    c.setLineWidth(2.0)
    c.rect(_P(stack_x), _P(base_y),
           _P(stack_w), _P(hem_depth_scaled),
           stroke=1, fill=1)
    _draw_leader_label(c, stack_x, base_y + hem_depth_scaled / 2,
                       "HEM BAR", side="left", offset_in=0.18)


# ── Scale bar ──────────────────────────────────────────────────────


def _render_scale_bar(c: Canvas, geo_w: float):
    """SCALE bar at the same scale as the front elevation. 1'-0"
    = 12" model."""
    inner_w = FRONT_W_IN - 0.6
    front_scale = min(inner_w / geo_w, (FRONT_H_IN - 0.7) / geo_w) if geo_w > 0 else 0.05
    scale_length_in = 1.0 * front_scale
    bar_x = FRONT_X_IN + 0.3
    bar_y = SCALE_Y_IN + 0.10
    c.setStrokeColor(colors.black)
    c.setLineWidth(1.2)
    seg = scale_length_in / 3
    for i in range(3):
        sx = bar_x + i * seg
        c.setFillColor(colors.black if i % 2 == 0 else colors.white)
        c.rect(_P(sx), _P(bar_y),
               _P(seg), _P(0.10),
               stroke=1, fill=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 8)
    c.drawString(_P(bar_x), _P(bar_y - 0.16),
                "SCALE 1'-0\" = 12\"  (model inches)")


# ── LAYOUT MATH block ─────────────────────────────────────────────


def _render_layout_math(c: Canvas, math_lines: list):
    """Closure block in monospace. Lives in the bottom-center zone
    (MATH_ZONE) — separate from the assumptions block so the QC
    text-vs-geometry gate doesn't flag them as overlapping the
    shade outline."""
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
        c.drawString(_P(MATH_X_IN + 0.05), _P(y), line)
        y -= 0.16
        if ml.note:
            c.setFont("Helvetica-Oblique", 7.5)
            c.drawString(_P(MATH_X_IN + 0.20), _P(y), "  " + ml.note)
            c.setFont("Courier", 8.5)
            y -= 0.16


# ── NOTES / ASSUMPTIONS block (HOTFIX B2c (5)) ────────────────


def _get_assumptions(geometry, product_type: str, spec: dict = None) -> list[str]:
    """Canonical Roman-shade assumptions (Sprint 1d Phase A Fix #1 +
    B1 contract, restored on the vector path in B2c):
      - Slat height ASSUMED from family default table
      - Mounting depth ASSUMED 2-1/2" inside mount (or per spec)
      - Ring/tassel placement ASSUMED for ringed styles
      - Explicit CONFIRM-before-fabrication language
    """
    out: list[str] = []
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
    c.drawString(_P(NOTES_X_IN + 0.05),
                _P(NOTES_Y_IN + NOTES_H_IN - 0.15),
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
    """Standard right-column title block. Adds REV + DATE + SCALE rows
    (HOTFIX B2c (1))."""
    x = TITLE_X_IN
    y_top = TITLE_Y_IN + TITLE_H_IN
    c.setFillColor(colors.HexColor("#1a1a1a"))
    c.rect(_P(x), _P(y_top - 0.5), _P(TITLE_W_IN), _P(0.5),
           stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(_P(x + 0.1), _P(y_top - 0.18), "EMPIRE WORKROOM")
    c.setFont("Helvetica", 9)
    c.drawString(_P(x + 0.1), _P(y_top - 0.65),
                "CUSTOM UPHOLSTERY & FABRICATION")

    y = y_top - 1.0
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

    client = (spec or {}).get("client_name", "").strip()
    if client:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(_P(x + 0.1), _P(y), "CLIENT:")
        c.setFont("Helvetica", 9)
        c.drawString(_P(x + 1.4), _P(y), client)
        y -= 0.22

    c.setFont("Helvetica-Bold", 9)
    c.drawString(_P(x + 0.1), _P(y), "SHEET:")
    c.setFont("Helvetica", 9)
    c.drawString(_P(x + 1.4), _P(y), "1 of 1 (B2c vector)")
    y -= 0.22
    c.setFont("Helvetica-Bold", 9)
    c.drawString(_P(x + 0.1), _P(y), "STATUS:")
    c.setFont("Helvetica", 9)
    c.drawString(_P(x + 1.4), _P(y), "FOR FOUNDER REVIEW")
    y -= 0.22
    # HOTFIX B2c (1) — REV + DATE + SCALE rows.
    c.setFont("Helvetica-Bold", 9)
    c.drawString(_P(x + 0.1), _P(y), "REV:")
    c.setFont("Helvetica", 9)
    c.drawString(_P(x + 1.4), _P(y),
                f"{(spec or {}).get('rev', '0')}")
    y -= 0.22
    c.setFont("Helvetica-Bold", 9)
    c.drawString(_P(x + 0.1), _P(y), "DATE:")
    c.setFont("Helvetica", 9)
    date_str = (spec or {}).get("date") or date.today().isoformat()
    c.drawString(_P(x + 1.4), _P(y), date_str)
    y -= 0.22
    c.setFont("Helvetica-Bold", 9)
    c.drawString(_P(x + 0.1), _P(y), "SCALE:")
    c.setFont("Helvetica", 9)
    inner_w = FRONT_W_IN - 0.6
    front_scale = (
        min(inner_w / geo_w, (FRONT_H_IN - 0.7) / geo_w) if geo_w > 0
        else 0.05
    )
    scale_in_per_ft = 12.0
    page_in_per_ft = scale_in_per_ft * front_scale
    c.drawString(_P(x + 1.4), _P(y),
                f"1'-0\" = {scale_in_per_ft:.0f}\"  ({page_in_per_ft:.2f}\" page)")
    y -= 0.22
    c.setFont("Helvetica-Bold", 9)
    c.drawString(_P(x + 0.1), _P(y), "DRAWN BY:")
    c.setFont("Helvetica", 9)
    c.drawString(_P(x + 1.4), _P(y), "Empire Drafting Studio (B2c)")
    y -= 0.22

    optional_rows = [
        ("SITE",     (spec or {}).get("site_address", "")),
        ("MATERIAL", (spec or {}).get("material", "")),
    ]
    for label, val in optional_rows:
        if not val or not str(val).strip():
            continue
        c.setFont("Helvetica-Bold", 9)
        c.drawString(_P(x + 0.1), _P(y), label + ":")
        c.setFont("Helvetica", 9)
        c.drawString(_P(x + 1.4), _P(y), str(val))
        y -= 0.22
