"""Parametric product templates for catalog-driven drawing sheets."""
from __future__ import annotations

from dataclasses import dataclass
import html
import re
from typing import Any


DRAPERY_STYLES = frozenset({
    "pinch_pleat", "french_pleat", "euro_pleat", "goblet", "ripplefold",
    "grommet", "rod_pocket", "tab_top", "inverted_box", "cartridge",
    "pencil", "smocked",
})

ROMAN_STYLES = frozenset({
    "flat_roman", "hobbled_roman", "balloon_roman", "austrian",
    "relaxed_roman", "london_roman", "tulip_roman",
})

CORNICE_STYLES = frozenset({
    "straight_cornice", "arched_cornice", "scalloped_cornice", "shaped_cornice",
    "upholstered_cornice", "swag_jabot", "balloon_valance", "box_pleat_valance",
    "kingston_valance", "rod_pocket_valance", "board_mounted_valance", "scarf_swag",
})

BANQUETTE_STYLES = frozenset({
    "straight", "l_shape", "u_shape", "curved", "booth", "single_booth",
    "high_back", "modular", "storage", "outdoor",
})

CHAIR_STYLES = frozenset({
    "wingback", "club", "barrel", "slipper", "bergere", "chesterfield",
    "midcentury", "oversized", "occasional", "egg", "chaise_lounge",
    "dining", "lounge", "parsons", "swivel", "rocking", "desk_chair",
})

SHELVING_STYLES = frozenset({
    "floating", "built_in", "open", "closed_cabinet", "ladder", "corner",
    "display_case", "modular_cube", "entertainment_center", "plate_rail",
})


@dataclass(frozen=True)
class TemplateDef:
    key: str
    family: str
    default_dimensions: dict[str, float]
    editable_parameters: tuple[str, ...]
    supported_views: tuple[str, ...]
    presentation_rules: dict[str, Any]
    shop_rules: dict[str, Any]


TEMPLATE_REGISTRY: dict[str, TemplateDef] = {
    "drapery": TemplateDef(
        key="drapery",
        family="Window Treatment / Drapery",
        default_dimensions={"width": 96, "height": 102, "drop": 102, "return": 4, "panels": 2, "fullness": 2.5},
        editable_parameters=("width", "height", "drop", "return", "panels", "fullness", "mount_type", "stack_direction"),
        supported_views=("front", "side", "top", "perspective"),
        presentation_rules={"dimensions": "primary", "callouts": "client", "title": "Presentation Sheet"},
        shop_rules={"dimensions": "full", "callouts": "technical", "title": "Shop Drawing"},
    ),
    "roman_shade": TemplateDef(
        key="roman_shade",
        family="Window Treatment / Roman Shade",
        default_dimensions={"width": 48, "height": 64, "drop": 64, "return": 1.5},
        editable_parameters=("width", "height", "drop", "return", "fold_spacing"),
        supported_views=("front", "side", "top", "perspective"),
        presentation_rules={"dimensions": "primary", "callouts": "client", "title": "Presentation Sheet"},
        shop_rules={"dimensions": "full", "callouts": "technical", "title": "Shop Drawing"},
    ),
    "cornice_valance": TemplateDef(
        key="cornice_valance",
        family="Window Treatment / Cornice & Valance",
        default_dimensions={"width": 72, "height": 24, "drop": 24, "return": 4},
        editable_parameters=("width", "height", "drop", "return"),
        supported_views=("front", "side", "top", "perspective"),
        presentation_rules={"dimensions": "primary", "callouts": "client", "title": "Presentation Sheet"},
        shop_rules={"dimensions": "full", "callouts": "technical", "title": "Shop Drawing"},
    ),
    "banquette": TemplateDef(
        key="banquette",
        family="WoodCraft / Bench & Banquette",
        default_dimensions={"width": 120, "depth": 20, "height": 34, "seat_height": 18, "back_height": 16},
        editable_parameters=("width", "depth", "height", "seat_height", "back_height", "arm_configuration", "base_type"),
        supported_views=("front", "side", "plan", "perspective"),
        presentation_rules={"dimensions": "primary", "callouts": "client", "title": "Presentation Sheet"},
        shop_rules={"dimensions": "full", "callouts": "technical", "title": "Shop Drawing"},
    ),
    "chair": TemplateDef(
        key="chair",
        family="Workroom / Chair Upholstery",
        default_dimensions={"width": 32, "depth": 34, "height": 36, "seat_height": 18, "back_height": 18, "arm_height": 24},
        editable_parameters=("width", "depth", "height", "seat_height", "arm_height", "back_profile", "leg_type"),
        supported_views=("front", "side", "plan", "perspective"),
        presentation_rules={"dimensions": "primary", "callouts": "client", "title": "Presentation Sheet"},
        shop_rules={"dimensions": "full", "callouts": "technical", "title": "Shop Drawing"},
    ),
    "shelving": TemplateDef(
        key="shelving",
        family="WoodCraft / Shelving & Cabinet Carcass",
        default_dimensions={"width": 48, "depth": 12, "height": 84, "shelves": 4, "material_thickness": 0.75, "bay_spacing": 24},
        editable_parameters=("width", "height", "depth", "shelves", "material_thickness", "bay_spacing", "door_style"),
        supported_views=("front", "side", "plan", "perspective"),
        presentation_rules={"dimensions": "primary", "callouts": "client", "title": "Presentation Sheet"},
        shop_rules={"dimensions": "full", "callouts": "technical", "title": "Shop Drawing"},
    ),
}


