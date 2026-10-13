"""
Client-presentation bench / banquette drawings.

Four-quadrant landscape sheet (1200×850):
  Q1 PLAN          — true straight / L / U footprint (never an unfolded strip)
  Q2 ISOMETRIC     — single solid matching that footprint
  Q3 FRONT ELEV    — dimensioned elevation
  Q4 TITLE BLOCK   — business branding + cut-list summary

Rules:
  - Every printed dimension is an imperial fraction (never a decimal)
  - Wood is cut true size
  - Foam matches wood length × width
  - Fabric cuts are labeled separately (seam allowance called out)
  - Line weights come from primitives (heavy / medium / light / hairline)
"""
from __future__ import annotations

import math
import os
import logging
from datetime import datetime
from .inches import format_inches, format_size
from .primitives import (
    BLACK, DIM_COLOR, EMPIRE_GOLD, EMPIRE_GOLD_LIGHT, FONT, GRAY, LIGHT_GRAY, WHITE,
    SW_BORDER, SW_CHANNEL, SW_DIM, SW_EXT, SW_FLOOR, SW_HEAVY, SW_LIGHT, SW_MED,
)

logger = logging.getLogger("bench_renderer")

ISO_A = 30
COS_A = math.cos(math.radians(ISO_A))
SIN_A = math.sin(math.radians(ISO_A))

BACK_T = 4
WOOD_THICK = 0.75
FOAM_SEAT_T = 4.0
FOAM_BACK_T = 2.0
FABRIC_SA = 2.0  # seam allowance each side — fabric only

LAYOUT_W = 1200
LAYOUT_H = 850
MARGIN = 18
ZONE_GAP = 24
HALF_W = (LAYOUT_W - MARGIN * 2 - ZONE_GAP) / 2
HALF_H = (LAYOUT_H - MARGIN * 2 - ZONE_GAP) / 2
Q1_X, Q1_Y, Q1_W, Q1_H = MARGIN, MARGIN, HALF_W, HALF_H
Q2_X, Q2_Y, Q2_W, Q2_H = MARGIN + HALF_W + ZONE_GAP, MARGIN, HALF_W, HALF_H
Q3_X, Q3_Y, Q3_W, Q3_H = MARGIN, MARGIN + HALF_H + ZONE_GAP, HALF_W, HALF_H
Q4_X, Q4_Y, Q4_W, Q4_H = MARGIN + HALF_W + ZONE_GAP, MARGIN + HALF_H + ZONE_GAP, HALF_W, HALF_H

CNC_MAX_X = 29
CNC_TILE_Y = 29
TILE_OVERLAP = 0.5


# ── DATA MODEL ─────────────────────────────────────────────────────

class BenchModel:
    """Encapsulates bench parameters for rendering and fabrication."""

    def __init__(
        self,
        name="Straight Bench",
        width=120,
        depth=20,
        seat_h=18,
        back_h=18,
        cushion_width=24,
        panel_style="vertical_channels",
        channel_count=6,
        client="",
        project="",
        quote_num="",
        bench_type="straight",
        long=0,
        short=0,
        back=0,
        side=0,
        side_depth=0,
        fabric_sa=FABRIC_SA,
        foam_seat_t=FOAM_SEAT_T,
        foam_back_t=FOAM_BACK_T,
        wood_t=WOOD_THICK,
    ):
        self.name = name
        self.width = float(width)
        self.depth = float(depth)
        self.seat_h = float(seat_h)
        self.back_h = float(back_h)
        self.cushion_width = float(cushion_width) if cushion_width else 24
        self.panel_style = panel_style or "vertical_channels"
        self.channel_count = int(channel_count or 6)
        self.client = client or ""
        self.project = project or ""
        self.quote_num = quote_num or ""
        self.date = datetime.now().strftime("%m/%d/%Y")
        self.bench_type = (bench_type or "straight").replace("-", "_")
        self.long = float(long or width)
        self.short = float(short or (width * 0.5))
        self.back = float(back or width)
        self.side = float(side or (width * 0.6))
        self.side_depth = float(side_depth or depth)
        self.fabric_sa = float(fabric_sa)
        self.foam_seat_t = float(foam_seat_t)
        self.foam_back_t = float(foam_back_t)
        self.wood_t = float(wood_t)

    @property
    def cushion_count(self):
        if self.cushion_width <= 0:
            return 1
        if self.bench_type == "l_shape":
            return _run_count(self.long, self.cushion_width) + _run_count(
                max(self.short - self.depth, self.cushion_width), self.cushion_width
            )
        if self.bench_type == "u_shape":
            return (
                _run_count(self.back, self.cushion_width)
                + _run_count(max(self.side - self.depth, self.cushion_width), self.cushion_width) * 2
            )
        count = self.width / self.cushion_width
        if count != int(count) and (count - int(count)) * self.cushion_width > 6:
            return math.ceil(count)
        return max(1, int(count))

    @property
    def total_height(self):
        return self.seat_h + self.back_h

    @property
    def plan_width(self):
        if self.bench_type == "l_shape":
            return self.long
        if self.bench_type == "u_shape":
            return self.back + self.side_depth * 2
        return self.width

    @property
    def plan_depth(self):
        if self.bench_type == "l_shape":
            return self.short
        if self.bench_type == "u_shape":
            return self.side
        return self.depth


class Part:
    """A fabrication part with CNC/SAW classification."""

    def __init__(self, name, width, length, thickness=0.75, kind="WOOD"):
        self.name = name
        self.width = width
        self.length = length
        self.thickness = thickness
        self.kind = kind
        self.process = "SAW"

    def classify(self):
        if self.kind != "WOOD":
            self.process = self.kind
            return self
        if self.width <= CNC_MAX_X:
            self.process = "CNC_TILE" if self.length > CNC_TILE_Y else "CNC"
        else:
            self.process = "SAW"
        return self


def _run_count(length, cushion_width):
    if cushion_width <= 0:
        return 1
    return max(1, math.ceil(length / cushion_width))


def _inches(value) -> str:
    return format_inches(value)


# ── TRUE PLAN POLYGONS (never unfolded strips) ────────────────────

def l_plan_points(long, short, depth):
    """Closed L footprint. Long along +x, short along +y, corner at the right."""
    d = min(depth, long * 0.9, short * 0.9)
    return [
        (0.0, 0.0),
        (long, 0.0),
        (long, short),
        (long - d, short),
        (long - d, d),
        (0.0, d),
    ]


def u_plan_points(back, side, depth, side_depth):
    """Closed U footprint. Opening toward +y (bottom of page). Back along y=0."""
    tw = back + side_depth * 2
    d = min(depth, side * 0.9)
    sd = min(side_depth, tw * 0.45)
    return [
        (0.0, 0.0),
        (tw, 0.0),
        (tw, side),
        (tw - sd, side),
        (tw - sd, d),
        (sd, d),
        (sd, side),
        (0.0, side),
    ]


