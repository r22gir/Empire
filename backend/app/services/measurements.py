"""Inch measurement helpers — Empire workroom displays fractions, not decimals.

Sewing-friendly denominators: halves, quarters, eighths, sixteenths.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any


def inches_to_fraction(value: Any, max_denominator: int = 16) -> str:
    """Format a decimal inch value as a workroom fraction.

    4.75 -> '4 3/4"'
    0.125 -> '1/8"'
    36 -> '36"'
    None / blank -> '—'
    Already-fraction-like strings are returned as-is (with a trailing inch mark).
    """
    if value is None or value == "":
        return "—"
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return "—"
        if any(ch in text for ch in "/″\"'"):
            return text if text.endswith(('"', "″")) else f'{text}"'
        try:
            numeric = float(text)
        except ValueError:
            return text
    else:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return str(value)

    if numeric < 0:
        return f"-{inches_to_fraction(abs(numeric), max_denominator)}"

    frac = Fraction(numeric).limit_denominator(max_denominator)
    whole = frac.numerator // frac.denominator
    remainder = frac.numerator % frac.denominator
    if remainder == 0:
        return f'{whole}"'
    piece = f"{remainder}/{frac.denominator}"
    if whole == 0:
        return f'{piece}"'
    return f'{whole} {piece}"'


def pair_inches(width: Any, height: Any, max_denominator: int = 16) -> str:
    """Format a width × height pair in fractions."""
    return f"{inches_to_fraction(width, max_denominator)} × {inches_to_fraction(height, max_denominator)}"
