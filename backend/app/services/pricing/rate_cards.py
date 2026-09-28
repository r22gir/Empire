"""Canonical Pricing Studio rate cards.

These are the rates the pricing engine already applies when a caller omits an
explicit rate. Quote lines look them up here so Workroom and WoodCraft quotes
use the same numbers Pricing Studio calculates with. Treatment formulas stay
in ``PRICING_SPECS``; this module does not copy those tables.
"""
from __future__ import annotations

COMPONENT_RATES: dict[str, dict[str, float]] = {
    "workroom": {
        # Default hourly labor inside price_workroom_item when labor_rate is omitted.
        "labor_rate": 65.0,
    },
    "woodcraft": {
        # Defaults inside price_woodcraft_item when the matching input is omitted.
        "machine_rate_per_hour": 95.0,
        "design_rate": 85.0,
        "assembly_rate": 75.0,
        "finishing_rate": 70.0,
        "labor_rate": 75.0,
    },
}


def lookup_rate(business_unit: str, key: str) -> float:
    """Return one canonical rate. Raises KeyError if the card has no such key."""
    unit = (business_unit or "").strip().lower()
    card = COMPONENT_RATES.get(unit)
    if not card or key not in card:
        known = sorted(COMPONENT_RATES)
        raise KeyError(f"No {unit or 'unknown'} rate '{key}'. Cards: {known}")
    return float(card[key])


def component_rates(business_unit: str) -> dict[str, float]:
    """Copy of the component rate card for API responses."""
    unit = (business_unit or "").strip().lower()
    card = COMPONENT_RATES.get(unit)
    if not card:
        raise KeyError(f"No rate card for '{business_unit}'")
    return dict(card)