def get_template_for_style(style_key: str | None, item_type: str | None = None) -> TemplateDef | None:
    style = _norm(style_key)
    item = _norm(item_type)
    if item == "banquette" and style in BANQUETTE_STYLES:
        return TEMPLATE_REGISTRY["banquette"]
    if item == "chair" and style in CHAIR_STYLES:
        return TEMPLATE_REGISTRY["chair"]
    if item == "shelving" and style in SHELVING_STYLES:
        return TEMPLATE_REGISTRY["shelving"]
    if style in DRAPERY_STYLES:
        return TEMPLATE_REGISTRY["drapery"]
    if style in ROMAN_STYLES:
        return TEMPLATE_REGISTRY["roman_shade"]
    if style in CORNICE_STYLES:
        return TEMPLATE_REGISTRY["cornice_valance"]
    return None


def render_template_instance(style_key: str, params: dict[str, Any]) -> dict[str, Any] | None:
    template = get_template_for_style(style_key, params.get("item_type"))
    if not template:
        return None

    mode = _sheet_mode(params.get("drawing_mode") or params.get("mode"))
    dims = _merge_dimensions(template, params)
    name = params.get("name") or _title(style_key)
    if template.key in {"drapery", "roman_shade", "cornice_valance"}:
        svg = _render_window_treatment_sheet(template, style_key, name, dims, params, mode)
        item_type = "window"
    else:
        svg = _render_product_family_sheet(template, style_key, name, dims, mode)
        item_type = template.key

    return {
        "svg": svg,
        "item_type": item_type,
        "template": template.key,
        "family": template.family,
        "style_key": _norm(style_key),
        "mode": mode,
        "name": name,
        "parameters": dims,
    }


