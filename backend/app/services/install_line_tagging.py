"""Detect installation quote/invoice lines and parse window count + linear feet.

On save, install descriptions are tagged item_type='installation' with
nullable windows (int) and lf (width inches / 12). Historical imported
docs (812-C, 838, 897, 909, 803-A, …) are included by the backfill and
by on-read tagging in compare_install_prices.

Measurements stay fractions in display helpers — never decimal inches/feet.
"""
from __future__ import annotations

import json
import math
import re
from fractions import Fraction
from typing import Any, Iterable, Optional

# Legacy paper / imported estimate numbers the founder still cites by hand.
LEGACY_DOC_NUMBERS = ("812-C", "838", "897", "909", "803-A")
LEGACY_DOC_RE = re.compile(r"\b(\d{3,4}(?:-[A-Za-z])?)\b", re.I)

_INSTALL_PHRASES = (
    r"removal\s+and\s+installation",
    r"remove\s+existing\s+track\s+and\s+install",
    r"hourly\s+install(?:ation)?",
    r"re-?install(?:ation|ing|ed)?",
    r"install(?:ation|ing|ed)?",
)
_INSTALL_RE = re.compile(r"(?:%s)" % "|".join(_INSTALL_PHRASES), re.I)

_WINDOWS_RE = re.compile(
    r"(?P<n>\d+)\s*(?:windows?|wnds?)\b"
    r"|(?:windows?|wnds?)\s*[:=]?\s*(?P<n2>\d+)",
    re.I,
)
_LF_LABEL_RE = re.compile(
    r"(?P<n>\d+(?:\s+\d+/\d+)?|\d+/\d+|\d+(?:\.\d+)?)\s*"
    r"(?:lf\b|lin(?:ear)?\s*(?:ft|feet|foot)\.?)",
    re.I,
)
_WIDTH_IN_RE = re.compile(
    r'(?P<n>\d+(?:\s+\d+/\d+)?|\d+/\d+|\d+(?:\.\d+)?)'
    r'\s*(?:["”]|in(?:ch(?:es)?)?)'
    r'(?:\s*(?:wall|track|opening|width|wide))?',
    re.I,
)
_FRACTION_RE = re.compile(
    r"^\s*(?P<sign>-)?(?:(?P<whole>\d+)\s+)?(?:(?P<num>\d+)\s*/\s*(?P<den>\d+)|(?P<dec>\d+(?:\.\d+)?))\s*$"
)

_WINDOW_UNITS = {"window", "windows", "wnd", "wnds", "opening", "openings"}


def ensure_install_columns(conn) -> None:
    """Idempotent windows / lf columns on quote_line_items."""
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(quote_line_items)").fetchall()}
    except Exception:
        return
    for name, decl in (("windows", "INTEGER"), ("lf", "REAL")):
        if name in cols:
            continue
        try:
            conn.execute(f"ALTER TABLE quote_line_items ADD COLUMN {name} {decl}")
        except Exception:
            pass


def parse_mixed_number(value: Any) -> Optional[float]:
    """Parse 13, 13.0, '13 1/3', '1/3', 160."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if math.isnan(value) or math.isinf(value):
            return None
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    m = _FRACTION_RE.match(text)
    if not m:
        try:
            return float(text)
        except (TypeError, ValueError):
            return None
    sign = -1.0 if m.group("sign") else 1.0
    if m.group("num") and m.group("den"):
        den = float(m.group("den"))
        if den == 0:
            return None
        whole = float(m.group("whole") or 0)
        return sign * (whole + (float(m.group("num")) / den))
    try:
        return sign * float(m.group("dec"))
    except (TypeError, ValueError):
        return None


def format_feet(value: Any) -> str:
    """13 1/3 ft — never a decimal foot label."""
    number = parse_mixed_number(value)
    if number is None:
        return "—"
    sign = "-" if number < 0 else ""
    number = abs(number)
    frac = Fraction(number).limit_denominator(16)
    whole, rem = divmod(frac.numerator, frac.denominator)
    if rem == 0:
        return f"{sign}{whole} ft"
    if whole == 0:
        return f"{sign}{rem}/{frac.denominator} ft"
    return f"{sign}{whole} {rem}/{frac.denominator} ft"


def format_inches(value: Any) -> str:
    """160\" or 14 1/2\" — never a decimal inch label."""
    from app.services.pricing.dimensions import format_inches_plain

    number = parse_mixed_number(value)
    if number is None:
        return "—"
    return format_inches_plain(number, with_mark=True)


def is_install_line(
    description: Any = None,
    *,
    item_type: Any = None,
    category: Any = None,
    labor_description: Any = None,
) -> bool:
    itype = str(item_type or "").strip().lower()
    cat = str(category or "").strip().lower()
    if itype in {"installation", "install"} or cat in {"installation", "install"}:
        return True
    blob = " ".join(
        str(part) for part in (description, labor_description) if part
    )
    if not blob.strip():
        return False
    return bool(_INSTALL_RE.search(blob))


def parse_windows(description: Any = None, *, quantity: Any = None, unit: Any = None, explicit: Any = None) -> Optional[int]:
    if explicit not in (None, ""):
        n = parse_mixed_number(explicit)
        if n is not None and n > 0:
            return int(round(n))
    text = str(description or "")
    m = _WINDOWS_RE.search(text)
    if m:
        raw = m.group("n") or m.group("n2")
        if raw:
            return int(raw)
    unit_l = str(unit or "").strip().lower()
    if unit_l in _WINDOW_UNITS:
        qty = parse_mixed_number(quantity)
        if qty is not None and qty > 0:
            return int(round(qty))
    return None