def straight_plan_points(width, depth):
    return [(0.0, 0.0), (width, 0.0), (width, depth), (0.0, depth)]


def polygon_bounds(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)


# ── CUT LIST ──────────────────────────────────────────────────────

def _wood_foam_fabric(name, width, length, wood_t, foam_t, fabric_sa, qty=1):
    """One shop group: wood true size, foam = wood, fabric labeled separately."""
    wood = {
        "name": name,
        "kind": "WOOD",
        "label": "WOOD CUT — TRUE SIZE",
        "width": width,
        "length": length,
        "thickness": wood_t,
        "qty": qty,
        "size": format_size(width, length, wood_t),
        "note": "Cut true size. No extra.",
    }
    foam = {
        "name": f"{name} Foam",
        "kind": "FOAM",
        "label": "FOAM CUT — MATCHES WOOD",
        "width": width,
        "length": length,
        "thickness": foam_t,
        "qty": qty,
        "size": format_size(width, length, foam_t),
        "note": "Foam = wood length × width.",
    }
    fabric = {
        "name": f"{name} Cover",
        "kind": "FABRIC",
        "label": "FABRIC CUT — LABELED SEPARATELY",
        "width": width + fabric_sa * 2,
        "length": length + fabric_sa * 2,
        "thickness": None,
        "qty": qty,
        "size": format_size(width + fabric_sa * 2, length + fabric_sa * 2),
        "note": f"Fabric cut. +{_inches(fabric_sa)} seam allowance each side. Not a wood size.",
    }
    return wood, foam, fabric


def generate_cut_list(model: BenchModel) -> dict:
    """Structured cut list. Wood true size, foam = wood, fabric separate."""
    wood, foam, fabric = [], [], []

    def add(name, w, l, foam_t, qty=1):
        a, b, c = _wood_foam_fabric(name, w, l, model.wood_t, foam_t, model.fabric_sa, qty)
        wood.append(a)
        foam.append(b)
        fabric.append(c)

    if model.bench_type == "l_shape":
        wing = max(model.short - model.depth, 0)
        add("Seat Panel — Long Run", model.long, model.depth, model.foam_seat_t)
        if wing > 0:
            add("Seat Panel — Short Run", wing, model.depth, model.foam_seat_t)
        add("Back Panel — Long Run", model.long, model.back_h, model.foam_back_t)
        add("Back Panel — Short Run", model.short, model.back_h, model.foam_back_t)
        add("End Panel", model.depth, model.seat_h, model.foam_seat_t, qty=2)
    elif model.bench_type == "u_shape":
        wing = max(model.side - model.depth, 0)
        add("Seat Panel — Back Run", model.back, model.depth, model.foam_seat_t)
        if wing > 0:
            add("Seat Panel — Left Wing", wing, model.side_depth, model.foam_seat_t)
            add("Seat Panel — Right Wing", wing, model.side_depth, model.foam_seat_t)
        add("Back Panel — Back Run", model.back, model.back_h, model.foam_back_t)
        add("Back Panel — Left Wing", model.side, model.back_h, model.foam_back_t)
        add("Back Panel — Right Wing", model.side, model.back_h, model.foam_back_t)
        add("End Panel", model.side_depth, model.seat_h, model.foam_seat_t, qty=2)
    else:
        add("Seat Panel", model.width, model.depth, model.foam_seat_t)
        add("Back Panel", model.width, model.back_h, model.foam_back_t)
        add("End Panel", model.depth, model.seat_h, model.foam_seat_t, qty=2)

    return {
        "item": model.name,
        "bench_type": model.bench_type,
        "wood": wood,
        "foam": foam,
        "fabric": fabric,
        "rules": [
            "WOOD CUT — TRUE SIZE (finished length × width × thickness).",
            "FOAM CUT — MATCHES WOOD length × width. Thickness is foam only.",
            "FABRIC CUT — LABELED SEPARATELY. Includes seam allowance. Do not cut fabric to the wood size.",
        ],
    }


def model_to_parts(model):
    """Legacy Part list derived from the wood section of the cut list."""
    cuts = generate_cut_list(model)
    parts = []
    for item in cuts["wood"]:
        parts.append(
            Part(item["name"], item["width"], item["length"], item["thickness"], "WOOD").classify()
        )
    return parts


def generate_tiles(length):
    tiles = []
    start = 0
    while start < length:
        end = min(start + CNC_TILE_Y, length)
        tiles.append((round(start, 4), round(end, 4)))
        if end >= length:
            break
        start = end - TILE_OVERLAP
    return tiles


def generate_shop_sheet(model):
    """Text cut list for the shop — fractions only, three labeled sections."""
    cuts = generate_cut_list(model)
    lines = [
        f"SHOP SHEET — {model.name}",
        f"Date: {model.date}",
        f"Quote: {model.quote_num or '—'}",
        f"Type: {model.bench_type.replace('_', ' ').upper()}",
        "",
    ]
    for section, key in (
        ("WOOD CUT — TRUE SIZE", "wood"),
        ("FOAM CUT — MATCHES WOOD", "foam"),
        ("FABRIC CUT — LABELED SEPARATELY", "fabric"),
    ):
        lines.append(section)
        lines.append(f"{'PART':<28} {'QTY':>4}  {'SIZE':<28} NOTE")
        lines.append("-" * 88)
        for p in cuts[key]:
            lines.append(f"{p['name']:<28} {p['qty']:>4}  {p['size']:<28} {p['note']}")
        lines.append("")
    lines.append(f"Cushions: {model.cushion_count} @ {_inches(model.cushion_width)} each")
    lines.extend(cuts["rules"])
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
                msp.add_text(p.name, dxfattribs={"height": 1.0}).set_placement((0.5, y_offset + 0.5))
                y_offset += p.length + gap

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    doc.saveas(output_path)
    logger.info(f"DXF saved: {output_path}")
    return output_path


# ── SVG PRIMITIVES ────────────────────────────────────────────────

def _esc(txt):
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
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        f'font-family="{FONT}" font-size="{size}" fill="{fill}" '
        f'font-weight="{weight}">{_esc(txt)}</text>'
    )


def _defs(marker_id="dim-arrow"):
    return f'''<defs>
  <marker id="{marker_id}" viewBox="0 0 10 6" refX="10" refY="3"
          markerWidth="8" markerHeight="6" orient="auto-start-reverse">
    <path d="M0,0 L10,3 L0,6 Z" fill="#000"/>
  </marker>
</defs>'''


def _iso(x, y, z, ox, oy, s):
    return (
        ox + (x * COS_A - y * COS_A) * s,
        oy - (x * SIN_A + y * SIN_A) * s - z * s,
    )


