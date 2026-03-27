"""
Architectural bench renderer — clean black-on-white isometric line drawings
with proper dimension callouts, channel lines, and accurate proportions.

Style matches professional architectural shop drawings:
- Black lines on white, no fills/gradients
- ALL text reads left-to-right or bottom-to-top — never angled
- Proper dimension lines with extension lines and arrowheads
- Subtle channel lines on seat backs
- Accurate proportions
"""
import math
import os

# ── CONSTANTS ──────────────────────────────────────────────────────
ISO_A = 30
COS_A = math.cos(math.radians(ISO_A))
SIN_A = math.sin(math.radians(ISO_A))

SW_CHAN = 0.3        # channel lines (very subtle)
SW_MED = 1.5         # outlines
SW_DIM = 0.75        # dimension + extension lines
SW_BORDER = 2.0      # outer border

FONT = "Arial, Helvetica, sans-serif"
BLACK = "#000000"
BACK_T = 4           # back cushion thickness (visual constant, inches)


# ── ISOMETRIC PROJECTION ──────────────────────────────────────────

def _iso(x, y, z, ox, oy, s):
    """3D (x=width, y=depth, z=height) → 2D isometric screen coords."""
    return (
        ox + (x * COS_A - y * COS_A) * s,
        oy - (x * SIN_A + y * SIN_A) * s - z * s,
    )


def _auto_scale(dims_3d, svg_w, svg_h, margin=30):
    """Compute scale and origin to fit a 3D bbox centered in SVG.

    Returns (scale, ox, oy). Uses small margins to fill ~75% of space.
    """
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


# ── SVG PRIMITIVES ────────────────────────────────────────────────

def _poly(pts, sw=SW_MED):
    """Polygon outline, no fill."""
    points = " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in pts)
    return f'<polygon points="{points}" fill="none" stroke="{BLACK}" stroke-width="{sw}" stroke-linejoin="round"/>'


def _line(x1, y1, x2, y2, sw=SW_MED):
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{BLACK}" stroke-width="{sw}"/>'


def _text(x, y, txt, size=10, anchor="middle", weight="normal", rotate=0):
    rot = f' transform="rotate({rotate},{x:.1f},{y:.1f})"' if rotate else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        f'font-family="{FONT}" font-size="{size}" fill="{BLACK}" '
        f'font-weight="{weight}"{rot}>{txt}</text>'
    )


def _defs():
    return '''<defs>
  <marker id="dim-arrow" viewBox="0 0 10 6" refX="10" refY="3"
          markerWidth="8" markerHeight="6" orient="auto-start-reverse">
    <path d="M0,0 L10,3 L0,6 Z" fill="#000"/>
  </marker>
</defs>'''


# ── DIMENSION CALLOUTS ────────────────────────────────────────────
# ALL dimension text is horizontal or vertical (bottom-to-top).
# No angled text ever.

def _dim_h(parts, p1, p2, label, offset_y, text_side="above"):
    """Horizontal-ish dimension line between two 2D points.

    Draws extension lines from p1 and p2 going vertically by offset_y,
    then a horizontal dimension line between them with arrows.
    Text is always horizontal, placed above or below the line.
    """
    # Extension line endpoints (vertical from object to dim line level)
    gap = 3  # gap between object and start of extension line
    ext_extra = 5  # extension past dim line
    dy = offset_y
    sign = 1 if dy > 0 else -1

    e1_start = (p1[0], p1[1] + gap * sign)
    e1_end = (p1[0], p1[1] + dy + ext_extra * sign)
    e2_start = (p2[0], p2[1] + gap * sign)
    e2_end = (p2[0], p2[1] + dy + ext_extra * sign)

    parts.append(_line(e1_start[0], e1_start[1], e1_end[0], e1_end[1], SW_DIM))
    parts.append(_line(e2_start[0], e2_start[1], e2_end[0], e2_end[1], SW_DIM))

    # Dimension line at offset
    d1 = (p1[0], p1[1] + dy)
    d2 = (p2[0], p2[1] + dy)
    parts.append(
        f'<line x1="{d1[0]:.1f}" y1="{d1[1]:.1f}" x2="{d2[0]:.1f}" y2="{d2[1]:.1f}" '
        f'stroke="{BLACK}" stroke-width="{SW_DIM}" '
        f'marker-start="url(#dim-arrow)" marker-end="url(#dim-arrow)"/>'
    )

    # Text — always horizontal, centered on dim line
    mx = (d1[0] + d2[0]) / 2
    my = (d1[1] + d2[1]) / 2
    text_y = my - 4 if text_side == "above" else my + 12
    parts.append(_text(mx, text_y, label, 9, weight="600"))


