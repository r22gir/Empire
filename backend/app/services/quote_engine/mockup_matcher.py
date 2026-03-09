"""
Mockup Matcher -- generates correct AI mockups for each quote item.

Fixes the bug where items get wrong mockups (e.g., ottoman image shown for
a wall bench).  For each item in a quote:

1. Determine the correct mockup category (bench, chair, sofa, window, etc.)
2. Build an inpaint prompt that describes the SPECIFIC treatment + fabric
3. Call the InpaintService to generate the visualization
4. Return the mockup URL associated with that specific item

The inpaint shows the ACTUAL item with the PROPOSED treatment,
not a generic stock image.
"""

import os
import io
import time
import uuid
import logging
import asyncio
import base64
from pathlib import Path
from typing import Optional

logger = logging.getLogger("quote_engine.mockup_matcher")


# ---------------------------------------------------------------------------
# Item-type -> mockup category mapping
# ---------------------------------------------------------------------------

MOCKUP_CATEGORIES = {
    # Window treatments
    "drapery_panel": "window_drapery",
    "roman_shade": "window_roman",
    "roller_shade": "window_roller",
    "valance": "window_valance",
    "cornice": "window_cornice",
    "swag": "window_swag",
    # Seating
    "dining_chair_seat": "chair_dining",
    "dining_chair_full": "chair_dining",
    "accent_chair": "chair_accent",
    "wingback_chair": "chair_wingback",
    "club_chair": "chair_club",
    # Sofas
    "loveseat": "sofa",
    "sofa_2cushion": "sofa",
    "sofa_3cushion": "sofa",
    "sectional_per_section": "sofa_sectional",
    # Other furniture
    "ottoman": "ottoman",
    "bench_small": "bench",
    "bench_medium": "bench",
    "bench_large": "bench",
    "banquette": "banquette",
    "headboard": "headboard",
    "seat_cushion": "cushion",
    "back_cushion": "cushion",
    "throw_pillow": "pillow",
    "bolster": "pillow",
}

# Which categories are window treatments vs upholstery
WINDOW_CATEGORIES = {
    "window_drapery", "window_roman", "window_roller",
    "window_valance", "window_cornice", "window_swag",
}

# Map our categories to the furniture_type string the inpaint prompts expect
CATEGORY_TO_FURNITURE_TYPE = {
    "chair_dining": "dining chair",
    "chair_accent": "accent chair",
    "chair_wingback": "wingback chair",
    "chair_club": "club chair",
    "sofa": "sofa",
    "sofa_sectional": "sectional sofa",
    "ottoman": "ottoman",
    "bench": "bench",
    "banquette": "banquette",
    "headboard": "headboard",
    "cushion": "cushion",
    "pillow": "throw pillow",
}

# Map our window categories to treatment types used in inpaint_prompts.py
CATEGORY_TO_TREATMENT = {
    "window_drapery": "ripplefold",
    "window_roman": "roman-shade",
    "window_roller": "roller-shade",
    "window_valance": "ripplefold",   # closest match
    "window_cornice": "ripplefold",   # closest match
    "window_swag": "pinch-pleat",     # closest match
}


# ---------------------------------------------------------------------------
# Fabric-grade descriptions (for standalone prompt builder)
# ---------------------------------------------------------------------------

FABRIC_DESCRIPTIONS = {
    "A": "quality cotton blend fabric",
    "B": "designer performance fabric",
    "C": "luxury premium fabric",
    "D": "ultra-luxury imported fabric",
}


# ---------------------------------------------------------------------------
# Per-category prompt templates (used when we need a precise item-level prompt
# instead of the generic tier prompts from inpaint_prompts.py)
# ---------------------------------------------------------------------------

