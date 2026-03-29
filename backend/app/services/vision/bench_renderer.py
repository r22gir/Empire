"""
Professional architectural bench renderer — multi-view shop drawings.

Layout (landscape 1200x850):
  +---------------------------+---------------------------+
  |        PLAN VIEW          |      ISOMETRIC VIEW       |
  |      (top-down 2D)        |     (30-degree 3D)        |
  +---------------------------+---------------------------+
  |    FRONT ELEVATION        |       TITLE BLOCK         |
  |    (straight-on view)     | Empire Workroom + details |
  +---------------------------+---------------------------+

Features:
- Professional dimension system with arrow markers and extension lines
- Cushion auto-numbering with miter joint callouts
- Line weight hierarchy (heavy/medium/dim/light/border/extension)
- Empire Workroom title block with scale bar
- All text horizontal or bottom-to-top (never angled)
"""
import math
import os

# ── CONSTANTS ──────────────────────────────────────────────────────
ISO_A = 30
COS_A = math.cos(math.radians(ISO_A))
SIN_A = math.sin(math.radians(ISO_A))

# Line weight hierarchy
SW_HEAVY = 2.5       # cut lines, outlines of primary geometry
SW_MED = 1.5         # secondary outlines, visible edges
SW_DIM = 0.75        # dimension + extension lines
SW_LIGHT = 0.4       # channel lines, hatching, subtle detail
SW_BORDER = 2.0      # drawing border
SW_EXT = 0.5         # extension lines past dimension arrows
SW_CHAN = 0.3         # channel lines (very subtle)

FONT = "Arial, Helvetica, sans-serif"
BLACK = "#000000"
GRAY = "#666666"
LIGHT_GRAY = "#CCCCCC"
BACK_T = 4           # back cushion thickness (visual constant, inches)

# Multi-view layout zones (within 1200x850 viewBox)
LAYOUT_W = 1200
LAYOUT_H = 850
MARGIN = 18
ZONE_GAP = 12

# Quadrant coordinates (with margins and gap)
HALF_W = (LAYOUT_W - MARGIN * 2 - ZONE_GAP) / 2
HALF_H = (LAYOUT_H - MARGIN * 2 - ZONE_GAP) / 2

PLAN_X = MARGIN
PLAN_Y = MARGIN
PLAN_W = HALF_W
PLAN_H = HALF_H

ISO_X = MARGIN + HALF_W + ZONE_GAP
ISO_Y = MARGIN
ISO_W = HALF_W
ISO_H = HALF_H

ELEV_X = MARGIN
ELEV_Y = MARGIN + HALF_H + ZONE_GAP
ELEV_W = HALF_W
ELEV_H = HALF_H

TITLE_X = MARGIN + HALF_W + ZONE_GAP
TITLE_Y = MARGIN + HALF_H + ZONE_GAP
TITLE_W = HALF_W
TITLE_H = HALF_H


# ── ISOMETRIC PROJECTION ──────────────────────────────────────────

def _iso(x, y, z, ox, oy, s):
    """3D (x=width, y=depth, z=height) -> 2D isometric screen coords."""
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


def _auto_scale_2d(w, h, area_w, area_h, margin=40):
    """Compute scale and origin to fit a 2D rect centered in an area."""
    if w == 0 or h == 0:
        return 1.0, area_w / 2, area_h / 2
    scale = min((area_w - margin * 2) / w, (area_h - margin * 2) / h)
    ox = (area_w - w * scale) / 2
    oy = (area_h - h * scale) / 2
    return scale, ox, oy


# ── SVG PRIMITIVES ────────────────────────────────────────────────

def _poly(pts, sw=SW_MED, fill="none", stroke=BLACK):
    points = " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in pts)
    return f'<polygon points="{points}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"/>'


def _line(x1, y1, x2, y2, sw=SW_MED, stroke=BLACK):
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{sw}"/>'


def _rect(x, y, w, h, sw=SW_MED, fill="none", stroke=BLACK):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


def _text(x, y, txt, size=10, anchor="middle", weight="normal", rotate=0, fill=BLACK):
    rot = f' transform="rotate({rotate},{x:.1f},{y:.1f})"' if rotate else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        f'font-family="{FONT}" font-size="{size}" fill="{fill}" '
        f'font-weight="{weight}"{rot}>{txt}</text>'
    )


def _defs():
    return '''<defs>
  <marker id="dim-arrow" viewBox="0 0 10 6" refX="10" refY="3"
          markerWidth="8" markerHeight="6" orient="auto-start-reverse">
    <path d="M0,0 L10,3 L0,6 Z" fill="#000"/>
  </marker>
  <marker id="dim-arrow-open" viewBox="0 0 10 6" refX="10" refY="3"
          markerWidth="8" markerHeight="6" orient="auto-start-reverse">
    <path d="M0,0 L10,3 L0,6" fill="none" stroke="#000" stroke-width="1"/>
  </marker>
</defs>'''


