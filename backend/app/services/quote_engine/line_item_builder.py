"""
Quote Intelligence System — Line Item Builder

Build detailed, human-readable line items for a single analyzed item.
"""

import logging
from typing import Any, Dict, List, Optional

from .pricing_tables import (
    FABRIC_GRADES,
    INSTALLATION,
    LINING,
    TAX_RATES,
    TIER_MULTIPLIERS,
    UPGRADES,
    get_fabric_price,
    get_labor_cost,
    get_upgrade_cost,
)
from .yardage_calculator import calculate_yardage

logger = logging.getLogger(__name__)

# Drapery / window treatment types — these get lining
DRAPERY_TYPES = {
    "drapery_panel", "drapery", "roman_shade", "roller_shade",
    "valance", "cornice", "swag", "sheer",
}


def _is_drapery(item_type: str) -> bool:
    """Return True if item_type is a drapery / window treatment."""
    t = item_type.lower()
    return t in DRAPERY_TYPES or t.startswith("drapery_")


def _calc_sq_ft(dims: dict) -> float:
    """Calculate surface sq ft from dimensions (inches)."""
    w = float(dims.get("width", 0) or 0)
    h = float(dims.get("height", 0) or 0)
    d = float(dims.get("depth", 0) or 0)
    if w and d:
        return round((w * d) / 144, 2)
    elif w and h:
        return round((w * h) / 144, 2)
    return 0.0


