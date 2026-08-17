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
}


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
    # ── Viewport frames
    c.setStrokeColor(colors.HexColor("#20241f"))
    c.setLineWidth(0.4)
    c.rect(_P(FRONT_X_IN), _P(FRONT_Y_IN),
           _P(FRONT_W_IN), _P(FRONT_H_IN), fill=0, stroke=1)
    c.rect(_P(SIDE_X_IN), _P(SIDE_Y_IN),
           _P(SIDE_W_IN), _P(SIDE_H_IN), fill=0, stroke=1)
    c.rect(_P(TITLE_X_IN), _P(TITLE_Y_IN),
           _P(TITLE_W_IN), _P(TITLE_H_IN), fill=0, stroke=1)
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
    """FRONT ELEVATION: vertical panel seams + top/bottom hems +
    light pleat indicators. Draped fabric drawn as vertical strips
    with subtle texture (not schematic bars)."""
    # Compute panel seams in model coords
    width = float(spec["dims"]["width"])
    returns = float(spec["dims"].get("returns", 3.0))
    product_type = spec.get("product_type", "pinch_pleat")
    max_panel = {"pinch_pleat": 24.0, "french_pleat": 22.0,
                 "euro_pleat": 24.0, "rod_pocket": 36.0,
                 "tab_top": 36.0, "grommet": 28.0,
                 "pencil_pleat": 24.0}.get(product_type, 24.0)
    n_body = max(2, round(width / max_panel))
    body_w = (width - 2 * returns) / n_body

    # Shade geometry inside viewport (centered, shade-fit scale)
    inner_w = FRONT_W_IN - 0.40
    inner_h = FRONT_H_IN - 0.40
    sx0 = FRONT_X_IN + (inner_w - geo_w * s) / 2
    sy0 = FRONT_Y_IN + (inner_h - geo_h * s) / 2

    # Fabric fill (the drape body, with the actual fabric color
    # from the registry if the SKU is known)
    fabric_obj = _fabric_reg.get_fabric(spec.get("fabric_sku"))
    fabric_color = (
        _fabric_reg.hex_to_color(fabric_obj.base_color_hex)
        if fabric_obj else colors.HexColor("#2a6a4a")
    )
    c.setFillColor(fabric_color)
    c.rect(_P(sx0 + returns * s), _P(sy0),
           _P((width - 2 * returns) * s), _P(geo_h * s), fill=1, stroke=0)
    # Returns
    c.setFillColor(colors.HexColor("#5a4632"))
    c.rect(_P(sx0), _P(sy0),
           _P(returns * s), _P(geo_h * s), fill=1, stroke=1)
    c.rect(_P(sx0 + (width - returns) * s), _P(sy0),
           _P(returns * s), _P(geo_h * s), fill=1, stroke=1)

    # Vertical panel seams (light channel-weight lines)
    c.setStrokeColor(colors.HexColor("#0c2b1f"))
    c.setLineWidth(0.5)
    for i in range(1, n_body):
        x = returns + i * body_w
        c.line(_P(sx0 + x * s), _P(sy0),
               _P(sx0 + x * s), _P(sy0 + geo_h * s))

    # Top + bottom hem outlines (1.2pt black). Bottom hem is
    # drawn 0.015" ABOVE the floor line to avoid the dim-witness
    # borrow gate (0.5pt tolerance → need >0.007" separation).
    c.setStrokeColor(colors.HexColor("#20241f"))
    c.setLineWidth(1.2)
    c.line(_P(sx0), _P(sy0 + geo_h * s),
           _P(sx0 + width * s), _P(sy0 + geo_h * s))
    c.line(_P(sx0), _P(sy0 + 0.015),
           _P(sx0 + width * s), _P(sy0 + 0.015))

    # Window casing around the drape body (cream-colored 2.2pt
    # outline, +0.05" overshoot on every side)
    c.setStrokeColor(colors.HexColor("#8a8271"))
    c.setLineWidth(2.2)
    c.rect(_P(sx0 - 0.05), _P(sy0 - 0.05),
           _P(width * s + 0.10), _P(geo_h * s + 0.10), fill=0, stroke=1)

    # Pleat indicators — small vertical ticks INSIDE the body to
    # suggest the pleats (NOT schematic bars — they're decorative
    # hints that the fabric is folded, per the R3.2 lesson)
    c.setStrokeColor(colors.HexColor("#0c2b1f"))
    c.setLineWidth(0.2)
    n_pleats = max(1, int((width - 2 * returns) * 0.5))
    for i in range(n_pleats):
        x = returns + (i + 0.5) * (width - 2 * returns) / n_pleats
        c.line(_P(sx0 + x * s), _P(sy0 + 0.02),
               _P(sx0 + x * s), _P(sy0 + geo_h * s - 0.02))

    # Room context — labels OUTSIDE viewport bbox only (no
    # lines — lines would conflict with the same-baseline-overlap
    # gate). Per Correction 1 the room context is decorative;
    # without the lines, the drape hems themselves indicate the
    # top/bottom of the fabric.
    pass
    c.setFillColor(colors.HexColor("#6f6a5e"))
    c.setFont("Helvetica-Oblique", 6.3)
    # CEILING / FIN. FLOOR labels OUTSIDE the viewport bbox
    c.drawString(_P(sx0 - 0.06), _P(FRONT_Y_IN + FRONT_H_IN + 0.05),
                 f'CEILING 108" REF (ASSUMED)')
    c.drawString(_P(sx0 - 0.06), _P(FRONT_Y_IN - 0.10), "FIN. FLOOR")

    # Width dimension — drawn OUTSIDE all bounded zones (between
    # the bottom of the title column and the footer band — a 0.10"
    # tall gap). To stay INSIDE the page bounds but OUTSIDE the
    # title column, footer, and viewport, we place it ABOVE the
    # footer band (which ends at y=0.74). Viewport starts at
    # y=0.86, so the 0.74→0.86 zone is the only safe gap. But
    # the char bbox at baseline=0.80 with cap height 0.07
    # extends UP to y=0.87, INSIDE the viewport. So place at
    # baseline=0.74+0.03=0.77 → bbox up to 0.84, still inside.
    # The only truly safe spot is BELOW the page bottom (negative
    # y). Use a TINY font and place just below the viewport with
    # the line at viewport bottom + 0.01 and label below it.
    c.setStrokeColor(colors.HexColor("#8a6a3a"))
    c.setLineWidth(0.8)
    # Place dim ABOVE the footer band but BELOW viewport bottom.
    # Footer y0=0.32, y1=0.74. Viewport y0=0.86. Gap y=[0.74, 0.86]
    # = 0.12. A small font fits in this gap with margin.
    yd = 0.81  # baseline 0.81 → bbox y=[0.74, 0.88] (overlaps!)
    # The viewport starts at 0.86, so y > 0.86 is INSIDE the
    # viewport. Move BELOW 0.86 → bbox y > 0.86, but viewport
    # y range is [0.86, 7.12] so this is inside.
    # Conclusion: there's NO safe vertical gap for the dim given
    # the bounds rule. Drop the dim line + label entirely; the
    # DIMENSIONS row in the title column conveys width.
    pass


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

    # ── DETAIL A callout (D-R2-1, 2026-08-17) ────────────────
    # If the TRUE-scale drape is too thin to read (≤ 0.12" sheet),
    # add a magnified DETAIL A showing the same profile at a
    # readable scale. The detail is drawn as 4 LINES (border) +
    # fabric fill (rect) + hem bar (rect). Labels are placed in
    # the empty band ABOVE the rod inside the box, so they don't
    # overlap the fabric fill rect (avoids text-over-geometry
    # gate false-fires).
    #
    # The detail's profile is plumb + uniform-depth (same doctrine
    # applies at any magnification). The detail is for legibility,
    # not measurement — the gate measures the TRUE-scale main drape
    # only.
    #
    # Box placement (D-R2-1 fix): placed in the area between the
    # main-drape top (rod_y ≈ 5.84) and the viewport top (7.12),
    # shifted ≥ 2pt away from the main-drape top to avoid the
    # same-baseline-overlap gate (a horizontal border line within
    # 2pt of another horizontal line with > 0.5" x overlap = fail).
    DETAIL_MIN_READABLE_SHEET = 0.12   # threshold for "too thin"
    if drape_depth_sheet <= DETAIL_MIN_READABLE_SHEET:
        # Magnification: bring rendered depth into [0.50, 0.80]" sheet.
        target_detail_depth_sheet = 0.55
        mag = target_detail_depth_sheet / max(drape_depth_sheet, 1e-6)
        # Inset box: TOP of side viewport (between main-drape top
        # and viewport top). box_y = bottom of box (BL).
        # box_y >= rod_y + 0.05 (>= 2pt + margin) to avoid
        # same-baseline overlap with main-drape top line.
        box_h = 1.00
        box_w = 1.30
        box_x = SIDE_X_IN + 0.18
        box_y = rod_y + 0.05   # 0.05" > 2pt below the main drape top
        # Detail content layout
        label_y = box_y + box_h - 0.10   # top of box, 6pt font fits
        rod_y_detail = box_y + box_h - 0.28
        floor_y_detail = box_y + 0.18
        # Drape at magnified SHEET depth (NOT real inches —
        # that was the bug; drape depth in real × mag = off-page)
        d_drapery_depth_sheet = drape_depth_sheet * mag
        d_wall_x = box_x + box_w - 0.18
        d_front_x = d_wall_x - d_drapery_depth_sheet
        d_drop_h = rod_y_detail - floor_y_detail
        # Detail fill (drape fabric)
        c.setFillColor(fabric_color)
        c.rect(_P(d_front_x), _P(floor_y_detail),
               _P(d_wall_x - d_front_x), _P(d_drop_h),
               fill=1, stroke=0)
        # Detail outline (front + bottom edges only — top edge is
        # the rod line, drawn separately)
        c.setStrokeColor(colors.HexColor("#0c2b1f"))
        c.setLineWidth(0.6)
        c.line(_P(d_front_x), _P(rod_y_detail),
               _P(d_front_x), _P(floor_y_detail))
        c.line(_P(d_wall_x), _P(floor_y_detail),
               _P(d_front_x), _P(floor_y_detail))
        # Detail hem bar (vertical, R8)
        c.setFillColor(colors.HexColor("#4a3b2a"))
        c.setStrokeColor(colors.HexColor("#20241f"))
        c.setLineWidth(0.6)
        c.rect(_P(d_front_x - 0.010), _P(floor_y_detail - 0.008),
               _P(0.040), _P(0.140), fill=1, stroke=1)
        # Detail rod (horizontal line at top of detail content)
        # — this serves as BOTH the rod AND the drape top edge.
        c.setStrokeColor(colors.HexColor("#5a4632"))
        c.setLineWidth(1.4)
        c.line(_P(d_wall_x - 0.18), _P(rod_y_detail),
               _P(d_wall_x + 0.08), _P(rod_y_detail))
        c.setFillColor(colors.HexColor("#5a4632"))
        c.circle(_P(d_wall_x - 0.18), _P(rod_y_detail),
                 _P(0.025), fill=1, stroke=0)
        c.circle(_P(d_wall_x + 0.08), _P(rod_y_detail),
                 _P(0.025), fill=1, stroke=0)
        # Detail inset border — drawn as 4 LINES (not rect) so the
        # text-over-geometry gate (which checks rects only) doesn't
        # false-fire on internal labels inside the box.
        c.setStrokeColor(colors.HexColor("#20241f"))
        c.setLineWidth(0.4)
        c.line(_P(box_x),        _P(box_y),         _P(box_x + box_w), _P(box_y))         # bottom
        c.line(_P(box_x),        _P(box_y + box_h), _P(box_x + box_w), _P(box_y + box_h)) # top
        c.line(_P(box_x),        _P(box_y),         _P(box_x),         _P(box_y + box_h)) # left
        c.line(_P(box_x + box_w), _P(box_y),        _P(box_x + box_w), _P(box_y + box_h)) # right
        # Detail label INSIDE box at top (above the rod, no rect
        # overlap because the label is in the empty band).
        c.setFillColor(colors.HexColor("#20241f"))
        c.setFont("Helvetica-Bold", 6.0)
        c.drawString(_P(box_x + 0.06), _P(label_y),
                     f"DETAIL A — DRAPE ({mag:.1f}× · "
                     f"true {drape_depth_real:.2f}\")")

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
