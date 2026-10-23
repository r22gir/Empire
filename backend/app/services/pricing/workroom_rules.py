"""Workroom job rules. Defaults live here; Pricing Studio can edit them.

Install is $245 per 8 ft section, prorated (Rafael 2026-10-23), never hourly
unless the founder explicitly overrides. Track is $325 per 8 ft section,
prorated. A flat section rate still replaces the formula when set.
Re-line widths are

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
    "install_per_8ft": 245.0,
    "track_per_8ft": 325.0,
    "install_section_ft": 8.0,
    # Alias: Pricing Studio historically edited install_per_window. It now
    # means the 8 ft section rate (same dollars as install_per_8ft).
    "install_per_window": 245.0,
    "install_included_ft": 8.0,
    "install_overage_per_ft": 0.0,
    "reline_per_width": 150.0,
    "reline_no_bump_per_width": 125.0,  # Rafael 10/4/2026: lining only, no bump
    "lining_removal_per_panel": 95.0,
    # Workroom SELL rates per yard (Rafael 10/4/2026). Always the workroom's own rates, never supplier
    # list prices (those exclude freight).
    "lining_per_yard": 10.50,           # lining
    "bump_per_yard": 12.50,             # napped lining / interlining (bump)
    "baton_each": 34.95,
    "ripplefold_carrier_cost": 0.75,
    "ripplefold_carrier_each": 1.50,
    "track_labor_per_hour": 65.0,
    "sheer_fabrication_per_width": 110.0,
    "fullness_add_in": 11.5,
    "fabric_width_in": 48.0,
    "hem_allowance_in": 16.0,
    "deposit_percent": 50.0,
    # New-fabrication rate card (Willard / REV C generator defaults).
    # Fixture rates only — not a live client job.
    "new_fab_per_width": 95.0,
    "new_fab_fullness": 2.5,
    "new_fab_goods_width_in": 54.0,
    "sheer_goods_width_in": 110.0,
    "sheer_hem_allowance_in": 12.0,
    "baton_fiberglass_each": 25.15,
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
    # Keep the 8 ft section rate and the legacy key in lockstep.
    if key == "install_per_window":
        _RULES["install_per_8ft"] = float(value)
    elif key == "install_per_8ft":
        _RULES["install_per_window"] = float(value)
    try:
        _persist_rule(key, float(value))
        if key == "install_per_window":
            _persist_rule("install_per_8ft", float(value))
        elif key == "install_per_8ft":
            _persist_rule("install_per_window", float(value))
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


def ceil_yards(width_count: float, cut_in: float) -> int:
    """Whole yards covering ``width_count`` cuts of ``cut_in`` inches."""
    return int(math.ceil(float(width_count) * float(cut_in) / 36.0 - 1e-9))


def track_feet(width_in: float) -> int:
    """Whole feet of track, rounded up (21 ft for 249 5/16\", 16 ft for 189 3/8\")."""
    return int(math.ceil(float(width_in) / 12.0 - 1e-9))


def new_fab_widths(
    coverage_in: float,
    *,
    fullness: float | None = None,
    goods_in: float | None = None,
    panels: int = 2,
) -> dict:
    """New-fabrication width count: coverage × fullness / goods, ceil to a whole width.

    REV C default: 2.5× fullness on 54\" goods (main) or 110\" goods (sheers).
    249 5/16\" × 2.5 / 54 → 12 widths; 189 3/8\" × 2.5 / 110 → 5 widths.
    """
    fullness = float(fullness if fullness is not None else rule("new_fab_fullness"))
    goods = float(goods_in if goods_in is not None else rule("new_fab_goods_width_in"))
    if fullness > 10:
        fullness = fullness / 100.0
    fabric_in = float(coverage_in) * fullness
    raw = fabric_in / goods if goods else 0.0
    total = int(math.ceil(raw - 1e-9)) if raw > 0 else 0
    panels = max(1, int(panels))
    per_panel = total / panels
    return {
        "coverage": float(coverage_in),
        "fullness": fullness,
        "goods_in": goods,
        "fabric_in": fabric_in,
        "raw": raw,
        "total": total,
        "panels": panels,
        "per_panel": per_panel,
    }


def install_price(
    width_in: float,
    flat: float | None = None,
    *,
    hourly: float | None = None,
) -> dict:
    """$245 per 8 ft section, prorated. Flat or hourly only when explicitly set."""
    from app.services.estimates.rafael_format import install_section_price
    return install_section_price(width_in, flat=flat, hourly=hourly)


def track_price(
    width_in: float,
    *,
    hours: float | None = None,
    flat: float | None = None,
) -> dict:
    """$325 per 8 ft section, prorated. Hourly only when hours are passed."""
    from app.services.estimates.rafael_format import track_section_price
    return track_section_price(width_in, hours=hours, flat=flat)
