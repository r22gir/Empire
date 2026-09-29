"""First-pass yardage / fabric estimation for Workroom items.

This is intentionally simple. It produces a fabric-yardage estimate from
the dimensions in the request, with separate handling for:

  - drapery (linear-yardage for a single panel or full window width)
  - roman shades
  - cornices / valances
  - upholstery (square-yardage from W × D × waste factor)
  - cushions / pillows
  - headboards
  - bedding (flat yardage)
  - banquette / bench (linear-yardage for back panel + side panels)

All numbers are conservative first-pass estimates intended to be useful
for quoting conversations, not for procurement. They are documented in
the response as "first-pass" so the founder knows the precision.

Inputs are inches unless suffixed `_ft`. Outputs are in yards for fabric
yardage and linear feet for trim/yardstick.

No external dependencies. Safe to import from anywhere.
"""

from __future__ import annotations

from typing import Any


# Industry-typical waste factors. Conservative — not a tight pattern.
WASTE_UPHOLSTERY = 1.15  # 15% waste for upholstery cuts
WASTE_DRAPERY = 1.20  # 20% waste for drapery pattern repeat + hem
WASTE_CUSHION = 1.10  # 10% waste for cushion covers
WASTE_BEDDING = 1.10  # 10% waste for bedding

# Standard fabric widths in inches.
FABRIC_WIDTH_54 = 54
FABRIC_WIDTH_60 = 60


def _fabric_width_with_provenance(dimensions: dict | None) -> tuple[float, str]:
    """Resolve fabric width for a drawing-yardage estimator.

    H68 D40: the pre-H68 hardcoded FABRIC_WIDTH_54 was an unsourced
    default. Per the ruling, a value entering yardage_calculator.py
    or a drawing carries its source OR is marked PENDING. Callers may
    pass `fabric_width_in` (override) and `fabric_width_provenance`
    ('catalog' / 'issued:<doc>' / 'search_results_url:<url>' /
    'pending'). When fabric_width_in is absent we fall back to the
    historical 54" default but the OUTPUT carries provenance='pending'
    so downstream rendering can label it. PENDING never blocks — a
    drawing with three PENDING fields is a working drawing.
    """
    d = dimensions or {}
    fw = d.get("fabric_width_in")
    if fw is not None:
        try:
            return float(fw), (d.get("fabric_width_provenance") or "explicit")
        except (TypeError, ValueError):
            return FABRIC_WIDTH_54, "pending"
    return FABRIC_WIDTH_54, "pending"


