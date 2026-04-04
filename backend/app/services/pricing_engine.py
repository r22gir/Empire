"""
Empire Auto-Pricing Engine
Industry-standard calculators for drapery, roman shades, and upholstery.
All calculations store their inputs in a pricing_snapshot for audit trail.
"""
import math
import json
import logging
from typing import Optional
from datetime import datetime
from app.db.database import get_db

logger = logging.getLogger(__name__)


# ── Constants ──────────────────────────────────────────────────

# Fullness ratios by pleat style
FULLNESS_RATIOS = {
    "pinch_pleat": 2.5,
    "pinch": 2.5,
    "french_pleat": 2.5,
    "euro_pleat": 2.0,
    "ripplefold": 2.0,
    "grommet": 1.8,
    "rod_pocket": 2.5,
    "tab_top": 1.5,
    "goblet": 2.5,
    "inverted_pleat": 2.5,
    "flat_panel": 1.0,
    "pencil_pleat": 2.5,
    "cartridge": 2.5,
    "default": 2.5,
}

# Header allowances (inches)
HEADER_ALLOWANCES = {
    "pinch_pleat": 4,
    "pinch": 4,
    "french_pleat": 4,
    "euro_pleat": 3,
    "ripplefold": 0,
    "grommet": 2,
    "rod_pocket": 6,
    "tab_top": 0,
    "goblet": 5,
    "inverted_pleat": 4,
    "flat_panel": 4,
    "default": 4,
}

# Hem allowances (inches)
HEM_ALLOWANCES = {
    "standard": 8,    # double 4" hem
    "weighted": 4,    # single weighted hem
    "sheer": 12,      # double 6" hem for sheers
    "default": 8,
}

# Roman shade multipliers
ROMAN_MULTIPLIERS = {
    "flat": 1.0,
    "hobbled": 2.0,
    "classic": 1.5,
    "balloon": 2.5,
    "austrian": 3.0,
    "relaxed": 1.5,
    "default": 1.0,
}

# Upholstery base yardage by type
UPHOLSTERY_BASE_YARDS = {
    "sofa": 14,
    "sofa_3cushion": 14,
    "loveseat": 10,
    "loveseat_2cushion": 10,
    "sectional": 22,
    "accent_chair": 6,
    "armchair": 6,
    "wing_chair": 7,
    "club_chair": 7,
    "dining_chair": 2.5,
    "ottoman": 3,
    "bench": 4,
    "banquette": 2,      # per linear foot
    "headboard_twin": 3,
    "headboard_full": 4,
    "headboard_queen": 5,
    "headboard_king": 6,
    "headboard_cal_king": 6.5,
    "bar_stool": 2,
    "chaise": 12,
    "daybed": 10,
    "default": 6,
}

# Extra yards per cushion by type
YARDS_PER_CUSHION = {
    "sofa": 2.0,
    "sofa_3cushion": 2.0,
    "loveseat": 2.0,
    "loveseat_2cushion": 2.0,
    "sectional": 2.0,
    "accent_chair": 1.5,
    "armchair": 1.5,
    "wing_chair": 1.5,
    "club_chair": 1.5,
    "dining_chair": 0.5,
    "ottoman": 0,
    "default": 1.5,
}

# Default labor rates ($/hr)
DEFAULT_LABOR_RATES = {
    "drapery_sewing": 45.0,
    "upholstery": 55.0,
    "installation": 65.0,
    "roman_shade": 50.0,
    "millwork": 60.0,
    "design": 85.0,
}

# Standard labor hours by item type
LABOR_HOURS = {
    "drapery_panel": 3.0,
    "drapery_pair": 6.0,
    "roman_shade": 4.0,
    "upholstery_chair": 8.0,
    "upholstery_sofa": 20.0,
    "upholstery_loveseat": 14.0,
    "upholstery_sectional": 30.0,
    "upholstery_dining": 2.0,
    "upholstery_ottoman": 4.0,
    "headboard": 6.0,
    "cushion": 1.5,
    "pillow": 0.5,
    "banquette_per_foot": 2.0,
    "installation_per_window": 1.0,
}


# ── Drapery Yardage Calculator ─────────────────────────────────