# ── DIMENSION CALLOUTS ────────────────────────────────────────────

def _dim_h(parts, p1, p2, label, offset_y, text_side="above"):
    """Horizontal dimension line between two 2D points."""
    gap = 3
    ext_extra = 5
    dy = offset_y
    sign = 1 if dy > 0 else -1

    e1_start = (p1[0], p1[1] + gap * sign)
    e1_end = (p1[0], p1[1] + dy + ext_extra * sign)
    e2_start = (p2[0], p2[1] + gap * sign)
    e2_end = (p2[0], p2[1] + dy + ext_extra * sign)

    parts.append(_line(e1_start[0], e1_start[1], e1_end[0], e1_end[1], SW_EXT))
    parts.append(_line(e2_start[0], e2_start[1], e2_end[0], e2_end[1], SW_EXT))

    d1 = (p1[0], p1[1] + dy)
    d2 = (p2[0], p2[1] + dy)
    parts.append(
        f'<line x1="{d1[0]:.1f}" y1="{d1[1]:.1f}" x2="{d2[0]:.1f}" y2="{d2[1]:.1f}" '
        f'stroke="{BLACK}" stroke-width="{SW_DIM}" '
        f'marker-start="url(#dim-arrow)" marker-end="url(#dim-arrow)"/>'
    )

    mx = (d1[0] + d2[0]) / 2
    my = (d1[1] + d2[1]) / 2
    text_y = my - 4 if text_side == "above" else my + 12
    parts.append(_text(mx, text_y, label, 9, weight="600"))


def _dim_v(parts, p1, p2, label, offset_x, text_side="right"):
    """Vertical dimension line between two 2D points."""
    gap = 3
    ext_extra = 5
    sign = 1 if offset_x > 0 else -1

    e1_start = (p1[0] + gap * sign, p1[1])
    e1_end = (p1[0] + offset_x + ext_extra * sign, p1[1])
    e2_start = (p2[0] + gap * sign, p2[1])
    e2_end = (p2[0] + offset_x + ext_extra * sign, p2[1])

    parts.append(_line(e1_start[0], e1_start[1], e1_end[0], e1_end[1], SW_EXT))
    parts.append(_line(e2_start[0], e2_start[1], e2_end[0], e2_end[1], SW_EXT))

    d1 = (p1[0] + offset_x, p1[1])
    d2 = (p2[0] + offset_x, p2[1])
    parts.append(
        f'<line x1="{d1[0]:.1f}" y1="{d1[1]:.1f}" x2="{d2[0]:.1f}" y2="{d2[1]:.1f}" '
        f'stroke="{BLACK}" stroke-width="{SW_DIM}" '
        f'marker-start="url(#dim-arrow)" marker-end="url(#dim-arrow)"/>'
    )

    mx = (d1[0] + d2[0]) / 2
    my = (d1[1] + d2[1]) / 2
    tx = mx + (8 if text_side == "right" else -8)
    parts.append(_text(tx, my + 3, label, 9, weight="600", rotate=-90))


def _dim_iso_width(parts, ox, oy, scale, x1, x2, y, z, label, below=True):
    """Width dimension along isometric X axis."""
    p1 = _iso(x1, y, z, ox, oy, scale)
    p2 = _iso(x2, y, z, ox, oy, scale)
    off = 22 if below else -22
    _dim_h(parts, p1, p2, label, off, "below" if below else "above")


def _dim_iso_depth(parts, ox, oy, scale, x, y1, y2, z, label, below=True):
    """Depth dimension along isometric Y axis."""
    p1 = _iso(x, y1, z, ox, oy, scale)
    p2 = _iso(x, y2, z, ox, oy, scale)
    off = 22 if below else -22
    _dim_h(parts, p1, p2, label, off, "below" if below else "above")


def _dim_iso_height(parts, ox, oy, scale, x, y, z1, z2, label, right=True):
    """Height dimension (vertical in iso)."""
    p1 = _iso(x, y, z1, ox, oy, scale)
    p2 = _iso(x, y, z2, ox, oy, scale)
    off = 18 if right else -18
    _dim_v(parts, p1, p2, label, off, "right" if right else "left")


def _dim_2d_h(parts, x1, x2, y, label, offset_y=20):
    """2D horizontal dimension for plan/elevation views."""
    _dim_h(parts, (x1, y), (x2, y), label, offset_y, "below" if offset_y > 0 else "above")


def _dim_2d_v(parts, x, y1, y2, label, offset_x=20):
    """2D vertical dimension for plan/elevation views."""
    _dim_v(parts, (x, y1), (x, y2), label, offset_x, "right" if offset_x > 0 else "left")


# ── CUSHION NUMBERING ─────────────────────────────────────────────

def _cushion_label(parts, cx, cy, num, size=11):
    """Draw a circled cushion number at (cx, cy)."""
    r = size * 0.7
    parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="white" stroke="{BLACK}" stroke-width="{SW_DIM}"/>')
    parts.append(_text(cx, cy + size * 0.35, str(num), size, weight="bold"))


