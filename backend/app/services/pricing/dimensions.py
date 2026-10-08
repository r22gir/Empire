"""Inch display for quotes and PDFs.

Whole inches stay whole. Fractional inches render as fractions
(14.5 → 14½", 72.00 → 72"), never as decimals.
"""
from __future__ import annotations

import math
import re

# Nearest sixteenth, with the common shop fractions as single glyphs.
_SIXTEENTHS = {
    1: "1/16",
    2: "⅛",
    3: "3/16",
    4: "¼",
    5: "5/16",
    6: "⅜",
    7: "7/16",
    8: "½",
    9: "9/16",
    10: "⅝",
    11: "11/16",
    12: "¾",
    13: "13/16",
    14: "⅞",
    15: "15/16",
}

_INCH_UNITS = {"in", "inch", "inches", '"', "''"}


def format_inches(value, *, with_mark: bool = True) -> str:
    """Format a length in inches. Empty input returns an empty string."""
    if value is None or value == "":
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    if math.isnan(number) or math.isinf(number):
        return ""

    sign = "-" if number < 0 else ""
    number = abs(number)
    whole = math.floor(number + 1e-9)
    sixteenths = int(round((number - whole) * 16))
    if sixteenths == 16:
        whole += 1
        sixteenths = 0
    mark = '"' if with_mark else ""
    if sixteenths == 0:
        return f"{sign}{whole}{mark}"
    frac = _SIXTEENTHS[sixteenths]
    if whole == 0:
        return f"{sign}{frac}{mark}"
    if "/" in frac:  # '14 3/16"', never the ambiguous '143/16"'
        return f"{sign}{whole} {frac}{mark}"
    return f"{sign}{whole}{frac}{mark}"


_GLYPH_PLAIN = {"⅛": "1/8", "¼": "1/4", "⅜": "3/8", "½": "1/2", "⅝": "5/8", "¾": "3/4", "⅞": "7/8",
                "⅓": "1/3", "⅔": "2/3", "⅙": "1/6", "⅚": "5/6", "⅕": "1/5"}
_GLYPH_RE = re.compile(r"(\d)?[ \u2009\u00a0]?([" + "".join(_GLYPH_PLAIN) + r"])")


def plain_fractions(text: str) -> str:
    """'26¾"' -> '26 3/4"': fractions as plain text (Rafael 2026-10-08), never glyphs."""
    if not text:
        return text or ""
    def _sub(m: "re.Match[str]") -> str:
        if m.group(1):
            return m.group(1) + " " + _GLYPH_PLAIN[m.group(2)]
        return m.group(0)[:-1] + _GLYPH_PLAIN[m.group(2)]  # keep the space before a bare glyph
    return _GLYPH_RE.sub(_sub, text)


def format_inches_plain(value, *, with_mark: bool = True) -> str:
    """Like format_inches but with plain-text fractions: 26.75 -> '26 3/4"'."""
    return plain_fractions(format_inches(value, with_mark=with_mark))


def _trim_number(value) -> str:
    number = float(value)
    text = f"{number:.4f}".rstrip("0").rstrip(".")
    return text or "0"


def quote_item_dimension_text(item: dict | None) -> str:
    """Customer-facing dimension phrase for a quote line (inches)."""
    item = item or {}
    parts = []
    for key in ("width", "height", "depth"):
        raw = item.get(key)
        if raw in (None, "", 0, 0.0):
            continue
        formatted = format_inches(raw)
        if formatted:
            parts.append(formatted)
    return " × ".join(parts)


def format_design_dimensions(width=None, height=None, depth=None, unit: str = "in") -> str:
    """WoodCraft quote/PDF dimension line. Inches use fractions; other units do not."""
    inch = (unit or "in").strip().lower() in _INCH_UNITS
    suffix = "" if inch else (unit or "").strip()
    parts = []
    for label, raw in (("W", width), ("H", height), ("D", depth)):
        if raw in (None, "", 0, 0.0):
            continue
        if inch:
            parts.append(f"{format_inches(raw)} {label}")
        else:
            parts.append(f"{_trim_number(raw)}{suffix} {label}")
    return " × ".join(parts)
