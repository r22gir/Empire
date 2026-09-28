"""Parametric idea diagrams for quoted Workroom / catalog items.

A quote item is classified into a diagram category MAX already knows,
then drawn from whatever dimensions were supplied. The sheet transmits
the idea. It is not a style-accurate shop drawing, and it is not the
final design.

Failures are returned as an honest degraded result. Callers that are
saving a quote must not treat that result as fatal.
"""
from __future__ import annotations

import html
import math
import re
from typing import Any, Optional


FIDELITY = "idea"
FINAL_DESIGN = "later"

# Categories MAX already classifies for Drawing Studio intake and for
# measurement drawings. Quoted items land in one of these — not in a
# new style family.
IDEA_CATEGORIES: dict[str, dict[str, Any]] = {
    "window_treatment": {
        "label": "Window Treatment",
        "kind": "window",
        "axes": ("width", "height"),
        "defaults": {"width": 48.0, "height": 84.0},
    },
    "cushion": {
        "label": "Cushion",
        "kind": "pad",
        "axes": ("width", "depth"),
        "defaults": {"width": 24.0, "depth": 24.0, "thickness": 4.0},
    },
    "pillow": {
        "label": "Pillow",
        "kind": "pad",
        "axes": ("width", "height"),
        "defaults": {"width": 20.0, "height": 20.0},
    },
    "headboard": {
        "label": "Headboard",
        "kind": "panel",
        "axes": ("width", "height"),
        "defaults": {"width": 62.0, "height": 56.0},
    },
    "upholstery_wall_panel": {
        "label": "Upholstery Wall Panel",
        "kind": "panel",
        "axes": ("width", "height"),
        "defaults": {"width": 48.0, "height": 96.0},
    },
    "sofa": {
        "label": "Sofa",
        "kind": "seat",
        "axes": ("width", "height"),
        "defaults": {"width": 84.0, "depth": 36.0, "height": 34.0},
    },
    "chair": {
        "label": "Chair",
        "kind": "seat",
        "axes": ("width", "height"),
        "defaults": {"width": 32.0, "depth": 34.0, "height": 36.0},
    },
    "ottoman": {
        "label": "Ottoman",
        "kind": "pad",
        "axes": ("width", "depth"),
        "defaults": {"width": 24.0, "depth": 24.0, "height": 18.0},
    },
    "bench": {
        "label": "Bench",
        "kind": "seat",
        "axes": ("width", "height"),
        "defaults": {"width": 60.0, "depth": 18.0, "height": 18.0},
    },
    "banquette": {
        "label": "Banquette",
        "kind": "seat",
        "axes": ("width", "height"),
        "defaults": {"width": 96.0, "depth": 22.0, "height": 36.0},
    },
    "shelving": {
        "label": "Shelving",
        "kind": "case",
        "axes": ("width", "height"),
        "defaults": {"width": 48.0, "depth": 12.0, "height": 84.0, "shelves": 4},
    },
    "storage_bench": {
        "label": "Storage Bench",
        "kind": "seat",
        "axes": ("width", "height"),
        "defaults": {"width": 48.0, "depth": 18.0, "height": 18.0},
    },
    "cabinet_millwork": {
        "label": "Cabinet / Millwork",
        "kind": "case",
        "axes": ("width", "height"),
        "defaults": {"width": 36.0, "depth": 24.0, "height": 34.5},
    },
    "desk": {
        "label": "Desk",
        "kind": "table",
        "axes": ("width", "height"),
        "defaults": {"width": 60.0, "depth": 30.0, "height": 30.0},
    },
    "table": {
        "label": "Table",
        "kind": "table",
        "axes": ("width", "height"),
        "defaults": {"width": 72.0, "depth": 36.0, "height": 30.0},
    },
    "murphy_bed": {
        "label": "Murphy Bed",
        "kind": "case",
        "axes": ("width", "height"),
        "defaults": {"width": 64.0, "depth": 16.0, "height": 86.0},
    },
}

