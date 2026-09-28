"""Map Photo Analyzer / QIS display lines onto Workroom quotes-v2 rows.

Workroom reads ``quotes_v2`` (business_unit=workroom). Photo display lines
often carry catalog categories such as ``labor``. Those categories are priced
by the engine and reject a photo estimate that has a rate but no catalog
inputs. A positive rate is stored as ``manual_line`` (quantity × unit_price).
An item with no price is stored as ``note`` so it still shows on the quote.
"""
from __future__ import annotations

import math
from typing import Any, Iterable, Optional

MEASURE_FABRIC_RATE = 45.0
MEASURE_LABOR_RATE = 150.0

WINDOW_TYPES = {
    "window",
    "drapery",
    "drapery_panel",
    "roman_shade",
    "roller_shade",
    "valance",
    "cornice",
    "swag",
    "sheer",
}


def _round_money(value: float) -> float:
    return round(float(value) + 1e-9, 2)


def _positive(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str):
        text = "".join(ch for ch in value.strip() if ch.isdigit() or ch in ".+-")
        if not text:
            return None
        try:
            number = float(text)
        except ValueError:
            return None
    else:
        return None
    if number <= 0:
        return None
    return number


def as_workroom_quote_line(raw: Optional[dict]) -> Optional[dict]:
    """One display line → quotes-v2 manual_line or note. Never a catalog category."""
    if not isinstance(raw, dict):
        return None
    description = str(raw.get("description") or "").strip()
    if not description:
        return None

    quantity = _positive(raw.get("quantity")) or 1.0
    unit = str(raw.get("unit") or "ea").strip() or "ea"
    rate = _positive(raw.get("rate"))
    if rate is None:
        rate = _positive(raw.get("unit_price"))
    amount = _positive(raw.get("amount"))
    if rate is None and amount is not None:
        rate = _round_money(amount / quantity)

    if rate is None:
        return {
            "description": description,
            "quantity": 1,
            "unit": "ea",
            "unit_price": 0,
            "rate": 0,
            "amount": 0,
            "category": "note",
        }

    return {
        "description": description,
        "quantity": quantity,
        "unit": unit,
        "unit_price": rate,
        "rate": rate,
        "amount": _round_money(quantity * rate),
        "category": "manual_line",
        "inputs": {
            "description": description,
            "unit_price": rate,
            "quantity": quantity,
        },
    }


def measure_display_lines(
    width_inches: Any,
    height_inches: Any,
    window_type: str = "Standard",
) -> list[dict]:
    """Same fullness / hem / 54\" goods as the Photo Analyzer Save-to-Quote UI."""
    width = _positive(width_inches)
    height = _positive(height_inches)
    label_type = (window_type or "").strip() or "Standard"
    label = f'Window Measurement — {label_type} ({width or 0}" W x {height or 0}" H)'
    if width is None or height is None:
        return [{
            "description": label,
            "quantity": 1,
            "unit": "ea",
            "rate": 0,
            "amount": 0,
            "category": "labor",
        }]
    fabric_width = 54.0
    fullness = 2.5
    hem = 8.0
    cut_length = height + hem
    widths = math.ceil((width * fullness) / fabric_width)
    total_yards = math.ceil((widths * cut_length) / 36 * 10) / 10
    fabric_amount = _round_money(total_yards * MEASURE_FABRIC_RATE)
    return [
        {
            "description": f"{label} — Fabric ({total_yards} yds)",
            "quantity": total_yards,
            "unit": "yd",
            "rate": MEASURE_FABRIC_RATE,
            "amount": fabric_amount,
            "category": "materials",
        },
        {
            "description": f"{label} — Labor",
            "quantity": 1,
            "unit": "ea",
            "rate": MEASURE_LABOR_RATE,
            "amount": MEASURE_LABOR_RATE,
            "category": "labor",
        },
    ]


def lines_from_photo_measure(measure: Optional[dict]) -> list[dict]:
    if not isinstance(measure, dict):
        return []
    return [
        line
        for line in (
            as_workroom_quote_line(raw)
            for raw in measure_display_lines(
                measure.get("width_inches"),
                measure.get("height_inches"),
                str(measure.get("window_type") or "Standard"),
            )
        )
        if line
    ]


def _tier_items(quote: Optional[dict]) -> list:
    if not isinstance(quote, dict):
        return []
    tiers = quote.get("tiers") or {}
    if isinstance(tiers, list):
        return (tiers[0] or {}).get("items") or [] if tiers else []
    if not isinstance(tiers, dict):
        return []
    tier = tiers.get("A") or tiers.get("a") or {}
    return tier.get("items") or []


def _item_label(item: dict) -> str:
    return str(item.get("description") or item.get("name") or item.get("type") or "Photo item").strip() or "Photo item"


def _priced_for_item(item: dict, index: int, tier_items: list) -> list:
    own = item.get("line_items")
    if isinstance(own, list) and own:
        return own
    label = _item_label(item).lower()
    for entry in tier_items:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or entry.get("description") or "").lower()
        if name and name == label and entry.get("line_items"):
            return entry["line_items"]
    if index < len(tier_items) and isinstance(tier_items[index], dict):
        entry = tier_items[index]
        name = str(entry.get("name") or "").lower()
        if entry.get("line_items") and (not name or name == label or name == str(item.get("name") or "").lower()):
            return entry["line_items"]
    return []


def lines_from_analyzed_items(
    items: Optional[Iterable[dict]],
    quote: Optional[dict] = None,
) -> list[dict]:
    """Selected analyzed items → Workroom lines. Unselected items are skipped."""
    tier_items = _tier_items(quote)
    out: list[dict] = []
    for index, item in enumerate(items or []):
        if not isinstance(item, dict) or item.get("selected") is False:
            continue
        priced = [
            line
            for line in (as_workroom_quote_line(raw) for raw in _priced_for_item(item, index, tier_items))
            if line and line["category"] == "manual_line"
        ]
        if priced:
            out.extend(priced)
            continue

        dims = item.get("dimensions") if isinstance(item.get("dimensions"), dict) else {}
        width = _positive(item.get("width")) or _positive(dims.get("width"))
        height = _positive(item.get("height")) or _positive(dims.get("height"))
        item_type = str(item.get("type") or "").lower()
        label = _item_label(item)
        if width and height and (item_type in WINDOW_TYPES or item_type == ""):
            measured = [
                line for line in lines_from_photo_measure({
                    "width_inches": width,
                    "height_inches": height,
                    "window_type": label,
                })
                if line["category"] == "manual_line"
            ]
            if measured:
                out.extend(measured)
                continue

        dims_label = f' ({width}" × {height}")' if width and height else ""
        note = as_workroom_quote_line({
            "description": f"{label}{dims_label}",
            "quantity": item.get("quantity") or 1,
            "rate": 0,
        })
        if note:
            out.append(note)
    return out
