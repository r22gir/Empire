"""Shop-facing inch display.

Geometry and pricing keep floats. Quote sheets, idea sheets, and Max
drawing callouts print whole inches or fractions. Two-decimal strings
such as ``72.00"`` and ``14.50"`` are not shop language.

This is the same 1/16" contract already used on B1/B2 sheets
(``72"``, ``14-1/2"``, ``6-1/4"``). Hyphen fractions stay in ASCII so
Helvetica title blocks and SVG callouts match, including eighths and
sixteenths that standard PDF fonts do not carry as glyphs.
"""
from __future__ import annotations

from math import gcd


def format_inches(value: float) -> str:
    """Format one inch measurement for a client or shop sheet.

    Examples:
      72     → 72"
      72.00  → 72"
      14.5   → 14-1/2"
      6.25   → 6-1/4"
      0.5    → 1/2"
    """
    sixteenths = round(float(value) * 16)
    whole = sixteenths // 16
    rem = sixteenths - whole * 16
    if rem == 0:
        return f'{whole}"' if whole else '0"'
    g = gcd(rem, 16)
    n = rem // g
    d = 16 // g
    if whole:
        return f'{whole}-{n}/{d}"'
    return f'{n}/{d}"'
