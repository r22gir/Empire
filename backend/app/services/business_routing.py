"""Helpers for routing quote and drawing records to the correct business."""
from __future__ import annotations

from typing import Optional


def normalize_route_to(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    value = raw.strip().lower()
    if value in {"workroom", "woodcraft"}:
        return value
    if value in {"empire workroom", "empire-workroom"}:
        return "workroom"
    if value in {"empire woodcraft", "empire-woodcraft", "craftforge"}:
        return "woodcraft"
    return None


def route_to_for_item_type(item_type: Optional[str], explicit: Optional[str] = None) -> str:
    """Resolve the business route for a drawing or quote item."""
    normalized = normalize_route_to(explicit)
    if normalized:
        return normalized

    item_value = (item_type or "").strip().lower()
    if not item_value:
        return "workroom"

    if "bench" in item_value:
        return "woodcraft"

    try:
        from app.services.vision.renderer_registry import get_business_unit

        routed = get_business_unit(item_value)
        if routed in {"workroom", "woodcraft"}:
            return routed
    except Exception:
        pass

    woodcraft_keywords = (
        "booth",
        "banquette",
        "shelving",
        "desk",
        "table",
        "millwork",
        "commercial",
        "cabinet",
        "bookcase",
        "closet",
        "vanity",
    )
    if any(keyword in item_value for keyword in woodcraft_keywords):
        return "woodcraft"
    return "workroom"
