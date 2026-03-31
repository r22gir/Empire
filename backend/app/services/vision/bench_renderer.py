"""
Professional architectural bench renderer + CNC fabrication engine.

Layout (landscape 1200×850 viewBox):
  ┌──────────────────────────┬──────────────────────────┐
  │ Q1: PLAN VIEW            │ Q2: ISOMETRIC VIEW       │
  │ Top-down 2D, cushion     │ 30° isometric 3D,        │
  │ dividers C1..Cn, dims    │ channel/tufted back, dims│
  ├──────────────────────────┼──────────────────────────┤
  │ Q3: FRONT ELEVATION      │ Q4: TITLE BLOCK          │
  │ Side view, floor line,   │ Empire Workroom branding, │
  │ seat + back dims         │ item specs, scale bar     │
  └──────────────────────────┴──────────────────────────┘

Rules enforced:
  - Cushion count = math.ceil(width / cushion_width) — NEVER hardcoded
  - ALL text horizontal — zero rotation transforms
  - Auto-scaling: drawing fills 75-80% of quadrant
  - panel_style / channel_count are owner params, never overridden
  - CNC tiling for parts > 29" with 0.5" overlap
  - DXF export via ezdxf (optional — fails gracefully)
"""
import math
import os
import logging
from datetime import datetime

logger = logging.getLogger("bench_renderer")

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

