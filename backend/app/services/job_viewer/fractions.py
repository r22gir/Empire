"""Inch display for the 3D viewer: plain fractions, never decimals.

26.75 → '26 3/4\"'   18 → '18\"'   0.5 → '1/2\"'
"""

from app.services.pricing.dimensions import format_inches_plain


def inches_label(value) -> str:
    return format_inches_plain(value, with_mark=True)


def dims_label(dims) -> str:
    if not dims:
        return ""
    parts = [inches_label(v) for v in dims if v not in (None, "")]
    return " × ".join(p for p in parts if p)