# Catalog, pricing, and quote item types that already mean one of the
# categories above. Style names are intentionally collapsed: the drawing
# transmits the idea, not pleat or tufting fidelity.
EXACT_CATEGORY: dict[str, str] = {
    "window_treatment": "window_treatment",
    "window": "window_treatment",
    "drapery": "window_treatment",
    "drape": "window_treatment",
    "curtain": "window_treatment",
    "shade": "window_treatment",
    "roman": "window_treatment",
    "roman_shade": "window_treatment",
    "roman_shades": "window_treatment",
    "roller_shade": "window_treatment",
    "valance": "window_treatment",
    "cornice": "window_treatment",
    "cornice_valance": "window_treatment",
    "cushion": "cushion",
    "cushions": "cushion",
    "cover": "cushion",
    "pillow": "pillow",
    "pillows": "pillow",
    "bedding": "pillow",
    "headboard": "headboard",
    "wall_panel": "upholstery_wall_panel",
    "upholstery_wall_panel": "upholstery_wall_panel",
    "sofa": "sofa",
    "chair": "chair",
    "slipcover": "chair",
    "ottoman": "ottoman",
    "bench": "bench",
    "banquette": "banquette",
    "shelving": "shelving",
    "shelf": "shelving",
    "storage_bench": "storage_bench",
    "cabinet_millwork": "cabinet_millwork",
    "millwork": "cabinet_millwork",
    "cabinet": "cabinet_millwork",
    "desk": "desk",
    "table": "table",
    "murphy_bed": "murphy_bed",
}

# Longer phrases win. Checked before the exact map's short tokens when
# scanning free text, so "storage bench" does not become a plain bench.
PHRASE_RULES: tuple[tuple[str, str], ...] = (
    ("storage bench", "storage_bench"),
    ("murphy bed", "murphy_bed"),
    ("wall panel", "upholstery_wall_panel"),
    ("window treatment", "window_treatment"),
    ("roman shade", "window_treatment"),
    ("roller shade", "window_treatment"),
    ("pinch pleat", "window_treatment"),
    ("seat cushion", "cushion"),
    ("throw pillow", "pillow"),
    ("cabinet", "cabinet_millwork"),
    ("millwork", "cabinet_millwork"),
    ("headboard", "headboard"),
    ("banquette", "banquette"),
    ("booth", "banquette"),
    ("shelving", "shelving"),
    ("bookcase", "shelving"),
    ("ottoman", "ottoman"),
    ("cushion", "cushion"),
    ("pillow", "pillow"),
    ("bolster", "pillow"),
    ("sham", "pillow"),
    ("cornice", "window_treatment"),
    ("valance", "window_treatment"),
    ("drapery", "window_treatment"),
    ("drape", "window_treatment"),
    ("curtain", "window_treatment"),
    ("shade", "window_treatment"),
    ("sofa", "sofa"),
    ("loveseat", "sofa"),
    ("sectional", "sofa"),
    ("couch", "sofa"),
    ("chair", "chair"),
    ("slipcover", "chair"),
    ("desk", "desk"),
    ("table", "table"),
    ("nightstand", "table"),
    ("console", "table"),
    ("bench", "bench"),
    ("window", "window_treatment"),
)

NON_DIAGRAM_CATEGORIES = frozenset({
    "labor",
    "fabric",
    "fabric_only",
    "fabric_materials",
    "hardware",
    "pickup",
    "delivery",
    "install",
    "installation",
    "pickup_delivery_install",
    "rush",
    "rush_custom_surcharge",
    "tax",
    "discount",
    "surcharge",
})

COUNT_KEYS = frozenset({
    "shelves", "panels", "quantity", "qty", "cushion_segments",
    "drawer_count", "doors", "leading_edges",
})
RATIO_KEYS = frozenset({"fullness"})
SKIP_VALUE_KEYS = frozenset({
    "price", "rate", "cost", "amount", "total", "tax", "subtotal",
    "unit_price", "proposed_price", "final_price", "quantity", "qty",
    "hours", "yards", "yards_needed", "labor_hours", "labor_rate",
})