def _miter_callout(parts, x, y, angle=45):
    """Draw miter joint indicator — small diagonal line with 'MITER' label."""
    length = 12
    rad = math.radians(angle)
    dx = length * math.cos(rad)
    dy = length * math.sin(rad)
    parts.append(_line(x - dx, y - dy, x + dx, y + dy, SW_DIM))
    parts.append(_text(x + dx + 4, y - dy - 4, "MITER", 7, anchor="start", weight="600", fill=GRAY))


# ── PLAN VIEW (top-down 2D) ──────────────────────────────────────

def _plan_straight(parts, ox, oy, scale, width, depth, seat_h, back_h):
    """Draw plan view of straight bench — top-down rectangle."""
    bt = BACK_T
    w = width * scale
    d = depth * scale
    bt_s = bt * scale

    # Seat area
    parts.append(_rect(ox, oy, w, d - bt_s, SW_HEAVY))
    # Back panel
    parts.append(_rect(ox, oy + d - bt_s, w, bt_s, SW_HEAVY, fill="#F0F0F0"))

    # Channel lines on seat
    num_ch = max(int(width / 12), 2)
    for i in range(1, num_ch):
        cx = ox + w * i / num_ch
        parts.append(_line(cx, oy, cx, oy + d - bt_s, SW_LIGHT, LIGHT_GRAY))

    # Cushion number
    _cushion_label(parts, ox + w / 2, oy + (d - bt_s) / 2, 1)

    # Dimensions
    _dim_2d_h(parts, ox, ox + w, oy + d, f'{width:.0f}"', 18)
    _dim_2d_v(parts, ox, oy, oy + d, f'{depth:.0f}"', -20)


def _plan_l_shape(parts, ox, oy, scale, long, short, depth, seat_h, back_h):
    """Draw plan view of L-shape bench."""
    bt = BACK_T
    d_s = depth * scale
    bt_s = bt * scale
    long_s = long * scale
    short_s = short * scale

    # Long section seat (along top)
    parts.append(_rect(ox, oy, long_s, d_s - bt_s, SW_HEAVY))
    # Long section back
    parts.append(_rect(ox, oy + d_s - bt_s, long_s, bt_s, SW_HEAVY, fill="#F0F0F0"))

    # Short wing seat (right side, going down)
    wing_x = ox + long_s - d_s + bt_s
    wing_y = oy + d_s
    wing_w = d_s - bt_s
    wing_h = short_s - d_s
    if wing_h > 0:
        parts.append(_rect(wing_x, wing_y, wing_w, wing_h, SW_HEAVY))
        # Short wing back (right edge)
        parts.append(_rect(wing_x + wing_w, wing_y, bt_s, wing_h, SW_HEAVY, fill="#F0F0F0"))

    # Miter at corner
    _miter_callout(parts, ox + long_s - d_s + bt_s, oy + d_s)

    # Cushion numbers
    _cushion_label(parts, ox + (long_s - d_s) / 2, oy + (d_s - bt_s) / 2, 1)
    if wing_h > 0:
        _cushion_label(parts, wing_x + wing_w / 2, wing_y + wing_h / 2, 2)

    # Dimensions
    _dim_2d_h(parts, ox, ox + long_s, oy - 4, f'{long:.0f}"', -18)
    _dim_2d_v(parts, ox + long_s + bt_s + 4, oy, oy + d_s + wing_h, f'{short:.0f}"', 18)
    _dim_2d_v(parts, ox - 4, oy, oy + d_s, f'{depth:.0f}"', -18)


def _plan_u_shape(parts, ox, oy, scale, back, side, depth, side_depth, seat_h, back_h):
    """Draw plan view of U-shape bench."""
    bt = BACK_T
    d_s = depth * scale
    sd_s = side_depth * scale
    bt_s = bt * scale
    back_s = back * scale
    side_s = side * scale
    total_w = (back + side_depth * 2) * scale

    # Left wing seat
    parts.append(_rect(ox, oy, sd_s - bt_s, side_s, SW_HEAVY))
    # Left wing back
    parts.append(_rect(ox - bt_s, oy, bt_s, side_s, SW_HEAVY, fill="#F0F0F0"))

    # Center back seat
    cx = ox + sd_s
    cy = oy + side_s - d_s
    parts.append(_rect(cx, cy, back_s, d_s - bt_s, SW_HEAVY))
    # Center back panel
    parts.append(_rect(cx, cy + d_s - bt_s, back_s, bt_s, SW_HEAVY, fill="#F0F0F0"))

    # Right wing seat
    rx = ox + sd_s + back_s
    parts.append(_rect(rx + bt_s, oy, sd_s - bt_s, side_s, SW_HEAVY))
    # Right wing back
    parts.append(_rect(rx + sd_s, oy, bt_s, side_s, SW_HEAVY, fill="#F0F0F0"))

    # Miter callouts
    _miter_callout(parts, cx, cy + d_s - bt_s)
    _miter_callout(parts, rx, cy + d_s - bt_s)

    # Cushion numbers
    _cushion_label(parts, ox + (sd_s - bt_s) / 2, oy + side_s / 2, 1)
    _cushion_label(parts, cx + back_s / 2, cy + (d_s - bt_s) / 2, 2)
    _cushion_label(parts, rx + bt_s + (sd_s - bt_s) / 2, oy + side_s / 2, 3)

    # Dimensions
    _dim_2d_h(parts, ox, ox + total_w, oy + side_s + 4, f'{back + side_depth * 2:.0f}"', 18)
    _dim_2d_v(parts, ox - bt_s - 4, oy, oy + side_s, f'{side:.0f}"', -18)
    _dim_2d_h(parts, cx, cx + back_s, oy - 4, f'{back:.0f}"', -18)


