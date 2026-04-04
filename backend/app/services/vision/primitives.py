"""
Shared SVG primitives library for Empire Drawing Studio.

All renderers (drawing_service, bench_renderer, future per-type renderers)
import building blocks from here to guarantee consistent line weights, fonts,
dimension style, and title block branding across every drawing.

Usage:
    from .primitives import (
        HEAVY, MEDIUM, LIGHT, HAIRLINE, BLACK, GRAY,
        dim_h, dim_v, leader, title_block, material_legend,
        view_label, svg_wrap, rect, line, text, cushion_shape,
    )
"""

from datetime import datetime

# ── LINE WEIGHTS ──────────────────────────────────────────────────
HEAVY = 2.5        # Object outlines, borders
MEDIUM = 1.5       # Structure lines, section cuts
LIGHT = 0.8        # Internal details, cushion dividers
HAIRLINE = 0.4     # Extension lines, hatching, channel lines

# Aliases matching existing renderer names
SW_HEAVY = HEAVY
SW_MED = MEDIUM
SW_LIGHT = LIGHT
SW_DIM = 0.75
SW_EXT = 0.5
SW_BORDER = 2.0
SW_CHANNEL = 0.3
SW_FLOOR = 1.0

# ── COLORS ────────────────────────────────────────────────────────
BLACK = "#000000"
DIM_COLOR = "#333333"
GRAY = "#666666"
LIGHT_GRAY = "#CCCCCC"
EMPIRE_GOLD = "#C5A258"
EMPIRE_GOLD_LIGHT = "#E8D5A3"
WHITE = "#FFFFFF"
PANE_FILL = "#f0f5fa"

# ── FONTS ─────────────────────────────────────────────────────────
FONT = "Arial, Helvetica, sans-serif"
FONT_TITLE = "Arial, Helvetica, sans-serif"
FONT_DIM = "Arial, Helvetica, sans-serif"

# ── BRANDING ──────────────────────────────────────────────────────
BRANDING_WORKROOM = {
    "company": "EMPIRE WORKROOM",
    "tagline": "Custom Upholstery &amp; Window Treatments",
    "address": "5124 Frolich Ln, Hyattsville, MD 20781",
    "contact": "(703) 213-6484 | workroom@empirebox.store",
}
BRANDING_WOODCRAFT = {
    "company": "EMPIRE WOODCRAFT",
    "tagline": "Custom Woodwork &amp; CNC Fabrication",
    "address": "5124 Frolich Ln, Hyattsville, MD 20781",
    "contact": "(703) 213-6484 | woodcraft@empirebox.store",
}


# ── SVG DEFS (shared markers) ────────────────────────────────────

def defs():
    """Standard SVG defs block with dimension arrow markers."""
    return '''<defs>
  <marker id="dim-arrow" viewBox="0 0 10 6" refX="10" refY="3"
          markerWidth="8" markerHeight="6" orient="auto-start-reverse">
    <path d="M0,0 L10,3 L0,6 Z" fill="#000"/>
  </marker>
  <marker id="leader-dot" viewBox="0 0 6 6" refX="3" refY="3"
          markerWidth="6" markerHeight="6">
    <circle cx="3" cy="3" r="2.5" fill="#000"/>
  </marker>
</defs>'''


# ── BASIC SVG HELPERS ─────────────────────────────────────────────

def esc(s: str) -> str:
    """Escape text for safe SVG embedding."""
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def rect(x, y, w, h, sw=MEDIUM, fill="none", stroke=BLACK):
    """SVG rectangle."""
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
    )


def line(x1, y1, x2, y2, sw=MEDIUM, color=BLACK):
    """SVG line segment."""
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{color}" stroke-width="{sw}"/>'
    )


def text(x, y, content, size=10, weight="normal", fill=BLACK, anchor="middle"):
    """SVG text element. Horizontal only — no rotation by default."""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        f'font-family="{FONT}" font-size="{size}" fill="{fill}" '
        f'font-weight="{weight}">{content}</text>'
    )