def _auto_scale(dims_3d, svg_w, svg_h, margin=30):
    mx, my, mz = dims_3d
    corners = [_iso(x, y, z, 0, 0, 1) for x in [0, mx] for y in [0, my] for z in [0, mz]]
    xs = [c[0] for c in corners]
    ys = [c[1] for c in corners]
    raw_w = max(xs) - min(xs)
    raw_h = max(ys) - min(ys)
    if raw_w == 0 or raw_h == 0:
        return 1.0, svg_w / 2, svg_h / 2
    scale = min((svg_w - margin * 2) / raw_w, (svg_h - margin * 2) / raw_h)
    corners2 = [_iso(x, y, z, 0, 0, scale) for x in [0, mx] for y in [0, my] for z in [0, mz]]
    xs2 = [c[0] for c in corners2]
    ys2 = [c[1] for c in corners2]
    ox = svg_w / 2 - (max(xs2) + min(xs2)) / 2
    oy = svg_h / 2 - (max(ys2) + min(ys2)) / 2 + 5
    return scale, ox, oy


def _auto_scale_2d(w, h, area_w, area_h, margin=50, fill=0.72):
    if w == 0 or h == 0:
        return 1.0, area_w / 2, area_h / 2
    scale = min((area_w - margin * 2) / w, (area_h - margin * 2) / h) * fill
    ox = (area_w - w * scale) / 2
    oy = (area_h - h * scale) / 2
    return scale, ox, oy


def _dim_h(parts, p1, p2, label, offset_y, text_side="above"):
    gap = 3
    ext = 5
    sign = 1 if offset_y > 0 else -1
    parts.append(_line(p1[0], p1[1] + gap * sign, p1[0], p1[1] + offset_y + ext * sign, SW_EXT, DIM_COLOR))
    parts.append(_line(p2[0], p2[1] + gap * sign, p2[0], p2[1] + offset_y + ext * sign, SW_EXT, DIM_COLOR))
    d1y = p1[1] + offset_y
    d2y = p2[1] + offset_y
    parts.append(
        f'<line x1="{p1[0]:.1f}" y1="{d1y:.1f}" x2="{p2[0]:.1f}" y2="{d2y:.1f}" '
        f'stroke="{DIM_COLOR}" stroke-width="{SW_DIM}" '
        f'marker-start="url(#dim-arrow)" marker-end="url(#dim-arrow)"/>'
    )
    mx = (p1[0] + p2[0]) / 2
    my = (d1y + d2y) / 2
    text_y = my - 4 if text_side == "above" else my + 12
    parts.append(_text(mx, text_y, label, 9, weight="600", fill=DIM_COLOR))


def _dim_v(parts, p1, p2, label, offset_x, text_side="right"):
    gap = 3
    ext = 5
    sign = 1 if offset_x > 0 else -1
    parts.append(_line(p1[0] + gap * sign, p1[1], p1[0] + offset_x + ext * sign, p1[1], SW_EXT, DIM_COLOR))
    parts.append(_line(p2[0] + gap * sign, p2[1], p2[0] + offset_x + ext * sign, p2[1], SW_EXT, DIM_COLOR))
    d1x = p1[0] + offset_x
    d2x = p2[0] + offset_x
    parts.append(
        f'<line x1="{d1x:.1f}" y1="{p1[1]:.1f}" x2="{d2x:.1f}" y2="{p2[1]:.1f}" '
        f'stroke="{DIM_COLOR}" stroke-width="{SW_DIM}" '
        f'marker-start="url(#dim-arrow)" marker-end="url(#dim-arrow)"/>'
    )
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
    _dim_h(parts, _iso(x1, y, z, ox, oy, scale), _iso(x2, y, z, ox, oy, scale),
           label, 22 if below else -22, "below" if below else "above")


def _dim_iso_depth(parts, ox, oy, scale, x, y1, y2, z, label, below=True):
    _dim_h(parts, _iso(x, y1, z, ox, oy, scale), _iso(x, y2, z, ox, oy, scale),
           label, 22 if below else -22, "below" if below else "above")


def _dim_iso_height(parts, ox, oy, scale, x, y, z1, z2, label, right=True):
    _dim_v(parts, _iso(x, y, z1, ox, oy, scale), _iso(x, y, z2, ox, oy, scale),
           label, 18 if right else -18, "right" if right else "left")


def _cushion_label(parts, cx, cy, num, size=11):
    r = size * 0.7
    parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="white" stroke="{BLACK}" stroke-width="{SW_DIM}"/>')
    parts.append(_text(cx, cy + size * 0.35, f"C{num}", size, weight="bold"))


def _miter_callout(parts, x, y):
    parts.append(_line(x - 8, y - 8, x + 8, y + 8, SW_DIM))
    parts.append(_text(x + 12, y - 8, "MITER", 7, anchor="start", weight="600", fill=GRAY))


def _back_style_label(panel_style):
    return {
        "vertical_channels": "CHANNELED BACK",
        "horizontal_channels": "H-CHANNELED BACK",
        "tufted": "TUFTED BACK",
        "button_tufted": "BUTTON TUFTED BACK",
        "flat": "FLAT BACK",
    }.get(panel_style, "CHANNELED BACK")


