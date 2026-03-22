"""
Empire Workroom — Luxury Product Catalog
Complete option trees for drapery, window treatments, upholstery, bedding, and hardware.
Referenced by: Quote Builder, AI Analysis, Pricing Engine, PDF Generator.
"""

from typing import Optional


# ---------------------------------------------------------------------------
# Master Product Catalog
# ---------------------------------------------------------------------------

PRODUCT_CATALOG = {
    # ===================================================================
    # DRAPERY
    # ===================================================================
    "drapery": {
        "label": "Drapery",
        "business": "workroom",
        "subcategories": [
            "pinch_pleat",
            "french_pleat",
            "euro_pleat",
            "cartridge_pleat",
            "box_pleat",
            "inverted_box_pleat",
            "goblet_pleat",
            "butterfly_pleat",
            "ripplefold",
            "rod_pocket",
            "tab_top",
            "grommet",
            "pencil_pleat",
            "smocked",
            "fan_pleat",
        ],
        "options": {
            "pleat_fingers": {
                "label": "Pleat Fingers",
                "applies_to": ["pinch_pleat"],
                "choices": [2, 3, 4],
            },
            "lining": {
                "label": "Lining",
                "choices": [
                    "unlined",
                    "standard_poly_cotton",
                    "blackout",
                    "interlining_bump",
                    "interlining_domette",
                    "interlining_flannel",
                    "thermal",
                    "sheer",
                ],
            },
            "fullness": {
                "label": "Fullness Multiplier",
                "choices": [2.0, 2.5, 3.0, "custom"],
            },
            "hardware": {
                "label": "Hardware / Hanging System",
                "choices": [
                    "traverse_rod",
                    "decorative_rod_wood",
                    "decorative_rod_metal",
                    "decorative_rod_acrylic",
                    "c_rings",
                    "pin_hooks",
                    "ripplefold_track_silent_gliss",
                    "ripplefold_track_kirsch",
                    "ripplefold_track_graber",
                    "motorized_somfy",
                    "motorized_lutron",
                    "motorized_hunter_douglas",
                    "ceiling_mount",
                    "wall_mount",
                    "double_rod",
                    "tension_rod",
                ],
            },
            "finials": {
                "label": "Finials",
                "choices": [
                    "ball",
                    "spear",
                    "fleur_de_lis",
                    "crystal",
                    "urn",
                    "cage",
                    "leaf",
                    "scroll",
                    "square",
                    "custom",
                ],
            },
            "brackets": {
                "label": "Brackets",
                "choices": [
                    "standard",
                    "ceiling",
                    "inside_mount",
                    "outside_mount",
                    "double",
                    "return",
                ],
            },
            "tiebacks": {
                "label": "Tiebacks",
                "choices": [
                    "fabric",
                    "rope",
                    "tassel",
                    "medallion",
                    "magnetic",
                    "holdback",
                ],
            },
            "leading_edge": {
                "label": "Leading Edge Treatment",
                "choices": [
                    "plain",
                    "contrast_banding",
                    "gimp",
                    "braid",
                    "fringe",
                    "tassel_fringe",
                    "beaded",
                    "brush_fringe",
                ],
            },
            "bottom_hem": {
                "label": "Bottom Hem",
                "choices": [
                    "double_fold_4in",
                    "double_fold_6in",
                    "double_fold_8in",
                    "weighted",
                    "chain_weighted",
                    "horsehair",
                ],
            },
            "returns": {
                "label": "Returns",
                "choices": [
                    "standard_3_5in",
                    "extended_6in",
                    "extended_8in",
                    "custom",
                ],
            },
            "stacking": {
                "label": "Stacking Direction",
                "choices": [
                    "left",
                    "right",
                    "split",
                    "one_way_left",
                    "one_way_right",
                ],
            },
        },
    },

    # ===================================================================
    # ROMAN SHADES
    # ===================================================================
    "roman_shades": {
        "label": "Roman Shades",
        "business": "workroom",
        "subcategories": [
            "flat_fold",
            "hobbled_teardrop",
            "european_relaxed",
            "balloon",
            "austrian",
            "london",
            "cascade",
            "waterfall",
            "tulip",
        ],
        "options": {
            "lift_system": {
                "label": "Lift System",
                "choices": [
                    "cord_lock",
                    "continuous_cord_loop",
                    "cordless",
                    "motorized_somfy",
                    "motorized_lutron",
                    "top_down_bottom_up",
                    "day_night_dual",
                ],
            },
            "lining": {
                "label": "Lining",
                "choices": [
                    "unlined",
                    "standard",
                    "blackout",
                    "thermal",
                    "privacy",
                ],
            },
            "mounting": {
                "label": "Mounting",
                "choices": [
                    "inside_mount",
                    "outside_mount",
                    "ceiling_mount",
                ],
            },
            "trim": {
                "label": "Trim",
                "choices": [
                    "contrast_banding",
                    "gimp",
                    "tassel",
                    "bead",
                    "brush_fringe",
                    "ribbon",
                ],
            },
            "valance": {
                "label": "Valance",
                "choices": [
                    "self_valance",
                    "separate_valance",
                    "no_valance",
                ],
            },
        },
    },

    # ===================================================================
    # VALANCES
    # ===================================================================
    "valances": {
        "label": "Valances",
        "business": "workroom",
        "subcategories": [
            "box_pleat",
            "inverted_box_pleat",
            "kingston",
            "cambridge",
            "scalloped",
            "arched",
            "serpentine",
            "balloon",
            "austrian",
            "london",
            "flat_board_mounted",
            "shaped",
            "pleated",
            "gathered",
            "swag_and_jabot",
            "cascades",
            "empire",
            "tab",
            "rod_pocket",
            "cornice_with_fabric",
        ],
        "options": {
            "mounting": {
                "label": "Mounting",
                "choices": [
                    "board_mounted",
                    "rod_mounted",
                    "pole_mounted",
                ],
            },
            "trim": {
                "label": "Trim",
                "choices": [
                    "contrast_banding",
                    "gimp",
                    "braid",
                    "fringe",
                    "tassel_fringe",
                    "beaded",
                    "brush_fringe",
                    "ribbon",
                    "rosettes",
                ],
            },
            "skirt": {
                "label": "Skirt",
                "choices": [
                    "bullion_fringe",
                    "tassel_fringe",
                    "beaded",
                    "butterfly",
                    "knotted",
                ],
            },
        },
    },

    # ===================================================================
    # CORNICES
    # ===================================================================
    "cornices": {
        "label": "Cornices",
        "business": "both",
        "subcategories": [
            "straight",
            "arched",
            "scalloped",
            "serpentine",
            "double_serpentine",
            "pagoda",
            "stepped",
            "custom_profile",
        ],
        "options": {
            "construction": {
                "label": "Construction",
                "choices": [
                    "foam_core",
                    "wood_frame",
                    "padded",
                    "upholstered",
                ],
            },
            "face": {
                "label": "Face Treatment",
                "choices": [
                    "flat_fabric",
                    "tufted",
                    "nailhead_outline",
                    "contrast_welt",
                    "double_welt",
                    "gimp",
                ],
            },
            "dust_cover": {
                "label": "Dust Cover",
                "choices": [
                    "none",
                    "self_fabric",
                    "lining",
                ],
            },
            "returns": {
                "label": "Returns",
                "choices": [
                    "standard",
                    "extended",
                    "custom",
                ],
            },
        },
    },

    # ===================================================================
    # BEDDING
    # ===================================================================
    "bedding": {
        "label": "Bedding",
        "business": "workroom",
        "subcategories": [
            "duvet_cover",
            "coverlet",
            "quilt",
            "bed_skirt",
            "pillow_sham",
            "decorative_pillow",
            "bolster",
            "bed_scarf",
            "fitted_sheet",
            "custom_mattress_cover",
        ],
        "options": {
            "bed_skirt_style": {
                "label": "Bed Skirt Style",
                "applies_to": ["bed_skirt"],
                "choices": [
                    "box_pleat",
                    "kick_pleat",
                    "gathered",
                    "tailored",
                    "split_corner",
                ],
            },
            "sham_size": {
                "label": "Sham Size",
                "applies_to": ["pillow_sham"],
                "choices": [
                    "standard",
                    "euro",
                    "king",
                    "boudoir",
                    "neckroll",
                ],
            },
            "quilting_pattern": {
                "label": "Quilting Pattern",
                "applies_to": ["quilt", "coverlet"],
                "choices": [
                    "diamond",
                    "channel",
                    "vermicelli",
                    "stipple",
                    "custom",
                ],
            },
            "details": {
                "label": "Detail / Embellishment",
                "choices": [
                    "cord_welt",
                    "flange",
                    "ruffle",
                    "monogram",
                    "contrast_lining",
                ],
            },
        },
    },

    # ===================================================================
    # TABLE LINENS
    # ===================================================================
    "table_linens": {
        "label": "Table Linens",
        "business": "workroom",
        "subcategories": [
            "tablecloth_round",
            "tablecloth_oval",
            "tablecloth_rectangular",
            "tablecloth_square",
            "table_runner",
            "placemat",
            "napkin",
            "table_skirt",
            "buffet_cover",
        ],
        "options": {
            "drop_length": {
                "label": "Drop Length (inches)",
                "choices": [8, 10, 15, 20, 30, "floor_length"],
            },
            "corner_style": {
                "label": "Corner Style",
                "choices": [
                    "square",
                    "rounded",
                    "mitered",
                    "inverted",
                ],
            },
            "trim": {
                "label": "Trim",
                "choices": [
                    "contrast_banding",
                    "gimp",
                    "fringe",
                    "tassel",
                    "monogram",
                ],
            },
        },
    },

    # ===================================================================
    # UPHOLSTERY (Furniture + Wall Panels + Cushions)
    # ===================================================================
    "upholstery": {
        "label": "Upholstery",
        "business": "both",
        "subcategories": [
            # Furniture
            "sofa",
            "chair",
            "ottoman",
            "bench",
            "banquette",
            "headboard",
            "dining_chair",
            "bar_stool",
            "chaise",
            "daybed",
            "settee",
            "loveseat",
            "sectional",
            # Wall panels
            "wall_panel_flat",
            "wall_panel_tufted_diamond",
            "wall_panel_tufted_biscuit",
            "wall_panel_channel_vertical",
            "wall_panel_channel_horizontal",
            "wall_panel_padded",
            "wall_panel_wrapped",
            "wall_panel_acoustic",
            "wall_panel_cornice_topped",
            # Cushions
            "cushion_seat",
            "cushion_back",
            "cushion_throw",
            "cushion_bolster",
            "cushion_box_edge",
            "cushion_waterfall",
            "cushion_t_cushion",
            "cushion_bullnose",
            "cushion_knife_edge",
        ],
        "options": {
            "foam_type": {
                "label": "Foam Type",
                "choices": [
                    "high_density",
                    "medium_density",
                    "down_wrap",
                    "down_blend",
                    "spring_down",
                    "memory_foam",
                    "latex",
                ],
            },
            "foam_thickness": {
                "label": "Foam Thickness (inches)",
                "choices": [1, 2, 3, 4, 5, 6],
            },
            "tufting": {
                "label": "Tufting",
                "choices": [
                    "none",
                    "diamond",
                    "biscuit",
                    "channel_vertical",
                    "channel_horizontal",
                    "button",
                    "blind_button",
                    "deep_button",
                ],
            },
            "welting": {
                "label": "Welting",
                "choices": [
                    "self_welt",
                    "contrast_welt",
                    "double_welt",
                    "cord",
                    "micro_welt",
                    "none",
                ],
            },
            "nailhead_finish": {
                "label": "Nailhead Finish",
                "choices": [
                    "none",
                    "standard",
                    "french_natural",
                    "antique_brass",
                    "nickel",
                    "pewter",
                    "black",
                    "gunmetal",
                    "gold",
                ],
            },
            "nailhead_spacing": {
                "label": "Nailhead Spacing",
                "choices": [
                    "standard",
                    "close",
                    "every_other",
                    "custom_pattern",
                ],
            },
            "skirt": {
                "label": "Skirt",
                "choices": [
                    "none",
                    "kick_pleat",
                    "box_pleat",
                    "gathered",
                    "tailored",
                    "bullion_fringe",
                    "waterfall",
                ],
            },
            "springs": {
                "label": "Spring System",
                "choices": [
                    "eight_way_hand_tied",
                    "sinuous_zigzag",
                    "no_sag",
                    "pocket_coil",
                ],
            },
            "arm_style": {
                "label": "Arm Style",
                "choices": [
                    "track",
                    "english",
                    "rolled",
                    "flared",
                    "slope",
                    "pad",
                    "recessed",
                ],
            },
            "back_style": {
                "label": "Back Style",
                "choices": [
                    "tight",
                    "loose_cushion",
                    "tufted",
                    "channeled",
                    "pillow_back",
                ],
            },
            "leg_style": {
                "label": "Leg Style",
                "choices": [
                    "exposed_wood",
                    "exposed_metal",
                    "exposed_acrylic",
                    "skirted",
                    "bun_feet",
                    "turned",
                    "tapered",
                    "cabriole",
                ],
            },
            "wall_panel_mounting": {
                "label": "Wall Panel Mounting",
                "applies_to": [
                    "wall_panel_flat",
                    "wall_panel_tufted_diamond",
                    "wall_panel_tufted_biscuit",
                    "wall_panel_channel_vertical",
                    "wall_panel_channel_horizontal",
                    "wall_panel_padded",
                    "wall_panel_wrapped",
                    "wall_panel_acoustic",
                    "wall_panel_cornice_topped",
                ],
                "choices": [
                    "french_cleat",
                    "z_clip",
                    "velcro",
                    "direct_mount",
                ],
            },
            "wall_panel_foam_thickness": {
                "label": "Wall Panel Foam Thickness (inches)",
                "applies_to": [
                    "wall_panel_flat",
                    "wall_panel_tufted_diamond",
                    "wall_panel_tufted_biscuit",
                    "wall_panel_channel_vertical",
                    "wall_panel_channel_horizontal",
                    "wall_panel_padded",
                    "wall_panel_wrapped",
                    "wall_panel_acoustic",
                    "wall_panel_cornice_topped",
                ],
                "choices": [0.5, 1, 2, 3, 4],
            },
        },
    },

    # ===================================================================
    # HARDWARE
    # ===================================================================
    "hardware": {
        "label": "Hardware & Accessories",
        "business": "both",
        "subcategories": [
            "rod",
            "ring",
            "bracket",
            "finial",
            "holdback",
            "tieback",
            "motorization",
            "batten",
            "weight",
            "chain",
            "cord",
            "carrier",
            "glide",
            "end_stop",
            "support_bracket",
            "splice_plate",
            "extension_bracket",
            "baton_wand",
        ],
        "options": {
            "material": {
                "label": "Material",
                "choices": [
                    "wood",
                    "metal",
                    "acrylic",
                    "iron",
                    "brass",
                    "nickel",
                    "bronze",
                ],
            },
            "finish": {
                "label": "Finish",
                "choices": [
                    "polished",
                    "brushed",
                    "satin",
                    "antique",
                    "oil_rubbed",
                    "matte",
                    "glossy",
                ],
            },
            "fabric_treatment": {
                "label": "Fabric Treatment",
                "choices": [
                    "stain_guard",
                    "fire_retardant",
                    "backing",
                ],
            },
        },
    },
}


