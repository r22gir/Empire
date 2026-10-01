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
BACK_T = 4          # back panel thickness (visual constant, inches)

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


def _poly(pts, sw=SW_MED, fill="none", stroke=BLACK):
    points = " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in pts)
    return f'<polygon points="{points}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"/>'


def _line(x1, y1, x2, y2, sw=SW_MED, stroke=BLACK, dash=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{sw}"{d}/>'


def _rect(x, y, w, h, sw=SW_MED, fill="none", stroke=BLACK):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


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
    gap = 3
    ext = 5
    dy = offset_y
    sign = 1 if dy > 0 else -1

    # Extension lines
    parts.append(_line(p1[0], p1[1] + gap * sign, p1[0], p1[1] + dy + ext * sign, SW_EXT, DIM_COLOR))
    parts.append(_line(p2[0], p2[1] + gap * sign, p2[0], p2[1] + dy + ext * sign, SW_EXT, DIM_COLOR))

    # Dimension line with arrows
    d1y = p1[1] + dy
    d2y = p2[1] + dy
    parts.append(
        f'<line x1="{p1[0]:.1f}" y1="{d1y:.1f}" x2="{p2[0]:.1f}" y2="{d2y:.1f}" '
        f'stroke="{DIM_COLOR}" stroke-width="{SW_DIM}" '
        f'marker-start="url(#dim-arrow)" marker-end="url(#dim-arrow)"/>'
    )

    # Text — always horizontal, centered above/below dimension line
    mx = (p1[0] + p2[0]) / 2
    my = (d1y + d2y) / 2
    text_y = my - 4 if text_side == "above" else my + 12
    parts.append(_text(mx, text_y, label, 9, weight="600", fill=DIM_COLOR))


def _dim_v(parts, p1, p2, label, offset_x, text_side="right"):
    """Vertical dimension line. TEXT IS HORIZONTAL — placed beside the line."""
    gap = 3
    ext = 5
    sign = 1 if offset_x > 0 else -1

    # Extension lines
    parts.append(_line(p1[0] + gap * sign, p1[1], p1[0] + offset_x + ext * sign, p1[1], SW_EXT, DIM_COLOR))
    parts.append(_line(p2[0] + gap * sign, p2[1], p2[0] + offset_x + ext * sign, p2[1], SW_EXT, DIM_COLOR))

    # Dimension line with arrows
    d1x = p1[0] + offset_x
    d2x = p2[0] + offset_x
    parts.append(
        f'<line x1="{d1x:.1f}" y1="{p1[1]:.1f}" x2="{d2x:.1f}" y2="{p2[1]:.1f}" '
        f'stroke="{DIM_COLOR}" stroke-width="{SW_DIM}" '
        f'marker-start="url(#dim-arrow)" marker-end="url(#dim-arrow)"/>'
    )

    # Text — HORIZONTAL, placed beside the vertical dimension line
    mx = (d1x + d2x) / 2
    my = (p1[1] + p2[1]) / 2
    tx = mx + (10 if text_side == "right" else -10)
    anch = "start" if text_side == "right" else "end"
    parts.append(_text(tx, my + 4, label, 9, anchor=anch, weight="600", fill=DIM_COLOR))


def _dim_2d_h(parts, x1, x2, y, label, offset_y=20):
    _dim_h(parts, (x1, y), (x2, y), label, offset_y, "below" if offset_y > 0 else "above")


def _dim_2d_v(parts, x, y1, y2, label, offset_x=20):
    _dim_v(parts, (x, y1), (x, y2), label, offset_x, "right" if offset_x > 0 else "left")


def _dim_iso_width(parts, ox, oy, scale, x1, x2, y, z, label, below=True):
    p1 = _iso(x1, y, z, ox, oy, scale)
    p2 = _iso(x2, y, z, ox, oy, scale)
    off = 22 if below else -22
    _dim_h(parts, p1, p2, label, off, "below" if below else "above")


def _dim_iso_depth(parts, ox, oy, scale, x, y1, y2, z, label, below=True):
    p1 = _iso(x, y1, z, ox, oy, scale)
    p2 = _iso(x, y2, z, ox, oy, scale)
    off = 22 if below else -22
    _dim_h(parts, p1, p2, label, off, "below" if below else "above")


def _dim_iso_height(parts, ox, oy, scale, x, y, z1, z2, label, right=True):
    p1 = _iso(x, y, z1, ox, oy, scale)
    p2 = _iso(x, y, z2, ox, oy, scale)
    off = 18 if right else -18
    _dim_v(parts, p1, p2, label, off, "right" if right else "left")


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
        pad = 2.0
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
                   cushion_width=24, panel_style="vertical_channels", channel_count=6):
    """Plan view — top-down rectangle with cushion dividers and numbering."""
    has_back = back_h is not None and back_h > 0 and panel_style != "none"
    bt = BACK_T if has_back else 0
    w = width * scale
    d = depth * scale
    bt_s = bt * scale

    # Seat area
    parts.append(_rect(ox, oy, w, d - bt_s, SW_HEAVY))
    if has_back:
        # Back panel
        parts.append(_rect(ox, oy + d - bt_s, w, bt_s, SW_HEAVY, fill="#F0F0F0"))
        _draw_back_style_2d(parts, ox, oy + d - bt_s, w, bt_s, panel_style, channel_count)

    # Cushion dividers + numbering
    c_count = max(1, math.ceil(width / cushion_width)) if cushion_width > 0 else 1
    seat_span = d - bt_s
    if c_count > 1:
        for i in range(1, c_count):
            cx = ox + w * i / c_count
            parts.append(_line(cx, oy + 2, cx, oy + seat_span - 2, SW_LIGHT, GRAY))
    # Cushion labels — shrink when the seat is too shallow to hold 11px type
    label_size = 11 if seat_span >= 28 else 8
    for i in range(c_count):
        label_x = ox + w * (i + 0.5) / c_count
        label_y = oy + seat_span / 2
        _cushion_label(parts, label_x, label_y, i + 1, size=label_size)


