"""
General architectural drawing service — smart classifier + per-type renderers.

Item types route to appropriate view counts:
  bench     → 4 views (bench_renderer.py — plan + iso + elevation + title)
  window    → 1 view  (front view with frame + treatment)
  chair     → 2 views (front + side elevation)
  sofa      → 2 views (front + plan)
  cushion   → 1 view  (top-down plan)
  ottoman   → 2 views (front + plan)
  headboard → 1 view  (front elevation)
  millwork  → 3 views (front + side + plan)
  table     → 2 views (front + plan)
  generic   → 1 view  (measurement diagram)
"""
import re
import math

# ── Shared constants (match bench_renderer.py style) ─────────────
FONT = "Arial, Helvetica, sans-serif"
BLACK = "#000000"
GRAY = "#666666"
LIGHT_GRAY = "#CCCCCC"
SW_HEAVY = 2.5
SW_MED = 1.5
SW_DIM = 0.75
SW_LIGHT = 0.4
SW_BORDER = 2.0
SW_EXT = 0.5

BRANDING = {
    "name": "EMPIRE WORKROOM",
    "tagline": "Custom Upholstery &amp; Window Treatments",
    "address": "5124 Frolich Ln, Hyattsville, MD 20781",
}


# ── SMART CLASSIFIER ─────────────────────────────────────────────

ITEM_CLASSIFICATION = {
    "bench": {
        "keywords": ["bench", "banquette", "booth", "restaurant seating",
                     "built-in seating", "built-in bench", "dining bench",
                     "entry bench", "window seat bench", "nook seating",
                     "breakfast nook"],
        "renderer": "bench",
        "views": 4,
    },
    "window": {
        "keywords": ["window", "shade", "roman shade", "roller shade",
                     "drapery", "drape", "curtain", "blind", "valance",
                     "cornice", "sheer", "shutter", "ripplefold",
                     "pinch pleat", "rod pocket", "grommet", "window treatment"],
        "renderer": "window",
        "views": 1,
    },
    "chair": {
        "keywords": ["chair", "dining chair", "accent chair", "wingback",
                     "club chair", "arm chair", "armchair", "side chair",
                     "bar stool", "barstool"],
        "renderer": "chair",
        "views": 2,
    },
    "sofa": {
        "keywords": ["sofa", "couch", "loveseat", "sectional", "chaise",
                     "settee", "daybed"],
        "renderer": "sofa",
        "views": 2,
    },
    "cushion": {
        "keywords": ["cushion", "pillow", "seat pad", "foam", "bolster",
                     "throw pillow", "lumbar", "seat cushion"],
        "renderer": "cushion",
        "views": 1,
    },
    "ottoman": {
        "keywords": ["ottoman", "footstool", "pouf", "storage ottoman"],
        "renderer": "ottoman",
        "views": 2,
    },
    "headboard": {
        "keywords": ["headboard", "bed frame", "upholstered headboard"],
        "renderer": "headboard",
        "views": 1,
    },
    "millwork": {
        "keywords": ["cabinet", "shelving", "shelf", "wall unit", "bookcase",
                     "bar", "casework", "built-in cabinet", "vanity",
                     "entertainment center", "credenza", "wardrobe", "closet"],
        "renderer": "millwork",
        "views": 3,
    },
    "table": {
        "keywords": ["table", "desk", "console", "coffee table", "end table",
                     "dining table", "work table"],
        "renderer": "table",
        "views": 2,
    },
}

# Legacy alias map for backward compat
LEGACY_TYPE_MAP = {
    "pillow": "cushion",
    "upholstery": "chair",
}


def classify_item(user_text: str = "", item_name: str = "",
                  description: str = "", filename: str = "") -> dict:
    """Classify what type of item to draw.

    Priority: user_text > item_name > description > filename.
    Returns: {"type", "renderer", "views", "confidence"}
    """
    all_text = f"{user_text} {item_name} {description} {filename}".lower()

    best_match = None
    best_score = 0

    for item_type, config in ITEM_CLASSIFICATION.items():
        score = sum(1 for kw in config["keywords"] if kw in all_text)
        if score > best_score:
            best_score = score
            best_match = item_type

    if best_match and best_score > 0:
        config = ITEM_CLASSIFICATION[best_match]
        return {
            "type": best_match,
            "renderer": config["renderer"],
            "views": config["views"],
            "confidence": "high" if best_score >= 2 else "medium",
        }

    return {
        "type": "generic",
        "renderer": "generic",
        "views": 1,
        "confidence": "low",
    }


def classify_input(text: str) -> str:
    """Legacy compat wrapper — returns just the type string."""
    result = classify_item(user_text=text)
    raw = result["type"]
    return raw


# ── SVG HELPERS ───────────────────────────────────────────────────