# ---------------------------------------------------------------------------
# Furniture Style Variants
# ---------------------------------------------------------------------------

FURNITURE_STYLES = {
    "sofa": [
        "2_cushion",
        "3_cushion",
        "sectional_l",
        "sectional_u",
        "chesterfield",
        "tuxedo",
        "camelback",
        "lawson",
        "english_arm",
        "track_arm",
        "mid_century",
    ],
    "chair": [
        "wingback",
        "club",
        "barrel",
        "accent",
        "slipper",
        "bergere",
        "fauteuil",
        "parsons",
        "dining_side",
        "dining_arm",
    ],
    "bench": [
        "straight",
        "l_shaped",
        "u_shaped_booth",
        "curved_banquette",
        "semicircle",
        "window_seat",
        "storage",
    ],
    "ottoman": [
        "round",
        "square",
        "rectangular",
        "tufted_cube",
        "storage",
    ],
    "headboard": [
        "rectangular",
        "arched",
        "wingback",
        "tufted",
        "camelback",
        "custom_profile",
    ],
    "cushion": [
        "box_edge",
        "knife_edge",
        "t_cushion",
        "bullnose",
        "waterfall",
        "bolster",
        "neckroll",
    ],
    "wall_panel": [
        "flat",
        "diamond_tufted",
        "biscuit_tufted",
        "channel_vertical",
        "channel_horizontal",
        "padded",
        "framed",
    ],
}