def _draw_back_style_2d(parts, x, y, w, h, panel_style, channel_count):
    if panel_style == "flat" or w <= 2 or h <= 2:
        return
    if panel_style == "horizontal_channels":
        count = max(2, channel_count)
        for i in range(1, count):
            parts.append(_line(x + 2, y + h * i / count, x + w - 2, y + h * i / count, SW_CHANNEL, LIGHT_GRAY))
    elif panel_style in ("tufted", "button_tufted"):
        rows = max(2, channel_count // 2)
        cols = max(3, channel_count)
        for r in range(rows + 1):
            for c in range(cols + 1):
                cx = x + w * c / cols + (w / cols / 2 if r % 2 else 0)
                if cx > x + w:
                    continue
                cy = y + h * r / rows
                parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="1.5" fill="{GRAY}" stroke="none"/>')
    else:
        count = max(2, channel_count)
        for i in range(1, count):
            cx = x + w * i / count
            parts.append(_line(cx, y + 2, cx, y + h - 2, SW_CHANNEL, LIGHT_GRAY))


def _branding(item_type="banquette"):
    try:
        from .renderer_registry import get_title_block
        return get_title_block(item_type)
    except Exception:
        return {
            "company": "EMPIRE WOODCRAFT",
            "tagline": "Custom Woodwork &amp; CNC Fabrication",
            "address": "5124 Frolich Ln, Hyattsville, MD 20781",
            "contact": "(703) 213-6484 | woodcraft@empirebox.store",
        }


# ── PLAN VIEWS ────────────────────────────────────────────────────

def _plan_scaled(pts, ox, oy, scale):
    return [(ox + x * scale, oy + y * scale) for x, y in pts]


def _plan_straight(parts, ox, oy, scale, model: BenchModel):
    w = model.width * scale
    d = model.depth * scale
    bt = BACK_T * scale
    pts = _plan_scaled(straight_plan_points(model.width, model.depth), ox, oy, scale)
    parts.append(_poly(pts, SW_HEAVY, fill="#FAFAF7"))
    parts.append(_rect(ox, oy, w, bt, SW_HEAVY, fill="#F0E6C8"))
    _draw_back_style_2d(parts, ox, oy, w, bt, model.panel_style, model.channel_count)

    c_count = _run_count(model.width, model.cushion_width)
    for i in range(1, c_count):
        cx = ox + w * i / c_count
        parts.append(_line(cx, oy + bt + 2, cx, oy + d - 2, SW_LIGHT, GRAY))
    for i in range(c_count):
        _cushion_label(parts, ox + w * (i + 0.5) / c_count, oy + bt + (d - bt) / 2, i + 1)

    parts.append(_text(ox + w / 2, oy + d + 14, _back_style_label(model.panel_style), 7, fill=GRAY, weight="600"))
    _dim_2d_h(parts, ox, ox + w, oy + d + 18, _inches(model.width), 16)
    _dim_2d_v(parts, ox, oy, oy + d, _inches(model.depth), -22)


def _plan_l_shape(parts, ox, oy, scale, model: BenchModel):
    """Single closed L — not two unfolded rectangles."""
    long, short, depth = model.long, model.short, model.depth
    d = min(depth, long * 0.9, short * 0.9)
    pts = _plan_scaled(l_plan_points(long, short, depth), ox, oy, scale)
    parts.append(_poly(pts, SW_HEAVY, fill="#FAFAF7"))

    # Back bands sit on the wall edges of the true L (top + right).
    bt = BACK_T * scale
    long_s, short_s, d_s = long * scale, short * scale, d * scale
    parts.append(_rect(ox, oy, long_s, bt, SW_MED, fill="#F0E6C8"))
    parts.append(_rect(ox + long_s - bt, oy, bt, short_s, SW_MED, fill="#F0E6C8"))
    _draw_back_style_2d(parts, ox, oy, long_s, bt, model.panel_style, model.channel_count)
    _miter_callout(parts, ox + long_s - bt, oy + d_s)

    c_long = _run_count(long, model.cushion_width)
    for i in range(1, c_long):
        cx = ox + long_s * i / c_long
        parts.append(_line(cx, oy + bt + 2, cx, oy + d_s - 2, SW_LIGHT, GRAY))
    for i in range(c_long):
        _cushion_label(parts, ox + long_s * (i + 0.5) / c_long, oy + bt + (d_s - bt) / 2, i + 1)

    wing = max(short - d, 0)
    if wing > 0:
        c_wing = _run_count(wing, model.cushion_width)
        wing_x = ox + long_s - d_s + bt
        wing_y = oy + d_s
        wing_w = d_s - bt
        wing_h = wing * scale
        for i in range(1, c_wing):
            cy = wing_y + wing_h * i / c_wing
            parts.append(_line(wing_x + 2, cy, wing_x + wing_w - 2, cy, SW_LIGHT, GRAY))
        _cushion_label(parts, wing_x + wing_w / 2, wing_y + wing_h / 2, c_long + 1)

    parts.append(_text(ox + long_s / 2, oy - 8, "TRUE L-SHAPE PLAN", 8, weight="700", fill=GRAY))
    _dim_2d_h(parts, ox, ox + long_s, oy - 4, _inches(long), -16)
    _dim_2d_v(parts, ox + long_s, oy, oy + short_s, _inches(short), 20)
    _dim_2d_v(parts, ox, oy, oy + d_s, _inches(depth), -20)


def _plan_u_shape(parts, ox, oy, scale, model: BenchModel):
    """Single closed U — not three unfolded strips."""
    back, side, depth, sd = model.back, model.side, model.depth, model.side_depth
    pts_in = u_plan_points(back, side, depth, sd)
    pts = _plan_scaled(pts_in, ox, oy, scale)
    parts.append(_poly(pts, SW_HEAVY, fill="#FAFAF7"))

    tw = (back + sd * 2) * scale
    side_s = side * scale
    d_s = min(depth, side * 0.9) * scale
    sd_s = min(sd, (back + sd * 2) * 0.45) * scale
    bt = BACK_T * scale

    # Wall backs: top span + both wing sides.
    parts.append(_rect(ox + sd_s, oy, back * scale, bt, SW_MED, fill="#F0E6C8"))
    parts.append(_rect(ox, oy, bt, side_s, SW_MED, fill="#F0E6C8"))
    parts.append(_rect(ox + tw - bt, oy, bt, side_s, SW_MED, fill="#F0E6C8"))
    _draw_back_style_2d(parts, ox + sd_s, oy, back * scale, bt, model.panel_style, model.channel_count)
    _miter_callout(parts, ox + sd_s, oy + d_s)
    _miter_callout(parts, ox + tw - sd_s, oy + d_s)

    n = 1
    _cushion_label(parts, ox + sd_s / 2, oy + side_s / 2, n)
    n += 1
    c_back = _run_count(back, model.cushion_width)
    for i in range(c_back):
        _cushion_label(parts, ox + sd_s + back * scale * (i + 0.5) / c_back, oy + bt + (d_s - bt) / 2, n)
        n += 1
    _cushion_label(parts, ox + tw - sd_s / 2, oy + side_s / 2, n)

    parts.append(_text(ox + tw / 2, oy - 8, "TRUE U-SHAPE PLAN", 8, weight="700", fill=GRAY))
    _dim_2d_h(parts, ox, ox + tw, oy + side_s + 4, _inches(back + sd * 2), 16)
    _dim_2d_h(parts, ox + sd_s, ox + sd_s + back * scale, oy - 4, _inches(back), -16)
    _dim_2d_v(parts, ox, oy, oy + side_s, _inches(side), -20)
    _dim_2d_v(parts, ox + tw, oy, oy + d_s, _inches(depth), 18)


# ── ELEVATIONS ────────────────────────────────────────────────────

def _elev_front(parts, ox, oy, scale, elev_w, model: BenchModel, wing_marks=()):
    w = elev_w * scale
    sh = model.seat_h * scale
    bh = model.back_h * scale
    parts.append(_line(ox - 15, oy, ox + w + 15, oy, SW_FLOOR, GRAY, "6,3"))
    parts.append(_text(ox - 18, oy + 4, "FL", 7, anchor="end", fill=GRAY))
    parts.append(_rect(ox, oy - sh, w, sh, SW_HEAVY, fill="#FAFAF7"))
    parts.append(_rect(ox, oy - sh - bh, w, bh, SW_HEAVY, fill="#F0E6C8"))
    _draw_back_style_2d(parts, ox, oy - sh - bh, w, bh, model.panel_style, model.channel_count)
    parts.append(_line(ox, oy - sh, ox + w, oy - sh, SW_MED))
    for mark in wing_marks:
        mx = ox + mark * scale
        parts.append(_line(mx, oy, mx, oy - sh - bh, SW_LIGHT, GRAY))
    _dim_2d_h(parts, ox, ox + w, oy, _inches(elev_w), 18)
    _dim_2d_v(parts, ox + w, oy, oy - sh, f'{_inches(model.seat_h)} SH', 22)
    _dim_2d_v(parts, ox + w + 44, oy - sh, oy - sh - bh, f'{_inches(model.back_h)} BH', 22)
    _dim_2d_v(parts, ox - 4, oy, oy - sh - bh, _inches(model.seat_h + model.back_h), -24)


# ── ISOMETRIC — true solids, not overlapping boxes ────────────────

def _draw_iso_polygon_prism(parts, ox, oy, scale, pts, z0, z1, fill_top="#FAFAF7"):
    """Extrude a 2D plan polygon into a single isometric solid."""
    top = [_iso(x, y, z1, ox, oy, scale) for x, y in pts]
    bot = [_iso(x, y, z0, ox, oy, scale) for x, y in pts]
    # Visible side faces (right and front-ish edges)
    n = len(pts)
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        face = [
            _iso(a[0], a[1], z0, ox, oy, scale),
            _iso(b[0], b[1], z0, ox, oy, scale),
            _iso(b[0], b[1], z1, ox, oy, scale),
            _iso(a[0], a[1], z1, ox, oy, scale),
        ]
        parts.append(_poly(face, SW_MED, fill=WHITE))
    parts.append(_poly(top, SW_HEAVY, fill=fill_top))
    parts.append(_poly(bot, SW_LIGHT, fill="none", stroke=LIGHT_GRAY))


def _draw_iso_back_wall(parts, ox, oy, scale, x1, y1, x2, y2, z0, z1, bt=BACK_T):
    """Thin back panel along a wall segment in plan."""
    # Offset the wall inward by bt along the segment normal (approx axis-aligned).
    dx, dy = x2 - x1, y2 - y1
    if abs(dx) >= abs(dy):
        # Horizontal wall along +x, inward is +y
        quad = [(x1, y1), (x2, y1), (x2, y1 + bt), (x1, y1 + bt)]
    else:
        # Vertical wall along +y, inward is -x if we are on the right, +x if left
        inward = bt if x1 <= 0.01 else -bt
        quad = [(x1, y1), (x1 + inward, y1), (x1 + inward, y2), (x1, y2)]
    _draw_iso_polygon_prism(parts, ox, oy, scale, quad, z0, z1, fill_top="#F0E6C8")


def _build_iso(model: BenchModel, svg_w=500, svg_h=350):
    parts = []
    pw, pd, ph = model.plan_width, model.plan_depth, model.total_height
    scale, ox, oy = _auto_scale((pw, pd, ph), svg_w, svg_h)
    sh, bh = model.seat_h, model.back_h

    if model.bench_type == "l_shape":
        pts = l_plan_points(model.long, model.short, model.depth)
        _draw_iso_polygon_prism(parts, ox, oy, scale, pts, 0, sh)
        _draw_iso_back_wall(parts, ox, oy, scale, 0, 0, model.long, 0, sh, sh + bh)
        _draw_iso_back_wall(parts, ox, oy, scale, model.long, 0, model.long, model.short, sh, sh + bh)
        _dim_iso_width(parts, ox, oy, scale, 0, model.long, -3, -4, _inches(model.long), below=True)
        _dim_iso_depth(parts, ox, oy, scale, model.long + 4, 0, model.short, -3, _inches(model.short))
        _dim_iso_height(parts, ox, oy, scale, model.long + 8, model.short, 0, sh, f'{_inches(model.seat_h)} SH')
        _dim_iso_height(parts, ox, oy, scale, model.long + 8, 0, sh, sh + bh, f'{_inches(model.back_h)} BH')
    elif model.bench_type == "u_shape":
        pts = u_plan_points(model.back, model.side, model.depth, model.side_depth)
        tw = model.back + model.side_depth * 2
        _draw_iso_polygon_prism(parts, ox, oy, scale, pts, 0, sh)
        _draw_iso_back_wall(parts, ox, oy, scale, model.side_depth, 0, model.side_depth + model.back, 0, sh, sh + bh)
        _draw_iso_back_wall(parts, ox, oy, scale, 0, 0, 0, model.side, sh, sh + bh)
        _draw_iso_back_wall(parts, ox, oy, scale, tw, 0, tw, model.side, sh, sh + bh)
        _dim_iso_width(parts, ox, oy, scale, model.side_depth, model.side_depth + model.back, -3, ph + 4, _inches(model.back), below=False)
        _dim_iso_depth(parts, ox, oy, scale, -6, 0, model.side, -3, _inches(model.side))
        _dim_iso_height(parts, ox, oy, scale, tw + 6, -3, 0, sh, f'{_inches(model.seat_h)} SH')
        _dim_iso_height(parts, ox, oy, scale, tw + 6, -3, sh, sh + bh, f'{_inches(model.back_h)} BH')
    else:
        pts = straight_plan_points(model.width, model.depth)
        _draw_iso_polygon_prism(parts, ox, oy, scale, pts, 0, sh)
        _draw_iso_back_wall(parts, ox, oy, scale, 0, 0, model.width, 0, sh, sh + bh)
        _dim_iso_width(parts, ox, oy, scale, 0, model.width, model.depth + 2, -4, _inches(model.width), below=True)
        _dim_iso_depth(parts, ox, oy, scale, model.width + 4, 0, model.depth, -3, _inches(model.depth))
        _dim_iso_height(parts, ox, oy, scale, model.width + 8, -3, 0, sh, f'{_inches(model.seat_h)} SH')
        _dim_iso_height(parts, ox, oy, scale, model.width + 8, model.depth, sh, sh + bh, f'{_inches(model.back_h)} BH')
    return parts


# ── TITLE BLOCK ──────────────────────────────────────────────────

def _title_block(parts, x, y, w, h, model: BenchModel, dims_text, cuts):
    brand = _branding("banquette")
    parts.append(_rect(x, y, w, h, SW_BORDER))
    parts.append(_rect(x, y, w, 5, 0, fill=EMPIRE_GOLD, stroke="none"))
    parts.append(_rect(x + 3, y + 8, w - 6, h - 11, 0.5))

    parts.append(_text(x + w / 2, y + 28, brand.get("company", "EMPIRE WOODCRAFT"), 16, weight="bold"))
    parts.append(_text(x + w / 2, y + 42, brand.get("tagline", ""), 7, fill=GRAY))
    parts.append(_text(x + w / 2, y + 54, brand.get("address", ""), 7, fill=GRAY))
    parts.append(_text(x + w / 2, y + 64, brand.get("contact", ""), 7, fill=GRAY))
    parts.append(_line(x + 15, y + 70, x + w - 15, y + 70, 0.5, LIGHT_GRAY))

    row_y = y + 86
    rows = [
        ("ITEM:", (model.name or "BENCH").upper()),
        ("TYPE:", model.bench_type.upper().replace("_", " ")),
        ("DIMENSIONS:", dims_text),
        ("CUSHIONS:", f"{model.cushion_count} @ {_inches(model.cushion_width)} each"),
        ("BACK STYLE:", _back_style_label(model.panel_style)),
    ]
    if model.client:
        rows.append(("CLIENT:", model.client.upper()))
    if model.project:
        rows.append(("PROJECT:", model.project.upper()))
    if model.quote_num:
        rows.append(("QUOTE:", model.quote_num))
    rows.append(("DATE:", model.date))
    rows.append(("DRAWN BY:", "MAX AI / Empire Drawing Studio"))

    for label, value in rows:
        parts.append(_text(x + 14, row_y, label, 8, anchor="start", weight="bold"))
        parts.append(_text(x + 88, row_y, value, 8, anchor="start"))
        row_y += 15

    # Compact cut-list legend
    parts.append(_rect(x + 10, y + h - 78, w - 20, 68, 0.5, fill="#FAFAFA", stroke=LIGHT_GRAY))
    parts.append(_rect(x + 10, y + h - 78, w - 20, 14, 0, fill=EMPIRE_GOLD_LIGHT, stroke="none"))
    parts.append(_text(x + w / 2, y + h - 67, "CUT LIST  ·  WOOD TRUE SIZE  ·  FOAM = WOOD  ·  FABRIC SEPARATE", 7, weight="bold"))
    legend_y = y + h - 50
    for section, items, color in (
        ("WOOD", cuts["wood"][:2], BLACK),
        ("FOAM", cuts["foam"][:2], GRAY),
        ("FABRIC", cuts["fabric"][:2], "#8a5a00"),
    ):
        if not items:
            continue
        sample = items[0]
        parts.append(_text(x + 18, legend_y, f"{section}: {sample['name']}  {sample['size']}", 7, anchor="start", fill=color))
        legend_y += 12


def _view_frame(parts, x, y, w, h, label):
    parts.append(_rect(x, y, w, h, 0.5, stroke=GRAY))
    parts.append(_text(x + w / 2, y + 14, label, 10, weight="bold"))


def _wrap_svg_raw(parts, svg_w, svg_h):
    body = "\n  ".join(parts)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}" '
        f'width="{svg_w}" height="{svg_h}">\n  {body}\n</svg>'
    )


