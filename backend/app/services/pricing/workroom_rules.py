"""Workroom job rules. Defaults live here; Pricing Studio can edit them.

Install is $145 per window through 8 ft, then $20 per foot over that,
unless the founder sets a flat rate for the section. Re-line widths are

    (window width × 2 + 11.5") / panels / 48

rounded up to the next half width, per panel. Re-line labor is
``reline_per_width`` ($150, lining and bump) or ``reline_no_bump_per_width``
($125, "Re-line with lining (no bump)": lining only, no bump material); both
count widths the same way (per 48" finished panel width at 100% fullness).
Sheers use that same
width count on the coverage, then half of it because the fabric is
double width, rounded up to the half width again.

Edits from ``POST /pricing/workroom/rules`` persist in SQLite
(``workroom_pricing_rules``); missing keys fall back to ``DEFAULT_RULES``.
"""
from __future__ import annotations

import logging
import math

logger = logging.getLogger(__name__)

DEFAULT_RULES: dict[str, float] = {
    "install_per_window": 145.0,
    "install_included_ft": 8.0,
    "install_overage_per_ft": 20.0,
    "reline_per_width": 150.0,
    "reline_no_bump_per_width": 125.0,  # Rafael 10/4/2026: lining only, no bump
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
_LOADED_FROM_DB = False


def _ensure_table(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS workroom_pricing_rules (
            rule_key TEXT PRIMARY KEY NOT NULL,
            value REAL NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )


def _load_from_db() -> None:
    global _LOADED_FROM_DB
    from app.db.database import get_db

    merged = dict(DEFAULT_RULES)
    try:
        with get_db() as conn:
            _ensure_table(conn)
            rows = conn.execute(
                "SELECT rule_key, value FROM workroom_pricing_rules"
            ).fetchall()
            for row in rows:
                key = row["rule_key"]
                if key in DEFAULT_RULES:
                    merged[key] = float(row["value"])
    except Exception:
        logger.debug("workroom rules: could not load from DB", exc_info=True)
    _RULES.clear()
    _RULES.update(merged)
    _LOADED_FROM_DB = True


def _ensure_loaded() -> None:
    if not _LOADED_FROM_DB:
        _load_from_db()


def _persist_rule(key: str, value: float) -> None:
    from app.db.database import get_db

    with get_db() as conn:
        _ensure_table(conn)
        conn.execute(
            """
            INSERT INTO workroom_pricing_rules (rule_key, value, updated_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(rule_key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (key, float(value)),
        )


def _clear_persisted() -> None:
    from app.db.database import get_db

    with get_db() as conn:
        _ensure_table(conn)
        conn.execute("DELETE FROM workroom_pricing_rules")


def rules() -> dict[str, float]:
    _ensure_loaded()
    return dict(_RULES)


def reload_rules() -> dict[str, float]:
    """Re-read persisted rules from SQLite (for tests and worker reload)."""
    global _LOADED_FROM_DB
    _LOADED_FROM_DB = False
    _ensure_loaded()
    return rules()


def reset_rules() -> dict[str, float]:
    _RULES.clear()
    _RULES.update(DEFAULT_RULES)
    try:
        _clear_persisted()
    except Exception:
        logger.debug("workroom rules: could not clear persisted rules", exc_info=True)
    global _LOADED_FROM_DB
    _LOADED_FROM_DB = True
    return rules()


def set_rule(key: str, value: float) -> dict[str, float]:
    _ensure_loaded()
    if key not in DEFAULT_RULES:
        known = ", ".join(sorted(DEFAULT_RULES))
        raise KeyError(f"Unknown workroom rule '{key}'. Known: {known}")
    _RULES[key] = float(value)
    try:
        _persist_rule(key, float(value))
    except Exception:
        logger.debug("workroom rules: could not persist %s", key, exc_info=True)
    return rules()


def apply_rules(updates: dict) -> dict[str, float]:
    for key, value in (updates or {}).items():
        set_rule(str(key), float(value))
    return rules()


def rule(key: str) -> float:
    _ensure_loaded()
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
