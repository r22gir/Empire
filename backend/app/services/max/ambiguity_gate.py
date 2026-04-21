"""Deterministic clarification gate for ambiguous inventory/value requests."""

from __future__ import annotations

import re


_ACTION_TERMS = (
    "inventory",
    "catalog",
    "catalogue",
    "value",
    "valuation",
    "appraise",
    "appraisal",
    "price",
    "sell",
    "sales",
    "listing",
    "list my",
    "worth",
)

_AMBIGUOUS_OBJECT_TERMS = (
    "live magazines",
    "live inventory",
    "my items",
    "my stuff",
    "the collection",
    "my collection",
    "these items",
    "those items",
    "this lot",
    "the lot",
)

_CATEGORY_HINTS = (
    "life magazine",
    "life magazines",
    "playboy",
    "sports illustrated",
    "comic",
    "comics",
    "vinyl",
    "record",
    "records",
    "watch",
    "watches",
    "coin",
    "coins",
    "stamp",
    "stamps",
    "book",
    "books",
    "furniture",
    "art",
    "jewelry",
    "camera",
    "card",
    "cards",
)


def _normalize(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def should_clarify_inventory_request(message: str | None) -> bool:
    """Return True when a request needs category identity before planning.

    The gate is intentionally narrow: it blocks category-specific inventory,
    valuation, cataloging, and sales plans only when the object/category is
    ambiguous. The live-test regression is "inventory my live magazines",
    where "live" can mean current active inventory or a LIFE magazine category.
    """

    text = _normalize(message)
    if not text:
        return False

    if not any(term in text for term in _ACTION_TERMS):
        return False

    if "live magazines" in text:
        return True

    if any(term in text for term in _AMBIGUOUS_OBJECT_TERMS):
        return True

    has_generic_magazines = "magazines" in text or "magazine" in text
    has_specific_category = any(term in text for term in _CATEGORY_HINTS)
    return has_generic_magazines and not has_specific_category


def build_inventory_clarification(message: str | None) -> str:
    quoted = (message or "").strip()
    prefix = f'Before I inventory or value "{quoted}", I need to confirm the category.' if quoted else (
        "Before I inventory or value this, I need to confirm the category."
    )
    return (
        f"{prefix}\n"
        "Which one do you mean?\n"
        "- current live inventory records\n"
        "- LIFE magazine issues\n"
        "- a magazine collection by title/date/issue\n"
        "- another category or product line\n\n"
        "Once you confirm the category, I can make the inventory, cataloging, valuation, or sales plan without guessing."
    )
