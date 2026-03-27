"""
Architectural bench renderer — clean black-on-white isometric line drawings
with proper dimension callouts, channel lines, and accurate proportions.

Matches professional architectural drawing standards:
- No fills, gradients, or colors — black lines on white only
- Isometric 3D projection with accurate proportions
- Dimension callouts with extension lines and arrowheads
- Vertical channel lines on seat backs
"""
import math
import os

# ── CONSTANTS ──────────────────────────────────────────────────────
ISO_A = 30
COS_A = math.cos(math.radians(ISO_A))
SIN_A = math.sin(math.radians(ISO_A))

SW_THIN = 0.5       # channel lines, details
SW_MED = 1.5        # outlines
SW_DIM = 0.75       # dimension lines + extension lines
SW_BORDER = 2.0     # outer border

FONT = "Arial, Helvetica, sans-serif"
BLACK = "#000000"
BACK_T = 4          # back cushion thickness (visual constant)

# ── ISOMETRIC PROJECTION ──────────────────────────────────────────

def _iso(x, y, z, ox, oy, s):
    """3D (x=width, y=depth, z=height) → 2D isometric."""
    return (
        ox + (x * COS_A - y * COS_A) * s,
        oy - (x * SIN_A + y * SIN_A) * s - z * s,
    )


def _auto_scale(dims_3d, svg_w, svg_h, margin=80):
    """Compute scale and origin to fit a 3D bounding box centered in SVG.

    dims_3d: (max_x, max_y, max_z) in inches.
    Returns (scale, ox, oy).
    """
    mx, my, mz = dims_3d
    # Project all 8 corners of bounding box at scale=1, origin=(0,0)
    corners = []
    for x in [0, mx]:
        for y in [0, my]:
            for z in [0, mz]:
                corners.append(_iso(x, y, z, 0, 0, 1))

    xs = [c[0] for c in corners]
    ys = [c[1] for c in corners]
    raw_w = max(xs) - min(xs)
    raw_h = max(ys) - min(ys)

    if raw_w == 0 or raw_h == 0:
        return 1.0, svg_w / 2, svg_h / 2

    usable_w = svg_w - margin * 2
    usable_h = svg_h - margin * 2 - 30  # leave room for title

    scale = min(usable_w / raw_w, usable_h / raw_h)

    # Reproject at computed scale to find centering offset
    corners2 = []
    for x in [0, mx]:
        for y in [0, my]:
            for z in [0, mz]:
                corners2.append(_iso(x, y, z, 0, 0, scale))

    xs2 = [c[0] for c in corners2]
    ys2 = [c[1] for c in corners2]

    cx = (max(xs2) + min(xs2)) / 2
    cy = (max(ys2) + min(ys2)) / 2

    target_cx = svg_w / 2
    target_cy = svg_h / 2 + 10  # slight shift down for title

    ox = target_cx - cx
    oy = target_cy - cy

    return scale, ox, oy


# ── SVG PRIMITIVES ────────────────────────────────────────────────

def _poly(pts, sw=SW_MED):
    """Polygon outline, no fill."""
    points = " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in pts)
    return f'<polygon points="{points}" fill="none" stroke="{BLACK}" stroke-width="{sw}" stroke-linejoin="round"/>'


def _line(x1, y1, x2, y2, sw=SW_MED):
    """Simple black line."""
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{BLACK}" stroke-width="{sw}"/>'


def _text(x, y, txt, size=10, anchor="middle", weight="normal", rotate=0):
    rot = f' transform="rotate({rotate},{x:.1f},{y:.1f})"' if rotate else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        f'font-family="{FONT}" font-size="{size}" fill="{BLACK}" '
        f'font-weight="{weight}"{rot}>{txt}</text>'
    )


def _defs():
    """SVG defs with arrowhead marker."""
    return '''<defs>
  <marker id="dim-arrow" viewBox="0 0 10 6" refX="10" refY="3"
          markerWidth="8" markerHeight="6" orient="auto-start-reverse">
    <path d="M0,0 L10,3 L0,6 Z" fill="#000"/>
  </marker>
</defs>'''


# ── DIMENSION CALLOUTS ────────────────────────────────────────────

