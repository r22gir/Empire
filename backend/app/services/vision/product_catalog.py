"""
Empire Drawing Studio — Complete Product Catalog.

DATA file containing all 150+ product styles organized by category.
This is NOT a renderer — it provides metadata used by renderer_registry,
title blocks, the drawing API, and MAX desk routing.

Each category includes:
    styles         — list of style slugs the system recognizes
    modes          — drawing modes available (presentation / shop / construction)
    business_unit  — "workroom" (Empire Workroom) or "woodcraft" (Empire WoodCraft)
    default_dims   — optional default dimensions in inches {width, depth, height}
    views          — optional list of standard views for this category
"""

PRODUCT_CATALOG = {
    # ── UPHOLSTERY / SOFT FURNISHINGS (Empire Workroom) ───────────
    "sofa": {
        "styles": [
            "lawson", "tuxedo", "chesterfield", "roll_arm", "camelback",
            "english_arm", "bridgewater", "track_arm", "slope_arm",
            "cabriole", "italian_modern", "armless", "sectional", "daybed",
            "sleeper", "settee", "chaise_section",
        ],
        "modes": ["presentation", "shop"],
        "business_unit": "workroom",
        "default_dims": {"width": 84, "depth": 36, "height": 34},
        "views": ["front", "side", "plan"],
    },
    "chair": {
        "styles": [
            "wingback", "club", "barrel", "slipper", "bergere",
            "chesterfield", "midcentury", "oversized", "occasional", "egg",
            "chaise_lounge", "dining", "lounge", "parsons", "swivel",
            "rocking", "desk_chair",
        ],
        "modes": ["presentation", "shop"],
        "business_unit": "workroom",
        "default_dims": {"width": 32, "depth": 34, "height": 36},
        "views": ["front", "side"],
    },
    "ottoman": {
        "styles": [
            "rectangular", "square", "round", "storage", "cocktail",
            "tufted", "cube", "x_bench", "pouf", "bench_ottoman",
        ],
        "modes": ["presentation", "shop"],
        "business_unit": "workroom",
        "default_dims": {"width": 24, "depth": 24, "height": 18},
        "views": ["front", "plan"],
    },
    "headboard": {
        "styles": [
            "straight", "arched", "wingback", "channel_tufted",
            "diamond_tufted", "biscuit_tufted", "panel", "slipcover",
            "full_bed_frame", "canopy", "floating",
        ],
        "modes": ["presentation", "shop"],
        "business_unit": "workroom",
        "default_dims": {"width": 62, "depth": 4, "height": 56},
        "views": ["front"],
    },
    "cushion": {
        "styles": [
            "box", "knife_edge", "bullnose", "t_cushion", "button_tufted",
            "channel", "bolster", "wedge", "window_seat", "outdoor",
            "bench_pad", "foam_topper",
        ],
        "modes": ["presentation", "shop"],
        "business_unit": "workroom",
        "default_dims": {"width": 24, "depth": 24, "height": 4},
        "views": ["plan"],
    },
    "pillow": {
        "styles": [
            "square", "lumbar", "euro_sham", "bolster", "neck_roll",
            "round", "floor", "outdoor",
        ],
        "modes": ["presentation"],
        "business_unit": "workroom",
        "default_dims": {"width": 20, "depth": 20, "height": 6},
        "views": ["front"],
    },
    "window": {
        "styles": [
            # Drapery styles
            "pinch_pleat", "french_pleat", "euro_pleat", "goblet",
            "ripplefold", "grommet", "rod_pocket", "tab_top",
            "inverted_box", "cartridge", "pencil", "smocked",
            # Roman shades
            "flat_roman", "hobbled_roman", "balloon_roman", "austrian",
            "relaxed_roman", "london_roman", "tulip_roman",
            # Cornices & valances
            "straight_cornice", "arched_cornice", "scalloped_cornice",
            "shaped_cornice", "upholstered_cornice",
            "swag_jabot", "balloon_valance", "box_pleat_valance",
            "kingston_valance", "rod_pocket_valance",
            "board_mounted_valance", "scarf_swag",
        ],
        "modes": ["presentation", "shop"],
        "business_unit": "workroom",
        "default_dims": {"width": 72, "depth": 6, "height": 96},
        "views": ["front"],
    },
    "bedding": {
        "styles": [
            "duvet", "coverlet", "bedskirt", "shams", "bed_runner",
            "bed_scarf", "pillow_stack",
        ],
        "modes": ["presentation"],
        "business_unit": "workroom",
        "default_dims": {"width": 90, "depth": 80, "height": 18},
        "views": ["front", "plan"],
    },
    "slipcover": {
        "styles": [
            "tight_fit", "relaxed_fit", "loose_fit", "dining_cover",
            "outdoor_cover",
        ],
        "modes": ["presentation"],
        "business_unit": "workroom",
        "default_dims": {"width": 36, "depth": 34, "height": 34},
        "views": ["front", "side"],
    },
    "wall_panel": {
        "styles": [
            "fabric", "padded", "channel", "tufted", "acoustic",
            "ceiling", "niche",
        ],
        "modes": ["presentation", "shop"],
        "business_unit": "workroom",
        "default_dims": {"width": 48, "depth": 2, "height": 96},
        "views": ["front"],
    },

    # ── WOODWORK / CNC (Empire WoodCraft) ─────────────────────────
    "banquette": {
        "styles": [
            "straight", "l_shape", "u_shape", "curved", "booth",
            "single_booth", "high_back", "modular", "storage", "outdoor",
        ],
        "modes": ["presentation", "shop", "construction"],
        "business_unit": "woodcraft",
        "default_dims": {"width": 120, "depth": 20, "height": 34},
        "views": ["plan", "front", "isometric"],
    },
    "shelving": {
        "styles": [
            "floating", "built_in", "open", "closed_cabinet", "ladder",
            "corner", "display_case", "modular_cube",
            "entertainment_center", "plate_rail",
        ],
        "modes": ["presentation", "shop", "construction"],
        "business_unit": "woodcraft",
        "default_dims": {"width": 48, "depth": 12, "height": 84},
        "views": ["front", "side", "plan"],
    },
    "murphy_bed": {
        "styles": [
            "vertical", "horizontal", "side_cabinets", "with_desk",
            "with_sofa", "cabinet_bed", "bunk_wall", "with_bookcase",
        ],
        "modes": ["presentation", "shop", "construction"],
        "business_unit": "woodcraft",
        "default_dims": {"width": 64, "depth": 18, "height": 86},
        "views": ["front", "side", "plan"],
    },
    "desk": {
        "styles": [
            "writing", "executive", "standing", "built_in", "secretary",
            "corner", "floating", "reception", "craft_sewing", "vanity",
        ],
        "modes": ["presentation", "shop", "construction"],
        "business_unit": "woodcraft",
        "default_dims": {"width": 60, "depth": 30, "height": 30},
        "views": ["front", "side", "plan"],
    },
    "storage_bench": {
        "styles": [
            "hinged_top", "drawer", "cubby", "hall_tree", "window_seat",
            "trunk", "shoe_bench", "banquette_storage",
        ],
        "modes": ["presentation", "shop", "construction"],
        "business_unit": "woodcraft",
        "default_dims": {"width": 48, "depth": 18, "height": 18},
        "views": ["front", "side", "plan"],
    },
    "table": {
        "styles": [
            "dining", "extension", "coffee", "side_end", "console",
            "nesting", "bar_pub", "kitchen_island", "nightstand",
            "pedestal", "trestle", "parsons",
        ],
        "modes": ["presentation", "shop", "construction"],
        "business_unit": "woodcraft",
        "default_dims": {"width": 72, "depth": 36, "height": 30},
        "views": ["front", "side", "plan"],
    },
    "millwork": {
        "styles": [
            "crown_molding", "base_molding", "chair_rail", "wainscoting",
            "coffered_ceiling", "built_in_cabinetry", "fireplace_surround",
            "stair_parts", "door_window_casing", "paneled_wall",
            "plate_rail", "ceiling_beams",
        ],
        "modes": ["presentation", "shop", "construction"],
        "business_unit": "woodcraft",
        "default_dims": {"width": 96, "depth": 6, "height": 96},
        "views": ["front", "side", "plan"],
    },
    "commercial": {
        "styles": [
            "restaurant_booth", "bar_front", "hostess_stand",
            "hotel_headboard_wall", "lobby_seating", "theater_seating",
            "retail_fixtures", "reception_counter", "server_station",
        ],
        "modes": ["presentation", "shop", "construction"],
        "business_unit": "woodcraft",
        "default_dims": {"width": 72, "depth": 30, "height": 42},
        "views": ["front", "side", "plan"],
    },
}


