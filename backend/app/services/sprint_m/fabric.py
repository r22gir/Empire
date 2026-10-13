"""Internal fabric codes only: V###-Color. Never brand or supplier names."""

from __future__ import annotations

import re

# V639-Navy, V12-Ivory, V1000-Soft Gold
INTERNAL_CODE_RE = re.compile(
    r"^V(\d{3,})\s*[-–]\s*([A-Za-z][A-Za-z0-9 /&'-]{0,40})$",
    re.IGNORECASE,
)
EXTRACT_RE = re.compile(
    r"\bV(\d{3,})\s*[-–]?\s*([A-Za-z][A-Za-z0-9 /&'-]{0,40})",
    re.IGNORECASE,
)

# Words that must never appear in a stored fabric field.
FORBIDDEN_BRAND_TOKENS = {
    "kravet",
    "fabricut",
    "schumacher",
    "brunschwig",
    "lee",
    "jofa",
    "pindler",
    "osborne",
    "little",
    "supplier",
    "wholesaler",
    "vendor",
    "robert",
    "allen",
    "designers",
    "guild",
    "www",
    "http",
    "https",
    ".com",
    "inc",
    "llc",
    "wholesale",
    "retailer",
    "mill",
    "house",
    "collection",
}


class FabricCodeError(ValueError):
    """Raised when a fabric value cannot be reduced to V###-Color."""


def is_internal_fabric_code(value: str | None) -> bool:
    if not value:
        return False
    return bool(INTERNAL_CODE_RE.match(value.strip()))


def _title_color(raw: str) -> str:
    color = re.sub(r"\s+", " ", raw.strip())
    color = re.sub(r"[^A-Za-z0-9 /&'-]", "", color)
    # Drop trailing brand-like leftovers after the color token.
    parts = [p for p in color.split(" ") if p and p.lower() not in FORBIDDEN_BRAND_TOKENS]
    if not parts:
        raise FabricCodeError("fabric color missing after sanitizing brand/supplier tokens")
    return " ".join(p.capitalize() if p.islower() else p for p in parts[:4])


def sanitize_fabric_code(raw: str | None, *, required: bool = False) -> str | None:
    """Return V###-Color or None. Never returns brand or supplier text."""
    if raw is None:
        if required:
            raise FabricCodeError("fabric code is required")
        return None
    text = str(raw).strip()
    if not text:
        if required:
            raise FabricCodeError("fabric code is required")
        return None

    match = INTERNAL_CODE_RE.match(text) or EXTRACT_RE.search(text)
    if not match:
        if required:
            raise FabricCodeError(
                f"fabric must be internal code V###-Color (got {text!r}); brand/supplier names are forbidden"
            )
        return None

    number, color = match.group(1), _title_color(match.group(2))
    code = f"V{number}-{color}"
    lowered = code.lower()
    if any(token in lowered for token in FORBIDDEN_BRAND_TOKENS if len(token) > 3):
        raise FabricCodeError("sanitized fabric code still contained a brand or supplier token")
    return code
