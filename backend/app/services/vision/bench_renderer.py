"""
Professional architectural bench renderer + CNC fabrication engine.

Layout (landscape 1200×850) comes from quote_sheet_layout. Views take
the wide left column; isometric sits over a content-sized title block.
Dimension text stays in gutters inside each frame.

  ┌────────────────────────────────────┬─────────────────┐
  │ PLAN                               │ ISOMETRIC       │
  ├────────────────────────────────────┤                 │
  │ FRONT ELEVATION                    ├─────────────────┤
  │                                    │ TITLE / SPECS   │
  └────────────────────────────────────┴─────────────────┘

Rules enforced:
  - Cushion count = math.ceil(width / cushion_width) — NEVER hardcoded
  - ALL text horizontal — zero rotation transforms
  - Geometry scales into the safe rect; dims stay in the gutter
  - panel_style / channel_count are owner params, never overridden
  - CNC tiling for parts > 29" with 0.5" overlap
  - DXF export via ezdxf (optional — fails gracefully)
"""
import math
import os
import logging
import uuid
from datetime import datetime

logger = logging.getLogger("bench_renderer")

# Quote-diagram policy (inches, BH, category chip, WC chrome) lives in
# one module so the API, Max, and CraftForge cannot drift.
from app.services.drawing.bench_quote_bridge import (  # noqa: E402
    back_style_label as _bridge_back_label,
    category_chip as _bridge_category_chip,
    normalize_length_unit as _normalize_length_unit,
    sheet_chrome as _bridge_chrome,
)
from app.services.drawing.inches import format_inches as _in
from app.services.drawing.quote_sheet_layout import (  # noqa: E402
    CAPTION_H,
    Rect,
    SHEET_H,
    SHEET_W,
    SVG_TYPE,
    idea_sheet_regions,
    layout_title_block,
)

# ── CONSTANTS ──────────────────────────────────────────────────────
ISO_A = 30
COS_A = math.cos(math.radians(ISO_A))
SIN_A = math.sin(math.radians(ISO_A))

# Line weights
SW_HEAVY = 2.5      # Object outlines
SW_MED = 1.5        # Structure lines, quadrant borders
SW_LIGHT = 1.0      # Cushion dividers, internal structure
SW_CHANNEL = 0.3    # Channel/detail lines
SW_DIM = 0.75       # Dimension lines
SW_EXT = 0.5        # Extension lines
SW_FLOOR = 1.0      # Floor line (dashed)
SW_BORDER = 2.0     # Drawing border

FONT = "Arial, Helvetica, sans-serif"
BLACK = "#000000"
DIM_COLOR = "#333333"
GRAY = "#666666"
LIGHT_GRAY = "#CCCCCC"
# Legacy names — use fabrication `back_thickness` (default 2") in new drawings.
BACK_T = 2          # plan back thickness when not overridden (inches)
SIDE_BACK_THK = 2   # side elevation back thickness default (inches)
FRONT_ELEV_PANEL_FRAC = 0.40  # front vs side width in split elevation panel

# Layout — sheet size is shared. Quadrant constants remain so older
# callers that read them still import; composition uses idea_sheet_regions.
LAYOUT_W = SHEET_W
LAYOUT_H = SHEET_H
MARGIN = 26
ZONE_GAP = 16

HALF_W = (LAYOUT_W - MARGIN * 2 - ZONE_GAP) / 2
HALF_H = (LAYOUT_H - MARGIN * 2 - ZONE_GAP) / 2

# Quadrant origins and sizes
Q1_X, Q1_Y, Q1_W, Q1_H = MARGIN, MARGIN, HALF_W, HALF_H
Q2_X, Q2_Y, Q2_W, Q2_H = MARGIN + HALF_W + ZONE_GAP, MARGIN, HALF_W, HALF_H
Q3_X, Q3_Y, Q3_W, Q3_H = MARGIN, MARGIN + HALF_H + ZONE_GAP, HALF_W, HALF_H
Q4_X, Q4_Y, Q4_W, Q4_H = MARGIN + HALF_W + ZONE_GAP, MARGIN + HALF_H + ZONE_GAP, HALF_W, HALF_H

# CNC constraints
CNC_MAX_X = 29      # inches — max X travel
CNC_TILE_Y = 29     # inches — max Y travel
TILE_OVERLAP = 0.5   # inches — overlap between tiles


# ── DATA MODEL ─────────────────────────────────────────────────────

class BenchModel:
    """Encapsulates bench parameters for rendering and CNC."""

    def __init__(self, name="Straight Bench", width=120, depth=18,
                 seat_h=18, back_h=18, cushion_width=24,
                 panel_style="vertical_channels", channel_count=6,
                 client="", project="", quote_num="", has_back=True):
        self.name = name
        self.width = width
        self.depth = depth
        self.seat_h = seat_h
        self.back_h = back_h
        self.cushion_width = cushion_width
        self.panel_style = panel_style
        self.channel_count = channel_count
        self.client = client
        self.project = project
        self.quote_num = quote_num
        self.has_back = has_back
        self.date = datetime.now().strftime("%m/%d/%Y")

    @property
    def cushion_count(self):
        """CALCULATE cushion count from width. NEVER hardcode."""
        if self.cushion_width <= 0:
            return 1
        count = self.width / self.cushion_width
        if count != int(count) and (count - int(count)) * self.cushion_width > 6:
            return math.ceil(count)
        return max(1, int(count))

    @property
    def total_height(self):
        return self.seat_h + self.back_h


# ── CNC / FABRICATION ─────────────────────────────────────────────

class Part:
    """A fabrication part with CNC/SAW classification."""

    def __init__(self, name, width, length, thickness=0.75):
        self.name = name
        self.width = width
        self.length = length
        self.thickness = thickness
        self.process = "SAW"

    def classify(self):
        if self.width <= CNC_MAX_X:
            self.process = "CNC_TILE" if self.length > CNC_TILE_Y else "CNC"
        else:
            self.process = "SAW"
        return self


def model_to_parts(model):
    """Break bench model into fabrication parts."""
    parts = [
        Part("Seat Panel", model.width, model.depth, 0.75).classify(),
        Part("Side Panel L", model.depth, model.seat_h, 0.75).classify(),
        Part("Side Panel R", model.depth, model.seat_h, 0.75).classify(),
    ]
    if getattr(model, "has_back", True) and model.back_h and model.back_h > 0:
        parts.insert(1, Part("Back Panel", model.width, model.back_h, 0.75).classify())
    return parts


def generate_tiles(length):
    """Split a long part into CNC-able tiles with overlap."""
    tiles = []
    start = 0
    while start < length:
        end = min(start + CNC_TILE_Y, length)
        tiles.append((round(start, 2), round(end, 2)))
        if end >= length:
            break
        start = end - TILE_OVERLAP
    return tiles


def generate_shop_sheet(model):
    """Generate a text cut list for the shop."""
    parts = model_to_parts(model)
    lines = [
        f"SHOP SHEET — {model.name}",
        f"Date: {model.date}",
        f"Quote: {model.quote_num or '—'}",
        "",
        f"{'PART':<20} {'SIZE':>15} {'PROCESS':>12}",
        "-" * 50,
    ]
    for p in parts:
        size_str = f'{_in(p.width)} × {_in(p.length)}'
        lines.append(f"{p.name:<20} {size_str:>15} {p.process:>12}")
        if p.process == "CNC_TILE":
            tiles = generate_tiles(p.length)
            for i, (s, e) in enumerate(tiles, 1):
                lines.append(f"  Tile {i}: {_in(s)} – {_in(e)}")
    lines.append("")
    lines.append(f"Cushions: {model.cushion_count} @ {_in(model.cushion_width)} each")
    return "\n".join(lines)


def generate_dxf(model, output_path):
    """Generate DXF file for CNC. Returns path or None if ezdxf unavailable."""
    try:
        import ezdxf
    except ImportError:
        logger.warning("ezdxf not installed — skipping DXF generation")
        return None

    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    parts = model_to_parts(model)
    y_offset = 0
    gap = 2

    for p in parts:
        if p.process in ("CNC", "CNC_TILE"):
            if p.process == "CNC_TILE":
                tiles = generate_tiles(p.length)
                for i, (start, end) in enumerate(tiles):
                    tile_len = end - start
                    msp.add_lwpolyline(
                        [(0, y_offset), (p.width, y_offset),
                         (p.width, y_offset + tile_len), (0, y_offset + tile_len)],
                        close=True,
                    )
                    msp.add_text(
                        f"{p.name} T{i+1}", dxfattribs={"height": 1.0}
                    ).set_placement((0.5, y_offset + 0.5))
                    y_offset += tile_len + gap
            else:
                msp.add_lwpolyline(
                    [(0, y_offset), (p.width, y_offset),
                     (p.width, y_offset + p.length), (0, y_offset + p.length)],
                    close=True,
                )
                msp.add_text(
                    p.name, dxfattribs={"height": 1.0}
                ).set_placement((0.5, y_offset + 0.5))
                y_offset += p.length + gap

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    doc.saveas(output_path)
    logger.info(f"DXF saved: {output_path}")
    return output_path


# ── ISOMETRIC PROJECTION ──────────────────────────────────────────

def _iso(x, y, z, ox, oy, s):
    """3D (x=width, y=depth, z=height) → 2D isometric screen coords."""
    return (
        ox + (x * COS_A - y * COS_A) * s,
        oy - (x * SIN_A + y * SIN_A) * s - z * s,
    )


def _auto_scale(dims_3d, svg_w, svg_h, margin=30):
    """Compute scale and origin to fit a 3D bbox centered in SVG area."""
    mx, my, mz = dims_3d
    corners = [_iso(x, y, z, 0, 0, 1)
               for x in [0, mx] for y in [0, my] for z in [0, mz]]
    xs = [c[0] for c in corners]
    ys = [c[1] for c in corners]
    raw_w = max(xs) - min(xs)
    raw_h = max(ys) - min(ys)
    if raw_w == 0 or raw_h == 0:
        return 1.0, svg_w / 2, svg_h / 2

    scale = min((svg_w - margin * 2) / raw_w, (svg_h - margin * 2) / raw_h)

    corners2 = [_iso(x, y, z, 0, 0, scale)
                for x in [0, mx] for y in [0, my] for z in [0, mz]]
    xs2 = [c[0] for c in corners2]
    ys2 = [c[1] for c in corners2]
    ox = svg_w / 2 - (max(xs2) + min(xs2)) / 2
    oy = svg_h / 2 - (max(ys2) + min(ys2)) / 2 + 5
    return scale, ox, oy


def _back_thickness_in(has_back: bool, back_thickness_in: float | None = None) -> float:
    if not has_back:
        return 0.0
    from app.services.drawing.bench_fabrication_params import DEFAULT_BACK_THICKNESS_IN
    return float(back_thickness_in if back_thickness_in is not None else DEFAULT_BACK_THICKNESS_IN)


def _resolve_cushions(width_in: float, cushion_width: float = 24, cushion_count=None):
    """Equal-width cushions: count from nominal width, each segment = length / count."""
    if cushion_count is not None and int(cushion_count) > 0:
        n = int(cushion_count)
    elif cushion_width and cushion_width > 0:
        n = max(1, math.ceil(float(width_in) / float(cushion_width)))
    else:
        n = 1
    actual_w = float(width_in) / n
    return n, actual_w


def _auto_scale_2d(w, h, area_w, area_h, margin=40, fill=0.78):
    """Compute scale and origin to fit a 2D rect centered, filling ~78%."""
    if w == 0 or h == 0:
        return 1.0, area_w / 2, area_h / 2
    usable_w = area_w - margin * 2
    usable_h = area_h - margin * 2
    scale = min(usable_w / w, usable_h / h) * fill
    ox = (area_w - w * scale) / 2
    oy = (area_h - h * scale) / 2
    return scale, ox, oy


# ── SVG PRIMITIVES ────────────────────────────────────────────────

def _fmt_in(value) -> str:
    """Shop inches with the mark. 20 → 20\", 14.5 → 14-1/2\"."""
    return _in(value)


def _esc(txt):
    """Escape XML special chars."""
    return str(txt).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _poly(pts, sw=SW_MED, fill="none", stroke=BLACK, attrs: str = "", geom=True):
    points = " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in pts)
    extra = f" {attrs}" if attrs else ""
    gtag = ' data-geom="1"' if geom and stroke not in (DIM_COLOR,) else ""
    return (
        f'<polygon points="{points}" fill="{fill}" stroke="{stroke}" '
        f'stroke-width="{sw}" stroke-linejoin="round"{extra}{gtag}/>'
    )


def _iso_corners(ox, oy, scale, corners_3d):
    """Map (x, y, z) inch corners to 2D screen points."""
    return [_iso(x, y, z, ox, oy, scale) for x, y, z in corners_3d]


def _iso_face(parts, ox, oy, scale, corners_3d, sw=SW_MED, fill="none", stroke=BLACK):
    """Closed isometric face (3+ corners)."""
    pts = _iso_corners(ox, oy, scale, corners_3d)
    parts.append(_poly(pts, sw=sw, fill=fill, stroke=stroke, attrs='data-iso-face="1"'))


def _line(x1, y1, x2, y2, sw=SW_MED, stroke=BLACK, dash="", geom=True,
          dim_ext: bool = False, dim_stroke: bool = False):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    tag = ' data-geom="1"' if geom and stroke not in (DIM_COLOR, GRAY, LIGHT_GRAY) else ""
    if dim_ext:
        tag += ' data-dim-ext="1"'
    if dim_stroke:
        tag += ' data-dim-stroke="1"'
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{stroke}" stroke-width="{sw}"{d}{tag}/>'
    )


def _rect(x, y, w, h, sw=SW_MED, fill="none", stroke=BLACK, geom=True):
    tag = ' data-geom="1"' if geom and stroke not in (DIM_COLOR,) else ""
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{tag}/>'
    )


def _text(x, y, txt, size=10, anchor="middle", weight="normal", fill=BLACK):
    """ALL TEXT HORIZONTAL — no rotation parameter."""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        f'font-family="{FONT}" font-size="{size}" fill="{fill}" '
        f'font-weight="{weight}">{_esc(txt)}</text>'
    )


def _defs():
    return '''<defs>
  <marker id="dim-arrow" viewBox="0 0 10 6" refX="10" refY="3"
          markerWidth="8" markerHeight="6" orient="auto-start-reverse">
    <path d="M0,0 L10,3 L0,6 Z" fill="#000"/>
  </marker>
</defs>'''


# ── DIMENSION CALLOUTS — ALL TEXT HORIZONTAL ──────────────────────

def _dim_h(parts, p1, p2, label, offset_y, text_side="above"):
    """Horizontal dimension line with extension lines + arrows. Text always horizontal."""
    gap = 2
    ext = 4
    dy = offset_y
    sign = 1 if dy > 0 else -1

    # Extension lines
    parts.append(_line(
        p1[0], p1[1] + gap * sign, p1[0], p1[1] + dy + ext * sign,
        SW_EXT, DIM_COLOR, dim_ext=True,
    ))
    parts.append(_line(
        p2[0], p2[1] + gap * sign, p2[0], p2[1] + dy + ext * sign,
        SW_EXT, DIM_COLOR, dim_ext=True,
    ))

    # Dimension line with arrows
    d1y = p1[1] + dy
    d2y = p2[1] + dy
    parts.append(
        f'<line x1="{p1[0]:.1f}" y1="{d1y:.1f}" x2="{p2[0]:.1f}" y2="{d2y:.1f}" '
        f'stroke="{DIM_COLOR}" stroke-width="{SW_DIM}" data-dim-stroke="1" '
        f'marker-start="url(#dim-arrow)" marker-end="url(#dim-arrow)"/>'
    )

    # Text — always horizontal, centered above/below dimension line
    mx = (p1[0] + p2[0]) / 2
    my = (d1y + d2y) / 2
    text_y = my - 4 if text_side == "above" else my + 12
    parts.append(_text(mx, text_y, label, 9, weight="600", fill=DIM_COLOR))