# ---------------------------------------------------------------------------
# Drapery / Window Treatment Style Variants
# ---------------------------------------------------------------------------

DRAPERY_STYLES = {
    "drapery": [
        "pinch_pleat",
        "french_pleat",
        "euro_pleat",
        "cartridge_pleat",
        "box_pleat",
        "inverted_box_pleat",
        "goblet_pleat",
        "butterfly_pleat",
        "ripplefold",
        "rod_pocket",
        "tab_top",
        "grommet",
        "pencil_pleat",
        "smocked",
        "fan_pleat",
    ],
    "roman_shade": [
        "flat_fold",
        "hobbled_teardrop",
        "european_relaxed",
        "balloon",
        "austrian",
        "london",
        "cascade",
        "waterfall",
        "tulip",
    ],
    "valance": [
        "box_pleat",
        "inverted_box_pleat",
        "kingston",
        "cambridge",
        "scalloped",
        "arched",
        "serpentine",
        "balloon",
        "austrian",
        "london",
        "flat_board_mounted",
        "shaped",
        "pleated",
        "gathered",
        "swag_and_jabot",
        "cascades",
        "empire",
        "tab",
        "rod_pocket",
        "cornice_with_fabric",
    ],
    "cornice": [
        "straight",
        "arched",
        "scalloped",
        "serpentine",
        "double_serpentine",
        "pagoda",
        "stepped",
        "custom_profile",
    ],
    "sheer": [
        "sheer_2x",
        "sheer_2_5x",
        "sheer_3x",
    ],
}


