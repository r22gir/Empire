"""
Quote Intelligence System — Tier Generator

Produce three pricing tiers (A / B / C) with genuinely different prices.
"""

import logging
from typing import Any, Dict, List

from .line_item_builder import build_line_items
from .pricing_tables import DEPOSIT_PERCENTAGE, TAX_RATES, TIER_MULTIPLIERS

logger = logging.getLogger(__name__)


def _sum_line_items(line_items: List[Dict[str, Any]]) -> float:
    """Sum the ``amount`` field across all line items."""
    return round(sum(li["amount"] for li in line_items), 2)


def generate_tiers(
    items: List[Dict[str, Any]],
    location: str = "DC",
    lining_preference: str = "standard",
) -> Dict[str, Any]:
    """Generate tier A / B / C quotes for a list of analyzed items.

    Parameters
    ----------
    items : list[dict]
        Each item dict must have at minimum ``name``, ``type``,
        ``dimensions``, ``quantity``.
    location : str
        ``"DC"`` / ``"MD"`` / ``"VA"`` — for tax rate lookup.
    lining_preference : str
        Default lining type applied to all items.

    Returns
    -------
    dict  keyed ``"A"`` / ``"B"`` / ``"C"``, each containing
    ``name``, ``fabric_grade``, ``items``, ``subtotal``,
    ``tax_rate``, ``tax``, ``total``, ``deposit``.
    """
    tax_rate = TAX_RATES.get(location.upper(), 0.06)
    tiers: Dict[str, Any] = {}

    for tier_key in ("A", "B", "C"):
        tier_info = TIER_MULTIPLIERS[tier_key]
        tier_items: List[Dict[str, Any]] = []
        tier_subtotal = 0.0

        for item in items:
            line_items = build_line_items(
                item=item,
                tier=tier_key,
                lining=lining_preference,
                location=location,
            )
            item_subtotal = _sum_line_items(line_items)

            tier_items.append({
                "name": item.get("name", item.get("type", "Item")),
                "type": item.get("type", ""),
                "quantity": item.get("quantity", 1),
                "dimensions": item.get("dimensions", {}),
                "construction": item.get("construction", ""),
                "condition": item.get("condition", ""),
                "photo_url": item.get("photo_url"),
                "mockup_url": item.get("mockup_url"),
                "line_items": line_items,
                "subtotal": item_subtotal,
            })
            tier_subtotal += item_subtotal

        tier_subtotal = round(tier_subtotal, 2)
        tax = round(tier_subtotal * tax_rate, 2)
        total = round(tier_subtotal + tax, 2)
        deposit = round(total * DEPOSIT_PERCENTAGE, 2)

        tiers[tier_key] = {
            "name": tier_info["name"],
            "fabric_grade": tier_key,
            "items": tier_items,
            "subtotal": tier_subtotal,
            "tax_rate": tax_rate,
            "tax": tax,
            "total": total,
            "deposit": deposit,
        }

        logger.info(
            "Tier %s (%s): subtotal=$%.2f  tax=$%.2f  total=$%.2f  deposit=$%.2f",
            tier_key, tier_info["name"], tier_subtotal, tax, total, deposit,
        )

    return tiers