def calculate_drapery_yardage(
    finished_width: float,       # inches
    finished_length: float,      # inches
    pleat_style: str = "pinch_pleat",
    fabric_width: float = 54,    # inches (usable width)
    pattern_repeat: float = 0,   # inches
    return_size: float = 4,      # inches per side
    overlap: float = 3,          # inches per panel
    hem_type: str = "standard",
    is_lining: bool = False,
    num_panels: int = 1,         # 1 for single, 2 for pair
) -> dict:
    """Industry-standard drapery yardage calculation.

    Formula:
    total_width = finished_width × fullness + returns + overlap
    num_widths = ceil(total_width / usable_fabric_width)
    cut_length = finished_length + header + hem + pattern_repeat_waste
    total_yards = (widths × cut_length) / 36
    """
    fullness = FULLNESS_RATIOS.get(pleat_style, FULLNESS_RATIOS["default"])
    header = HEADER_ALLOWANCES.get(pleat_style, HEADER_ALLOWANCES["default"])
    hem = HEM_ALLOWANCES.get(hem_type, HEM_ALLOWANCES["default"])

    if is_lining:
        header = max(header - 1, 0)  # lining slightly shorter
        hem = hem - 2

    # Total width needed
    total_width = (finished_width * fullness) + (return_size * 2) + (overlap * num_panels)

    # Number of fabric widths
    usable_width = fabric_width - 1  # 0.5" per side for seams
    num_widths = math.ceil(total_width / usable_width)

    # Cut length
    cut_length = finished_length + header + hem

    # Pattern repeat waste
    repeat_waste = 0
    if pattern_repeat > 0:
        cut_length_with_repeat = math.ceil(cut_length / pattern_repeat) * pattern_repeat
        repeat_waste = cut_length_with_repeat - cut_length
        cut_length = cut_length_with_repeat

    # Total yards
    total_inches = num_widths * cut_length
    total_yards = round(total_inches / 36, 2)

    return {
        "total_yards": total_yards,
        "num_widths": num_widths,
        "cut_length_inches": round(cut_length, 2),
        "total_width_needed": round(total_width, 2),
        "fullness_ratio": fullness,
        "header_allowance": header,
        "hem_allowance": hem,
        "pattern_repeat_waste": round(repeat_waste, 2),
        "formula": {
            "finished_width": finished_width,
            "finished_length": finished_length,
            "pleat_style": pleat_style,
            "fabric_width": fabric_width,
            "pattern_repeat": pattern_repeat,
            "return_size": return_size,
            "overlap": overlap,
            "hem_type": hem_type,
            "is_lining": is_lining,
            "num_panels": num_panels,
        },
    }


# ── Roman Shade Calculator ────────────────────────────────────

def calculate_roman_shade_yardage(
    finished_width: float,       # inches
    finished_length: float,      # inches
    shade_style: str = "flat",
    fabric_width: float = 54,    # inches
    pattern_repeat: float = 0,   # inches
) -> dict:
    """Roman shade yardage calculation.

    Formula:
    cut_width = finished_width + 6" (3" per side for hems)
    cut_length = finished_length + 12" (header + bottom hem)
    Multiply by style factor (flat=1×, hobbled=2×, balloon=2.5×, austrian=3×)
    """
    multiplier = ROMAN_MULTIPLIERS.get(shade_style, ROMAN_MULTIPLIERS["default"])

    cut_width = finished_width + 6   # 3" per side
    cut_length = finished_length + 12  # 6" top + 6" bottom

    # Pattern repeat
    repeat_waste = 0
    if pattern_repeat > 0:
        adjusted = math.ceil(cut_length / pattern_repeat) * pattern_repeat
        repeat_waste = adjusted - cut_length
        cut_length = adjusted

    # Number of fabric widths (if shade is wider than fabric)
    usable_width = fabric_width - 1
    num_widths = math.ceil(cut_width / usable_width)

    # Apply style multiplier to length
    adjusted_length = cut_length * multiplier

    total_inches = num_widths * adjusted_length
    total_yards = round(total_inches / 36, 2)

    return {
        "total_yards": total_yards,
        "num_widths": num_widths,
        "cut_width_inches": round(cut_width, 2),
        "cut_length_inches": round(cut_length, 2),
        "style_multiplier": multiplier,
        "pattern_repeat_waste": round(repeat_waste, 2),
        "formula": {
            "finished_width": finished_width,
            "finished_length": finished_length,
            "shade_style": shade_style,
            "fabric_width": fabric_width,
            "pattern_repeat": pattern_repeat,
        },
    }


# ── Upholstery Estimator ──────────────────────────────────────