def _dim_along_edge(parts, p1, p2, label, offset_px: float):
    """Dimension parallel to screen segment p1→p2, offset along the outward normal."""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    nx, ny = -uy, ux
    if offset_px < 0:
        nx, ny = -nx, -ny
        off = -offset_px
    else:
        off = offset_px
    gap = 2
    ext = 4

    def _ext_from(p):
        parts.append(_line(
            p[0] + nx * gap, p[1] + ny * gap,
            p[0] + nx * (off + ext), p[1] + ny * (off + ext),
            SW_EXT, DIM_COLOR, dim_ext=True,
        ))

    _ext_from(p1)
    _ext_from(p2)
    q1 = (p1[0] + nx * off, p1[1] + ny * off)
    q2 = (p2[0] + nx * off, p2[1] + ny * off)
    parts.append(
        f'<line x1="{q1[0]:.1f}" y1="{q1[1]:.1f}" x2="{q2[0]:.1f}" y2="{q2[1]:.1f}" '
        f'stroke="{DIM_COLOR}" stroke-width="{SW_DIM}" data-dim-stroke="1" '
        f'marker-start="url(#dim-arrow)" marker-end="url(#dim-arrow)"/>'
    )
    mx = (q1[0] + q2[0]) / 2
    my = (q1[1] + q2[1]) / 2
    parts.append(_text(mx + nx * 8, my + ny * 8 + 4, label, 9, weight="600", fill=DIM_COLOR))


def _dim_along_edge_outward(parts, p1, p2, label, offset_px: float, interior_pt):
    """Edge-parallel dim offset away from bench interior (iso plan/depth)."""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    nx, ny = -uy, ux
    mid_x = (p1[0] + p2[0]) / 2
    mid_y = (p1[1] + p2[1]) / 2
    to_in = (interior_pt[0] - mid_x, interior_pt[1] - mid_y)
    if nx * to_in[0] + ny * to_in[1] > 0:
        nx, ny = -nx, -ny
    off = abs(offset_px)
    gap = 2
    ext = 4

    def _ext_from(p):
        parts.append(_line(
            p[0] + nx * gap, p[1] + ny * gap,
            p[0] + nx * (off + ext), p[1] + ny * (off + ext),
            SW_EXT, DIM_COLOR, dim_ext=True,
        ))

    _ext_from(p1)
    _ext_from(p2)
    q1 = (p1[0] + nx * off, p1[1] + ny * off)
    q2 = (p2[0] + nx * off, p2[1] + ny * off)
    parts.append(
        f'<line x1="{q1[0]:.1f}" y1="{q1[1]:.1f}" x2="{q2[0]:.1f}" y2="{q2[1]:.1f}" '
        f'stroke="{DIM_COLOR}" stroke-width="{SW_DIM}" data-dim-stroke="1" '
        f'marker-start="url(#dim-arrow)" marker-end="url(#dim-arrow)"/>'
    )
    mx = (q1[0] + q2[0]) / 2
    my = (q1[1] + q2[1]) / 2
    parts.append(_text(mx + nx * 8, my + ny * 8 + 4, label, 9, weight="600", fill=DIM_COLOR))


def _dim_v_at_screen_x(parts, p1, p2, label, dim_x: float):
    """Vertical dim at fixed screen x (iso height chain outside solid projection)."""
    gap = 2
    ext = 4
    y_top, y_bot = (p1[1], p2[1]) if p1[1] <= p2[1] else (p2[1], p1[1])
    for p in (p1, p2):
        sx = p[0]
        sign = 1 if dim_x >= sx else -1
        parts.append(_line(
            sx + gap * sign, p[1], dim_x + ext * sign, p[1],
            SW_EXT, DIM_COLOR, dim_ext=True,
        ))
    parts.append(
        f'<line x1="{dim_x:.1f}" y1="{y_top:.1f}" x2="{dim_x:.1f}" y2="{y_bot:.1f}" '
        f'stroke="{DIM_COLOR}" stroke-width="{SW_DIM}" data-dim-stroke="1" '
        f'marker-start="url(#dim-arrow)" marker-end="url(#dim-arrow)"/>'
    )
    my = (y_top + y_bot) / 2
    parts.append(_text(dim_x + 8, my + 4, label, 9, anchor="start", weight="600", fill=DIM_COLOR))


def _iso_bench_vertices(
    width_in, depth_in, seat_h_in, back_h_in, has_back, sx: float = 0, sy: float = 0,
):
    """Corner vertices of the straight-bench iso solid (matches ``_draw_bench_box``)."""
    w, d, sh = width_in, depth_in, seat_h_in
    bh = back_h_in if has_back else 0
    bt = BACK_T if has_back else 0
    y_seat_rear = sy + d - (bt if has_back else 0)
    y_back = sy + d
    verts = [
        (sx, sy, 0), (sx + w, sy, 0), (sx + w, sy, sh), (sx, sy, sh),
        (sx, sy, sh), (sx + w, sy, sh), (sx + w, y_seat_rear, sh), (sx, y_seat_rear, sh),
        (sx, sy, 0), (sx, y_seat_rear, 0), (sx, y_seat_rear, sh), (sx, sy, sh),
        (sx + w, sy, 0), (sx + w, y_seat_rear, 0), (sx + w, y_seat_rear, sh), (sx + w, sy, sh),
        (sx, y_seat_rear, 0), (sx + w, y_seat_rear, 0), (sx + w, y_seat_rear, sh), (sx, y_seat_rear, sh),
    ]
    if has_back:
        verts.extend([
            (sx, y_seat_rear, sh), (sx + w, y_seat_rear, sh),
            (sx + w, y_seat_rear, sh + bh), (sx, y_seat_rear, sh + bh),
            (sx, y_seat_rear, sh + bh), (sx + w, y_seat_rear, sh + bh),
            (sx + w, y_back, sh + bh), (sx, y_back, sh + bh),
            (sx, y_seat_rear, sh), (sx, y_back, sh), (sx, y_back, sh + bh), (sx, y_seat_rear, sh + bh),
            (sx + w, y_seat_rear, sh), (sx + w, y_back, sh),
            (sx + w, y_back, sh + bh), (sx + w, y_seat_rear, sh + bh),
        ])
    return verts


def _iso_bench_screen_max_x(
    width_in, depth_in, seat_h_in, back_h_in, has_back, ox, oy, scale,
) -> float:
    mx = 0.0
    for x, y, z in _iso_bench_vertices(width_in, depth_in, seat_h_in, back_h_in, has_back):
        mx = max(mx, _iso(x, y, z, ox, oy, scale)[0])
    return mx


def _iso_straight_face_polys(
    width_in, depth_in, seat_h_in, back_h_in, has_back, ox, oy, scale,
):
    """Screen-space quads for straight bench iso solids (for dim clearance)."""
    sx, sy = 0, 0
    w, d, sh = width_in, depth_in, seat_h_in
    bh = back_h_in if has_back else 0
    bt = BACK_T if has_back else 0
    y_seat_rear = sy + d - (bt if has_back else 0)
    y_back = sy + d
    defs = [
        [(sx, sy, 0), (sx + w, sy, 0), (sx + w, sy, sh), (sx, sy, sh)],
        [(sx, sy, sh), (sx + w, sy, sh), (sx + w, y_seat_rear, sh), (sx, y_seat_rear, sh)],
        [(sx, sy, 0), (sx, y_seat_rear, 0), (sx, y_seat_rear, sh), (sx, sy, sh)],
        [(sx + w, sy, 0), (sx + w, y_seat_rear, 0), (sx + w, y_seat_rear, sh), (sx + w, sy, sh)],
        [(sx, y_seat_rear, 0), (sx + w, y_seat_rear, 0), (sx + w, y_seat_rear, sh), (sx, y_seat_rear, sh)],
    ]
    if has_back:
        defs.extend([
            [(sx, y_seat_rear, sh), (sx + w, y_seat_rear, sh),
             (sx + w, y_seat_rear, sh + bh), (sx, y_seat_rear, sh + bh)],
            [(sx, y_seat_rear, sh + bh), (sx + w, y_seat_rear, sh + bh),
             (sx + w, y_back, sh + bh), (sx, y_back, sh + bh)],
            [(sx, y_seat_rear, sh), (sx, y_back, sh), (sx, y_back, sh + bh), (sx, y_seat_rear, sh + bh)],
            [(sx + w, y_seat_rear, sh), (sx + w, y_back, sh),
             (sx + w, y_back, sh + bh), (sx + w, y_seat_rear, sh + bh)],
        ])
    return [
        [_iso(x, y, z, ox, oy, scale) for x, y, z in corners]
        for corners in defs
    ]


def _dim_seg_hits_iso_faces(x1, y1, x2, y2, faces) -> bool:
    from app.services.vision.bench_svg_dim_layout import _seg_hits_poly_interior
    return any(_seg_hits_poly_interior(x1, y1, x2, y2, face) for face in faces)


def _dim_along_edge_clear(parts, p1, p2, label, interior_pt, faces, preferred: float):
    """Edge-parallel dim; pick offset so the dimension stroke clears iso faces."""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    nx, ny = -uy, ux
    mid_x = (p1[0] + p2[0]) / 2
    mid_y = (p1[1] + p2[1]) / 2
    to_in = (interior_pt[0] - mid_x, interior_pt[1] - mid_y)
    if nx * to_in[0] + ny * to_in[1] > 0:
        nx, ny = -nx, -ny

    candidates = [
        preferred, preferred + 8, preferred + 16,
        -preferred, -(preferred + 8), -(preferred + 16),
    ]
    chosen = preferred
    for off in candidates:
        sign = 1 if off >= 0 else -1
        dist = abs(off)
        q1 = (p1[0] + nx * sign * dist, p1[1] + ny * sign * dist)
        q2 = (p2[0] + nx * sign * dist, p2[1] + ny * sign * dist)
        if not _dim_seg_hits_iso_faces(q1[0], q1[1], q2[0], q2[1], faces):
            chosen = dist if sign > 0 else -dist
            break
    off_px = abs(chosen)
    if chosen < 0:
        # Draw on the opposite side of the edge.
        _dim_along_edge(parts, p1, p2, label, -off_px)
    else:
        _dim_along_edge_outward(parts, p1, p2, label, off_px, interior_pt)


def _iso_bench_centroid(
    width_in, depth_in, seat_h_in, back_h_in, has_back, ox, oy, scale,
):
    pts = [
        _iso(x, y, z, ox, oy, scale)
        for x, y, z in _iso_bench_vertices(width_in, depth_in, seat_h_in, back_h_in, has_back)
    ]
    return (
        sum(p[0] for p in pts) / len(pts),
        sum(p[1] for p in pts) / len(pts),
    )


def _dim_h_local(parts, x1, x2, y_anchor, gap_below: float, label: str):
    """Horizontal dim with short vertical extensions (split elevation panels)."""
    gap = 2
    ext = 4
    below = min(max(gap_below, 14.0), 48.0)
    y_dim = y_anchor + below
    parts.append(_line(x1, y_anchor + gap, x1, y_dim + ext, SW_EXT, DIM_COLOR, dim_ext=True))
    parts.append(_line(x2, y_anchor + gap, x2, y_dim + ext, SW_EXT, DIM_COLOR, dim_ext=True))
    parts.append(
        f'<line x1="{x1:.1f}" y1="{y_dim:.1f}" x2="{x2:.1f}" y2="{y_dim:.1f}" '
        f'stroke="{DIM_COLOR}" stroke-width="{SW_DIM}" data-dim-stroke="1" '
        f'marker-start="url(#dim-arrow)" marker-end="url(#dim-arrow)"/>'
    )
    parts.append(_text((x1 + x2) / 2, y_dim + 12, label, 9, anchor="middle",
                       weight="600", fill=DIM_COLOR))


def _dim_h_local_above(parts, x1, x2, y_anchor, gap_above: float, label: str):
    """Horizontal dim above an anchor edge (e.g. back top — clear of tufting)."""
    gap = 2
    ext = 4
    above = min(max(gap_above, 14.0), 40.0)
    y_dim = y_anchor - above
    parts.append(_line(x1, y_anchor - gap, x1, y_dim - ext, SW_EXT, DIM_COLOR, dim_ext=True))
    parts.append(_line(x2, y_anchor - gap, x2, y_dim - ext, SW_EXT, DIM_COLOR, dim_ext=True))
    parts.append(
        f'<line x1="{x1:.1f}" y1="{y_dim:.1f}" x2="{x2:.1f}" y2="{y_dim:.1f}" '
        f'stroke="{DIM_COLOR}" stroke-width="{SW_DIM}" data-dim-stroke="1" '
        f'marker-start="url(#dim-arrow)" marker-end="url(#dim-arrow)"/>'
    )
    parts.append(_text((x1 + x2) / 2, y_dim - 8, label, 9, anchor="middle",
                       weight="600", fill=DIM_COLOR))


_DIM_LABEL_CHAR_W = 0.55
_SECTION_LABEL_GAP_PX = 6.0
_SECTION_LABEL_MAX_COUNT = 5


def _dim_label_width_px(label: str, size: float = 9) -> float:
    return len(label) * size * _DIM_LABEL_CHAR_W


def _section_dims_should_collapse(n_sections: int, section_px: float, unit_label: str) -> bool:
    n = max(1, int(n_sections))
    if n <= 1:
        return False
    if n > _SECTION_LABEL_MAX_COUNT:
        return True
    return _dim_label_width_px(unit_label) + _SECTION_LABEL_GAP_PX > section_px


def _chained_section_dim_label(n_sections: int, section_width_in: float) -> str:
    return f'{int(n_sections)} @ {_fmt_in(section_width_in)}'


def _dim_h_section_splits(
    parts,
    ox: float,
    span_px: float,
    n_sections: int,
    section_width_in: float,
    y_anchor: float,
    *,
    above: bool,
    v_gap: float = 16,
):
    """Per-section dims, or one chained label with interior ticks when labels won't fit."""
    n = max(1, int(n_sections))
    if n <= 1:
        return
    unit = _fmt_in(section_width_in)
    sec_px = span_px / n
    collapse = _section_dims_should_collapse(n, sec_px, unit)
    x0, x1 = ox, ox + span_px
    if collapse:
        chain = _chained_section_dim_label(n, section_width_in)
        if above:
            _dim_h_local_above(parts, x0, x1, y_anchor, v_gap, chain)
            y_dim = y_anchor - min(max(v_gap, 14.0), 40.0)
        else:
            _dim_h_local(parts, x0, x1, y_anchor, v_gap, chain)
            y_dim = y_anchor + min(max(v_gap, 14.0), 48.0)
        for i in range(1, n):
            sx = ox + span_px * i / n
            parts.append(_line(
                sx, y_dim - 4, sx, y_dim + 4, SW_DIM, DIM_COLOR,
                geom=False, dim_stroke=True,
            ))
    else:
        for i in range(n):
            xa = ox + span_px * i / n
            xb = ox + span_px * (i + 1) / n
            if above:
                _dim_h_local_above(parts, xa, xb, y_anchor, v_gap, unit)
            else:
                _dim_h_local(parts, xa, xb, y_anchor, v_gap, unit)