def _dim_v(parts, p1, p2, label, offset_x, text_side="right"):
    """Vertical dimension line between two 2D points.

    Extension lines go horizontally by offset_x, dim line is vertical.
    Text reads bottom-to-top (rotated -90), placed to left or right.
    """
    gap = 3
    ext_extra = 5
    sign = 1 if offset_x > 0 else -1

    e1_start = (p1[0] + gap * sign, p1[1])
    e1_end = (p1[0] + offset_x + ext_extra * sign, p1[1])
    e2_start = (p2[0] + gap * sign, p2[1])
    e2_end = (p2[0] + offset_x + ext_extra * sign, p2[1])

    parts.append(_line(e1_start[0], e1_start[1], e1_end[0], e1_end[1], SW_DIM))
    parts.append(_line(e2_start[0], e2_start[1], e2_end[0], e2_end[1], SW_DIM))

    d1 = (p1[0] + offset_x, p1[1])
    d2 = (p2[0] + offset_x, p2[1])
    parts.append(
        f'<line x1="{d1[0]:.1f}" y1="{d1[1]:.1f}" x2="{d2[0]:.1f}" y2="{d2[1]:.1f}" '
        f'stroke="{BLACK}" stroke-width="{SW_DIM}" '
        f'marker-start="url(#dim-arrow)" marker-end="url(#dim-arrow)"/>'
    )

    mx = (d1[0] + d2[0]) / 2
    my = (d1[1] + d2[1]) / 2
    # Text reads bottom-to-top (rotate -90)
    tx = mx + (8 if text_side == "right" else -8)
    parts.append(_text(tx, my + 3, label, 9, weight="600", rotate=-90))


def _dim_iso_width(parts, ox, oy, scale, x1, x2, y, z, label, below=True):
    """Width dimension along isometric X axis. Text always horizontal."""
    p1 = _iso(x1, y, z, ox, oy, scale)
    p2 = _iso(x2, y, z, ox, oy, scale)
    off = 22 if below else -22
    _dim_h(parts, p1, p2, label, off, "below" if below else "above")


def _dim_iso_depth(parts, ox, oy, scale, x, y1, y2, z, label, below=True):
    """Depth dimension along isometric Y axis. Text always horizontal."""
    p1 = _iso(x, y1, z, ox, oy, scale)
    p2 = _iso(x, y2, z, ox, oy, scale)
    off = 22 if below else -22
    _dim_h(parts, p1, p2, label, off, "below" if below else "above")


def _dim_iso_height(parts, ox, oy, scale, x, y, z1, z2, label, right=True):
    """Height dimension (vertical in iso). Text reads bottom-to-top."""
    p1 = _iso(x, y, z1, ox, oy, scale)
    p2 = _iso(x, y, z2, ox, oy, scale)
    off = 18 if right else -18
    _dim_v(parts, p1, p2, label, off, "right" if right else "left")


# ── BENCH BOX DRAWING ────────────────────────────────────────────