def calculate_upholstery_yardage(
    piece_type: str = "accent_chair",
    cushion_count: int = 0,
    linear_feet: float = 0,      # for banquettes
    pattern_repeat: float = 0,   # inches
    fabric_width: float = 54,    # inches
) -> dict:
    """Upholstery yardage estimation using industry standards.

    Base yards by type + extra per cushion.
    Banquettes: 2 + 1.5/linear_foot.
    Pattern repeat adds ~15% waste.
    """
    base = UPHOLSTERY_BASE_YARDS.get(piece_type, UPHOLSTERY_BASE_YARDS["default"])
    per_cushion = YARDS_PER_CUSHION.get(piece_type, YARDS_PER_CUSHION["default"])

    if piece_type == "banquette" and linear_feet > 0:
        total_yards = base + (1.5 * linear_feet)
    else:
        total_yards = base + (per_cushion * cushion_count)

    # Pattern repeat waste (add ~15%)
    repeat_waste = 0
    if pattern_repeat > 0:
        repeat_waste = round(total_yards * 0.15, 2)
        total_yards += repeat_waste

    # Narrow fabric adjustment (if under 54")
    if fabric_width < 54:
        total_yards = round(total_yards * (54 / fabric_width), 2)

    total_yards = round(total_yards, 2)

    return {
        "total_yards": total_yards,
        "base_yards": base,
        "cushion_yards": round(per_cushion * cushion_count, 2),
        "repeat_waste_yards": repeat_waste,
        "formula": {
            "piece_type": piece_type,
            "cushion_count": cushion_count,
            "linear_feet": linear_feet,
            "pattern_repeat": pattern_repeat,
            "fabric_width": fabric_width,
        },
    }


# ── Full Price Calculator ──────────────────────────────────────

def calculate_full_price(
    item_type: str,              # "drapery", "roman_shade", "upholstery", "pillow", etc.
    dimensions: dict = None,     # {width, height, depth}
    fabric_price_per_yard: float = 0,
    lining_type: str = "none",   # "none", "standard", "blackout", "interlining"
    labor_rate: float = None,
    hardware: list = None,       # [{description, cost}]
    materials: list = None,      # [{description, cost}]
    pleat_style: str = "pinch_pleat",
    shade_style: str = "flat",
    piece_type: str = "accent_chair",
    cushion_count: int = 0,
    linear_feet: float = 0,
    pattern_repeat: float = 0,
    fabric_width: float = 54,
    quantity: int = 1,
    num_panels: int = 1,
) -> dict:
    """Complete price calculation with full breakdown.

    Returns unit_price, subtotal, and pricing_snapshot with all inputs.
    """
    dims = dimensions or {}
    width = float(dims.get('width', 0))
    height = float(dims.get('height', 0))

    yardage_result = None
    yardage = 0
    labor_hours = 0

    # ── Calculate yardage by type ──
    if item_type in ("drapery", "curtain", "drape"):
        if width > 0 and height > 0:
            yardage_result = calculate_drapery_yardage(
                finished_width=width, finished_length=height,
                pleat_style=pleat_style, fabric_width=fabric_width,
                pattern_repeat=pattern_repeat, num_panels=num_panels,
            )
            yardage = yardage_result["total_yards"]
        labor_hours = LABOR_HOURS.get("drapery_pair" if num_panels >= 2 else "drapery_panel", 3)
        if labor_rate is None:
            labor_rate = DEFAULT_LABOR_RATES["drapery_sewing"]

    elif item_type in ("roman_shade", "roman", "shade"):
        if width > 0 and height > 0:
            yardage_result = calculate_roman_shade_yardage(
                finished_width=width, finished_length=height,
                shade_style=shade_style, fabric_width=fabric_width,
                pattern_repeat=pattern_repeat,
            )
            yardage = yardage_result["total_yards"]
        labor_hours = LABOR_HOURS.get("roman_shade", 4)
        if labor_rate is None:
            labor_rate = DEFAULT_LABOR_RATES["roman_shade"]

    elif item_type in ("upholstery", "reupholstery", "sofa", "chair", "loveseat",
                       "accent_chair", "wing_chair", "sectional", "ottoman", "bench",
                       "banquette", "headboard", "dining_chair", "bar_stool", "chaise"):
        uph_type = piece_type if piece_type != "accent_chair" else item_type
        yardage_result = calculate_upholstery_yardage(
            piece_type=uph_type, cushion_count=cushion_count,
            linear_feet=linear_feet, pattern_repeat=pattern_repeat,
            fabric_width=fabric_width,
        )
        yardage = yardage_result["total_yards"]

        # Map labor hours
        if "sofa" in uph_type or "sectional" in uph_type:
            labor_hours = LABOR_HOURS.get(f"upholstery_{uph_type}", LABOR_HOURS["upholstery_sofa"])
        elif "chair" in uph_type:
            labor_hours = LABOR_HOURS.get("upholstery_chair", 8)
        elif "dining" in uph_type:
            labor_hours = LABOR_HOURS["upholstery_dining"]
        elif "ottoman" in uph_type:
            labor_hours = LABOR_HOURS["upholstery_ottoman"]
        else:
            labor_hours = LABOR_HOURS.get(f"upholstery_{uph_type}", 8)

        if labor_rate is None:
            labor_rate = DEFAULT_LABOR_RATES["upholstery"]

    else:
        # Generic item — use provided values
        if labor_rate is None:
            labor_rate = DEFAULT_LABOR_RATES.get("drapery_sewing", 45)
        labor_hours = 2

    # ── Cost breakdown ──
    fabric_total = round(yardage * fabric_price_per_yard, 2)

    # Lining cost
    lining_prices = {"none": 0, "standard": 8, "blackout": 14, "interlining": 18}
    lining_price_per_yard = lining_prices.get(lining_type, 0)
    lining_yards = round(yardage * 0.9, 2) if lining_type != "none" else 0
    lining_cost = round(lining_yards * lining_price_per_yard, 2)

    labor_total = round(labor_hours * (labor_rate or 0), 2)

    hardware_total = sum(h.get('cost', 0) for h in (hardware or []))
    materials_total = sum(m.get('cost', 0) for m in (materials or []))

    unit_price = round(fabric_total + lining_cost + labor_total + hardware_total + materials_total, 2)
    subtotal = round(unit_price * quantity, 2)

    # Build pricing snapshot
    snapshot = {
        "calculated_at": datetime.now().isoformat(),
        "item_type": item_type,
        "dimensions": dims,
        "yardage": yardage,
        "yardage_detail": yardage_result,
        "fabric_price_per_yard": fabric_price_per_yard,
        "fabric_total": fabric_total,
        "lining_type": lining_type,
        "lining_yards": lining_yards,
        "lining_price_per_yard": lining_price_per_yard,
        "lining_cost": lining_cost,
        "labor_hours": labor_hours,
        "labor_rate": labor_rate,
        "labor_total": labor_total,
        "hardware": hardware or [],
        "hardware_total": hardware_total,
        "materials": materials or [],
        "materials_total": materials_total,
        "quantity": quantity,
        "unit_price": unit_price,
        "subtotal": subtotal,
    }

    return {
        "yardage": yardage,
        "fabric_total": fabric_total,
        "lining_yards": lining_yards,
        "lining_cost": lining_cost,
        "labor_hours": labor_hours,
        "labor_rate": labor_rate,
        "labor_total": labor_total,
        "hardware_total": hardware_total,
        "materials_total": materials_total,
        "unit_price": unit_price,
        "quantity": quantity,
        "subtotal": subtotal,
        "pricing_snapshot": snapshot,
    }