def circle(cx, cy, r, sw=MEDIUM, fill="none", stroke=BLACK):
    """SVG circle."""
    return (
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
    )


def dashed_line(x1, y1, x2, y2, sw=LIGHT, color=BLACK, dash="6,3"):
    """SVG dashed line."""
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{color}" stroke-width="{sw}" stroke-dasharray="{dash}"/>'
    )


# ── DIMENSION HELPERS ─────────────────────────────────────────────

def dim_h(parts, x1, x2, y, label, offset=20):
    """Horizontal dimension line with extension lines and tick marks.

    Args:
        parts: list to append SVG elements to
        x1: left x coordinate (object edge)
        x2: right x coordinate (object edge)
        y: y coordinate of the object edge
        label: dimension text (e.g. "72\"")
        offset: distance from object edge to dim line (positive=below, negative=above)
    """
    sign = 1 if offset > 0 else -1
    gap = 3
    ext = 5
    # Extension lines from object edge to dimension line
    parts.append(line(x1, y + gap * sign, x1, y + offset + ext * sign, SW_EXT))
    parts.append(line(x2, y + gap * sign, x2, y + offset + ext * sign, SW_EXT))
    # Dimension line with arrows
    dy = y + offset
    parts.append(
        f'<line x1="{x1:.1f}" y1="{dy:.1f}" x2="{x2:.1f}" y2="{dy:.1f}" '
        f'stroke="{BLACK}" stroke-width="{SW_DIM}" '
        f'marker-start="url(#dim-arrow)" marker-end="url(#dim-arrow)"/>'
    )
    # Label centered on dimension line
    mx = (x1 + x2) / 2
    ty = dy - 4 if offset < 0 else dy + 12
    parts.append(text(mx, ty, label, 9, weight="600"))


def dim_v(parts, x, y1, y2, label, offset=20):
    """Vertical dimension line with extension lines and tick marks.

    Args:
        parts: list to append SVG elements to
        x: x coordinate of the object edge
        y1: top y coordinate
        y2: bottom y coordinate
        label: dimension text (e.g. "36\"")
        offset: distance from object edge to dim line (positive=right, negative=left)
    """
    sign = 1 if offset > 0 else -1
    gap = 3
    ext = 5
    # Extension lines
    parts.append(line(x + gap * sign, y1, x + offset + ext * sign, y1, SW_EXT))
    parts.append(line(x + gap * sign, y2, x + offset + ext * sign, y2, SW_EXT))
    # Dimension line with arrows
    dx = x + offset
    parts.append(
        f'<line x1="{dx:.1f}" y1="{y1:.1f}" x2="{dx:.1f}" y2="{y2:.1f}" '
        f'stroke="{BLACK}" stroke-width="{SW_DIM}" '
        f'marker-start="url(#dim-arrow)" marker-end="url(#dim-arrow)"/>'
    )
    # Label — placed alongside the vertical dim line
    mx = dx + (8 if offset > 0 else -8)
    my = (y1 + y2) / 2 + 3
    # Vertical labels rotated -90 for readability
    parts.append(
        f'<text x="{mx:.1f}" y="{my:.1f}" text-anchor="middle" '
        f'font-family="{FONT}" font-size="9" fill="{BLACK}" font-weight="600" '
        f'transform="rotate(-90,{mx:.1f},{my:.1f})">{label}</text>'
    )


