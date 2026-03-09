"""
Quote Intelligence System — Yardage Calculator

Calculate fabric / material needs from item type + dimensions.
All yardage values assume 54-inch wide fabric unless noted.
"""

import logging
import math
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Base yardage table (yards of 54" fabric)
# ---------------------------------------------------------------------------
YARDAGE_TABLE: Dict[str, float] = {
    "dining_chair_seat": 0.5,
    "dining_chair_full": 2.5,
    "accent_chair": 5.0,
    "wingback_chair": 7.0,
    "club_chair": 6.5,
    "ottoman_small": 2.0,   # up to 24"
    "ottoman_large": 3.5,   # 24"+
    "bench_per_linear_ft": 1.2,
    "loveseat": 10.0,
    "sofa_2cushion": 12.0,
    "sofa_3cushion": 16.0,
    "sectional_per_section": 10.0,
    "headboard_per_sqft": 0.5,
    "banquette_per_linear_ft": 1.5,
    "seat_cushion": 1.5,
    "back_cushion": 2.0,
    "throw_pillow": 0.75,
    "drapery_per_width": 3.0,
    "roman_shade_per_sqft": 0.25,
    "valance_per_linear_ft": 0.75,
    "cornice_per_linear_ft": 0.5,
    "swag": 2.5,
}

FABRIC_WIDTH_INCHES = 54


def _round_up_half_yard(yards: float) -> float:
    """Round *yards* UP to the nearest 0.5 yard."""
    return math.ceil(yards * 2) / 2


def calculate_yardage(
    item_type: str,
    dimensions: Optional[Dict[str, float]] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Calculate fabric yardage for an item.

    Parameters
    ----------
    item_type : str
        Key matching an item category (e.g. ``"sofa_3cushion"``).
    dimensions : dict, optional
        ``{"width": inches, "height": inches, "depth": inches}``
    options : dict, optional
        ``{"tufted": bool, "pattern_repeat": int (inches),
           "cushion_count": int, "fullness": float}``

    Returns
    -------
    dict  ``{"yards": float, "calculation": str}``
    """
    dims = dimensions or {}
    opts = options or {}
    explanation_parts: list[str] = []
    yards = 0.0

    width_in = dims.get("width", 0)
    height_in = dims.get("height", 0)
    depth_in = dims.get("depth", 0)
    linear_ft = width_in / 12 if width_in else 0

    # ----- Ottoman sizing -----
    if item_type == "ottoman":
        if width_in and width_in <= 24:
            item_type = "ottoman_small"
        else:
            item_type = "ottoman_large"

    # ----- Bench types → per-linear-ft -----
    if item_type in ("bench_small", "bench_medium", "bench_large", "bench"):
        yards = YARDAGE_TABLE["bench_per_linear_ft"] * max(linear_ft, 1)
        explanation_parts.append(
            f"Bench: {YARDAGE_TABLE['bench_per_linear_ft']} yd/ft × {linear_ft:.1f} ft = {yards:.1f} yd"
        )

    # ----- Banquette → per-linear-ft -----
    elif item_type == "banquette":
        yards = YARDAGE_TABLE["banquette_per_linear_ft"] * max(linear_ft, 1)
        explanation_parts.append(
            f"Banquette: {YARDAGE_TABLE['banquette_per_linear_ft']} yd/ft × {linear_ft:.1f} ft = {yards:.1f} yd"
        )

    # ----- Headboard → per-sqft -----
    elif item_type == "headboard":
        sqft = (width_in * height_in) / 144 if width_in and height_in else 1
        yards = YARDAGE_TABLE["headboard_per_sqft"] * max(sqft, 1)
        explanation_parts.append(
            f"Headboard: {YARDAGE_TABLE['headboard_per_sqft']} yd/sqft × {sqft:.1f} sqft = {yards:.1f} yd"
        )

    # ----- Sectional → per-section -----
    elif item_type == "sectional_per_section":
        sections = opts.get("section_count", dims.get("section_count", 1))
        yards = YARDAGE_TABLE["sectional_per_section"] * sections
        explanation_parts.append(
            f"Sectional: {YARDAGE_TABLE['sectional_per_section']} yd/section × {sections} = {yards:.1f} yd"
        )

    # ----- Drapery -----
    elif item_type == "drapery_panel":
        fullness = opts.get("fullness", 2.5)
        total_width_in = width_in * fullness if width_in else FABRIC_WIDTH_INCHES * fullness
        num_widths = math.ceil(total_width_in / FABRIC_WIDTH_INCHES)
        # Height in yards + 18" top/bottom allowances
        cut_length_yd = ((height_in or 96) + 18) / 36
        yards = num_widths * cut_length_yd * YARDAGE_TABLE["drapery_per_width"] / YARDAGE_TABLE["drapery_per_width"]
        # Simplified: widths × cut-length
        yards = num_widths * cut_length_yd
        explanation_parts.append(
            f"Drapery: {fullness}x fullness → {num_widths} widths × {cut_length_yd:.1f} yd cut length = {yards:.1f} yd"
        )

    # ----- Roman shade → sqft -----
    elif item_type == "roman_shade":
        sqft = (width_in * height_in) / 144 if width_in and height_in else 6
        yards = YARDAGE_TABLE["roman_shade_per_sqft"] * sqft
        explanation_parts.append(
            f"Roman shade: {YARDAGE_TABLE['roman_shade_per_sqft']} yd/sqft × {sqft:.1f} sqft = {yards:.1f} yd"
        )

    # ----- Valance → per-linear-ft -----
    elif item_type == "valance":
        yards = YARDAGE_TABLE["valance_per_linear_ft"] * max(linear_ft, 1)
        explanation_parts.append(
            f"Valance: {YARDAGE_TABLE['valance_per_linear_ft']} yd/ft × {linear_ft:.1f} ft = {yards:.1f} yd"
        )

    # ----- Cornice → per-linear-ft -----
    elif item_type == "cornice":
        yards = YARDAGE_TABLE["cornice_per_linear_ft"] * max(linear_ft, 1)
        explanation_parts.append(
            f"Cornice: {YARDAGE_TABLE['cornice_per_linear_ft']} yd/ft × {linear_ft:.1f} ft = {yards:.1f} yd"
        )

    # ----- Roller shade — treat like roman shade -----
    elif item_type == "roller_shade":
        sqft = (width_in * height_in) / 144 if width_in and height_in else 6
        yards = YARDAGE_TABLE.get("roller_shade_per_sqft", 0.25) * sqft
        explanation_parts.append(
            f"Roller shade: 0.25 yd/sqft × {sqft:.1f} sqft = {yards:.1f} yd"
        )

    # ----- Direct lookup items -----
    elif item_type in YARDAGE_TABLE:
        yards = YARDAGE_TABLE[item_type]
        explanation_parts.append(f"{item_type}: base {yards} yd")

    else:
        # Attempt fuzzy match or default
        logger.warning("No yardage entry for '%s'; using 3.0 yd default", item_type)
        yards = 3.0
        explanation_parts.append(f"{item_type}: default 3.0 yd (no table entry)")

    # ----- Cushion count adjustment -----
    cushion_count = opts.get("cushion_count", 0)
    if cushion_count and item_type not in ("seat_cushion", "back_cushion", "throw_pillow"):
        cushion_add = cushion_count * 1.5  # extra per cushion
        yards += cushion_add
        explanation_parts.append(f"+{cushion_add:.1f} yd for {cushion_count} cushions")

    # ----- Tufting adjustment (+15%) -----
    if opts.get("tufted"):
        before = yards
        yards *= 1.15
        explanation_parts.append(f"+15% tufting: {before:.1f} → {yards:.1f} yd")

    # ----- Pattern repeat adjustment (+25%) -----
    pattern_repeat = opts.get("pattern_repeat", 0)
    if pattern_repeat:
        before = yards
        yards *= 1.25
        explanation_parts.append(
            f"+25% pattern repeat ({pattern_repeat}\"): {before:.1f} → {yards:.1f} yd"
        )

    # ----- Round UP to nearest 0.5 yard -----
    raw_yards = yards
    yards = _round_up_half_yard(yards)
    if yards != raw_yards:
        explanation_parts.append(f"Rounded up: {raw_yards:.2f} → {yards} yd")

    calculation = "; ".join(explanation_parts)
    logger.info("Yardage for %s: %.1f yd — %s", item_type, yards, calculation)

    return {"yards": yards, "calculation": calculation}