def build_line_items(
    item: Dict[str, Any],
    tier: str = "A",
    lining: str = "standard",
    location: str = "DC",
) -> List[Dict[str, Any]]:
    """Build a list of priced line items for a single analyzed item.

    Parameters
    ----------
    item : dict
        Must contain at least ``name``, ``type``, ``dimensions``, ``quantity``.
        Optional: ``construction``, ``special_features``, ``condition``,
        ``cushion_count``, ``photo_url``.
    tier : str
        ``"A"`` / ``"B"`` / ``"C"`` — controls fabric grade and labor multiplier.
    lining : str
        ``"none"`` / ``"standard"`` / ``"blackout"`` / ``"thermal"`` / ``"interlining"``.
    location : str
        ``"DC"`` / ``"MD"`` / ``"VA"`` — for tax lookup.

    Returns
    -------
    list[dict]  Each dict: ``{category, description, quantity, unit, rate, amount}``
    """
    tier = tier.upper()
    tier_info = TIER_MULTIPLIERS.get(tier, TIER_MULTIPLIERS["A"])
    fabric_grade = tier  # A→A, B→B, C→C
    fabric_info = FABRIC_GRADES.get(fabric_grade, FABRIC_GRADES["A"])
    lining_info = LINING.get(lining, LINING["standard"])

    item_type = item.get("type", "accent_chair")
    item_name = item.get("name", item_type.replace("_", " ").title())
    dims = item.get("dimensions", {})
    qty = item.get("quantity", 1)
    special_features = item.get("special_features", [])
    cushion_count = item.get("cushion_count", 0)
    construction = item.get("construction", "")

    line_items: List[Dict[str, Any]] = []

    # ---- 1. Fabric ----
    yardage_opts: Dict[str, Any] = {}
    if cushion_count:
        yardage_opts["cushion_count"] = cushion_count
    # Detect tufting from special features
    tufted = any("tuft" in f.lower() for f in special_features)
    if tufted:
        yardage_opts["tufted"] = True
    # Pattern repeat — look for it in construction notes
    if "pattern" in (construction or "").lower():
        yardage_opts["pattern_repeat"] = 24  # default repeat

    yardage_result = calculate_yardage(item_type, dims, yardage_opts)
    yards = item.get("fabric_yards_needed")
    if yards in (None, ""):
        yards = yardage_result["yards"]
    yards = round(float(yards or 0), 2)

    custom_fabric_cost = item.get("fabric_cost_at_quote")
    custom_fabric_margin = item.get("fabric_margin_at_quote") or 0
    custom_fabric_name = item.get("fabric_name") or item.get("fabric_code")

    if custom_fabric_cost not in (None, ""):
        base_cost = float(custom_fabric_cost)
        margin_multiplier = 1 + (float(custom_fabric_margin) / 100)
        fabric_rate = round(base_cost * margin_multiplier, 2)
        fabric_label = custom_fabric_name or f"Selected fabric ({yards} yd)"
        fabric_desc = f"{fabric_label} ({yards} yd)"
    else:
        # Apply tier fabric multiplier to price per yard
        fabric_rate = round(fabric_info["price_per_yard"] * tier_info["fabric"], 2)
        fabric_desc = f"Grade {fabric_grade} fabric — {fabric_info['name']} ({yards} yd)"

    fabric_total = round(fabric_rate * yards, 2)

    line_items.append({
        "category": "fabric",
        "description": fabric_desc,
        "quantity": yards,
        "unit": "yd",
        "rate": fabric_rate,
        "amount": fabric_total,
    })

    backing_yards = item.get("backing_yards_needed")
    backing_cost = item.get("backing_fabric_cost_at_quote")
    if backing_yards not in (None, "", 0) and backing_cost not in (None, ""):
        backing_margin = item.get("backing_fabric_margin_at_quote") or 0
        backing_rate = round(float(backing_cost) * (1 + (float(backing_margin) / 100)), 2)
        backing_name = item.get("backing_fabric_name") or item.get("backing_fabric_code") or "Backing fabric"
        backing_yards = round(float(backing_yards), 2)
        line_items.append({
            "category": "backing",
            "description": f"{backing_name} ({backing_yards} yd)",
            "quantity": backing_yards,
            "unit": "yd",
            "rate": backing_rate,
            "amount": round(backing_rate * backing_yards, 2),
        })

    # ---- 2. Lining (drapery only) OR sq ft pricing (upholstery) ----
    if _is_drapery(item_type):
        if lining != "none":
            lining_rate = lining_info["add_per_yard"]
            lining_total = round(lining_rate * yards, 2)
            line_items.append({
                "category": "lining",
                "description": f"{lining_info['name']} ({yards} yd)",
                "quantity": yards,
                "unit": "yd",
                "rate": lining_rate,
                "amount": lining_total,
            })
    else:
        # Upholstery — priced per sq ft, no lining
        sq_ft = _calc_sq_ft(dims)
        if sq_ft > 0:
            line_items.append({
                "category": "sqft",
                "description": f"Upholstery ({sq_ft} sq ft)",
                "quantity": sq_ft,
                "unit": "sqft",
                "rate": 0,
                "amount": 0,
            })
        # Dacron (optional) — yardage from roll width
        dacron_roll = item.get("dacron_roll_width", 0)
        if dacron_roll and sq_ft > 0:
            dacron_yards = round((sq_ft * 144) / dacron_roll / 36, 2)
            line_items.append({
                "category": "dacron",
                "description": f"Dacron ({dacron_roll}\" wide roll — {dacron_yards} yd needed)",
                "quantity": dacron_yards,
                "unit": "yd",
                "rate": 0,
                "amount": 0,
            })

    # ---- 3. Labor ----
    labor_dims = dict(dims)
    if cushion_count:
        labor_dims["cushion_count"] = cushion_count

    base_labor = get_labor_cost(item_type, labor_dims)
    labor_rate = round(base_labor * tier_info["labor"], 2)

    # Build a descriptive label
    size_label = ""
    if dims.get("width"):
        if dims["width"] >= 12:
            size_label = f"{dims['width'] / 12:.0f}ft"
        else:
            size_label = f"{dims['width']}in"
    labor_desc = f"{item_name} reupholstery"
    if size_label:
        labor_desc += f" — {size_label} {item_name.lower()}"

    line_items.append({
        "category": "labor",
        "description": labor_desc,
        "quantity": 1,
        "unit": "ea",
        "rate": labor_rate,
        "amount": labor_rate,
    })

    # ---- 4. Special features / upgrades ----
    for feature in special_features:
        feature_lower = feature.lower()

        # Map feature names to upgrade keys
        upgrade_key: Optional[str] = None
        if "diamond" in feature_lower and "tuft" in feature_lower:
            upgrade_key = "tufting_diamond"
        elif "channel" in feature_lower and "tuft" in feature_lower:
            upgrade_key = "tufting_channel"
        elif "tuft" in feature_lower:
            upgrade_key = "tufting_diamond"  # default tufting
        elif "welt" in feature_lower or "piping" in feature_lower:
            upgrade_key = "contrast_welting"
        elif "nailhead" in feature_lower or "nail" in feature_lower:
            upgrade_key = "nailhead_trim"
        elif "skirt" in feature_lower:
            upgrade_key = "tailored_skirt"
        elif "fringe" in feature_lower:
            upgrade_key = "fringe"
        elif "foam" in feature_lower:
            upgrade_key = "new_foam"
        elif "spring" in feature_lower:
            upgrade_key = "spring_repair"
        elif "motor" in feature_lower:
            upgrade_key = "motorized"

        if upgrade_key:
            upgrade_info = UPGRADES[upgrade_key]
            cost = get_upgrade_cost(upgrade_key, quantity=1, dimensions=dims)
            line_items.append({
                "category": "upgrade",
                "description": upgrade_info["name"],
                "quantity": 1,
                "unit": "ea",
                "rate": cost,
                "amount": cost,
            })

    # ---- 5. New foam (if condition is poor/worn and not already added) ----
    condition = (item.get("condition", "") or "").lower()
    foam_already = any(li["category"] == "upgrade" and "foam" in li["description"].lower() for li in line_items)
    if condition in ("poor", "worn", "damaged") and not foam_already:
        foam_cost = get_upgrade_cost("new_foam", quantity=max(cushion_count, 1), dimensions=dims)
        line_items.append({
            "category": "foam",
            "description": "New Foam/Cushion Fill",
            "quantity": max(cushion_count, 1),
            "unit": "ea",
            "rate": round(foam_cost / max(cushion_count, 1), 2),
            "amount": foam_cost,
        })

    # ---- 6. Installation ----
    install_type = "standard"
    if item_type in ("banquette", "headboard", "sectional_per_section"):
        install_type = "complex"

    install_info = INSTALLATION[install_type]
    install_cost = round(install_info["base"] + install_info["per_item"], 2)
    line_items.append({
        "category": "installation",
        "description": f"{install_info['name']}",
        "quantity": 1,
        "unit": "ea",
        "rate": install_cost,
        "amount": install_cost,
    })

    # ---- 7. Apply quantity (multiply amounts for qty > 1) ----
    if qty > 1:
        for li in line_items:
            li["amount"] = round(li["amount"] * qty, 2)
            li["description"] = f"{li['description']} (×{qty})"

    logger.info(
        "Built %d line items for '%s' (tier %s, qty %d)",
        len(line_items), item_name, tier, qty,
    )
    return line_items