_LENGTH_RE = re.compile(
    r"""^\s*
        (?:
            (?P<whole>\d+(?:\.\d+)?)\s+(?P<num>\d+)\s*/\s*(?P<den>\d+)
            | (?P<hyphen>\d+)\s*-\s*(?P<hnum>\d+)\s*/\s*(?P<hden>\d+)
            | (?P<fnum>\d+)\s*/\s*(?P<fden>\d+)
            | (?P<decimal>\d+(?:\.\d+)?)
        )
        \s*(?:inches|inch|in\.?)?
        \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)

SHEET_W = 720
SHEET_H = 480


def format_inches(value: float) -> str:
    """Format a decimal inch measurement as a reduced sixteenth.

    54.5 -> 54 1/2"    0.75 -> 3/4"    34.5 -> 34 1/2"
    """
    if value < 0:
        return "-" + format_inches(-value)
    whole = int(math.floor(value + 1e-9))
    sixteenths = int(round((value - whole) * 16))
    if sixteenths >= 16:
        whole += sixteenths // 16
        sixteenths = sixteenths % 16
    if sixteenths <= 0:
        return f'{whole}"'
    divisor = math.gcd(sixteenths, 16)
    num = sixteenths // divisor
    den = 16 // divisor
    if whole == 0:
        return f'{num}/{den}"'
    return f'{whole} {num}/{den}"'


def parse_length(value: Any) -> Optional[float]:
    """Parse a dimension that may be numeric or a fractional inch string."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if number > 0 else None
    text = str(value).strip().replace("″", '"').replace("”", '"').replace('"', "")
    if not text:
        return None
    match = _LENGTH_RE.match(text)
    if not match:
        return None
    if match.group("hyphen"):
        den = int(match.group("hden") or 0)
        if den == 0:
            return None
        return int(match.group("hyphen")) + int(match.group("hnum")) / den
    if match.group("whole") is not None and match.group("num") is not None:
        den = int(match.group("den") or 0)
        if den == 0:
            return None
        return float(match.group("whole")) + int(match.group("num")) / den
    if match.group("fnum"):
        den = int(match.group("fden") or 0)
        if den == 0:
            return None
        number = int(match.group("fnum")) / den
        return number if number > 0 else None
    if match.group("decimal") is not None:
        number = float(match.group("decimal"))
        return number if number > 0 else None
    return None


def _norm_key(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return re.sub(r"_+", "_", text)


def _canonical_dim_key(key: str) -> str:
    key = _norm_key(key)
    aliases = {
        "window_width_in": "width",
        "width_in": "width",
        "width_inches": "width",
        "w": "width",
        "length_in": "height",
        "height_in": "height",
        "height_inches": "height",
        "drop": "height",
        "drop_in": "height",
        "h": "height",
        "depth_in": "depth",
        "depth_inches": "depth",
        "d": "depth",
        "projection": "depth",
        "thickness_in": "thickness",
        "seat_depth": "depth",
    }
    return aliases.get(key, key)


def collect_dimensions(item: dict) -> dict[str, float]:
    """Pull every positive dimension off a quote item.

    Nested ``dimensions``, ``measurements``, and ``inputs`` are included.
    Pricing rates, quantities, and yardage are not dimensions.
    """
    found: dict[str, float] = {}

    def take(key: str, value: Any) -> None:
        canon = _canonical_dim_key(key)
        if canon in SKIP_VALUE_KEYS or canon in {"category", "type", "item_type", "style", "name", "description", "notes"}:
            return
        if any(token in canon for token in ("price", "cost", "rate", "tax", "amount", "total", "subtotal")):
            return
        number = parse_length(value)
        if number is None:
            return
        # First explicit value wins so a nested default cannot overwrite it.
        found.setdefault(canon, number)

    for source_key in ("dimensions", "measurements", "inputs"):
        nested = item.get(source_key)
        if isinstance(nested, dict):
            for key, value in nested.items():
                take(str(key), value)
    for key, value in item.items():
        if key in {"dimensions", "measurements", "inputs"}:
            continue
        if isinstance(value, dict):
            continue
        take(str(key), value)
    return found


def _text_blob(item: dict) -> str:
    parts = []
    for key in ("diagram_category", "category", "item_type", "type", "item_style", "style", "name", "description", "notes"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(value)
    return " ".join(parts).lower().replace("_", " ").replace("-", " ")


def _is_fee_category(category: str) -> bool:
    if not category:
        return False
    if category in NON_DIAGRAM_CATEGORIES or category.startswith("hardware"):
        return True
    return False


def resolve_category(item: dict) -> tuple[Optional[str], str]:
    """Return ``(category, reason)``.

    reason is ``matched``, ``not_applicable``, or ``unknown``.
    """
    explicit = _norm_key(item.get("diagram_category"))
    if explicit in IDEA_CATEGORIES:
        return explicit, "matched"

    category = _norm_key(item.get("category"))
    item_type = _norm_key(item.get("item_type") or item.get("type"))
    style = _norm_key(item.get("item_style") or item.get("style"))

    if item_type in EXACT_CATEGORY:
        return EXACT_CATEGORY[item_type], "matched"
    if style in EXACT_CATEGORY and not _is_fee_category(category):
        return EXACT_CATEGORY[style], "matched"
    if category in EXACT_CATEGORY:
        return EXACT_CATEGORY[category], "matched"
    if _is_fee_category(category) or _is_fee_category(item_type):
        return None, "not_applicable"

    blob = _text_blob(item)
    for phrase, mapped in PHRASE_RULES:
        if phrase in blob:
            return mapped, "matched"
    if _is_fee_category(category) or any(word in blob.split() for word in ("labor", "hardware", "delivery", "installation")):
        if not any(phrase in blob for phrase, _mapped in PHRASE_RULES):
            return None, "not_applicable"
    if blob.strip():
        return None, "unknown"
    return None, "not_applicable"


def _label_for(key: str, value: float, assumed: bool) -> str:
    title = key.replace("_", " ").title()
    if key in COUNT_KEYS:
        shown = str(int(value)) if float(value).is_integer() else f"{value:g}"
    elif key in RATIO_KEYS:
        shown = f"{value:g}×"
    else:
        shown = format_inches(value)
    suffix = " (assumed)" if assumed else ""
    return f"{title}: {shown}{suffix}"


def _resolve_draw_dims(category: str, provided: dict[str, float]) -> tuple[dict[str, float], list[str]]:
    spec = IDEA_CATEGORIES[category]
    draw = dict(provided)
    assumed: list[str] = []
    for axis in spec["axes"]:
        if axis not in draw:
            draw[axis] = float(spec["defaults"][axis])
            assumed.append(axis)
    for key, value in spec["defaults"].items():
        if key not in draw and key not in spec["axes"]:
            # Secondary defaults (depth, thickness, shelves) are listed only
            # when the sheet needs them to describe the silhouette.
            if key in {"depth", "thickness", "height", "shelves"} and key not in provided:
                draw[key] = float(value)
                assumed.append(key)
    return draw, assumed


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _notice_svg(message: str, category: Optional[str] = None) -> str:
    title = IDEA_CATEGORIES.get(category or "", {}).get("label", "Idea diagram")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SHEET_W} {SHEET_H}" '
        f'width="{SHEET_W}" height="{SHEET_H}" role="img">'
        f'<rect width="{SHEET_W}" height="{SHEET_H}" fill="#faf8f2" stroke="#111827" stroke-width="1.4"/>'
        f'<text x="36" y="48" font-family="Arial, Helvetica, sans-serif" font-size="18" font-weight="700" fill="#1a1a2e">IDEA DIAGRAM</text>'
        f'<text x="36" y="74" font-family="Arial, Helvetica, sans-serif" font-size="13" fill="#8a5a00">{_esc(title)}</text>'
        f'<text x="36" y="120" font-family="Arial, Helvetica, sans-serif" font-size="14" fill="#344054">{_esc(message)}</text>'
        f'<text x="36" y="150" font-family="Arial, Helvetica, sans-serif" font-size="12" fill="#667085">The quote is unchanged. Final design is a later process.</text>'
        f"</svg>"
    )


def _line(x1: float, y1: float, x2: float, y2: float, stroke: str = "#111827", sw: float = 1.4) -> str:
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{stroke}" stroke-width="{sw}"/>'
    )


