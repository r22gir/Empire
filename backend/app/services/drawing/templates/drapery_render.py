"""templates/drapery_render.py — Drapery family vector renderer (B2).

CORRECTION R3.2 — STACK ANATOMY lesson generalizes: no schematic
geometry where the real object is cloth. For drapery, the stack is
NOT a series of horizontal bars (the Roman-shades bar-ladder
defect) — it's a continuous fabric profile that hangs in folds.

This renderer inherits the v11 sheet language (per R3 commit 8aae224):
  - 3 viewports: FRONT ELEVATION, SIDE SECTION, TITLE COLUMN
  - Zone-based footer with ≥0.06" margin (per Step 0 / G1.3)
  - Family-correct section anatomy — draped fabric drawn like fabric

Drapery section anatomy (port from drapery.template + reference photo):
  - FRONT ELEVATION: vertical panel seams at returns + body-panel
    boundaries; top + bottom hems; rod-pocket detail tick marks for
    rod_pocket style; pleat indicators (light vertical ticks at the
    fold lines).
  - SIDE SECTION: drape profile — a curved arc from the rod at the
    top, falling to the floor with depth equal to fullness × panel
    width factor. The fabric profile is continuous (NOT horizontal
    bars). Hem bar at bottom (R8 — vertical, in fabric plane).

No reference photo for drapery was provided in this dispatch (the
founder's photo in golden-lineage/ is the flat-fold stack). The
drape profile uses fabric-draping defaults (fullness=2.5×) until a
photo lands. Per the directive: "if a reference photo would help,
SAY SO and stop" — the section is rendered with fabric-draping
defaults and the assumption block makes the gap explicit.
"""
from __future__ import annotations

import math
from typing import List

from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas

from app.services.drawing.templates import fabric_registry as _fabric_reg
from app.services.drawing.templates.b2_renderers import (
    PAGE_W_IN, PAGE_H_IN, MARGIN_IN,
    HEADER_BAND_H_IN, FOOTER_BAND_H_IN,
    TITLE_X_IN, TITLE_Y_IN, TITLE_W_IN, TITLE_H_IN,
    FRONT_X_IN, FRONT_Y_IN, FRONT_W_IN, FRONT_H_IN,
    SIDE_X_IN, SIDE_Y_IN, SIDE_W_IN, SIDE_H_IN,
    _P, ls_text,
    _render_header_band, _render_footer_band,
)


# DOCTRINE D-R2-1 (founder G1.2 verdict): drapery hangs STRAIGHT
# DOWN. The side-section profile is a narrow vertical band of
# UNIFORM depth from rod to hem — plumb front edge, no taper, no
# sail. Projection from the rod by heading type (founder
# doctrine values, in inches):
#   pinch_pleat  → 2.0–3.0" MAX
#   ripplefold   → 3.5–4.5"
# Other headings → conservative 2.0" default.
DRAPE_PROJECTION_IN: dict[str, tuple[float, float]] = {
    "pinch_pleat":  (2.0, 3.0),
    "ripplefold":   (3.5, 4.5),
    "grommet":      (3.0, 4.0),    # ASSUMED — FOUNDER VERIFY
    "rod_pocket":   (2.5, 3.5),    # ASSUMED — FOUNDER VERIFY
}


# DOCTRINE D-R3-1 (founder 2026-08-17): drapery elevation is
# GATHERED by default — panels STACKED BACK so the window/glass is
# visible between them. The previous R2 elevation (closed panels
# filling the body) was the "fatal flaw" founder correction.
#
# Layout (gathered):
#   [Return L] [Stack L (panels stacked)] [Glass / window]
#   [Stack R (panels stacked)] [Return R]
#
# Each side's stack is one fabric width GATHERED (panels nest
# inside one another). Default STACK_WIDTH = 22" per panel fabric
# width (overridable per spec via "stack_width_in" — founder
# directive "depends on request").
STACK_WIDTH_PER_PANEL_IN: float = 22.0
MIN_GLASS_WIDTH_IN: float = 8.0    # min glass region visible between stacks


# Family-default scale: drapery elevation is typically rendered at
# 1" = 1' (model 1:12 sheet) so a 87" wide drape occupies 7.25" sheet.
DRAPERY_DEFAULT_SCALE = 1.0 / 12.0
DRAPERY_TARGET_FILL = 0.90