def leader(parts, x1, y1, x2, y2, label):
    """Leader line with dot at origin and text label at endpoint.

    Args:
        parts: list to append SVG elements to
        x1, y1: start point (on the object — gets a dot)
        x2, y2: end point (where the label sits)
        label: callout text
    """
    # Leader line
    parts.append(
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{BLACK}" stroke-width="{SW_DIM}" '
        f'marker-start="url(#leader-dot)"/>'
    )
    # Horizontal tail from endpoint
    tail_dir = 1 if x2 >= x1 else -1
    tail_len = 30
    tx = x2 + tail_len * tail_dir
    parts.append(line(x2, y2, tx, y2, SW_DIM))
    # Label above the tail
    anchor = "start" if tail_dir > 0 else "end"
    parts.append(text(x2 + 2 * tail_dir, y2 - 5, esc(label), 8, anchor=anchor))


# ── TITLE BLOCK ───────────────────────────────────────────────────

def title_block(parts, x, y, w, h, company="", item_type="", dims_str="",
                client="", project="", job="", revision="", date="",
                sheet="1 of 1", scale="NTS", mode="presentation"):
    """Professional title block with Empire gold accent bar.

    Renders a bordered box with company branding, project info grid,
    and a gold accent stripe along the top edge.

    Args:
        parts: list to append SVG elements to
        x, y: top-left corner
        w, h: width and height
        company: company name (auto-detected from item_type if empty)
        item_type: used to pick Workroom vs WoodCraft branding
        dims_str: overall dimensions string for display
        client: client name
        project: project name or description
        job: job / quote number
        revision: revision letter or number
        date: date string (defaults to today)
        sheet: sheet numbering (e.g. "1 of 1")
        scale: scale notation (e.g. "NTS", "1:10")
        mode: "presentation" | "shop" | "construction"
    """
    # Auto-detect branding
    from .product_catalog import get_business_unit
    if not company:
        unit = get_business_unit(item_type) if item_type else "workroom"
        brand = BRANDING_WOODCRAFT if unit == "woodcraft" else BRANDING_WORKROOM
    else:
        brand = {"company": company, "tagline": "", "address": "", "contact": ""}

    if not date:
        date = datetime.now().strftime("%m/%d/%Y")

    # Outer border
    parts.append(rect(x, y, w, h, SW_MED))
    # Gold accent bar across top
    parts.append(rect(x, y, w, 4, 0, fill=EMPIRE_GOLD, stroke="none"))

    # Company name
    parts.append(text(x + w / 2, y + 20, brand.get("company", "EMPIRE"), 14, weight="bold"))
    # Tagline
    tagline = brand.get("tagline", "")
    if tagline:
        parts.append(text(x + w / 2, y + 33, tagline, 7, fill=GRAY))

    # Divider
    parts.append(line(x + 10, y + 38, x + w - 10, y + 38, HAIRLINE, LIGHT_GRAY))

    # Project info grid — two columns
    col1_x = x + 12
    col2_x = x + w / 2 + 6
    info_y = y + 52
    row_h = 14

    def _info_row(lx, ly, label_text, value_text):
        parts.append(text(lx, ly, label_text, 7, fill=GRAY, anchor="start"))
        parts.append(text(lx + 50, ly, esc(str(value_text)), 8, weight="600", anchor="start"))

    if item_type:
        _info_row(col1_x, info_y, "ITEM:", item_type.upper().replace("_", " "))
    if dims_str:
        _info_row(col2_x, info_y, "DIMS:", dims_str)

    if client:
        _info_row(col1_x, info_y + row_h, "CLIENT:", client)
    if project:
        _info_row(col2_x, info_y + row_h, "PROJECT:", project)

    if job:
        _info_row(col1_x, info_y + row_h * 2, "JOB #:", job)
    if revision:
        _info_row(col2_x, info_y + row_h * 2, "REV:", revision)

    # Bottom row: date, sheet, scale, mode
    bottom_y = y + h - 12
    parts.append(line(x + 10, bottom_y - 8, x + w - 10, bottom_y - 8, HAIRLINE, LIGHT_GRAY))

    seg_w = w / 4
    parts.append(text(x + seg_w * 0.5, bottom_y, f"DATE: {date}", 7, fill=GRAY))
    parts.append(text(x + seg_w * 1.5, bottom_y, f"SHEET: {sheet}", 7, fill=GRAY))
    parts.append(text(x + seg_w * 2.5, bottom_y, f"SCALE: {scale}", 7, fill=GRAY))
    parts.append(text(x + seg_w * 3.5, bottom_y, mode.upper(), 7, fill=EMPIRE_GOLD, weight="bold"))

    # Address footer
    address = brand.get("address", "")
    if address:
        parts.append(text(x + w / 2, y + h - 2, address, 6, fill=LIGHT_GRAY))