def _rect(x: float, y: float, w: float, h: float, stroke: str = "#111827", fill: str = "none", sw: float = 1.6) -> str:
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w, 1):.1f}" height="{max(h, 1):.1f}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
    )


def _text(x: float, y: float, value: Any, size: int = 12, anchor: str = "start", weight: str = "400", fill: str = "#1f2933") -> str:
    # Inch marks stay as quotation characters inside the text node.
    safe = html.escape(str(value), quote=False)
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-family="Arial, Helvetica, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill}">{safe}</text>'
    )


def _draw_kind(kind: str, x: float, y: float, w: float, h: float, dims: dict[str, float]) -> list[str]:
    parts: list[str] = []
    if kind == "window":
        parts.append(_rect(x, y, w, h, fill="#f4f7fb"))
        rail_h = max(8, h * 0.08)
        parts.append(_rect(x - 6, y - rail_h, w + 12, rail_h, fill="#9aa3af", sw=1))
        parts.append(_line(x + w * 0.5, y, x + w * 0.5, y + h, "#c5d0dc", 1))
        return parts
    if kind == "pad":
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="10" '
            f'fill="#f7f1e4" stroke="#111827" stroke-width="1.6"/>'
        )
        return parts
    if kind == "panel":
        parts.append(_rect(x, y, w, h, fill="#f6f3ee"))
        parts.append(_rect(x + 8, y + 8, w - 16, h - 16, stroke="#c4b8a4", sw=1))
        return parts
    if kind == "seat":
        parts.append(_rect(x, y, w, h, fill="#f7f1e4"))
        seat = dims.get("seat_height")
        height = dims.get("height") or h
        ratio = 0.45
        if seat and height:
            ratio = min(0.8, max(0.25, float(seat) / float(height)))
        seat_y = y + h * (1 - ratio)
        parts.append(_rect(x, seat_y, w, h * ratio, fill="#efe4cf", sw=1.2))
        return parts
    if kind == "table":
        top_h = max(8, h * 0.08)
        parts.append(_rect(x, y, w, top_h, fill="#d8c7a1"))
        inset = w * 0.12
        parts.append(_line(x + inset, y + top_h, x + inset, y + h, sw=2))
        parts.append(_line(x + w - inset, y + top_h, x + w - inset, y + h, sw=2))
        return parts
    # case: shelving, cabinet, murphy
    parts.append(_rect(x, y, w, h, fill="#f8f5ef"))
    shelves = int(dims.get("shelves") or 3)
    shelves = max(1, min(shelves, 8))
    for i in range(1, shelves + 1):
        sy = y + h * i / (shelves + 1)
        parts.append(_line(x + 4, sy, x + w - 4, sy, "#8a8175", 1))
    return parts


