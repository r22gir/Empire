"""Canonical Pricing Studio rate cards.

These are the rates the pricing engine already applies when a caller omits an
explicit rate. Quote lines look them up here so Workroom and WoodCraft quotes
use the same numbers Pricing Studio calculates with. Treatment formulas stay
in ``PRICING_SPECS``; this module does not copy those tables.
"""
from __future__ import annotations

import time
from typing import Any

# Founder-approved client overlays and format rules.  These are durable
# Pricing Studio data, not chat-only guidance or quote-specific notes.
CLIENT_RATE_RULES: dict[str, dict[str, object]] = {
    "maggie_o_neill": {
        "prices_include_client_factor": 1.20,
        "valance_rate_per_linear_foot": 84.95,
        "valance_includes_fringe_application": True,
        "panel_swag_trim_application_rate": 74.95,
        "panel_swag_trim_material": "COM",
        "trim_yardage_required": True,
        "drapery_excludes_hardware": True,
        "rings_rate_per_8_pack": 74.95,
        "other_hardware_cost_multiplier": 1.5,
        "other_hardware_client_factor": 1.20,
        "other_hardware_shipping_included_in_markup": True,
        "hardware_shipping_line": False,
        "valances_are_add_ons_over_ripplefold": True,
        "swags_per_window": 1,
        "center_tassels_per_swag": 2,
        "willard_tassel_count_total": 14,
        "willard_tassel_scope": "per swag window: 1 tieback pair + 2 center tassels; passway: 1 tieback pair",
        "tassel_totals_include_tiebacks_and_center_tassels": True,
        "no_holdback_cylinders_when_tassel_tiebacks_used": True,
        "holdback_rule": "when tassel tiebacks are used, no holdback cylinders are billed",
        "no_separate_sheer_removal_installation_add_on": True,
        "sheer_removal_installation_rule": "no separate sheer removal/install add-on when the original estimate already includes removal and installation",
        "swag_trim_application_included_in_valance_rate": True,
        "trim_edges": "leading edge only",
        "tassel_tiebacks_replace_holdbacks": True,
        "rowley_cart_scope": "W4 passway door",
        "email_format": "each item, amount, and note on its own line or bullet; never lumped into one paragraph",
        "revision": "founder-2026-09-30",
    },
}


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


_OVERLAY_CACHE: tuple[float, dict[str, Any]] | None = None
_OVERLAY_TTL = 2.0


def invalidate_rate_overlay_cache() -> None:
    global _OVERLAY_CACHE
    _OVERLAY_CACHE = None


def _company_rate_overlay() -> dict[str, Any]:
    """Cached company-setup rate_cards blob. Failed reads stay empty."""
    global _OVERLAY_CACHE
    now = time.monotonic()
    if _OVERLAY_CACHE and now - _OVERLAY_CACHE[0] < _OVERLAY_TTL:
        return _OVERLAY_CACHE[1]
    data: dict[str, Any] = {}
    try:
        from app.services.company_setup.store import load_merged

        raw = load_merged().get("rate_cards") or {}
        if isinstance(raw, dict):
            data = raw
    except Exception:
        data = {}
    _OVERLAY_CACHE = (now, data)
    return data


def apply_company_rate_overlay(business_unit: str, card: dict[str, float]) -> dict[str, float]:
    """Apply interview rates onto one card.

    Only keys already on the card. Values must be numeric and > 0.
    ``bool`` is rejected (it is an ``int`` subclass).
    """
    out = dict(card)
    unit = (business_unit or "").strip().lower()
    overlay = _company_rate_overlay().get(unit)
    if not isinstance(overlay, dict):
        return out
    for key, value in overlay.items():
        name = str(key)
        if name not in out:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if float(value) > 0:
            out[name] = float(value)
    return out


def _base_card(business_unit: str) -> dict[str, float]:
    unit = (business_unit or "").strip().lower()
    card = COMPONENT_RATES.get(unit)
    if not card:
        known = sorted(COMPONENT_RATES)
        raise KeyError(f"No rate card for '{business_unit}'. Cards: {known}")
    return dict(card)


def lookup_rate(business_unit: str, key: str) -> float:
    """Return one canonical rate. Raises KeyError if the card has no such key."""
    unit = (business_unit or "").strip().lower()
    card = apply_company_rate_overlay(unit, _base_card(unit))
    if key not in card:
        known = sorted(COMPONENT_RATES)
        raise KeyError(f"No {unit or 'unknown'} rate '{key}'. Cards: {known}")
    return float(card[key])


def component_rates(business_unit: str) -> dict[str, float]:
    """Copy of the component rate card for API responses."""
    unit = (business_unit or "").strip().lower()
    return apply_company_rate_overlay(unit, _base_card(unit))


def client_rate_rules(client_key: str) -> dict[str, object]:
    """Return a copy of durable client-specific rate and format rules."""
    key = (client_key or "").strip().lower().replace(" ", "_").replace("'", "_")
    if key not in CLIENT_RATE_RULES:
        raise KeyError(f"No client rate rules for '{client_key}'")
    return dict(CLIENT_RATE_RULES[key])