# ── MATERIAL LEGEND ───────────────────────────────────────────────

def material_legend(parts, x, y, materials):
    """Compact material legend block.

    Args:
        parts: list to append SVG elements to
        x, y: top-left corner
        materials: list of dicts with keys "label", "value", and optional "swatch" (color)
            e.g. [{"label": "Fabric", "value": "Kravet 36950.16", "swatch": "#C4A882"},
                  {"label": "Welt", "value": "Self-welt"},
                  {"label": "Foam", "value": '4" HR 35ILD'}]
    """
    if not materials:
        return

    row_h = 16
    header_h = 18
    total_h = header_h + len(materials) * row_h + 6
    max_w = 180

    # Background
    parts.append(rect(x, y, max_w, total_h, HAIRLINE, fill="#FAFAFA", stroke=LIGHT_GRAY))
    # Header
    parts.append(rect(x, y, max_w, header_h, 0, fill=EMPIRE_GOLD_LIGHT, stroke="none"))
    parts.append(text(x + max_w / 2, y + 13, "MATERIALS", 8, weight="bold"))

    for i, mat in enumerate(materials):
        ry = y + header_h + i * row_h + 12
        # Optional color swatch
        swatch = mat.get("swatch")
        if swatch:
            parts.append(rect(x + 8, ry - 8, 10, 10, 0.5, fill=swatch, stroke=GRAY))
            label_x = x + 24
        else:
            label_x = x + 8
        parts.append(text(label_x, ry, esc(mat.get("label", "")), 7, fill=GRAY, anchor="start"))
        parts.append(text(label_x + 50, ry, esc(mat.get("value", "")), 7, weight="600", anchor="start"))


# ── VIEW LABEL ────────────────────────────────────────────────────

def view_label(parts, x, y, w, label):
    """Section/view label centered above a drawing zone.

    Args:
        parts: list to append SVG elements to
        x: left edge of the zone
        y: top of the label area
        w: width of the zone
        label: label text (e.g. "FRONT ELEVATION", "PLAN VIEW")
    """
    parts.append(text(x + w / 2, y + 14, label, 10, weight="bold"))


# ── SVG WRAP ──────────────────────────────────────────────────────

def svg_wrap(parts, w, h):
    """Wrap SVG content list with proper xmlns, viewBox, and dimensions.

    Args:
        parts: list of SVG element strings
        w: viewBox width
        h: viewBox height

    Returns:
        Complete SVG document string.
    """
    body = "\n  ".join(parts)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}">\n  {body}\n</svg>'
    )


# ── CUSHION SHAPE ─────────────────────────────────────────────────

