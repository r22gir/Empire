"""
Parametric SVG Renderer — converts JSON drafting instructions to clean SVG.

Stage 2 of the two-stage pipeline:
  All creative/spatial decisions are in the JSON from Stage 1.
  This code ONLY does projection math, line drawing, and text placement.
  Line weights, fonts, arrow styles are NEVER from AI — always from code.
"""
import math
import re

# ============================================================
# ISOMETRIC PROJECTION
# ============================================================
ISO_ANGLE = math.radians(30)
COS_A = math.cos(ISO_ANGLE)
SIN_A = math.sin(ISO_ANGLE)


def iso_project(x: float, y: float, z: float, scale: float = 1.0) -> tuple[float, float]:
    """Convert 3D point to 2D isometric screen coordinates."""
    sx = (x * COS_A - y * COS_A) * scale
    sy = -((x * SIN_A + y * SIN_A) + z) * scale
    return sx, sy


# ============================================================
# STYLE CONSTANTS — code-controlled, never from AI
# ============================================================
STYLES = {
    "outline": {"stroke": "#000", "width": 1.5},
    "detail":  {"stroke": "#000", "width": 0.5},
    "channel": {"stroke": "#000", "width": 0.3},
    "dim":     {"stroke": "#000", "width": 0.75},
    "ext":     {"stroke": "#000", "width": 0.5},
}

FONT = "Arial, Helvetica, sans-serif"
FONT_DIM = 9
FONT_LABEL = 11
FONT_TITLE = 18
ARROW_SIZE = 6  # px


# ============================================================
# MAIN RENDER FUNCTION
# ============================================================

def render_to_svg(drawing: dict, width: int = 700, height: int = 500) -> str:
    """Render a single drawing JSON to SVG string."""
    if not drawing or "geometry" not in drawing:
        return _error_svg("No valid geometry data", width, height)

    geom = drawing["geometry"]
    points_3d = geom.get("points", {})
    edges = geom.get("edges", [])
    faces = geom.get("faces", [])
    dimensions = drawing.get("dimensions", [])
    channels = drawing.get("channels", {})
    label = drawing.get("label", "")

    # Calculate fit
    scale, off_x, off_y = _calculate_fit(points_3d, width, height, margin=50)

    # Project all 3D points to 2D
    pts = {}
    for name, coords in points_3d.items():
        sx, sy = iso_project(coords[0], coords[1], coords[2], scale)
        pts[name] = (sx + off_x, sy + off_y)

    els = []  # SVG elements

    # Defs (arrow marker)
    els.append(_svg_defs())

    # Background
    els.append(f'<rect width="{width}" height="{height}" fill="white"/>')

    # Draw edges by weight (channels first, then detail, then outline on top)
    for weight in ("channel", "detail", "outline"):
        for edge in edges:
            if edge.get("weight", "outline") != weight:
                continue
            p1 = pts.get(edge["from"])
            p2 = pts.get(edge["to"])
            if p1 and p2:
                st = STYLES.get(weight, STYLES["outline"])
                els.append(
                    f'<line x1="{p1[0]:.1f}" y1="{p1[1]:.1f}" '
                    f'x2="{p2[0]:.1f}" y2="{p2[1]:.1f}" '
                    f'stroke="{st["stroke"]}" stroke-width="{st["width"]}" '
                    f'stroke-linejoin="round"/>'
                )

    # Draw channel lines from channel spec (if AI provided face reference)
    if channels and channels.get("count") and faces:
        _draw_channels(els, channels, faces, pts)

    # Draw dimensions
    for dim in dimensions:
        p1 = pts.get(dim.get("from"))
        p2 = pts.get(dim.get("to"))
        if p1 and p2:
            _draw_dimension(els, p1, p2, dim.get("label", ""),
                            dim.get("placement", "bottom"),
                            dim.get("offset", 25))

    # Label
    if label:
        els.append(
            f'<text x="{width/2:.0f}" y="22" text-anchor="middle" '
            f'font-family="{FONT}" font-size="{FONT_LABEL}" '
            f'font-weight="bold" fill="#000">{_esc(label)}</text>'
        )

    # Footer
    els.append(
        f'<text x="{width-8}" y="{height-6}" text-anchor="end" '
        f'font-family="{FONT}" font-size="7" fill="#000">Empire Workroom</text>'
    )

    body = "\n  ".join(els)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}">\n  {body}\n</svg>'
    )