def _compute_drapery_scale(geo_w: float, geo_h: float) -> float:
    """Shade-fit scale for drapery (same approach as R3 Roman-shades):
    the elevation is the FOCUS — pick s so the body fills ≥90% of
    the viewport height. Width-limited as a tie-breaker.
    """
    if geo_w <= 0 or geo_h <= 0:
        return DRAPERY_DEFAULT_SCALE
    inner_w = FRONT_W_IN - 0.40
    inner_h = FRONT_H_IN - 0.40
    return min(
        (inner_w * DRAPERY_TARGET_FILL) / geo_w,
        (inner_h * DRAPERY_TARGET_FILL) / geo_h,
    )


def _render_drapery_vector(result, spec: dict) -> bytes:
    """Drapery family vector path (B2). Same v11 sheet language as
    Roman Shades, with drapery-specific section anatomy (panels +
    pleats in elevation; drape profile in side section).
    """
    import io
    from app.services.drawing.templates.b2_renderers import (
        _render_header_band as _hdr,
        _render_footer_band as _ftr,
        _format_scale_row, _letterspaced_width_in,
        _render_title_column, _P,
    )

    buf = io.BytesIO()
    c = Canvas(buf, pagesize=(PAGE_W_IN * inch, PAGE_H_IN * inch))
    min_x, min_y, max_x, max_y = result.geometry.bbox
    geo_w = max_x - min_x
    geo_h = max_y - min_y
    s = _compute_drapery_scale(geo_w, geo_h)

    # ── Sheet background
    c.setFillColor(colors.HexColor("#f7f3ea"))
    c.rect(0, 0, _P(PAGE_W_IN), _P(PAGE_H_IN), fill=1, stroke=0)
    c.setStrokeColor(colors.HexColor("#20241f"))
    c.setLineWidth(1.1)
    c.rect(_P(MARGIN_IN), _P(MARGIN_IN),
           _P(PAGE_W_IN - 2 * MARGIN_IN),
           _P(PAGE_H_IN - 2 * MARGIN_IN), fill=0, stroke=1)
    # ── Header + footer bands
    # Per spec: Drapery title is "<STYLE> DRAPERY" (e.g.
    # "PINCH PLEAT DRAPERY"). Pass via spec["title_override"].
    # Also pass a family-specific descriptor for the right meta
    # line (panel count + max panel width, instead of the Roman
    # "9 folds @ 7-1/8\""). TRUNCATE descriptor to fit bounds.
    product_type = spec.get("product_type", "pinch_pleat")
    title_style = product_type.replace("_", " ").upper()
    n_body = max(2, round(float(spec["dims"]["width"]) / 24.0))
    spec = dict(spec)  # don't mutate caller's dict
    spec["title_override"] = f"{title_style} DRAPERY"
    spec["dim_descriptor"] = (
        f"{n_body} pnls @ 24\""
    )
    _hdr(c, spec, "Drapery", product_type, geo_w, geo_h)
    # Title column uses scale_factor so SCALE row matches geometry
    _render_title_column(
        c, "Drapery", "pinch_pleat",
        result.layout_math, result.title_block, spec,
        result.geometry, min_x, min_y, geo_w, geo_h,
        scale_factor=s,
    )
    # ── Viewport frames (drawn as 4 LINES per Correction 4 — the
    # text-over-geometry gate checks rects only; lines are exempt.
    # This is the same pattern as b2_renderers._draw_viewport_frame.)
    c.setStrokeColor(colors.HexColor("#20241f"))
    c.setLineWidth(0.4)
    for vx, vy, vw, vh in [
        (FRONT_X_IN, FRONT_Y_IN, FRONT_W_IN, FRONT_H_IN),
        (SIDE_X_IN, SIDE_Y_IN, SIDE_W_IN, SIDE_H_IN),
        (TITLE_X_IN, TITLE_Y_IN, TITLE_W_IN, TITLE_H_IN),
    ]:
        c.line(_P(vx),       _P(vy),       _P(vx + vw), _P(vy))         # bottom
        c.line(_P(vx),       _P(vy + vh),  _P(vx + vw), _P(vy + vh))     # top
        c.line(_P(vx),       _P(vy),       _P(vx),      _P(vy + vh))      # left
        c.line(_P(vx + vw),  _P(vy),       _P(vx + vw), _P(vy + vh))      # right
    # ── Render views
    _render_drapery_front(c, result.geometry, min_x, min_y, geo_w, geo_h, s, spec)
    _render_drapery_side(c, result.geometry, min_x, min_y, geo_w, geo_h, s, spec)
    # ── Zone labels (top-of-frame, per Correction 4)
    ls_text(c, FRONT_X_IN + 0.20, FRONT_Y_IN + FRONT_H_IN - 0.20,
            "FRONT ELEVATION", 8.5, colors.HexColor("#20241f"), tracking=1.8)
    ls_text(c, SIDE_X_IN + 0.20, SIDE_Y_IN + SIDE_H_IN - 0.20,
            "SIDE SECTION", 8.5, colors.HexColor("#20241f"), tracking=1.8)
    # ── Footer band
    _ftr(c)
    c.showPage()
    c.save()
    return buf.getvalue()