def _safe_num(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def estimate_drapery(dimensions: dict) -> dict:
    """Linear-yardage estimate for a drapery panel set.

    Expects dimensions: width, drop, return, panels, fullness.
    Returns: fabric_yards, linear_feet_of_fabric (at 54" width),
             notes.
    """
    width = _safe_num(dimensions.get("width"), 108)
    drop = _safe_num(dimensions.get("drop"), 108)
    return_in = _safe_num(dimensions.get("return"), 4.5)
    panels = max(1, int(_safe_num(dimensions.get("panels"), 2)))
    fullness = _safe_num(dimensions.get("fullness"), 2.5)

    # Total finished width after fullness, in inches
    finished_width = width * fullness
    # Each panel width before seam allowances
    panel_width_in = finished_width / panels
    # Cut length per panel = drop + hem + return
    cut_length_in = drop + 4 + return_in  # 4" double hem

    # Fabric is sold by the yard at a standard width. The number of widths
    # needed per panel = ceil(panel_width_in / fabric_width)
    import math

    widths_needed = math.ceil(panel_width_in / FABRIC_WIDTH_54)

    # Yards per panel = (widths_needed * cut_length_in) / 36
    yards_per_panel = (widths_needed * cut_length_in) / 36.0
    total_yards = yards_per_panel * panels * WASTE_DRAPERY

    return {
        "fabric_yards": round(total_yards, 2),
        "linear_feet": round(total_yards * 3, 2),
        "panels": panels,
        "fabric_width": FABRIC_WIDTH_54,
        "fabric_width_provenance": "pending",  # H68 D40: 54" default is unsourced
        "waste_factor": WASTE_DRAPERY,
        "notes": "First-pass estimate; verify with pattern repeat before ordering.",
    }


def estimate_roman_shade(dimensions: dict) -> dict:
    """Linear-yardage estimate for a roman shade.

    Expects: width, height/drop, fold_spacing (optional).
    """
    import math

    width = _safe_num(dimensions.get("width"), 54)
    drop = _safe_num(dimensions.get("drop") or dimensions.get("height"), 72)
    return_in = _safe_num(dimensions.get("return"), 1.5)

    # Width on fabric after fullness (1.0 for flat; +0.25 for fold clearance)
    cut_width = width * 1.0
    cut_length = drop + return_in + 6  # 6" rod pocket + hems

    widths_needed = math.ceil(cut_width / FABRIC_WIDTH_54)
    yards = (widths_needed * cut_length) / 36.0 * WASTE_DRAPERY
    return {
        "fabric_yards": round(yards, 2),
        "linear_feet": round(yards * 3, 2),
        "fabric_width": FABRIC_WIDTH_54,
        "fabric_width_provenance": "pending",  # H68 D40: 54" default is unsourced
        "waste_factor": WASTE_DRAPERY,
        "notes": "First-pass estimate; add lining yardage separately.",
    }


def estimate_cornice(dimensions: dict) -> dict:
    """Linear-yardage for a cornice or valance.

    Cornices use very little fabric — typically a single width.
    """
    width = _safe_num(dimensions.get("width"), 72)
    height = _safe_num(dimensions.get("height") or dimensions.get("drop"), 24)
    return_in = _safe_num(dimensions.get("return"), 4)

    import math

    cut_length = (height * 2) + 6  # top + front + hems
    widths_needed = math.ceil(width / FABRIC_WIDTH_54)
    yards = (widths_needed * cut_length) / 36.0 * WASTE_DRAPERY
    return {
        "fabric_yards": round(yards, 2),
        "linear_feet": round(yards * 3, 2),
        "fabric_width": FABRIC_WIDTH_54,
        "fabric_width_provenance": "pending",  # H68 D40: 54" default is unsourced
        "waste_factor": WASTE_DRAPERY,
        "notes": "Cornice yardage is approximate; add 0.5 yd for welt if used.",
    }


def estimate_upholstery(dimensions: dict) -> dict:
    """Square-yardage estimate for a generic upholstery piece.

    Computed as (W * D) / 36 sq.ft. * 2 (sides) * waste, divided by
    standard 54" width.

    Expects: width, depth, height. (Cushions, arms, and back may add
    10-20% in a real estimate.)
    """
    width = _safe_num(dimensions.get("width"), 32)
    depth = _safe_num(dimensions.get("depth"), 34)
    height = _safe_num(dimensions.get("height"), 36)

    # Surface area in sq inches: front, back, top, two sides, bottom
    front = width * height
    back = width * height
    top = width * depth
    side1 = depth * height
    side2 = depth * height
    bottom = width * depth
    total_sq_in = front + back + top + side1 + side2 + bottom
    total_sq_ft = total_sq_in / 144.0

    # Convert to linear yards at 54" width: yard = 54" * 36" = 1944 sq.in
    # We need to cover total_sq_in * waste / 1944 yards
    raw_yards = (total_sq_in * WASTE_UPHOLSTERY) / (FABRIC_WIDTH_54 * 36)
    return {
        "fabric_yards": round(raw_yards, 2),
        "linear_feet": round(raw_yards * 3, 2),
        "square_feet": round(total_sq_ft, 2),
        "fabric_width": FABRIC_WIDTH_54,
        "fabric_width_provenance": "pending",  # H68 D40: 54" default is unsourced
        "waste_factor": WASTE_UPHOLSTERY,
        "notes": "First-pass upholstery estimate; add 0.5-1.0 yd for welts/piping.",
    }


def estimate_cushion(dimensions: dict) -> dict:
    """Cushion / pillow yardage from W × D × H."""
    width = _safe_num(dimensions.get("width"), 24)
    depth = _safe_num(dimensions.get("depth"), 24)
    height = _safe_num(dimensions.get("height"), 4)

    import math

    # Cushion needs top, bottom, 4 sides, plus seam allowance
    perimeter = 2 * (width + depth)
    total_length_in = (width * depth) / FABRIC_WIDTH_54 + perimeter + height * 4
    yards = (total_length_in / 36.0) * WASTE_CUSHION
    return {
        "fabric_yards": round(yards, 2),
        "linear_feet": round(yards * 3, 2),
        "fabric_width": FABRIC_WIDTH_54,
        "fabric_width_provenance": "pending",  # H68 D40: 54" default is unsourced
        "waste_factor": WASTE_CUSHION,
        "notes": "First-pass estimate for single cushion; add zipper allowance if used.",
    }


def estimate_headboard(dimensions: dict) -> dict:
    """Headboard yardage — single panel, height-driven."""
    width = _safe_num(dimensions.get("width"), 62)
    height = _safe_num(dimensions.get("height"), 56)
    depth = _safe_num(dimensions.get("depth"), 4)

    import math

    front = width * height
    back = width * height
    side = 2 * (depth * height)
    total_sq_in = front + back + side
    raw_yards = (total_sq_in * WASTE_UPHOLSTERY) / (FABRIC_WIDTH_54 * 36)
    return {
        "fabric_yards": round(raw_yards, 2),
        "linear_feet": round(raw_yards * 3, 2),
        "fabric_width": FABRIC_WIDTH_54,
        "fabric_width_provenance": "pending",  # H68 D40: 54" default is unsourced
        "waste_factor": WASTE_UPHOLSTERY,
        "notes": "First-pass estimate; tufting adds 10-20% depending on density.",
    }


def estimate_bedding(dimensions: dict) -> dict:
    """Bedding — flat-yardage from W × D."""
    width = _safe_num(dimensions.get("width"), 90)
    depth = _safe_num(dimensions.get("depth"), 80)

    import math

    # Duvet: top + bottom + 2 sides
    total_sq_in = (width * depth) * 2 + (depth * 12 * 2) + (width * 12 * 2)
    yards = (total_sq_in * WASTE_BEDDING) / (FABRIC_WIDTH_54 * 36)
    return {
        "fabric_yards": round(yards, 2),
        "linear_feet": round(yards * 3, 2),
        "fabric_width": FABRIC_WIDTH_54,
        "fabric_width_provenance": "pending",  # H68 D40: 54" default is unsourced
        "waste_factor": WASTE_BEDDING,
        "notes": "First-pass estimate; add shams and pillows separately.",
    }


def estimate_banquette(dimensions: dict) -> dict:
    """Banquette / bench linear-yardage for seat + back + sides."""
    width = _safe_num(dimensions.get("width"), 120)
    depth = _safe_num(dimensions.get("depth"), 22)
    seat_h = _safe_num(dimensions.get("seat_height"), 18)
    back_h = _safe_num(dimensions.get("back_height"), 18)

    # Seat face: width * depth (top + front)
    # Back face: width * back_h (front + back + top)
    # Sides: 2 * depth * (seat_h + back_h)
    seat_sq = width * depth * 2
    back_sq = width * back_h * 2 + width * 4  # +4" thickness
    sides_sq = 2 * depth * (seat_h + back_h) * 2
    total_sq_in = seat_sq + back_sq + sides_sq
    yards = (total_sq_in * WASTE_UPHOLSTERY) / (FABRIC_WIDTH_54 * 36)
    return {
        "fabric_yards": round(yards, 2),
        "linear_feet": round(yards * 3, 2),
        "fabric_width": FABRIC_WIDTH_54,
        "fabric_width_provenance": "pending",  # H68 D40: 54" default is unsourced
        "waste_factor": WASTE_UPHOLSTERY,
        "notes": "First-pass estimate for full-upholstered banquette; cushions separate.",
    }


_ESTIMATORS = {
    "drapery": estimate_drapery,
    "curtain": estimate_drapery,
    "window": estimate_drapery,
    "roman_shade": estimate_roman_shade,
    "roman": estimate_roman_shade,
    "shade": estimate_roman_shade,
    "cornice": estimate_cornice,
    "valance": estimate_cornice,
    "cornice_valance": estimate_cornice,
    "sofa": estimate_upholstery,
    "chair": estimate_upholstery,
    "ottoman": estimate_upholstery,
    "slipcover": estimate_upholstery,
    "cushion": estimate_cushion,
    "pillow": estimate_cushion,
    "headboard": estimate_headboard,
    "bedding": estimate_bedding,
    "duvet": estimate_bedding,
    "banquette": estimate_banquette,
    "bench": estimate_banquette,
}


def estimate(item_type: str, dimensions: dict) -> dict:
    """Dispatch to the right estimator for an item type.

    Always returns a dict, even for unknown types — falls back to a generic
    upholstery estimate and marks it `confidence="fallback"`.
    """
    fn = _ESTIMATORS.get(item_type.lower())
    if fn:
        result = fn(dimensions)
        result["item_type"] = item_type
        result["estimator"] = fn.__name__
        result["confidence"] = "first_pass"
        return result
    # Fallback: treat as upholstery
    result = estimate_upholstery(dimensions)
    result["item_type"] = item_type
    result["estimator"] = "estimate_upholstery"
    result["confidence"] = "fallback"
    result["notes"] = (result.get("notes", "") + " [fallback estimator]").strip()
    return result