def _dim_v(parts, p1, p2, label, offset_x, text_side="right", outward_text: bool = True,
           text_dy: float = 4, label_center: bool = False, dim_attrs: str = "",
           label_frac: float | None = None, label_h_offset: float = 0):
    """Vertical dimension line. TEXT IS HORIZONTAL — placed beside the line."""
    gap = 2
    ext = 4
    sign = 1 if offset_x > 0 else -1

    # Extension lines
    parts.append(_line(
        p1[0] + gap * sign, p1[1], p1[0] + offset_x + ext * sign, p1[1],
        SW_EXT, DIM_COLOR, dim_ext=True,
    ))
    parts.append(_line(
        p2[0] + gap * sign, p2[1], p2[0] + offset_x + ext * sign, p2[1],
        SW_EXT, DIM_COLOR, dim_ext=True,
    ))

    # Dimension line with arrows
    d1x = p1[0] + offset_x
    d2x = p2[0] + offset_x
    parts.append(
        f'<line x1="{d1x:.1f}" y1="{p1[1]:.1f}" x2="{d2x:.1f}" y2="{p2[1]:.1f}" '
        f'stroke="{DIM_COLOR}" stroke-width="{SW_DIM}" data-dim-stroke="1"{dim_attrs} '
        f'marker-start="url(#dim-arrow)" marker-end="url(#dim-arrow)"/>'
    )

    mx = (d1x + d2x) / 2
    frac = 0.5 if label_frac is None else float(label_frac)
    my = p1[1] + frac * (p2[1] - p1[1])
    if label_center:
        hoff = label_h_offset
        if hoff == 0:
            hoff = 11 if offset_x >= 0 else -11
        if hoff < 0:
            parts.append(_text(mx + hoff, my + text_dy, label, 9, anchor="end",
                               weight="600", fill=DIM_COLOR))
        else:
            parts.append(_text(mx + hoff, my + text_dy, label, 9, anchor="start",
                               weight="600", fill=DIM_COLOR))
        return
    if offset_x >= 0:
        if outward_text:
            tx, anch = mx + 10, "start"
        else:
            tx, anch = mx + 8, "end"
    else:
        tx, anch = mx - 10, "end"
    parts.append(_text(tx, my + text_dy, label, 9, anchor=anch, weight="600", fill=DIM_COLOR))


def _dim_2d_h(parts, x1, x2, y, label, offset_y=20):
    _dim_h(parts, (x1, y), (x2, y), label, offset_y, "below" if offset_y > 0 else "above")


def _dim_2d_v(parts, x, y1, y2, label, offset_x=20, outward_text: bool = True,
              text_dy: float = 4, label_center: bool = False, dim_attrs: str = "",
              label_frac: float | None = None, label_h_offset: float = 0):
    side = "right" if offset_x > 0 else "left"
    _dim_v(parts, (x, y1), (x, y2), label, offset_x, side,
           outward_text=outward_text, text_dy=text_dy,
           label_center=label_center, dim_attrs=dim_attrs,
           label_frac=label_frac, label_h_offset=label_h_offset)


def _dim_oblique_rear(
    parts,
    p1: tuple[float, float],
    p2: tuple[float, float],
    label: str,
    offset: float = 26.0,
    attrs: str = "",
):
    """Oblique dim parallel to p1→p2, offset to the rear (+x) of the side back."""
    x1, y1 = p1
    x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    ln = math.hypot(dx, dy) or 1.0
    n1 = (dy / ln, -dx / ln)
    n2 = (-dy / ln, dx / ln)
    nx, ny = n1 if n1[0] >= n2[0] else n2
    if nx < 0:
        nx, ny = -nx, -ny
    ox, oy = nx * offset, ny * offset
    ext = 4.0
    scale = 1 + ext / max(abs(offset), 1)
    parts.append(_line(
        x1, y1, x1 + ox * scale, y1 + oy * scale,
        SW_EXT, DIM_COLOR, dim_ext=True,
    ))
    parts.append(_line(
        x2, y2, x2 + ox * scale, y2 + oy * scale,
        SW_EXT, DIM_COLOR, dim_ext=True,
    ))
    ax, ay = x1 + ox, y1 + oy
    bx, by = x2 + ox, y2 + oy
    extra = f' data-dim-stroke="1" data-dim-oblique="1"{attrs}'
    parts.append(
        f'<line x1="{ax:.1f}" y1="{ay:.1f}" x2="{bx:.1f}" y2="{by:.1f}" '
        f'stroke="{DIM_COLOR}" stroke-width="{SW_DIM}"{extra} '
        f'marker-start="url(#dim-arrow)" marker-end="url(#dim-arrow)"/>'
    )
    mx, my = (ax + bx) / 2, (ay + by) / 2
    label_off = 20.0
    parts.append(_text(mx + nx * label_off, my + ny * label_off + 4, label, 9,
                         anchor="start", weight="600", fill=DIM_COLOR))


def _elev_height_dims_left(
    parts, x, y_top, y_seat, y_floor, seat_h, back_h, panel_w: float = 0,
    deck_height_in: float | None = None, seat_cushion_thickness_in: float = 0,
    include_overall: bool = True,
):
    """Stacked vertical dims left of elevation (16px / 28px chains)."""
    inner, outer = -16, -24
    total = seat_h + (back_h or 0)
    if include_overall:
        _dim_2d_v(parts, x, y_top, y_floor, _in(total), offset_x=outer)
    if back_h and back_h > 0:
        _dim_2d_v(parts, x, y_top, y_seat, f'{_in(back_h)} BH', offset_x=inner - 10)
    cush = float(seat_cushion_thickness_in or 0)
    deck = deck_height_in if deck_height_in is not None else (float(seat_h) - cush)
    if cush > 0.05 and deck > 0.05 and seat_h:
        y_deck = y_floor + (y_seat - y_floor) * (deck / float(seat_h))
        if abs(y_seat - y_deck) < 18:
            _dim_2d_v(parts, x, y_seat, y_floor, f'{_in(seat_h)} SH', offset_x=inner)
            return
        sub_x = -26 if not include_overall else -12
        _dim_2d_v(parts, x, y_seat, y_floor, f'{_in(seat_h)} SH', offset_x=-22)
        _dim_2d_v(parts, x, y_deck, y_floor, f'{_in(deck)} DK', offset_x=-30)
        _dim_2d_v(parts, x, y_seat, y_deck, f'{_in(cush)} CUSH', offset_x=-30)
    elif seat_h:
        _dim_2d_v(parts, x, y_seat, y_floor, f'{_in(seat_h)} SH', offset_x=inner)


def _elev_height_dims_right(
    parts, x, y_top, y_seat, y_floor, seat_h, back_h, panel_w: float = 0,
    deck_height_in: float | None = None, seat_cushion_thickness_in: float = 0,
    include_overall: bool = True, y_deck_px: float | None = None,
    force_seat_breakdown: bool = False, skip_back_height: bool = False,
):
    """Stacked vertical dims right of side elevation (seat chain only if skip_back_height)."""
    inner, outer = 18, 28
    total = seat_h + (back_h or 0)
    if include_overall:
        _dim_2d_v(parts, x, y_top, y_floor, _in(total), offset_x=outer)
    cush = float(seat_cushion_thickness_in or 0)
    deck = deck_height_in if deck_height_in is not None else (float(seat_h) - cush)
    if cush > 0.05 and deck > 0.05:
        if y_deck_px is not None:
            y_deck = float(y_deck_px)
        else:
            y_deck = y_floor + (y_seat - y_floor) * (deck / float(seat_h))
        if not force_seat_breakdown and abs(y_seat - y_deck) < 18:
            if back_h and back_h > 0 and not skip_back_height:
                _dim_2d_v(parts, x, y_top, y_seat, f'{_in(back_h)} BH', offset_x=inner - 10)
            _dim_2d_v(parts, x, y_seat, y_floor, f'{_in(seat_h)} SH', offset_x=inner)
            return
        off_cush, off_dk, off_sh = 10, 18, 26
        seat_attr = ' data-side-seat-dim="1"'
        _dim_2d_v(
            parts, x, y_seat, y_deck, f'{_in(cush)} CUSH',
            offset_x=off_cush, text_dy=-3, label_center=True,
            label_frac=0.2, label_h_offset=22, dim_attrs=seat_attr,
        )
        _dim_2d_v(
            parts, x, y_deck, y_floor, f'{_in(deck)} DK',
            offset_x=off_dk, text_dy=0, label_center=True,
            label_frac=0.28, label_h_offset=12, dim_attrs=seat_attr,
        )
        _dim_2d_v(
            parts, x, y_seat, y_floor, f'{_in(seat_h)} SH',
            offset_x=off_sh, text_dy=0, label_center=True,
            label_frac=0.72, label_h_offset=12, dim_attrs=seat_attr,
        )
        if back_h and back_h > 0 and not skip_back_height:
            _dim_2d_v(
                parts, x, y_top, y_seat, f'{_in(back_h)} BH',
                offset_x=28, text_dy=0, label_center=True,
                label_frac=0.5, label_h_offset=12,
            )
    else:
        if back_h and back_h > 0 and not skip_back_height:
            _dim_2d_v(parts, x, y_top, y_seat, f'{_in(back_h)} BH', offset_x=inner - 10)
        if seat_h:
            _dim_2d_v(parts, x, y_seat, y_floor, f'{_in(seat_h)} SH', offset_x=inner)


def _dim_iso_width(parts, ox, oy, scale, x1, x2, y, z, label, below=True, offset=None):
    p1 = _iso(x1, y, z, ox, oy, scale)
    p2 = _iso(x2, y, z, ox, oy, scale)
    off = offset if offset is not None else (22 if below else -22)
    _dim_h(parts, p1, p2, label, off, "below" if below else "above")


def _dim_iso_depth(parts, ox, oy, scale, x, y1, y2, z, label, below=True, offset=None):
    p1 = _iso(x, y1, z, ox, oy, scale)
    p2 = _iso(x, y2, z, ox, oy, scale)
    off = offset if offset is not None else (22 if below else -22)
    _dim_h(parts, p1, p2, label, off, "below" if below else "above")


def _dim_iso_height(parts, ox, oy, scale, x, y, z1, z2, label, right=True, offset=None):
    p1 = _iso(x, y, z1, ox, oy, scale)
    p2 = _iso(x, y, z2, ox, oy, scale)
    off = offset if offset is not None else (18 if right else -18)
    _dim_v(parts, p1, p2, label, off, "right" if right else "left", outward_text=False)


# ── CUSHION NUMBERING ─────────────────────────────────────────────

def _cushion_label(parts, cx, cy, num, size=11):
    """Circled cushion number at (cx, cy)."""
    r = size * 0.7
    parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="white" stroke="{BLACK}" stroke-width="{SW_DIM}"/>')
    parts.append(_text(cx, cy + size * 0.35, f"C{num}", size, weight="bold"))


def _miter_callout(parts, x, y, angle=45):
    """Miter joint indicator at corner."""
    length = 12
    rad = math.radians(angle)
    dx = length * math.cos(rad)
    dy = length * math.sin(rad)
    parts.append(_line(x - dx, y - dy, x + dx, y + dy, SW_DIM))
    parts.append(_text(x + dx + 4, y - dy - 4, "MITER", 7, anchor="start", weight="600", fill=GRAY))


# ── BACK STYLE RENDERING ──────────────────────────────────────────

def _clip_path_polygon(parts, clip_id: str, pts: list[tuple[float, float]]) -> None:
    points = " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in pts)
    parts.append(f'<clipPath id="{clip_id}"><polygon points="{points}"/></clipPath>')