def parse_lf(
    description: Any = None,
    *,
    width: Any = None,
    explicit: Any = None,
    width_inches: Any = None,
) -> Optional[float]:
    """Linear feet. Width inches / 12 when a width is present ('160\" wall' → 13 1/3)."""
    if explicit not in (None, ""):
        n = parse_mixed_number(explicit)
        if n is not None and n > 0:
            return float(n)
    inches = parse_mixed_number(width_inches if width_inches not in (None, "") else width)
    if inches is not None and inches > 0:
        return inches / 12.0
    text = str(description or "")
    m = _LF_LABEL_RE.search(text)
    if m:
        n = parse_mixed_number(m.group("n"))
        if n is not None and n > 0:
            return float(n)
    m = _WIDTH_IN_RE.search(text)
    if m:
        n = parse_mixed_number(m.group("n"))
        if n is not None and n > 0:
            return n / 12.0
    return None


def tag_install_line(data: Optional[dict]) -> dict:
    """Return item_type / windows / lf for one quote or invoice line."""
    line = data if isinstance(data, dict) else {}
    desc = line.get("description") or line.get("name") or line.get("labor_description") or ""
    item_type = line.get("item_type") or line.get("type") or ""
    category = line.get("category")
    detected = is_install_line(
        desc,
        item_type=item_type,
        category=category,
        labor_description=line.get("labor_description"),
    )
    windows = parse_windows(
        desc,
        quantity=line.get("quantity") or line.get("qty"),
        unit=line.get("unit"),
        explicit=line.get("windows") if line.get("windows") not in (None, "") else line.get("window_count"),
    )
    width = (
        line.get("width")
        if line.get("width") not in (None, "")
        else line.get("width_in")
        if line.get("width_in") not in (None, "")
        else line.get("finished_width")
    )
    lf = parse_lf(
        desc,
        width=width,
        explicit=line.get("lf") if line.get("lf") not in (None, "") else line.get("linear_feet"),
        width_inches=line.get("width_inches"),
    )
    out_type = "installation" if detected else (str(item_type) if item_type else "")
    return {
        "item_type": out_type,
        "windows": windows,
        "lf": lf,
        "is_install": detected,
    }


def apply_tags_to_line(line: dict) -> dict:
    """Copy a line dict and stamp install tags when detected."""
    tagged = dict(line or {})
    tags = tag_install_line(tagged)
    if tags["is_install"]:
        tagged["item_type"] = "installation"
    if tags["windows"] is not None:
        tagged["windows"] = tags["windows"]
    if tags["lf"] is not None:
        tagged["lf"] = tags["lf"]
    return tagged


def tag_invoice_lines(lines: Any) -> list:
    if not lines:
        return []
    if isinstance(lines, str):
        try:
            lines = json.loads(lines)
        except (json.JSONDecodeError, TypeError):
            return []
    if not isinstance(lines, list):
        return []
    return [apply_tags_to_line(li) if isinstance(li, dict) else li for li in lines]


def dumps_line_items(lines: Any) -> Optional[str]:
    """json.dumps replacement for invoice line_items that tags install rows."""
    if lines is None:
        return None
    if isinstance(lines, str):
        try:
            parsed = json.loads(lines)
        except (json.JSONDecodeError, TypeError):
            return lines
        return json.dumps(tag_invoice_lines(parsed), default=str)
    return json.dumps(tag_invoice_lines(lines), default=str)


def persist_quote_line_tags(conn, data: dict, *, quote_id: str | None = None,
                            line_number: int | None = None, item_id: int | None = None,
                            incoming: dict | None = None) -> dict:
    """Write item_type/windows/lf onto a just-saved quote_line_items row.

    `incoming` is the PATCH/create payload. Stored windows/lf on `data` are
    ignored unless the caller sent those keys, so a description edit re-parses.
    """
    ensure_install_columns(conn)
    working = dict(data or {})
    if incoming is not None:
        if "windows" not in incoming and "window_count" not in incoming:
            working.pop("windows", None)
            working.pop("window_count", None)
        if "lf" not in incoming and "linear_feet" not in incoming:
            working.pop("lf", None)
            working.pop("linear_feet", None)
    tags = tag_install_line(working)
    sets = ["windows = ?", "lf = ?"]
    params: list[Any] = [tags["windows"], tags["lf"]]
    if tags["is_install"]:
        sets.append("item_type = ?")
        params.append("installation")
    if item_id is not None:
        params.append(item_id)
        conn.execute(
            f"UPDATE quote_line_items SET {', '.join(sets)} WHERE id = ?",
            params,
        )
    elif quote_id is not None and line_number is not None:
        params.extend([quote_id, line_number])
        conn.execute(
            f"UPDATE quote_line_items SET {', '.join(sets)} "
            "WHERE quote_id = ? AND line_number = ?",
            params,
        )
    return tags


def normalize_doc_ref(value: Any) -> str:
    text = str(value or "").strip().upper()
    text = re.sub(r"^(EST|INV|QUOTE|DOC|ESTIMATE)[-\s]+", "", text)
    return text.strip()


def looks_like_legacy_doc(value: Any) -> bool:
    text = normalize_doc_ref(value)
    if not text:
        return False
    if text in {n.upper() for n in LEGACY_DOC_NUMBERS}:
        return True
    return bool(LEGACY_DOC_RE.fullmatch(text))


def iter_legacy_refs(*values: Any) -> Iterable[str]:
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        text = str(value)
        for m in LEGACY_DOC_RE.finditer(text):
            ref = m.group(1).upper()
            if ref not in seen:
                seen.add(ref)
                yield ref
