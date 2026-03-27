"""
General architectural drawing service — classifies input and routes to the
correct renderer. Falls back to a clean measurement diagram for items
without a dedicated renderer.

Used by the sketch_to_drawing MAX tool.
"""
import re
import os
from pathlib import Path

# ── Item type classification ──────────────────────────────────────────
ITEM_KEYWORDS = {
    "bench": ["bench", "banquette", "booth", "seating"],
    "window": ["window", "drapery", "drape", "curtain", "shade", "blind", "valance", "cornice", "roman shade", "ripplefold", "pinch pleat", "rod pocket", "grommet"],
    "pillow": ["pillow", "bolster", "cushion", "throw"],
    "upholstery": ["chair", "sofa", "couch", "ottoman", "headboard", "slipcover", "reupholster"],
    "table": ["table", "desk", "console"],
}


def classify_input(text: str) -> str:
    """Classify what type of item the input describes. Returns item type string."""
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for item_type, keywords in ITEM_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[item_type] = score
    if not scores:
        return "generic"
    return max(scores, key=scores.get)


def render_measurement_diagram(
    name: str,
    item_type: str,
    dimensions: dict,
    notes: str = "",
    svg_w: int = 740,
    svg_h: int = 460,
) -> str:
    """Generate a clean SVG measurement diagram for any item type.

    dimensions: dict of label→value pairs, e.g. {"Width": "72\"", "Height": "48\"", "Drop": "84\""}
    """
    # Colors
    c_bg = "#faf8f4"
    c_border = "#d4b87a"
    c_text = "#1a1a2e"
    c_dim = "#b8960c"
    c_line = "#c9a96e"
    c_label = "#666"

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}" width="{svg_w}" height="{svg_h}">',
        f'<rect width="{svg_w}" height="{svg_h}" fill="{c_bg}" rx="8"/>',
        # Border
        f'<rect x="4" y="4" width="{svg_w-8}" height="{svg_h-8}" fill="none" stroke="{c_border}" stroke-width="2" rx="6"/>',
    ]

    # ── Header ──
    parts.append(f'<text x="{svg_w/2}" y="36" text-anchor="middle" font-size="20" font-weight="800" fill="{c_text}" font-family="sans-serif">{_esc(name)}</text>')
    type_label = item_type.replace("_", " ").title()
    parts.append(f'<text x="{svg_w/2}" y="56" text-anchor="middle" font-size="13" fill="{c_label}" font-family="sans-serif">{type_label} — Measurement Diagram</text>')

    # ── Central shape representation ──
    cx, cy = svg_w / 2, svg_h / 2
    shape_w, shape_h = 280, 200

    if item_type == "window":
        _draw_window(parts, cx, cy, shape_w, shape_h, c_line, c_border, c_text)
    elif item_type == "pillow":
        _draw_pillow(parts, cx, cy, shape_w, shape_h, c_line, c_border)
    elif item_type in ("upholstery", "chair"):
        _draw_chair(parts, cx, cy, shape_w, shape_h, c_line, c_border)
    elif item_type == "table":
        _draw_table(parts, cx, cy, shape_w, shape_h, c_line, c_border)
    else:
        # Generic rectangle with cross-hatch
        x0, y0 = cx - shape_w / 2, cy - shape_h / 2
        parts.append(f'<rect x="{x0}" y="{y0}" width="{shape_w}" height="{shape_h}" fill="#f5f0e6" stroke="{c_border}" stroke-width="2" rx="4"/>')
        # Cross lines
        parts.append(f'<line x1="{x0}" y1="{y0}" x2="{x0+shape_w}" y2="{y0+shape_h}" stroke="{c_line}" stroke-width="0.5" stroke-dasharray="6,4"/>')
        parts.append(f'<line x1="{x0+shape_w}" y1="{y0}" x2="{x0}" y2="{y0+shape_h}" stroke="{c_line}" stroke-width="0.5" stroke-dasharray="6,4"/>')

    # ── Dimension callouts ──
    dim_items = list(dimensions.items())
    if dim_items:
        # Layout dimensions around the shape
        left_x = cx - shape_w / 2 - 60
        right_x = cx + shape_w / 2 + 20
        top_y = cy - shape_h / 2 - 20
        bottom_y = cy + shape_h / 2 + 30

        positions = []
        if len(dim_items) >= 1:
            positions.append((cx, bottom_y + 10))  # bottom center
        if len(dim_items) >= 2:
            positions.append((right_x + 30, cy))  # right
        if len(dim_items) >= 3:
            positions.append((cx, top_y - 6))  # top center
        if len(dim_items) >= 4:
            positions.append((left_x - 10, cy))  # left
        # Additional dims stack below
        for i in range(4, len(dim_items)):
            positions.append((cx, bottom_y + 10 + (i - 3) * 24))

        for i, (label, value) in enumerate(dim_items):
            if i >= len(positions):
                break
            px, py = positions[i]
            parts.append(f'<text x="{px}" y="{py}" text-anchor="middle" font-size="14" font-weight="700" fill="{c_dim}" font-family="sans-serif">{_esc(str(value))}</text>')
            parts.append(f'<text x="{px}" y="{py+16}" text-anchor="middle" font-size="10" fill="{c_label}" font-family="sans-serif">{_esc(label)}</text>')

    # ── Notes ──
    if notes:
        parts.append(f'<text x="{svg_w/2}" y="{svg_h-24}" text-anchor="middle" font-size="11" fill="{c_label}" font-family="sans-serif" font-style="italic">{_esc(notes[:100])}</text>')

    # ── Footer ──
    parts.append(f'<text x="{svg_w-12}" y="{svg_h-10}" text-anchor="end" font-size="8" fill="#ccc" font-family="sans-serif">Empire Workroom</text>')
    parts.append('</svg>')
    return '\n'.join(parts)


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _draw_window(parts, cx, cy, w, h, c_line, c_border, c_text):
    x0, y0 = cx - w / 2, cy - h / 2
    # Outer frame
    parts.append(f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" fill="#e8e4dc" stroke="{c_border}" stroke-width="2.5" rx="2"/>')
    # Inner panes (2 panes)
    pw = (w - 16) / 2
    ph = h - 12
    parts.append(f'<rect x="{x0+6}" y="{y0+6}" width="{pw}" height="{ph}" fill="#d6e8f0" stroke="{c_border}" stroke-width="1" rx="1"/>')
    parts.append(f'<rect x="{x0+10+pw}" y="{y0+6}" width="{pw}" height="{ph}" fill="#d6e8f0" stroke="{c_border}" stroke-width="1" rx="1"/>')
    # Sill
    parts.append(f'<rect x="{x0-8}" y="{y0+h}" width="{w+16}" height="6" fill="#c9a96e" stroke="{c_border}" stroke-width="1" rx="1"/>')
    # Curtain rod
    parts.append(f'<line x1="{x0-20}" y1="{y0-8}" x2="{x0+w+20}" y2="{y0-8}" stroke="#8b7340" stroke-width="3" stroke-linecap="round"/>')
    # Drapery swoops (simplified)
    for offset in [0, w]:
        bx = x0 + offset
        parts.append(f'<path d="M{bx},{y0-8} Q{bx + (15 if offset == 0 else -15)},{y0+h*0.3} {bx + (8 if offset == 0 else -8)},{y0+h}" fill="none" stroke="{c_line}" stroke-width="1.5" stroke-dasharray="4,3"/>')


def _draw_pillow(parts, cx, cy, w, h, c_line, c_border):
    w2, h2 = w * 0.6, h * 0.6
    x0, y0 = cx - w2 / 2, cy - h2 / 2
    parts.append(f'<rect x="{x0}" y="{y0}" width="{w2}" height="{h2}" fill="#f0e6d0" stroke="{c_border}" stroke-width="2" rx="16"/>')
    # Center button
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="6" fill="{c_line}" stroke="{c_border}" stroke-width="1"/>')


def _draw_chair(parts, cx, cy, w, h, c_line, c_border):
    # Simplified chair silhouette
    seat_w, seat_h = w * 0.55, h * 0.25
    back_w, back_h = w * 0.5, h * 0.45
    sx, sy = cx - seat_w / 2, cy + h * 0.05
    bx, by = cx - back_w / 2, sy - back_h
    # Back
    parts.append(f'<rect x="{bx}" y="{by}" width="{back_w}" height="{back_h}" fill="#e8dcc8" stroke="{c_border}" stroke-width="2" rx="6"/>')
    # Seat
    parts.append(f'<rect x="{sx}" y="{sy}" width="{seat_w}" height="{seat_h}" fill="#f0e6d0" stroke="{c_border}" stroke-width="2" rx="4"/>')
    # Legs
    for lx in [sx + 8, sx + seat_w - 8]:
        parts.append(f'<line x1="{lx}" y1="{sy+seat_h}" x2="{lx}" y2="{sy+seat_h+30}" stroke="{c_border}" stroke-width="3" stroke-linecap="round"/>')


def _draw_table(parts, cx, cy, w, h, c_line, c_border):
    tw, th = w * 0.7, h * 0.12
    tx, ty = cx - tw / 2, cy - 10
    # Tabletop
    parts.append(f'<rect x="{tx}" y="{ty}" width="{tw}" height="{th}" fill="#d4b87a" stroke="{c_border}" stroke-width="2" rx="3"/>')
    # Legs
    for lx in [tx + 12, tx + tw - 12]:
        parts.append(f'<line x1="{lx}" y1="{ty+th}" x2="{lx}" y2="{ty+th+60}" stroke="{c_border}" stroke-width="3" stroke-linecap="round"/>')


def generate_drawing(
    name: str,
    description: str,
    dimensions: dict,
    item_type: str | None = None,
    notes: str = "",
) -> dict:
    """Main entry point — classify input and generate the right drawing.

    Returns: {"svg": str, "item_type": str, "name": str}
    """
    if item_type is None:
        # Auto-classify from name + description
        classify_text = f"{name} {description}"
        item_type = classify_input(classify_text)

    if item_type == "bench":
        # Route to dedicated bench renderer
        return {"svg": None, "item_type": "bench", "name": name, "route": "bench_renderer"}

    # All other types: measurement diagram
    svg = render_measurement_diagram(
        name=name,
        item_type=item_type,
        dimensions=dimensions,
        notes=notes,
    )
    return {"svg": svg, "item_type": item_type, "name": name, "route": "measurement_diagram"}