def _dim_horizontal(x1: float, x2: float, y: float, label: str) -> list[str]:
    return [
        _line(x1, y - 10, x1, y + 4, "#8a5a00", 0.8),
        _line(x2, y - 10, x2, y + 4, "#8a5a00", 0.8),
        _line(x1, y, x2, y, "#8a5a00", 1),
        _text((x1 + x2) / 2, y - 6, label, 11, "middle", "700", "#8a5a00"),
    ]


def _dim_vertical(x: float, y1: float, y2: float, label: str, anchor: str = "start") -> list[str]:
    text_x = x + 8 if anchor == "start" else x - 8
    return [
        _line(x - 10, y1, x + 4, y1, "#8a5a00", 0.8),
        _line(x - 10, y2, x + 4, y2, "#8a5a00", 0.8),
        _line(x, y1, x, y2, "#8a5a00", 1),
        _text(text_x, (y1 + y2) / 2, label, 11, anchor, "700", "#8a5a00"),
    ]


def render_idea_svg(
    category: str,
    dims: dict[str, float],
    assumed: list[str],
    *,
    name: str = "",
    note: str = "",
) -> str:
    spec = IDEA_CATEGORIES[category]
    kind = spec["kind"]
    width_key, height_key = spec["axes"]
    width_in = max(float(dims.get(width_key) or 1), 0.25)
    height_in = max(float(dims.get(height_key) or 1), 0.25)

    view_x, view_y, view_w, view_h = 36, 108, 340, 250
    # Leave room for fraction labels on the right and below, at any aspect ratio.
    scale = min((view_w - 120) / width_in, (view_h - 78) / height_in)
    box_w = width_in * scale
    box_h = height_in * scale
    box_x = view_x + 16 + (view_w - 120 - box_w) / 2
    box_y = view_y + 22 + (view_h - 78 - box_h) / 2

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SHEET_W} {SHEET_H}" '
        f'width="{SHEET_W}" height="{SHEET_H}" role="img" aria-label="Idea diagram for {_esc(spec["label"])}">',
        f'<rect width="{SHEET_W}" height="{SHEET_H}" fill="#ffffff"/>',
        _rect(10, 10, SHEET_W - 20, SHEET_H - 20, sw=1.3),
        _text(28, 40, "EMPIRE WORKROOM", 12, weight="700", fill="#8a5a00"),
        _text(28, 64, "IDEA DIAGRAM", 20, weight="800"),
        _text(SHEET_W - 28, 40, spec["label"].upper(), 14, "end", "700"),
        _text(SHEET_W - 28, 62, (name or "Quoted item")[:48], 11, "end", "400", "#667085"),
        _text(28, 88, "Transmits the idea — not a style-accurate drawing. Final design is a later process.", 11, fill="#667085"),
        _rect(view_x, view_y, view_w, view_h, stroke="#e4e7ec", sw=1),
    ]
    parts.extend(_draw_kind(kind, box_x, box_y, box_w, box_h, dims))
    h_label = format_inches(width_in)
    v_label = format_inches(height_in)
    if width_key in assumed:
        h_label += " assumed"
    if height_key in assumed:
        v_label += " assumed"
    parts.extend(_dim_horizontal(box_x, box_x + box_w, min(box_y + box_h + 22, view_y + view_h - 16), h_label))
    v_x = box_x + box_w + 16
    v_anchor = "start"
    if v_x > view_x + view_w - 52:
        v_x = max(view_x + 8, box_x - 12)
        v_anchor = "end"
    parts.extend(_dim_vertical(v_x, box_y, box_y + box_h, v_label, v_anchor))
    parts.append(_text(view_x + 12, view_y + 18, f'{width_key.title()} × {height_key.title()}', 10, weight="700", fill="#98a2b3"))

    parts.append(_text(400, 128, "PARAMETERS", 13, weight="800"))
    lines = [_label_for(key, value, key in assumed) for key, value in dims.items()]
    if note:
        lines.append(note)
    if assumed:
        lines.append("Assumed values are category defaults, not field measures.")
    lines.append("Category silhouette only. Style fidelity is a later design step.")
    for index, line in enumerate(lines[:12]):
        parts.append(_text(400, 154 + index * 22, line, 12, weight="600" if index == 0 else "400"))

    parts.append(_text(28, SHEET_H - 28, "IDEA ONLY  ·  NTS  ·  NOT FOR FABRICATION", 11, weight="700", fill="#8a5a00"))
    parts.append("</svg>")
    return "\n".join(parts)