# ── COMPOSITION ───────────────────────────────────────────────────

def _compose(model: BenchModel, dims_text: str) -> str:
    cuts = generate_cut_list(model)
    parts = [_defs()]
    parts.append(f'<rect width="{LAYOUT_W}" height="{LAYOUT_H}" fill="white"/>')
    parts.append(_rect(4, 4, LAYOUT_W - 8, LAYOUT_H - 8, SW_BORDER))
    parts.append(_rect(8, 8, LAYOUT_W - 16, LAYOUT_H - 16, 0.5))

    # Q1 PLAN
    _view_frame(parts, Q1_X, Q1_Y, Q1_W, Q1_H, "PLAN VIEW")
    plan_scale, plan_ox, plan_oy = _auto_scale_2d(model.plan_width, model.plan_depth, Q1_W - 20, Q1_H - 70)
    plan_group = []
    if model.bench_type == "l_shape":
        _plan_l_shape(plan_group, plan_ox + 10, plan_oy + 16, plan_scale, model)
    elif model.bench_type == "u_shape":
        _plan_u_shape(plan_group, plan_ox + 10, plan_oy + 16, plan_scale, model)
    else:
        _plan_straight(plan_group, plan_ox + 10, plan_oy + 16, plan_scale, model)
    parts.append(f'<g transform="translate({Q1_X:.0f},{Q1_Y + 18:.0f})">')
    parts.extend(plan_group)
    parts.append("</g>")

    # Q2 ISO
    _view_frame(parts, Q2_X, Q2_Y, Q2_W, Q2_H, "ISOMETRIC VIEW")
    iso = _build_iso(model, svg_w=Q2_W - 20, svg_h=Q2_H - 30)
    parts.append(f'<g transform="translate({Q2_X + 10:.0f},{Q2_Y + 20:.0f})">')
    parts.extend(iso)
    parts.append("</g>")

    # Q3 ELEV
    _view_frame(parts, Q3_X, Q3_Y, Q3_W, Q3_H, "FRONT ELEVATION")
    elev_w = model.plan_width
    elev_scale, elev_ox, elev_oy = _auto_scale_2d(elev_w, model.total_height, Q3_W - 20, Q3_H - 70)
    ground = elev_oy + model.total_height * elev_scale + 10
    marks = []
    if model.bench_type == "u_shape":
        marks = [model.side_depth, elev_w - model.side_depth]
    elev_group = []
    _elev_front(elev_group, elev_ox + 10, ground, elev_scale, elev_w, model, wing_marks=marks)
    parts.append(f'<g transform="translate({Q3_X:.0f},{Q3_Y + 18:.0f})">')
    parts.extend(elev_group)
    parts.append("</g>")

    # Q4 TITLE
    _title_block(parts, Q4_X, Q4_Y, Q4_W, Q4_H, model, dims_text, cuts)
    return _wrap_svg_raw(parts, LAYOUT_W, LAYOUT_H)


