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
        default_dimensions={"width": 72, "height": 96, "drop": 96, "return": 3.5},
        editable_parameters=("width", "height", "drop", "return", "panels", "fullness"),
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
}


def get_template_for_style(style_key: str | None) -> TemplateDef | None:
    style = _norm(style_key)
    if style in DRAPERY_STYLES:
        return TEMPLATE_REGISTRY["drapery"]
    if style in ROMAN_STYLES:
        return TEMPLATE_REGISTRY["roman_shade"]
    if style in CORNICE_STYLES:
        return TEMPLATE_REGISTRY["cornice_valance"]
    return None


def render_template_instance(style_key: str, params: dict[str, Any]) -> dict[str, Any] | None:
    template = get_template_for_style(style_key)
    if not template:
        return None

    mode = _sheet_mode(params.get("drawing_mode") or params.get("mode"))
    dims = _merge_dimensions(template, params)
    name = params.get("name") or _title(style_key)
    svg = _render_window_treatment_sheet(template, style_key, name, dims, params, mode)
    return {
        "svg": svg,
        "item_type": "window",
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


def _merge_dimensions(template: TemplateDef, params: dict[str, Any]) -> dict[str, float]:
    dims = dict(template.default_dimensions)
    raw_dims = params.get("dimensions") or {}
    for key, default in list(dims.items()):
        dims[key] = _num(raw_dims.get(key, params.get(key)), default)
    dims["panels"] = _num(params.get("panels"), 2)
    dims["fullness"] = _num(params.get("fullness"), 2.5)
    dims["fold_spacing"] = _num(params.get("fold_spacing"), 7)
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