def _draw_back_style_2d(parts, x, y, w, h, panel_style, channel_count, scale=1.0):
    """Draw back panel pattern in a 2D rectangle (plan or elevation view)."""
    if panel_style in ("flat", "none", "", None):
        return
    elif panel_style == "horizontal_channels":
        count = max(2, channel_count)
        for i in range(1, count):
            cy = y + h * i / count
            parts.append(_line(x + 2, cy, x + w - 2, cy, SW_CHANNEL, LIGHT_GRAY))
    elif panel_style == "tufted" or panel_style == "button_tufted":
        # Diamond/button tufting grid — stay inside the back panel rect.
        pad = max(2.0, min(w, h) * 0.12)
        rows = max(2, channel_count // 2)
        cols = max(3, channel_count)
        y0, y1 = y + pad, y + h - pad
        x0, x1 = x + pad, x + w - pad
        for r in range(rows + 1):
            for c in range(cols + 1):
                cx = x0 + (x1 - x0) * c / cols
                cy = y0 + (y1 - y0) * r / rows
                if r % 2 == 1:
                    cx += (x1 - x0) / cols / 2
                    if cx > x1:
                        continue
                parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="1.5" fill="{GRAY}" stroke="none"/>')
        if panel_style == "tufted":
            for r in range(rows):
                for c in range(cols):
                    cx1 = x0 + (x1 - x0) * c / cols
                    cy1 = y0 + (y1 - y0) * r / rows
                    cx2 = x0 + (x1 - x0) * (c + 0.5) / cols
                    cy2 = y0 + (y1 - y0) * (r + 0.5) / rows
                    if r % 2 == 1:
                        cx1 += (x1 - x0) / cols / 2
                        cx2 += (x1 - x0) / cols / 2
                    if x0 <= cx2 <= x1 and y0 <= cy2 <= y1:
                        parts.append(_line(cx1, cy1, cx2, cy2, SW_CHANNEL, LIGHT_GRAY))
    elif panel_style == "vertical_channels":
        count = max(2, channel_count)
        for i in range(1, count):
            cx = x + w * i / count
            parts.append(_line(cx, y + 2, cx, y + h - 2, SW_CHANNEL, LIGHT_GRAY))


def _draw_back_style_iso(parts, ox, oy, scale, sx, sy_back, width, sh, bh, bt,
                         panel_style, channel_count):
    """Draw back panel pattern on isometric back face."""
    if panel_style in ("flat", "none", "", None):
        return
    elif panel_style == "horizontal_channels":
        count = max(2, channel_count)
        for i in range(1, count):
            z = sh + bh * i / count
            p1 = _iso(sx, sy_back, z, ox, oy, scale)
            p2 = _iso(sx + width, sy_back, z, ox, oy, scale)
            parts.append(_line(p1[0], p1[1], p2[0], p2[1], SW_CHANNEL))
    elif panel_style in ("tufted", "button_tufted"):
        rows = max(2, channel_count // 2)
        cols = max(3, channel_count)
        for r in range(rows + 1):
            for c in range(cols + 1):
                fx = sx + width * c / cols
                fz = sh + bh * r / rows
                if r % 2 == 1:
                    fx += width / cols / 2
                    if fx > sx + width:
                        continue
                pt = _iso(fx, sy_back, fz, ox, oy, scale)
                parts.append(f'<circle cx="{pt[0]:.1f}" cy="{pt[1]:.1f}" r="1.2" fill="{BLACK}" stroke="none"/>')
    elif panel_style == "vertical_channels":
        count = max(2, channel_count)
        for i in range(1, count):
            cx = sx + width * i / count
            p1 = _iso(cx, sy_back, sh + 1, ox, oy, scale)
            p2 = _iso(cx, sy_back, sh + bh - 1, ox, oy, scale)
            parts.append(_line(p1[0], p1[1], p2[0], p2[1], SW_CHANNEL))


def _back_style_label(panel_style, has_back=True):
    """Human-readable label for the back style. Flat stays flat."""
    return _bridge_back_label(panel_style or "flat", has_back=has_back)


# ── PLAN VIEW ──────────────────────────────────────────────────────

def _plan_straight(parts, ox, oy, scale, width, depth, seat_h, back_h,
                   cushion_width=24, panel_style="vertical_channels", channel_count=6,
                   cushion_count=None, back_thickness_in=None, back_sections=None,
                   seat_cushion_overhang_in: float = 0,
                   seat_cushion_thickness_in: float = 0):
    """Plan view — top-down rectangle with cushion dividers and numbering."""
    has_back = back_h is not None and back_h > 0 and panel_style != "none"
    bt = _back_thickness_in(has_back, back_thickness_in)
    w = width * scale
    d = depth * scale
    bt_s = bt * scale
    frame_span = d - bt_s
    oh_s = max(0.0, float(seat_cushion_overhang_in or 0)) * scale

    # Seat frame (depth = overall − back thickness)
    parts.append(_rect(ox, oy, w, frame_span, SW_HEAVY))
    if oh_s > 0.25:
        parts.append(_rect(
            ox, oy - oh_s, w, oh_s, SW_MED, fill="#E8E8E8",
        ))
        parts.append(
            f'<line x1="{ox:.1f}" y1="{oy:.1f}" x2="{ox + w:.1f}" y2="{oy:.1f}" '
            f'stroke="{GRAY}" stroke-width="{SW_LIGHT}" data-plan-overhang-edge="1"/>'
        )
    if has_back:
        # Back panel
        parts.append(_rect(ox, oy + d - bt_s, w, bt_s, SW_HEAVY, fill="#F0F0F0"))
        _draw_back_style_2d(parts, ox, oy + d - bt_s, w, bt_s, panel_style, channel_count)
        b_sec = max(1, int(back_sections or 1))
        if b_sec > 1:
            for i in range(1, b_sec):
                cx = ox + w * i / b_sec
                parts.append(_line(cx, oy + d - bt_s + 1, cx, oy + d - 1, SW_LIGHT, GRAY))

    # Cushion dividers + numbering
    if cushion_count is not None and int(cushion_count) > 0:
        c_count = int(cushion_count)
    else:
        c_count = max(1, math.ceil(width / cushion_width)) if cushion_width > 0 else 1
    seat_span = frame_span
    if c_count > 1:
        for i in range(1, c_count):
            cx = ox + w * i / c_count
            y0 = oy - oh_s if oh_s > 0.25 else oy
            parts.append(_line(cx, y0 + 2, cx, oy + seat_span - 2, SW_LIGHT, GRAY))
    # Cushion labels — shrink when the seat is too shallow to hold 11px type
    label_size = 11 if seat_span >= 28 else 8
    for i in range(c_count):
        label_x = ox + w * (i + 0.5) / c_count
        label_y = oy + seat_span / 2
        _cushion_label(parts, label_x, label_y, i + 1, size=label_size)


def _plan_l_shape(parts, ox, oy, scale, long, short, depth, seat_h, back_h,
                  cushion_width=24, panel_style="vertical_channels", channel_count=6,
                  back_thickness_in=None):
    """Plan view — L-shaped bench."""
    has_back = back_h is not None and back_h > 0 and panel_style != "none"
    bt = _back_thickness_in(has_back, back_thickness_in)
    d_s = depth * scale
    bt_s = bt * scale
    long_s = long * scale
    short_s = short * scale

    # Long section seat
    parts.append(_rect(ox, oy, long_s, d_s - bt_s, SW_HEAVY))
    if has_back:
        parts.append(_rect(ox, oy + d_s - bt_s, long_s, bt_s, SW_HEAVY, fill="#F0F0F0"))
        _draw_back_style_2d(parts, ox, oy + d_s - bt_s, long_s, bt_s, panel_style, channel_count)

    # Short wing
    wing_x = ox + long_s - d_s + bt_s
    wing_y = oy + d_s
    wing_w = d_s - bt_s
    wing_h = short_s - d_s
    if wing_h > 0:
        parts.append(_rect(wing_x, wing_y, wing_w, wing_h, SW_HEAVY))
        if has_back:
            parts.append(_rect(wing_x + wing_w, wing_y, bt_s, wing_h, SW_HEAVY, fill="#F0F0F0"))

    _miter_callout(parts, ox + long_s - d_s + bt_s, oy + d_s)

    # Cushion labels
    c_long = max(1, math.ceil(long / cushion_width)) if cushion_width > 0 else 1
    for i in range(c_long):
        cx = ox + long_s * (i + 0.5) / c_long
        _cushion_label(parts, cx, oy + (d_s - bt_s) / 2, i + 1)

    if wing_h > 0:
        c_wing = max(1, math.ceil(short / cushion_width)) if cushion_width > 0 else 1
        _cushion_label(parts, wing_x + wing_w / 2, wing_y + wing_h / 2, c_long + 1)


def _plan_u_shape(parts, ox, oy, scale, back, side, depth, side_depth, seat_h, back_h,
                  cushion_width=24, panel_style="vertical_channels", channel_count=6,
                  side_left=None, side_right=None, back_thickness_in=None):
    """Plan view — U-shaped booth.

    side_left / side_right: optional asymmetric wing projections (inches).
    When omitted, both wings use `side` (legacy symmetric behavior).
    Cushion labels are counted per run: ceil(run/cushion_width) each.
    """
    has_back = back_h is not None and back_h > 0 and panel_style != "none"
    bt = _back_thickness_in(has_back, back_thickness_in)
    sl = float(side_left) if side_left not in (None, 0, "") else float(side)
    sr = float(side_right) if side_right not in (None, 0, "") else float(side)
    side_max = max(sl, sr)
    d_s = depth * scale
    sd_s = side_depth * scale
    bt_s = bt * scale
    back_s = back * scale
    sl_s = sl * scale
    sr_s = sr * scale
    side_max_s = side_max * scale
    total_w = (back + side_depth * 2) * scale

    # Left wing — bottom-aligned so longer wing defines oy baseline
    left_y = oy + (side_max_s - sl_s)
    parts.append(_rect(ox, left_y, sd_s - bt_s, sl_s, SW_HEAVY))
    if has_back:
        parts.append(_rect(ox - bt_s, left_y, bt_s, sl_s, SW_HEAVY, fill="#F0F0F0"))

    # Center back — at far end of longer wing
    cx = ox + sd_s
    cy = oy + side_max_s - d_s
    parts.append(_rect(cx, cy, back_s, d_s - bt_s, SW_HEAVY))
    if has_back:
        parts.append(_rect(cx, cy + d_s - bt_s, back_s, bt_s, SW_HEAVY, fill="#F0F0F0"))
        _draw_back_style_2d(parts, cx, cy + d_s - bt_s, back_s, bt_s, panel_style, channel_count)

    # Right wing
    rx = ox + sd_s + back_s
    right_y = oy + (side_max_s - sr_s)
    parts.append(_rect(rx + bt_s, right_y, sd_s - bt_s, sr_s, SW_HEAVY))
    if has_back:
        parts.append(_rect(rx + sd_s, right_y, bt_s, sr_s, SW_HEAVY, fill="#F0F0F0"))

    _miter_callout(parts, cx, cy + d_s - bt_s)
    _miter_callout(parts, rx, cy + d_s - bt_s)

    # Cushion labels per run
    idx = 1
    c_left = max(1, math.ceil(sl / cushion_width)) if cushion_width > 0 else 1
    for i in range(c_left):
        _cushion_label(parts, ox + (sd_s - bt_s) / 2,
                       left_y + sl_s * (i + 0.5) / c_left, idx)
        idx += 1
    c_back = max(1, math.ceil(back / cushion_width)) if cushion_width > 0 else 1
    for i in range(c_back):
        _cushion_label(parts, cx + back_s * (i + 0.5) / c_back,
                       cy + (d_s - bt_s) / 2, idx)
        idx += 1
    c_right = max(1, math.ceil(sr / cushion_width)) if cushion_width > 0 else 1
    for i in range(c_right):
        _cushion_label(parts, rx + bt_s + (sd_s - bt_s) / 2,
                       right_y + sr_s * (i + 0.5) / c_right, idx)
        idx += 1


# ── FRONT ELEVATION ───────────────────────────────────────────────

def _side_straight(parts, ox, oy, scale, depth, seat_h, back_h,
                   panel_style="vertical_channels", channel_count=6,
                   panel_w: float = 0, panel_h: float = 0, draw_dims: bool = True,
                   split_panel: bool = False, back_thickness_in=None,
                   seat_cushion_thickness_in: float = 0, back_angle_deg: float = 0,
                   seat_cushion_overhang_in: float = 0, frame_depth_in: float | None = None):
    """Side elevation — stated depth is full frame; back cushion sits inside at rear."""
    has_back = back_h is not None and back_h > 0 and panel_style != "none"
    bt_in = _back_thickness_in(has_back, back_thickness_in)
    overall_depth = float(frame_depth_in) if frame_depth_in is not None else float(depth)
    usable_seat_depth = max(0.0, overall_depth - bt_in) if has_back else overall_depth
    oh_in = max(0.0, float(seat_cushion_overhang_in or 0))
    frame_d = overall_depth * scale
    bt_s = bt_in * scale
    usable_d = usable_seat_depth * scale
    d = frame_d
    sh = seat_h * scale
    bh = (back_h if has_back else 0) * scale
    cush_in = max(0.0, float(seat_cushion_thickness_in or 0))
    cush_s = min(cush_in * scale, sh - 1)
    deck_s = sh - cush_s
    oh_s = oh_in * scale
    rake_deg = float(back_angle_deg or 0)
    if rake_deg > 0 and has_back:
        lean = (back_h if has_back else 0) * scale * math.tan(math.radians(rake_deg))
        lean = min(lean, 4.0 * scale)
    else:
        lean = 0.0
    top_y = oy - sh - bh
    parts.append(
        f'<line x1="{ox:.1f}" y1="{oy:.1f}" x2="{ox + d:.1f}" y2="{oy:.1f}" '
        f'stroke="{GRAY}" stroke-width="{SW_FLOOR}" stroke-dasharray="6,3" '
        f'data-side-floor="1"/>'
    )
    parts.append(_rect(ox, oy - deck_s, frame_d, deck_s, SW_HEAVY))
    if cush_s > 0.5:
        cush_w = usable_d + oh_s
        parts.append(_rect(ox - oh_s, oy - sh, cush_w, cush_s, SW_MED, fill="#E8E8E8"))
        parts.append(_line(ox, oy - deck_s, ox + frame_d, oy - deck_s, SW_LIGHT, GRAY))
    if has_back:
        bx_front = ox + frame_d - bt_s
        bx_rear = ox + frame_d
        angle_attr = f' data-back-angle-deg="{rake_deg:.2f}"'
        back_pts = [
            (bx_front, oy - sh),
            (bx_rear, oy - sh),
            (bx_rear + lean, top_y),
            (bx_front + lean, top_y),
        ]
        parts.append(_poly(back_pts, SW_MED, attrs=f'data-side-back="1"{angle_attr}'))
        if panel_style in ("tufted", "button_tufted"):
            clip_id = f"side-back-{uuid.uuid4().hex[:8]}"
            parts.append("<defs>")
            _clip_path_polygon(parts, clip_id, back_pts)
            parts.append("</defs>")
            parts.append(f'<g clip-path="url(#{clip_id})" data-side-back-tuft="1">')
            _draw_back_style_2d(
                parts, bx_front, top_y, bt_s + lean, bh,
                panel_style, channel_count,
            )
            parts.append("</g>")
        else:
            _draw_back_style_2d(
                parts, bx_front, top_y, bt_s + lean, bh,
                panel_style, channel_count,
            )
    if not draw_dims or panel_w < 20:
        return
    dim_band_h = 30.0
    raked = rake_deg > 0.05
    if split_panel:
        _dim_h_local(parts, ox, ox + frame_d, oy, 50, f'{_in(overall_depth)}')
        if has_back and bt_s > 1:
            _dim_h_local(
                parts, ox + frame_d - bt_s, ox + frame_d, oy, 30,
                _in(bt_in),
            )
            _dim_h_local(
                parts, ox, ox + frame_d - bt_s, oy, 14,
                f'{_in(usable_seat_depth)} SEAT',
            )
        if oh_s > 0.25:
            oh_y = oy - sh - 10
            parts.append(_line(ox - oh_s, oh_y, ox - oh_s, oy - sh + 2, SW_EXT, DIM_COLOR, dim_ext=True))
            parts.append(_line(ox, oh_y, ox, oy - sh + 2, SW_EXT, DIM_COLOR, dim_ext=True))
            parts.append(
                f'<line x1="{ox - oh_s:.1f}" y1="{oh_y:.1f}" x2="{ox:.1f}" y2="{oh_y:.1f}" '
                f'stroke="{DIM_COLOR}" stroke-width="{SW_DIM}" data-dim-stroke="1" '
                f'marker-start="url(#dim-arrow)" marker-end="url(#dim-arrow)"/>'
            )
            parts.append(_text((ox - oh_s + ox) / 2, oh_y - 6, f'{_in(oh_in)} OH', 9,
                               weight="600", fill=DIM_COLOR))
        _elev_height_dims_right(
            parts, ox + d, top_y, oy - sh, oy,
            seat_h, back_h if has_back else 0, panel_w=panel_w,
            seat_cushion_thickness_in=cush_in,
            deck_height_in=max(0.0, float(seat_h) - cush_in),
            include_overall=False,
            y_deck_px=oy - deck_s,
            force_seat_breakdown=True,
            skip_back_height=raked,
        )
        if has_back and bh > 1 and raked:
            rear_off = max(22.0, bt_s + 14.0)
            _dim_oblique_rear(
                parts, (bx_front, oy - sh), (bx_front + lean, top_y),
                f'{_in(back_h)} BH', offset=rear_off,
                attrs=' data-side-bh="1"',
            )
        return
    _gutter_width(
        parts, ox, ox + d, oy,
        Rect(ox, min(oy + 4, panel_h - dim_band_h), max(d, 20), dim_band_h),
        _in(depth),
    )
    total_h = seat_h + (back_h if has_back else 0)
    dim_w = 34.0
    right_band = Rect(
        min(ox + d + 6, panel_w - dim_w - 2),
        max(top_y - 6, 8),
        dim_w,
        max(oy - top_y + 12, 24),
    )
    _gutter_height(
        parts, top_y, oy, ox + d + 4,
        right_band,
        _in(total_h), side="right",
    )
    if has_back and bh > 2 and not split_panel:
        sh_y = oy - sh / 2 + 4
        bh_y = top_y + bh / 2 + 4
        sh_y, bh_y = _separate_baseline(sh_y, bh_y, gap=16)
        left_band = Rect(4, max(top_y - 4, 8), 28, max(oy - top_y + 12, 24))
        _gutter_height(
            parts, oy, oy - sh, ox, left_band,
            _in(seat_h) + " SH", side="left", label_y=sh_y,
        )
        _gutter_height(
            parts, oy - sh, top_y, ox, left_band,
            _in(back_h) + " BH", side="left", label_y=bh_y,
        )
    elif has_back and bh > 2 and split_panel:
        sh_y = oy - sh / 2 + 4
        bh_y = top_y + bh / 2 + 4
        sh_y, bh_y = _separate_baseline(sh_y, bh_y, gap=16)
        right_band = Rect(min(ox + d + 8, panel_w - 34), max(top_y - 4, 8), 32, max(oy - top_y + 12, 28))
        _gutter_height(
            parts, oy, oy - sh, ox + d, right_band,
            _in(seat_h) + " SH", side="right", label_y=sh_y,
        )
        _gutter_height(
            parts, oy - sh, top_y, ox + d, right_band,
            _in(back_h) + " BH", side="right", label_y=bh_y,
        )


def _elev_straight(parts, ox, oy, scale, width, depth, seat_h, back_h,
                   panel_style="vertical_channels", channel_count=6,
                   panel_w: float = 0, panel_h: float = 0, cushion_count: int = 1,
                   draw_dims: bool = True, split_panel: bool = False,
                   back_sections: int = 1, seat_cushion_thickness_in: float = 0):
    """Front elevation with floor line, seat, back, and dimensions."""
    has_back = back_h is not None and back_h > 0 and panel_style != "none"
    w = width * scale
    sh = seat_h * scale
    bh = (back_h if has_back else 0) * scale
    top_y = oy - sh - bh
    cush_in = max(0.0, float(seat_cushion_thickness_in or 0))
    cush_s = min(cush_in * scale, sh - 1)
    deck_s = sh - cush_s

    # Floor line (dashed). "FL" sits on the seat, clear of the left gutter dim.
    parts.append(_line(ox - 4, oy, ox + w + 4, oy, SW_FLOOR, GRAY, "6,3"))
    if not split_panel:
        parts.append(_text(ox + 6, oy - 8, "FL", 9, anchor="start", fill=GRAY))

    parts.append(_rect(ox, oy - deck_s, w, deck_s, SW_HEAVY))
    if cush_s > 0.5:
        parts.append(_rect(ox, oy - sh, w, cush_s, SW_MED, fill="#E8E8E8"))
        parts.append(_line(ox, oy - deck_s, ox + w, oy - deck_s, SW_LIGHT, GRAY))
    if has_back:
        parts.append(_rect(ox, oy - sh - bh, w, bh, SW_MED))
        _draw_back_style_2d(parts, ox, oy - sh - bh, w, bh, panel_style, channel_count)
        b_sec = max(1, int(back_sections or 1))
        if b_sec > 1:
            for i in range(1, b_sec):
                cx = ox + w * i / b_sec
                parts.append(_line(cx, oy - sh - bh + 1, cx, oy - sh - 1, SW_LIGHT, GRAY))
        parts.append(_line(ox, oy - sh, ox + w, oy - sh, SW_MED))
    else:
        parts.append(_text(ox + w / 2, oy - sh - 14, "NO BACK", 10, fill=GRAY, weight="600"))

    if not draw_dims or panel_w < 20:
        return
    cw = width / max(1, cushion_count)
    bsw = width / max(1, int(back_sections or 1))
    dim_band_h = 30.0
    if split_panel:
        if cushion_count > 1:
            _dim_h_section_splits(
                parts, ox, w, cushion_count, cw, oy - sh,
                above=False, v_gap=14,
            )
        if has_back and int(back_sections or 1) > 1:
            _dim_h_section_splits(
                parts, ox, w, int(back_sections or 1), bsw, top_y,
                above=True, v_gap=16,
            )
        _dim_h_local(parts, ox, ox + w, oy, 18, _in(width))
        _elev_height_dims_right(
            parts, ox + w, top_y, oy - sh, oy,
            seat_h, back_h if has_back else 0, panel_w=panel_w,
            seat_cushion_thickness_in=cush_in,
            deck_height_in=max(0.0, float(seat_h) - cush_in),
            include_overall=False,
        )
    else:
        bottom_band = Rect(ox, min(oy + 2, panel_h - dim_band_h - 4), w, dim_band_h)
        _gutter_width(parts, ox, ox + w, oy, bottom_band, _in(width))
        if cushion_count > 1:
            seg_band = Rect(ox, min(oy + 2, panel_h - dim_band_h - 22), w, 18)
            sec_px = w / cushion_count
            unit = _fmt_in(cw)
            if _section_dims_should_collapse(cushion_count, sec_px, unit):
                _gutter_width(
                    parts, ox, ox + w, oy - sh, seg_band,
                    _chained_section_dim_label(cushion_count, cw),
                )
            else:
                for i in range(cushion_count):
                    x1 = ox + w * i / cushion_count
                    x2 = ox + w * (i + 1) / cushion_count
                    _gutter_width(parts, x1, x2, oy - sh, seg_band, unit)
        left_band = Rect(4, max(top_y - 4, 8), 30, max(oy - top_y + 12, 28))
        _gutter_height(parts, top_y, oy, ox, left_band, _in(seat_h + (back_h if has_back else 0)), side="left")
        if has_back and bh > 2:
            sh_y = oy - sh / 2 + 4
            bh_y = top_y + bh / 2 + 4
            sh_y, bh_y = _separate_baseline(sh_y, bh_y, gap=16)
            right_band = Rect(min(ox + w + 6, panel_w - 32), max(top_y - 4, 8), 30, max(oy - top_y + 12, 28))
            _gutter_height(parts, oy, oy - sh, ox + w, right_band, _in(seat_h) + " SH", side="right", label_y=sh_y)
            _gutter_height(parts, oy - sh, top_y, ox + w, right_band, _in(back_h) + " BH", side="right", label_y=bh_y)


def _elev_l_shape(parts, ox, oy, scale, long, short, depth, seat_h, back_h,
                  panel_style="vertical_channels", channel_count=6):
    _elev_straight(parts, ox, oy, scale, long, depth, seat_h, back_h, panel_style, channel_count)


def _elev_u_shape(parts, ox, oy, scale, back, side, depth, side_depth, seat_h, back_h,
                  panel_style="vertical_channels", channel_count=6):
    total_w = back + side_depth * 2
    _elev_straight(parts, ox, oy, scale, total_w, depth, seat_h, back_h, panel_style, channel_count)
    # Wing boundary lines
    sd_s = side_depth * scale
    w = total_w * scale
    parts.append(_line(ox + sd_s, oy, ox + sd_s, oy - (seat_h + back_h) * scale, SW_LIGHT, GRAY))
    parts.append(_line(ox + w - sd_s, oy, ox + w - sd_s, oy - (seat_h + back_h) * scale, SW_LIGHT, GRAY))


# ── ISOMETRIC BENCH BOX ──────────────────────────────────────────

def _draw_bench_box(parts, ox, oy, scale, sx, sy, width, depth, seat_h, back_h,
                    panel_style="vertical_channels", channel_count=6,
                    back_thickness_in=None, seat_sections: int = 1,
                    back_sections: int = 1, seat_cushion_thickness_in: float = 0):
    """Draw one bench section in isometric: closed seat solid + back panel."""
    w, d, sh, bh = width, depth, seat_h, back_h
    has_back = bh is not None and bh > 0 and panel_style != "none"
    bt = _back_thickness_in(has_back, back_thickness_in)
    y_seat_rear = sy + d - (bt if has_back else 0)
    y_back = sy + d

    # Seat — five closed faces (no dangling edges)
    _iso_face(parts, ox, oy, scale, [
        (sx, sy, 0), (sx + w, sy, 0), (sx + w, sy, sh), (sx, sy, sh),
    ], sw=SW_HEAVY)
    _iso_face(parts, ox, oy, scale, [
        (sx, sy, sh), (sx + w, sy, sh), (sx + w, y_seat_rear, sh), (sx, y_seat_rear, sh),
    ], sw=SW_MED)
    _iso_face(parts, ox, oy, scale, [
        (sx, sy, 0), (sx, y_seat_rear, 0), (sx, y_seat_rear, sh), (sx, sy, sh),
    ], sw=SW_MED)
    _iso_face(parts, ox, oy, scale, [
        (sx + w, sy, 0), (sx + w, y_seat_rear, 0), (sx + w, y_seat_rear, sh), (sx + w, sy, sh),
    ], sw=SW_MED)
    _iso_face(parts, ox, oy, scale, [
        (sx, y_seat_rear, 0), (sx + w, y_seat_rear, 0),
        (sx + w, y_seat_rear, sh), (sx, y_seat_rear, sh),
    ], sw=SW_MED)

    cush_in = max(0.0, float(seat_cushion_thickness_in or 0))
    if cush_in > 0.05 and cush_in < sh:
        cz0 = sh - cush_in
        _iso_face(parts, ox, oy, scale, [
            (sx, sy, cz0), (sx + w, sy, cz0), (sx + w, sy, sh), (sx, sy, sh),
        ], sw=SW_MED, fill="#E8E8E8")
        _iso_face(parts, ox, oy, scale, [
            (sx, y_seat_rear, cz0), (sx + w, y_seat_rear, cz0),
            (sx + w, y_seat_rear, sh), (sx, y_seat_rear, sh),
        ], sw=SW_LIGHT, fill="#E8E8E8")

    s_sec = max(1, int(seat_sections or 1))
    if s_sec > 1:
        for i in range(1, s_sec):
            cx = sx + w * i / s_sec
            p1 = _iso(cx, sy, sh - 0.5, ox, oy, scale)
            p2 = _iso(cx, y_seat_rear, sh - 0.5, ox, oy, scale)
            parts.append(_line(p1[0], p1[1], p2[0], p2[1], SW_LIGHT, GRAY))

    if not has_back:
        return

    # Back — front, top, left end, right end (rear face omitted — not visible)
    _iso_face(parts, ox, oy, scale, [
        (sx, y_seat_rear, sh), (sx + w, y_seat_rear, sh),
        (sx + w, y_seat_rear, sh + bh), (sx, y_seat_rear, sh + bh),
    ], sw=SW_HEAVY)
    _iso_face(parts, ox, oy, scale, [
        (sx, y_seat_rear, sh + bh), (sx + w, y_seat_rear, sh + bh),
        (sx + w, y_back, sh + bh), (sx, y_back, sh + bh),
    ], sw=SW_MED)
    _iso_face(parts, ox, oy, scale, [
        (sx, y_seat_rear, sh), (sx, y_back, sh),
        (sx, y_back, sh + bh), (sx, y_seat_rear, sh + bh),
    ], sw=SW_MED)
    _iso_face(parts, ox, oy, scale, [
        (sx + w, y_seat_rear, sh), (sx + w, y_back, sh),
        (sx + w, y_back, sh + bh), (sx + w, y_seat_rear, sh + bh),
    ], sw=SW_MED)

    b_sec = max(1, int(back_sections or 1))
    if b_sec > 1:
        for i in range(1, b_sec):
            cx = sx + w * i / b_sec
            p1 = _iso(cx, y_seat_rear, sh + 1, ox, oy, scale)
            p2 = _iso(cx, y_seat_rear, sh + bh - 1, ox, oy, scale)
            parts.append(_line(p1[0], p1[1], p2[0], p2[1], SW_LIGHT, GRAY))

    _draw_back_style_iso(parts, ox, oy, scale, sx, y_seat_rear, width, sh, bh, bt,
                         panel_style, channel_count)


# ── TITLE BLOCK ──────────────────────────────────────────────────

def _title_rows(name="", quote_num="", dims_text="", bench_type="STRAIGHT",
                cushion_count=1, cushion_width=24, panel_style="vertical_channels",
                client="", project="", date="", assumptions=None, has_back=True,
                drawn_by="MAX AI", back_cushion_count=None, back_cushion_width=None):
    rows = [
        ("ITEM:", (name or "BENCH").upper()),
        ("TYPE:", bench_type.upper().replace("_", " ")),
        ("DIMENSIONS:", dims_text or "SEE VIEWS"),
        ("SEAT CUSHIONS:", f"{cushion_count} @ {_fmt_in(cushion_width)}"),
        ("BACK CUSHIONS:", f"{(back_cushion_count or cushion_count)} @ "
         f"{_fmt_in(back_cushion_width if back_cushion_width is not None else cushion_width)}"),
        ("BACK STYLE:", _back_style_label(panel_style, has_back=has_back)),
    ]
    if client:
        rows.append(("CLIENT:", client.upper()))
    if project:
        rows.append(("PROJECT:", project.upper()))
    if quote_num:
        rows.append(("QUOTE:", quote_num))
    rows.append(("DATE:", date or datetime.now().strftime("%m/%d/%Y")))
    rows.append(("DRAWN BY:", drawn_by))
    for note in assumptions or []:
        if note:
            rows.append(("NOTE:", note))
    return rows


def _paint_title_ops(parts, ox, oy, ops):
    """Paint top-down title-block ops into SVG coordinates."""
    fills = {
        "ink": BLACK,
        "mute": GRAY,
        "chip": "#f4efe2",
    }
    for op in ops:
        kind = op["kind"]
        if kind == "text":
            parts.append(_text(
                ox + op["x"], oy + op["y"], op["text"], op["size"],
                anchor=op.get("anchor", "start"),
                weight=op.get("weight", "normal"),
                fill=fills.get(op.get("fill", "ink"), BLACK),
            ))
        elif kind == "rule":
            parts.append(_line(ox + op["x1"], oy + op["y"], ox + op["x2"], oy + op["y"], 0.6, GRAY))
        elif kind == "rect":
            parts.append(_rect(
                ox + op["x"], oy + op["y"], op["w"], op["h"], 0.4,
                fill=fills.get(op.get("fill", "chip"), "#f4efe2"),
                stroke="#e4dcc8",
            ))


def _title_block(parts, x, y, w, h, name="", quote_num="", dims_text="",
                 bench_type="STRAIGHT", cushion_count=1, cushion_width=24,
                 panel_style="vertical_channels", client="", project="", date="",
                 category_chip="", chrome=None, assumptions=None, has_back=True,
                 back_cushion_count=None, back_cushion_width=None):
    """Title block. WoodCraft sheets use WC chrome, not Workroom letterhead."""
    brand = chrome or _bridge_chrome("workroom")
    parts.append(_rect(x, y, w, h, 1.0, stroke="#20241f"))
    rows = _title_rows(
        name=name, quote_num=quote_num, dims_text=dims_text,
        bench_type=bench_type, cushion_count=cushion_count,
        cushion_width=cushion_width, panel_style=panel_style,
        client=client, project=project, date=date,
        assumptions=assumptions, has_back=has_back,
        drawn_by=brand.get("drawn_by") or "MAX AI",
        back_cushion_count=back_cushion_count,
        back_cushion_width=back_cushion_width,
    )
    ops = layout_title_block(w, h, brand, rows, category_chip, SVG_TYPE)
    _paint_title_ops(parts, x, y, ops)


# ── VIEW FRAME ───────────────────────────────────────────────────

def _view_frame(parts, frame, label, aside=""):
    """Framed view with a caption band. Dims belong in the gutters below."""
    parts.append(_rect(frame.x, frame.y, frame.w, frame.h, 0.8, stroke="#20241f"))
    parts.append(_rect(frame.x, frame.y, frame.w, CAPTION_H, 0, fill="#f6f3ec", stroke="none"))
    parts.append(_line(frame.x, frame.y + CAPTION_H, frame.right, frame.y + CAPTION_H, 0.6, "#c8c2b4"))
    parts.append(_text(
        frame.x + 10, frame.y + 17, label, SVG_TYPE["caption"],
        anchor="start", weight="bold",
    ))
    if aside:
        parts.append(_text(
            frame.right - 10, frame.y + 17, aside, 10,
            anchor="end", weight="600", fill=GRAY,
        ))


def _gutter_width(parts, x1, x2, obj_y, band, label):
    """Horizontal dimension in the bottom gutter, under the object."""
    if band.w < 8 or band.h < 8:
        return
    y = band.y + 14
    parts.append(_line(x1, obj_y + 2, x1, y + 3, SW_EXT, DIM_COLOR))
    parts.append(_line(x2, obj_y + 2, x2, y + 3, SW_EXT, DIM_COLOR))
    parts.append(
        f'<line x1="{x1:.1f}" y1="{y:.1f}" x2="{x2:.1f}" y2="{y:.1f}" '
        f'stroke="{DIM_COLOR}" stroke-width="{SW_DIM}" '
        f'marker-start="url(#dim-arrow)" marker-end="url(#dim-arrow)"/>'
    )
    parts.append(_text((x1 + x2) / 2, min(band.bottom - 4, y + 15), label,
                       SVG_TYPE["dim"], weight="600", fill=DIM_COLOR))


def _gutter_height(parts, y1, y2, obj_x, band, label, side="left", label_y=None):
    """Vertical dimension. Text stays inside the gutter, horizontal."""
    if band.w < 8 or band.h < 8:
        return
    top, bot = (y1, y2) if y1 < y2 else (y2, y1)
    if side == "left":
        x = band.right - 12
        text_x = band.x + 4
        anchor = "start"
    else:
        x = band.x + 12
        text_x = band.right - 4
        anchor = "end"
    parts.append(_line(obj_x - 2 if side == "left" else obj_x + 2, top, x, top, SW_EXT, DIM_COLOR))
    parts.append(_line(obj_x - 2 if side == "left" else obj_x + 2, bot, x, bot, SW_EXT, DIM_COLOR))
    parts.append(
        f'<line x1="{x:.1f}" y1="{top:.1f}" x2="{x:.1f}" y2="{bot:.1f}" '
        f'stroke="{DIM_COLOR}" stroke-width="{SW_DIM}" '
        f'marker-start="url(#dim-arrow)" marker-end="url(#dim-arrow)"/>'
    )
    ly = (top + bot) / 2 + 4 if label_y is None else label_y
    ly = min(max(ly, band.y + 12), band.bottom - 4)
    parts.append(_text(text_x, ly, label, SVG_TYPE["dim"],
                       anchor=anchor, weight="600", fill=DIM_COLOR))


def _separate_baseline(y_a, y_b, gap=16):
    """Push two baselines apart when they would share a line."""
    if abs(y_a - y_b) >= gap:
        return y_a, y_b
    mid = (y_a + y_b) / 2
    if y_a <= y_b:
        return mid - gap / 2, mid + gap / 2
    return mid + gap / 2, mid - gap / 2


# ── BUILD FUNCTIONS (isometric) ──────────────────────────────────

# Right and bottom lanes inside the iso panel. Geometry scales into
# the remaining box so callouts cannot sit on the linework.
_ISO_LANE_R = 52
_ISO_LANE_B = 40


def _iso_fit(dims_3d, svg_w, svg_h):
    return _auto_scale(
        dims_3d,
        max(48, svg_w - _ISO_LANE_R),
        max(48, svg_h - _ISO_LANE_B),
        margin=8,
    )


def _iso_callouts(parts, svg_w, svg_h, width_label, width_pts, stack):
    """Overall width in the bottom lane. Other callouts stacked on the right.

    ``stack`` is (label, target_xy) from top to bottom. Baselines are
    spaced across the lane so the labels cannot collide.
    """
    p1, p2 = width_pts
    x1, x2 = (p1[0], p2[0]) if p1[0] <= p2[0] else (p2[0], p1[0])
    y_text = svg_h - 14
    y_line = y_text - 12
    parts.append(_line(x1, y_line - 4, x1, y_line + 4, SW_EXT, DIM_COLOR))
    parts.append(_line(x2, y_line - 4, x2, y_line + 4, SW_EXT, DIM_COLOR))
    parts.append(_line(x1, y_line, x2, y_line, SW_DIM, DIM_COLOR))
    parts.append(_text((x1 + x2) / 2, y_text, width_label, SVG_TYPE["dim"],
                       weight="600", fill=DIM_COLOR))

    n = len(stack)
    if n == 0:
        return
    top = 16
    bot = svg_h - _ISO_LANE_B - 10
    if bot - top < n * 16:
        top = 8
        bot = svg_h - 8
    if n == 1:
        ys = [(top + bot) / 2]
    else:
        step = (bot - top) / (n - 1)
        ys = [top + i * step for i in range(n)]
    text_x = svg_w - 6
    leader_x = svg_w - _ISO_LANE_R + 8
    for (label, target), ly in zip(stack, ys):
        parts.append(_line(target[0], target[1], leader_x, ly - 3, 0.6, DIM_COLOR))
        parts.append(_text(text_x, ly, label, SVG_TYPE["dim"],
                           anchor="end", weight="600", fill=DIM_COLOR))


def _iso_callouts_compact(
    parts, ox, oy, scale, width_in, depth_in, seat_h_in, back_h_in, has_back,
    svg_w: float, svg_h: float,
):
    """Iso dims: width/depth along bottom edges; vertical SH/BH right of front edge."""
    interior = _iso_bench_centroid(
        width_in, depth_in, seat_h_in, back_h_in, has_back, ox, oy, scale,
    )
    face_polys = _iso_straight_face_polys(
        width_in, depth_in, seat_h_in, back_h_in, has_back, ox, oy, scale,
    )
    max_sx = _iso_bench_screen_max_x(
        width_in, depth_in, seat_h_in, back_h_in, has_back, ox, oy, scale,
    )
    dim_inner_x = max_sx + 14
    dim_outer_x = max_sx + 24

    p1 = _iso(0, 0, 0, ox, oy, scale)
    p2 = _iso(width_in, 0, 0, ox, oy, scale)
    _dim_along_edge_clear(parts, p1, p2, _in(width_in), interior, face_polys, 12)
    # Right-bottom depth stroke cannot clear iso face projections at ≤30px extensions;
    # use the parallel left floor edge for the depth chain.
    ld1 = _iso(0, 0, 0, ox, oy, scale)
    ld2 = _iso(0, depth_in, 0, ox, oy, scale)
    _dim_along_edge_clear(
        parts, ld1, ld2, f'{_in(depth_in)} frame', interior, face_polys, 18,
    )
    total_z = seat_h_in + (back_h_in if has_back else 0)
    pf = _iso(width_in, 0, 0, ox, oy, scale)
    ps = _iso(width_in, 0, seat_h_in, ox, oy, scale)
    _dim_v_at_screen_x(parts, pf, ps, f'{_in(seat_h_in)} SH', dim_inner_x)
    if has_back:
        pt = _iso(width_in, 0, total_z, ox, oy, scale)
        _dim_v_at_screen_x(parts, ps, pt, f'{_in(back_h_in)} BH', dim_inner_x)
        _dim_v_at_screen_x(parts, pf, pt, _in(total_z), dim_outer_x)


def _build_straight(name, width_in, depth_in, seat_h_in, back_h_in, quote_num="",
                    svg_w=500, svg_h=350, panel_style="vertical_channels", channel_count=6,
                    back_thickness_in=None, seat_sections: int = 1, back_sections: int = 1,
                    seat_cushion_thickness_in: float = 0):
    has_back = back_h_in is not None and back_h_in > 0 and panel_style != "none"
    total_h = seat_h_in + (back_h_in if has_back else 0)
    scale, ox, oy = _iso_fit((width_in, depth_in, total_h), svg_w, svg_h)
    parts = []
    _draw_bench_box(
        parts, ox, oy, scale, 0, 0, width_in, depth_in, seat_h_in, back_h_in,
        panel_style, channel_count,
        back_thickness_in=back_thickness_in,
        seat_sections=seat_sections,
        back_sections=back_sections,
        seat_cushion_thickness_in=seat_cushion_thickness_in,
    )

    _iso_callouts_compact(
        parts, ox, oy, scale, width_in, depth_in, seat_h_in, back_h_in, has_back, svg_w, svg_h,
    )
    return parts, scale, ox, oy


def _build_l_shape(name, long_in, short_in, depth_in, seat_h_in, back_h_in, quote_num="",
                   svg_w=500, svg_h=350, panel_style="vertical_channels", channel_count=6):
    has_back = back_h_in is not None and back_h_in > 0 and panel_style != "none"
    total_h = seat_h_in + (back_h_in if has_back else 0)
    scale, ox, oy = _iso_fit((long_in, short_in, total_h), svg_w, svg_h)
    parts = []

    _draw_bench_box(parts, ox, oy, scale, 0, short_in - depth_in, long_in, depth_in, seat_h_in, back_h_in,
                    panel_style, channel_count)
    _draw_bench_box(parts, ox, oy, scale, long_in - depth_in, 0, depth_in, short_in, seat_h_in, back_h_in,
                    panel_style, channel_count)

    stack = [(f'{_in(short_in)}', _iso(long_in, short_in, 0, ox, oy, scale))]
    stack.append((f'{_in(depth_in)} D', _iso(long_in, short_in - depth_in, 0, ox, oy, scale)))
    if has_back:
        stack.append((
            f'{_in(back_h_in)} BH',
            _iso(long_in, short_in, total_h, ox, oy, scale),
        ))
    stack.append((f'{_in(seat_h_in)} SH', _iso(long_in, 0, seat_h_in, ox, oy, scale)))
    _iso_callouts(
        parts, svg_w, svg_h, f'{_in(long_in)}',
        (_iso(0, 0, 0, ox, oy, scale), _iso(long_in, 0, 0, ox, oy, scale)),
        stack,
    )
    return parts, scale, ox, oy


def _build_u_shape(name, back_in, side_in, depth_in, side_depth_in, seat_h_in, back_h_in,
                   quote_num="", svg_w=500, svg_h=350,
                   panel_style="vertical_channels", channel_count=6):
    has_back = back_h_in is not None and back_h_in > 0 and panel_style != "none"
    total_h = seat_h_in + (back_h_in if has_back else 0)
    total_w = back_in + side_depth_in * 2
    scale, ox, oy = _iso_fit((total_w, side_in, total_h), svg_w, svg_h)
    parts = []

    _draw_bench_box(parts, ox, oy, scale, 0, 0, side_depth_in, side_in, seat_h_in, back_h_in,
                    panel_style, channel_count)
    _draw_bench_box(parts, ox, oy, scale, side_depth_in, side_in - depth_in, back_in, depth_in, seat_h_in, back_h_in,
                    panel_style, channel_count)
    _draw_bench_box(parts, ox, oy, scale, side_depth_in + back_in, 0, side_depth_in, side_in, seat_h_in, back_h_in,
                    panel_style, channel_count)

    stack = [
        (f'{_in(side_in)}', _iso(0, side_in, 0, ox, oy, scale)),
        (f'{_in(depth_in)} D', _iso(side_depth_in, side_in, 0, ox, oy, scale)),
    ]
    if has_back:
        stack.append((
            f'{_in(back_h_in)} BH',
            _iso(total_w, side_in, total_h, ox, oy, scale),
        ))
    stack.append((f'{_in(seat_h_in)} SH', _iso(total_w, 0, seat_h_in, ox, oy, scale)))
    _iso_callouts(
        parts, svg_w, svg_h, f'{_in(total_w)}',
        (_iso(0, 0, 0, ox, oy, scale), _iso(total_w, 0, 0, ox, oy, scale)),
        stack,
    )
    return parts, scale, ox, oy


# ── MULTI-VIEW COMPOSITION ──────────────────────────────────────

def _sheet_header(parts, frame, chip, quote_num, sheet_kind="idea"):
    parts.append(_rect(frame.x, frame.y, frame.w, frame.h, 0, fill="#f6f3ec", stroke="none"))
    parts.append(_line(frame.x, frame.bottom, frame.right, frame.bottom, 1.4, "#b8912f"))
    if chip:
        parts.append(_text(
            frame.x + 12, frame.y + 23, chip, SVG_TYPE["caption"],
            anchor="start", weight="bold",
        ))
    right_title = "SHOP DRAWING" if sheet_kind == "shop" else "IDEA SHEET"
    if quote_num:
        parts.append(_text(
            frame.right - 12, frame.y + 15, quote_num,
            11, anchor="end", weight="bold",
        ))
        parts.append(_text(
            frame.right - 12, frame.y + 29, right_title,
            9, anchor="end", fill=GRAY,
        ))
    else:
        parts.append(_text(
            frame.right - 12, frame.y + 22, right_title,
            11, anchor="end", weight="bold",
        ))


def _draw_ortho_dims(parts, layout, ortho, include_elev: bool = True):
    """Plan and elevation dimensions, parked in each frame's gutters."""
    if not ortho:
        return
    px, py, pw, ph = ortho["plan_box"]
    _gutter_width(parts, px, px + pw, py + ph, layout["plan_dim_bottom"], ortho["plan_width"])
    _gutter_height(parts, py, py + ph, px, layout["plan_dim_left"], ortho["plan_depth"], side="left")
    back_px = ortho.get("plan_back_px") or 0
    if back_px > 2 and ortho.get("plan_back_thk"):
        bt_y = py + ph - back_px
        _gutter_height(
            parts, bt_y, bt_y + back_px, px + pw,
            layout["plan_dim_right"],
            ortho["plan_back_thk"], side="right",
        )
    if not include_elev:
        return

    ex, floor, ew, eh = ortho["elev_box"]
    top = floor - eh
    _gutter_width(parts, ex, ex + ew, floor, layout["elev_dim_bottom"], ortho["elev_width"])
    _gutter_height(parts, top, floor, ex, layout["elev_dim_left"], ortho["elev_overall"], side="left")
    sh = ortho.get("sh_px") or 0
    bh = ortho.get("bh_px") or 0
    if sh > 1:
        sh_y = floor - sh / 2 + 4
        if bh > 1:
            bh_y = floor - sh - bh / 2 + 4
            sh_y, bh_y = _separate_baseline(sh_y, bh_y, gap=18)
            _gutter_height(
                parts, floor - sh, top, ex + ew, layout["elev_dim_right"],
                ortho["elev_bh"], side="right", label_y=bh_y,
            )
        _gutter_height(
            parts, floor, floor - sh, ex + ew, layout["elev_dim_right"],
            ortho["elev_sh"], side="right", label_y=sh_y,
        )


def _compose_multiview(name, bench_type, build_fn, plan_fn, elev_fn,
                       dims_text, cushion_count, cushion_width=24,
                       panel_style="vertical_channels", channel_count=6,
                       quote_num="", client="", project="", date="",
                       plan_args=(), elev_args=(), iso_args=(),
                       plan_kwargs=None, elev_kwargs=None, iso_kwargs=None,
                       side_kwargs=None, category_chip="", chrome=None,
                       assumptions=None, has_back=True, title_panel_style=None,
                       layout=None, ortho=None, plan_aside="",
                       include_side_elevation=False, side_args=(),
                       sheet_kind="idea", split_elevation=False,
                       back_cushion_count=None, back_cushion_width=None):
    """Compose the shared idea-sheet: plan + elevation, iso, title block."""
    layout = layout or idea_sheet_regions()
    parts = [_defs()]
    parts.append(f'<rect width="{LAYOUT_W}" height="{LAYOUT_H}" fill="white"/>')
    parts.append(_rect(12, 12, LAYOUT_W - 24, LAYOUT_H - 24, 1.15))

    _sheet_header(parts, layout["header"], category_chip, quote_num, sheet_kind=sheet_kind)

    _view_frame(parts, layout["plan"], "PLAN VIEW", aside=plan_aside)
    plan_group = []
    _pk = dict(plan_kwargs or {})
    plan_safe = layout["plan_safe"]
    plan_fn(plan_group, *plan_args, cushion_width=cushion_width,
            panel_style=panel_style, channel_count=channel_count, **_pk)
    parts.append(
        f'<g transform="translate({plan_safe.x:.1f},{plan_safe.y:.1f})" data-panel="plan">'
    )
    parts.extend(plan_group)
    parts.append('</g>')

    _view_frame(parts, layout["iso"], "ISOMETRIC VIEW")
    iso_draw = layout["iso_draw"]
    iso_group = []
    _ik = dict(iso_kwargs or {})
    bp, *_ = build_fn(
        *iso_args, svg_w=iso_draw.w, svg_h=iso_draw.h,
        panel_style=panel_style, channel_count=channel_count, **_ik,
    )
    iso_group.extend(bp)
    parts.append(
        f'<g transform="translate({iso_draw.x:.1f},{iso_draw.y:.1f})" data-panel="iso">'
    )
    parts.extend(iso_group)
    parts.append('</g>')

    elev_safe = layout["elev_safe"]
    if include_side_elevation and split_elevation:
        width_in, depth_in, seat_h_in, back_h_in = (
            elev_args[3], elev_args[4], elev_args[5], elev_args[6],
        )
        geo_back = float(back_h_in or 0) if back_h_in else 0.0
        elev_h = seat_h_in + geo_back
        elev_frame = Rect(
            elev_safe.x, elev_safe.y - CAPTION_H, elev_safe.w, elev_safe.h + CAPTION_H,
        )
        _view_frame(parts, elev_frame, "FRONT + SIDE ELEVATION")
        gap = max(18.0, elev_safe.w * 0.04)
        front_w = elev_safe.w * FRONT_ELEV_PANEL_FRAC
        side_w = elev_safe.w - gap - front_w
        left_safe = Rect(elev_safe.x + 4, elev_safe.y, front_w - 4, elev_safe.h)
        right_safe = Rect(elev_safe.x + front_w + gap, elev_safe.y, side_w - 4, elev_safe.h)
        dim_stack_h = 44.0
        dim_lr = 84.0
        dim_rhs_labels = 84.0
        dim_gutter = 40.0
        target_fill_front = 0.72
        target_fill_side = 0.90
        scale_w_front = (left_safe.w - dim_lr - 8) / float(width_in)
        scale_w_side = (right_safe.w - dim_gutter - 8) / float(depth_in)
        scale_h_front = (left_safe.h * target_fill_front - dim_stack_h) / (elev_h or 1)
        scale_h_side = (right_safe.h * target_fill_side - dim_stack_h) / (elev_h or 1)
        elev_scale_front = min(scale_w_front, scale_h_front)
        elev_scale_side = min(scale_w_side, scale_h_side)
        elev_scale = elev_scale_front
        content_px_front = elev_h * elev_scale_front
        content_px_side = elev_h * elev_scale_side
        block_h_front = content_px_front + dim_stack_h
        block_h_side = content_px_side + dim_stack_h
        block_top = max(6.0, (left_safe.h - block_h_front) / 2)
        front_floor = block_top + content_px_front
        geo_w = width_in * elev_scale_front
        fox = max(6.0, (left_safe.w - geo_w - dim_rhs_labels) / 2)
        front_group = []
        _ek = dict(elev_kwargs or {})
        elev_fn(
            front_group, fox, front_floor, elev_scale_front,
            width_in, depth_in, seat_h_in, back_h_in,
            panel_style=panel_style, channel_count=channel_count,
            panel_w=left_safe.w, panel_h=left_safe.h,
            cushion_count=cushion_count, draw_dims=True, split_panel=True,
            **_ek,
        )
        parts.append(
            f'<g transform="translate({left_safe.x:.1f},{left_safe.y:.1f})" '
            f'data-panel="front-elev">'
        )
        parts.extend(front_group)
        parts.append('</g>')
        block_top_side = max(6.0, (right_safe.h - block_h_side) / 2)
        side_floor = block_top_side + content_px_side
        geo_sw = depth_in * elev_scale_side
        sox = max(6.0, (right_safe.w - geo_sw - dim_gutter) / 2)
        side_group = []
        _sk = dict(side_kwargs or {})
        _side_straight(
            side_group, sox, side_floor, elev_scale_side,
            depth_in, seat_h_in, back_h_in,
            panel_style=panel_style, channel_count=channel_count,
            panel_w=right_safe.w, panel_h=right_safe.h, draw_dims=True,
            split_panel=True,
            **_sk,
        )
        parts.append(
            f'<g transform="translate({right_safe.x:.1f},{right_safe.y:.1f})" '
            f'data-panel="side-elev">'
        )
        parts.extend(side_group)
        parts.append('</g>')
        label_y = elev_safe.y + CAPTION_H + 14
        parts.append(_text(left_safe.x + left_safe.w * 0.45, label_y, "FRONT", 10, weight="600"))
        parts.append(_text(right_safe.x + right_safe.w * 0.42, label_y, "SIDE", 10, weight="600"))
    else:
        _view_frame(parts, layout["elev"], "FRONT ELEVATION")
        elev_group = []
        elev_fn(elev_group, *elev_args, panel_style=panel_style, channel_count=channel_count)
        parts.append(f'<g transform="translate({elev_safe.x:.1f},{elev_safe.y:.1f})">')
        parts.extend(elev_group)
        parts.append('</g>')

    if ortho:
        split = bool(include_side_elevation and split_elevation)
        _draw_ortho_dims(parts, layout, ortho, include_elev=not split)

    title = layout["title"]
    _title_block(parts, title.x, title.y, title.w, title.h,
                 name=name, quote_num=quote_num, dims_text=dims_text,
                 bench_type=bench_type, cushion_count=cushion_count,
                 cushion_width=cushion_width,
                 panel_style=title_panel_style or panel_style,
                 client=client, project=project, date=date,
                 category_chip=category_chip, chrome=chrome,
                 assumptions=assumptions, has_back=has_back,
                 back_cushion_count=back_cushion_count,
                 back_cushion_width=back_cushion_width)

    return _wrap_svg_raw(parts, LAYOUT_W, LAYOUT_H)


def _regions_for(name, bench_type, panel_style, has_back, cushion_count,
                 cushion_width, dims_text, quote_num, client, project, date,
                 extras):
    rows = _title_rows(
        name=name, quote_num=quote_num, dims_text=dims_text,
        bench_type=bench_type, cushion_count=cushion_count,
        cushion_width=cushion_width, panel_style=panel_style,
        client=client, project=project, date=date,
        assumptions=extras.get("assumptions"), has_back=has_back,
        drawn_by=(extras.get("chrome") or {}).get("drawn_by") or "MAX AI",
    )
    extra = sum(1 for _, value in rows if len(str(value)) > 32)
    return idea_sheet_regions(title_rows=len(rows) + extra)


# ── PUBLIC RENDER FUNCTIONS ──────────────────────────────────────
# Signatures preserved for compatibility with tool_executor.py and drawings.py

def _inches_if_feet(value, length_unit):
    """Inches-first. Multiply only when the caller says the number is feet."""
    if value is None:
        return 0.0
    number = float(value)
    if number <= 0:
        return 0.0
    if _normalize_length_unit(length_unit) == "ft":
        return number * 12.0
    return number


def _sheet_extras(name, bench_type, panel_style, has_back, back_h_in, kw):
    business = kw.get("business_unit") or ""
    product = kw.get("product_type") or ""
    chip = kw.get("category_chip") or _bridge_category_chip(
        business_unit=business,
        bench_type=bench_type,
        product_type=product,
        name=name or "",
        panel_style=panel_style if has_back else "none",
        has_back=has_back,
    )
    assumptions = list(kw.get("assumptions") or [])
    mark = "ASSUMED — CONFIRM BEFORE FABRICATION"
    if kw.get("back_height_assumed") and has_back and not any(mark in a for a in assumptions):
        assumptions.append(f'back height {_in(float(back_h_in))} {mark}')
    return dict(
        category_chip=chip,
        chrome=kw.get("chrome") or _bridge_chrome(business),
        assumptions=assumptions,
        has_back=has_back,
        title_panel_style=panel_style if has_back else "none",
    )


def render_straight(name, width_in, depth_in=20, seat_h_in=18, back_h_in=18,
                    quote_num="", svg_w=600, svg_h=400,
                    cushion_width=24, panel_style="vertical_channels", channel_count=6,
                    client="", project="", **kw):
    from app.services.drawing.bench_fabrication_params import resolve_bench_fabrication
    """Render a straight bench — 4-quadrant professional drawing.

    width_in is inches unless length_unit='ft'. Values ≤40 are not
    guessed as feet.
    """
    width_in = _inches_if_feet(width_in, kw.get("length_unit") or "in")
    has_back = bool(kw["has_back"]) if kw.get("has_back") is not None and "has_back" in kw else panel_style != "none"
    geo_back = float(back_h_in or 0) if has_back else 0.0
    draw_panel = panel_style if has_back else "none"

    c_default, _cw_default = _resolve_cushions(
        width_in, cushion_width, kw.get("cushion_count"),
    )
    notes = str(kw.get("description") or kw.get("notes") or "")
    fab = resolve_bench_fabrication(
        width_in=width_in,
        overall_depth_in=depth_in,
        seat_height_in=seat_h_in,
        dims=kw,
        params=kw,
        notes=notes,
        seat_sections_default=c_default,
    )
    c_count = fab.seat_sections
    actual_cw = fab.seat_section_width_in
    back_sec = fab.back_sections
    back_sw = fab.back_section_width_in
    bt_in = fab.back_thickness_in
    cush_thk = fab.seat_cushion_thickness_in
    back_angle = fab.back_angle_deg
    overhang_in = fab.seat_cushion_overhang_in
    seat_depth_usable = fab.seat_frame_depth_in(depth_in)
    deck_h = fab.seat_deck_height_in()

    if has_back:
        dims_text = (
            f'{_in(width_in)} W × {_in(depth_in)} D × '
            f'{_in(seat_h_in)} SH × {_in(geo_back)} BH'
        )
    else:
        dims_text = f'{_in(width_in)} W × {_in(depth_in)} D × {_in(seat_h_in)} SH × NO BACK'

    extras = _sheet_extras(name, "straight", panel_style, has_back, geo_back, kw)
    oh_part = f'; {_in(overhang_in)} OH front' if overhang_in > 0 else ''
    depth_note = (
        f'D {_in(depth_in)} frame: {_in(seat_depth_usable)} seat + {_in(bt_in)} back inside{oh_part}'
    )
    extras["assumptions"] = list(extras.get("assumptions") or []) + [depth_note]
    layout = _regions_for(
        name, "straight", panel_style, has_back, c_count, actual_cw,
        dims_text, quote_num, client, project, kw.get("date", ""), extras,
    )
    plan_scale, plan_ox, plan_oy = _auto_scale_2d(
        width_in, depth_in, layout["plan_safe"].w, layout["plan_safe"].h, margin=4, fill=0.96,
    )
    plan_args = (plan_ox, plan_oy, plan_scale, width_in, depth_in, seat_h_in, geo_back)
    elev_h = seat_h_in + geo_back
    elev_scale, elev_ox, elev_oy = _auto_scale_2d(
        width_in, elev_h or 1, layout["elev_safe"].w, layout["elev_safe"].h, margin=4, fill=0.96,
    )
    elev_ground_y = elev_oy + elev_h * elev_scale
    elev_args = (elev_ox, elev_ground_y, elev_scale, width_in, depth_in, seat_h_in, geo_back)
    safe_p = layout["plan_safe"]
    safe_e = layout["elev_safe"]
    back_px = bt_in * plan_scale if has_back else 0
    ortho = {
        "plan_box": (safe_p.x + plan_ox, safe_p.y + plan_oy, width_in * plan_scale, depth_in * plan_scale),
        "plan_width": f'{_in(width_in)}',
        "plan_depth": f'{_in(depth_in)}',
        "plan_back_thk": f'{_in(bt_in)} back' if has_back else None,
        "plan_back_px": back_px,
        "plan_seat_depth": f'{_in(seat_depth_usable)} seat' if has_back else None,
        "plan_seat_depth_px": seat_depth_usable * plan_scale if has_back else 0,
        "elev_box": (safe_e.x + elev_ox, safe_e.y + elev_ground_y, width_in * elev_scale, elev_h * elev_scale),
        "elev_width": f'{_in(width_in)}',
        "elev_overall": f'{_in(elev_h)}',
        "elev_sh": f'{_in(seat_h_in)} SH',
        "elev_bh": f'{_in(geo_back)} BH',
        "sh_px": seat_h_in * elev_scale,
        "bh_px": geo_back * elev_scale,
    }
    iso_args = (name, width_in, depth_in, seat_h_in, geo_back, quote_num)

    include_side = bool(
        kw.get("include_side_elevation")
        or kw.get("sheet_kind") == "shop"
    )
    sheet_kind = "shop" if kw.get("sheet_kind") == "shop" else "idea"
    fab_kw = {
        "back_thickness_in": bt_in,
        "seat_cushion_thickness_in": cush_thk,
        "back_angle_deg": back_angle,
        "seat_cushion_overhang_in": overhang_in,
        "frame_depth_in": depth_in,
    }
    return _compose_multiview(
        name, "straight", _build_straight, _plan_straight, _elev_straight,
        dims_text, c_count, actual_cw, draw_panel, channel_count,
        quote_num, client, project, date=kw.get("date", ""),
        plan_args=plan_args, elev_args=elev_args, iso_args=iso_args,
        plan_kwargs={
            "cushion_count": c_count,
            "back_thickness_in": bt_in,
            "back_sections": back_sec,
            "seat_cushion_overhang_in": overhang_in,
            "seat_cushion_thickness_in": cush_thk,
        },
        elev_kwargs={
            "back_sections": back_sec,
            "seat_cushion_thickness_in": cush_thk,
        },
        iso_kwargs={
            "back_thickness_in": bt_in,
            "seat_sections": c_count,
            "back_sections": back_sec,
            "seat_cushion_thickness_in": cush_thk,
        },
        side_kwargs=fab_kw,
        layout=layout, ortho=ortho,
        plan_aside=_back_style_label(panel_style, has_back=has_back),
        include_side_elevation=include_side,
        split_elevation=include_side,
        sheet_kind=sheet_kind,
        back_cushion_count=back_sec,
        back_cushion_width=back_sw,
        **extras,
    )


def render_l_shape(name, long_in, short_in=0, depth_in=20, seat_h_in=18, back_h_in=18,
                   quote_num="", svg_w=600, svg_h=400,
                   cushion_width=24, panel_style="vertical_channels", channel_count=6,
                   client="", project="", **kw):
    """Render an L-shaped bench — 4-quadrant professional drawing.

    Lengths are inches unless length_unit='ft'. A single foot-length
    with no short leg still splits 60/40 — that is the legacy quote
    batch entry, and only runs for an explicit feet unit.
    """
    if _normalize_length_unit(kw.get("length_unit") or "in") == "ft" and long_in and long_in > 0:
        if not short_in or short_in < 10:
            lf = float(long_in)
            long_in = lf * 0.6 * 12
            short_in = lf * 0.4 * 12
        else:
            long_in = _inches_if_feet(long_in, "ft")
            short_in = _inches_if_feet(short_in, "ft")
    if short_in == 0:
        short_in = long_in * 0.5
    has_back = bool(kw["has_back"]) if "has_back" in kw and kw.get("has_back") is not None else panel_style != "none"
    geo_back = float(back_h_in or 0) if has_back else 0.0
    draw_panel = panel_style if has_back else "none"

    c_count = max(1, math.ceil(long_in / cushion_width)) if cushion_width > 0 else 1

    if has_back:
        dims_text = f'{_in(long_in)} L × {_in(short_in)} S × {_in(depth_in)} D × {_in(seat_h_in)} SH × {_in(geo_back)} BH'
    else:
        dims_text = f'{_in(long_in)} L × {_in(short_in)} S × {_in(depth_in)} D × {_in(seat_h_in)} SH × NO BACK'

    extras = _sheet_extras(name, "l_shape", panel_style, has_back, geo_back, kw)
    layout = _regions_for(
        name, "l_shape", panel_style, has_back, c_count, cushion_width,
        dims_text, quote_num, client, project, kw.get("date", ""), extras,
    )
    plan_scale, plan_ox, plan_oy = _auto_scale_2d(
        long_in, short_in, layout["plan_safe"].w, layout["plan_safe"].h, margin=4, fill=0.96,
    )
    plan_args = (plan_ox, plan_oy, plan_scale, long_in, short_in, depth_in, seat_h_in, geo_back)
    elev_h = seat_h_in + geo_back
    elev_scale, elev_ox, elev_oy = _auto_scale_2d(
        long_in, elev_h or 1, layout["elev_safe"].w, layout["elev_safe"].h, margin=4, fill=0.96,
    )
    elev_ground_y = elev_oy + elev_h * elev_scale
    elev_args = (elev_ox, elev_ground_y, elev_scale, long_in, short_in, depth_in, seat_h_in, geo_back)
    safe_p = layout["plan_safe"]
    safe_e = layout["elev_safe"]
    ortho = {
        "plan_box": (safe_p.x + plan_ox, safe_p.y + plan_oy, long_in * plan_scale, short_in * plan_scale),
        "plan_width": f'{_in(long_in)}',
        "plan_depth": f'{_in(short_in)}',
        "elev_box": (safe_e.x + elev_ox, safe_e.y + elev_ground_y, long_in * elev_scale, elev_h * elev_scale),
        "elev_width": f'{_in(long_in)}',
        "elev_overall": f'{_in(elev_h)}',
        "elev_sh": f'{_in(seat_h_in)} SH',
        "elev_bh": f'{_in(geo_back)} BH',
        "sh_px": seat_h_in * elev_scale,
        "bh_px": geo_back * elev_scale,
    }
    iso_args = (name, long_in, short_in, depth_in, seat_h_in, geo_back, quote_num)

    return _compose_multiview(
        name, "l_shape", _build_l_shape, _plan_l_shape, _elev_l_shape,
        dims_text, c_count, cushion_width, draw_panel, channel_count,
        quote_num, client, project, date=kw.get("date", ""),
        plan_args=plan_args, elev_args=elev_args, iso_args=iso_args,
        layout=layout, ortho=ortho,
        plan_aside=_back_style_label(panel_style, has_back=has_back),
        **extras,
    )


def render_u_shape(name, back_in, side_in=0, depth_in=20, side_depth_in=0,
                   seat_h_in=18, back_h_in=18, multiplier=1,
                   quote_num="", svg_w=600, svg_h=400,
                   cushion_width=24, panel_style="vertical_channels", channel_count=6,
                   client="", project="",
                   side_left_in=None, side_right_in=None, **kw):
    """Render a U-shaped booth — 4-quadrant professional drawing.

    Length args are INCHES unless length_unit='ft'. A single foot-length
    with no wing still uses the legacy 45/27.5 split. Pass side_left_in /
    side_right_in for asymmetric arms (Marleys: 41.25 / 52); otherwise
    both use side_in.
    """
    if _normalize_length_unit(kw.get("length_unit") or "in") == "ft" and back_in and back_in > 0:
        if not side_in:
            lf = float(back_in)
            per = lf / multiplier if multiplier > 1 else lf
            back_in = per * 0.45 * 12
            side_in = per * 0.275 * 12
            if side_depth_in == 0:
                side_depth_in = depth_in
        else:
            back_in = _inches_if_feet(back_in, "ft")
            side_in = _inches_if_feet(side_in, "ft")
            if side_depth_in:
                side_depth_in = _inches_if_feet(side_depth_in, "ft")
    if side_in == 0:
        side_in = back_in * 0.6
    if side_depth_in == 0:
        side_depth_in = depth_in

    sl = float(side_left_in) if side_left_in not in (None, 0, "") else float(side_in)
    sr = float(side_right_in) if side_right_in not in (None, 0, "") else float(side_in)
    side_max = max(sl, sr)

    total_w = back_in + side_depth_in * 2
    c_left = max(1, math.ceil(sl / cushion_width)) if cushion_width > 0 else 1
    c_back = max(1, math.ceil(back_in / cushion_width)) if cushion_width > 0 else 1
    c_right = max(1, math.ceil(sr / cushion_width)) if cushion_width > 0 else 1
    c_count = c_left + c_back + c_right

    has_back = bool(kw["has_back"]) if "has_back" in kw and kw.get("has_back") is not None else panel_style != "none"
    geo_back = float(back_h_in or 0) if has_back else 0.0
    draw_panel = panel_style if has_back else "none"

    if abs(sl - sr) > 0.05:
        side_txt = f'{_in(sl)}/{_in(sr)} S(L/R)'
    else:
        side_txt = f'{_in(side_max)} S'
    if has_back:
        dims_text = (f'{_in(back_in)} B × {side_txt} × {_in(depth_in)} D × '
                     f'{_in(side_depth_in)} SD × {_in(seat_h_in)} SH × {_in(geo_back)} BH')
    else:
        dims_text = (f'{_in(back_in)} B × {side_txt} × {_in(depth_in)} D × '
                     f'{_in(side_depth_in)} SD × {_in(seat_h_in)} SH × NO BACK')

    extras = _sheet_extras(name, "u_shape", panel_style, has_back, geo_back, kw)
    layout = _regions_for(
        name, "u_shape", panel_style, has_back, c_count, cushion_width,
        dims_text, quote_num, client, project, kw.get("date", ""), extras,
    )
    plan_scale, plan_ox, plan_oy = _auto_scale_2d(
        total_w, side_max, layout["plan_safe"].w, layout["plan_safe"].h, margin=4, fill=0.96,
    )
    plan_args = (plan_ox, plan_oy, plan_scale, back_in, side_max,
                 depth_in, side_depth_in, seat_h_in, geo_back)
    plan_kwargs = dict(side_left=sl, side_right=sr)
    elev_h = seat_h_in + geo_back
    elev_scale, elev_ox, elev_oy = _auto_scale_2d(
        total_w, elev_h or 1, layout["elev_safe"].w, layout["elev_safe"].h, margin=4, fill=0.96,
    )
    elev_ground_y = elev_oy + elev_h * elev_scale
    elev_args = (elev_ox, elev_ground_y, elev_scale, back_in, side_max,
                 depth_in, side_depth_in, seat_h_in, geo_back)
    safe_p = layout["plan_safe"]
    safe_e = layout["elev_safe"]
    ortho = {
        "plan_box": (safe_p.x + plan_ox, safe_p.y + plan_oy, total_w * plan_scale, side_max * plan_scale),
        "plan_width": f'{_in(total_w)}',
        "plan_depth": f'{_in(side_max)}',
        "elev_box": (safe_e.x + elev_ox, safe_e.y + elev_ground_y, total_w * elev_scale, elev_h * elev_scale),
        "elev_width": f'{_in(total_w)}',
        "elev_overall": f'{_in(elev_h)}',
        "elev_sh": f'{_in(seat_h_in)} SH',
        "elev_bh": f'{_in(geo_back)} BH',
        "sh_px": seat_h_in * elev_scale,
        "bh_px": geo_back * elev_scale,
    }
    # Iso still uses max side (symmetric box approx) — flagged in dims_text when asymmetric
    iso_args = (name, back_in, side_max, depth_in, side_depth_in, seat_h_in, geo_back, quote_num)

    return _compose_multiview(
        name, "u_shape", _build_u_shape, _plan_u_shape, _elev_u_shape,
        dims_text, c_count, cushion_width, draw_panel, channel_count,
        quote_num, client, project, date=kw.get("date", ""),
        plan_args=plan_args, elev_args=elev_args, iso_args=iso_args,
        plan_kwargs=plan_kwargs,
        layout=layout, ortho=ortho,
        plan_aside=_back_style_label(panel_style, has_back=has_back),
        **extras,
    )


# ── PROJECT SHEET ────────────────────────────────────────────────

def render_project_sheet(benches, title="BUILT-IN BENCHES", quote_num="",
                         svg_w=1100, svg_h=850):
    """Render a 2×2 grid of benches with title block at bottom right."""
    parts = [_defs()]
    parts.append(f'<rect width="{svg_w}" height="{svg_h}" fill="white"/>')

    parts.append(_rect(8, 8, svg_w - 16, svg_h - 16, SW_BORDER))
    parts.append(_rect(14, 14, svg_w - 28, svg_h - 28, 0.5))

    # Title block
    tb_w = 300
    tb_h = 65
    tb_x = svg_w - 14 - tb_w
    tb_y = svg_h - 14 - tb_h
    parts.append(_rect(tb_x, tb_y, tb_w, tb_h, SW_MED))
    parts.append(_text(tb_x + tb_w / 2, tb_y + 22, "EMPIRE WORKROOM", 16, weight="bold"))
    parts.append(_text(tb_x + tb_w / 2, tb_y + 38, title, 12, weight="bold"))
    if quote_num:
        parts.append(_text(tb_x + tb_w / 2, tb_y + 54, quote_num, 10))

    # Grid
    cols = 2
    rows = 2 if len(benches) > 2 else 1
    content_y_end = tb_y - 8 if rows == 2 else svg_h - 14

    area_x = 20
    area_y = 20
    area_w = svg_w - 40
    area_h = content_y_end - area_y

    cell_w = area_w / cols
    cell_h = area_h / rows

    if cols > 1:
        mid_x = area_x + cell_w
        parts.append(_line(mid_x, area_y, mid_x, area_y + area_h, 0.5))
    if rows > 1:
        mid_y = area_y + cell_h
        parts.append(_line(area_x, mid_y, area_x + area_w, mid_y, 0.5))

    for idx, bench in enumerate(benches[:4]):
        col = idx % cols
        row = idx // cols

        cx = area_x + col * cell_w + 8
        cy = area_y + row * cell_h + 4

        draw_w = cell_w - 16
        draw_h = cell_h - 28

        b_type = bench.get("type", "straight")
        b_name = bench.get("name", "Bench")
        qty = bench.get("qty", 1)
        ps = bench.get("panel_style", "vertical_channels")
        cc = bench.get("channel_count", 6)

        if b_type == "l_shape":
            bp, *_ = _build_l_shape(
                b_name,
                bench.get("long_in", bench.get("width_in", 120)),
                bench.get("short_in", 60),
                bench.get("depth_in", 20),
                bench.get("seat_h_in", 18),
                bench.get("back_h_in", 18),
                svg_w=draw_w, svg_h=draw_h,
                panel_style=ps, channel_count=cc,
            )
        elif b_type == "u_shape":
            bp, *_ = _build_u_shape(
                b_name,
                bench.get("back_in", bench.get("width_in", 84)),
                bench.get("side_in", 60),
                bench.get("depth_in", 20),
                bench.get("side_depth_in", bench.get("depth_in", 20)),
                bench.get("seat_h_in", 18),
                bench.get("back_h_in", 18),
                svg_w=draw_w, svg_h=draw_h,
                panel_style=ps, channel_count=cc,
            )
        else:
            bp, *_ = _build_straight(
                b_name,
                bench.get("width_in", 120),
                bench.get("depth_in", 20),
                bench.get("seat_h_in", 18),
                bench.get("back_h_in", 18),
                svg_w=draw_w, svg_h=draw_h,
                panel_style=ps, channel_count=cc,
            )

        qty_str = f" ({qty}X)" if qty > 1 else ""
        parts.append(f'<g transform="translate({cx:.0f},{cy:.0f})">')
        parts.append(_text(draw_w / 2, 12, f"{b_name.upper()}{qty_str}", 11, weight="bold"))
        parts.extend(bp)
        parts.append('</g>')

    return _wrap_svg_raw(parts, svg_w, svg_h)


# ── SVG WRAPPERS ─────────────────────────────────────────────────

def _wrap_svg_raw(parts, svg_w, svg_h):
    body = "\n  ".join(parts)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}" '
        f'width="{svg_w}" height="{svg_h}">\n  {body}\n</svg>'
    )