def _normalize_width(width_in, **kw):
    if width_in < 50 and "rate" not in kw:
        return width_in * 12
    return width_in


# ── PUBLIC RENDER FUNCTIONS (signatures preserved) ────────────────

def render_straight(name, width_in, depth_in=20, seat_h_in=18, back_h_in=18,
                    quote_num="", svg_w=600, svg_h=400,
                    cushion_width=24, panel_style="vertical_channels", channel_count=6,
                    client="", project="", **kw):
    width_in = _normalize_width(width_in, **kw)
    model = BenchModel(
        name=name, width=width_in, depth=depth_in, seat_h=seat_h_in, back_h=back_h_in,
        cushion_width=cushion_width, panel_style=panel_style, channel_count=channel_count,
        client=client, project=project, quote_num=quote_num, bench_type="straight",
    )
    dims_text = f'{_inches(width_in)} W × {_inches(depth_in)} D × {_inches(seat_h_in)} SH × {_inches(back_h_in)} BH'
    return _compose(model, dims_text)


def render_l_shape(name, long_in, short_in=0, depth_in=20, seat_h_in=18, back_h_in=18,
                   quote_num="", svg_w=600, svg_h=400,
                   cushion_width=24, panel_style="vertical_channels", channel_count=6,
                   client="", project="", **kw):
    if long_in < 50:
        lf = long_in
        long_in = lf * 0.6 * 12
        if short_in == 0 or short_in < 10:
            short_in = lf * 0.4 * 12
    if short_in == 0:
        short_in = long_in * 0.5
    model = BenchModel(
        name=name, width=long_in, depth=depth_in, seat_h=seat_h_in, back_h=back_h_in,
        cushion_width=cushion_width, panel_style=panel_style, channel_count=channel_count,
        client=client, project=project, quote_num=quote_num, bench_type="l_shape",
        long=long_in, short=short_in,
    )
    dims_text = (
        f'{_inches(long_in)} L × {_inches(short_in)} S × {_inches(depth_in)} D × '
        f'{_inches(seat_h_in)} SH × {_inches(back_h_in)} BH'
    )
    return _compose(model, dims_text)


