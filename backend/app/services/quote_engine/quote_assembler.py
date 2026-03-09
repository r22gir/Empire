"""
Quote Intelligence System — Quote Assembler

Orchestrate the full pipeline: yardage → line items → tiers → quote.
Produces a complete quote data structure compatible with the existing
JSON format in ~/empire-repo/backend/data/quotes/.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .tier_generator import generate_tiers
from .yardage_calculator import calculate_yardage

logger = logging.getLogger(__name__)

QUOTES_DIR = os.path.expanduser("~/empire-repo/backend/data/quotes")


def _next_quote_number() -> str:
    """Generate sequential quote number like EST-2026-042."""
    year = datetime.now(timezone.utc).year
    existing = []
    if os.path.isdir(QUOTES_DIR):
        for fname in os.listdir(QUOTES_DIR):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(QUOTES_DIR, fname), "r") as f:
                        data = json.load(f)
                    qn = data.get("quote_number", "")
                    if qn.startswith(f"EST-{year}-"):
                        num = int(qn.split("-")[-1])
                        existing.append(num)
                except Exception:
                    continue
    next_num = max(existing, default=0) + 1
    return f"EST-{year}-{next_num:03d}"


def assemble_quote(
    analyzed_items: List[Dict[str, Any]],
    customer_name: str,
    location: str = "DC",
    lining: str = "standard",
    photo_urls: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Assemble a complete multi-tier quote from analyzed items.

    Parameters
    ----------
    analyzed_items : list[dict]
        Each dict must have: ``name``, ``type``, ``dimensions``, ``quantity``.
        Optional: ``construction``, ``special_features``, ``condition``,
        ``cushion_count``, ``photo_url``, ``mockup_url``.
    customer_name : str
        Client's name.
    location : str
        ``"DC"`` / ``"MD"`` / ``"VA"``.
    lining : str
        Default lining preference.
    photo_urls : dict, optional
        Map of item name → photo URL (overrides item-level photo_url).

    Returns
    -------
    dict  Complete quote ready for JSON storage and PDF generation.
    """
    # Apply photo_urls overrides if provided
    if photo_urls:
        for item in analyzed_items:
            name = item.get("name", "")
            if name in photo_urls:
                item["photo_url"] = photo_urls[name]

    # Compute yardage for each item (attach to item for reference)
    for item in analyzed_items:
        yardage_opts: Dict[str, Any] = {}
        if item.get("cushion_count"):
            yardage_opts["cushion_count"] = item["cushion_count"]
        if any("tuft" in f.lower() for f in item.get("special_features", [])):
            yardage_opts["tufted"] = True
        yardage_result = calculate_yardage(
            item.get("type", "accent_chair"),
            item.get("dimensions", {}),
            yardage_opts,
        )
        item["_yardage"] = yardage_result

    # Generate all three tiers
    tiers = generate_tiers(analyzed_items, location=location, lining_preference=lining)

    # Build final quote structure
    quote_id = uuid.uuid4().hex[:8]
    quote_number = _next_quote_number()
    now = datetime.now(timezone.utc).isoformat()

    quote: Dict[str, Any] = {
        "id": quote_id,
        "quote_number": quote_number,
        "customer_name": customer_name,
        "customer_email": "",
        "customer_phone": "",
        "customer_address": "",
        "project_name": f"Quote for {customer_name}",
        "location": location.upper(),
        "lining_preference": lining,
        "status": "draft",
        "created_at": now,
        "updated_at": now,
        "items": [
            {
                "name": item.get("name", ""),
                "type": item.get("type", ""),
                "dimensions": item.get("dimensions", {}),
                "quantity": item.get("quantity", 1),
                "construction": item.get("construction", ""),
                "condition": item.get("condition", ""),
                "special_features": item.get("special_features", []),
                "cushion_count": item.get("cushion_count", 0),
                "photo_url": item.get("photo_url"),
                "mockup_url": item.get("mockup_url"),
                "yardage": item.get("_yardage", {}),
            }
            for item in analyzed_items
        ],
        "tiers": tiers,
    }

    # Save to disk
    os.makedirs(QUOTES_DIR, exist_ok=True)
    filepath = os.path.join(QUOTES_DIR, f"{quote_id}.json")
    with open(filepath, "w") as f:
        json.dump(quote, f, indent=2, default=str)
    logger.info("Quote %s saved to %s", quote_number, filepath)

    return quote


def recalculate_quote(quote_id: str) -> Dict[str, Any]:
    """Reload an existing quote and re-run pricing with current tables.

    Parameters
    ----------
    quote_id : str
        The 8-character hex quote ID.

    Returns
    -------
    dict  Updated quote.
    """
    filepath = os.path.join(QUOTES_DIR, f"{quote_id}.json")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Quote '{quote_id}' not found at {filepath}")

    with open(filepath, "r") as f:
        existing = json.load(f)

    logger.info("Recalculating quote %s (%s)", existing.get("quote_number"), quote_id)

    # Reconstruct analyzed_items from stored items
    analyzed_items = []
    for stored_item in existing.get("items", []):
        analyzed_items.append({
            "name": stored_item.get("name", ""),
            "type": stored_item.get("type", ""),
            "dimensions": stored_item.get("dimensions", {}),
            "quantity": stored_item.get("quantity", 1),
            "construction": stored_item.get("construction", ""),
            "condition": stored_item.get("condition", ""),
            "special_features": stored_item.get("special_features", []),
            "cushion_count": stored_item.get("cushion_count", 0),
            "photo_url": stored_item.get("photo_url"),
            "mockup_url": stored_item.get("mockup_url"),
        })

    location = existing.get("location", "DC")
    lining = existing.get("lining_preference", "standard")

    # Re-generate tiers with current pricing tables
    tiers = generate_tiers(analyzed_items, location=location, lining_preference=lining)

    # Update the quote
    now = datetime.now(timezone.utc).isoformat()
    existing["tiers"] = tiers
    existing["updated_at"] = now
    existing["status"] = existing.get("status", "draft")

    # Re-compute yardage
    for i, item in enumerate(analyzed_items):
        yardage_opts: Dict[str, Any] = {}
        if item.get("cushion_count"):
            yardage_opts["cushion_count"] = item["cushion_count"]
        if any("tuft" in f.lower() for f in item.get("special_features", [])):
            yardage_opts["tufted"] = True
        yardage_result = calculate_yardage(
            item.get("type", "accent_chair"),
            item.get("dimensions", {}),
            yardage_opts,
        )
        if i < len(existing.get("items", [])):
            existing["items"][i]["yardage"] = yardage_result

    # Save updated version
    with open(filepath, "w") as f:
        json.dump(existing, f, indent=2, default=str)
    logger.info("Quote %s recalculated and saved", existing.get("quote_number"))

    return existing