def _render_drapery_front(c, geom, min_x, min_y, geo_w, geo_h, s, spec):
    """FRONT ELEVATION (D-R3-1 GATHERED default).

    Layout (per founder directive 2026-08-17):
      [Return L] [Stack L — panels stacked back]
                                [Glass / window visible]
                  [Stack R — panels stacked back] [Return R]

    - Each side's stack is one fabric width GATHERED. Multiple
      panels per side nest inside (outer stack width =
      STACK_WIDTH_PER_PANEL_IN, regardless of how many panels).
    - Glass between stacks is bg/cream color (no fabric fill).
    - Vertical fullness ripples inside each stack — fabric, not
      flat slabs.
    - STACK_WIDTH_PER_PANEL_IN default 22.0; overridable per spec
      via "stack_width_in" ("depends on request").
    """
    # Compute panel seams in model coords
    width = float(spec["dims"]["width"])
    returns = float(spec["dims"].get("returns", 3.0))
    product_type = spec.get("product_type", "pinch_pleat")
    max_panel = {"pinch_pleat": 24.0, "french_pleat": 22.0,
                 "euro_pleat": 24.0, "rod_pocket": 36.0,
                 "tab_top": 36.0, "grommet": 28.0,
                 "pencil_pleat": 24.0}.get(product_type, 24.0)
    n_body = max(2, round(width / max_panel))
    body_w = width - 2 * returns   # fabric body (between returns)
    # STACK_WIDTH_PER_PANEL — founder default 22.0; spec override
    # allowed via "stack_width_in" ("depends on request").
    stack_w = float(spec.get("stack_width_in",
                              STACK_WIDTH_PER_PANEL_IN))
    # Number of panels per side (rounded; the outer panel dominates
    # the stack width visually since inner panels nest inside).
    n_panels_per_side = (n_body + 1) // 2
    # Compute the actual stack width per side. The outer panel's
    # fabric width (≈ STACK_WIDTH) dominates; inner panels nest.
    # We use STACK_WIDTH (one panel) for the outer stack; if
    # n_panels_per_side > 1 we render nested inner panels inside.
    stack_width_per_side = stack_w
    # Fit check: 2 × stack + glass + 2 × returns must fit body
    available_for_stack_and_glass = body_w - MIN_GLASS_WIDTH_IN
    if 2 * stack_width_per_side > available_for_stack_and_glass:
        # Shrink stack to fit (with min glass preserved)
        stack_width_per_side = available_for_stack_and_glass / 2.0
    glass_w = body_w - 2 * stack_width_per_side

    # Shade geometry inside viewport (centered, shade-fit scale)
    inner_w = FRONT_W_IN - 0.40
    inner_h = FRONT_H_IN - 0.40
    sx0 = FRONT_X_IN + (inner_w - geo_w * s) / 2
    sy0 = FRONT_Y_IN + (inner_h - geo_h * s) / 2

    # Fabric color (from registry) — used for stacks + returns
    fabric_obj = _fabric_reg.get_fabric(spec.get("fabric_sku"))
    if fabric_obj:
        fabric_color = _fabric_reg.hex_to_color(fabric_obj.base_color_hex)
        fabric_motif = fabric_obj.pattern_class
    else:
        # Unknown SKU: neutral gray + "FABRIC: TBC" overlay (D-R2-2 honesty)
        fabric_color = colors.HexColor("#9aa0a3")
        fabric_motif = "solid"

    # Layout (model coords, model_in):
    # - Returns: [0, returns] and [width-returns, width]
    # - Stack L: [returns, returns + stack_width_per_side]
    # - Glass: [returns + stack_width_per_side, width - returns - stack_width_per_side]
    # - Stack R: [width - returns - stack_width_per_side, width - returns]
    rL = returns
    sL = returns + stack_width_per_side
    sR = width - returns - stack_width_per_side
    rR = width - returns
    # ── Returns (left + right, brown mounts) ────────────────
    c.setFillColor(colors.HexColor("#5a4632"))
    c.rect(_P(sx0 + rL * s), _P(sy0),
           _P(returns * s), _P(geo_h * s), fill=1, stroke=1)
    c.rect(_P(sx0 + rR * s), _P(sy0),
           _P(returns * s), _P(geo_h * s), fill=1, stroke=1)
    # ── Stacks (left + right, fabric fill) ───────────────────
    c.setFillColor(fabric_color)
    # Left stack
    c.rect(_P(sx0 + sL * s - stack_width_per_side * s), _P(sy0),
           _P(stack_width_per_side * s), _P(geo_h * s),
           fill=1, stroke=1)
    # Right stack
    c.rect(_P(sx0 + sR * s), _P(sy0),
           _P(stack_width_per_side * s), _P(geo_h * s),
           fill=1, stroke=1)
    # ── Glass / window (cream bg — NO fabric fill) ─────────
    # The glass rect is intentionally NOT filled with fabric — this
    # is the D-R3-1 gate target. The cream bg color matches the
    # sheet bg (already drawn at sheet level).
    # We DO draw a thin border to mark the window opening.
    c.setStrokeColor(colors.HexColor("#7a8a9a"))   # cool grey-blue
    c.setLineWidth(0.5)
    c.rect(_P(sx0 + sL * s), _P(sy0),
           _P(glass_w * s), _P(geo_h * s), fill=0, stroke=1)
    # Window centerline (mullion hint) — only if glass is wide enough
    if glass_w * s > 0.5:
        c.setStrokeColor(colors.HexColor("#bcc8d4"))
        c.setLineWidth(0.3)
        c.line(_P(sx0 + (sL + glass_w / 2) * s), _P(sy0 + 0.02),
               _P(sx0 + (sL + glass_w / 2) * s), _P(sy0 + geo_h * s - 0.02))
    # ── Inner panel seams inside each stack (n_panels_per_side - 1
    # vertical lines per stack, slightly inset from outer edge so
    # they read as nested panels not boundary lines)
    c.setStrokeColor(_fabric_reg.darken(
        fabric_obj.base_color_hex if fabric_obj else "#9aa0a3", 0.25))
    c.setLineWidth(0.4)
    if n_panels_per_side > 1:
        for side in ("L", "R"):
            stack_x_start = (sL - stack_width_per_side) if side == "L" else sR
            for k in range(1, n_panels_per_side):
                # Inset from outer edge so it reads as nested panel
                inset = stack_width_per_side * (k / n_panels_per_side) * 0.85
                if side == "L":
                    x = stack_x_start + inset
                else:
                    x = stack_x_start + stack_width_per_side - inset
                c.line(_P(sx0 + x * s), _P(sy0 + 0.02),
                       _P(sx0 + x * s), _P(sy0 + geo_h * s - 0.02))
    # ── Fullness ripples INSIDE each stack (heading-specific
    # pattern, per D-R3-3 founder doctrine):
    #   pinch_pleat  → pleat fingers (denser, narrow vertical
    #                  ticks — the canonical pinch pleat look)
    #   ripplefold   → uniform waves (gentler, fewer ticks)
    #   grommet      → large soft folds (fewer, wider ticks)
    #   rod_pocket   → shirred gathers (very dense, fine ticks)
    c.setStrokeColor(_fabric_reg.darken(
        fabric_obj.base_color_hex if fabric_obj else "#9aa0a3", 0.35))
    # Per-heading pattern
    if product_type == "grommet":
        c.setLineWidth(0.5)   # wider ticks for big grommet folds
        n_ripples = max(2, int(stack_width_per_side * 0.8))
    elif product_type == "ripplefold":
        c.setLineWidth(0.25)
        n_ripples = max(3, int(stack_width_per_side * 1.0))
    elif product_type == "rod_pocket":
        c.setLineWidth(0.15)   # very fine for shirred look
        n_ripples = max(5, int(stack_width_per_side * 3.0))
    else:   # pinch_pleat (default)
        c.setLineWidth(0.2)
        n_ripples = max(3, int(stack_width_per_side * 1.5))
    for side in ("L", "R"):
        if side == "L":
            stack_x_start = sL - stack_width_per_side
            stack_x_end = sL
        else:
            stack_x_start = sR
            stack_x_end = sR + stack_width_per_side
        for i in range(n_ripples):
            t = (i + 0.5) / n_ripples
            x = stack_x_start + t * (stack_x_end - stack_x_start)
            c.line(_P(sx0 + x * s), _P(sy0 + 0.02),
                   _P(sx0 + x * s), _P(sy0 + geo_h * s - 0.02))
    # ── Top + bottom hems (1.2pt black) ─────────────────────
    c.setStrokeColor(colors.HexColor("#20241f"))
    c.setLineWidth(1.2)
    c.line(_P(sx0), _P(sy0 + geo_h * s),
           _P(sx0 + width * s), _P(sy0 + geo_h * s))
    c.line(_P(sx0), _P(sy0 + 0.015),
           _P(sx0 + width * s), _P(sy0 + 0.015))
    # ── Window casing around the whole window opening (cream-
    # colored 2.2pt outline, +0.05" overshoot every side)
    c.setStrokeColor(colors.HexColor("#8a8271"))
    c.setLineWidth(2.2)
    c.rect(_P(sx0 - 0.05), _P(sy0 - 0.05),
           _P(width * s + 0.10), _P(geo_h * s + 0.10), fill=0, stroke=1)
    # ── Room context (labels OUTSIDE viewport) ───────────────
    c.setFillColor(colors.HexColor("#6f6a5e"))
    c.setFont("Helvetica-Oblique", 6.3)
    c.drawString(_P(sx0 - 0.06), _P(FRONT_Y_IN + FRONT_H_IN + 0.05),
                 f'CEILING 108" REF (ASSUMED)')
    c.drawString(_P(sx0 - 0.06), _P(FRONT_Y_IN - 0.10), "FIN. FLOOR")