def _dim_line(parts, p1, p2, label, offset_x=0, offset_y=0, ext_len=6):
    """Architectural dimension with extension lines and arrows.

    p1, p2: 2D screen points of the object corners being dimensioned.
    offset_x, offset_y: direction to offset the dimension line from the object.
    ext_len: how far extension lines extend past the dimension line.
    """
    # Offset positions for dimension line endpoints
    d1 = (p1[0] + offset_x, p1[1] + offset_y)
    d2 = (p2[0] + offset_x, p2[1] + offset_y)

    # Normalize offset direction for extension beyond dim line
    dist = math.hypot(offset_x, offset_y)
    if dist > 0:
        nx, ny = offset_x / dist, offset_y / dist
    else:
        nx, ny = 0, -1

    # Extension lines from object to beyond dimension line
    e1_start = (p1[0] + nx * 3, p1[1] + ny * 3)
    e1_end = (d1[0] + nx * ext_len, d1[1] + ny * ext_len)
    e2_start = (p2[0] + nx * 3, p2[1] + ny * 3)
    e2_end = (d2[0] + nx * ext_len, d2[1] + ny * ext_len)

    parts.append(_line(e1_start[0], e1_start[1], e1_end[0], e1_end[1], SW_DIM))
    parts.append(_line(e2_start[0], e2_start[1], e2_end[0], e2_end[1], SW_DIM))

    # Dimension line with arrows
    parts.append(
        f'<line x1="{d1[0]:.1f}" y1="{d1[1]:.1f}" x2="{d2[0]:.1f}" y2="{d2[1]:.1f}" '
        f'stroke="{BLACK}" stroke-width="{SW_DIM}" '
        f'marker-start="url(#dim-arrow)" marker-end="url(#dim-arrow)"/>'
    )

    # Label
    mx = (d1[0] + d2[0]) / 2
    my = (d1[1] + d2[1]) / 2
    angle = math.degrees(math.atan2(d2[1] - d1[1], d2[0] - d1[0]))
    # Keep text readable (not upside down)
    if angle > 90:
        angle -= 180
    elif angle < -90:
        angle += 180

    # Offset text slightly from the line
    text_off = 10
    perp_x = -math.sin(math.radians(angle)) * text_off
    perp_y = math.cos(math.radians(angle)) * text_off

    parts.append(_text(mx + perp_x, my + perp_y, label, 10, weight="600", rotate=angle))


def _dim_width(parts, ox, oy, scale, x1, x2, y, z, label, below=True):
    """Horizontal width dimension along front edge (iso X axis)."""
    p1 = _iso(x1, y, z, ox, oy, scale)
    p2 = _iso(x2, y, z, ox, oy, scale)
    off = 25 if below else -25
    _dim_line(parts, p1, p2, label, offset_x=0, offset_y=off)


def _dim_depth(parts, ox, oy, scale, x, y1, y2, z, label, right=True):
    """Depth dimension along side edge (iso Y axis)."""
    p1 = _iso(x, y1, z, ox, oy, scale)
    p2 = _iso(x, y2, z, ox, oy, scale)
    off = 25 if right else -25
    _dim_line(parts, p1, p2, label, offset_x=off, offset_y=0)


def _dim_height(parts, ox, oy, scale, x, y, z1, z2, label, right_side=True):
    """Vertical height dimension."""
    p1 = _iso(x, y, z1, ox, oy, scale)
    p2 = _iso(x, y, z2, ox, oy, scale)
    off_x = 20 if right_side else -20
    _dim_line(parts, p1, p2, label, offset_x=off_x, offset_y=0)


# ── BENCH BOX DRAWING ────────────────────────────────────────────