def _draw_bench_box(parts, ox, oy, scale, sx, sy, width, depth, seat_h, back_h):
    """Draw one bench section: seat box + back panel + channel lines + seat line."""
    w, d, sh, bh = width, depth, seat_h, back_h
    bt = BACK_T

    # ── SEAT BOX (ground to seat height) ──
    # Front face
    parts.append(_poly([
        _iso(sx, sy, 0, ox, oy, scale),
        _iso(sx + w, sy, 0, ox, oy, scale),
        _iso(sx + w, sy, sh, ox, oy, scale),
        _iso(sx, sy, sh, ox, oy, scale),
    ]))
    # Top face of seat
    parts.append(_poly([
        _iso(sx, sy, sh, ox, oy, scale),
        _iso(sx + w, sy, sh, ox, oy, scale),
        _iso(sx + w, sy + d - bt, sh, ox, oy, scale),
        _iso(sx, sy + d - bt, sh, ox, oy, scale),
    ]))
    # Right side face of seat
    parts.append(_poly([
        _iso(sx + w, sy, 0, ox, oy, scale),
        _iso(sx + w, sy + d - bt, 0, ox, oy, scale),
        _iso(sx + w, sy + d - bt, sh, ox, oy, scale),
        _iso(sx + w, sy, sh, ox, oy, scale),
    ]))

    # ── BACK PANEL (seat_h to seat_h + back_h) ──
    # Front face of back
    parts.append(_poly([
        _iso(sx, sy + d - bt, sh, ox, oy, scale),
        _iso(sx + w, sy + d - bt, sh, ox, oy, scale),
        _iso(sx + w, sy + d - bt, sh + bh, ox, oy, scale),
        _iso(sx, sy + d - bt, sh + bh, ox, oy, scale),
    ]))
    # Top face of back
    parts.append(_poly([
        _iso(sx, sy + d - bt, sh + bh, ox, oy, scale),
        _iso(sx + w, sy + d - bt, sh + bh, ox, oy, scale),
        _iso(sx + w, sy + d, sh + bh, ox, oy, scale),
        _iso(sx, sy + d, sh + bh, ox, oy, scale),
    ]))
    # Right side of back
    parts.append(_poly([
        _iso(sx + w, sy + d - bt, sh, ox, oy, scale),
        _iso(sx + w, sy + d, sh, ox, oy, scale),
        _iso(sx + w, sy + d, sh + bh, ox, oy, scale),
        _iso(sx + w, sy + d - bt, sh + bh, ox, oy, scale),
    ]))

    # ── SEAT/BACK SEPARATION LINE (clear horizontal line at junction) ──
    sl1 = _iso(sx, sy + d - bt, sh, ox, oy, scale)
    sl2 = _iso(sx + w, sy + d - bt, sh, ox, oy, scale)
    parts.append(_line(sl1[0], sl1[1], sl2[0], sl2[1], 1.0))

    # ── CHANNEL LINES on back front face — subtle, every ~12" ──
    num_channels = max(int(w / 12), 2)
    for i in range(1, num_channels):
        cx = sx + w * i / num_channels
        p1 = _iso(cx, sy + d - bt, sh + 1, ox, oy, scale)
        p2 = _iso(cx, sy + d - bt, sh + bh - 1, ox, oy, scale)
        parts.append(_line(p1[0], p1[1], p2[0], p2[1], SW_CHAN))


# ── BUILD FUNCTIONS (return parts list for embedding) ─────────────

def _build_straight(name, width_in, depth_in, seat_h_in, back_h_in, quote_num="",
                    svg_w=500, svg_h=350):
    """Build straight bench parts. Returns (parts, scale, ox, oy)."""
    total_h = seat_h_in + back_h_in
    scale, ox, oy = _auto_scale((width_in, depth_in, total_h), svg_w, svg_h)
    parts = []
    _draw_bench_box(parts, ox, oy, scale, 0, 0, width_in, depth_in, seat_h_in, back_h_in)

    # Width dimension below front edge
    _dim_iso_width(parts, ox, oy, scale, 0, width_in, -3, -6, f'{width_in:.0f}"', below=True)
    # Back height — right side
    _dim_iso_height(parts, ox, oy, scale, width_in + 6, depth_in, seat_h_in, total_h, f'{back_h_in:.0f}"')
    # Seat height — right side, further out
    _dim_iso_height(parts, ox, oy, scale, width_in + 20, -3, 0, seat_h_in, f'{seat_h_in:.0f}"')
    # Depth — right side bottom
    _dim_iso_depth(parts, ox, oy, scale, width_in + 4, 0, depth_in, -3, f'{depth_in:.0f}"')

    return parts, scale, ox, oy