# ── BATCH RENDERING ──────────────────────────────────────────────

def render_quote_drawings(line_items, quote_num=""):
    """Generate drawings for all areas in a quote."""
    results = []
    for item in line_items:
        desc = item.get("description", "")
        lf = item.get("quantity", 0)
        if lf <= 0:
            continue
        name = desc.split("\u2014")[0].strip() if "\u2014" in desc else desc
        desc_lower = desc.lower()
        if "u-shape" in desc_lower or "u shape" in desc_lower:
            mult = 2 if "\u00d72" in desc or "x2" in desc_lower else 1
            svg = render_u_shape(name, lf, multiplier=mult, quote_num=quote_num, length_unit="ft")
        elif "l-shape" in desc_lower or "l shape" in desc_lower:
            svg = render_l_shape(name, lf, quote_num=quote_num, length_unit="ft")
        else:
            svg = render_straight(name, lf, quote_num=quote_num, length_unit="ft")
        results.append({"name": name, "svg": svg, "lf": lf})
    return results


def drawings_to_pdf(drawings, output_path):
    """Convert list of drawing dicts to a multi-page PDF.

    The sheet is scaled to the letter-landscape content box. Intrinsic
    SVG pixel sizes are stripped so headers are not clipped.
    """
    from weasyprint import HTML as WeasyHTML
    from app.services.drawing.empire_sheet_chrome import drawings_pdf_html

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    WeasyHTML(string=drawings_pdf_html(drawings)).write_pdf(output_path)
    return output_path
