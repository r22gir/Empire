"""Empire fabric codes for the viewer: code + color only.

Never expose brand, supplier, SKU, or notes. Color hex is derived from the
color name so Cognac looks cognac even when the CSV has no swatch.
"""

from __future__ import annotations

import colorsys
import hashlib
import os
import re
from pathlib import Path
from typing import Any, Optional

from app.services.fabric_code_catalog import client_view, csv_path, load_registry_rows

# Shop-known colors used by the Marley reference and common vinyls.
_NAMED_HEX = {
    "cognac": 0x8B4A1F,
    "charcoal": 0x2A2A2A,
    "black": 0x1C1C1C,
    "navy": 0x1E3A5F,
    "ivory": 0xE8D9B8,
    "cream": 0xEFE6D2,
    "sand": 0xC4A574,
    "taupe": 0x8B7355,
    "mushroom": 0x9A8B78,
    "forest": 0x2F4F3E,
    "emerald": 0x1F6B4A,
    "oxblood": 0x6B1D2A,
    "burgundy": 0x6B1D2A,
    "wine": 0x6B1D2A,
    "slate": 0x4A5560,
    "stone": 0xA39A8C,
    "greige": 0xB8B09A,
    "white": 0xF4F0E6,
    "offwhite": 0xF4F0E6,
    "gray": 0x6B6B6B,
    "grey": 0x6B6B6B,
    "brown": 0x6B3E1A,
    "tan": 0xC4A574,
    "camel": 0xC19A6B,
    "rust": 0xA3441A,
    "terracotta": 0xC45C32,
    "olive": 0x6B7A3A,
    "sage": 0x8A9A7A,
    "blush": 0xD4A5A0,
    "sky": 0x7BA3C4,
    "assigned": 0x8B4A1F,
}


def _color_key(color: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (color or "").lower())


def hex_for_color(color: str) -> int:
    key = _color_key(color)
    if key in _NAMED_HEX:
        return _NAMED_HEX[key]
    for name, value in _NAMED_HEX.items():
        if name in key or key in name:
            return value
    digest = hashlib.sha1(key.encode("utf-8")).digest()
    hue = digest[0] / 255.0
    r, g, b = colorsys.hls_to_rgb(hue, 0.38, 0.42)
    return (int(r * 255) << 16) | (int(g * 255) << 8) | int(b * 255)


def _split_code(code: str) -> tuple[str, str]:
    raw = (code or "").strip()
    if "-" in raw:
        prefix, color = raw.split("-", 1)
        return prefix, color
    return raw, ""


def display_code(code: str, color: str | None = None) -> str:
    """Client-facing label: V003-Cognac (code + color only)."""
    prefix, embedded = _split_code(code)
    color_part = (color or embedded or "").strip()
    if not color_part:
        return prefix
    if code.strip().endswith(color_part) and "-" in code:
        return code.strip()
    return f"{prefix}-{color_part}"


def viewer_swatches(rows: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Registry rows reduced to what the viewer may show."""
    source = rows if rows is not None else load_registry_rows()
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in source:
        safe = client_view(row)
        code = (safe.get("code") or "").strip()
        if not code or code in seen:
            continue
        seen.add(code)
        color = (safe.get("color") or _split_code(code)[1] or "Assigned").strip()
        label = display_code(code, color)
        tile = 6.0
        repeat_h = safe.get("pattern_repeat_h")
        if isinstance(repeat_h, (int, float)) and repeat_h > 0:
            tile = float(repeat_h)
        out.append(
            {
                "id": label,
                "code": label,
                "color": color,
                "hex": hex_for_color(color),
                "tileInches": tile,
                "widthInches": safe.get("width_inches") or 54,
            }
        )
    return out


def resolve_swatch(code: Optional[str], swatches: list[dict[str, Any]] | None = None) -> Optional[dict[str, Any]]:
    cleaned = (code or "").strip()
    if not cleaned:
        return None
    catalog = swatches if swatches is not None else viewer_swatches()
    for row in catalog:
        if row["code"] == cleaned or row["id"] == cleaned:
            return row
    prefix = _split_code(cleaned)[0]
    for row in catalog:
        if row["code"].startswith(prefix + "-") or row["code"] == prefix:
            return row
    # Unknown code: still show code+color, never invent a registry row.
    color = _split_code(cleaned)[1] or cleaned
    return {
        "id": display_code(cleaned, color),
        "code": display_code(cleaned, color),
        "color": color,
        "hex": hex_for_color(color),
        "tileInches": 6.0,
        "widthInches": 54,
        "uncoded": True,
    }


def fixture_csv_path() -> Path:
    override = os.getenv("EMPIRE_FABRIC_CODES_CSV")
    if override:
        return Path(override)
    return csv_path()