# ── FRONT ELEVATION VIEW ─────────────────────────────────────────

def _elev_straight(parts, ox, oy, scale, width, depth, seat_h, back_h):
    """Front elevation — straight-on view showing seat + back heights."""
    w = width * scale
    sh = seat_h * scale
    bh = back_h * scale
    d_s = depth * scale * 0.3  # foreshortened depth indicator

    # Seat box
    parts.append(_rect(ox, oy - sh, w, sh, SW_HEAVY))
    # Back panel
    parts.append(_rect(ox, oy - sh - bh, w, bh, SW_MED))
    # Seat line
    parts.append(_line(ox, oy - sh, ox + w, oy - sh, SW_MED))

    # Channel lines on back
    num_ch = max(int(width / 12), 2)
    for i in range(1, num_ch):
        cx = ox + w * i / num_ch
        parts.append(_line(cx, oy - sh - bh + 2, cx, oy - sh - 2, SW_LIGHT, LIGHT_GRAY))

    # Dimensions
    _dim_2d_h(parts, ox, ox + w, oy, f'{width:.0f}"', 18)
    _dim_2d_v(parts, ox + w, oy, oy - sh, f'{seat_h:.0f}"', 20)
    _dim_2d_v(parts, ox + w + 30, oy - sh, oy - sh - bh, f'{back_h:.0f}"', 20)
    # Overall height
    _dim_2d_v(parts, ox - 4, oy, oy - sh - bh, f'{seat_h + back_h:.0f}"', -22)


def _elev_l_shape(parts, ox, oy, scale, long, short, depth, seat_h, back_h):
    """Front elevation for L-shape — shows long section straight-on."""
    _elev_straight(parts, ox, oy, scale, long, depth, seat_h, back_h)


def _elev_u_shape(parts, ox, oy, scale, back, side, depth, side_depth, seat_h, back_h):
    """Front elevation for U-shape — shows back section + side wing hints."""
    total_w = back + side_depth * 2
    _elev_straight(parts, ox, oy, scale, total_w, depth, seat_h, back_h)
    # Vertical lines showing wing boundaries
    sd_s = side_depth * scale
    w = total_w * scale
    parts.append(_line(ox + sd_s, oy, ox + sd_s, oy - (seat_h + back_h) * scale, SW_LIGHT, GRAY))
    parts.append(_line(ox + w - sd_s, oy, ox + w - sd_s, oy - (seat_h + back_h) * scale, SW_LIGHT, GRAY))


# ── ISOMETRIC BENCH BOX ──────────────────────────────────────────

