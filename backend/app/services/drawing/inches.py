"""Shop-facing inch display.

Geometry and pricing keep floats. Quote sheets, idea sheets, and Max
drawing callouts print whole inches or fractions. Two-decimal strings
such as ``72.00"`` and ``14.50"`` are not shop language.

Banquette / job-drawing chat uses ``format_cut_inches`` (``249 3/4"``).
This helper stays the B1/B2 ASCII hyphen contract (``14-1/2"``) so
Helvetica title blocks keep eighths and sixteenths that standard PDF
fonts do not carry as glyphs.
"""
from __future__ import annotations

from math import gcd


def format_inches(value: float) -> str:
    """Format one inch measurement for a B1/B2 client or shop sheet.

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