def _norm(value: str | None) -> str:
    return (value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _title(value: str) -> str:
    return _norm(value).replace("_", " ").title()


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _num(value: Any, default: float) -> float:
    if value is None or value == "":
        return default
    try:
        return float(re.sub(r"[^0-9.]+", "", str(value)))
    except (TypeError, ValueError):
        return default


def _choice(raw_dims: dict[str, Any], params: dict[str, Any], key: str, default: str) -> str:
    value = raw_dims.get(key, params.get(key, default))
    return _norm(str(value or default)) or default


def _merge_dimensions(template: TemplateDef, params: dict[str, Any]) -> dict[str, Any]:
    dims = dict(template.default_dimensions)
    raw_dims = params.get("dimensions") or {}
    for key, default in list(dims.items()):
        dims[key] = _num(raw_dims.get(key, params.get(key)), default)
    dims["panels"] = _num(raw_dims.get("panels", params.get("panels")), dims.get("panels", 2))
    dims["fullness"] = _num(raw_dims.get("fullness", params.get("fullness")), dims.get("fullness", 2.5))
    dims["fold_spacing"] = _num(raw_dims.get("fold_spacing", params.get("fold_spacing")), dims.get("fold_spacing", 7))
    dims["seat_height"] = _num(raw_dims.get("seat_height", params.get("seat_height")), dims.get("seat_height", 18))
    dims["back_height"] = _num(raw_dims.get("back_height", params.get("back_height")), dims.get("back_height", 18))
    dims["arm_height"] = _num(raw_dims.get("arm_height", params.get("arm_height")), dims.get("arm_height", 24))
    dims["shelves"] = _num(raw_dims.get("shelves", params.get("shelves")), dims.get("shelves", 4))
    dims["material_thickness"] = _num(raw_dims.get("material_thickness", params.get("material_thickness")), dims.get("material_thickness", 0.75))
    dims["bay_spacing"] = _num(raw_dims.get("bay_spacing", params.get("bay_spacing")), dims.get("bay_spacing", 24))
    dims["arm_configuration"] = _choice(raw_dims, params, "arm_configuration", "none")
    dims["base_type"] = _choice(raw_dims, params, "base_type", "toe_kick")
    dims["back_profile"] = _choice(raw_dims, params, "back_profile", "straight")
    dims["leg_type"] = _choice(raw_dims, params, "leg_type", "tapered")
    dims["door_style"] = _choice(raw_dims, params, "door_style", "open")
    dims["mount_type"] = _choice(raw_dims, params, "mount_type", "outside")
    dims["stack_direction"] = _choice(raw_dims, params, "stack_direction", "split")
    return dims


def _sheet_mode(mode: Any) -> str:
    raw = _norm(str(mode or "presentation"))
    return "shop" if raw in {"shop", "shop_drawing", "technical"} else "presentation"


def _line(x1: float, y1: float, x2: float, y2: float, sw: float = 1, stroke: str = "#111") -> str:
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{sw}"/>'


def _rect(x: float, y: float, w: float, h: float, sw: float = 1, fill: str = "none", stroke: str = "#111", rx: float = 0) -> str:
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


def _text(x: float, y: float, value: Any, size: int = 10, anchor: str = "middle", weight: str = "400", fill: str = "#1f2933") -> str:
    return f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-size="{size}" font-weight="{weight}" fill="{fill}">{_esc(value)}</text>'


def _dim_h(parts: list[str], x1: float, x2: float, y: float, label: str, offset: float = 16) -> None:
    ty = y + offset
    parts.append(_line(x1, y, x1, ty + 4, 0.7, "#333"))
    parts.append(_line(x2, y, x2, ty + 4, 0.7, "#333"))
    parts.append(_line(x1, ty, x2, ty, 0.8, "#111"))
    parts.append(_text((x1 + x2) / 2, ty - 4, label, 10, weight="600"))


def _dim_v(parts: list[str], x: float, y1: float, y2: float, label: str, offset: float = 18) -> None:
    tx = x + offset
    parts.append(_line(x, y1, tx + 4, y1, 0.7, "#333"))
    parts.append(_line(x, y2, tx + 4, y2, 0.7, "#333"))
    parts.append(_line(tx, y1, tx, y2, 0.8, "#111"))
    parts.append(_text(tx + 13, (y1 + y2) / 2, label, 10, weight="600"))


def _draw_front(parts: list[str], template: TemplateDef, style: str, x: float, y: float, w: float, h: float, dims: dict[str, float], mode: str) -> None:
    width = dims["width"]
    drop = dims["drop"]
    scale = min((w - 80) / max(width, 1), (h - 95) / max(drop, 1))
    dw = width * scale
    dh = drop * scale
    x0 = x + w / 2 - dw / 2
    y0 = y + 52
    if dh > h - 110:
        y0 = y + 35

    parts.append(_text(x + w / 2, y + 18, "FRONT ELEVATION", 11, weight="700"))
    parts.append(_rect(x0 - 10, y0 - 10, dw + 20, dh + 20, 1.2, "#f8fafc", "#667085"))
    parts.append(_rect(x0, y0, dw, dh, 1.4, "#ffffff", "#111"))
    parts.append(_line(x0 + dw / 2, y0, x0 + dw / 2, y0 + dh, 0.6, "#c4c7cc"))

    if template.key == "drapery":
        rod_y = y0 - 17
        parts.append(_line(x0 - 20, rod_y, x0 + dw + 20, rod_y, 3, "#222"))
        fold_count = max(8, min(28, int(width * dims["fullness"] / 7)))
        for i in range(fold_count + 1):
            px = x0 + dw * i / fold_count
            amp = 4 if i % 2 == 0 else -2
            parts.append(_line(px + amp, rod_y + 7, px - amp, y0 + dh, 0.7, "#9aa3af"))
        panel_w = dw / max(dims["panels"], 1)
        for i in range(1, int(dims["panels"])):
            px = x0 + panel_w * i
            parts.append(_line(px, y0 - 2, px, y0 + dh, 1.1, "#555"))
    elif template.key == "roman_shade":
        folds = max(5, int(drop / max(dims["fold_spacing"], 1)))
        for i in range(1, folds):
            py = y0 + dh * i / folds
            parts.append(_line(x0 + 4, py, x0 + dw - 4, py, 0.8, "#667085"))
        parts.append(_text(x0 + dw / 2, y0 + dh / 2, _title(style), 10, fill="#667085"))
    else:
        profile_h = min(dh, max(38, dh * 0.35))
        parts.append(_rect(x0 - 16, y0 - 8, dw + 32, profile_h, 1.6, "#f3efe8", "#111"))
        if "scallop" in style or "swag" in style:
            scallops = 5
            for i in range(scallops):
                cx = x0 + dw * (i + 0.5) / scallops
                parts.append(f'<path d="M {cx - dw / scallops / 2:.1f} {y0 + profile_h - 5:.1f} Q {cx:.1f} {y0 + profile_h + 18:.1f} {cx + dw / scallops / 2:.1f} {y0 + profile_h - 5:.1f}" fill="none" stroke="#111" stroke-width="1.1"/>')
        parts.append(_text(x0 + dw / 2, y0 + profile_h / 2 + 4, _title(style), 9, fill="#667085"))

    _dim_h(parts, x0, x0 + dw, y0 + dh + 8, f'{width:.0f}" W')
    _dim_v(parts, x0 + dw + 10, y0, y0 + dh, f'{drop:.0f}" DROP')
    if mode == "shop":
        parts.append(_text(x0, y0 + dh + 58, "VERIFY FINISHED WIDTH, DROP, RETURNS, AND MOUNT HEIGHT", 8, "start", "700", "#8a5a00"))


def _draw_side(parts: list[str], x: float, y: float, w: float, h: float, dims: dict[str, float], mode: str) -> None:
    parts.append(_text(x + w / 2, y + 18, "SIDE RETURN", 11, weight="700"))
    sx = x + w / 2 - 18
    sy = y + 50
    sh = h - 105
    ret = max(10, min(46, dims["return"] * 6))
    parts.append(_rect(sx, sy, 22, sh, 1.2, "#ffffff", "#111"))
    parts.append(_rect(sx - ret, sy + 15, ret, 28, 1.1, "#f3efe8", "#111"))
    _dim_v(parts, sx + 30, sy, sy + sh, f'{dims["drop"]:.0f}"', 16)
    if mode == "shop":
        _dim_h(parts, sx - ret, sx, sy + 52, f'{dims["return"]:.1f}" RETURN', 12)
        parts.append(_text(x + 14, y + h - 20, "SIDE VIEW CONFIRMS RETURN / PROJECTION", 8, "start", fill="#667085"))


def _draw_top(parts: list[str], x: float, y: float, w: float, h: float, dims: dict[str, float], mode: str) -> None:
    parts.append(_text(x + w / 2, y + 18, "TOP PLAN", 11, weight="700"))
    x0 = x + 34
    y0 = y + h / 2 - 18
    ww = w - 68
    depth = max(18, min(48, dims["return"] * 7))
    parts.append(_rect(x0, y0, ww, depth, 1.3, "#ffffff", "#111"))
    parts.append(_line(x0 + 12, y0 + depth / 2, x0 + ww - 12, y0 + depth / 2, 0.8, "#98a2b3"))
    _dim_h(parts, x0, x0 + ww, y0 + depth + 6, f'{dims["width"]:.0f}"')
    if mode == "shop":
        _dim_v(parts, x0 + ww + 8, y0, y0 + depth, f'{dims["return"]:.1f}"')


def _draw_perspective(parts: list[str], x: float, y: float, w: float, h: float, template: TemplateDef, style: str) -> None:
    parts.append(_text(x + w / 2, y + 18, "PERSPECTIVE", 11, weight="700"))
    cx = x + w / 2
    cy = y + h / 2
    parts.append(f'<path d="M {cx - 88:.1f} {cy - 35:.1f} L {cx + 62:.1f} {cy - 58:.1f} L {cx + 92:.1f} {cy + 26:.1f} L {cx - 58:.1f} {cy + 50:.1f} Z" fill="#f7f4ed" stroke="#111" stroke-width="1.2"/>')
    if template.key == "drapery":
        for i in range(8):
            px = cx - 62 + i * 19
            parts.append(_line(px, cy - 42, px - 12, cy + 42, 0.8, "#98a2b3"))
    elif template.key == "roman_shade":
        for i in range(5):
            parts.append(_line(cx - 74, cy - 24 + i * 15, cx + 75, cy - 48 + i * 15, 0.8, "#98a2b3"))
    parts.append(_text(cx, y + h - 16, _title(style), 9, fill="#667085"))


def _draw_family_front(parts: list[str], template: TemplateDef, style: str, x: float, y: float, w: float, h: float, dims: dict[str, Any], mode: str) -> None:
    width = dims["width"]
    height = dims["height"]
    scale = min((w - 110) / max(width, 1), (h - 112) / max(height, 1))
    dw = width * scale
    dh = height * scale
    x0 = x + w / 2 - dw / 2
    y0 = y + 52 + (h - 112 - dh) / 2

    parts.append(_text(x + w / 2, y + 18, "FRONT ELEVATION", 11, weight="700"))

    if template.key == "banquette":
        seat_h = min(dh * 0.55, dims["seat_height"] * scale)
        back_h = min(dh - seat_h, dims["back_height"] * scale)
        base_type = dims.get("base_type", "toe_kick")
        arm_config = dims.get("arm_configuration", "none")
        base_h = max(7, min(seat_h * 0.34, 12 if base_type == "toe_kick" else 20))
        if base_type == "legs":
            leg_w = max(5, dw * 0.035)
            for leg_x in (x0 + leg_w, x0 + dw - leg_w * 2):
                parts.append(_rect(leg_x, y0 + back_h + seat_h - base_h, leg_w, base_h, 1, "#fff", "#111"))
        else:
            toe_inset = max(8, dw * 0.035)
            parts.append(_rect(x0 + toe_inset, y0 + back_h + seat_h - base_h, dw - toe_inset * 2, base_h, 1.2, "#fff", "#111"))
        parts.append(_rect(x0, y0 + back_h, dw, seat_h, 1.5, "#f6f2ea", "#111"))
        parts.append(_rect(x0, y0, dw, back_h, 1.5, "#ffffff", "#111"))
        arm_w = max(10, dw * 0.06)
        if arm_config in {"left", "both"}:
            parts.append(_rect(x0 - arm_w, y0 + back_h * 0.28, arm_w, back_h + seat_h * 0.72, 1.4, "#fff", "#111"))
        if arm_config in {"right", "both"}:
            parts.append(_rect(x0 + dw, y0 + back_h * 0.28, arm_w, back_h + seat_h * 0.72, 1.4, "#fff", "#111"))
        channel_count = max(4, min(10, int(width / 16)))
        for i in range(1, channel_count):
            px = x0 + dw * i / channel_count
            parts.append(_line(px, y0 + 4, px, y0 + back_h - 4, 0.7, "#98a2b3"))
    elif template.key == "chair":
        seat_h = min(dh * 0.4, dims["seat_height"] * scale)
        back_h = dh - seat_h
        arm_h = max(seat_h * 0.65, min(dh * 0.78, dims["arm_height"] * scale))
        leg_type = dims.get("leg_type", "tapered")
        back_profile = dims.get("back_profile", "straight")
        arm_w = max(14, dw * 0.16)
        if leg_type in {"tapered", "legs"}:
            leg_h = max(8, seat_h * 0.3)
            parts.append(f'<path d="M {x0 + arm_w + 6:.1f} {y0 + back_h + seat_h - 2:.1f} L {x0 + arm_w + 14:.1f} {y0 + back_h + seat_h - 2:.1f} L {x0 + arm_w + 11:.1f} {y0 + back_h + seat_h + leg_h:.1f} L {x0 + arm_w + 3:.1f} {y0 + back_h + seat_h + leg_h:.1f} Z" fill="#fff" stroke="#111" stroke-width="1"/>')
            parts.append(f'<path d="M {x0 + dw - arm_w - 14:.1f} {y0 + back_h + seat_h - 2:.1f} L {x0 + dw - arm_w - 6:.1f} {y0 + back_h + seat_h - 2:.1f} L {x0 + dw - arm_w - 3:.1f} {y0 + back_h + seat_h + leg_h:.1f} L {x0 + dw - arm_w - 11:.1f} {y0 + back_h + seat_h + leg_h:.1f} Z" fill="#fff" stroke="#111" stroke-width="1"/>')
        parts.append(_rect(x0 + arm_w, y0 + back_h, dw - arm_w * 2, seat_h, 1.5, "#f7f4ef", "#111", 4))
        if back_profile in {"curved", "wingback"}:
            parts.append(f'<path d="M {x0 + arm_w * 0.7:.1f} {y0 + back_h + 8:.1f} Q {x0 + dw / 2:.1f} {y0 - 24:.1f} {x0 + dw - arm_w * 0.7:.1f} {y0 + back_h + 8:.1f} Z" fill="#fff" stroke="#111" stroke-width="1.5"/>')
        else:
            parts.append(_rect(x0 + arm_w * 0.7, y0, dw - arm_w * 1.4, back_h + 8, 1.5, "#fff", "#111", 6))
        arm_y = y0 + back_h + seat_h - arm_h
        parts.append(_rect(x0, arm_y, arm_w, arm_h, 1.4, "#fff", "#111", 5))
        parts.append(_rect(x0 + dw - arm_w, arm_y, arm_w, arm_h, 1.4, "#fff", "#111", 5))
    else:
        shelf_count = max(2, min(8, int(dims["shelves"])))
        thickness = max(1.5, min(8, dims["material_thickness"] * scale))
        door_style = dims.get("door_style", "open")
        parts.append(_rect(x0, y0, dw, dh, 1.6, "#fff", "#111"))
        for i in range(1, shelf_count):
            py = y0 + dh * i / shelf_count
            parts.append(_rect(x0, py - thickness / 2, dw, thickness, 0.8, "#f8fafc", "#111"))
        parts.append(_line(x0 + dw / 2, y0, x0 + dw / 2, y0 + dh, 0.8, "#98a2b3"))
        if door_style in {"closed", "doors"}:
            parts.append(_rect(x0, y0 + dh * 0.55, dw / 2, dh * 0.45, 1.0, "none", "#667085"))
            parts.append(_rect(x0 + dw / 2, y0 + dh * 0.55, dw / 2, dh * 0.45, 1.0, "none", "#667085"))

    _dim_h(parts, x0, x0 + dw, y0 + dh + 8, f'{width:.0f}" W')
    _dim_v(parts, x0 + dw + 12, y0, y0 + dh, f'{height:.0f}" H')
    if mode == "shop":
        parts.append(_text(x0, y0 + dh + 58, _shop_family_note(template), 8, "start", "700", "#8a5a00"))


def _draw_family_side(parts: list[str], template: TemplateDef, x: float, y: float, w: float, h: float, dims: dict[str, Any], mode: str) -> None:
    depth = dims["depth"]
    height = dims["height"]
    scale = min((w - 90) / max(depth, 1), (h - 112) / max(height, 1))
    dd = depth * scale
    dh = height * scale
    x0 = x + w / 2 - dd / 2
    y0 = y + 52 + (h - 112 - dh) / 2
    parts.append(_text(x + w / 2, y + 18, "SIDE ELEVATION", 11, weight="700"))
    if template.key == "chair":
        parts.append(_rect(x0, y0 + dh * 0.52, dd, dh * 0.28, 1.3, "#f7f4ef", "#111", 4))
        if dims.get("back_profile") in {"curved", "wingback"}:
            parts.append(f'<path d="M {x0 + dd * 0.42:.1f} {y0 + dh * 0.12:.1f} Q {x0 + dd * 0.83:.1f} {y0 + dh * 0.18:.1f} {x0 + dd:.1f} {y0 + dh * 0.55:.1f} L {x0 + dd * 0.7:.1f} {y0 + dh * 0.58:.1f} Q {x0 + dd * 0.56:.1f} {y0 + dh * 0.28:.1f} {x0 + dd * 0.42:.1f} {y0 + dh * 0.12:.1f} Z" fill="#fff" stroke="#111" stroke-width="1.4"/>')
        else:
            parts.append(f'<path d="M {x0 + dd * 0.65:.1f} {y0:.1f} L {x0 + dd:.1f} {y0 + dh * 0.55:.1f} L {x0 + dd * 0.7:.1f} {y0 + dh * 0.58:.1f} L {x0 + dd * 0.42:.1f} {y0 + dh * 0.12:.1f} Z" fill="#fff" stroke="#111" stroke-width="1.4"/>')
    else:
        parts.append(_rect(x0, y0, dd, dh, 1.4, "#fff", "#111"))
        if template.key == "shelving":
            shelf_count = max(2, min(8, int(dims["shelves"])))
            thickness = max(1.2, min(6, dims["material_thickness"] * scale))
            for i in range(1, shelf_count):
                py = y0 + dh * i / shelf_count
                parts.append(_rect(x0, py - thickness / 2, dd, thickness, 0.6, "#f8fafc", "#98a2b3"))
    _dim_h(parts, x0, x0 + dd, y0 + dh + 8, f'{depth:.0f}" D')
    if mode == "shop":
        _dim_v(parts, x0 + dd + 10, y0, y0 + dh, f'{height:.0f}" H')


def _draw_family_plan(parts: list[str], template: TemplateDef, x: float, y: float, w: float, h: float, dims: dict[str, Any], mode: str) -> None:
    width = dims["width"]
    depth = dims["depth"]
    scale = min((w - 110) / max(width, 1), (h - 90) / max(depth, 1))
    dw = width * scale
    dd = depth * scale
    x0 = x + w / 2 - dw / 2
    y0 = y + h / 2 - dd / 2 + 10
    parts.append(_text(x + w / 2, y + 18, "PLAN VIEW", 11, weight="700"))
    parts.append(_rect(x0, y0, dw, dd, 1.4, "#fff", "#111"))
    if template.key == "chair":
        parts.append(_rect(x0 + dw * 0.12, y0 + dd * 0.12, dw * 0.76, dd * 0.72, 0.9, "#f7f4ef", "#667085", 5))
    elif template.key == "banquette":
        cushion_count = max(2, min(6, int(width / 30)))
        for i in range(1, cushion_count):
            px = x0 + dw * i / cushion_count
            parts.append(_line(px, y0, px, y0 + dd, 0.8, "#98a2b3"))
        arm_config = dims.get("arm_configuration", "none")
        arm_d = max(8, dd * 0.22)
        if arm_config in {"left", "both"}:
            parts.append(_rect(x0, y0, arm_d, dd, 0.9, "none", "#667085"))
        if arm_config in {"right", "both"}:
            parts.append(_rect(x0 + dw - arm_d, y0, arm_d, dd, 0.9, "none", "#667085"))
    else:
        bay_count = max(1, min(6, round(width / max(dims.get("bay_spacing", 24), 1))))
        for i in range(1, bay_count):
            px = x0 + dw * i / bay_count
            parts.append(_line(px, y0, px, y0 + dd, 0.8, "#98a2b3"))
        parts.append(_text(x0 + dw / 2, y0 + dd / 2 + 4, f'{bay_count} BAY PLAN', 8, fill="#667085"))
    _dim_h(parts, x0, x0 + dw, y0 + dd + 6, f'{width:.0f}"')
    if mode == "shop":
        _dim_v(parts, x0 + dw + 10, y0, y0 + dd, f'{depth:.0f}"')


def _draw_family_perspective(parts: list[str], template: TemplateDef, style: str, x: float, y: float, w: float, h: float, dims: dict[str, Any]) -> None:
    parts.append(_text(x + w / 2, y + 18, "PERSPECTIVE", 11, weight="700"))
    cx = x + w / 2
    cy = y + h / 2
    if template.key == "chair":
        parts.append(f'<path d="M {cx - 58:.1f} {cy + 18:.1f} L {cx + 34:.1f} {cy:.1f} L {cx + 62:.1f} {cy + 48:.1f} L {cx - 28:.1f} {cy + 70:.1f} Z" fill="#f7f4ef" stroke="#111" stroke-width="1.2"/>')
        if dims.get("back_profile") in {"curved", "wingback"}:
            parts.append(f'<path d="M {cx - 4:.1f} {cy - 12:.1f} Q {cx + 36:.1f} {cy - 92:.1f} {cx + 58:.1f} {cy - 38:.1f} L {cx + 52:.1f} {cy + 10:.1f} Z" fill="#fff" stroke="#111" stroke-width="1.2"/>')
        else:
            parts.append(f'<path d="M {cx + 8:.1f} {cy - 70:.1f} L {cx + 58:.1f} {cy - 38:.1f} L {cx + 52:.1f} {cy + 10:.1f} L {cx - 4:.1f} {cy - 12:.1f} Z" fill="#fff" stroke="#111" stroke-width="1.2"/>')
    else:
        parts.append(f'<path d="M {cx - 78:.1f} {cy - 42:.1f} L {cx + 52:.1f} {cy - 64:.1f} L {cx + 86:.1f} {cy + 32:.1f} L {cx - 44:.1f} {cy + 58:.1f} Z" fill="#f8fafc" stroke="#111" stroke-width="1.2"/>')
        if template.key == "shelving":
            for i in range(3):
                parts.append(_line(cx - 60 + i * 38, cy - 48 + i * 2, cx - 30 + i * 38, cy + 48 + i * 2, 0.7, "#98a2b3"))
    parts.append(_text(cx, y + h - 16, f'{template.family} / {_title(style)}', 9, fill="#667085"))


def _shop_family_note(template: TemplateDef) -> str:
    if template.key == "banquette":
        return "VERIFY SEAT HEIGHT, TOE KICK, BACK PITCH, CUSHION BREAKS"
    if template.key == "chair":
        return "VERIFY FRAME WIDTH, SEAT DECK, ARM HEIGHT, BACK PITCH"
    return "VERIFY CARCASS, SHELF SPACING, MATERIAL THICKNESS, WALL CONDITIONS"


def _render_product_family_sheet(template: TemplateDef, style: str, name: str, dims: dict[str, Any], mode: str) -> str:
    w, h = 1320, 900
    margin = 34
    title = template.shop_rules["title"] if mode == "shop" else template.presentation_rules["title"]
    company = "EMPIRE WOODCRAFT" if template.key in {"banquette", "shelving"} else "EMPIRE WORKROOM"
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" style="font-family: Arial, Helvetica, sans-serif;">',
        '<rect width="1320" height="900" fill="#ffffff"/>',
        _rect(12, 12, w - 24, h - 24, 1.4, "none", "#111827"),
        _text(margin, 44, company, 16, "start", "800"),
        _text(margin, 65, title.upper(), 12, "start", "700", "#8a5a00"),
        _text(w - margin, 44, _esc(name).upper(), 15, "end", "800"),
        _text(w - margin, 65, template.family, 10, "end", "600", "#667085"),
    ]
    top_y = 86
    bottom_y = 568
    left_w = 620
    mid_w = 290
    right_w = 300
    parts.append(_rect(margin, top_y, left_w, 450, 0.6, "#fff", "#d0d5dd"))
    parts.append(_rect(margin + left_w + 24, top_y, mid_w, 450, 0.6, "#fff", "#d0d5dd"))
    parts.append(_rect(margin + left_w + mid_w + 48, top_y, right_w, 450, 0.6, "#fff", "#d0d5dd"))
    parts.append(_rect(margin, bottom_y, left_w, 210, 0.6, "#fff", "#d0d5dd"))
    parts.append(_rect(margin + left_w + 24, bottom_y, mid_w + right_w + 24, 210, 0.6, "#fff", "#d0d5dd"))

    _draw_family_front(parts, template, style, margin, top_y, left_w, 450, dims, mode)
    _draw_family_side(parts, template, margin + left_w + 24, top_y, mid_w, 450, dims, mode)
    _draw_family_perspective(parts, template, style, margin + left_w + mid_w + 48, top_y, right_w, 450, dims)
    _draw_family_plan(parts, template, margin, bottom_y, left_w, 210, dims, mode)

    spec_x = margin + left_w + 48
    spec_y = bottom_y + 34
    parts.append(_text(spec_x, spec_y, "PARAMETERS", 12, "start", "800"))
    spec_lines = [
        f'Style: {_title(style)}',
        f'Width: {dims["width"]:.0f}"',
        f'Depth: {dims["depth"]:.0f}"',
        f'Height: {dims["height"]:.0f}"',
    ]
    if template.key in {"banquette", "chair"}:
        spec_lines.extend([f'Seat height: {dims["seat_height"]:.0f}"', f'Back height: {dims["back_height"]:.0f}"'])
    if template.key == "banquette":
        spec_lines.extend([f'Arms: {str(dims["arm_configuration"]).replace("_", " ").title()}', f'Base: {str(dims["base_type"]).replace("_", " ").title()}'])
    if template.key == "chair":
        spec_lines.extend([f'Arm height: {dims["arm_height"]:.0f}"', f'Back profile: {str(dims["back_profile"]).replace("_", " ").title()}', f'Leg type: {str(dims["leg_type"]).replace("_", " ").title()}'])
    if template.key == "shelving":
        spec_lines.extend([f'Shelves: {dims["shelves"]:.0f}', f'Material: {dims["material_thickness"]:.2f}"', f'Bay spacing: {dims["bay_spacing"]:.0f}"', f'Doors: {str(dims["door_style"]).replace("_", " ").title()}'])
    spec_lines.append(_shop_family_note(template) if mode == "shop" else "Client-facing scale sheet for design review.")
    for i, line in enumerate(spec_lines):
        parts.append(_text(spec_x, spec_y + 26 + i * 20, line, 10, "start", "600" if i == 0 else "400", "#344054"))

    tb_x, tb_y, tb_w, tb_h = w - 382, h - 98, 348, 62
    parts.append(_rect(tb_x, tb_y, tb_w, tb_h, 1.1, "#fff", "#111827"))
    parts.append(_line(tb_x, tb_y + 22, tb_x + tb_w, tb_y + 22, 0.8))
    parts.append(_line(tb_x + 112, tb_y, tb_x + 112, tb_y + tb_h, 0.8))
    parts.append(_text(tb_x + 10, tb_y + 15, "PROJECT", 8, "start", "700", "#667085"))
    parts.append(_text(tb_x + 122, tb_y + 15, _esc(name).upper(), 8, "start", "700"))
    parts.append(_text(tb_x + 10, tb_y + 42, "SHEET", 8, "start", "700", "#667085"))
    parts.append(_text(tb_x + 122, tb_y + 42, f'{title} / NTS', 8, "start", "600"))
    parts.append("</svg>")
    return "\n".join(parts)