def _draw_bench_box(parts, ox, oy, scale, sx, sy, width, depth, seat_h, back_h):
    """Draw one bench section as wireframe isometric with channel lines.

    Coordinate system: sx,sy = starting corner (front-left at ground).
    width = along X, depth = along Y, heights along Z.
    """
    w, d, sh, bh = width, depth, seat_h, back_h
    bt = BACK_T  # back thickness

    # ── SEAT BOX (base to seat height) ──
    # Front face
    parts.append(_poly([
        _iso(sx, sy, 0, ox, oy, scale),
        _iso(sx + w, sy, 0, ox, oy, scale),
        _iso(sx + w, sy, sh, ox, oy, scale),
        _iso(sx, sy, sh, ox, oy, scale),
    ], SW_MED))
    # Top face
    parts.append(_poly([
        _iso(sx, sy, sh, ox, oy, scale),
        _iso(sx + w, sy, sh, ox, oy, scale),
        _iso(sx + w, sy + d - bt, sh, ox, oy, scale),
        _iso(sx, sy + d - bt, sh, ox, oy, scale),
    ], SW_MED))
    # Right side face
    parts.append(_poly([
        _iso(sx + w, sy, 0, ox, oy, scale),
        _iso(sx + w, sy + d - bt, 0, ox, oy, scale),
        _iso(sx + w, sy + d - bt, sh, ox, oy, scale),
        _iso(sx + w, sy, sh, ox, oy, scale),
    ], SW_MED))

    # ── BACK PANEL (seat_h to seat_h + back_h) ──
    # Front face of back
    parts.append(_poly([
        _iso(sx, sy + d - bt, sh, ox, oy, scale),
        _iso(sx + w, sy + d - bt, sh, ox, oy, scale),
        _iso(sx + w, sy + d - bt, sh + bh, ox, oy, scale),
        _iso(sx, sy + d - bt, sh + bh, ox, oy, scale),
    ], SW_MED))
    # Top face of back
    parts.append(_poly([
        _iso(sx, sy + d - bt, sh + bh, ox, oy, scale),
        _iso(sx + w, sy + d - bt, sh + bh, ox, oy, scale),
        _iso(sx + w, sy + d, sh + bh, ox, oy, scale),
        _iso(sx, sy + d, sh + bh, ox, oy, scale),
    ], SW_MED))
    # Right side of back
    parts.append(_poly([
        _iso(sx + w, sy + d - bt, sh, ox, oy, scale),
        _iso(sx + w, sy + d, sh, ox, oy, scale),
        _iso(sx + w, sy + d, sh + bh, ox, oy, scale),
        _iso(sx + w, sy + d - bt, sh + bh, ox, oy, scale),
    ], SW_MED))
    # Back face (rear — partially visible at top in iso view)
    parts.append(_poly([
        _iso(sx, sy + d, sh, ox, oy, scale),
        _iso(sx + w, sy + d, sh, ox, oy, scale),
        _iso(sx + w, sy + d, sh + bh, ox, oy, scale),
        _iso(sx, sy + d, sh + bh, ox, oy, scale),
    ], SW_THIN))

    # ── CHANNEL LINES on back front face ──
    num_channels = max(int(w / 6), 3)
    for i in range(1, num_channels):
        cx = sx + w * i / num_channels
        p1 = _iso(cx, sy + d - bt, sh, ox, oy, scale)
        p2 = _iso(cx, sy + d - bt, sh + bh, ox, oy, scale)
        parts.append(_line(p1[0], p1[1], p2[0], p2[1], SW_THIN))


def _build_straight(name, width_in, depth_in, seat_h_in, back_h_in, quote_num="",
                    svg_w=600, svg_h=400):
    """Build straight bench SVG parts. Returns (parts, bbox_3d)."""
    total_h = seat_h_in + back_h_in
    scale, ox, oy = _auto_scale((width_in, depth_in, total_h), svg_w, svg_h)

    parts = []
    _draw_bench_box(parts, ox, oy, scale, 0, 0, width_in, depth_in, seat_h_in, back_h_in)

    # Dimensions
    # Width along bottom front
    _dim_width(parts, ox, oy, scale, 0, width_in, -2, -4, f'{width_in:.0f}"', below=True)
    # Back height — right side
    _dim_height(parts, ox, oy, scale, width_in + 4, depth_in - BACK_T, seat_h_in, total_h, f'{back_h_in:.0f}"')
    # Seat height — right side
    _dim_height(parts, ox, oy, scale, width_in + 4, -2, 0, seat_h_in, f'{seat_h_in:.0f}"')
    # Depth — bottom right
    _dim_depth(parts, ox, oy, scale, width_in + 2, 0, depth_in, 0, f'{depth_in:.0f}"')

    return parts, scale, ox, oy


