"""Shop-inch fractions.

Internal math uses integer sixteenths so kerf and grain never depend on
binary floats. Every public measurement is a fraction string such as
``29 1/2"`` or ``1/8"``. Decimal output is forbidden.
"""
from __future__ import annotations

from fractions import Fraction
from math import gcd
import re
from typing import Any

SIXTEENTHS_PER_INCH = 16

_FRACTION_RE = re.compile(
    r"""
    ^\s*
    (?P<sign>-)?
    (?:
        (?P<whole>\d+)\s+(?P<num>\d+)\s*/\s*(?P<den>\d+)
      | (?P<hyphen_whole>\d+)\s*-\s*(?P<hyphen_num>\d+)\s*/\s*(?P<hyphen_den>\d+)
      | (?P<only_num>\d+)\s*/\s*(?P<only_den>\d+)
      | (?P<int_only>\d+)
    )
    \s*"?\s*$
    """,
    re.VERBOSE,
)


class InchFormatError(ValueError):
    """Raised when a size cannot be expressed as a shop fraction."""


def sixteenths_to_fraction(sixteenths: int) -> Fraction:
    return Fraction(int(sixteenths), SIXTEENTHS_PER_INCH)


def format_inches(value: Any) -> str:
    """Format sixteenths, a Fraction, or a parseable string as a shop inch.

    Examples: 472 → ``29 1/2"``; 2 → ``1/8"``; 0 → ``0"``.
    Never emits a decimal point.
    """
    if isinstance(value, str):
        if value.strip() in {"", "0", "0\""}:
            return '0"'
        sixteenths = parse_inches(value)
    elif isinstance(value, Fraction):
        sixteenths = _fraction_to_sixteenths(value)
    else:
        sixteenths = int(value)
    sign = "-" if sixteenths < 0 else ""
    sixteenths = abs(sixteenths)
    whole, rem = divmod(sixteenths, SIXTEENTHS_PER_INCH)
    if rem == 0:
        return f'{sign}{whole}"'
    g = gcd(rem, SIXTEENTHS_PER_INCH)
    n = rem // g
    d = SIXTEENTHS_PER_INCH // g
    if whole:
        text = f'{sign}{whole} {n}/{d}"'
    else:
        text = f'{sign}{n}/{d}"'
    if "." in text:
        raise InchFormatError(f"decimal leaked into shop inch: {text!r}")
    return text


def parse_inches(value: Any) -> int:
    """Parse a shop size into integer sixteenths.

    Accepts ``29 1/2``, ``29-1/2"``, ``1/8``, ``36``, and (input only)
    a Python float/Decimal so callers can hand in existing numeric data.
    Floats are rounded to the nearest 1/16". Parsed output is still
    always formatted as a fraction.
    """
    if value is None or value == "":
        raise InchFormatError("empty inch value")
    if isinstance(value, bool):
        raise InchFormatError("boolean is not a size")
    if isinstance(value, int):
        # Bare ints are treated as whole inches (shop input), not sixteenths.
        return value * SIXTEENTHS_PER_INCH
    if isinstance(value, Fraction):
        return _fraction_to_sixteenths(value)
    if isinstance(value, float):
        return int(round(float(value) * SIXTEENTHS_PER_INCH))
    text = str(value).strip().replace("″", '"').replace("”", '"')
    if text.endswith("in"):
        text = text[:-2].strip()
    match = _FRACTION_RE.match(text)
    if not match:
        # Last-resort numeric input (legacy JSON). Never used for output.
        try:
            return int(round(float(text) * SIXTEENTHS_PER_INCH))
        except (TypeError, ValueError) as exc:
            raise InchFormatError(f"cannot parse inch value {value!r}") from exc
    sign = -1 if match.group("sign") else 1
    if match.group("whole") is not None:
        whole = int(match.group("whole"))
        num = int(match.group("num"))
        den = int(match.group("den"))
    elif match.group("hyphen_whole") is not None:
        whole = int(match.group("hyphen_whole"))
        num = int(match.group("hyphen_num"))
        den = int(match.group("hyphen_den"))
    elif match.group("only_num") is not None:
        whole = 0
        num = int(match.group("only_num"))
        den = int(match.group("only_den"))
    else:
        whole = int(match.group("int_only"))
        num = 0
        den = 1
    if den <= 0:
        raise InchFormatError(f"invalid denominator in {value!r}")
    frac = Fraction(whole) + Fraction(num, den)
    return sign * _fraction_to_sixteenths(frac)


def _fraction_to_sixteenths(frac: Fraction) -> int:
    scaled = frac * SIXTEENTHS_PER_INCH
    if scaled.denominator != 1:
        # Round to nearest sixteenth; shop work is 1/16" resolution.
        return int(round(float(scaled)))
    return int(scaled)


def yield_fraction(used_sixteenths_sq: int, total_sixteenths_sq: int) -> str:
    """Per-sheet yield as a simplified proper/improper fraction, never a decimal."""
    if total_sixteenths_sq <= 0:
        return "0/1"
    frac = Fraction(max(0, used_sixteenths_sq), total_sixteenths_sq)
    if frac > 1:
        frac = Fraction(1, 1)
    text = f"{frac.numerator}/{frac.denominator}"
    if "." in text:
        raise InchFormatError(f"decimal leaked into yield: {text!r}")
    return text


def assert_no_decimal_measurements(payload: Any) -> None:
    """Walk a nest result and fail if any public size/yield has a decimal point."""
    keys = {
        "width", "length", "height", "kerf", "blade_width", "thickness",
        "x", "y", "used_width", "used_length", "sheet_width", "sheet_length",
        "tile_length", "machine_width", "wood_width", "wood_length",
        "foam_width", "foam_length", "fabric_width", "fabric_length",
        "yield", "yield_fraction", "leftover_width", "leftover_length",
        "mark_size", "inset",
    }
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in keys and isinstance(value, str) and "." in value:
                raise InchFormatError(f"{key} must be a fraction, got {value!r}")
            if key in keys and isinstance(value, float):
                raise InchFormatError(f"{key} must not be a float, got {value!r}")
            assert_no_decimal_measurements(value)
    elif isinstance(payload, list):
        for item in payload:
            assert_no_decimal_measurements(item)