def _draw_bench_box(parts, ox, oy, scale, sx, sy, width, depth, seat_h, back_h):
    """Draw one bench section in isometric: seat box + back panel + channels."""
    w, d, sh, bh = width, depth, seat_h, back_h
    bt = BACK_T

    # Seat box front face
    parts.append(_poly([
        _iso(sx, sy, 0, ox, oy, scale),
        _iso(sx + w, sy, 0, ox, oy, scale),
        _iso(sx + w, sy, sh, ox, oy, scale),
        _iso(sx, sy, sh, ox, oy, scale),
    ], SW_HEAVY))
    # Seat top face
    parts.append(_poly([
        _iso(sx, sy, sh, ox, oy, scale),
        _iso(sx + w, sy, sh, ox, oy, scale),
        _iso(sx + w, sy + d - bt, sh, ox, oy, scale),
        _iso(sx, sy + d - bt, sh, ox, oy, scale),
    ], SW_MED))
    # Seat right side
    parts.append(_poly([
        _iso(sx + w, sy, 0, ox, oy, scale),
        _iso(sx + w, sy + d - bt, 0, ox, oy, scale),
        _iso(sx + w, sy + d - bt, sh, ox, oy, scale),
        _iso(sx + w, sy, sh, ox, oy, scale),
    ], SW_MED))

    # Back panel front face
    parts.append(_poly([
        _iso(sx, sy + d - bt, sh, ox, oy, scale),
        _iso(sx + w, sy + d - bt, sh, ox, oy, scale),
        _iso(sx + w, sy + d - bt, sh + bh, ox, oy, scale),
        _iso(sx, sy + d - bt, sh + bh, ox, oy, scale),
    ], SW_HEAVY))
    # Back top face
    parts.append(_poly([
        _iso(sx, sy + d - bt, sh + bh, ox, oy, scale),
        _iso(sx + w, sy + d - bt, sh + bh, ox, oy, scale),
        _iso(sx + w, sy + d, sh + bh, ox, oy, scale),
        _iso(sx, sy + d, sh + bh, ox, oy, scale),
    ], SW_MED))
    # Back right side
    parts.append(_poly([
        _iso(sx + w, sy + d - bt, sh, ox, oy, scale),
        _iso(sx + w, sy + d, sh, ox, oy, scale),
        _iso(sx + w, sy + d, sh + bh, ox, oy, scale),
        _iso(sx + w, sy + d - bt, sh + bh, ox, oy, scale),
    ], SW_MED))

    # Seat/back separation line
    sl1 = _iso(sx, sy + d - bt, sh, ox, oy, scale)
    sl2 = _iso(sx + w, sy + d - bt, sh, ox, oy, scale)
    parts.append(_line(sl1[0], sl1[1], sl2[0], sl2[1], 1.0))

    # Channel lines on back face
    num_channels = max(int(w / 12), 2)
    for i in range(1, num_channels):
        cx = sx + w * i / num_channels
        p1 = _iso(cx, sy + d - bt, sh + 1, ox, oy, scale)
        p2 = _iso(cx, sy + d - bt, sh + bh - 1, ox, oy, scale)
        parts.append(_line(p1[0], p1[1], p2[0], p2[1], SW_CHAN))


# ── TITLE BLOCK ───────────────────────────────────────────────────

def _title_block(parts, x, y, w, h, name="", quote_num="", dims_text="",
                 bench_type="STRAIGHT", cushion_count=1):
    """Professional title block with Empire Workroom branding and scale bar."""
    # Outer border
    parts.append(_rect(x, y, w, h, SW_BORDER))
    # Inner border
    parts.append(_rect(x + 3, y + 3, w - 6, h - 6, 0.5))

    # Company name
    parts.append(_text(x + w / 2, y + 32, "EMPIRE WORKROOM", 22, weight="bold"))
    parts.append(_text(x + w / 2, y + 50, "CUSTOM UPHOLSTERY & FABRICATION", 9, fill=GRAY))

    # Divider line
    parts.append(_line(x + 20, y + 60, x + w - 20, y + 60, 0.5))

    # Drawing info rows
    row_y = y + 80
    row_h = 22
    col1_x = x + 20
    col2_x = x + w / 2

    info_rows = [
        ("ITEM:", name.upper() if name else "BENCH"),
        ("TYPE:", bench_type.upper().replace("_", " ")),
        ("DIMENSIONS:", dims_text if dims_text else "SEE VIEWS"),
    ]
    if quote_num:
        info_rows.append(("QUOTE:", quote_num))
    info_rows.append(("CUSHIONS:", str(cushion_count)))

    for label, value in info_rows:
        parts.append(_text(col1_x, row_y, label, 9, anchor="start", weight="bold"))
        parts.append(_text(col1_x + 90, row_y, value, 9, anchor="start"))
        row_y += row_h

    # Scale bar
    bar_y = y + h - 50
    bar_x = x + 30
    bar_w = w - 60
    parts.append(_text(x + w / 2, bar_y - 8, "SCALE REFERENCE", 8, weight="bold"))
    # 12" = 1 foot reference bar
    seg_count = 4
    seg_w = bar_w / seg_count
    for i in range(seg_count):
        fill = "#000" if i % 2 == 0 else "#FFF"
        parts.append(_rect(bar_x + i * seg_w, bar_y, seg_w, 8, 0.5, fill=fill))
    for i in range(seg_count + 1):
        parts.append(_text(bar_x + i * seg_w, bar_y + 20, f'{i * 12}"', 7))

    # Bottom line
    parts.append(_text(x + w / 2, y + h - 14, "5124 Frolich Ln, Hyattsville, MD 20781", 7, fill=GRAY))


# ── VIEW FRAME ────────────────────────────────────────────────────

def _view_frame(parts, x, y, w, h, label):
    """Draw a thin frame around a view zone with a label."""
    parts.append(_rect(x, y, w, h, 0.5, stroke=GRAY))
    parts.append(_text(x + w / 2, y + 14, label, 10, weight="bold"))


# ── BUILD FUNCTIONS (multi-view) ─────────────────────────────────