def _plan_l_shape(parts, ox, oy, scale, long, short, depth, seat_h, back_h,
                  cushion_width=24, panel_style="vertical_channels", channel_count=6):
    """Plan view — L-shaped bench."""
    has_back = back_h is not None and back_h > 0 and panel_style != "none"
    bt = BACK_T if has_back else 0
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
                  side_left=None, side_right=None):
    """Plan view — U-shaped booth.

    side_left / side_right: optional asymmetric wing projections (inches).
    When omitted, both wings use `side` (legacy symmetric behavior).
    Cushion labels are counted per run: ceil(run/cushion_width) each.
    """
    has_back = back_h is not None and back_h > 0 and panel_style != "none"
    bt = BACK_T if has_back else 0
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
                   panel_w: float = 0, panel_h: float = 0):
    """Side elevation: depth × (seat height + back height), local panel coords."""
    has_back = back_h is not None and back_h > 0 and panel_style != "none"
    d = depth * scale
    sh = seat_h * scale
    bh = (back_h if has_back else 0) * scale
    lean = min(d * 0.12, 10.0)
    top_y = oy - sh - bh
    parts.append(_line(ox - 6, oy, ox + d + lean + 6, oy, SW_FLOOR, GRAY, "6,3"))
    parts.append(_rect(ox, oy - sh, d, sh, SW_HEAVY))
    if has_back:
        parts.append(_rect(ox + lean * 0.35, oy - sh - bh, d, bh, SW_MED))
        _draw_back_style_2d(
            parts, ox + lean * 0.35, oy - sh - bh, d, bh,
            panel_style, channel_count,
        )
    dim_band_h = 28.0
    _gutter_width(
        parts, ox, ox + d, oy,
        Rect(ox, min(oy + 4, panel_h - dim_band_h), max(d, 20), dim_band_h),
        _in(depth),
    )
    total_h = seat_h + (back_h if has_back else 0)
    dim_w = 30.0
    _gutter_height(
        parts, top_y, oy, ox + d + lean + 4,
        Rect(
            min(ox + d + lean + 8, panel_w - dim_w - 2),
            max(top_y - 4, CAPTION_H),
            dim_w,
            max(oy - top_y + 8, 20),
        ),
        _in(total_h), side="right",
    )