def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _defs():
    return '''<defs>
  <marker id="dim-arrow" viewBox="0 0 10 6" refX="10" refY="3"
          markerWidth="8" markerHeight="6" orient="auto-start-reverse">
    <path d="M0,0 L10,3 L0,6 Z" fill="#000"/>
  </marker>
</defs>'''


def _line(x1, y1, x2, y2, sw=SW_MED, stroke=BLACK):
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{sw}"/>'


def _rect(x, y, w, h, sw=SW_MED, fill="none", stroke=BLACK):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


def _text(x, y, txt, size=10, anchor="middle", weight="normal", fill=BLACK, rotate=0):
    rot = f' transform="rotate({rotate},{x:.1f},{y:.1f})"' if rotate else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        f'font-family="{FONT}" font-size="{size}" fill="{fill}" '
        f'font-weight="{weight}"{rot}>{txt}</text>'
    )


def _dim_h(parts, x1, x2, y, label, offset_y=20):
    """Horizontal dimension line."""
    sign = 1 if offset_y > 0 else -1
    gap = 3
    ext = 5
    # Extension lines
    parts.append(_line(x1, y + gap * sign, x1, y + offset_y + ext * sign, SW_EXT))
    parts.append(_line(x2, y + gap * sign, x2, y + offset_y + ext * sign, SW_EXT))
    # Dimension line with arrows
    dy = y + offset_y
    parts.append(
        f'<line x1="{x1:.1f}" y1="{dy:.1f}" x2="{x2:.1f}" y2="{dy:.1f}" '
        f'stroke="{BLACK}" stroke-width="{SW_DIM}" '
        f'marker-start="url(#dim-arrow)" marker-end="url(#dim-arrow)"/>'
    )
    # Label
    mx = (x1 + x2) / 2
    ty = dy - 4 if offset_y < 0 else dy + 12
    parts.append(_text(mx, ty, label, 9, weight="600"))


def _dim_v(parts, x, y1, y2, label, offset_x=20):
    """Vertical dimension line."""
    sign = 1 if offset_x > 0 else -1
    gap = 3
    ext = 5
    parts.append(_line(x + gap * sign, y1, x + offset_x + ext * sign, y1, SW_EXT))
    parts.append(_line(x + gap * sign, y2, x + offset_x + ext * sign, y2, SW_EXT))
    dx = x + offset_x
    parts.append(
        f'<line x1="{dx:.1f}" y1="{y1:.1f}" x2="{dx:.1f}" y2="{y2:.1f}" '
        f'stroke="{BLACK}" stroke-width="{SW_DIM}" '
        f'marker-start="url(#dim-arrow)" marker-end="url(#dim-arrow)"/>'
    )
    mx = dx + (8 if offset_x > 0 else -8)
    my = (y1 + y2) / 2 + 3
    parts.append(_text(mx, my, label, 9, weight="600", rotate=-90))


def _title_block_small(parts, x, y, w, h, name="", item_type=""):
    """Compact title block for non-bench drawings."""
    parts.append(_rect(x, y, w, h, SW_MED))
    parts.append(_text(x + w / 2, y + 18, BRANDING["name"], 14, weight="bold"))
    parts.append(_text(x + w / 2, y + 32, BRANDING["tagline"], 8, fill=GRAY))
    if name:
        parts.append(_line(x + 10, y + 40, x + w - 10, y + 40, 0.5))
        parts.append(_text(x + w / 2, y + 54, _esc(name.upper()), 11, weight="bold"))
    if item_type:
        parts.append(_text(x + w / 2, y + 68, item_type.upper().replace("_", " "), 8, fill=GRAY))
    parts.append(_text(x + w / 2, y + h - 8, BRANDING["address"], 7, fill=GRAY))


def _view_label(parts, x, y, w, label):
    """Label for a view section."""
    parts.append(_text(x + w / 2, y + 14, label, 10, weight="bold"))


def _wrap_svg(parts, w, h):
    body = "\n  ".join(parts)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}">\n  {body}\n</svg>'
    )


def _parse_dim(dimensions: dict, key: str, default: float = 0) -> float:
    """Extract a numeric dimension value from a dict, handling strings like '72\"'."""
    for k, v in dimensions.items():
        if key.lower() in k.lower():
            val_str = str(v).strip().rstrip('"\'').strip()
            try:
                return float(re.sub(r'[^0-9.]', '', val_str))
            except (ValueError, TypeError):
                pass
    return default


# ── WINDOW RENDERER (1 view) ─────────────────────────────────────