def _build_straight(name, width_in, depth_in, seat_h_in, back_h_in, quote_num="",
                    svg_w=500, svg_h=350):
    """Build straight bench parts (multi-view or standalone iso)."""
    total_h = seat_h_in + back_h_in
    scale, ox, oy = _auto_scale((width_in, depth_in, total_h), svg_w, svg_h)
    parts = []
    _draw_bench_box(parts, ox, oy, scale, 0, 0, width_in, depth_in, seat_h_in, back_h_in)

    _dim_iso_width(parts, ox, oy, scale, 0, width_in, -3, -6, f'{width_in:.0f}"', below=True)
    _dim_iso_height(parts, ox, oy, scale, width_in + 6, depth_in, seat_h_in, total_h, f'{back_h_in:.0f}"')
    _dim_iso_height(parts, ox, oy, scale, width_in + 20, -3, 0, seat_h_in, f'{seat_h_in:.0f}"')
    _dim_iso_depth(parts, ox, oy, scale, width_in + 4, 0, depth_in, -3, f'{depth_in:.0f}"')

    return parts, scale, ox, oy


def _build_l_shape(name, long_in, short_in, depth_in, seat_h_in, back_h_in, quote_num="",
                   svg_w=500, svg_h=350):
    """Build L-shape bench parts."""
    total_h = seat_h_in + back_h_in
    scale, ox, oy = _auto_scale((long_in, short_in, total_h), svg_w, svg_h)
    parts = []

    _draw_bench_box(parts, ox, oy, scale, 0, short_in - depth_in, long_in, depth_in, seat_h_in, back_h_in)
    _draw_bench_box(parts, ox, oy, scale, long_in - depth_in, 0, depth_in, short_in, seat_h_in, back_h_in)

    _dim_iso_width(parts, ox, oy, scale, 0, long_in, short_in - depth_in - 3, total_h + 6, f'{long_in:.0f}"', below=False)
    _dim_iso_depth(parts, ox, oy, scale, long_in + 4, 0, short_in, -3, f'{short_in:.0f}"')
    _dim_iso_depth(parts, ox, oy, scale, long_in + 20, short_in - depth_in, short_in, -3, f'{depth_in:.0f}"')
    _dim_iso_height(parts, ox, oy, scale, long_in + 6, -3, seat_h_in, total_h, f'{back_h_in:.0f}"')
    _dim_iso_height(parts, ox, oy, scale, long_in + 6, short_in - 3, 0, seat_h_in, f'{seat_h_in:.0f}"')

    return parts, scale, ox, oy


def _build_u_shape(name, back_in, side_in, depth_in, side_depth_in, seat_h_in, back_h_in,
                   quote_num="", svg_w=500, svg_h=350):
    """Build U-shape bench parts."""
    total_h = seat_h_in + back_h_in
    total_w = back_in + side_depth_in * 2
    scale, ox, oy = _auto_scale((total_w, side_in, total_h), svg_w, svg_h)
    parts = []

    _draw_bench_box(parts, ox, oy, scale, 0, 0, side_depth_in, side_in, seat_h_in, back_h_in)
    _draw_bench_box(parts, ox, oy, scale, side_depth_in, side_in - depth_in, back_in, depth_in, seat_h_in, back_h_in)
    _draw_bench_box(parts, ox, oy, scale, side_depth_in + back_in, 0, side_depth_in, side_in, seat_h_in, back_h_in)

    _dim_iso_width(parts, ox, oy, scale, side_depth_in, side_depth_in + back_in, side_in - depth_in - 3, total_h + 6, f'{back_in:.0f}"', below=False)
    _dim_iso_depth(parts, ox, oy, scale, -6, 0, side_in, -3, f'{side_in:.0f}"')
    _dim_iso_height(parts, ox, oy, scale, -6, -3, seat_h_in, total_h, f'{back_h_in:.0f}"', right=False)
    _dim_iso_height(parts, ox, oy, scale, total_w + 6, -3, 0, seat_h_in, f'{seat_h_in:.0f}"')
    _dim_iso_depth(parts, ox, oy, scale, total_w + 4, 0, side_in, -3, f'{side_in:.0f}"')
    _dim_iso_depth(parts, ox, oy, scale, side_depth_in - 6, side_in - depth_in, side_in, -3, f'{depth_in:.0f}"')
    _dim_iso_width(parts, ox, oy, scale, 0, side_depth_in, -3, -6, f'{side_depth_in:.0f}"', below=True)
    _dim_iso_width(parts, ox, oy, scale, side_depth_in + back_in, total_w, -3, -6, f'{side_depth_in:.0f}"', below=True)

    return parts, scale, ox, oy


# ── MULTI-VIEW COMPOSITION ───────────────────────────────────────