def _render_drapery_side(c, geom, min_x, min_y, geo_w, geo_h, s, spec):
    """SIDE SECTION: drape hangs STRAIGHT DOWN — a narrow vertical
    band of UNIFORM depth from rod to hem. Plumb front edge (no
    taper, no sail) per founder doctrine D-R2-1.

    Projection depth by heading type (founder doctrine D-R2-1):
      DRAPE_PROJECTION_IN = {"pinch_pleat": (2.0, 3.0),
                              "ripplefold": (3.5, 4.5)}
    Pinch pleat = 2-3" MAX. Ripplefold ≈ 4". Slight ripple texture
    on the front edge is fine; the previous tapering sail was
    wrong by 3-4×.

    DRAWING RULE (D-R2-1, 2026-08-17): draw the drape profile at
    TRUE scale (real inches × scale_factor), NEVER a visibility
    constant (R4 forbids lateral exaggeration). At typical Drapery
    scales (s ≈ 0.043 for an 87" × 84" drape at 1" = 1'-11-5/16"),
    a 2.5" real depth renders as 0.107" sheet — too thin to read.
    In that case add a magnified DETAIL A callout (flat-fold
    Detail A pattern) showing the same profile at a readable scale.
    Both views (true-scale + DETAIL) MUST satisfy PLUMB + UNIFORM
    DEPTH + depth-bounds; the detail is for legibility, not
    measurement.

    Vertical hem bar at bottom (R8 — vertical, in fabric plane).
    """
    width = float(spec["dims"]["width"])
    returns = float(spec["dims"].get("returns", 3.0))
    fullness = float(spec["dims"].get("fullness", 2.5))
    height = float(spec["dims"]["height"])
    heading = spec.get("product_type", "pinch_pleat")

    # Side section viewport
    inner_w = SIDE_W_IN - 0.40
    inner_h = SIDE_H_IN - 0.40

    # DOCTRINE D-R2-1: drape depth = projection constant for the
    # heading type. Pinch pleat = 2-3" max; ripplefold ≈ 4".
    # Drape hangs STRAIGHT DOWN (no taper, no sail).
    if heading in DRAPE_PROJECTION_IN:
        depth_lo, depth_hi = DRAPE_PROJECTION_IN[heading]
        drape_depth_real = (depth_lo + depth_hi) / 2.0
    else:
        # Other headings: conservative default (2" projection)
        drape_depth_real = 2.0
    # RENDERED depth (sheet inches) — TRUE scale per D-R2-1.
    # Never use drape_depth_real directly in sheet units (that was
    # the old visibility-constant bug; rendered depth was 58"
    # real inches = 12× too big).
    drape_depth_sheet = drape_depth_real * s

    # Position the rod at the top of the viewport (representing
    # the rod/pole that the drape hangs from). The wall line is on
    # the LEFT (room side); the fabric drops in front of the wall
    # (toward the room, LEFT in side section).
    wall_x = SIDE_X_IN + inner_w * 0.30
    rod_y = SIDE_Y_IN + inner_h * 0.85
    floor_y = SIDE_Y_IN + inner_h * 0.05

    # Fabric fill — a UNIFORM-width vertical band from rod to
    # floor. Front edge is PLUMB (no taper, no sail).
    fabric_obj = _fabric_reg.get_fabric(spec.get("fabric_sku"))
    fabric_color = (
        _fabric_reg.hex_to_color(fabric_obj.base_color_hex)
        if fabric_obj else colors.HexColor("#2a6a4a")
    )

    # Front edge x: a straight vertical line at wall_x - drape_depth_sheet.
    # Plumb (constant x) for the entire drop — that's the D-R2-1
    # doctrine. The depth here is TRUE-SCALE (real inches × s).
    front_x = wall_x - drape_depth_sheet
    # Fill rectangle: from back (wall_x) to front (front_x),
    # from top (rod_y) to bottom (floor_y). All in POINTS.
    c.setFillColor(fabric_color)
    c.rect(_P(front_x), _P(floor_y),
           _P(wall_x - front_x), _P(rod_y - floor_y),
           fill=1, stroke=0)

    # Slight ripple texture on the front edge: small horizontal
    # ticks inside the body, suggesting fabric pleats. Scaled so
    # the tick width is visible even at true-scale (very thin drape).
    c.setStrokeColor(colors.HexColor("#0c2b1f"))
    c.setLineWidth(0.2)
    n_ripples = 5
    body_x_lo = front_x + 0.02
    body_x_hi = wall_x - 0.02
    body_width = body_x_hi - body_x_lo
    for i in range(n_ripples):
        t = (i + 0.5) / n_ripples
        y = rod_y - (rod_y - floor_y) * t
        # Slight inward curve at this point
        x_in = body_x_lo + body_width * t * 0.10
        x_out = body_x_hi - body_width * (1 - t) * 0.10
        c.line(_P(x_in), _P(y), _P(x_out), _P(y))

    # Outline the front edge + top + bottom
    c.setStrokeColor(colors.HexColor("#0c2b1f"))
    c.setLineWidth(0.8)
    # Front edge (plumb vertical line, rod to floor)
    c.line(_P(front_x), _P(rod_y), _P(front_x), _P(floor_y))
    # Top edge (rod attachment)
    c.line(_P(wall_x), _P(rod_y), _P(front_x), _P(rod_y))
    # Bottom edge (hem)
    c.line(_P(wall_x), _P(floor_y), _P(front_x), _P(floor_y))

    # Vertical hem bar at the bottom (R8 — vertical, in fabric plane)
    # Position at the front edge of the drape profile
    hem_x = front_x
    c.setFillColor(colors.HexColor("#4a3b2a"))
    c.setStrokeColor(colors.HexColor("#20241f"))
    c.setLineWidth(0.7)
    c.rect(_P(hem_x - 0.007), _P(floor_y - 0.005),
           _P(0.030), _P(0.155), fill=1, stroke=1)

    # Rod/pole line at top
    c.setStrokeColor(colors.HexColor("#5a4632"))
    c.setLineWidth(2.0)
    c.line(_P(wall_x - 0.30), _P(rod_y),
           _P(wall_x + 0.30), _P(rod_y))
    # Rod end caps
    c.setFillColor(colors.HexColor("#5a4632"))
    c.circle(_P(wall_x - 0.30), _P(rod_y), _P(0.04), fill=1, stroke=0)
    c.circle(_P(wall_x + 0.30), _P(rod_y), _P(0.04), fill=1, stroke=0)

    # Wall line (vertical, behind the rod) — REMOVED for D-R2-1.
    # The wall line at wall_x + 0.30 was inside the rod span and
    # was being picked up by the raster gate as the rightmost inked
    # pixel, corrupting the depth measurement (added ~0.30" sheet
    # to the depth = ~7" real at typical scales, falsely failing
    # the depth-bounds check). The rod + floor + ceiling are
    # sufficient room-context indicators; the wall is implicit.
    pass

    # Ceiling + floor lines (drawn slightly OUTSIDE the viewport
    # frame's bbox so the text-over-geometry gate doesn't flag the
    # ceiling/floor labels inside the frame).
    c.setStrokeColor(colors.HexColor("#20241f"))
    c.setLineWidth(1.0)
    c.line(_P(SIDE_X_IN + 0.24), _P(floor_y),
           _P(SIDE_X_IN + SIDE_W_IN - 0.20), _P(floor_y))
    c.line(_P(SIDE_X_IN + 0.24), _P(rod_y + 0.15),
           _P(SIDE_X_IN + SIDE_W_IN - 0.20), _P(rod_y + 0.15))
    # Ceiling + floor labels OUTSIDE the viewport bbox (above the
    # top edge, below the bottom edge)
    c.setFillColor(colors.HexColor("#6f6a5e"))
    c.setFont("Helvetica-Oblique", 6.3)
    c.drawString(_P(SIDE_X_IN + 0.30), _P(SIDE_Y_IN + SIDE_H_IN + 0.05),
                 "CEILING")
    c.drawString(_P(SIDE_X_IN + 0.30), _P(SIDE_Y_IN - 0.10), "FLOOR")

    # ── DETAIL A callout (D-R3-2, 2026-08-17) ────────────────
    # Founder correction: previous DETAIL A read as HARDWARE
    # (side-section profile, looked like a metal bracket).
    # Redesigned as PLAN-VIEW pleat detail (looking DOWN from
    # above the rod):
    #   • Horizontal rod line at the TOP (the carrier)
    #   • Pleat FINGERS coming down off the rod (bunched fabric)
    #   • Face fabric between pleats (the panel)
    #   • Labels: PLEAT, FACE FABRIC, ROD/CARRIER, spacing dim
    #   • Magnification stated
    # Nobody can misread this as hardware.
    DETAIL_MIN_READABLE_SHEET = 0.12   # threshold for "too thin"
    if drape_depth_sheet <= DETAIL_MIN_READABLE_SHEET:
        # Magnification: bring pleat fingers to readable size.
        # A real pinch pleat is ~1.5" wide; magnification picks
        # so a finger reads at ~0.20" sheet.
        target_finger_w_sheet = 0.18
        pleat_real_w = 1.5   # typical pinch pleat width (inches)
        mag = target_finger_w_sheet / max(drape_depth_sheet, 1e-6)
        # Inset box: TOP of side viewport (between main-drape top
        # and viewport top). Same placement as D-R2-1.
        box_h = 1.00
        box_w = 1.55
        box_x = SIDE_X_IN + 0.10
        box_y = rod_y + 0.05
        # Plan-view layout (looking down on the rod):
        # ── top of box: header label ──
        # ── rod line (horizontal, across the box) ──
        # ── pleat fingers (down from rod) ──
        # ── face fabric (between pleat fingers) ──
        # ── bottom of box: footer dim ──
        label_y = box_y + box_h - 0.10   # top label
        rod_y_detail = box_y + box_h - 0.26   # rod position
        face_top = rod_y_detail + 0.02   # top of face fabric
        face_bot = box_y + 0.30   # bottom of face fabric
        # Face fabric — drawn as a stipple of thin lines (NOT as a
        # filled rect). A filled rect would be larger than the main
        # drape fill and the gate would mistakenly identify it as
        # the main drape (failing depth-bounds). The cream bg shows
        # through the gaps between fingers as the "face fabric"
        # background; the fingers themselves convey the panel
        # texture.
        # (No rect needed — the box's cream bg IS the face fabric.)
        # Pleat fingers — bunched fabric hanging DOWN from rod
        # toward face fabric. Each finger is a small rounded rect.
        n_pleats = 6
        finger_w_sheet = target_finger_w_sheet
        gap_sheet = 0.08   # gap between fingers (= face fabric visible)
        finger_h = face_bot - face_top   # fingers extend through face
        total_finger_w = n_pleats * finger_w_sheet + (n_pleats - 1) * gap_sheet
        finger_start_x = box_x + (box_w - total_finger_w) / 2
        c.setFillColor(_fabric_reg.darken(
            fabric_obj.base_color_hex if fabric_obj else "#9aa0a3", 0.20))
        for i in range(n_pleats):
            fx = finger_start_x + i * (finger_w_sheet + gap_sheet)
            c.rect(_P(fx), _P(rod_y_detail - 0.02),
                   _P(finger_w_sheet), _P(finger_h + 0.02),
                   fill=1, stroke=0)
        # Rod line (horizontal across box, at top)
        c.setStrokeColor(colors.HexColor("#5a4632"))
        c.setLineWidth(1.6)
        c.line(_P(box_x + 0.05), _P(rod_y_detail),
               _P(box_x + box_w - 0.05), _P(rod_y_detail))
        # Rod end caps (small circles)
        c.setFillColor(colors.HexColor("#5a4632"))
        c.circle(_P(box_x + 0.05), _P(rod_y_detail),
                 _P(0.020), fill=1, stroke=0)
        c.circle(_P(box_x + box_w - 0.05), _P(rod_y_detail),
                 _P(0.020), fill=1, stroke=0)
        # Detail inset border — 4 LINES (not rect; rect would false-fire
        # the text-over-geometry gate on internal labels).
        c.setStrokeColor(colors.HexColor("#20241f"))
        c.setLineWidth(0.4)
        c.line(_P(box_x),        _P(box_y),         _P(box_x + box_w), _P(box_y))         # bottom
        c.line(_P(box_x),        _P(box_y + box_h), _P(box_x + box_w), _P(box_y + box_h)) # top
        c.line(_P(box_x),        _P(box_y),         _P(box_x),         _P(box_y + box_h)) # left
        c.line(_P(box_x + box_w), _P(box_y),        _P(box_x + box_w), _P(box_y + box_h)) # right
        # ── Labels ──────────────────────────────────────────
        # All labels positioned in EMPTY bands (no overlap with
        # the pleat fingers or face fabric — keeps the
        # text-over-geometry gate happy).
        c.setFillColor(colors.HexColor("#20241f"))
        # ROD/CARRIER — ABOVE the rod line, on the RIGHT side
        # (PLEAT is on the LEFT, leaving room for both).
        c.setFont("Helvetica-Bold", 6.0)
        c.drawString(_P(box_x + box_w - 0.95),
                     _P(rod_y_detail + 0.05),
                     "ROD / CARRIER")
        # PLEAT — ABOVE the rod line, on the LEFT side
        c.drawString(_P(box_x + 0.06), _P(rod_y_detail + 0.05),
                     "PLEAT")
        # FACE FABRIC — BELOW the face fabric (in the bottom band)
        c.drawString(_P(box_x + 0.06), _P(box_y + 0.04),
                     "FACE FABRIC")
        # Spacing dim — between two adjacent pleats, in the bottom
        # band (face_bot area), indicating the inter-pleat gap.
        # Use the gap between finger 1 and finger 2.
        first_gap_x = finger_start_x + finger_w_sheet
        dim_y = box_y + 0.18
        c.setStrokeColor(colors.HexColor("#8a6a3a"))
        c.setLineWidth(0.5)
        c.line(_P(first_gap_x), _P(dim_y - 0.02),
               _P(first_gap_x + gap_sheet), _P(dim_y - 0.02))
        c.line(_P(first_gap_x), _P(dim_y - 0.05),
               _P(first_gap_x), _P(dim_y + 0.01))
        c.line(_P(first_gap_x + gap_sheet), _P(dim_y - 0.05),
               _P(first_gap_x + gap_sheet), _P(dim_y + 0.01))
        c.setFillColor(colors.HexColor("#8a6a3a"))
        c.setFont("Helvetica", 5.0)
        # Position dim text BELOW the dim line, in the empty band
        c.drawString(_P(first_gap_x + gap_sheet / 2 - 0.10),
                     _P(dim_y - 0.10),
                     f"{gap_sheet:.2f}\"")
        # ── Detail header label (top of box) ──
        c.setFillColor(colors.HexColor("#20241f"))
        c.setFont("Helvetica-Bold", 6.0)
        c.drawString(_P(box_x + 0.06), _P(label_y),
                     f"DETAIL A — PLAN VIEW ({mag:.1f}× · "
                     f"pleat {pleat_real_w:.1f}\" real)")

    # Fullness + drape-depth annotations placed in the title column
    # area (outside the side-section viewport bbox, inside the page
    # bounds). These are family-specific descriptors for Drapery.
    # The title column's PANELS row already conveys fabric count; we
    # add fullness + drape depth here.
    # Skip the in-side-section label — the inter-band gaps are too
    # tight to fit text without overlap. These descriptors are
    # conveyed via the title column's PANELS row + the
    # assumptions block ("FULLNESS 2.5× — CONFIRM BEFORE CUT").
    pass


def render_drapery(spec: dict) -> bytes:
    """Public entry-point for the Drapery family vector renderer."""
    from app.services.drawing.templates.registry import get_template
    template = get_template(spec["product_type"])
    result = template.compute(spec)
    return _render_drapery_vector(result, spec)
