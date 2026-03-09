"""
Quote Intelligence System (QIS) — Core Engine

Public API:
    pricing_tables   — master pricing data + lookup helpers
    yardage_calculator — fabric/material yardage calculations
    line_item_builder  — per-item line-item generation
    tier_generator     — A/B/C tier quote generation
    quote_assembler    — full pipeline orchestration
"""

from .line_item_builder import build_line_items
from .pricing_tables import (
    DEPOSIT_PERCENTAGE,
    FABRIC_GRADES,
    HARDWARE,
    INSTALLATION,
    LABOR_RATES,
    LINING,
    TAX_RATES,
    TIER_MULTIPLIERS,
    UPGRADES,
    get_all_tables,
    get_fabric_price,
    get_labor_cost,
    get_upgrade_cost,
    update_table,
)
from .quote_assembler import assemble_quote, recalculate_quote
from .tier_generator import generate_tiers
from .yardage_calculator import YARDAGE_TABLE, calculate_yardage
from .item_analyzer import analyze_photo_items, analyze_photo_items_sync, manual_item
from .mockup_matcher import generate_all_item_mockups, generate_item_mockup
from .verification import (
    QuoteVerifier,
    MARKET_RANGES,
    verify_quote,
    save_verification,
    load_verification,
)

__all__ = [
    # Pricing tables & constants
    "FABRIC_GRADES",
    "LABOR_RATES",
    "UPGRADES",
    "HARDWARE",
    "LINING",
    "INSTALLATION",
    "TAX_RATES",
    "TIER_MULTIPLIERS",
    "DEPOSIT_PERCENTAGE",
    "YARDAGE_TABLE",
    # Pricing helpers
    "get_fabric_price",
    "get_labor_cost",
    "get_upgrade_cost",
    "get_all_tables",
    "update_table",
    # Yardage
    "calculate_yardage",
    # Line items
    "build_line_items",
    # Tiers
    "generate_tiers",
    # Full pipeline
    "assemble_quote",
    "recalculate_quote",
    # Photo analysis
    "analyze_photo_items",
    "analyze_photo_items_sync",
    "manual_item",
    # Mockup generation
    "generate_all_item_mockups",
    "generate_item_mockup",
    # Verification
    "QuoteVerifier",
    "MARKET_RANGES",
    "verify_quote",
    "save_verification",
    "load_verification",
]