def render_u_shape(name, back_in, side_in=0, depth_in=20, side_depth_in=0,
                   seat_h_in=18, back_h_in=18, multiplier=1,
                   quote_num="", svg_w=600, svg_h=400,
                   cushion_width=24, panel_style="vertical_channels", channel_count=6,
                   client="", project="", **kw):
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
    model = BenchModel(
        name=name, width=back_in + side_depth_in * 2, depth=depth_in,
        seat_h=seat_h_in, back_h=back_h_in, cushion_width=cushion_width,
        panel_style=panel_style, channel_count=channel_count,
        client=client, project=project, quote_num=quote_num, bench_type="u_shape",
        back=back_in, side=side_in, side_depth=side_depth_in,
    )
    dims_text = (
        f'{_inches(back_in)} B × {_inches(side_in)} S × {_inches(depth_in)} D × '
        f'{_inches(side_depth_in)} SD × {_inches(seat_h_in)} SH × {_inches(back_h_in)} BH'
    )
    return _compose(model, dims_text)


def model_from_render_args(bench_type, **kwargs) -> BenchModel:
    """Build a BenchModel from the same kwargs the public renderers accept."""
    if bench_type == "l_shape":
        long_in = kwargs.get("long_in", kwargs.get("width_in", 120))
        short_in = kwargs.get("short_in", 60)
        if long_in < 50:
            long_in = long_in * 0.6 * 12
            if short_in < 10:
                short_in = kwargs.get("long_in", 10) * 0.4 * 12
        return BenchModel(
            name=kwargs.get("name", "Bench"), width=long_in,
            depth=kwargs.get("depth_in", 20), seat_h=kwargs.get("seat_h_in", 18),
            back_h=kwargs.get("back_h_in", 18), bench_type="l_shape",
            long=long_in, short=short_in, quote_num=kwargs.get("quote_num", ""),
            client=kwargs.get("client", ""), project=kwargs.get("project", ""),
        )
    if bench_type == "u_shape":
        back_in = kwargs.get("back_in", kwargs.get("width_in", 84))
        side_in = kwargs.get("side_in", 60)
        side_depth = kwargs.get("side_depth_in", kwargs.get("depth_in", 20))
        if back_in < 50:
            back_in = back_in * 0.45 * 12
            if side_in == 0:
                side_in = 36
        return BenchModel(
            name=kwargs.get("name", "Bench"), width=back_in + side_depth * 2,
            depth=kwargs.get("depth_in", 20), seat_h=kwargs.get("seat_h_in", 18),
            back_h=kwargs.get("back_h_in", 18), bench_type="u_shape",
            back=back_in, side=side_in, side_depth=side_depth,
            quote_num=kwargs.get("quote_num", ""),
            client=kwargs.get("client", ""), project=kwargs.get("project", ""),
        )
    width = kwargs.get("width_in", 120)
    if width < 50:
        width *= 12
    return BenchModel(
        name=kwargs.get("name", "Bench"), width=width,
        depth=kwargs.get("depth_in", 20), seat_h=kwargs.get("seat_h_in", 18),
        back_h=kwargs.get("back_h_in", 18), bench_type="straight",
        quote_num=kwargs.get("quote_num", ""),
        client=kwargs.get("client", ""), project=kwargs.get("project", ""),
    )


# ── CUT LIST SHEET (second PDF page) ──────────────────────────────

def render_cut_list_sheet(cuts: dict, name: str = "", quote_num: str = "") -> str:
    """Presentation-grade shop sheet: wood / foam / fabric in three columns."""
    svg_w, svg_h = 1200, 850
    parts = [_defs("cut-dim-arrow")]
    parts.append(f'<rect width="{svg_w}" height="{svg_h}" fill="white"/>')
    parts.append(_rect(8, 8, svg_w - 16, svg_h - 16, SW_BORDER))
    brand = _branding("banquette")
    parts.append(_rect(20, 20, svg_w - 40, 8, 0, fill=EMPIRE_GOLD, stroke="none"))
    parts.append(_text(svg_w / 2, 52, brand.get("company", "EMPIRE WOODCRAFT"), 20, weight="bold"))
    parts.append(_text(svg_w / 2, 72, "FABRICATION CUT LIST", 13, weight="bold", fill="#8a5a00"))
    parts.append(_text(svg_w / 2, 90, _esc((name or cuts.get("item") or "BENCH").upper()), 12, weight="600"))
    if quote_num:
        parts.append(_text(svg_w / 2, 106, f"QUOTE {quote_num}", 10, fill=GRAY))

    col_w = 360
    col_x = [30, 420, 810]
    sections = [
        ("WOOD CUT — TRUE SIZE", cuts.get("wood") or [], "Finished wood. Cut true size. No extra."),
        ("FOAM CUT — MATCHES WOOD", cuts.get("foam") or [], "Foam length × width equals the wood it sits on."),
        ("FABRIC CUT — LABELED SEPARATELY", cuts.get("fabric") or [], "Do not cut fabric to the wood size."),
    ]
    for i, (title, items, note) in enumerate(sections):
        x = col_x[i]
        parts.append(_rect(x, 124, col_w, 680, 0.8))
        parts.append(_rect(x, 124, col_w, 36, 0, fill=EMPIRE_GOLD_LIGHT, stroke="none"))
        parts.append(_text(x + col_w / 2, 148, title, 11, weight="bold"))
        parts.append(_text(x + 12, 176, note, 8, anchor="start", fill=GRAY))
        y = 198
        parts.append(_text(x + 12, y, "PART", 8, anchor="start", weight="bold", fill=GRAY))
        parts.append(_text(x + 220, y, "QTY", 8, anchor="start", weight="bold", fill=GRAY))
        parts.append(_text(x + 260, y, "SIZE", 8, anchor="start", weight="bold", fill=GRAY))
        y += 8
        parts.append(_line(x + 10, y, x + col_w - 10, y, 0.5, LIGHT_GRAY))
        y += 18
        for item in items:
            parts.append(_text(x + 12, y, item["name"], 9, anchor="start", weight="600"))
            parts.append(_text(x + 226, y, str(item["qty"]), 9, anchor="start"))
            parts.append(_text(x + 260, y, item["size"], 9, anchor="start"))
            y += 14
            parts.append(_text(x + 12, y, item["note"], 7, anchor="start", fill=GRAY))
            y += 20
            if y > 760:
                parts.append(_text(x + 12, y, "…", 10, anchor="start"))
                break

    parts.append(_text(svg_w / 2, 830, " · ".join(cuts.get("rules") or []), 8, fill=GRAY))
    return _wrap_svg_raw(parts, svg_w, svg_h)


