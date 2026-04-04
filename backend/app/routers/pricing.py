"""
Pricing Engine API Router
Drapery yardage, roman shade, upholstery, and full price calculations.
"""
from fastapi import APIRouter, HTTPException
import logging

from app.services.pricing_engine import (
    calculate_drapery_yardage,
    calculate_roman_shade_yardage,
    calculate_upholstery_yardage,
    calculate_full_price,
    auto_price_line_item,
    get_labor_rates,
    update_labor_rate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pricing", tags=["pricing"])


@router.post("/calculate")
async def calculate_price(body: dict):
    """Full price calculation with breakdown and audit snapshot.

    Required: item_type
    Optional: dimensions, fabric_price_per_yard, lining_type, labor_rate,
              hardware, materials, pleat_style, shade_style, piece_type,
              cushion_count, pattern_repeat, fabric_width, quantity
    """
    try:
        result = calculate_full_price(
            item_type=body.get("item_type", "drapery"),
            dimensions=body.get("dimensions"),
            fabric_price_per_yard=float(body.get("fabric_price_per_yard", 0)),
            lining_type=body.get("lining_type", "none"),
            labor_rate=body.get("labor_rate"),
            hardware=body.get("hardware"),
            materials=body.get("materials"),
            pleat_style=body.get("pleat_style", "pinch_pleat"),
            shade_style=body.get("shade_style", "flat"),
            piece_type=body.get("piece_type", "accent_chair"),
            cushion_count=int(body.get("cushion_count", 0)),
            linear_feet=float(body.get("linear_feet", 0)),
            pattern_repeat=float(body.get("pattern_repeat", 0)),
            fabric_width=float(body.get("fabric_width", 54)),
            quantity=int(body.get("quantity", 1)),
            num_panels=int(body.get("num_panels", 1)),
        )
        return result
    except Exception as e:
        raise HTTPException(400, str(e))


@router.post("/yardage")
async def calculate_yardage(body: dict):
    """Calculate yardage only (no pricing). Auto-detects type.

    Required: item_type, width, height (for drapery/roman)
    """
    item_type = body.get("item_type", "drapery")
    width = float(body.get("width", body.get("finished_width", 0)))
    height = float(body.get("height", body.get("finished_length", 0)))

    if item_type in ("drapery", "curtain", "drape"):
        return calculate_drapery_yardage(
            finished_width=width,
            finished_length=height,
            pleat_style=body.get("pleat_style", "pinch_pleat"),
            fabric_width=float(body.get("fabric_width", 54)),
            pattern_repeat=float(body.get("pattern_repeat", 0)),
            num_panels=int(body.get("num_panels", 1)),
        )
    elif item_type in ("roman_shade", "roman", "shade"):
        return calculate_roman_shade_yardage(
            finished_width=width,
            finished_length=height,
            shade_style=body.get("shade_style", "flat"),
            fabric_width=float(body.get("fabric_width", 54)),
            pattern_repeat=float(body.get("pattern_repeat", 0)),
        )
    elif item_type in ("upholstery", "reupholstery", "sofa", "chair", "accent_chair"):
        return calculate_upholstery_yardage(
            piece_type=body.get("piece_type", item_type),
            cushion_count=int(body.get("cushion_count", 0)),
            linear_feet=float(body.get("linear_feet", 0)),
            pattern_repeat=float(body.get("pattern_repeat", 0)),
            fabric_width=float(body.get("fabric_width", 54)),
        )
    else:
        raise HTTPException(400, f"Unknown item type for yardage: {item_type}")


@router.get("/labor-rates")
async def labor_rates():
    """Get current labor rates by category."""
    return get_labor_rates()


@router.patch("/labor-rates")
async def update_rates(body: dict):
    """Update a labor rate. Body: {category: str, rate: float}"""
    category = body.get("category")
    rate = body.get("rate")
    if not category or rate is None:
        raise HTTPException(400, "category and rate required")
    try:
        return update_labor_rate(category, float(rate))
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/quotes/{quote_id}/items/{item_id}/auto-price")
async def auto_price_item(quote_id: str, item_id: int):
    """Auto-price a specific line item using the pricing engine.
    Updates the item in-place and recalculates quote totals."""
    try:
        result = auto_price_line_item(quote_id, item_id)
        return {"status": "priced", "pricing": result}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))
