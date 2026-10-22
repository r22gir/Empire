"""Seat vs back finish, client-facing fabric labels, named color hex.

Seat material/color and back material/color are separate inputs. A revision
that changes only the seat color must render seats in that color (legend,
plan, elevations). Client sheets never print supplier / mill brand names.
"""
from __future__ import annotations

import re
from typing import Any, Optional

# Named colors used on banquettes. Black must read dark next to cognac.
NAMED_FINISH_HEX: dict[str, str] = {
    "black": "#1A1A1A",
    "cognac": "#9A5B2E",
    "white": "#F4F1EA",
    "ivory": "#F3E6C8",
    "cream": "#F5E6C8",
    "navy": "#1B2A4A",
    "charcoal": "#2B2B2B",
    "brown": "#6B3F24",
    "tan": "#C4A574",
    "gray": "#6E6E6E",
    "grey": "#6E6E6E",
    "saddle": "#8B5A2B",
}

_SUPPLIER_MARKERS = (
    "kravet", "robert allen", "fabricut", "schumacher", "duralee",
    "spradling", "apex", "softside", "designtex", "maharam", "knoll",
    "osborne", "little", "stroheim", "bernstein", "supplier",
    "keyston", "charlotte fabrics", "gp&j", "baker",
)

_BRAND_IN_PARENS = re.compile(r"\([^)]*(?:spradling|apex|softside|kravet|maharam)[^)]*\)", re.I)


def luminance(hex_color: str) -> float:
    """Relative luminance 0..1. Black seats must be clearly darker than cognac."""
    s = (hex_color or "").strip().lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if len(s) != 6:
        return 0.5
    r, g, b = int(s[0:2], 16) / 255.0, int(s[2:4], 16) / 255.0, int(s[4:6], 16) / 255.0
    return 0.299 * r + 0.587 * g + 0.114 * b


def is_dark_hex(hex_color: str) -> bool:
    return luminance(hex_color) < 0.22


def color_hex_for_name(name: str | None, fallback: str = "#9A5B2E") -> str:
    """Resolve a spoken / registry color to a fill hex. Black → dark."""
    raw = (name or "").strip().lower()
    if not raw:
        return fallback
    if raw.startswith("#") and len(raw) in (4, 7):
        return raw.upper() if len(raw) == 7 else "#" + "".join(ch * 2 for ch in raw[1:]).upper()
    key = re.sub(r"[^a-z]+", "", raw)
    if key in NAMED_FINISH_HEX:
        return NAMED_FINISH_HEX[key]
    for token, hex_val in NAMED_FINISH_HEX.items():
        if token in raw.split() or token == key:
            return hex_val
    return fallback


def strip_supplier_brand(text: str | None) -> str:
    cleaned = str(text or "").strip()
    if not cleaned:
        return ""
    cleaned = _BRAND_IN_PARENS.sub("", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" -·,")
    low = cleaned.lower()
    if any(marker in low for marker in _SUPPLIER_MARKERS):
        return ""
    return cleaned


def client_facing_label(
    *,
    code: str | None = None,
    color: str | None = None,
    material_type: str | None = None,
    fallback: str = "TBC — CONFIRM BEFORE CUT",
) -> str:
    """Empire internal code + color (V003-Cognac), else color + material type.

    Never a mill / supplier brand.
    """
    code_s = strip_supplier_brand(code)
    color_s = strip_supplier_brand(color)
    mat = strip_supplier_brand(material_type)
    if code_s and re.match(r"^V\d{3}-", code_s, re.I):
        return code_s
    if code_s and color_s:
        return f"{code_s}-{color_s}" if color_s.lower() not in code_s.lower() else code_s
    if color_s and mat:
        return f"{color_s} {mat}"
    return color_s or mat or fallback


def effective_seat_color_name(material: Any) -> str:
    seat = str(getattr(material, "seat_color_name", "") or "").strip()
    if seat:
        return seat
    return str(getattr(material, "color_name", "") or "").strip()


def back_client_label(material: Any) -> str:
    code = getattr(material, "fabric_code", None)
    color = getattr(material, "color_name", None)
    mat = getattr(material, "material_type", None)
    named = strip_supplier_brand(getattr(material, "name", None))
    label = client_facing_label(code=code, color=color, material_type=mat)
    if label and label != "TBC — CONFIRM BEFORE CUT":
        return label
    return named or label


def seat_client_label(material: Any) -> str:
    code = getattr(material, "seat_fabric_code", None)
    color = effective_seat_color_name(material)
    mat = getattr(material, "seat_material_type", None) or getattr(material, "material_type", None)
    return client_facing_label(code=code, color=color, material_type=mat)


def apply_seat_back_finish(
    material: Any,
    *,
    back: Optional[dict[str, Any]] = None,
    seat: Optional[dict[str, Any]] = None,
) -> Any:
    """Write separate seat / back fields onto a MaterialFinishSpec (in place)."""
    back = back or {}
    seat = seat or {}
    back_color = back.get("color") or getattr(material, "color_name", None)
    seat_color = seat.get("color")
    back_code = back.get("code")
    seat_code = seat.get("code")
    back_mat = back.get("material_type") or getattr(material, "material_type", None)
    seat_mat = seat.get("material_type") or back_mat

    if back_color:
        material.color_name = str(back_color)
        material.color_hex = color_hex_for_name(str(back_color), getattr(material, "color_hex", "#9A5B2E"))
    if back_code:
        material.fabric_code = back_code
    if back_mat:
        material.material_type = back_mat
    material.name = client_facing_label(
        code=back_code or getattr(material, "fabric_code", None),
        color=getattr(material, "color_name", None),
        material_type=getattr(material, "material_type", None),
        fallback=strip_supplier_brand(getattr(material, "name", "")) or "vinyl",
    )

    if seat_color:
        material.seat_color_name = str(seat_color)
        material.seat_color_hex = color_hex_for_name(str(seat_color), "#1A1A1A")
        material.seat_material_type = seat_mat
        if seat_code:
            material.seat_fabric_code = seat_code
    elif not getattr(material, "seat_color_name", None):
        material.seat_color_name = getattr(material, "color_name", "") or ""
    return material