def render_window(params: dict) -> str:
    """Single clean front-view window diagram. Portrait 850x1100."""
    name = params.get("name", "Window Treatment")
    width = _parse_dim(params.get("dimensions", {}), "width", params.get("width", 72))
    height = _parse_dim(params.get("dimensions", {}), "height", params.get("height", 48))
    drop = _parse_dim(params.get("dimensions", {}), "drop", params.get("drop", 0))
    treatment = params.get("treatment_type", "")
    mount = params.get("mount_type", "inside")
    notes = params.get("notes", "")

    svg_w, svg_h = 850, 1100
    parts = [_defs()]
    parts.append(f'<rect width="{svg_w}" height="{svg_h}" fill="white"/>')
    parts.append(_rect(6, 6, svg_w - 12, svg_h - 12, SW_BORDER))
    parts.append(_rect(10, 10, svg_w - 20, svg_h - 20, 0.5))

    # View label
    _view_label(parts, 0, 30, svg_w, "FRONT VIEW")

    # Scale to fit
    draw_area_w = svg_w - 200
    draw_area_h = svg_h - 380
    eff_h = drop if drop > 0 else height
    scale = min(draw_area_w / max(width, 1), draw_area_h / max(eff_h, 1))
    scale = min(scale, 6)

    w_s = width * scale
    h_s = eff_h * scale
    cx = svg_w / 2
    cy = 300

    x0 = cx - w_s / 2
    y0 = cy - h_s / 2

    # Window frame (double lines)
    frame_pad = 8
    parts.append(_rect(x0 - frame_pad, y0 - frame_pad, w_s + frame_pad * 2, h_s + frame_pad * 2, SW_HEAVY))
    parts.append(_rect(x0, y0, w_s, h_s, SW_MED))

    # Window panes (2 panes)
    pw = (w_s - 6) / 2
    parts.append(_rect(x0 + 2, y0 + 2, pw, h_s - 4, SW_LIGHT, fill="#f0f5fa"))
    parts.append(_rect(x0 + pw + 4, y0 + 2, pw, h_s - 4, SW_LIGHT, fill="#f0f5fa"))

    # Treatment based on type
    treatment_lower = (treatment or name).lower()
    if any(kw in treatment_lower for kw in ["roman", "shade", "roller"]):
        # Roman shade — horizontal pleats
        pleat_count = max(int(eff_h / 6), 4)
        pleat_h = h_s / pleat_count
        for i in range(1, pleat_count):
            py = y0 + i * pleat_h
            parts.append(_line(x0 + 4, py, x0 + w_s - 4, py, SW_LIGHT, LIGHT_GRAY))
        # Bottom hem
        parts.append(_line(x0 + 4, y0 + h_s - 2, x0 + w_s - 4, y0 + h_s - 2, SW_MED))
        parts.append(_text(cx, y0 + h_s / 2, "ROMAN SHADE", 10, fill=GRAY))
    elif any(kw in treatment_lower for kw in ["drape", "drapery", "curtain", "ripple", "pleat"]):
        # Drapery — vertical folds
        rod_y = y0 - frame_pad - 10
        parts.append(_line(x0 - 30, rod_y, x0 + w_s + 30, rod_y, 3))
        # Curtain folds
        fold_count = max(int(width / 4), 6)
        fold_w = w_s / fold_count
        for i in range(fold_count):
            fx = x0 + i * fold_w + fold_w / 2
            parts.append(_line(fx, rod_y + 4, fx, y0 + h_s + 10, SW_LIGHT, LIGHT_GRAY))
        # Side panels
        panel_w = w_s * 0.15
        parts.append(_rect(x0 - 2, rod_y + 4, panel_w, h_s + frame_pad + 14, SW_MED, fill="#f5f0eb"))
        parts.append(_rect(x0 + w_s - panel_w + 2, rod_y + 4, panel_w, h_s + frame_pad + 14, SW_MED, fill="#f5f0eb"))
        parts.append(_text(cx, y0 + h_s / 2, "DRAPERY", 10, fill=GRAY))
    elif any(kw in treatment_lower for kw in ["valance", "cornice"]):
        # Valance/cornice — top treatment
        val_h = min(h_s * 0.25, 40)
        parts.append(_rect(x0 - 10, y0 - frame_pad - val_h, w_s + 20, val_h, SW_HEAVY, fill="#f5f0eb"))
        parts.append(_text(cx, y0 - frame_pad - val_h / 2 + 4, "VALANCE", 9, fill=GRAY))
    else:
        # Generic window treatment
        parts.append(_text(cx, y0 + h_s / 2, "WINDOW TREATMENT", 10, fill=GRAY))

    # Sill
    sill_y = y0 + h_s + frame_pad
    parts.append(_rect(x0 - 16, sill_y, w_s + 32, 6, SW_MED, fill="#e8e4dc"))

    # Dimensions
    _dim_h(parts, x0, x0 + w_s, sill_y + 6, f'{width:.0f}"', 22)
    _dim_v(parts, x0 + w_s + frame_pad, y0, y0 + h_s, f'{eff_h:.0f}"', 30)
    if mount == "outside":
        _dim_v(parts, x0 - frame_pad, y0 - frame_pad, y0 + h_s + frame_pad, f'{eff_h + frame_pad * 2 / scale:.0f}" O.M.', -30)

    # Notes
    if notes:
        parts.append(_text(cx, svg_h - 200, _esc(notes[:100]), 10, fill=GRAY))

    # Title block
    _title_block_small(parts, svg_w / 2 - 160, svg_h - 170, 320, 130, name, "Window Treatment")

    return _wrap_svg(parts, svg_w, svg_h)