# ── ACCESSOR FUNCTIONS ────────────────────────────────────────────

def get_styles(item_type: str) -> list[str]:
    """Return the list of recognized style slugs for an item type."""
    return PRODUCT_CATALOG.get(item_type, {}).get("styles", [])


def get_modes(item_type: str) -> list[str]:
    """Return available drawing modes for an item type."""
    return PRODUCT_CATALOG.get(item_type, {}).get("modes", ["presentation"])


def get_business_unit(item_type: str) -> str:
    """Return 'workroom' or 'woodcraft' for an item type."""
    return PRODUCT_CATALOG.get(item_type, {}).get("business_unit", "workroom")


def get_default_dims(item_type: str) -> dict:
    """Return default dimensions dict for an item type."""
    return PRODUCT_CATALOG.get(item_type, {}).get("default_dims", {})


def get_views(item_type: str) -> list[str]:
    """Return standard views list for an item type."""
    return PRODUCT_CATALOG.get(item_type, {}).get("views", ["front"])


def get_all_types() -> list[str]:
    """Return all registered item type keys."""
    return list(PRODUCT_CATALOG.keys())


def get_total_styles() -> int:
    """Return the total count of styles across all categories."""
    return sum(len(v["styles"]) for v in PRODUCT_CATALOG.values())


def find_type_for_style(style: str) -> str:
    """Given a style slug, find which item type it belongs to.

    Returns the item type key, or 'generic' if not found.
    """
    style = style.lower().strip().replace(" ", "_").replace("-", "_")
    for item_type, config in PRODUCT_CATALOG.items():
        if style in config["styles"]:
            return item_type
    return "generic"
