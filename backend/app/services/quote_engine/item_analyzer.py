"""
Quote Intelligence System — AI Item Analyzer

Takes a customer photo and returns a structured list of all items detected,
with dimensions, quantities, construction details, and recommended treatments.
Uses Grok vision (via the backend vision endpoint) with Claude/MAX fallback.
"""

import json
import logging
import re
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

# Item type classification for pricing engine lookup
ITEM_TYPES = {
    # Window treatments
    "drapery_panel", "roman_shade", "roller_shade", "valance", "cornice", "swag",
    # Upholstery
    "dining_chair_seat", "dining_chair_full", "accent_chair", "wingback_chair",
    "club_chair", "ottoman", "bench_small", "bench_medium", "bench_large",
    "loveseat", "sofa_2cushion", "sofa_3cushion", "sectional_per_section",
    "headboard", "banquette", "seat_cushion", "back_cushion", "throw_pillow", "bolster",
}

ANALYSIS_PROMPT = """You are a professional upholsterer and window treatment specialist analyzing a customer photo.

Analyze this photo carefully and identify EVERY piece of furniture and EVERY window that could need service.

CRITICAL RULES:
1. Each DISTINCT item gets its own entry (3 different-sized windows = 3 separate items)
2. IDENTICAL items get ONE entry with a quantity count (6 matching dining chairs = quantity: 6)
3. Estimate dimensions in INCHES using visual reference objects (doors ~80"H, standard chairs ~18" seat, tables ~30"H, outlets ~4.5"H)
4. Classify each item using EXACTLY one of these types:
   Window: drapery_panel, roman_shade, roller_shade, valance, cornice, swag
   Seating: dining_chair_seat, dining_chair_full, accent_chair, wingback_chair, club_chair
   Sofa: loveseat, sofa_2cushion, sofa_3cushion, sectional_per_section
   Other: ottoman, bench_small (<=48"), bench_medium (49-96"), bench_large (>96"), banquette, headboard
   Cushion: seat_cushion, back_cushion, throw_pillow, bolster

{customer_notes_section}

Return ONLY valid JSON (no markdown, no explanation):
{{
    "room_type": "residential_dining" | "residential_living" | "commercial_restaurant" | "commercial_office" | "bedroom" | "other",
    "style": "modern" | "traditional" | "transitional" | "farmhouse" | "contemporary" | "industrial",
    "items": [
        {{
            "name": "Descriptive name (e.g. 'Left Wall Window', 'Dining Chair Set')",
            "type": "exact_type_from_list_above",
            "quantity": 1,
            "dimensions": {{"width": 72, "height": 84, "depth": 24}},
            "construction": "plain | tufted_diamond | tufted_channel | cushioned | skirted | buttoned",
            "current_material": "fabric | vinyl | leather | velvet | wood | none",
            "condition": "good | worn | damaged | needs_foam | needs_springs | new_construction",
            "cushion_count": 0,
            "special_features": ["welting", "nailhead", "skirt", "fringe", "piping", "tufting"],
            "recommended_treatment": "full_reupholster | recover_cushions | slipcover | new_construction | drapery | roman_shade | roller_shade",
            "notes": "Specific observations about this item",
            "location_in_photo": "left | center | right | background | foreground"
        }}
    ],
    "overall_notes": "General observations about the space",
    "questions": ["Question 1 for customer", "Question 2"]
}}
"""


async def analyze_photo_items(
    image_data: str,
    customer_notes: str = "",
    api_base: str = "http://localhost:8000/api/v1",
) -> dict:
    """
    Send photo to AI vision for structured item analysis.

    Args:
        image_data: base64 image data (with or without data:image prefix)
        customer_notes: customer's description of what they want
        api_base: backend API base URL

    Returns:
        dict with room_type, style, items[], overall_notes, questions[]
    """
    notes_section = (
        f"Customer notes: {customer_notes}"
        if customer_notes
        else "No customer notes provided."
    )
    prompt = ANALYSIS_PROMPT.format(customer_notes_section=notes_section)

    # Try the dedicated vision/analyze-items endpoint first
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(
                f"{api_base}/vision/analyze-items",
                json={"image": image_data, "prompt": prompt},
            )
            if res.status_code == 200:
                return res.json()
    except Exception as e:
        logger.warning(f"Vision analyze-items endpoint failed: {e}")

    # Fallback: use MAX chat with image
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            res = await client.post(
                f"{api_base}/max/chat/stream",
                json={
                    "message": prompt,
                    "image_data": image_data,
                    "model": "auto",
                    "history": [],
                },
            )
            # Parse SSE response for text content
            text = ""
            for line in res.text.split("\n"):
                if line.startswith("data: "):
                    try:
                        ev = json.loads(line[6:])
                        if ev.get("type") == "text":
                            text += ev.get("content", "")
                    except json.JSONDecodeError:
                        pass

            # Extract JSON from response
            return _extract_json(text)
    except Exception as e:
        logger.error(f"AI analysis failed: {e}")
        return _empty_result()


def analyze_photo_items_sync(image_data: str, customer_notes: str = "") -> dict:
    """Synchronous wrapper for analyze_photo_items."""
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run, analyze_photo_items(image_data, customer_notes)
                )
                return future.result(timeout=120)
        return loop.run_until_complete(
            analyze_photo_items(image_data, customer_notes)
        )
    except Exception:
        return asyncio.run(analyze_photo_items(image_data, customer_notes))


def _extract_json(text: str) -> dict:
    """Extract JSON object from AI response text."""
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from code blocks or raw JSON
    patterns = [
        r"```json\s*\n?(.*?)\n?```",
        r"```\s*\n?(.*?)\n?```",
        r'(\{[\s\S]*"items"[\s\S]*\})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue

    logger.error(f"Could not extract JSON from AI response: {text[:200]}")
    return _empty_result()


def _empty_result() -> dict:
    return {
        "room_type": "unknown",
        "style": "unknown",
        "items": [],
        "overall_notes": "Analysis failed — please try again or enter items manually.",
        "questions": [],
    }


def manual_item(
    name: str,
    item_type: str,
    quantity: int = 1,
    width: float = 0,
    height: float = 0,
    depth: float = 0,
    construction: str = "plain",
    condition: str = "good",
    cushion_count: int = 0,
    special_features: list = None,
    treatment: str = "full_reupholster",
    photo_url: str = None,
    notes: str = "",
) -> dict:
    """Create a manual item entry (when no photo analysis is used)."""
    return {
        "name": name,
        "type": item_type,
        "quantity": quantity,
        "dimensions": {"width": width, "height": height, "depth": depth},
        "construction": construction,
        "current_material": "unknown",
        "condition": condition,
        "cushion_count": cushion_count,
        "special_features": special_features or [],
        "recommended_treatment": treatment,
        "notes": notes,
        "photo_url": photo_url,
        "location_in_photo": "center",
    }