def _result(
    *,
    status: str,
    category: Optional[str],
    dimensions: dict[str, float],
    labels: dict[str, str],
    assumed: list[str],
    note: str,
    svg: Optional[str],
) -> dict[str, Any]:
    drawing_id = None
    if status == "attached" and category:
        drawing_id = f"idea:{category}"
    elif status == "degraded":
        drawing_id = "idea:degraded"
    return {
        "status": status,
        "category": category,
        "dimensions": dimensions,
        "labels": labels,
        "assumed": assumed,
        "fidelity": FIDELITY,
        "final_design": FINAL_DESIGN,
        "note": note,
        "svg": svg,
        "drawing_id": drawing_id,
    }


def build_idea_diagram(item: Optional[dict]) -> dict[str, Any]:
    """Build an idea diagram for one quoted item. Never raises."""
    try:
        return _build_idea_diagram(item or {})
    except Exception as exc:
        message = f"Idea diagram failed: {exc}"
        return _result(
            status="degraded",
            category=None,
            dimensions={},
            labels={},
            assumed=[],
            note=message,
            svg=_notice_svg(message),
        )


def _build_idea_diagram(item: dict) -> dict[str, Any]:
    if not isinstance(item, dict):
        item = {}
    category, reason = resolve_category(item)
    provided = collect_dimensions(item)
    name = str(item.get("name") or item.get("description") or item.get("item_type") or item.get("type") or "").strip()

    if reason == "not_applicable":
        return _result(
            status="not_applicable",
            category=None,
            dimensions=provided,
            labels={key: _label_for(key, value, False) for key, value in provided.items()},
            assumed=[],
            note="No idea diagram — this line is not a drawn catalog piece.",
            svg=None,
        )

    if category is None:
        raw = str(item.get("category") or item.get("item_type") or item.get("type") or item.get("description") or "item")
        message = f'No Max diagram category for "{raw}". Quote continues without an idea drawing.'
        return _result(
            status="degraded",
            category=None,
            dimensions=provided,
            labels={key: _label_for(key, value, False) for key, value in provided.items()},
            assumed=[],
            note=message,
            svg=_notice_svg(message),
        )

    if not provided:
        label = IDEA_CATEGORIES[category]["label"]
        needed = ", ".join(IDEA_CATEGORIES[category]["axes"])
        message = f"{label} needs at least one dimension ({needed}) before an idea diagram can be drawn."
        return _result(
            status="degraded",
            category=category,
            dimensions={},
            labels={},
            assumed=[],
            note=message,
            svg=_notice_svg(message, category),
        )

    dims, assumed = _resolve_draw_dims(category, provided)
    labels = {key: _label_for(key, value, key in assumed) for key, value in dims.items()}
    mapping_note = ""
    source = _norm_key(item.get("item_type") or item.get("type") or item.get("category"))
    if source in {"bedding", "slipcover", "cover"}:
        mapping_note = f"Shown as a {IDEA_CATEGORIES[category]['label'].lower()} idea, not a finished {source} style."
    note = mapping_note or "Idea sheet from category and dimensions."
    svg = render_idea_svg(category, dims, assumed, name=name, note=note)
    return _result(
        status="attached",
        category=category,
        dimensions=dims,
        labels=labels,
        assumed=assumed,
        note=note,
        svg=svg,
    )


