"""Inch formatting for Drawing Studio.

Every client-facing dimension is a whole number or an imperial fraction.
Never emit a decimal point in a dimension label (72.5" is illegal; 72 1/2" is required).
"""
from __future__ import annotations

import math
import re
from typing import Any

# Woodworking / upholstery stock: 1/16" is the finest mark we print.
_DENOM = 16
_FRACTION_RE = re.compile(
    r"""
    ^\s*
    (?P<sign>-)?
    (?:
        (?P<whole>\d+)\s+(?P<num>\d+)\s*/\s*(?P<den>\d+)
      | (?P<only_num>\d+)\s*/\s*(?P<only_den>\d+)
      | (?P<int_only>\d+(?:\.\d+)?)
    )
    \s*(?P<unit>"|in|inch|inches)?\s*$
    """,
    re.VERBOSE | re.IGNORECASE,
)


def format_inches(value: Any, mark: bool = True) -> str:
    """Format a numeric inch value as an imperial fraction.

    72      -> 72"
    22.5    -> 22 1/2"
    4.75    -> 4 3/4"
    0.375   -> 3/8"
    -1.25   -> -1 1/4"
    """
    try:
        inches = float(value)
    except (TypeError, ValueError):
        return '0"' if mark else "0"

    if not math.isfinite(inches):
        return '0"' if mark else "0"

    sign = "-" if inches < 0 else ""
    inches = abs(inches)
    sixteenths = int(round(inches * _DENOM))
    whole = sixteenths // _DENOM
    frac = sixteenths % _DENOM

    if frac == 0:
        body = str(whole)
    else:
        gcd = math.gcd(frac, _DENOM)
        num, den = frac // gcd, _DENOM // gcd
        body = f"{whole} {num}/{den}" if whole else f"{num}/{den}"

    if mark:
        return f'{sign}{body}"'
    return f"{sign}{body}"


def format_size(width: Any, length: Any, thickness: Any | None = None) -> str:
    """True-size cut label: 72" × 20" or 72" × 20" × 3/4"."""
    parts = [format_inches(width), format_inches(length)]
    if thickness is not None:
        parts.append(format_inches(thickness))
    return " × ".join(parts)


def parse_inches(value: Any, default: float = 0.0) -> float:
    """Parse '4 1/2"', '3/4', '72', or 22.5 into a float inch value."""
    if value is None or value == "":
        return default
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(float(value)) else default

    raw = str(value).strip().replace("″", '"').replace("”", '"').replace("'", "")
    match = _FRACTION_RE.match(raw)
    if not match:
        digits = re.sub(r"[^0-9./-]+", "", raw)
        try:
            return float(digits) if digits not in {"", ".", "-", "-."} else default
        except ValueError:
            return default

    sign = -1.0 if match.group("sign") else 1.0
    if match.group("whole") is not None:
        return sign * (int(match.group("whole")) + int(match.group("num")) / int(match.group("den")))
    if match.group("only_num") is not None:
        den = int(match.group("only_den"))
        if den == 0:
            return default
        return sign * (int(match.group("only_num")) / den)
    try:
        return sign * float(match.group("int_only"))
    except (TypeError, ValueError):
        return default


def has_decimal_dimension(text: str) -> bool:
    """True when a human-readable dimension label still contains a decimal inch."""
    return bool(re.search(r'\d+\.\d+\s*"', text or ""))