ITEM_PROMPT_TEMPLATES = {
    "window_drapery": (
        "Beautiful {style} drapery panels in {fabric_desc}, professionally "
        "installed on a {width}-inch wide window, floor-length, with proper "
        "fullness and even folds"
    ),
    "window_roman": (
        "Flat-fold roman shade in {fabric_desc}, mounted on a {width}-inch "
        "window, showing clean horizontal folds when raised"
    ),
    "window_roller": (
        "Modern roller shade on a {width}-inch window, {fabric_desc}, "
        "clean lines, professional installation"
    ),
    "window_valance": (
        "Tailored valance in {fabric_desc} across a {width}-inch window"
    ),
    "window_cornice": (
        "Upholstered wooden cornice in {fabric_desc}, {width} inches wide"
    ),
    "window_swag": (
        "Elegant swag and jabot in {fabric_desc}, {width} inches wide, "
        "draped gracefully"
    ),
    "chair_dining": (
        "Beautifully reupholstered dining chair in {fabric_desc}"
        "{features_suffix}, professional finish"
    ),
    "chair_accent": (
        "Stunning accent chair reupholstered in {fabric_desc}, "
        "{construction} style{features_suffix}"
    ),
    "chair_wingback": (
        "Classic wingback chair in {fabric_desc}, {construction} back, "
        "with matching seat cushion"
    ),
    "chair_club": (
        "Refined club chair in {fabric_desc}, comfortable proportions, "
        "{construction} style"
    ),
    "sofa": (
        "Professionally reupholstered sofa in {fabric_desc}, "
        "{construction} style, with matching cushions"
    ),
    "sofa_sectional": (
        "Sectional sofa section in {fabric_desc}, matching the suite"
    ),
    "ottoman": (
        "Ottoman upholstered in {fabric_desc}, {construction} top"
    ),
    "bench": (
        "Long upholstered bench ({width} inches) in {fabric_desc}, "
        "{construction} style{features_suffix}, professional "
        "restaurant/commercial quality"
    ),
    "banquette": (
        "Built-in banquette seating in {fabric_desc}, {construction} back, "
        "{width} inches long"
    ),
    "headboard": (
        "Upholstered headboard in {fabric_desc}, {construction} design, "
        "{width} inches wide"
    ),
    "cushion": (
        "Custom cushion in {fabric_desc}, expertly sewn with clean edges"
    ),
    "pillow": (
        "Decorative throw pillow in {fabric_desc}, {construction} style"
    ),
}


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def build_inpaint_prompt(
    item: dict,
    fabric_grade: str = "B",
    fabric_color: str = "",
    style: str = "",
) -> str:
    """
    Build a detailed inpaint prompt for a single quote item.

    The prompt describes what the FINISHED item should look like so the AI can
    generate a realistic mockup showing the proposed treatment.
    """
    item_type = item.get("type", "")
    category = MOCKUP_CATEGORIES.get(item_type, "furniture")
    name = item.get("name", "item")
    construction = item.get("construction", "plain")
    features = item.get("special_features", [])
    dims = item.get("dimensions", {})
    width = dims.get("width", 60)

    # Fabric description
    fabric_desc = FABRIC_DESCRIPTIONS.get(fabric_grade, "quality fabric")
    if fabric_color:
        fabric_desc = f"{fabric_color} {fabric_desc}"

    features_suffix = (
        ", with " + ", ".join(features) if features else ""
    )

    template = ITEM_PROMPT_TEMPLATES.get(category)
    if template:
        base_prompt = template.format(
            fabric_desc=fabric_desc,
            style=style or "elegant",
            construction=construction,
            width=width,
            features_suffix=features_suffix,
        )
    else:
        base_prompt = f"Professionally finished {name} in {fabric_desc}"

    return (
        f"{base_prompt}. Photorealistic, professional interior photography, "
        "natural lighting, high quality."
    )


# ---------------------------------------------------------------------------
# Single-item mockup generation
# ---------------------------------------------------------------------------