# ── CUSHION RENDERER (1 view — top-down) ─────────────────────────

def render_cushion(params: dict) -> str:
    """Single top-down plan view for cushions/pillows. Portrait 850x1100."""
    name = params.get("name", "Cushion")
    dims = params.get("dimensions", {})
    width = _parse_dim(dims, "width", params.get("width", 24))
    depth = _parse_dim(dims, "depth", params.get("depth", 24))
    height = _parse_dim(dims, "height", params.get("height", 0))  # thickness
    notes = params.get("notes", "")

    svg_w, svg_h = 850, 1100
    parts = [_defs()]
    parts.append(f'<rect width="{svg_w}" height="{svg_h}" fill="white"/>')
    parts.append(_rect(6, 6, svg_w - 12, svg_h - 12, SW_BORDER))

    _view_label(parts, 0, 30, svg_w, "PLAN VIEW (TOP DOWN)")

    # Scale
    scale = min((svg_w - 200) / max(width, 1), (svg_h - 400) / max(depth, 1), 8)
    w_s = width * scale
    d_s = depth * scale
    cx = svg_w / 2
    cy = 320
    x0 = cx - w_s / 2
    y0 = cy - d_s / 2

    # Cushion shape (rounded rect)
    radius = min(w_s, d_s) * 0.08
    parts.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{w_s:.1f}" height="{d_s:.1f}" '
                 f'fill="none" stroke="{BLACK}" stroke-width="{SW_HEAVY}" rx="{radius:.1f}"/>')

    # Welt/piping line (inner)
    inset = 6
    parts.append(f'<rect x="{x0 + inset:.1f}" y="{y0 + inset:.1f}" width="{w_s - inset * 2:.1f}" '
                 f'height="{d_s - inset * 2:.1f}" fill="none" stroke="{LIGHT_GRAY}" '
                 f'stroke-width="{SW_LIGHT}" stroke-dasharray="4,3" rx="{max(radius - 2, 0):.1f}"/>')

    # Center label
    parts.append(_text(cx, cy, f'{width:.0f}" x {depth:.0f}"', 12, weight="600"))
    if height > 0:
        parts.append(_text(cx, cy + 16, f'{height:.0f}" thick', 9, fill=GRAY))

    # Dimensions
    _dim_h(parts, x0, x0 + w_s, y0 + d_s, f'{width:.0f}"', 22)
    _dim_v(parts, x0 + w_s, y0, y0 + d_s, f'{depth:.0f}"', 22)

    if notes:
        parts.append(_text(cx, svg_h - 200, _esc(notes[:100]), 10, fill=GRAY))

    _title_block_small(parts, svg_w / 2 - 160, svg_h - 170, 320, 130, name, "Cushion")

    return _wrap_svg(parts, svg_w, svg_h)


# ── HEADBOARD RENDERER (1 view — front elevation) ────────────────

