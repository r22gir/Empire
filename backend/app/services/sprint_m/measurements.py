"""Workroom measurements are always displayed as inch fractions, never decimals."""

from __future__ import annotations

import math
import re
from fractions import Fraction
from typing import Any

FRACTION_DENOMS = (2, 4, 8, 16)


def inches_to_fraction(value: Any, *, unit: str = "in") -> str:
    """84.5 -> '84 1/2 in'; 96 -> '96 in'; 72.375 -> '72 3/8 in'."""
    if value is None or value == "":
        return ""
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return ""
        if "/" in text and not any(ch == "." for ch in text):
            cleaned = re.sub(r'["\']', "", text)
            cleaned = re.sub(r"\s*(in|inch|inches)\s*$", "", cleaned, flags=re.I)
            return f"{cleaned.strip()} {unit}".strip()
        try:
            number = float(re.sub(r"[^0-9.+-]", "", text.split()[0]))
        except (TypeError, ValueError):
            return text
    else:
        number = float(value)

    sign = "-" if number < 0 else ""
    number = abs(number)
    whole = int(math.floor(number + 1e-9))
    frac = number - whole
    if frac < 1e-6:
        body = str(whole)
    else:
        best = min(
            (Fraction(frac).limit_denominator(16) for _ in FRACTION_DENOMS),
            key=lambda f: abs(float(f) - frac),
        )
        # Snap to common workroom sixteenths.
        snapped = Fraction(round(frac * 16), 16)
        if abs(float(snapped) - frac) <= abs(float(best) - frac) + 1e-9:
            best = snapped
        if best.numerator == 0:
            body = str(whole)
        elif best.numerator == best.denominator:
            body = str(whole + 1)
        elif whole == 0:
            body = f"{best.numerator}/{best.denominator}"
        else:
            body = f"{whole} {best.numerator}/{best.denominator}"
    return f"{sign}{body} {unit}".strip()


def normalize_measurement(value: Any) -> dict[str, Any]:
    """Store both the numeric inches and the fraction display string."""
    if value is None or value == "":
        return {"inches": None, "display": ""}
    if isinstance(value, str) and "/" in value:
        text = re.sub(r'["\']', "", value)
        text = re.sub(r"\s*(in|inch|inches)\s*$", "", text, flags=re.I).strip()
        parts = text.split()
        try:
            if len(parts) == 2 and "/" in parts[1]:
                num, den = parts[1].split("/", 1)
                inches = float(parts[0]) + (float(num) / float(den))
            elif len(parts) == 1 and "/" in parts[0]:
                num, den = parts[0].split("/", 1)
                inches = float(num) / float(den)
            else:
                inches = float(re.sub(r"[^0-9.+-]", "", parts[0]))
        except (TypeError, ValueError, ZeroDivisionError):
            return {"inches": None, "display": inches_to_fraction(value)}
        return {"inches": round(inches, 4), "display": inches_to_fraction(inches)}
    try:
        inches = float(value)
    except (TypeError, ValueError):
        return {"inches": None, "display": str(value)}
    return {"inches": round(inches, 4), "display": inches_to_fraction(inches)}


def normalize_dimensions(raw: dict | None) -> dict:
    dims = raw or {}
    out = {}
    for key in ("width", "height", "depth", "return", "overlap"):
        if key in dims and dims[key] not in (None, ""):
            out[key] = normalize_measurement(dims[key])
    return out
