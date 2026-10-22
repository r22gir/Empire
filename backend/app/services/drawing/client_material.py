"""Client-facing fabric labels for drawings.

Seat and back are separate. Client sheets print Empire internal code + color
(e.g. V100-Cognac) or color + material type. Never brand / supplier names.
"""
from __future__ import annotations

import re
from typing import Any, Optional

SUPPLIER_MARKERS = (
    "kravet", "robert allen", "fabricut", "schumacher", "duralee",
    "spradling", "apex", "softside", "designtex", "maharam", "knoll",
    "osborne", "little", "stroheim", "bernstein", "supplier", "brand",
    "wholesale", "mill",
)

COLOR_HEX = {
    "cognac": "#9A5B2E",
    "black": "#1C1C1C",
    "navy": "#1B3A4B",
    "emerald": "#1B4D3E",
    "green": "#225F4D",
    "brown": "#8B5A2B",
    "walnut": "#8B5A2B",
    "tan": "#C4A574",
    "cream": "#E8D9B8",
    "white": "#F4F0E6",
    "charcoal": "#2B2B2B",
    "grey": "#6B6F68",
    "gray": "#6B6F68",
}

_CODE_RE = re.compile(r"^V\d{3}-[A-Za-z0-9]+$", re.I)


def strip_supplier_names(text: str | None) -> str:
    cleaned = str(text or "").strip()
    if not cleaned:
        return ""
    low = cleaned.lower()
    if any(marker in low for marker in SUPPLIER_MARKERS):
        return ""
    return cleaned


def color_hex_for(name: str | None, default: str = "#9A5B2E") -> str:
    key = re.sub(r"[^a-z]", "", (name or "").lower())
    if key in COLOR_HEX:
        return COLOR_HEX[key]
    for token, hex_v in COLOR_HEX.items():
        if token in key:
            return hex_v
    return default


def client_facing_label(
    token: str | None = None,
    *,
    color: str | None = None,
    material_type: str | None = None,
    code: str | None = None,
    registry_rows: list[dict] | None = None,
) -> str:
    """V###-Color from the registry when known; else color + material type."""
    from app.services.drawing.job_drawing import resolve_internal_fabric

    raw = (code or token or color or "").strip()
    resolved = resolve_internal_fabric(raw, registry_rows)
    found_code = str(resolved.get("code") or "").strip()
    found_color = strip_supplier_names(str(resolved.get("color") or color or "").strip())
    if found_code and not any(m in found_code.lower() for m in SUPPLIER_MARKERS):
        return found_code
    mat = (material_type or "").strip()
    if found_color and mat:
        return f"{found_color} {mat}"
    if found_color:
        return found_color
    cleaned = strip_supplier_names(raw)
    if cleaned and not _CODE_RE.match(cleaned):
        return cleaned
    return (mat or "TBC").strip()


def apply_seat_back_materials(
    material,
    *,
    back: dict[str, Any] | None = None,
    seat: dict[str, Any] | None = None,
    material_type: str | None = None,
) -> Any:
    """Write separate seat/back color, hex, and client labels onto a MaterialFinishSpec."""
    back = back or {}
    seat = seat or {}
    mat = material_type or getattr(material, "material_type", None) or "vinyl"
    back_color = str(back.get("color") or back.get("label") or getattr(material, "color_name", "") or "").strip()
    seat_color = str(seat.get("color") or seat.get("label") or getattr(material, "seat_color_name", "") or "").strip()
    back_code = str(back.get("code") or "").strip() or None
    seat_code = str(seat.get("code") or "").strip() or None
    material.fabric_code = back_code or ""
    material.seat_fabric_code = seat_code or ""
    material.color_name = back_color or material.color_name
    material.seat_color_name = seat_color or back_color or material.color_name
    material.color_hex = color_hex_for(back_color, getattr(material, "color_hex", "#9A5B2E"))
    material.seat_color_hex = color_hex_for(seat_color or back_color, getattr(material, "seat_color_hex", "#1C1C1C"))
    material.name = client_facing_label(
        back_code or back_color, color=back_color, material_type=mat, code=back_code,
    )
    return material