# ── Auto-price a quote line item ──────────────────────────────

def auto_price_line_item(quote_id: str, item_id: int) -> dict:
    """Auto-price a quote line item using the pricing engine.
    Updates the line item in-place and returns the result."""
    with get_db() as conn:
        item = conn.execute(
            "SELECT * FROM quote_line_items WHERE id = ? AND quote_id = ?",
            (item_id, quote_id)
        ).fetchone()
        if not item:
            raise ValueError(f"Item {item_id} not found in quote {quote_id}")

        item = dict(item)

        result = calculate_full_price(
            item_type=item.get('item_type', 'drapery'),
            dimensions={'width': item.get('width', 0), 'height': item.get('height', 0), 'depth': item.get('depth', 0)},
            fabric_price_per_yard=item.get('fabric_price_per_yard', 0),
            lining_type=item.get('lining_type', 'none'),
            labor_rate=item.get('labor_rate'),
            pleat_style=item.get('item_style', 'pinch_pleat'),
            cushion_count=0,
            pattern_repeat=item.get('pattern_repeat', 0),
            fabric_width=item.get('fabric_width', 54) or 54,
            quantity=int(item.get('quantity', 1)),
        )

        conn.execute("""
            UPDATE quote_line_items SET
                yards_needed = ?, fabric_total = ?,
                lining_yards = ?, lining_cost = ?,
                labor_hours = ?, labor_rate = ?, labor_total = ?,
                unit_price = ?, subtotal = ?,
                pricing_snapshot_json = ?,
                updated_at = ?
            WHERE id = ? AND quote_id = ?
        """, (
            result['yardage'], result['fabric_total'],
            result['lining_yards'], result['lining_cost'],
            result['labor_hours'], result['labor_rate'], result['labor_total'],
            result['unit_price'], result['subtotal'],
            json.dumps(result['pricing_snapshot'], default=str),
            datetime.now().isoformat(),
            item_id, quote_id,
        ))

        # Recalculate quote totals
        from app.services.quote_service import _recalculate_totals
        _recalculate_totals(conn, quote_id, 'pricing_engine')

    return result


# ── Get/Update Labor Rates ─────────────────────────────────────

def get_labor_rates() -> dict:
    """Get current labor rates. For now returns defaults; could be DB-backed."""
    return {**DEFAULT_LABOR_RATES}


def update_labor_rate(category: str, rate: float) -> dict:
    """Update a labor rate category."""
    if category not in DEFAULT_LABOR_RATES:
        raise ValueError(f"Unknown labor category: {category}")
    DEFAULT_LABOR_RATES[category] = rate
    return get_labor_rates()