def _render_window_treatment_sheet(template: TemplateDef, style: str, name: str, dims: dict[str, float], params: dict[str, Any], mode: str) -> str:
    w, h = 1320, 900
    margin = 34
    title = template.shop_rules["title"] if mode == "shop" else template.presentation_rules["title"]
    stroke = "#111827"
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" style="font-family: Arial, Helvetica, sans-serif;">',
        '<rect width="1320" height="900" fill="#ffffff"/>',
        _rect(12, 12, w - 24, h - 24, 1.4, "none", stroke),
        _text(margin, 44, "EMPIRE WORKROOM", 16, "start", "800"),
        _text(margin, 65, title.upper(), 12, "start", "700", "#8a5a00"),
        _text(w - margin, 44, _esc(name).upper(), 15, "end", "800"),
        _text(w - margin, 65, template.family, 10, "end", "600", "#667085"),
    ]

    top_y = 86
    bottom_y = 568
    left_w = 640
    mid_w = 270
    right_w = 300
    parts.append(_rect(margin, top_y, left_w, 450, 0.6, "#fff", "#d0d5dd"))
    parts.append(_rect(margin + left_w + 24, top_y, mid_w, 450, 0.6, "#fff", "#d0d5dd"))
    parts.append(_rect(margin + left_w + mid_w + 48, top_y, right_w, 450, 0.6, "#fff", "#d0d5dd"))
    parts.append(_rect(margin, bottom_y, left_w, 210, 0.6, "#fff", "#d0d5dd"))
    parts.append(_rect(margin + left_w + 24, bottom_y, mid_w + right_w + 24, 210, 0.6, "#fff", "#d0d5dd"))

    _draw_front(parts, template, style, margin, top_y, left_w, 450, dims, mode)
    _draw_side(parts, margin + left_w + 24, top_y, mid_w, 450, dims, mode)
    _draw_perspective(parts, margin + left_w + mid_w + 48, top_y, right_w, 450, template, style)
    _draw_top(parts, margin, bottom_y, left_w, 210, dims, mode)

    spec_x = margin + left_w + 48
    spec_y = bottom_y + 34
    parts.append(_text(spec_x, spec_y, "PARAMETERS", 12, "start", "800"))
    spec_lines = [
        f'Style: {_title(style)}',
        f'Width: {dims["width"]:.0f}"',
        f'Drop: {dims["drop"]:.0f}"',
        f'Return: {dims["return"]:.1f}"',
    ]
    if template.key == "drapery":
        spec_lines.extend([f'Panels: {dims["panels"]:.0f}', f'Fullness: {dims["fullness"]:.1f}x'])
    if mode == "shop":
        spec_lines.extend(["Seams, hems, hardware, and lining to be verified before cut.", "Use field measure for final fabrication."])
    else:
        spec_lines.append("Client-facing scale sheet for design review.")
    for i, line in enumerate(spec_lines):
        parts.append(_text(spec_x, spec_y + 26 + i * 20, line, 10, "start", "600" if i == 0 else "400", "#344054"))

    tb_x, tb_y, tb_w, tb_h = w - 382, h - 98, 348, 62
    parts.append(_rect(tb_x, tb_y, tb_w, tb_h, 1.1, "#fff", "#111827"))
    parts.append(_line(tb_x, tb_y + 22, tb_x + tb_w, tb_y + 22, 0.8))
    parts.append(_line(tb_x + 112, tb_y, tb_x + 112, tb_y + tb_h, 0.8))
    parts.append(_text(tb_x + 10, tb_y + 15, "PROJECT", 8, "start", "700", "#667085"))
    parts.append(_text(tb_x + 122, tb_y + 15, _esc(name).upper(), 8, "start", "700"))
    parts.append(_text(tb_x + 10, tb_y + 42, "SHEET", 8, "start", "700", "#667085"))
    parts.append(_text(tb_x + 122, tb_y + 42, f'{title} / NTS', 8, "start", "600"))
    parts.append("</svg>")
    return "\n".join(parts)
