"""Workroom job rules. Defaults live here; Pricing Studio can edit them.

Install is $145 per window through 8 ft, then $20 per foot over that,
unless the founder sets a flat rate for the section. Re-line widths are

    (window width × 2 + 11.5") / panels / 48

rounded up to the next half width, per panel. Sheers use that same
width count on the coverage, then half of it because the fabric is
double width, rounded up to the half width again.
"""
from __future__ import annotations

import math


DEFAULT_RULES: dict[str, float] = {
    "install_per_window": 145.0,
    "install_included_ft": 8.0,
    "install_overage_per_ft": 20.0,
    "reline_per_width": 150.0,
    "lining_removal_per_panel": 95.0,
    "lining_per_yard": 10.50,
    "bump_per_yard": 12.95,
    "baton_each": 34.95,
    "ripplefold_carrier_cost": 0.75,
    "ripplefold_carrier_each": 1.50,
    "track_labor_per_hour": 65.0,
    "sheer_fabrication_per_width": 110.0,
    "fullness_add_in": 11.5,
    "fabric_width_in": 48.0,
    "hem_allowance_in": 16.0,
    "deposit_percent": 50.0,
}

_RULES: dict[str, float] = dict(DEFAULT_RULES)


def rules() -> dict[str, float]:
    return dict(_RULES)


def reset_rules() -> dict[str, float]:
    _RULES.clear()
    _RULES.update(DEFAULT_RULES)
    return rules()


def set_rule(key: str, value: float) -> dict[str, float]:
    if key not in DEFAULT_RULES:
        known = ", ".join(sorted(DEFAULT_RULES))
        raise KeyError(f"Unknown workroom rule '{key}'. Known: {known}")
    _RULES[key] = float(value)
    return rules()


def apply_rules(updates: dict) -> dict[str, float]:
    for key, value in (updates or {}).items():
        set_rule(str(key), float(value))
    return rules()


def rule(key: str) -> float:
    return float(_RULES[key])


def round_up_half(value: float) -> float:
    """Smallest half-width that covers `value`. Exact halves stay put."""
    return math.ceil(value * 2 - 1e-9) / 2.0


def fabric_inches(width_in: float, add_in: float | None = None) -> float:
    add = rule("fullness_add_in") if add_in is None else float(add_in)
    return float(width_in) * 2.0 + add


def panel_widths(window_in: float, panels: int) -> dict:
    """Per-panel and total widths for a stationary pair (or N panels)."""
    panels = max(1, int(panels))
    cloth = fabric_inches(window_in)
    each_raw = cloth / panels / rule("fabric_width_in")
    each = round_up_half(each_raw)
    return {
        "fabric_in": cloth,
        "per_panel_raw": each_raw,
        "per_panel": each,
        "panels": panels,
        "total": each * panels,
    }


def sheer_widths(coverage_in: float) -> dict:
    """Double-width sheer: full width count, then half, then up to the half."""
    cloth = fabric_inches(coverage_in)
    full_raw = cloth / rule("fabric_width_in")
    full = round_up_half(full_raw)
    halved_raw = full / 2.0
    charged = round_up_half(halved_raw)
    return {
        "fabric_in": cloth,
        "full_raw": full_raw,
        "full": full,
        "halved_raw": halved_raw,
        "charged": charged,
    }


def cut_length(finished_in: float) -> float:
    return float(finished_in) + rule("hem_allowance_in")


def lining_yards(width_count: float, finished_in: float) -> float:
    yards = width_count * cut_length(finished_in) / 36.0
    return round(yards + 1e-9, 1)


def install_price(width_in: float, flat: float | None = None) -> dict:
    """Flat section rate replaces the measured formula when the founder sets one."""
    if flat is not None:
        return {"amount": round(float(flat), 2), "method": "flat", "width_ft": width_in / 12.0}
    width_ft = float(width_in) / 12.0
    included = rule("install_included_ft")
    over = max(0.0, width_ft - included)
    amount = rule("install_per_window") + over * rule("install_overage_per_ft")
    return {
        "amount": round(amount, 2),
        "method": "measured",
        "width_ft": width_ft,
        "over_ft": over,
    }