def idea_metadata(diagram: dict) -> dict[str, Any]:
    """JSON-safe summary stored beside the SVG. The SVG itself is omitted."""
    return {
        "status": diagram.get("status"),
        "category": diagram.get("category"),
        "dimensions": diagram.get("dimensions") or {},
        "labels": diagram.get("labels") or {},
        "assumed": diagram.get("assumed") or [],
        "fidelity": diagram.get("fidelity") or FIDELITY,
        "final_design": diagram.get("final_design") or FINAL_DESIGN,
        "note": diagram.get("note") or "",
        "drawing_id": diagram.get("drawing_id"),
    }


def annotate_quote(quote: dict) -> dict:
    """Attach idea diagrams onto quote items. Never raises and never drops the quote."""
    if not isinstance(quote, dict):
        return quote
    try:
        for room in quote.get("rooms") or []:
            if not isinstance(room, dict):
                continue
            for key in ("items", "windows", "upholstery"):
                for item in room.get(key) or []:
                    if isinstance(item, dict):
                        item["idea_diagram"] = build_idea_diagram(item)
        annotated_lines = []
        for item in quote.get("line_items") or []:
            if isinstance(item, dict):
                item["idea_diagram"] = build_idea_diagram(item)
                annotated_lines.append(item)
        # Notes-extraction quotes already reserve ``diagrams`` for SVG slots.
        if quote.get("source") == "notes_extraction" or "extracted_items" in quote:
            diagrams = []
            for item in quote.get("extracted_items") or annotated_lines:
                if not isinstance(item, dict):
                    diagrams.append(None)
                    continue
                diagram = item.get("idea_diagram") or build_idea_diagram(item)
                item["idea_diagram"] = diagram
                diagrams.append(diagram.get("svg"))
            quote["diagrams"] = diagrams
    except Exception as exc:
        quote["idea_diagram_error"] = f"Idea diagrams could not be attached: {exc}"
    return quote


def quote_idea_html(quote: dict) -> str:
    """HTML block for the quote PDF. Empty when nothing should be shown.

    Window and upholstery rows already render their own drawings in the
    room section, so this block covers catalog ``items``, notes diagrams,
    and flat line items.
    """
    if not isinstance(quote, dict):
        return ""
    try:
        blocks: list[str] = []
        rendered_rooms = False
        for room in quote.get("rooms") or []:
            if not isinstance(room, dict):
                continue
            for item in room.get("items") or []:
                if not isinstance(item, dict):
                    continue
                diagram = item.get("idea_diagram")
                if not isinstance(diagram, dict):
                    diagram = build_idea_diagram(item)
                html_block = _figure_html(diagram, item)
                if html_block:
                    blocks.append(html_block)
                    rendered_rooms = True

        diagrams = quote.get("diagrams") or []
        if diagrams and not rendered_rooms:
            for svg in diagrams:
                if isinstance(svg, str) and "<svg" in svg:
                    blocks.append(
                        '<div style="margin:8px 0 16px;page-break-inside:avoid">'
                        f"{svg}</div>"
                    )

        if not blocks:
            for item in quote.get("line_items") or []:
                if not isinstance(item, dict):
                    continue
                diagram = item.get("idea_diagram")
                if not isinstance(diagram, dict):
                    diagram = build_idea_diagram(item)
                html_block = _figure_html(diagram, item)
                if html_block:
                    blocks.append(html_block)

        if not blocks:
            return ""
        body = "".join(blocks)
        return (
            '<div style="margin-top:18px">'
            '<h3 style="color:#8a5a00;margin:0 0 4px">Idea diagrams</h3>'
            '<p style="margin:0 0 10px;color:#667085;font-size:0.85em">'
            "These sheets transmit the idea from the quoted category and dimensions. "
            "They are not the final design."
            "</p>"
            f"{body}</div>"
        )
    except Exception as exc:
        return (
            '<p style="color:#8a5a00;font-size:0.85em">'
            f"Idea diagrams unavailable: {_esc(exc)}. The quote totals are unchanged."
            "</p>"
        )