def _compose_multiview(name, bench_type, build_fn, plan_fn, elev_fn,
                       dims_text, cushion_count, quote_num="",
                       plan_args=(), elev_args=(), iso_args=()):
    """Compose a 4-quadrant multi-view drawing."""
    parts = [_defs()]
    parts.append(f'<rect width="{LAYOUT_W}" height="{LAYOUT_H}" fill="white"/>')

    # Double border
    parts.append(_rect(4, 4, LAYOUT_W - 8, LAYOUT_H - 8, SW_BORDER))
    parts.append(_rect(8, 8, LAYOUT_W - 16, LAYOUT_H - 16, 0.5))

    # ── PLAN VIEW (top-left) ──
    _view_frame(parts, PLAN_X, PLAN_Y, PLAN_W, PLAN_H, "PLAN VIEW")
    plan_group = []
    plan_fn(plan_group, *plan_args)
    parts.append(f'<g transform="translate({PLAN_X:.0f},{PLAN_Y + 20:.0f})">')
    parts.extend(plan_group)
    parts.append('</g>')

    # ── ISOMETRIC VIEW (top-right) ──
    _view_frame(parts, ISO_X, ISO_Y, ISO_W, ISO_H, "ISOMETRIC VIEW")
    iso_group = []
    bp, *_ = build_fn(*iso_args, svg_w=ISO_W - 20, svg_h=ISO_H - 30)
    iso_group.extend(bp)
    parts.append(f'<g transform="translate({ISO_X + 10:.0f},{ISO_Y + 20:.0f})">')
    parts.extend(iso_group)
    parts.append('</g>')

    # ── FRONT ELEVATION (bottom-left) ──
    _view_frame(parts, ELEV_X, ELEV_Y, ELEV_W, ELEV_H, "FRONT ELEVATION")
    elev_group = []
    elev_fn(elev_group, *elev_args)
    parts.append(f'<g transform="translate({ELEV_X:.0f},{ELEV_Y + 20:.0f})">')
    parts.extend(elev_group)
    parts.append('</g>')

    # ── TITLE BLOCK (bottom-right) ──
    _title_block(parts, TITLE_X, TITLE_Y, TITLE_W, TITLE_H,
                 name=name, quote_num=quote_num, dims_text=dims_text,
                 bench_type=bench_type, cushion_count=cushion_count)

    return _wrap_svg_raw(parts, LAYOUT_W, LAYOUT_H)


# ── PUBLIC RENDER FUNCTIONS ───────────────────────────────────────

def render_straight(name, width_in, depth_in=20, seat_h_in=18, back_h_in=18,
                    quote_num="", svg_w=600, svg_h=400, **kw):
    """Render a straight bench — multi-view professional drawing."""
    if width_in < 50 and 'rate' not in kw:
        width_in = width_in * 12

    dims_text = f'{width_in:.0f}" W x {depth_in:.0f}" D x {seat_h_in:.0f}" SH x {back_h_in:.0f}" BH'

    # Plan view args
    plan_scale, plan_ox, plan_oy = _auto_scale_2d(width_in, depth_in, PLAN_W - 20, PLAN_H - 40)
    plan_args = (plan_ox + 10, plan_oy + 10, plan_scale, width_in, depth_in, seat_h_in, back_h_in)

    # Elevation args
    elev_scale, elev_ox, elev_oy = _auto_scale_2d(width_in, seat_h_in + back_h_in, ELEV_W - 20, ELEV_H - 40)
    elev_ground_y = elev_oy + (seat_h_in + back_h_in) * elev_scale + 10
    elev_args = (elev_ox + 10, elev_ground_y, elev_scale, width_in, depth_in, seat_h_in, back_h_in)

    # Iso args
    iso_args = (name, width_in, depth_in, seat_h_in, back_h_in, quote_num)

    return _compose_multiview(
        name, "straight", _build_straight, _plan_straight, _elev_straight,
        dims_text, 1, quote_num,
        plan_args=plan_args, elev_args=elev_args, iso_args=iso_args,
    )


def render_l_shape(name, long_in, short_in=0, depth_in=20, seat_h_in=18, back_h_in=18,
                   quote_num="", svg_w=600, svg_h=400, **kw):
    """Render an L-shaped bench — multi-view professional drawing."""
    if long_in < 50:
        lf = long_in
        long_in = lf * 0.6 * 12
        if short_in == 0 or short_in < 10:
            short_in = lf * 0.4 * 12
    if short_in == 0:
        short_in = long_in * 0.5

    dims_text = f'{long_in:.0f}" L x {short_in:.0f}" S x {depth_in:.0f}" D x {seat_h_in:.0f}" SH x {back_h_in:.0f}" BH'

    # Plan view
    plan_scale, plan_ox, plan_oy = _auto_scale_2d(long_in, short_in, PLAN_W - 20, PLAN_H - 40)
    plan_args = (plan_ox + 10, plan_oy + 10, plan_scale, long_in, short_in, depth_in, seat_h_in, back_h_in)

    # Elevation (shows long section)
    elev_scale, elev_ox, elev_oy = _auto_scale_2d(long_in, seat_h_in + back_h_in, ELEV_W - 20, ELEV_H - 40)
    elev_ground_y = elev_oy + (seat_h_in + back_h_in) * elev_scale + 10
    elev_args = (elev_ox + 10, elev_ground_y, elev_scale, long_in, short_in, depth_in, seat_h_in, back_h_in)

    iso_args = (name, long_in, short_in, depth_in, seat_h_in, back_h_in, quote_num)

    return _compose_multiview(
        name, "l_shape", _build_l_shape, _plan_l_shape, _elev_l_shape,
        dims_text, 2, quote_num,
        plan_args=plan_args, elev_args=elev_args, iso_args=iso_args,
    )