def _build_l_shape(name, long_in, short_in, depth_in, seat_h_in, back_h_in, quote_num="",
                   svg_w=600, svg_h=400):
    """Build L-shape bench SVG parts."""
    total_h = seat_h_in + back_h_in
    # L-shape bounding box: long_in wide, short_in deep (the wing extends in Y)
    scale, ox, oy = _auto_scale((long_in, short_in, total_h), svg_w, svg_h)

    parts = []
    # Long section along X axis (back along far Y edge)
    _draw_bench_box(parts, ox, oy, scale, 0, short_in - depth_in, long_in, depth_in, seat_h_in, back_h_in)
    # Short wing along Y axis (back on right X edge, runs from y=0 to y=short_in)
    _draw_bench_box(parts, ox, oy, scale, long_in - depth_in, 0, depth_in, short_in, seat_h_in, back_h_in)

    # Dimensions
    # Long side width along top
    _dim_width(parts, ox, oy, scale, 0, long_in, short_in - depth_in - 2, total_h + 4, f'{long_in:.0f}"', below=False)
    # Short wing depth along bottom
    _dim_depth(parts, ox, oy, scale, long_in + 2, 0, short_in, 0, f'{short_in:.0f}"')
    # Depth
    _dim_depth(parts, ox, oy, scale, long_in + 16, short_in - depth_in, short_in, 0, f'{depth_in:.0f}"')
    # Back height on right
    _dim_height(parts, ox, oy, scale, long_in + 4, -2, seat_h_in, total_h, f'{back_h_in:.0f}"')
    # Seat height
    _dim_height(parts, ox, oy, scale, long_in + 4, short_in - 2, 0, seat_h_in, f'{seat_h_in:.0f}"')

    return parts, scale, ox, oy


def _build_u_shape(name, back_in, side_in, depth_in, side_depth_in, seat_h_in, back_h_in,
                   quote_num="", svg_w=600, svg_h=400):
    """Build U-shape bench SVG parts."""
    total_h = seat_h_in + back_h_in
    total_w = back_in + side_depth_in * 2

    scale, ox, oy = _auto_scale((total_w, side_in, total_h), svg_w, svg_h)

    parts = []
    # Left wing (runs along Y)
    _draw_bench_box(parts, ox, oy, scale, 0, 0, side_depth_in, side_in, seat_h_in, back_h_in)
    # Center back (runs along X, at far Y edge)
    _draw_bench_box(parts, ox, oy, scale, side_depth_in, side_in - depth_in, back_in, depth_in, seat_h_in, back_h_in)
    # Right wing (runs along Y)
    _draw_bench_box(parts, ox, oy, scale, side_depth_in + back_in, 0, side_depth_in, side_in, seat_h_in, back_h_in)

    # Dimensions
    # Total width along top
    _dim_width(parts, ox, oy, scale, 0, total_w, -2, total_h + 4, f'{back_in:.0f}"', below=False)
    # Left side depth
    _dim_depth(parts, ox, oy, scale, -4, 0, side_in, 0, f'{side_in:.0f}"', right=False)
    # Back height — left side
    _dim_height(parts, ox, oy, scale, -4, -2, seat_h_in, total_h, f'{back_h_in:.0f}"', right_side=False)
    # Seat height — right side
    _dim_height(parts, ox, oy, scale, total_w + 4, -2, 0, seat_h_in, f'{seat_h_in:.0f}"')
    # Right wing depth
    _dim_depth(parts, ox, oy, scale, total_w + 2, 0, side_in, 0, f'{side_in:.0f}"')
    # Seat depth — bottom
    _dim_depth(parts, ox, oy, scale, side_depth_in - 2, side_in - depth_in, side_in, 0, f'{depth_in:.0f}"', right=False)
    # Side depth — bottom
    _dim_width(parts, ox, oy, scale, 0, side_depth_in, -2, -4, f'{side_depth_in:.0f}"', below=True)
    # Right side depth
    _dim_width(parts, ox, oy, scale, side_depth_in + back_in, total_w, -2, -4, f'{side_depth_in:.0f}"', below=True)

    return parts, scale, ox, oy