def render_project_sheet(bench_drawings: list, layout: dict = None,
                         width: int = 1100, height: int = 850) -> str:
    """Render multiple bench drawings in a 2x2 grid with title block."""
    layout = layout or {}
    title = layout.get("title", "BUILT-IN BENCHES")
    subtitle = layout.get("subtitle", "")
    cols = layout.get("grid", [2, 2])[0] if isinstance(layout.get("grid"), list) else 2
    rows = layout.get("grid", [2, 2])[1] if isinstance(layout.get("grid"), list) else 2

    els = [_svg_defs()]
    els.append(f'<rect width="{width}" height="{height}" fill="white"/>')

    # Double border
    els.append(f'<rect x="8" y="8" width="{width-16}" height="{height-16}" fill="none" stroke="#000" stroke-width="2"/>')
    els.append(f'<rect x="14" y="14" width="{width-28}" height="{height-28}" fill="none" stroke="#000" stroke-width="0.5"/>')

    # Title block
    tb_w, tb_h = 280, 55
    tb_x = width - 14 - tb_w
    tb_y = height - 14 - tb_h
    els.append(f'<rect x="{tb_x}" y="{tb_y}" width="{tb_w}" height="{tb_h}" fill="none" stroke="#000" stroke-width="1.5"/>')
    els.append(f'<text x="{tb_x + tb_w/2:.0f}" y="{tb_y + 28}" text-anchor="middle" font-family="{FONT}" font-size="{FONT_TITLE}" font-weight="bold">{_esc(title)}</text>')
    if subtitle:
        els.append(f'<text x="{tb_x + tb_w/2:.0f}" y="{tb_y + 44}" text-anchor="middle" font-family="{FONT}" font-size="10">{_esc(subtitle)}</text>')

    # Grid
    area_x, area_y = 20, 20
    area_w = width - 40
    area_h = tb_y - 28

    cell_w = area_w / cols
    cell_h = area_h / rows

    # Grid lines
    for c in range(1, cols):
        x = area_x + c * cell_w
        els.append(f'<line x1="{x:.0f}" y1="{area_y}" x2="{x:.0f}" y2="{area_y + area_h:.0f}" stroke="#000" stroke-width="0.5"/>')
    for r in range(1, rows):
        y = area_y + r * cell_h
        els.append(f'<line x1="{area_x}" y1="{y:.0f}" x2="{area_x + area_w:.0f}" y2="{y:.0f}" stroke="#000" stroke-width="0.5"/>')

    # Render each bench in its cell
    for idx, bench in enumerate(bench_drawings[:cols * rows]):
        col = idx % cols
        row = idx // cols
        cx = area_x + col * cell_w + 8
        cy = area_y + row * cell_h + 4
        cw = cell_w - 16
        ch = cell_h - 8

        cell_svg = render_to_svg(bench, int(cw), int(ch))
        inner = _extract_svg_content(cell_svg)
        els.append(f'<g transform="translate({cx:.0f},{cy:.0f})">{inner}</g>')

    body = "\n  ".join(els)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}">\n  {body}\n</svg>'
    )


# ============================================================
# DIMENSION DRAWING — always horizontal or vertical text
# ============================================================

def _draw_dimension(els, p1, p2, label, placement, offset):
    """Architectural dimension with extension lines, arrows, horizontal/vertical text."""
    dx, dy = 0.0, 0.0
    if placement == "bottom":
        dy = abs(offset)
    elif placement == "top":
        dy = -abs(offset)
    elif placement == "right":
        dx = abs(offset)
    elif placement == "left":
        dx = -abs(offset)

    # Offset points for the dimension line
    d1 = (p1[0] + dx, p1[1] + dy)
    d2 = (p2[0] + dx, p2[1] + dy)

    # Extension lines
    _ext_line(els, p1, d1)
    _ext_line(els, p2, d2)

    # Dimension line with arrow markers
    els.append(
        f'<line x1="{d1[0]:.1f}" y1="{d1[1]:.1f}" '
        f'x2="{d2[0]:.1f}" y2="{d2[1]:.1f}" '
        f'stroke="{STYLES["dim"]["stroke"]}" stroke-width="{STYLES["dim"]["width"]}" '
        f'marker-start="url(#dim-arrow)" marker-end="url(#dim-arrow)"/>'
    )

    # Text — always horizontal for bottom/top, vertical (bottom-to-top) for left/right
    mx = (d1[0] + d2[0]) / 2
    my = (d1[1] + d2[1]) / 2
    if placement in ("left", "right"):
        tx = mx + (8 if placement == "right" else -8)
        els.append(
            f'<text x="{tx:.1f}" y="{my + 3:.1f}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="{FONT_DIM}" font-weight="600" '
            f'fill="#000" transform="rotate(-90,{tx:.1f},{my:.1f})">{_esc(label)}</text>'
        )
    else:
        ty = my - 4 if placement == "top" else my - 4
        els.append(
            f'<text x="{mx:.1f}" y="{ty:.1f}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="{FONT_DIM}" font-weight="600" '
            f'fill="#000">{_esc(label)}</text>'
        )