def render_headboard(params: dict) -> str:
    """Single front elevation for headboards. Portrait 850x1100."""
    name = params.get("name", "Headboard")
    dims = params.get("dimensions", {})
    width = _parse_dim(dims, "width", params.get("width", 62))
    height = _parse_dim(dims, "height", params.get("height", 48))
    notes = params.get("notes", "")

    svg_w, svg_h = 850, 1100
    parts = [_defs()]
    parts.append(f'<rect width="{svg_w}" height="{svg_h}" fill="white"/>')
    parts.append(_rect(6, 6, svg_w - 12, svg_h - 12, SW_BORDER))

    _view_label(parts, 0, 30, svg_w, "FRONT ELEVATION")

    scale = min((svg_w - 200) / max(width, 1), (svg_h - 400) / max(height, 1), 6)
    w_s = width * scale
    h_s = height * scale
    cx = svg_w / 2
    ground_y = 580
    x0 = cx - w_s / 2
    y0 = ground_y - h_s

    # Headboard shape (rounded top)
    top_r = min(w_s * 0.06, 20)
    parts.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{w_s:.1f}" height="{h_s:.1f}" '
                 f'fill="none" stroke="{BLACK}" stroke-width="{SW_HEAVY}" rx="{top_r:.1f}"/>')

    # Tufting grid
    cols = max(int(width / 8), 3)
    rows = max(int(height / 8), 3)
    for r in range(1, rows):
        for c in range(1, cols):
            bx = x0 + w_s * c / cols
            by = y0 + h_s * r / rows
            parts.append(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="2" fill="{LIGHT_GRAY}" stroke="{BLACK}" stroke-width="0.5"/>')

    # Mattress line
    parts.append(_line(x0 - 10, ground_y, x0 + w_s + 10, ground_y, SW_MED, GRAY))
    parts.append(_text(cx, ground_y + 14, "MATTRESS LINE", 7, fill=GRAY))

    # Dimensions
    _dim_h(parts, x0, x0 + w_s, ground_y, f'{width:.0f}"', 28)
    _dim_v(parts, x0 + w_s, y0, ground_y, f'{height:.0f}"', 28)

    if notes:
        parts.append(_text(cx, svg_h - 200, _esc(notes[:100]), 10, fill=GRAY))

    _title_block_small(parts, svg_w / 2 - 160, svg_h - 170, 320, 130, name, "Headboard")

    return _wrap_svg(parts, svg_w, svg_h)


# ── 2-VIEW FURNITURE RENDERER (chair, sofa, ottoman, table) ──────

def render_furniture_2view(item_type: str, params: dict) -> str:
    """Two-view diagram for furniture. Landscape 1200x850."""
    name = params.get("name", item_type.title())
    dims = params.get("dimensions", {})
    width = _parse_dim(dims, "width", params.get("width", 36))
    height = _parse_dim(dims, "height", params.get("height", 32))
    depth = _parse_dim(dims, "depth", params.get("depth", 24))
    seat_h = _parse_dim(dims, "seat", params.get("seat_height", 18))
    notes = params.get("notes", "")

    svg_w, svg_h = 1200, 850
    parts = [_defs()]
    parts.append(f'<rect width="{svg_w}" height="{svg_h}" fill="white"/>')
    parts.append(_rect(6, 6, svg_w - 12, svg_h - 12, SW_BORDER))
    parts.append(_rect(10, 10, svg_w - 20, svg_h - 20, 0.5))

    half_w = (svg_w - 60) / 2
    view_h = svg_h - 200

    # ── VIEW 1: Front Elevation (left half) ──
    v1_x = 30
    v1_y = 40
    parts.append(_rect(v1_x - 2, v1_y - 2, half_w + 4, view_h + 4, 0.5, stroke=GRAY))
    _view_label(parts, v1_x, v1_y, half_w, "FRONT ELEVATION")

    f_scale = min((half_w - 80) / max(width, 1), (view_h - 80) / max(height, 1), 6)
    fw = width * f_scale
    fh = height * f_scale
    f_cx = v1_x + half_w / 2
    f_ground = v1_y + view_h - 30
    fx0 = f_cx - fw / 2
    fy0 = f_ground - fh

    if item_type == "chair":
        # Back
        back_h = (height - seat_h) * f_scale
        parts.append(_rect(fx0 + fw * 0.1, fy0, fw * 0.8, back_h, SW_HEAVY))
        # Seat
        seat_hs = seat_h * f_scale
        parts.append(_rect(fx0, f_ground - seat_hs, fw, seat_hs * 0.35, SW_HEAVY))
        # Legs
        leg_h = seat_hs * 0.65
        for lx in [fx0 + 8, fx0 + fw - 8]:
            parts.append(_line(lx, f_ground - leg_h, lx, f_ground, SW_HEAVY))
    elif item_type == "sofa":
        # Back
        back_h = fh * 0.45
        parts.append(_rect(fx0, fy0, fw, back_h, SW_HEAVY))
        # Arms
        arm_w = fw * 0.08
        arm_h = fh * 0.5
        parts.append(_rect(fx0, fy0 + back_h - arm_h * 0.3, arm_w, arm_h, SW_MED))
        parts.append(_rect(fx0 + fw - arm_w, fy0 + back_h - arm_h * 0.3, arm_w, arm_h, SW_MED))
        # Seat
        seat_hs = seat_h * f_scale
        parts.append(_rect(fx0 + arm_w, f_ground - seat_hs, fw - arm_w * 2, seat_hs * 0.4, SW_MED))
        # Legs
        for lx in [fx0 + 12, fx0 + fw - 12]:
            parts.append(_line(lx, f_ground - 8, lx, f_ground, SW_MED))
    elif item_type == "ottoman":
        parts.append(_rect(fx0, fy0, fw, fh * 0.4, SW_HEAVY))
        for lx in [fx0 + 10, fx0 + fw - 10]:
            parts.append(_line(lx, fy0 + fh * 0.4, lx, f_ground, SW_MED))
    elif item_type == "table":
        top_h = fh * 0.08
        parts.append(_rect(fx0, fy0, fw, top_h, SW_HEAVY))
        for lx in [fx0 + 12, fx0 + fw - 12]:
            parts.append(_line(lx, fy0 + top_h, lx, f_ground, SW_MED))

    # Front dims
    _dim_h(parts, fx0, fx0 + fw, f_ground, f'{width:.0f}"', 22)
    _dim_v(parts, fx0 + fw, fy0, f_ground, f'{height:.0f}"', 22)

    # ── VIEW 2: Side Elevation or Plan View (right half) ──
    v2_x = 30 + half_w + 30
    parts.append(_rect(v2_x - 2, v1_y - 2, half_w + 4, view_h + 4, 0.5, stroke=GRAY))

    if item_type == "chair":
        # Side elevation
        _view_label(parts, v2_x, v1_y, half_w, "SIDE ELEVATION")
        s_scale = min((half_w - 80) / max(depth, 1), (view_h - 80) / max(height, 1), 6)
        sd = depth * s_scale
        sh = height * s_scale
        s_cx = v2_x + half_w / 2
        sx0 = s_cx - sd / 2
        sy0 = f_ground - sh

        # Back
        back_thick = sd * 0.15
        parts.append(_rect(sx0 + sd - back_thick, sy0, back_thick, sh * 0.65, SW_HEAVY))
        # Seat
        seat_hs = seat_h * s_scale
        parts.append(_rect(sx0, f_ground - seat_hs, sd, seat_hs * 0.3, SW_HEAVY))
        # Legs
        for lx in [sx0 + 6, sx0 + sd - 6]:
            parts.append(_line(lx, f_ground - seat_hs * 0.7, lx, f_ground, SW_MED))

        _dim_h(parts, sx0, sx0 + sd, f_ground, f'{depth:.0f}"', 22)
        _dim_v(parts, sx0 + sd, sy0, f_ground, f'{height:.0f}"', 22)
    else:
        # Plan view (top-down)
        _view_label(parts, v2_x, v1_y, half_w, "PLAN VIEW")
        p_scale = min((half_w - 80) / max(width, 1), (view_h - 80) / max(depth, 1), 6)
        pw = width * p_scale
        pd = depth * p_scale
        p_cx = v2_x + half_w / 2
        p_cy = v1_y + view_h / 2
        px0 = p_cx - pw / 2
        py0 = p_cy - pd / 2

        parts.append(_rect(px0, py0, pw, pd, SW_HEAVY))
        parts.append(_text(p_cx, p_cy + 4, f'{width:.0f}" x {depth:.0f}"', 11, weight="600"))

        _dim_h(parts, px0, px0 + pw, py0 + pd, f'{width:.0f}"', 22)
        _dim_v(parts, px0 + pw, py0, py0 + pd, f'{depth:.0f}"', 22)

    # Title block
    _title_block_small(parts, svg_w / 2 - 160, svg_h - 140, 320, 110, name, item_type)

    if notes:
        parts.append(_text(svg_w / 2, svg_h - 150, _esc(notes[:100]), 10, fill=GRAY))

    return _wrap_svg(parts, svg_w, svg_h)


# ── MILLWORK RENDERER (3 views) ──────────────────────────────────

def render_millwork(params: dict) -> str:
    """Three-view for cabinets/millwork. Landscape 1200x850."""
    name = params.get("name", "Cabinet")
    dims = params.get("dimensions", {})
    width = _parse_dim(dims, "width", params.get("width", 36))
    height = _parse_dim(dims, "height", params.get("height", 32))
    depth = _parse_dim(dims, "depth", params.get("depth", 18))
    notes = params.get("notes", "")

    svg_w, svg_h = 1200, 850
    parts = [_defs()]
    parts.append(f'<rect width="{svg_w}" height="{svg_h}" fill="white"/>')
    parts.append(_rect(6, 6, svg_w - 12, svg_h - 12, SW_BORDER))
    parts.append(_rect(10, 10, svg_w - 20, svg_h - 20, 0.5))

    # 3 views in top row, title block bottom right
    third_w = (svg_w - 80) / 3
    view_h = svg_h - 220

    # ── FRONT ELEVATION ──
    v1_x = 30
    v1_y = 40
    parts.append(_rect(v1_x - 2, v1_y - 2, third_w + 4, view_h + 4, 0.5, stroke=GRAY))
    _view_label(parts, v1_x, v1_y, third_w, "FRONT ELEVATION")

    f_scale = min((third_w - 60) / max(width, 1), (view_h - 60) / max(height, 1), 4)
    fw = width * f_scale
    fh = height * f_scale
    f_cx = v1_x + third_w / 2
    f_ground = v1_y + view_h - 20
    fx0 = f_cx - fw / 2
    fy0 = f_ground - fh

    # Cabinet carcass
    parts.append(_rect(fx0, fy0, fw, fh, SW_HEAVY))
    # Doors (2 doors)
    door_gap = 3
    dw = (fw - door_gap) / 2
    parts.append(_rect(fx0 + 1, fy0 + 1, dw - 1, fh - 2, SW_MED))
    parts.append(_rect(fx0 + dw + door_gap, fy0 + 1, dw - 1, fh - 2, SW_MED))
    # Handles
    handle_y = fy0 + fh * 0.45
    parts.append(_line(fx0 + dw - 12, handle_y, fx0 + dw - 12, handle_y + 16, SW_MED))
    parts.append(_line(fx0 + dw + door_gap + 2, handle_y, fx0 + dw + door_gap + 2, handle_y + 16, SW_MED))

    _dim_h(parts, fx0, fx0 + fw, f_ground, f'{width:.0f}"', 18)
    _dim_v(parts, fx0 + fw, fy0, f_ground, f'{height:.0f}"', 18)

    # ── SIDE ELEVATION ──
    v2_x = v1_x + third_w + 10
    parts.append(_rect(v2_x - 2, v1_y - 2, third_w + 4, view_h + 4, 0.5, stroke=GRAY))
    _view_label(parts, v2_x, v1_y, third_w, "SIDE ELEVATION")

    s_scale = min((third_w - 60) / max(depth, 1), (view_h - 60) / max(height, 1), 4)
    sd = depth * s_scale
    sh = height * s_scale
    s_cx = v2_x + third_w / 2
    sx0 = s_cx - sd / 2
    sy0 = f_ground - sh

    parts.append(_rect(sx0, sy0, sd, sh, SW_HEAVY))
    # Shelves
    shelf_count = max(int(height / 12), 2)
    for i in range(1, shelf_count):
        sy = sy0 + sh * i / shelf_count
        parts.append(_line(sx0 + 2, sy, sx0 + sd - 2, sy, SW_LIGHT, GRAY))

    _dim_h(parts, sx0, sx0 + sd, f_ground, f'{depth:.0f}"', 18)
    _dim_v(parts, sx0 + sd, sy0, f_ground, f'{height:.0f}"', 18)

    # ── PLAN VIEW ──
    v3_x = v2_x + third_w + 10
    parts.append(_rect(v3_x - 2, v1_y - 2, third_w + 4, view_h + 4, 0.5, stroke=GRAY))
    _view_label(parts, v3_x, v1_y, third_w, "PLAN VIEW")

    p_scale = min((third_w - 60) / max(width, 1), (view_h - 60) / max(depth, 1), 4)
    pw = width * p_scale
    pd = depth * p_scale
    p_cx = v3_x + third_w / 2
    p_cy = v1_y + view_h / 2
    px0 = p_cx - pw / 2
    py0 = p_cy - pd / 2

    parts.append(_rect(px0, py0, pw, pd, SW_HEAVY))
    parts.append(_text(p_cx, p_cy + 4, f'{width:.0f}" x {depth:.0f}"', 10, weight="600"))

    _dim_h(parts, px0, px0 + pw, py0 + pd, f'{width:.0f}"', 18)
    _dim_v(parts, px0 + pw, py0, py0 + pd, f'{depth:.0f}"', 18)

    # Title block
    _title_block_small(parts, svg_w / 2 - 160, svg_h - 160, 320, 120, name, "Millwork")

    if notes:
        parts.append(_text(svg_w / 2, svg_h - 170, _esc(notes[:100]), 10, fill=GRAY))

    return _wrap_svg(parts, svg_w, svg_h)


# ── GENERIC MEASUREMENT DIAGRAM (1 view) ─────────────────────────

def render_generic(params: dict) -> str:
    """Generic measurement diagram for unknown items. Portrait 850x1100."""
    name = params.get("name", "Item")
    dims = params.get("dimensions", {})
    notes = params.get("notes", "")

    svg_w, svg_h = 850, 1100
    parts = [_defs()]
    parts.append(f'<rect width="{svg_w}" height="{svg_h}" fill="white"/>')
    parts.append(_rect(6, 6, svg_w - 12, svg_h - 12, SW_BORDER))

    _view_label(parts, 0, 30, svg_w, "MEASUREMENT DIAGRAM")

    cx = svg_w / 2
    cy = 340
    shape_w = 300
    shape_h = 220

    # Generic shape
    x0 = cx - shape_w / 2
    y0 = cy - shape_h / 2
    parts.append(_rect(x0, y0, shape_w, shape_h, SW_HEAVY))
    # Cross lines
    parts.append(_line(x0, y0, x0 + shape_w, y0 + shape_h, SW_LIGHT, LIGHT_GRAY))
    parts.append(_line(x0 + shape_w, y0, x0, y0 + shape_h, SW_LIGHT, LIGHT_GRAY))

    # Place dimensions around shape
    dim_items = list(dims.items())
    positions = [
        (cx, y0 + shape_h + 28, "h"),     # bottom
        (x0 + shape_w + 30, cy, "v"),      # right
        (cx, y0 - 14, "h_above"),          # top
        (x0 - 30, cy, "v_left"),           # left
    ]

    for i, (label, value) in enumerate(dim_items[:4]):
        px, py, ptype = positions[i]
        val_str = str(value)
        if ptype == "h":
            _dim_h(parts, x0, x0 + shape_w, y0 + shape_h, val_str, 22)
            parts.append(_text(cx, y0 + shape_h + 46, _esc(label), 8, fill=GRAY))
        elif ptype == "v":
            _dim_v(parts, x0 + shape_w, y0, y0 + shape_h, val_str, 25)
        elif ptype == "h_above":
            parts.append(_text(px, py, f'{_esc(label)}: {_esc(val_str)}', 11, weight="600"))
        elif ptype == "v_left":
            _dim_v(parts, x0, y0, y0 + shape_h, val_str, -25)

    # Overflow dimensions as text list
    if len(dim_items) > 4:
        ty = y0 + shape_h + 70
        for label, value in dim_items[4:]:
            parts.append(_text(cx - 60, ty, f'{_esc(label)}:', 10, anchor="end", fill=GRAY))
            parts.append(_text(cx - 50, ty, _esc(str(value)), 11, anchor="start", weight="600"))
            ty += 18

    if notes:
        parts.append(_text(cx, svg_h - 200, _esc(notes[:100]), 10, fill=GRAY))

    _title_block_small(parts, svg_w / 2 - 160, svg_h - 170, 320, 130, name, "General")

    return _wrap_svg(parts, svg_w, svg_h)


# ── LEGACY COMPAT ─────────────────────────────────────────────────

def render_measurement_diagram(name: str, item_type: str, dimensions: dict,
                               notes: str = "", svg_w: int = 740, svg_h: int = 0) -> str:
    """Legacy entry point — routes to appropriate new renderer."""
    params = {"name": name, "dimensions": dimensions, "notes": notes}

    mapped_type = LEGACY_TYPE_MAP.get(item_type, item_type)

    if mapped_type == "window":
        return render_window(params)
    elif mapped_type == "cushion":
        return render_cushion(params)
    elif mapped_type == "headboard":
        return render_headboard(params)
    elif mapped_type == "millwork":
        return render_millwork(params)
    elif mapped_type in ("chair", "sofa", "ottoman", "table"):
        return render_furniture_2view(mapped_type, params)
    else:
        return render_generic(params)


# ── MAIN ENTRY POINT ─────────────────────────────────────────────

def generate_drawing(name: str = "", description: str = "",
                     dimensions: dict = None, item_type: str | None = None,
                     notes: str = "", user_text: str = "",
                     params: dict = None) -> dict:
    """Main entry point — classify input and generate the right drawing.

    Returns: {"svg": str, "item_type": str, "name": str, "classification": dict}
    """
    if params is None:
        params = {}

    # Merge convenience args into params
    if name:
        params.setdefault("name", name)
    if dimensions:
        params.setdefault("dimensions", dimensions)
    if notes:
        params.setdefault("notes", notes)

    # Classify
    if item_type:
        classification = classify_item(user_text=item_type)
        if classification["type"] == "generic" and item_type != "generic":
            # Direct type override
            classification["type"] = LEGACY_TYPE_MAP.get(item_type, item_type)
    else:
        classification = classify_item(
            user_text=user_text or "",
            item_name=params.get("name", name),
            description=description,
        )

    resolved_type = classification["type"]

    if resolved_type == "bench":
        # Route to bench_renderer.py (4-quadrant professional)
        return {
            "svg": None,
            "item_type": "bench",
            "name": params.get("name", name),
            "route": "bench_renderer",
            "classification": classification,
        }

    # Route to correct renderer
    if resolved_type == "window":
        svg = render_window(params)
    elif resolved_type == "cushion":
        svg = render_cushion(params)
    elif resolved_type == "headboard":
        svg = render_headboard(params)
    elif resolved_type == "millwork":
        svg = render_millwork(params)
    elif resolved_type in ("chair", "sofa", "ottoman", "table"):
        svg = render_furniture_2view(resolved_type, params)
    else:
        svg = render_generic(params)

    return {
        "svg": svg,
        "item_type": resolved_type,
        "name": params.get("name", name),
        "route": f"{resolved_type}_renderer",
        "classification": classification,
    }
