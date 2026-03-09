"""
Quote Intelligence System — Master Pricing Tables

All pricing data for fabric, labor, upgrades, hardware, lining,
installation, taxes, and tier multipliers. Functions for lookups
and live table updates by the founder.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fabric grades
# ---------------------------------------------------------------------------
FABRIC_GRADES = {
    "A": {"name": "Quality Basics", "price_per_yard": 15.00, "examples": "Cotton blend, basic polyester"},
    "B": {"name": "Designer Collection", "price_per_yard": 35.00, "examples": "Sunbrella, mid-range performance"},
    "C": {"name": "Luxury Premium", "price_per_yard": 65.00, "examples": "Crypton, high-end velvet, leather"},
    "D": {"name": "Ultra Luxury", "price_per_yard": 120.00, "examples": "Imported silk, premium leather, custom prints"},
}

# ---------------------------------------------------------------------------
# Labor rates
# ---------------------------------------------------------------------------
LABOR_RATES = {
    "drapery_panel": {"base": 85, "per_width": 25, "per_pleat": 3, "lining_add": 35},
    "roman_shade": {"base": 120, "per_sqft": 8, "motorized_add": 150},
    "roller_shade": {"base": 75, "per_sqft": 5, "motorized_add": 120},
    "valance": {"base": 65, "per_linear_ft": 12},
    "cornice": {"base": 95, "per_linear_ft": 18},
    "swag": {"base": 55, "per_unit": 55},
    "dining_chair_seat": {"base": 45, "per_unit": 45},
    "dining_chair_full": {"base": 150, "per_unit": 150},
    "accent_chair": {"base": 250, "per_unit": 250},
    "wingback_chair": {"base": 350, "per_unit": 350},
    "club_chair": {"base": 300, "per_unit": 300},
    "ottoman": {"base": 125, "per_unit": 125},
    "bench_small": {"base": 150, "per_linear_ft": 25},
    "bench_medium": {"base": 200, "per_linear_ft": 30},
    "bench_large": {"base": 300, "per_linear_ft": 40},
    "loveseat": {"base": 400, "per_unit": 400},
    "sofa_2cushion": {"base": 500, "per_unit": 500},
    "sofa_3cushion": {"base": 650, "per_unit": 650},
    "sectional_per_section": {"base": 400, "per_section": 400},
    "headboard": {"base": 200, "per_sqft": 15},
    "banquette": {"base": 250, "per_linear_ft": 35},
    "seat_cushion": {"base": 45, "per_cushion": 45},
    "back_cushion": {"base": 55, "per_cushion": 55},
    "throw_pillow": {"base": 35, "per_unit": 35},
    "bolster": {"base": 45, "per_unit": 45},
}

# ---------------------------------------------------------------------------
# Upgrades
# ---------------------------------------------------------------------------
UPGRADES = {
    "tufting_diamond": {"name": "Diamond Tufting", "price_range": [100, 250], "per": "piece"},
    "tufting_channel": {"name": "Channel Tufting", "price_range": [75, 200], "per": "piece"},
    "contrast_welting": {"name": "Contrast Welting", "price_range": [50, 120], "per": "piece"},
    "nailhead_trim": {"name": "Nailhead Trim", "price_range": [100, 300], "per": "linear_ft_factor"},
    "tailored_skirt": {"name": "Tailored Skirt", "price_range": [75, 150], "per": "piece"},
    "fringe": {"name": "Decorative Fringe", "price_range": [50, 150], "per": "linear_ft_factor"},
    "new_foam": {"name": "New Foam/Cushion Fill", "price_range": [50, 200], "per": "cushion"},
    "spring_repair": {"name": "Spring Repair", "price_range": [75, 250], "per": "piece"},
    "motorized": {"name": "Motorized (Somfy/Lutron)", "price_range": [285, 425], "per": "unit"},
}

# ---------------------------------------------------------------------------
# Hardware
# ---------------------------------------------------------------------------
HARDWARE = {
    "rod_basic": {"name": "Basic Rod", "price_per_ft": 8},
    "rod_decorative": {"name": "Decorative Rod", "price_per_ft": 18},
    "rod_traverse": {"name": "Traverse Rod", "price_per_ft": 25},
    "track_ceiling": {"name": "Ceiling Track", "price_per_ft": 15},
    "brackets": {"name": "Brackets", "price_per_pair": 12},
    "rings": {"name": "Rings", "price_per_unit": 2.50},
    "holdbacks": {"name": "Holdbacks", "price_per_pair": 25},
    "motorized_somfy": {"name": "Somfy Motor", "price": 285},
    "motorized_lutron": {"name": "Lutron Motor", "price": 425},
}

# ---------------------------------------------------------------------------
# Lining
# ---------------------------------------------------------------------------
LINING = {
    "none": {"name": "No Lining", "multiplier": 1.0, "add_per_yard": 0},
    "standard": {"name": "Standard Lining", "multiplier": 1.15, "add_per_yard": 8},
    "blackout": {"name": "Blackout Lining", "multiplier": 1.25, "add_per_yard": 14},
    "thermal": {"name": "Thermal Lining", "multiplier": 1.20, "add_per_yard": 12},
    "interlining": {"name": "Interlining", "multiplier": 1.30, "add_per_yard": 18},
}

# ---------------------------------------------------------------------------
# Installation
# ---------------------------------------------------------------------------
INSTALLATION = {
    "standard": {"name": "Standard Install", "base": 75, "per_item": 25},
    "complex": {"name": "Complex Install", "base": 125, "per_item": 50},
    "commercial": {"name": "Commercial Install", "base": 200, "per_item": 75},
}

# ---------------------------------------------------------------------------
# Tax rates by jurisdiction
# ---------------------------------------------------------------------------
TAX_RATES = {"DC": 0.06, "MD": 0.06, "VA": 0.053}

# ---------------------------------------------------------------------------
# Tier multipliers
# ---------------------------------------------------------------------------
TIER_MULTIPLIERS = {
    "A": {"fabric": 1.0, "labor": 1.0, "name": "Essential"},
    "B": {"fabric": 2.0, "labor": 1.15, "name": "Designer"},
    "C": {"fabric": 3.5, "labor": 1.30, "name": "Premium"},
}

DEPOSIT_PERCENTAGE = 0.50

# ===================================================================
# Lookup helpers
# ===================================================================


def get_fabric_price(grade: str, yards: float) -> float:
    """Return fabric cost for *grade* and *yards* of fabric."""
    grade = grade.upper()
    if grade not in FABRIC_GRADES:
        raise ValueError(f"Unknown fabric grade '{grade}'. Valid: {list(FABRIC_GRADES.keys())}")
    price = round(FABRIC_GRADES[grade]["price_per_yard"] * yards, 2)
    logger.debug("Fabric grade %s × %.1f yd = $%.2f", grade, yards, price)
    return price


def get_labor_cost(item_type: str, dimensions: Optional[Dict[str, float]] = None) -> float:
    """Calculate labor cost for *item_type* using optional *dimensions*.

    Dimensions dict may contain: width, height, depth (in inches),
    linear_ft, sqft, cushion_count, section_count, pleat_count, widths.
    """
    if item_type not in LABOR_RATES:
        raise ValueError(f"Unknown item type '{item_type}'. Valid: {list(LABOR_RATES.keys())}")

    rate = LABOR_RATES[item_type]
    cost = float(rate["base"])
    dims = dimensions or {}

    # Linear-foot items
    if "per_linear_ft" in rate:
        linear_ft = dims.get("linear_ft", dims.get("width", 0) / 12 if dims.get("width") else 0)
        cost += rate["per_linear_ft"] * linear_ft

    # Square-foot items
    if "per_sqft" in rate:
        sqft = dims.get("sqft", 0)
        if not sqft and dims.get("width") and dims.get("height"):
            sqft = (dims["width"] * dims["height"]) / 144
        cost += rate["per_sqft"] * sqft

    # Drapery specifics
    if "per_width" in rate:
        widths = dims.get("widths", 1)
        cost += rate["per_width"] * widths
    if "per_pleat" in rate:
        pleats = dims.get("pleat_count", 0)
        cost += rate["per_pleat"] * pleats
    if "lining_add" in rate and dims.get("lined"):
        cost += rate["lining_add"]

    # Motorized add-on
    if "motorized_add" in rate and dims.get("motorized"):
        cost += rate["motorized_add"]

    # Per-unit / per-cushion / per-section
    if "per_cushion" in rate:
        cushions = dims.get("cushion_count", 1)
        cost += rate["per_cushion"] * max(cushions - 1, 0)  # base covers first
    if "per_section" in rate:
        sections = dims.get("section_count", 1)
        cost += rate["per_section"] * max(sections - 1, 0)

    cost = round(cost, 2)
    logger.debug("Labor for %s: $%.2f (dims=%s)", item_type, cost, dims)
    return cost


def get_upgrade_cost(
    upgrade_key: str, quantity: int = 1, dimensions: Optional[Dict[str, float]] = None
) -> float:
    """Return upgrade cost.  For *linear_ft_factor* items, uses dimensions width."""
    if upgrade_key not in UPGRADES:
        raise ValueError(f"Unknown upgrade '{upgrade_key}'. Valid: {list(UPGRADES.keys())}")

    upgrade = UPGRADES[upgrade_key]
    low, high = upgrade["price_range"]
    mid = (low + high) / 2  # default to midpoint

    if upgrade["per"] == "linear_ft_factor" and dimensions:
        linear_ft = dimensions.get("linear_ft", dimensions.get("width", 0) / 12)
        # Scale from low to high based on linear feet (assume 1-10 ft range)
        factor = min(max(linear_ft / 10, 0), 1)
        mid = low + (high - low) * factor

    cost = round(mid * quantity, 2)
    logger.debug("Upgrade %s × %d = $%.2f", upgrade_key, quantity, cost)
    return cost


def get_all_tables() -> Dict[str, Any]:
    """Return every pricing table as a dictionary (for API / frontend)."""
    return {
        "fabric_grades": FABRIC_GRADES,
        "labor_rates": LABOR_RATES,
        "upgrades": UPGRADES,
        "hardware": HARDWARE,
        "lining": LINING,
        "installation": INSTALLATION,
        "tax_rates": TAX_RATES,
        "tier_multipliers": TIER_MULTIPLIERS,
        "deposit_percentage": DEPOSIT_PERCENTAGE,
    }


def update_table(table_name: str, key: str, value: Any) -> Dict[str, Any]:
    """Update a pricing entry at runtime (founder editor).

    Returns the updated table.
    """
    tables = {
        "fabric_grades": FABRIC_GRADES,
        "labor_rates": LABOR_RATES,
        "upgrades": UPGRADES,
        "hardware": HARDWARE,
        "lining": LINING,
        "installation": INSTALLATION,
        "tax_rates": TAX_RATES,
        "tier_multipliers": TIER_MULTIPLIERS,
    }
    if table_name not in tables:
        raise ValueError(f"Unknown table '{table_name}'. Valid: {list(tables.keys())}")

    table = tables[table_name]
    table[key] = value
    logger.info("Updated %s[%s] = %s", table_name, key, value)
    return table