def _elev_straight(parts, ox, oy, scale, width, depth, seat_h, back_h,
                   panel_style="vertical_channels", channel_count=6):
    """Front elevation with floor line, seat, back, and dimensions."""
    has_back = back_h is not None and back_h > 0 and panel_style != "none"
    w = width * scale
    sh = seat_h * scale
    bh = (back_h if has_back else 0) * scale

    # Floor line (dashed). "FL" sits on the seat, clear of the left gutter dim.
    parts.append(_line(ox - 8, oy, ox + w + 8, oy, SW_FLOOR, GRAY, "6,3"))
    parts.append(_text(ox + 6, oy - 8, "FL", 9, anchor="start", fill=GRAY))

    # Seat box
    parts.append(_rect(ox, oy - sh, w, sh, SW_HEAVY))
    if has_back:
        parts.append(_rect(ox, oy - sh - bh, w, bh, SW_MED))
        _draw_back_style_2d(parts, ox, oy - sh - bh, w, bh, panel_style, channel_count)
        parts.append(_line(ox, oy - sh, ox + w, oy - sh, SW_MED))
    else:
        parts.append(_text(ox + w / 2, oy - sh - 14, "NO BACK", 10, fill=GRAY, weight="600"))


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
                    panel_style="vertical_channels", channel_count=6):
    """Draw one bench section in isometric: seat box + back panel + style pattern."""
    w, d, sh, bh = width, depth, seat_h, back_h
    has_back = bh is not None and bh > 0 and panel_style != "none"
    bt = BACK_T if has_back else 0

    # Seat box — front face
    parts.append(_poly([
        _iso(sx, sy, 0, ox, oy, scale),
        _iso(sx + w, sy, 0, ox, oy, scale),
        _iso(sx + w, sy, sh, ox, oy, scale),
        _iso(sx, sy, sh, ox, oy, scale),
    ], SW_HEAVY))
    # Seat — top face
    parts.append(_poly([
        _iso(sx, sy, sh, ox, oy, scale),
        _iso(sx + w, sy, sh, ox, oy, scale),
        _iso(sx + w, sy + d - bt, sh, ox, oy, scale),
        _iso(sx, sy + d - bt, sh, ox, oy, scale),
    ], SW_MED))
    # Seat — right side
    parts.append(_poly([
        _iso(sx + w, sy, 0, ox, oy, scale),
        _iso(sx + w, sy + d - bt, 0, ox, oy, scale),
        _iso(sx + w, sy + d - bt, sh, ox, oy, scale),
        _iso(sx + w, sy, sh, ox, oy, scale),
    ], SW_MED))

    if not has_back:
        return

    # Back panel — front face
    parts.append(_poly([
        _iso(sx, sy + d - bt, sh, ox, oy, scale),
        _iso(sx + w, sy + d - bt, sh, ox, oy, scale),
        _iso(sx + w, sy + d - bt, sh + bh, ox, oy, scale),
        _iso(sx, sy + d - bt, sh + bh, ox, oy, scale),
    ], SW_HEAVY))
    # Back — top face
    parts.append(_poly([
        _iso(sx, sy + d - bt, sh + bh, ox, oy, scale),
        _iso(sx + w, sy + d - bt, sh + bh, ox, oy, scale),
        _iso(sx + w, sy + d, sh + bh, ox, oy, scale),
        _iso(sx, sy + d, sh + bh, ox, oy, scale),
    ], SW_MED))
    # Back — right side
    parts.append(_poly([
        _iso(sx + w, sy + d - bt, sh, ox, oy, scale),
        _iso(sx + w, sy + d, sh, ox, oy, scale),
        _iso(sx + w, sy + d, sh + bh, ox, oy, scale),
        _iso(sx + w, sy + d - bt, sh + bh, ox, oy, scale),
    ], SW_MED))

    # Seat/back separation
    sl1 = _iso(sx, sy + d - bt, sh, ox, oy, scale)
    sl2 = _iso(sx + w, sy + d - bt, sh, ox, oy, scale)
    parts.append(_line(sl1[0], sl1[1], sl2[0], sl2[1], 1.0))

    # Back style pattern on back face (isometric)
    _draw_back_style_iso(parts, ox, oy, scale, sx, sy + d - bt, width, sh, bh, bt,
                         panel_style, channel_count)