# ── PUBLIC RENDER FUNCTIONS (inch-based) ──────────────────────────

def render_straight(name, width_in, depth_in=20, seat_h_in=18, back_h_in=18,
                    quote_num="", svg_w=600, svg_h=400, **kw):
    """Render a straight bench. All dimensions in inches."""
    # Legacy detection: if width_in looks like LF (small number + rate arg)
    if width_in < 50 and 'rate' not in kw:
        width_in = width_in * 12  # was probably LF

    build_parts, *_ = _build_straight(name, width_in, depth_in, seat_h_in, back_h_in,
                                      quote_num, svg_w, svg_h)
    return _wrap_svg(build_parts, svg_w, svg_h, name, quote_num)


def render_l_shape(name, long_in, short_in=0, depth_in=20, seat_h_in=18, back_h_in=18,
                   quote_num="", svg_w=600, svg_h=400, **kw):
    """Render an L-shaped bench. All dimensions in inches."""
    if long_in < 50:
        lf = long_in
        long_in = lf * 0.6 * 12
        if short_in == 0 or short_in < 10:
            short_in = lf * 0.4 * 12
    if short_in == 0:
        short_in = long_in * 0.5

    build_parts, *_ = _build_l_shape(name, long_in, short_in, depth_in, seat_h_in, back_h_in,
                                     quote_num, svg_w, svg_h)
    return _wrap_svg(build_parts, svg_w, svg_h, name, quote_num)


def render_u_shape(name, back_in, side_in=0, depth_in=20, side_depth_in=0,
                   seat_h_in=18, back_h_in=18, multiplier=1,
                   quote_num="", svg_w=600, svg_h=400, **kw):
    """Render a U-shaped booth. All dimensions in inches."""
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

    build_parts, *_ = _build_u_shape(name, back_in, side_in, depth_in, side_depth_in,
                                     seat_h_in, back_h_in, quote_num, svg_w, svg_h)
    return _wrap_svg(build_parts, svg_w, svg_h, name, quote_num)


# ── PROJECT SHEET (multi-bench on one page) ───────────────────────