# Layout
LAYOUT_W = 1200
LAYOUT_H = 850
MARGIN = 18
ZONE_GAP = 24       # 24px gap between quadrants (12px each side)

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
                 seat_h=18, back_h=34, cushion_width=24,
                 panel_style="vertical_channels", channel_count=6,
                 client="", project="", quote_num=""):
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
    return [
        Part("Seat Panel", model.width, model.depth, 0.75).classify(),
        Part("Back Panel", model.width, model.back_h, 0.75).classify(),
        Part("Side Panel L", model.depth, model.seat_h, 0.75).classify(),
        Part("Side Panel R", model.depth, model.seat_h, 0.75).classify(),
    ]


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
        size_str = f'{p.width:.0f}" × {p.length:.0f}"'
        lines.append(f"{p.name:<20} {size_str:>15} {p.process:>12}")
        if p.process == "CNC_TILE":
            tiles = generate_tiles(p.length)
            for i, (s, e) in enumerate(tiles, 1):
                lines.append(f"  Tile {i}: {s:.1f}\" – {e:.1f}\"")
    lines.append("")
    lines.append(f"Cushions: {model.cushion_count} @ {model.cushion_width}\" each")
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
    if panel_style == "flat":
        return
    elif panel_style == "horizontal_channels":
        count = max(2, channel_count)
        for i in range(1, count):
            cy = y + h * i / count
            parts.append(_line(x + 2, cy, x + w - 2, cy, SW_CHANNEL, LIGHT_GRAY))
    elif panel_style == "tufted" or panel_style == "button_tufted":
        # Diamond/button tufting grid
        rows = max(2, channel_count // 2)
        cols = max(3, channel_count)
        for r in range(rows + 1):
            for c in range(cols + 1):
                cx = x + w * c / cols
                cy = y + h * r / rows
                # Offset every other row
                if r % 2 == 1:
                    cx += w / cols / 2
                    if cx > x + w:
                        continue
                parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="1.5" fill="{GRAY}" stroke="none"/>')
        # Diamond lines for tufted
        if panel_style == "tufted":
            for r in range(rows):
                for c in range(cols):
                    cx1 = x + w * c / cols
                    cy1 = y + h * r / rows
                    cx2 = x + w * (c + 0.5) / cols
                    cy2 = y + h * (r + 0.5) / rows
                    if r % 2 == 1:
                        cx1 += w / cols / 2
                        cx2 += w / cols / 2
                    if cx2 <= x + w and cy2 <= y + h:
                        parts.append(_line(cx1, cy1, cx2, cy2, SW_CHANNEL, LIGHT_GRAY))
    else:
        # vertical_channels (default)
        count = max(2, channel_count)
        for i in range(1, count):
            cx = x + w * i / count
            parts.append(_line(cx, y + 2, cx, y + h - 2, SW_CHANNEL, LIGHT_GRAY))


def _draw_back_style_iso(parts, ox, oy, scale, sx, sy_back, width, sh, bh, bt,
                         panel_style, channel_count):
    """Draw back panel pattern on isometric back face."""
    if panel_style == "flat":
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
    else:
        # vertical_channels (default)
        count = max(2, channel_count)
        for i in range(1, count):
            cx = sx + width * i / count
            p1 = _iso(cx, sy_back, sh + 1, ox, oy, scale)
            p2 = _iso(cx, sy_back, sh + bh - 1, ox, oy, scale)
            parts.append(_line(p1[0], p1[1], p2[0], p2[1], SW_CHANNEL))


def _back_style_label(panel_style):
    """Human-readable label for the back style."""
    labels = {
        "vertical_channels": "CHANNELED BACK",
        "horizontal_channels": "H-CHANNELED BACK",
        "tufted": "TUFTED BACK",
        "button_tufted": "BUTTON TUFTED BACK",
        "flat": "FLAT BACK",
    }
    return labels.get(panel_style, "CHANNELED BACK")


# ── PLAN VIEW ──────────────────────────────────────────────────────

def _plan_straight(parts, ox, oy, scale, width, depth, seat_h, back_h,
                   cushion_width=24, panel_style="vertical_channels", channel_count=6):
    """Plan view — top-down rectangle with cushion dividers and numbering."""
    bt = BACK_T
    w = width * scale
    d = depth * scale
    bt_s = bt * scale

    # Seat area
    parts.append(_rect(ox, oy, w, d - bt_s, SW_HEAVY))
    # Back panel
    parts.append(_rect(ox, oy + d - bt_s, w, bt_s, SW_HEAVY, fill="#F0F0F0"))

    # Back style pattern on back strip
    _draw_back_style_2d(parts, ox, oy + d - bt_s, w, bt_s, panel_style, channel_count)

    # Cushion dividers + numbering
    c_count = max(1, math.ceil(width / cushion_width)) if cushion_width > 0 else 1
    if c_count > 1:
        for i in range(1, c_count):
            cx = ox + w * i / c_count
            parts.append(_line(cx, oy + 2, cx, oy + d - bt_s - 2, SW_LIGHT, GRAY))
    # Cushion labels
    for i in range(c_count):
        label_x = ox + w * (i + 0.5) / c_count
        label_y = oy + (d - bt_s) / 2
        _cushion_label(parts, label_x, label_y, i + 1)

    # Back style label
    parts.append(_text(ox + w / 2, oy + d + 14, _back_style_label(panel_style), 7, fill=GRAY, weight="600"))

    # Dimensions
    _dim_2d_h(parts, ox, ox + w, oy + d + 20, f'{width:.0f}"', 18)
    _dim_2d_v(parts, ox, oy, oy + d, f'{depth:.0f}"', -22)


def _plan_l_shape(parts, ox, oy, scale, long, short, depth, seat_h, back_h,
                  cushion_width=24, panel_style="vertical_channels", channel_count=6):
    """Plan view — L-shaped bench."""
    bt = BACK_T
    d_s = depth * scale
    bt_s = bt * scale
    long_s = long * scale
    short_s = short * scale

    # Long section seat
    parts.append(_rect(ox, oy, long_s, d_s - bt_s, SW_HEAVY))
    parts.append(_rect(ox, oy + d_s - bt_s, long_s, bt_s, SW_HEAVY, fill="#F0F0F0"))
    _draw_back_style_2d(parts, ox, oy + d_s - bt_s, long_s, bt_s, panel_style, channel_count)

    # Short wing
    wing_x = ox + long_s - d_s + bt_s
    wing_y = oy + d_s
    wing_w = d_s - bt_s
    wing_h = short_s - d_s
    if wing_h > 0:
        parts.append(_rect(wing_x, wing_y, wing_w, wing_h, SW_HEAVY))
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

    # Dimensions
    _dim_2d_h(parts, ox, ox + long_s, oy - 4, f'{long:.0f}"', -18)
    _dim_2d_v(parts, ox + long_s + bt_s + 4, oy, oy + d_s + wing_h, f'{short:.0f}"', 18)
    _dim_2d_v(parts, ox - 4, oy, oy + d_s, f'{depth:.0f}"', -18)


def _plan_u_shape(parts, ox, oy, scale, back, side, depth, side_depth, seat_h, back_h,
                  cushion_width=24, panel_style="vertical_channels", channel_count=6):
    """Plan view — U-shaped booth."""
    bt = BACK_T
    d_s = depth * scale
    sd_s = side_depth * scale
    bt_s = bt * scale
    back_s = back * scale
    side_s = side * scale
    total_w = (back + side_depth * 2) * scale

    # Left wing
    parts.append(_rect(ox, oy, sd_s - bt_s, side_s, SW_HEAVY))
    parts.append(_rect(ox - bt_s, oy, bt_s, side_s, SW_HEAVY, fill="#F0F0F0"))

    # Center back
    cx = ox + sd_s
    cy = oy + side_s - d_s
    parts.append(_rect(cx, cy, back_s, d_s - bt_s, SW_HEAVY))
    parts.append(_rect(cx, cy + d_s - bt_s, back_s, bt_s, SW_HEAVY, fill="#F0F0F0"))
    _draw_back_style_2d(parts, cx, cy + d_s - bt_s, back_s, bt_s, panel_style, channel_count)

    # Right wing
    rx = ox + sd_s + back_s
    parts.append(_rect(rx + bt_s, oy, sd_s - bt_s, side_s, SW_HEAVY))
    parts.append(_rect(rx + sd_s, oy, bt_s, side_s, SW_HEAVY, fill="#F0F0F0"))

    _miter_callout(parts, cx, cy + d_s - bt_s)
    _miter_callout(parts, rx, cy + d_s - bt_s)

    # Cushion labels
    _cushion_label(parts, ox + (sd_s - bt_s) / 2, oy + side_s / 2, 1)

    c_back = max(1, math.ceil(back / cushion_width)) if cushion_width > 0 else 1
    for i in range(c_back):
        lx = cx + back_s * (i + 0.5) / c_back
        _cushion_label(parts, lx, cy + (d_s - bt_s) / 2, 2 + i)

    _cushion_label(parts, rx + bt_s + (sd_s - bt_s) / 2, oy + side_s / 2, 2 + c_back)

    # Dimensions
    _dim_2d_h(parts, ox, ox + total_w, oy + side_s + 4, f'{back + side_depth * 2:.0f}"', 18)
    _dim_2d_v(parts, ox - bt_s - 4, oy, oy + side_s, f'{side:.0f}"', -18)
    _dim_2d_h(parts, cx, cx + back_s, oy - 4, f'{back:.0f}"', -18)


# ── FRONT ELEVATION ───────────────────────────────────────────────

def _elev_straight(parts, ox, oy, scale, width, depth, seat_h, back_h,
                   panel_style="vertical_channels", channel_count=6):
    """Front elevation with floor line, seat, back, and dimensions."""
    w = width * scale
    sh = seat_h * scale
    bh = back_h * scale

    # Floor line (dashed)
    parts.append(_line(ox - 15, oy, ox + w + 15, oy, SW_FLOOR, GRAY, "6,3"))
    parts.append(_text(ox - 18, oy + 4, "FL", 7, anchor="end", fill=GRAY))

    # Seat box
    parts.append(_rect(ox, oy - sh, w, sh, SW_HEAVY))
    # Back panel
    parts.append(_rect(ox, oy - sh - bh, w, bh, SW_MED))

    # Back style pattern
    _draw_back_style_2d(parts, ox, oy - sh - bh, w, bh, panel_style, channel_count)

    # Seat/back separation line
    parts.append(_line(ox, oy - sh, ox + w, oy - sh, SW_MED))

    # Dimensions — all horizontal text
    _dim_2d_h(parts, ox, ox + w, oy, f'{width:.0f}"', 18)
    _dim_2d_v(parts, ox + w, oy, oy - sh, f'{seat_h:.0f}" SH', 22)
    _dim_2d_v(parts, ox + w + 40, oy - sh, oy - sh - bh, f'{back_h:.0f}" BH', 22)
    _dim_2d_v(parts, ox - 4, oy, oy - sh - bh, f'{seat_h + back_h:.0f}"', -24)


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
    bt = BACK_T

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

def _title_block(parts, x, y, w, h, name="", quote_num="", dims_text="",
                 bench_type="STRAIGHT", cushion_count=1, cushion_width=24,
                 panel_style="vertical_channels", client="", project="", date=""):
    """Professional title block with Empire Workroom branding and specs."""
    # Outer + inner border
    parts.append(_rect(x, y, w, h, SW_BORDER))
    parts.append(_rect(x + 3, y + 3, w - 6, h - 6, 0.5))

    # Company name
    parts.append(_text(x + w / 2, y + 28, "EMPIRE WORKROOM", 20, weight="bold"))
    parts.append(_text(x + w / 2, y + 44, "CUSTOM UPHOLSTERY & FABRICATION", 8, fill=GRAY))
    parts.append(_text(x + w / 2, y + 56, "5124 Frolich Ln, Hyattsville, MD 20781", 7, fill=GRAY))
    parts.append(_text(x + w / 2, y + 66, "(703) 213-6484 | workroom@empirebox.store", 7, fill=GRAY))

    # Divider
    parts.append(_line(x + 15, y + 74, x + w - 15, y + 74, 0.5))

    # Info rows
    row_y = y + 90
    row_h = 18
    col1_x = x + 15

    rows = [
        ("ITEM:", (name or "BENCH").upper()),
        ("TYPE:", bench_type.upper().replace("_", " ")),
        ("DIMENSIONS:", dims_text or "SEE VIEWS"),
        ("CUSHIONS:", f"{cushion_count} @ {cushion_width}\" each"),
        ("BACK STYLE:", _back_style_label(panel_style)),
    ]
    if client:
        rows.append(("CLIENT:", client.upper()))
    if project:
        rows.append(("PROJECT:", project.upper()))
    if quote_num:
        rows.append(("QUOTE:", quote_num))
    rows.append(("DATE:", date or datetime.now().strftime("%m/%d/%Y")))
    rows.append(("DRAWN BY:", "MAX AI / Empire Workroom"))

    for label, value in rows:
        parts.append(_text(col1_x, row_y, label, 8, anchor="start", weight="bold"))
        parts.append(_text(col1_x + 85, row_y, value, 8, anchor="start"))
        row_y += row_h

    # Scale bar
    bar_y = y + h - 42
    bar_x = x + 25
    bar_w = w - 50
    parts.append(_text(x + w / 2, bar_y - 6, "SCALE REFERENCE", 7, weight="bold"))
    seg_count = 4
    seg_w = bar_w / seg_count
    for i in range(seg_count):
        fill = "#000" if i % 2 == 0 else "#FFF"
        parts.append(_rect(bar_x + i * seg_w, bar_y, seg_w, 7, 0.5, fill=fill))
    for i in range(seg_count + 1):
        parts.append(_text(bar_x + i * seg_w, bar_y + 17, f'{i * 12}"', 6))


# ── VIEW FRAME ───────────────────────────────────────────────────

def _view_frame(parts, x, y, w, h, label):
    """Thin frame around a view zone with label."""
    parts.append(_rect(x, y, w, h, 0.5, stroke=GRAY))
    parts.append(_text(x + w / 2, y + 14, label, 10, weight="bold"))


# ── BUILD FUNCTIONS (isometric) ──────────────────────────────────

def _build_straight(name, width_in, depth_in, seat_h_in, back_h_in, quote_num="",
                    svg_w=500, svg_h=350, panel_style="vertical_channels", channel_count=6):
    total_h = seat_h_in + back_h_in
    scale, ox, oy = _auto_scale((width_in, depth_in, total_h), svg_w, svg_h)
    parts = []
    _draw_bench_box(parts, ox, oy, scale, 0, 0, width_in, depth_in, seat_h_in, back_h_in,
                    panel_style, channel_count)

    _dim_iso_width(parts, ox, oy, scale, 0, width_in, -3, -6, f'{width_in:.0f}"', below=True)
    _dim_iso_height(parts, ox, oy, scale, width_in + 6, depth_in, seat_h_in, total_h, f'{back_h_in:.0f}" BH')
    _dim_iso_height(parts, ox, oy, scale, width_in + 20, -3, 0, seat_h_in, f'{seat_h_in:.0f}" SH')
    _dim_iso_depth(parts, ox, oy, scale, width_in + 4, 0, depth_in, -3, f'{depth_in:.0f}"')

    return parts, scale, ox, oy


def _build_l_shape(name, long_in, short_in, depth_in, seat_h_in, back_h_in, quote_num="",
                   svg_w=500, svg_h=350, panel_style="vertical_channels", channel_count=6):
    total_h = seat_h_in + back_h_in
    scale, ox, oy = _auto_scale((long_in, short_in, total_h), svg_w, svg_h)
    parts = []

    _draw_bench_box(parts, ox, oy, scale, 0, short_in - depth_in, long_in, depth_in, seat_h_in, back_h_in,
                    panel_style, channel_count)
    _draw_bench_box(parts, ox, oy, scale, long_in - depth_in, 0, depth_in, short_in, seat_h_in, back_h_in,
                    panel_style, channel_count)

    _dim_iso_width(parts, ox, oy, scale, 0, long_in, short_in - depth_in - 3, total_h + 6, f'{long_in:.0f}"', below=False)
    _dim_iso_depth(parts, ox, oy, scale, long_in + 4, 0, short_in, -3, f'{short_in:.0f}"')
    _dim_iso_depth(parts, ox, oy, scale, long_in + 20, short_in - depth_in, short_in, -3, f'{depth_in:.0f}"')
    _dim_iso_height(parts, ox, oy, scale, long_in + 6, -3, seat_h_in, total_h, f'{back_h_in:.0f}" BH')
    _dim_iso_height(parts, ox, oy, scale, long_in + 6, short_in - 3, 0, seat_h_in, f'{seat_h_in:.0f}" SH')

    return parts, scale, ox, oy


def _build_u_shape(name, back_in, side_in, depth_in, side_depth_in, seat_h_in, back_h_in,
                   quote_num="", svg_w=500, svg_h=350,
                   panel_style="vertical_channels", channel_count=6):
    total_h = seat_h_in + back_h_in
    total_w = back_in + side_depth_in * 2
    scale, ox, oy = _auto_scale((total_w, side_in, total_h), svg_w, svg_h)
    parts = []

    _draw_bench_box(parts, ox, oy, scale, 0, 0, side_depth_in, side_in, seat_h_in, back_h_in,
                    panel_style, channel_count)
    _draw_bench_box(parts, ox, oy, scale, side_depth_in, side_in - depth_in, back_in, depth_in, seat_h_in, back_h_in,
                    panel_style, channel_count)
    _draw_bench_box(parts, ox, oy, scale, side_depth_in + back_in, 0, side_depth_in, side_in, seat_h_in, back_h_in,
                    panel_style, channel_count)

    _dim_iso_width(parts, ox, oy, scale, side_depth_in, side_depth_in + back_in, side_in - depth_in - 3, total_h + 6, f'{back_in:.0f}"', below=False)
    _dim_iso_depth(parts, ox, oy, scale, -6, 0, side_in, -3, f'{side_in:.0f}"')
    _dim_iso_height(parts, ox, oy, scale, -6, -3, seat_h_in, total_h, f'{back_h_in:.0f}" BH', right=False)
    _dim_iso_height(parts, ox, oy, scale, total_w + 6, -3, 0, seat_h_in, f'{seat_h_in:.0f}" SH')
    _dim_iso_depth(parts, ox, oy, scale, total_w + 4, 0, side_in, -3, f'{side_in:.0f}"')
    _dim_iso_depth(parts, ox, oy, scale, side_depth_in - 6, side_in - depth_in, side_in, -3, f'{depth_in:.0f}"')
    _dim_iso_width(parts, ox, oy, scale, 0, side_depth_in, -3, -6, f'{side_depth_in:.0f}"', below=True)
    _dim_iso_width(parts, ox, oy, scale, side_depth_in + back_in, total_w, -3, -6, f'{side_depth_in:.0f}"', below=True)

    return parts, scale, ox, oy


# ── MULTI-VIEW COMPOSITION ──────────────────────────────────────

def _compose_multiview(name, bench_type, build_fn, plan_fn, elev_fn,
                       dims_text, cushion_count, cushion_width=24,
                       panel_style="vertical_channels", channel_count=6,
                       quote_num="", client="", project="", date="",
                       plan_args=(), elev_args=(), iso_args=()):
    """Compose a 4-quadrant multi-view drawing."""
    parts = [_defs()]
    parts.append(f'<rect width="{LAYOUT_W}" height="{LAYOUT_H}" fill="white"/>')

    # Double border
    parts.append(_rect(4, 4, LAYOUT_W - 8, LAYOUT_H - 8, SW_BORDER))
    parts.append(_rect(8, 8, LAYOUT_W - 16, LAYOUT_H - 16, 0.5))

    # ── Q1: PLAN VIEW (top-left) ──
    _view_frame(parts, Q1_X, Q1_Y, Q1_W, Q1_H, "PLAN VIEW")
    plan_group = []
    plan_fn(plan_group, *plan_args, cushion_width=cushion_width,
            panel_style=panel_style, channel_count=channel_count)
    parts.append(f'<g transform="translate({Q1_X:.0f},{Q1_Y + 20:.0f})">')
    parts.extend(plan_group)
    parts.append('</g>')

    # ── Q2: ISOMETRIC VIEW (top-right) ──
    _view_frame(parts, Q2_X, Q2_Y, Q2_W, Q2_H, "ISOMETRIC VIEW")
    iso_group = []
    bp, *_ = build_fn(*iso_args, svg_w=Q2_W - 20, svg_h=Q2_H - 30,
                       panel_style=panel_style, channel_count=channel_count)
    iso_group.extend(bp)
    parts.append(f'<g transform="translate({Q2_X + 10:.0f},{Q2_Y + 20:.0f})">')
    parts.extend(iso_group)
    parts.append('</g>')

    # ── Q3: FRONT ELEVATION (bottom-left) ──
    _view_frame(parts, Q3_X, Q3_Y, Q3_W, Q3_H, "FRONT ELEVATION")
    elev_group = []
    elev_fn(elev_group, *elev_args, panel_style=panel_style, channel_count=channel_count)
    parts.append(f'<g transform="translate({Q3_X:.0f},{Q3_Y + 20:.0f})">')
    parts.extend(elev_group)
    parts.append('</g>')

    # ── Q4: TITLE BLOCK (bottom-right) ──
    _title_block(parts, Q4_X, Q4_Y, Q4_W, Q4_H,
                 name=name, quote_num=quote_num, dims_text=dims_text,
                 bench_type=bench_type, cushion_count=cushion_count,
                 cushion_width=cushion_width, panel_style=panel_style,
                 client=client, project=project, date=date)

    return _wrap_svg_raw(parts, LAYOUT_W, LAYOUT_H)


# ── PUBLIC RENDER FUNCTIONS ──────────────────────────────────────
# Signatures preserved for compatibility with tool_executor.py and drawings.py

def render_straight(name, width_in, depth_in=20, seat_h_in=18, back_h_in=18,
                    quote_num="", svg_w=600, svg_h=400,
                    cushion_width=24, panel_style="vertical_channels", channel_count=6,
                    client="", project="", **kw):
    """Render a straight bench — 4-quadrant professional drawing."""
    if width_in < 50 and 'rate' not in kw:
        width_in = width_in * 12

    # Cushion count from actual math
    c_count = max(1, math.ceil(width_in / cushion_width)) if cushion_width > 0 else 1

    dims_text = f'{width_in:.0f}" W × {depth_in:.0f}" D × {seat_h_in:.0f}" SH × {back_h_in:.0f}" BH'

    plan_scale, plan_ox, plan_oy = _auto_scale_2d(width_in, depth_in, Q1_W - 20, Q1_H - 60)
    plan_args = (plan_ox + 10, plan_oy + 10, plan_scale, width_in, depth_in, seat_h_in, back_h_in)

    elev_scale, elev_ox, elev_oy = _auto_scale_2d(width_in, seat_h_in + back_h_in, Q3_W - 20, Q3_H - 60)
    elev_ground_y = elev_oy + (seat_h_in + back_h_in) * elev_scale + 10
    elev_args = (elev_ox + 10, elev_ground_y, elev_scale, width_in, depth_in, seat_h_in, back_h_in)

    iso_args = (name, width_in, depth_in, seat_h_in, back_h_in, quote_num)

    return _compose_multiview(
        name, "straight", _build_straight, _plan_straight, _elev_straight,
        dims_text, c_count, cushion_width, panel_style, channel_count,
        quote_num, client, project,
        plan_args=plan_args, elev_args=elev_args, iso_args=iso_args,
    )


def render_l_shape(name, long_in, short_in=0, depth_in=20, seat_h_in=18, back_h_in=18,
                   quote_num="", svg_w=600, svg_h=400,
                   cushion_width=24, panel_style="vertical_channels", channel_count=6,
                   client="", project="", **kw):
    """Render an L-shaped bench — 4-quadrant professional drawing."""
    if long_in < 50:
        lf = long_in
        long_in = lf * 0.6 * 12
        if short_in == 0 or short_in < 10:
            short_in = lf * 0.4 * 12
    if short_in == 0:
        short_in = long_in * 0.5

    c_count = max(1, math.ceil(long_in / cushion_width)) if cushion_width > 0 else 1

    dims_text = f'{long_in:.0f}" L × {short_in:.0f}" S × {depth_in:.0f}" D × {seat_h_in:.0f}" SH × {back_h_in:.0f}" BH'

    plan_scale, plan_ox, plan_oy = _auto_scale_2d(long_in, short_in, Q1_W - 20, Q1_H - 60)
    plan_args = (plan_ox + 10, plan_oy + 10, plan_scale, long_in, short_in, depth_in, seat_h_in, back_h_in)

    elev_scale, elev_ox, elev_oy = _auto_scale_2d(long_in, seat_h_in + back_h_in, Q3_W - 20, Q3_H - 60)
    elev_ground_y = elev_oy + (seat_h_in + back_h_in) * elev_scale + 10
    elev_args = (elev_ox + 10, elev_ground_y, elev_scale, long_in, short_in, depth_in, seat_h_in, back_h_in)

    iso_args = (name, long_in, short_in, depth_in, seat_h_in, back_h_in, quote_num)

    return _compose_multiview(
        name, "l_shape", _build_l_shape, _plan_l_shape, _elev_l_shape,
        dims_text, c_count, cushion_width, panel_style, channel_count,
        quote_num, client, project,
        plan_args=plan_args, elev_args=elev_args, iso_args=iso_args,
    )


def render_u_shape(name, back_in, side_in=0, depth_in=20, side_depth_in=0,
                   seat_h_in=18, back_h_in=18, multiplier=1,
                   quote_num="", svg_w=600, svg_h=400,
                   cushion_width=24, panel_style="vertical_channels", channel_count=6,
                   client="", project="", **kw):
    """Render a U-shaped booth — 4-quadrant professional drawing."""
    if back_in < 50:
        lf = back_in
        per = lf / multiplier if multiplier > 1 else lf
        back_in = per * 0.45 * 12
        if side_in == 0:
            side_in = per * 0.275 * 12
        if side_depth_in == 0:
            side_depth_in = depth_in
    if side_in == 0:
        side_in = back_in * 0.6
    if side_depth_in == 0:
        side_depth_in = depth_in

    total_w = back_in + side_depth_in * 2
    c_back = max(1, math.ceil(back_in / cushion_width)) if cushion_width > 0 else 1
    c_count = c_back + 2  # left wing + back cushions + right wing

    dims_text = (f'{back_in:.0f}" B × {side_in:.0f}" S × {depth_in:.0f}" D × '
                 f'{side_depth_in:.0f}" SD × {seat_h_in:.0f}" SH × {back_h_in:.0f}" BH')

    plan_scale, plan_ox, plan_oy = _auto_scale_2d(total_w, side_in, Q1_W - 20, Q1_H - 60)
    plan_args = (plan_ox + 10, plan_oy + 10, plan_scale, back_in, side_in, depth_in, side_depth_in, seat_h_in, back_h_in)

    elev_scale, elev_ox, elev_oy = _auto_scale_2d(total_w, seat_h_in + back_h_in, Q3_W - 20, Q3_H - 60)
    elev_ground_y = elev_oy + (seat_h_in + back_h_in) * elev_scale + 10
    elev_args = (elev_ox + 10, elev_ground_y, elev_scale, back_in, side_in, depth_in, side_depth_in, seat_h_in, back_h_in)

    iso_args = (name, back_in, side_in, depth_in, side_depth_in, seat_h_in, back_h_in, quote_num)

    return _compose_multiview(
        name, "u_shape", _build_u_shape, _plan_u_shape, _elev_u_shape,
        dims_text, c_count, cushion_width, panel_style, channel_count,
        quote_num, client, project,
        plan_args=plan_args, elev_args=elev_args, iso_args=iso_args,
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
            svg = render_u_shape(name, lf, multiplier=mult, quote_num=quote_num)
        elif "l-shape" in desc_lower or "l shape" in desc_lower:
            svg = render_l_shape(name, lf, quote_num=quote_num)
        else:
            svg = render_straight(name, lf, quote_num=quote_num)
        results.append({"name": name, "svg": svg, "lf": lf})
    return results


def drawings_to_pdf(drawings, output_path):
    """Convert list of drawing dicts to a multi-page PDF."""
    from weasyprint import HTML as WeasyHTML
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    html = (
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        '<style>@page{size:letter landscape;margin:0.3in}'
        'body{margin:0}.pg{page-break-after:always;display:flex;'
        'align-items:center;justify-content:center;min-height:92vh}'
        '.pg:last-child{page-break-after:auto}</style></head><body>'
    )
    for d in drawings:
        html += f'<div class="pg">{d["svg"]}</div>'
    html += '</body></html>'
    WeasyHTML(string=html).write_pdf(output_path)
    return output_path