# ── TITLE BLOCK ──────────────────────────────────────────────────

def _title_rows(name="", quote_num="", dims_text="", bench_type="STRAIGHT",
                cushion_count=1, cushion_width=24, panel_style="vertical_channels",
                client="", project="", date="", assumptions=None, has_back=True,
                drawn_by="MAX AI"):
    rows = [
        ("ITEM:", (name or "BENCH").upper()),
        ("TYPE:", bench_type.upper().replace("_", " ")),
        ("DIMENSIONS:", dims_text or "SEE VIEWS"),
        ("CUSHIONS:", f"{cushion_count} @ {_fmt_in(cushion_width)} each"),
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
                 category_chip="", chrome=None, assumptions=None, has_back=True):
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
_ISO_LANE_R = 88
_ISO_LANE_B = 36


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


def _build_straight(name, width_in, depth_in, seat_h_in, back_h_in, quote_num="",
                    svg_w=500, svg_h=350, panel_style="vertical_channels", channel_count=6):
    has_back = back_h_in is not None and back_h_in > 0 and panel_style != "none"
    total_h = seat_h_in + (back_h_in if has_back else 0)
    scale, ox, oy = _iso_fit((width_in, depth_in, total_h), svg_w, svg_h)
    parts = []
    _draw_bench_box(parts, ox, oy, scale, 0, 0, width_in, depth_in, seat_h_in, back_h_in,
                    panel_style, channel_count)

    stack = []
    if has_back:
        stack.append((
            f'{_in(back_h_in)} BH',
            _iso(width_in, depth_in, seat_h_in + back_h_in, ox, oy, scale),
        ))
    stack.append((f'{_in(seat_h_in)} SH', _iso(width_in, 0, seat_h_in, ox, oy, scale)))
    stack.append((f'{_in(depth_in)} D', _iso(width_in, depth_in, 0, ox, oy, scale)))
    _iso_callouts(
        parts, svg_w, svg_h, f'{_in(width_in)}',
        (_iso(0, 0, 0, ox, oy, scale), _iso(width_in, 0, 0, ox, oy, scale)),
        stack,
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


def _draw_ortho_dims(parts, layout, ortho):
    """Plan and elevation dimensions, parked in each frame's gutters."""
    if not ortho:
        return
    px, py, pw, ph = ortho["plan_box"]
    _gutter_width(parts, px, px + pw, py + ph, layout["plan_dim_bottom"], ortho["plan_width"])
    _gutter_height(parts, py, py + ph, px, layout["plan_dim_left"], ortho["plan_depth"], side="left")

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
                       plan_kwargs=None, category_chip="", chrome=None,
                       assumptions=None, has_back=True, title_panel_style=None,
                       layout=None, ortho=None, plan_aside="",
                       include_side_elevation=False, side_args=(),
                       sheet_kind="idea", split_elevation=False):
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
    bp, *_ = build_fn(*iso_args, svg_w=iso_draw.w, svg_h=iso_draw.h,
                       panel_style=panel_style, channel_count=channel_count)
    iso_group.extend(bp)
    parts.append(f'<g transform="translate({iso_draw.x:.1f},{iso_draw.y:.1f})">')
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
        gap = 10.0
        half_w = (elev_safe.w - gap) / 2
        left_safe = Rect(elev_safe.x + 4, elev_safe.y, half_w - 4, elev_safe.h)
        right_safe = Rect(elev_safe.x + half_w + gap, elev_safe.y, half_w - 4, elev_safe.h)
        front_scale, fox, foy = _auto_scale_2d(
            width_in, elev_h or 1, left_safe.w, left_safe.h, margin=8, fill=0.9,
        )
        front_floor = foy + elev_h * front_scale
        front_group = []
        elev_fn(
            front_group, fox, front_floor, front_scale,
            width_in, depth_in, seat_h_in, back_h_in,
            panel_style=panel_style, channel_count=channel_count,
        )
        parts.append(
            f'<g transform="translate({left_safe.x:.1f},{left_safe.y:.1f})" '
            f'data-panel="front-elev">'
        )
        parts.extend(front_group)
        parts.append('</g>')
        side_scale, sox, soy = _auto_scale_2d(
            depth_in, elev_h or 1, right_safe.w, right_safe.h, margin=8, fill=0.9,
        )
        side_floor = soy + elev_h * side_scale
        side_group = []
        _side_straight(
            side_group, sox, side_floor, side_scale,
            depth_in, seat_h_in, back_h_in,
            panel_style=panel_style, channel_count=channel_count,
            panel_w=right_safe.w, panel_h=right_safe.h,
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

    if not include_side_elevation:
        _draw_ortho_dims(parts, layout, ortho)

    title = layout["title"]
    _title_block(parts, title.x, title.y, title.w, title.h,
                 name=name, quote_num=quote_num, dims_text=dims_text,
                 bench_type=bench_type, cushion_count=cushion_count,
                 cushion_width=cushion_width,
                 panel_style=title_panel_style or panel_style,
                 client=client, project=project, date=date,
                 category_chip=category_chip, chrome=chrome,
                 assumptions=assumptions, has_back=has_back)

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
    """Render a straight bench — 4-quadrant professional drawing.

    width_in is inches unless length_unit='ft'. Values ≤40 are not
    guessed as feet.
    """
    width_in = _inches_if_feet(width_in, kw.get("length_unit") or "in")
    has_back = bool(kw["has_back"]) if kw.get("has_back") is not None and "has_back" in kw else panel_style != "none"
    geo_back = float(back_h_in or 0) if has_back else 0.0
    draw_panel = panel_style if has_back else "none"

    # Cushion count from actual math
    c_count = max(1, math.ceil(width_in / cushion_width)) if cushion_width > 0 else 1

    if has_back:
        dims_text = f'{_in(width_in)} W × {_in(depth_in)} D × {_in(seat_h_in)} SH × {_in(geo_back)} BH'
    else:
        dims_text = f'{_in(width_in)} W × {_in(depth_in)} D × {_in(seat_h_in)} SH × NO BACK'

    extras = _sheet_extras(name, "straight", panel_style, has_back, geo_back, kw)
    layout = _regions_for(
        name, "straight", panel_style, has_back, c_count, cushion_width,
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
    ortho = {
        "plan_box": (safe_p.x + plan_ox, safe_p.y + plan_oy, width_in * plan_scale, depth_in * plan_scale),
        "plan_width": f'{_in(width_in)}',
        "plan_depth": f'{_in(depth_in)}',
        "elev_box": (safe_e.x + elev_ox, safe_e.y + elev_ground_y, width_in * elev_scale, elev_h * elev_scale),
        "elev_width": f'{_in(width_in)}',
        "elev_overall": f'{_in(elev_h)}',
        "elev_sh": f'{_in(seat_h_in)} SH',
        "elev_bh": f'{_in(geo_back)} BH',
        "sh_px": seat_h_in * elev_scale,
        "bh_px": geo_back * elev_scale,
    }
    iso_args = (name, width_in, depth_in, seat_h_in, geo_back, quote_num)

    include_side = bool(kw.get("include_side_elevation"))
    sheet_kind = "shop" if kw.get("sheet_kind") == "shop" else "idea"
    return _compose_multiview(
        name, "straight", _build_straight, _plan_straight, _elev_straight,
        dims_text, c_count, cushion_width, draw_panel, channel_count,
        quote_num, client, project, date=kw.get("date", ""),
        plan_args=plan_args, elev_args=elev_args, iso_args=iso_args,
        layout=layout, ortho=ortho,
        plan_aside=_back_style_label(panel_style, has_back=has_back),
        include_side_elevation=include_side,
        split_elevation=include_side,
        sheet_kind=sheet_kind,
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