def render_u_shape(name, back_in, side_in=0, depth_in=20, side_depth_in=0,
                   seat_h_in=18, back_h_in=18, multiplier=1,
                   quote_num="", svg_w=600, svg_h=400, **kw):
    """Render a U-shaped booth — multi-view professional drawing."""
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
    dims_text = (f'{back_in:.0f}" B x {side_in:.0f}" S x {depth_in:.0f}" D x '
                 f'{side_depth_in:.0f}" SD x {seat_h_in:.0f}" SH x {back_h_in:.0f}" BH')

    # Plan view
    plan_scale, plan_ox, plan_oy = _auto_scale_2d(total_w, side_in, PLAN_W - 20, PLAN_H - 40)
    plan_args = (plan_ox + 10, plan_oy + 10, plan_scale, back_in, side_in, depth_in, side_depth_in, seat_h_in, back_h_in)

    # Elevation
    elev_scale, elev_ox, elev_oy = _auto_scale_2d(total_w, seat_h_in + back_h_in, ELEV_W - 20, ELEV_H - 40)
    elev_ground_y = elev_oy + (seat_h_in + back_h_in) * elev_scale + 10
    elev_args = (elev_ox + 10, elev_ground_y, elev_scale, back_in, side_in, depth_in, side_depth_in, seat_h_in, back_h_in)

    iso_args = (name, back_in, side_in, depth_in, side_depth_in, seat_h_in, back_h_in, quote_num)

    return _compose_multiview(
        name, "u_shape", _build_u_shape, _plan_u_shape, _elev_u_shape,
        dims_text, 3, quote_num,
        plan_args=plan_args, elev_args=elev_args, iso_args=iso_args,
    )


# ── PROJECT SHEET ─────────────────────────────────────────────────

def render_project_sheet(benches, title="BUILT-IN BENCHES", quote_num="",
                         svg_w=1100, svg_h=850):
    """Render a 2x2 grid of benches with title block at bottom right."""
    parts = [_defs()]
    parts.append(f'<rect width="{svg_w}" height="{svg_h}" fill="white"/>')

    # Double border
    parts.append(_rect(8, 8, svg_w - 16, svg_h - 16, SW_BORDER))
    parts.append(_rect(14, 14, svg_w - 28, svg_h - 28, 0.5))

    # Title block at bottom right
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

        if b_type == "l_shape":
            bp, *_ = _build_l_shape(
                b_name,
                bench.get("long_in", bench.get("width_in", 120)),
                bench.get("short_in", 60),
                bench.get("depth_in", 20),
                bench.get("seat_h_in", 18),
                bench.get("back_h_in", 18),
                svg_w=draw_w, svg_h=draw_h,
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
            )
        else:
            bp, *_ = _build_straight(
                b_name,
                bench.get("width_in", 120),
                bench.get("depth_in", 20),
                bench.get("seat_h_in", 18),
                bench.get("back_h_in", 18),
                svg_w=draw_w, svg_h=draw_h,
            )

        qty_str = f" ({qty}X)" if qty > 1 else ""
        parts.append(f'<g transform="translate({cx:.0f},{cy:.0f})">')
        parts.append(_text(draw_w / 2, 12, f"{b_name.upper()}{qty_str}", 11, weight="bold"))
        parts.extend(bp)
        parts.append('</g>')

    return _wrap_svg_raw(parts, svg_w, svg_h)


# ── SVG WRAPPERS ──────────────────────────────────────────────────

def _wrap_svg(parts, svg_w, svg_h, name="", quote_num=""):
    all_parts = [_defs()]
    all_parts.append(f'<rect width="{svg_w}" height="{svg_h}" fill="white"/>')
    all_parts.append(_rect(4, 4, svg_w - 8, svg_h - 8, 1))
    if name:
        label = name.upper()
        if quote_num:
            label += f"  \u2014  {quote_num}"
        all_parts.append(_text(svg_w / 2, 20, label, 12, weight="bold"))
    all_parts.extend(parts)
    all_parts.append(_text(svg_w - 12, svg_h - 8, "Empire Workroom", 7, anchor="end"))
    return _wrap_svg_raw(all_parts, svg_w, svg_h)


def _wrap_svg_raw(parts, svg_w, svg_h):
    body = "\n  ".join(parts)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}" '
        f'width="{svg_w}" height="{svg_h}">\n  {body}\n</svg>'
    )


# ── BATCH RENDERING ───────────────────────────────────────────────

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