def _ext_line(els, obj_pt, dim_pt):
    """Extension line from object point toward dimension line, with gap."""
    dx = dim_pt[0] - obj_pt[0]
    dy = dim_pt[1] - obj_pt[1]
    dist = math.hypot(dx, dy)
    if dist < 1:
        return
    nx, ny = dx / dist, dy / dist
    gap = 3
    extra = 5
    start = (obj_pt[0] + nx * gap, obj_pt[1] + ny * gap)
    end = (dim_pt[0] + nx * extra, dim_pt[1] + ny * extra)
    els.append(
        f'<line x1="{start[0]:.1f}" y1="{start[1]:.1f}" '
        f'x2="{end[0]:.1f}" y2="{end[1]:.1f}" '
        f'stroke="{STYLES["ext"]["stroke"]}" stroke-width="{STYLES["ext"]["width"]}"/>'
    )


# ============================================================
# CHANNEL LINES
# ============================================================

def _draw_channels(els, channels, faces, pts):
    """Draw channel lines on the specified face."""
    face_type = channels.get("face", "back_front")
    count = channels.get("count", 6)

    target = None
    for f in faces:
        if f.get("type") == face_type:
            target = f
            break
    if not target:
        return

    face_pts = [pts[p] for p in target.get("points", []) if p in pts]
    if len(face_pts) < 4:
        return

    # Assume face_pts order: bottom-left, bottom-right, top-right, top-left
    bl, br, tr, tl = face_pts[0], face_pts[1], face_pts[2], face_pts[3]

    for i in range(1, count):
        t = i / count
        # Interpolate along bottom and top edges
        bx = bl[0] + (br[0] - bl[0]) * t
        by = bl[1] + (br[1] - bl[1]) * t
        tx = tl[0] + (tr[0] - tl[0]) * t
        ty = tl[1] + (tr[1] - tl[1]) * t
        st = STYLES["channel"]
        els.append(
            f'<line x1="{bx:.1f}" y1="{by:.1f}" x2="{tx:.1f}" y2="{ty:.1f}" '
            f'stroke="{st["stroke"]}" stroke-width="{st["width"]}"/>'
        )


# ============================================================
# HELPERS
# ============================================================

def _calculate_fit(points_3d, width, height, margin=50):
    """Calculate scale and offset to fit all projected points."""
    if not points_3d:
        return 1.0, width / 2, height / 2

    projected = [iso_project(c[0], c[1], c[2], 1.0) for c in points_3d.values()]
    xs = [p[0] for p in projected]
    ys = [p[1] for p in projected]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    rw = (max_x - min_x) or 1
    rh = (max_y - min_y) or 1

    # Leave room for labels at top (30px) and dims (margin)
    avail_w = width - 2 * margin
    avail_h = height - 2 * margin - 30

    scale = min(avail_w / rw, avail_h / rh)

    # Re-project at computed scale to center
    proj2 = [iso_project(c[0], c[1], c[2], scale) for c in points_3d.values()]
    xs2 = [p[0] for p in proj2]
    ys2 = [p[1] for p in proj2]
    cx = (min(xs2) + max(xs2)) / 2
    cy = (min(ys2) + max(ys2)) / 2

    off_x = width / 2 - cx
    off_y = height / 2 - cy + 15  # shift down for title
    return scale, off_x, off_y


def _svg_defs():
    return '''<defs>
  <marker id="dim-arrow" viewBox="0 0 10 6" refX="10" refY="3"
          markerWidth="8" markerHeight="6" orient="auto-start-reverse">
    <path d="M0,0 L10,3 L0,6 Z" fill="#000"/>
  </marker>
</defs>'''


def _extract_svg_content(svg_str):
    """Strip outer <svg> tags to get inner content for embedding."""
    content = re.sub(r"^<svg[^>]*>", "", svg_str)
    content = re.sub(r"</svg>$", "", content)
    return content.strip()


def _error_svg(msg, w, h):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}">'
        f'<rect width="{w}" height="{h}" fill="white"/>'
        f'<text x="{w/2}" y="{h/2}" text-anchor="middle" fill="red" '
        f'font-size="14">Error: {_esc(msg)}</text></svg>'
    )


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