def render_project_sheet(benches, title="BUILT-IN BENCHES", quote_num="",
                         svg_w=1100, svg_h=850):
    """Render a 2×2 grid of benches on one page with title block.

    benches: list of dicts with keys:
        name, type (straight/l_shape/u_shape), qty,
        width_in, depth_in, seat_h_in, back_h_in,
        long_in, short_in (for l_shape),
        back_in, side_in, side_depth_in (for u_shape)
    """
    parts = [_defs()]
    parts.append(f'<rect width="{svg_w}" height="{svg_h}" fill="white"/>')

    # Outer border (double line like architectural drawings)
    parts.append(f'<rect x="8" y="8" width="{svg_w-16}" height="{svg_h-16}" fill="none" stroke="{BLACK}" stroke-width="{SW_BORDER}"/>')
    parts.append(f'<rect x="14" y="14" width="{svg_w-28}" height="{svg_h-28}" fill="none" stroke="{BLACK}" stroke-width="0.5"/>')

    # Title block at bottom right
    tb_w = 280
    tb_h = 50
    tb_x = svg_w - 14 - tb_w
    tb_y = svg_h - 14 - tb_h
    parts.append(f'<rect x="{tb_x}" y="{tb_y}" width="{tb_w}" height="{tb_h}" fill="none" stroke="{BLACK}" stroke-width="{SW_MED}"/>')
    parts.append(_text(tb_x + tb_w / 2, tb_y + 30, title, 18, weight="bold"))
    if quote_num:
        parts.append(_text(tb_x + tb_w / 2, tb_y + 44, quote_num, 10))

    # Grid layout
    cols = 2
    rows = 2 if len(benches) > 2 else 1

    # Usable area (inside border, above title block)
    pad = 24
    area_x = 14 + pad
    area_y = 14 + pad
    area_w = svg_w - 28 - pad * 2
    area_h = tb_y - 14 - pad * 2

    cell_w = area_w / cols
    cell_h = area_h / rows

    for idx, bench in enumerate(benches[:4]):
        col = idx % cols
        row = idx // cols

        cx = area_x + col * cell_w
        cy = area_y + row * cell_h

        # Cell dimensions for the individual bench SVG
        cw = cell_w - 10
        ch = cell_h - 30  # leave room for label

        b_type = bench.get("type", "straight")
        b_name = bench.get("name", "Bench")
        qty = bench.get("qty", 1)

        # Build bench parts into this cell
        cell_parts = []
        if b_type == "l_shape":
            bp, sc, bx, by = _build_l_shape(
                b_name,
                bench.get("long_in", bench.get("width_in", 120)),
                bench.get("short_in", 60),
                bench.get("depth_in", 20),
                bench.get("seat_h_in", 18),
                bench.get("back_h_in", 18),
                svg_w=cw, svg_h=ch,
            )
        elif b_type == "u_shape":
            bp, sc, bx, by = _build_u_shape(
                b_name,
                bench.get("back_in", bench.get("width_in", 84)),
                bench.get("side_in", 60),
                bench.get("depth_in", 20),
                bench.get("side_depth_in", bench.get("depth_in", 20)),
                bench.get("seat_h_in", 18),
                bench.get("back_h_in", 18),
                svg_w=cw, svg_h=ch,
            )
        else:
            bp, sc, bx, by = _build_straight(
                b_name,
                bench.get("width_in", 120),
                bench.get("depth_in", 20),
                bench.get("seat_h_in", 18),
                bench.get("back_h_in", 18),
                svg_w=cw, svg_h=ch,
            )

        # Wrap in a group translated to cell position
        group_parts = "\n    ".join(bp)
        parts.append(f'<g transform="translate({cx:.0f},{cy:.0f})">')
        # Cell label
        qty_str = f" ({qty}X)" if qty > 1 else ""
        parts.append(_text(cw / 2, 14, f"{b_name.upper()}{qty_str}", 11, weight="bold"))
        # Bench drawing
        parts.extend(bp)
        # Cell separator lines
        if col == 0 and cols > 1:
            parts.append(_line(cw + 5, 0, cw + 5, cell_h, 0.3))
        if row == 0 and rows > 1 and idx < 2:
            parts.append(_line(0, cell_h, cell_w * 2, cell_h, 0.3))
        parts.append('</g>')

    return _wrap_svg_raw(parts, svg_w, svg_h)


# ── SVG WRAPPERS ──────────────────────────────────────────────────

def _wrap_svg(parts, svg_w, svg_h, name="", quote_num=""):
    """Wrap bench parts in a complete SVG with defs, border, and label."""
    all_parts = [_defs()]
    all_parts.append(f'<rect width="{svg_w}" height="{svg_h}" fill="white"/>')
    # Light border
    all_parts.append(f'<rect x="4" y="4" width="{svg_w-8}" height="{svg_h-8}" fill="none" stroke="{BLACK}" stroke-width="1"/>')

    # Title
    if name:
        label = name.upper()
        if quote_num:
            label += f"  —  {quote_num}"
        all_parts.append(_text(svg_w / 2, 22, label, 12, weight="bold"))

    all_parts.extend(parts)

    # Footer
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
    """Generate drawings for all areas in a quote. Returns [{name, svg, lf}, ...]."""
    results = []
    for item in line_items:
        desc = item.get("description", "")
        lf = item.get("quantity", 0)
        if lf <= 0:
            continue
        name = desc.split("—")[0].strip() if "—" in desc else desc
        desc_lower = desc.lower()
        if "u-shape" in desc_lower or "u shape" in desc_lower:
            mult = 2 if "×2" in desc or "x2" in desc_lower else 1
            svg = render_u_shape(name, lf, multiplier=mult, quote_num=quote_num)
        elif "l-shape" in desc_lower or "l shape" in desc_lower:
            svg = render_l_shape(name, lf, quote_num=quote_num)
        else:
            svg = render_straight(name, lf, quote_num=quote_num)
        results.append({"name": name, "svg": svg, "lf": lf})
    return results


def drawings_to_pdf(drawings, output_path):
    """Convert list of drawing dicts to a multi-page PDF. Returns path."""
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