# ---------------------------------------------------------------------------
# Measurement Requirements by Product Type
# ---------------------------------------------------------------------------

MEASUREMENT_REQUIREMENTS = {
    # --- Drapery ---
    "pinch_pleat":          {"required": ["width", "height"], "optional": ["returns", "stacking"]},
    "french_pleat":         {"required": ["width", "height"], "optional": ["returns", "stacking"]},
    "euro_pleat":           {"required": ["width", "height"], "optional": ["returns", "stacking"]},
    "cartridge_pleat":      {"required": ["width", "height"], "optional": ["returns", "stacking"]},
    "box_pleat":            {"required": ["width", "height"], "optional": ["returns", "stacking"]},
    "inverted_box_pleat":   {"required": ["width", "height"], "optional": ["returns", "stacking"]},
    "goblet_pleat":         {"required": ["width", "height"], "optional": ["returns", "stacking"]},
    "butterfly_pleat":      {"required": ["width", "height"], "optional": ["returns", "stacking"]},
    "ripplefold":           {"required": ["width", "height"], "optional": ["returns", "stacking"]},
    "rod_pocket":           {"required": ["width", "height"], "optional": ["returns", "stacking"]},
    "tab_top":              {"required": ["width", "height"], "optional": ["returns", "stacking"]},
    "grommet":              {"required": ["width", "height"], "optional": ["returns", "stacking"]},
    "pencil_pleat":         {"required": ["width", "height"], "optional": ["returns", "stacking"]},
    "smocked":              {"required": ["width", "height"], "optional": ["returns", "stacking"]},
    "fan_pleat":            {"required": ["width", "height"], "optional": ["returns", "stacking"]},

    # --- Roman Shades ---
    "flat_fold":            {"required": ["width", "height"], "optional": ["mounting_depth"]},
    "hobbled_teardrop":     {"required": ["width", "height"], "optional": ["mounting_depth"]},
    "european_relaxed":     {"required": ["width", "height"], "optional": ["mounting_depth"]},
    "balloon":              {"required": ["width", "height"], "optional": ["mounting_depth"]},
    "austrian":             {"required": ["width", "height"], "optional": ["mounting_depth"]},
    "london":               {"required": ["width", "height"], "optional": ["mounting_depth"]},
    "cascade":              {"required": ["width", "height"], "optional": ["mounting_depth"]},
    "waterfall":            {"required": ["width", "height"], "optional": ["mounting_depth"]},
    "tulip":                {"required": ["width", "height"], "optional": ["mounting_depth"]},

    # --- Valances ---
    "kingston":             {"required": ["width", "drop"], "optional": ["returns"]},
    "cambridge":            {"required": ["width", "drop"], "optional": ["returns"]},
    "scalloped":            {"required": ["width", "drop"], "optional": ["returns"]},
    "arched":               {"required": ["width", "drop"], "optional": ["returns"]},
    "serpentine":           {"required": ["width", "drop"], "optional": ["returns"]},
    "flat_board_mounted":   {"required": ["width", "drop"], "optional": ["returns"]},
    "shaped":               {"required": ["width", "drop"], "optional": ["returns"]},
    "pleated":              {"required": ["width", "drop"], "optional": ["returns"]},
    "gathered":             {"required": ["width", "drop"], "optional": ["returns"]},
    "swag_and_jabot":       {"required": ["width", "drop"], "optional": ["returns"]},
    "cascades":             {"required": ["width", "drop"], "optional": ["returns"]},
    "empire":               {"required": ["width", "drop"], "optional": ["returns"]},
    "tab":                  {"required": ["width", "drop"], "optional": ["returns"]},
    "cornice_with_fabric":  {"required": ["width", "drop"], "optional": ["returns"]},

    # --- Cornices ---
    "straight":             {"required": ["width", "depth", "drop"], "optional": ["returns"]},
    "double_serpentine":    {"required": ["width", "depth", "drop"], "optional": ["returns"]},
    "pagoda":               {"required": ["width", "depth", "drop"], "optional": ["returns"]},
    "stepped":              {"required": ["width", "depth", "drop"], "optional": ["returns"]},
    "custom_profile":       {"required": ["width", "depth", "drop"], "optional": ["returns"]},

    # --- Upholstery: Furniture ---
    "sofa":                 {"required": ["width", "height", "depth"], "optional": ["seat_height", "arm_height"]},
    "chair":                {"required": ["width", "height", "depth"], "optional": ["seat_height", "arm_height"]},
    "ottoman":              {"required": ["width", "depth", "height"], "optional": []},
    "bench":                {"required": ["width", "height", "depth"], "optional": ["seat_height"]},
    "banquette":            {"required": ["width", "height", "depth"], "optional": ["seat_height", "arm_height"]},
    "headboard":            {"required": ["width", "height"], "optional": ["thickness"]},
    "dining_chair":         {"required": ["width", "height", "depth"], "optional": ["seat_height"]},
    "bar_stool":            {"required": ["width", "height", "depth"], "optional": ["seat_height", "footrest_height"]},
    "chaise":               {"required": ["width", "height", "depth"], "optional": ["seat_height", "arm_height"]},
    "daybed":               {"required": ["width", "height", "depth"], "optional": ["seat_height"]},
    "settee":               {"required": ["width", "height", "depth"], "optional": ["seat_height", "arm_height"]},
    "loveseat":             {"required": ["width", "height", "depth"], "optional": ["seat_height", "arm_height"]},
    "sectional":            {"required": ["width", "height", "depth"], "optional": ["seat_height", "arm_height", "configuration"]},

    # --- Upholstery: Wall Panels ---
    "wall_panel_flat":                  {"required": ["width", "height"], "optional": ["quantity"]},
    "wall_panel_tufted_diamond":        {"required": ["width", "height"], "optional": ["quantity"]},
    "wall_panel_tufted_biscuit":        {"required": ["width", "height"], "optional": ["quantity"]},
    "wall_panel_channel_vertical":      {"required": ["width", "height"], "optional": ["quantity"]},
    "wall_panel_channel_horizontal":    {"required": ["width", "height"], "optional": ["quantity"]},
    "wall_panel_padded":                {"required": ["width", "height"], "optional": ["quantity"]},
    "wall_panel_wrapped":               {"required": ["width", "height"], "optional": ["quantity"]},
    "wall_panel_acoustic":              {"required": ["width", "height"], "optional": ["quantity"]},
    "wall_panel_cornice_topped":        {"required": ["width", "height"], "optional": ["quantity"]},

    # --- Upholstery: Cushions ---
    "cushion_seat":         {"required": ["width", "depth", "thickness"], "optional": []},
    "cushion_back":         {"required": ["width", "height", "thickness"], "optional": []},
    "cushion_throw":        {"required": ["width", "depth", "thickness"], "optional": []},
    "cushion_bolster":      {"required": ["diameter", "length"], "optional": []},
    "cushion_box_edge":     {"required": ["width", "depth", "thickness"], "optional": []},
    "cushion_waterfall":    {"required": ["width", "depth", "thickness"], "optional": []},
    "cushion_t_cushion":    {"required": ["width", "depth", "thickness"], "optional": []},
    "cushion_bullnose":     {"required": ["width", "depth", "thickness"], "optional": []},
    "cushion_knife_edge":   {"required": ["width", "depth", "thickness"], "optional": []},

    # --- Bedding ---
    "duvet_cover":          {"required": ["bed_size"], "optional": ["width", "length"]},
    "coverlet":             {"required": ["bed_size"], "optional": ["width", "length"]},
    "quilt":                {"required": ["bed_size"], "optional": ["width", "length"]},
    "bed_skirt":            {"required": ["bed_size", "drop"], "optional": ["split_corners"]},
    "pillow_sham":          {"required": ["sham_size"], "optional": ["width", "height"]},
    "decorative_pillow":    {"required": ["width", "height"], "optional": []},
    "bolster":              {"required": ["diameter", "length"], "optional": []},
    "bed_scarf":            {"required": ["bed_size"], "optional": ["width", "length"]},
    "fitted_sheet":         {"required": ["bed_size"], "optional": ["mattress_depth"]},
    "custom_mattress_cover": {"required": ["width", "length", "mattress_depth"], "optional": []},

    # --- Table Linens ---
    "tablecloth_round":         {"required": ["table_diameter", "drop_length"], "optional": []},
    "tablecloth_oval":          {"required": ["table_width", "table_length", "drop_length"], "optional": []},
    "tablecloth_rectangular":   {"required": ["table_width", "table_length", "drop_length"], "optional": []},
    "tablecloth_square":        {"required": ["table_width", "drop_length"], "optional": []},
    "table_runner":             {"required": ["width", "length"], "optional": ["overhang"]},
    "placemat":                 {"required": ["width", "length"], "optional": []},
    "napkin":                   {"required": ["size"], "optional": []},
    "table_skirt":              {"required": ["table_width", "table_length", "drop_length"], "optional": []},
    "buffet_cover":             {"required": ["table_width", "table_length", "drop_length"], "optional": []},

    # --- Hardware ---
    "rod":                  {"required": ["length"], "optional": ["diameter"]},
    "ring":                 {"required": ["diameter"], "optional": ["quantity"]},
    "bracket":              {"required": ["projection"], "optional": ["quantity"]},
    "finial":               {"required": ["rod_diameter"], "optional": []},
    "holdback":             {"required": ["projection"], "optional": []},
    "tieback":              {"required": ["length"], "optional": []},
    "motorization":         {"required": ["track_length"], "optional": ["power_source"]},
    "batten":               {"required": ["width"], "optional": ["quantity"]},
    "weight":               {"required": ["length"], "optional": []},
    "chain":                {"required": ["length"], "optional": []},
    "cord":                 {"required": ["length"], "optional": []},
    "carrier":              {"required": [], "optional": ["quantity"]},
    "glide":                {"required": [], "optional": ["quantity"]},
    "end_stop":             {"required": [], "optional": ["quantity"]},
    "support_bracket":      {"required": ["projection"], "optional": ["quantity"]},
    "splice_plate":         {"required": [], "optional": ["quantity"]},
    "extension_bracket":    {"required": ["projection"], "optional": ["quantity"]},
    "baton_wand":           {"required": ["length"], "optional": []},
}