def _figure_html(diagram: dict, item: dict) -> str:
    status = diagram.get("status")
    if status == "not_applicable":
        return ""
    svg = diagram.get("svg") or ""
    label = str(item.get("description") or item.get("name") or item.get("type") or diagram.get("category") or "Item")
    note = diagram.get("note") or ""
    if "<svg" not in svg:
        return (
            '<p style="color:#8a5a00;font-size:0.85em">'
            f"{_esc(label)}: {_esc(note or 'Idea diagram unavailable.')}"
            "</p>"
        )
    return (
        '<div style="margin:8px 0 14px;page-break-inside:avoid">'
        f'<p style="margin:0 0 4px;font-size:0.78em;color:#667085">{_esc(label)}</p>'
        f'<div style="max-width:720px">{svg}</div>'
        f'<p style="margin:4px 0 0;font-size:0.75em;color:#98a2b3">{_esc(note)}</p>'
        "</div>"
    )


def idea_png_bytes(diagram: dict) -> Optional[bytes]:
    """Rasterize an idea sheet for the reportlab quote PDF.

    The SVG is what HTML quotes and the review screen show. This PNG is the
    same category, dimensions, and fraction labels for the SQL quote PDF.
    Returns None if the sheet cannot be drawn; callers keep the quote.
    """
    if not isinstance(diagram, dict):
        return None
    try:
        from io import BytesIO
        from PIL import Image, ImageDraw, ImageFont

        image = Image.new("RGB", (SHEET_W, SHEET_H), "white")
        draw = ImageDraw.Draw(image)

        def _font(size: int, bold: bool = False):
            candidates = (
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold
                else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
                else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            )
            for path in candidates:
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue
            return ImageFont.load_default()

        font_sm = _font(12)
        font = _font(14)
        font_lg = _font(20, bold=True)
        draw.rectangle((8, 8, SHEET_W - 8, SHEET_H - 8), outline="#111827", width=2)
        category = diagram.get("category")
        label = IDEA_CATEGORIES.get(category or "", {}).get("label", "Idea diagram")
        draw.text((28, 22), "EMPIRE WORKROOM", fill="#8a5a00", font=_font(12, bold=True))
        draw.text((28, 42), "IDEA DIAGRAM", fill="#1a1a2e", font=font_lg)
        draw.text((400, 28), label.upper(), fill="#1a1a2e", font=_font(14, bold=True))
        draw.text((28, 72), "Transmits the idea. Final design is a later process.", fill="#667085", font=font_sm)

        dims = diagram.get("dimensions") or {}
        spec = IDEA_CATEGORIES.get(category or "")
        if diagram.get("status") == "attached" and spec and dims:
            width_key, height_key = spec["axes"]
            width_in = max(float(dims.get(width_key) or 1), 0.25)
            height_in = max(float(dims.get(height_key) or 1), 0.25)
            view = (36, 100, 360, 250)
            scale = min((view[2] - 80) / width_in, (view[3] - 60) / height_in)
            box_w = width_in * scale
            box_h = height_in * scale
            box_x = view[0] + 40 + (view[2] - 80 - box_w) / 2
            box_y = view[1] + 24 + (view[3] - 60 - box_h) / 2
            draw.rectangle((view[0], view[1], view[0] + view[2], view[1] + view[3]), outline="#e4e7ec")
            draw.rectangle((box_x, box_y, box_x + box_w, box_y + box_h), outline="#111827", width=2)
            draw.text((box_x, box_y + box_h + 8), format_inches(width_in), fill="#8a5a00", font=_font(13, bold=True))
            draw.text((box_x + box_w + 6, box_y), format_inches(height_in), fill="#8a5a00", font=_font(13, bold=True))
        note_y = 108
        for line in list((diagram.get("labels") or {}).values())[:8]:
            draw.text((400, note_y), str(line), fill="#344054", font=font)
            note_y += 22
        note = diagram.get("note") or ""
        if note:
            draw.text((400, min(note_y + 8, 400)), str(note)[:90], fill="#667085", font=font_sm)
        draw.text((28, SHEET_H - 36), "IDEA ONLY  ·  NTS  ·  NOT FOR FABRICATION", fill="#8a5a00", font=_font(12, bold=True))
        buf = BytesIO()
        image.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None