def _build_l_shape(name, long_in, short_in, depth_in, seat_h_in, back_h_in, quote_num="",
                   svg_w=500, svg_h=350):
    """Build L-shape bench parts."""
    total_h = seat_h_in + back_h_in
    scale, ox, oy = _auto_scale((long_in, short_in, total_h), svg_w, svg_h)
    parts = []

    # Long section along X axis (back along far Y edge)
    _draw_bench_box(parts, ox, oy, scale, 0, short_in - depth_in, long_in, depth_in, seat_h_in, back_h_in)
    # Short wing along Y axis at right end
    _draw_bench_box(parts, ox, oy, scale, long_in - depth_in, 0, depth_in, short_in, seat_h_in, back_h_in)

    # Long side width — above
    _dim_iso_width(parts, ox, oy, scale, 0, long_in, short_in - depth_in - 3, total_h + 6, f'{long_in:.0f}"', below=False)
    # Short wing — right side
    _dim_iso_depth(parts, ox, oy, scale, long_in + 4, 0, short_in, -3, f'{short_in:.0f}"')
    # Depth label
    _dim_iso_depth(parts, ox, oy, scale, long_in + 20, short_in - depth_in, short_in, -3, f'{depth_in:.0f}"')
    # Back height
    _dim_iso_height(parts, ox, oy, scale, long_in + 6, -3, seat_h_in, total_h, f'{back_h_in:.0f}"')
    # Seat height
    _dim_iso_height(parts, ox, oy, scale, long_in + 6, short_in - 3, 0, seat_h_in, f'{seat_h_in:.0f}"')

    return parts, scale, ox, oy


def _build_u_shape(name, back_in, side_in, depth_in, side_depth_in, seat_h_in, back_h_in,
                   quote_num="", svg_w=500, svg_h=350):
    """Build U-shape bench parts."""
    total_h = seat_h_in + back_h_in
    total_w = back_in + side_depth_in * 2
    scale, ox, oy = _auto_scale((total_w, side_in, total_h), svg_w, svg_h)
    parts = []

    # Left wing
    _draw_bench_box(parts, ox, oy, scale, 0, 0, side_depth_in, side_in, seat_h_in, back_h_in)
    # Center back
    _draw_bench_box(parts, ox, oy, scale, side_depth_in, side_in - depth_in, back_in, depth_in, seat_h_in, back_h_in)
    # Right wing
    _draw_bench_box(parts, ox, oy, scale, side_depth_in + back_in, 0, side_depth_in, side_in, seat_h_in, back_h_in)

    # Back width — above
    _dim_iso_width(parts, ox, oy, scale, side_depth_in, side_depth_in + back_in, side_in - depth_in - 3, total_h + 6, f'{back_in:.0f}"', below=False)
    # Left side length — left
    _dim_iso_depth(parts, ox, oy, scale, -6, 0, side_in, -3, f'{side_in:.0f}"')
    # Back height — left
    _dim_iso_height(parts, ox, oy, scale, -6, -3, seat_h_in, total_h, f'{back_h_in:.0f}"', right=False)
    # Seat height — right
    _dim_iso_height(parts, ox, oy, scale, total_w + 6, -3, 0, seat_h_in, f'{seat_h_in:.0f}"')
    # Right side length
    _dim_iso_depth(parts, ox, oy, scale, total_w + 4, 0, side_in, -3, f'{side_in:.0f}"')
    # Seat depth
    _dim_iso_depth(parts, ox, oy, scale, side_depth_in - 6, side_in - depth_in, side_in, -3, f'{depth_in:.0f}"')
    # Side depth — bottom left
    _dim_iso_width(parts, ox, oy, scale, 0, side_depth_in, -3, -6, f'{side_depth_in:.0f}"', below=True)
    # Side depth — bottom right
    _dim_iso_width(parts, ox, oy, scale, side_depth_in + back_in, total_w, -3, -6, f'{side_depth_in:.0f}"', below=True)

    return parts, scale, ox, oy