async def generate_item_mockup(
    item: dict,
    original_photo_b64: Optional[str],
    fabric_grade: str = "B",
    fabric_color: str = "",
    style: str = "",
) -> Optional[str]:
    """
    Generate an AI mockup for a specific quote item.

    Uses the InpaintService (Stability AI inpaint on the customer photo with
    region detection + masking), falling back to Grok image generation, then
    to Stability text-to-image.

    Returns
    -------
    str or None
        URL of the generated mockup image, or ``None`` on failure.
    """
    item_type = item.get("type", "")
    category = MOCKUP_CATEGORIES.get(item_type, "furniture")
    is_window = category in WINDOW_CATEGORIES

    # ── Strategy 1: InpaintService (photo inpainting) ─────────────
    if original_photo_b64:
        try:
            from app.services.max.inpaint_service import InpaintService
            from app.services.max.inpaint_prompts import (
                build_window_inpaint_prompt,
                build_window_clean_prompt,
                build_upholstery_inpaint_prompt,
                build_upholstery_clean_prompt,
                build_upholstery_details,
                get_negative_prompt,
            )

            service = InpaintService()

            xai_key = os.getenv("XAI_API_KEY", "")
            stability_key = os.getenv("STABILITY_API_KEY", "")

            # Preprocess the customer photo
            photo_bytes = service._preprocess_image(original_photo_b64)
            if not photo_bytes:
                logger.warning("Could not preprocess photo for item mockup")
            else:
                # Detect regions relevant to THIS item
                regions = await service._detect_regions(
                    photo_bytes, xai_key,
                    detect_windows=is_window,
                    detect_furniture=not is_window,
                )

                # Build mask for the correct region type
                region_type = "window" if is_window else "furniture"
                mask_bytes = service._render_mask(
                    photo_bytes, regions, region_type
                )

                # Build prompt using the existing prompt library when possible
                if is_window:
                    treatment = CATEGORY_TO_TREATMENT.get(
                        category, "ripplefold"
                    )
                    inpaint_prompt = build_window_inpaint_prompt(
                        treatment, fabric_grade, fabric_color, style,
                    )
                    fallback_prompt = build_window_clean_prompt(
                        treatment, fabric_grade, fabric_color, style,
                    )
                    negative_prompt = get_negative_prompt(treatment)
                else:
                    furniture_type = CATEGORY_TO_FURNITURE_TYPE.get(
                        category, item.get("name", "furniture")
                    )
                    ai_analysis = item.get("ai_analysis", {})
                    details = build_upholstery_details(ai_analysis)
                    inpaint_prompt = build_upholstery_inpaint_prompt(
                        furniture_type, fabric_grade, fabric_color,
                        details, style,
                    )
                    fallback_prompt = build_upholstery_clean_prompt(
                        furniture_type, fabric_grade, fabric_color,
                        details, style,
                    )
                    negative_prompt = ""

                result = await service._inpaint_with_fallback(
                    photo_bytes,
                    mask_bytes,
                    inpaint_prompt,
                    negative_prompt,
                    stability_key,
                    xai_key,
                    fallback_prompt,
                )

                if result and result.get("image"):
                    from app.services.max.inpaint_service import _save_image
                    url = _save_image(
                        result["image"],
                        prefix=f"item-{category}",
                    )
                    logger.info(
                        "InpaintService mockup generated for %s (%s): %s",
                        item.get("name"), category, url,
                    )
                    return url

        except ImportError:
            logger.warning("InpaintService not importable")
        except Exception as e:
            logger.warning(
                "InpaintService failed for %s: %s", item.get("name"), e,
            )

    # ── Strategy 2: Stability AI text-to-image (no customer photo) ─
    prompt = build_inpaint_prompt(item, fabric_grade, fabric_color, style)
    try:
        import httpx

        api_key = os.getenv("STABILITY_API_KEY", "")
        if not api_key:
            logger.warning("No STABILITY_API_KEY for mockup generation")
            return None

        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(
                "https://api.stability.ai/v1/generation/"
                "stable-diffusion-xl-1024-v1-0/text-to-image",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "text_prompts": [{"text": prompt, "weight": 1.0}],
                    "cfg_scale": 7,
                    "height": 768,
                    "width": 1024,
                    "samples": 1,
                    "steps": 30,
                },
            )
            if res.status_code == 200:
                data = res.json()
                artifacts = data.get("artifacts", [])
                if artifacts:
                    img_b64 = artifacts[0]["base64"]
                    img_bytes = base64.b64decode(img_b64)

                    img_dir = Path(
                        os.path.expanduser(
                            "~/empire-repo/backend/data/generated"
                        )
                    )
                    img_dir.mkdir(parents=True, exist_ok=True)

                    filename = (
                        f"item-{category}-{int(time.time())}"
                        f"-{uuid.uuid4().hex[:6]}.png"
                    )
                    (img_dir / filename).write_bytes(img_bytes)

                    url = f"/api/v1/vision/images/{filename}"
                    logger.info("Stability t2i mockup generated: %s", filename)
                    return url
            else:
                logger.warning(
                    "Stability t2i error %s: %s",
                    res.status_code, res.text[:300],
                )
    except Exception as e:
        logger.warning("Stability AI text-to-image mockup failed: %s", e)

    return None


# ---------------------------------------------------------------------------
# Batch: generate mockups for every item in a quote
# ---------------------------------------------------------------------------

async def generate_all_item_mockups(
    items: list,
    original_photo_b64: Optional[str] = None,
    fabric_grade: str = "B",
    fabric_color: str = "",
    style: str = "",
) -> dict:
    """
    Generate mockups for all items in a quote, each matched to its type.

    Returns
    -------
    dict
        Mapping of item index (int) to mockup URL (str).
        Each ``item`` dict also gets a ``"mockup_url"`` key set in-place.
    """
    mockups: dict[int, str] = {}

    # Run all item mockups concurrently
    tasks = [
        generate_item_mockup(
            item=item,
            original_photo_b64=original_photo_b64,
            fabric_grade=fabric_grade,
            fabric_color=fabric_color,
            style=style,
        )
        for item in items
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.warning("Mockup failed for item %d: %s", i, result)
            continue
        if result:
            mockups[i] = result
            items[i]["mockup_url"] = result

    logger.info(
        "Generated %d/%d item mockups", len(mockups), len(items),
    )
    return mockups
