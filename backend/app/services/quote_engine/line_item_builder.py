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
    yards = yardage_result["yards"]

    # Apply tier fabric multiplier to price per yard
    fabric_rate = round(fabric_info["price_per_yard"] * tier_info["fabric"], 2)
    fabric_total = round(fabric_rate * yards, 2)

    line_items.append({
        "category": "fabric",
        "description": (
            f"Grade {fabric_grade} fabric — {fabric_info['name']} ({yards} yd)"
        ),
        "quantity": yards,
        "unit": "yd",
        "rate": fabric_rate,
        "amount": fabric_total,
    })

    # ---- 2. Lining ----
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
