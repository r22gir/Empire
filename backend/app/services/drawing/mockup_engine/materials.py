"""Seat vs back finishes and client-facing fabric labels.

A revision that changes seat color must render seats in that color.
Client sheets never print supplier / brand names: use the Empire
internal fabric code + color (V003-Cognac) when the registry has it,
otherwise color + material type only.
"""
from __future__ import annotations

import re
from typing import Any, Optional

_SUPPLIER_MARKERS = (
    "kravet", "robert allen", "fabricut", "schumacher", "duralee",
    "spradling", "apex", "softside", "designtex", "maharam", "knoll",
    "osborne", "little", "stroheim", "bernstein", "supplier",
    "brand",
)

# Named upholstery colors → hex. Seat and back are looked up independently.
_COLOR_HEX = {
    "black": "#1A1A1A",
    "cognac": "#9A5B2E",
    "ivory": "#F3E6C8",
    "cream": "#F5E6C8",
    "white": "#F4F1EA",
    "navy": "#1B2A4A",
    "emerald": "#1B4D3E",
    "emerald green": "#1B4D3E",
    "warm brown": "#8B5A2B",
    "brown": "#6B3F1F",
    "tan": "#C4A574",
    "charcoal": "#2B2B2B",
    "grey": "#6B6F68",
    "gray": "#6B6F68",
    "red": "#8B1E1E",
    "burgundy": "#5C1A1A",
}

_DEFAULT_BACK_HEX = "#9A5B2E"
_DEFAULT_SEAT_HEX = "#A8693A"


def color_hex_for(name: str | None, *, role: str = "back") -> str:
    """Map a color word to a fill hex. Unknown names keep a role default."""
    key = re.sub(r"[^a-z ]+", "", (name or "").strip().lower())
    key = re.sub(r"\s+", " ", key)
    if key in _COLOR_HEX:
        return _COLOR_HEX[key]
    for token, hex_v in _COLOR_HEX.items():
        if token and token in key:
            return hex_v
    return _DEFAULT_SEAT_HEX if role == "seat" else _DEFAULT_BACK_HEX


def seam_hex_for(fill_hex: str) -> str:
    raw = (fill_hex or "").lstrip("#")
    if len(raw) != 6:
        return "#5E3518"
    try:
        r, g, b = int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)
    except ValueError:
        return "#5E3518"
    return f"#{max(0, r // 2):02X}{max(0, g // 2):02X}{max(0, b // 2):02X}"


def strip_supplier_text(text: str | None) -> str:
    cleaned = str(text or "").strip()
    if not cleaned:
        return ""
    low = cleaned.lower()
    if any(marker in low for marker in _SUPPLIER_MARKERS):
        return ""
    return cleaned


def _code_color_label(code: str | None, color: str | None) -> str:
    code = (code or "").strip()
    color = (color or "").strip()
    if code and color:
        if color.lower() in code.lower():
            return code
        return f"{code}-{color}"
    return code or color or ""


def client_facing_fabric_label(
    token: str | None,
    *,
    material_type: str = "vinyl",
    registry_rows: list[dict] | None = None,
) -> dict[str, Any]:
    """Resolve a color / V### token to a client-safe label. Never invent a code."""
    from app.services.drawing.job_drawing import resolve_internal_fabric

    resolved = dict(resolve_internal_fabric(token, registry_rows))
    color = (resolved.get("color") or (token or "").strip() or "").strip()
    code = resolved.get("code")
    kind = (material_type or resolved.get("material_type") or "vinyl").strip()
    if code:
        resolved["label"] = _code_color_label(str(code), color)
    elif color:
        resolved["label"] = f"{color} {kind}".strip()
    else:
        resolved["label"] = "TBC"
    resolved["material_type"] = kind
    resolved["color"] = color or None
    if strip_supplier_text(resolved["label"]) != resolved["label"]:
        resolved["label"] = f"{(color or 'TBC')} {kind}".strip()
    return resolved


def apply_seat_back_finish(
    material: Any,
    *,
    back: dict[str, Any] | None = None,
    seat: dict[str, Any] | None = None,
):
    """Write independent seat and back color / label onto a MaterialFinishSpec."""
    back = back or {}
    seat = seat or {}
    back_color = (back.get("color") or getattr(material, "color_name", None) or "cognac")
    seat_color = (seat.get("color") or getattr(material, "seat_color_name", None) or back_color)
    back_label = strip_supplier_text(back.get("label")) or _code_color_label(back.get("code"), back_color) or f"{back_color} vinyl"
    seat_label = strip_supplier_text(seat.get("label")) or _code_color_label(seat.get("code"), seat_color) or f"{seat_color} vinyl"
    material.color_name = str(back_color)
    material.seat_color_name = str(seat_color)
    material.color_hex = color_hex_for(str(back_color), role="back")
    material.seat_color_hex = color_hex_for(str(seat_color), role="seat")
    material.seam_color_hex = seam_hex_for(material.color_hex)
    material.name = back_label
    material.client_back_label = back_label
    material.client_seat_label = seat_label
    kind = (back.get("material_type") or seat.get("material_type") or getattr(material, "material_type", None) or "vinyl")
    try:
        material.material_type = kind
    except Exception:
        pass
    return material


def back_label_of(material: Any) -> str:
    return (
        strip_supplier_text(getattr(material, "client_back_label", None))
        or strip_supplier_text(getattr(material, "name", None))
        or (getattr(material, "color_name", None) or "back")
    )


def seat_label_of(material: Any) -> str:
    return (
        strip_supplier_text(getattr(material, "client_seat_label", None))
        or (getattr(material, "seat_color_name", None) or "")
        or (getattr(material, "color_name", None) or "seat")
    )
