"""Empire internal fabric codes.

Format: V### / F### / L### plus a sanitized color — e.g. ``V042-Navy``.

Prefixes follow the workroom convention used on quote fabrics:
  V — upholstery (vinyl / seating goods)
  F — drapery and general cloth
  L — outdoor / leisure (Sunbrella-class)

``FABRIC_CODES`` is an optional override registry. When a vendor SKU is
already known (workspace-style hand registry), that code wins. Otherwise
the next free number for the category prefix is allocated.
"""

from __future__ import annotations

import re
from typing import Iterable

# Known SKU → Empire code. Additive. Do not invent codes for live jobs here.
FABRIC_CODES: dict[str, str] = {
    "V639": "V639-Spruce",
    "V638": "V638-Teak",
    "V1012": "V1012-Hazelnut",
    "R357": "F357-Natural",
    "SVI001": "V001-VintageAle",
    "5408-0000": "L001-Navy",
}

CATEGORY_PREFIX = {
    "Upholstery": "V",
    "Drapery": "F",
    "Outdoor": "L",
    "Other": "F",
}

_COLOR_RE = re.compile(r"[^A-Za-z0-9]+")
_CODE_RE = re.compile(r"^([VFL])(\d{3,})-([A-Za-z0-9]+)$")


def sanitize_color(color: str) -> str:
    cleaned = _COLOR_RE.sub("", (color or "").strip())
    return cleaned[:24] or "Undyed"


def lookup_known_code(sku: str | None, color: str | None = None) -> str | None:
    if not sku:
        return None
    key = str(sku).strip()
    if key in FABRIC_CODES:
        return FABRIC_CODES[key]
    if color:
        colored = f"{key}-{sanitize_color(color)}"
        if colored in FABRIC_CODES:
            return FABRIC_CODES[colored]
    return None


def parse_code(code: str) -> tuple[str, int, str] | None:
    match = _CODE_RE.match((code or "").strip())
    if not match:
        return None
    return match.group(1), int(match.group(2)), match.group(3)


def next_sequence(prefix: str, existing: Iterable[str]) -> int:
    highest = 0
    for code in existing:
        parsed = parse_code(code)
        if parsed and parsed[0] == prefix:
            highest = max(highest, parsed[1])
    return highest + 1


def allocate_empire_code(
    category: str,
    color: str,
    *,
    sku: str | None = None,
    existing_codes: Iterable[str] = (),
) -> str:
    known = lookup_known_code(sku, color)
    existing = {str(c) for c in existing_codes if c}
    if known and known not in existing:
        return known
    prefix = CATEGORY_PREFIX.get((category or "").strip() or "Other", "F")
    color_part = sanitize_color(color)
    n = next_sequence(prefix, existing)
    while True:
        code = f"{prefix}{n:03d}-{color_part}"
        if code not in existing:
            return code
        n += 1