# ── PUBLIC RENDER FUNCTIONS ───────────────────────────────────────

def render_straight(name, width_in, depth_in=20, seat_h_in=18, back_h_in=18,
                    quote_num="", svg_w=600, svg_h=400, **kw):
    """Render a straight bench. All dimensions in inches."""
    if width_in < 50 and 'rate' not in kw:
        width_in = width_in * 12
    bp, *_ = _build_straight(name, width_in, depth_in, seat_h_in, back_h_in, quote_num, svg_w, svg_h)
    return _wrap_svg(bp, svg_w, svg_h, name, quote_num)


def render_l_shape(name, long_in, short_in=0, depth_in=20, seat_h_in=18, back_h_in=18,
                   quote_num="", svg_w=600, svg_h=400, **kw):
    """Render an L-shaped bench."""
    if long_in < 50:
        lf = long_in
        long_in = lf * 0.6 * 12
        if short_in == 0 or short_in < 10:
            short_in = lf * 0.4 * 12
    if short_in == 0:
        short_in = long_in * 0.5
    bp, *_ = _build_l_shape(name, long_in, short_in, depth_in, seat_h_in, back_h_in, quote_num, svg_w, svg_h)
    return _wrap_svg(bp, svg_w, svg_h, name, quote_num)


def render_u_shape(name, back_in, side_in=0, depth_in=20, side_depth_in=0,
                   seat_h_in=18, back_h_in=18, multiplier=1,
                   quote_num="", svg_w=600, svg_h=400, **kw):
    """Render a U-shaped booth."""
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
    bp, *_ = _build_u_shape(name, back_in, side_in, depth_in, side_depth_in,
                             seat_h_in, back_h_in, quote_num, svg_w, svg_h)
    return _wrap_svg(bp, svg_w, svg_h, name, quote_num)


# ── PROJECT SHEET ─────────────────────────────────────────────────

def render_project_sheet(benches, title="BUILT-IN BENCHES", quote_num="",
                         svg_w=1100, svg_h=850):
    """Render a 2x2 grid of benches with title block at bottom right."""
    parts = [_defs()]
    parts.append(f'<rect width="{svg_w}" height="{svg_h}" fill="white"/>')

    # Double border
    parts.append(f'<rect x="8" y="8" width="{svg_w-16}" height="{svg_h-16}" fill="none" stroke="{BLACK}" stroke-width="{SW_BORDER}"/>')
    parts.append(f'<rect x="14" y="14" width="{svg_w-28}" height="{svg_h-28}" fill="none" stroke="{BLACK}" stroke-width="0.5"/>')

    # Title block at bottom right
    tb_w = 280
    tb_h = 55
    tb_x = svg_w - 14 - tb_w
    tb_y = svg_h - 14 - tb_h
    parts.append(f'<rect x="{tb_x}" y="{tb_y}" width="{tb_w}" height="{tb_h}" fill="none" stroke="{BLACK}" stroke-width="{SW_MED}"/>')
    parts.append(_text(tb_x + tb_w / 2, tb_y + 28, title, 20, weight="bold"))
    if quote_num:
        parts.append(_text(tb_x + tb_w / 2, tb_y + 46, quote_num, 10))

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

    # Grid separator lines
    if cols > 1:
        mid_x = area_x + cell_w
        parts.append(_line(mid_x, area_y, mid_x, area_y + area_h, 0.5))
    if rows > 1:
        mid_y = area_y + cell_h
        parts.append(_line(area_x, mid_y, area_x + area_w, mid_y, 0.5))

    for idx, bench in enumerate(benches[:4]):
        col = idx % cols
        row = idx // cols

        # Cell origin
        cx = area_x + col * cell_w + 8
        cy = area_y + row * cell_h + 4

        # Available space for the bench drawing (leave room for label)
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

        # Cell label
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
    all_parts.append(f'<rect x="4" y="4" width="{svg_w-8}" height="{svg_h-8}" fill="none" stroke="{BLACK}" stroke-width="1"/>')
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