# ── PROJECT SHEET ────────────────────────────────────────────────

def render_project_sheet(benches, title="BUILT-IN BENCHES", quote_num="",
                         svg_w=1100, svg_h=850):
    parts = [_defs()]
    parts.append(f'<rect width="{svg_w}" height="{svg_h}" fill="white"/>')
    parts.append(_rect(8, 8, svg_w - 16, svg_h - 16, SW_BORDER))
    parts.append(_rect(14, 14, svg_w - 28, svg_h - 28, 0.5))
    brand = _branding("banquette")

    tb_w, tb_h = 300, 72
    tb_x = svg_w - 14 - tb_w
    tb_y = svg_h - 14 - tb_h
    parts.append(_rect(tb_x, tb_y, tb_w, tb_h, SW_MED))
    parts.append(_rect(tb_x, tb_y, tb_w, 5, 0, fill=EMPIRE_GOLD, stroke="none"))
    parts.append(_text(tb_x + tb_w / 2, tb_y + 26, brand.get("company", "EMPIRE WOODCRAFT"), 14, weight="bold"))
    parts.append(_text(tb_x + tb_w / 2, tb_y + 44, title, 11, weight="bold"))
    if quote_num:
        parts.append(_text(tb_x + tb_w / 2, tb_y + 60, quote_num, 10))

    cols = 2
    rows = 2 if len(benches) > 2 else 1
    content_y_end = tb_y - 8 if rows == 2 else svg_h - 14
    area_x, area_y = 20, 20
    area_w = svg_w - 40
    area_h = content_y_end - area_y
    cell_w = area_w / cols
    cell_h = area_h / rows
    if cols > 1:
        parts.append(_line(area_x + cell_w, area_y, area_x + cell_w, area_y + area_h, 0.5))
    if rows > 1:
        parts.append(_line(area_x, area_y + cell_h, area_x + area_w, area_y + cell_h, 0.5))

    for idx, bench in enumerate(benches[:4]):
        col, row = idx % cols, idx // cols
        cx = area_x + col * cell_w + 8
        cy = area_y + row * cell_h + 4
        draw_w, draw_h = cell_w - 16, cell_h - 28
        b_type = bench.get("type", "straight")
        b_name = bench.get("name", "Bench")
        qty = bench.get("qty", 1)
        model = model_from_render_args(
            b_type,
            name=b_name,
            width_in=bench.get("width_in", 120),
            long_in=bench.get("long_in", bench.get("width_in", 120)),
            short_in=bench.get("short_in", 60),
            back_in=bench.get("back_in", bench.get("width_in", 84)),
            side_in=bench.get("side_in", 60),
            depth_in=bench.get("depth_in", 20),
            side_depth_in=bench.get("side_depth_in", bench.get("depth_in", 20)),
            seat_h_in=bench.get("seat_h_in", 18),
            back_h_in=bench.get("back_h_in", 18),
        )
        bp = _build_iso(model, svg_w=draw_w, svg_h=draw_h)
        qty_str = f" ({qty}X)" if qty > 1 else ""
        parts.append(f'<g transform="translate({cx:.0f},{cy:.0f})">')
        parts.append(_text(draw_w / 2, 12, f"{b_name.upper()}{qty_str}", 11, weight="bold"))
        parts.extend(bp)
        parts.append("</g>")

    return _wrap_svg_raw(parts, svg_w, svg_h)


def render_quote_drawings(line_items, quote_num=""):
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
    """Convert list of drawing dicts to a multi-page PDF. Writes only to output_path."""
    from weasyprint import HTML as WeasyHTML
    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    html = (
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        '<style>@page{size:letter landscape;margin:0.3in}'
        'body{margin:0}.pg{page-break-after:always;display:flex;'
        'align-items:center;justify-content:center;min-height:92vh}'
        '.pg:last-child{page-break-after:auto}</style></head><body>'
    )
    for d in drawings:
        html += f'<div class="pg">{d["svg"]}</div>'
    html += "</body></html>"
    WeasyHTML(string=html).write_pdf(output_path)
    return output_path


# Compat aliases used by older isometric callers
def _build_straight(name, width_in, depth_in, seat_h_in, back_h_in, quote_num="",
                    svg_w=500, svg_h=350, panel_style="vertical_channels", channel_count=6, **kw):
    model = BenchModel(name=name, width=width_in, depth=depth_in, seat_h=seat_h_in,
                       back_h=back_h_in, panel_style=panel_style, channel_count=channel_count,
                       quote_num=quote_num, bench_type="straight")
    return _build_iso(model, svg_w, svg_h), 1, 0, 0


def _build_l_shape(name, long_in, short_in, depth_in, seat_h_in, back_h_in, quote_num="",
                   svg_w=500, svg_h=350, panel_style="vertical_channels", channel_count=6, **kw):
    model = BenchModel(name=name, width=long_in, depth=depth_in, seat_h=seat_h_in,
                       back_h=back_h_in, panel_style=panel_style, channel_count=channel_count,
                       quote_num=quote_num, bench_type="l_shape", long=long_in, short=short_in)
    return _build_iso(model, svg_w, svg_h), 1, 0, 0


def _build_u_shape(name, back_in, side_in, depth_in, side_depth_in, seat_h_in, back_h_in,
                   quote_num="", svg_w=500, svg_h=350,
                   panel_style="vertical_channels", channel_count=6, **kw):
    model = BenchModel(name=name, width=back_in + side_depth_in * 2, depth=depth_in,
                       seat_h=seat_h_in, back_h=back_h_in, panel_style=panel_style,
                       channel_count=channel_count, quote_num=quote_num, bench_type="u_shape",
                       back=back_in, side=side_in, side_depth=side_depth_in)
    return _build_iso(model, svg_w, svg_h), 1, 0, 0