def cushion_shape(parts, x, y, w, h, style="box"):
    """Draw a cushion outline in the given style.

    Styles:
        box      — crisp rectangle with welt seam inset
        pillow   — rounded corners with soft crown line
        tufted   — grid of button dimples
        channel  — vertical channel lines
        bullnose — rounded front edge
        knife    — thin knife-edge profile (tapered sides)

    Args:
        parts: list to append SVG elements to
        x, y: top-left corner
        w, h: width and height
        style: one of the above style keywords
    """
    style = (style or "box").lower().replace("-", "_").replace(" ", "_")

    if style == "pillow":
        r = min(w, h) * 0.15
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'rx="{r:.1f}" ry="{r:.1f}" fill="none" stroke="{BLACK}" stroke-width="{LIGHT}"/>'
        )
        # Crown line (soft curve across top)
        mid_x = x + w / 2
        parts.append(
            f'<path d="M{x + r:.1f},{y + h * 0.3:.1f} Q{mid_x:.1f},{y + h * 0.15:.1f} '
            f'{x + w - r:.1f},{y + h * 0.3:.1f}" fill="none" stroke="{LIGHT_GRAY}" '
            f'stroke-width="{HAIRLINE}"/>'
        )

    elif style == "tufted":
        parts.append(rect(x, y, w, h, LIGHT))
        # Button grid
        cols = max(2, int(w / 20))
        rows = max(2, int(h / 20))
        for r in range(rows):
            for c in range(cols):
                bx = x + (c + 0.5) * w / cols
                by = y + (r + 0.5) * h / rows
                parts.append(circle(bx, by, 2.5, 0.5, fill="#DDD", stroke=GRAY))

    elif style == "channel":
        parts.append(rect(x, y, w, h, LIGHT))
        ch_count = max(3, int(w / 12))
        for i in range(1, ch_count):
            cx = x + i * w / ch_count
            parts.append(line(cx, y + 2, cx, y + h - 2, SW_CHANNEL, GRAY))

    elif style == "bullnose":
        r = min(h * 0.4, 8)
        parts.append(
            f'<path d="M{x:.1f},{y:.1f} L{x + w:.1f},{y:.1f} '
            f'L{x + w:.1f},{y + h - r:.1f} Q{x + w:.1f},{y + h:.1f} '
            f'{x + w - r:.1f},{y + h:.1f} L{x + r:.1f},{y + h:.1f} '
            f'Q{x:.1f},{y + h:.1f} {x:.1f},{y + h - r:.1f} Z" '
            f'fill="none" stroke="{BLACK}" stroke-width="{LIGHT}"/>'
        )

    elif style == "knife" or style == "knife_edge":
        # Tapered — narrower at edges
        inset = min(h * 0.25, 6)
        parts.append(
            f'<path d="M{x:.1f},{y + inset:.1f} L{x + w / 2:.1f},{y:.1f} '
            f'L{x + w:.1f},{y + inset:.1f} L{x + w:.1f},{y + h - inset:.1f} '
            f'L{x + w / 2:.1f},{y + h:.1f} L{x:.1f},{y + h - inset:.1f} Z" '
            f'fill="none" stroke="{BLACK}" stroke-width="{LIGHT}"/>'
        )

    else:
        # Default: box with welt seam
        parts.append(rect(x, y, w, h, LIGHT))
        inset = min(w, h) * 0.08
        if inset >= 2:
            parts.append(rect(x + inset, y + inset, w - inset * 2, h - inset * 2, HAIRLINE, stroke=GRAY))


# ── HATCHING PATTERNS ─────────────────────────────────────────────

def hatch_area(parts, x, y, w, h, spacing=6, angle=45):
    """Add diagonal hatch lines to indicate cut sections.

    Args:
        parts: list to append SVG elements to
        x, y: top-left of hatch area
        w, h: dimensions
        spacing: distance between hatch lines
        angle: hatch angle in degrees (45 = standard section hatch)
    """
    import math
    parts.append(f'<g clip-path="url(#hatch-clip-{id(parts)})">')
    # Clip rect
    parts.append(
        f'<clipPath id="hatch-clip-{id(parts)}">'
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}"/>'
        f'</clipPath>'
    )
    diag = math.sqrt(w * w + h * h)
    count = int(diag / spacing) + 2
    cx, cy = x + w / 2, y + h / 2
    for i in range(-count, count + 1):
        offset = i * spacing
        lx1 = cx + offset - diag
        ly1 = cy - diag
        lx2 = cx + offset + diag
        ly2 = cy + diag
        parts.append(line(lx1, ly1, lx2, ly2, HAIRLINE, LIGHT_GRAY))
    parts.append('</g>')