# ---------------------------------------------------------------------------
# Internal Lookup Index  (built once at import time)
# ---------------------------------------------------------------------------

_TYPE_TO_CATEGORY: dict[str, str] = {}
for _cat_slug, _cat_data in PRODUCT_CATALOG.items():
    for _sub in _cat_data["subcategories"]:
        _TYPE_TO_CATEGORY[_sub] = _cat_slug


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def get_category(product_type: str) -> Optional[str]:
    """Return the top-level category slug for a given product type.

    >>> get_category("pinch_pleat")
    'drapery'
    >>> get_category("wall_panel_flat")
    'upholstery'
    """
    return _TYPE_TO_CATEGORY.get(product_type)


def get_options(product_type: str) -> dict:
    """Return the full options dict available for *product_type*.

    Options that carry an ``applies_to`` list are only included when
    *product_type* appears in that list (or when ``applies_to`` is absent,
    meaning the option is universal within the category).
    """
    category = get_category(product_type)
    if category is None:
        return {}
    all_opts = PRODUCT_CATALOG[category].get("options", {})
    filtered: dict = {}
    for key, opt in all_opts.items():
        applies = opt.get("applies_to")
        if applies is None or product_type in applies:
            filtered[key] = opt
    return filtered


def get_all_types(category: Optional[str] = None, business: Optional[str] = None) -> list[str]:
    """Return every product type, optionally filtered by category and/or business.

    Parameters
    ----------
    category : str, optional
        Limit to a single category slug (e.g. ``"drapery"``).
    business : str, optional
        ``"workroom"``, ``"woodcraft"``, or ``"both"``.  When ``"both"`` is
        given, categories whose business is ``"both"`` *and* those matching
        either single value are included.
    """
    types: list[str] = []
    for cat_slug, cat_data in PRODUCT_CATALOG.items():
        if category and cat_slug != category:
            continue
        if business:
            cat_biz = cat_data["business"]
            if business == "both":
                pass  # include everything
            elif cat_biz != business and cat_biz != "both":
                continue
        types.extend(cat_data["subcategories"])
    return types


def get_measurement_requirements(product_type: str) -> dict:
    """Return the measurement specification for *product_type*.

    Returns a dict with ``required`` and ``optional`` lists, or an empty
    dict if the type is unknown.

    >>> get_measurement_requirements("sofa")
    {'required': ['width', 'height', 'depth'], 'optional': ['seat_height', 'arm_height']}
    """
    return MEASUREMENT_REQUIREMENTS.get(product_type, {})
