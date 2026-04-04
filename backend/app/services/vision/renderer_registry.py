"""
Renderer Registry — maps ALL product styles and item types to renderer functions.

Imports the full product catalog and builds a comprehensive RENDERER_MAP so every
recognized style string resolves to a working renderer. Categories without their
own dedicated renderer fall back to the closest match:

    sofa / chair / ottoman / slipcover → render_furniture_2view
    window (all 31 styles)             → render_window
    cushion / pillow                   → render_cushion
    headboard                          → render_headboard
    banquette (straight/L/U)           → bench_renderer
    millwork / shelving / murphy_bed / desk / storage_bench / commercial
                                       → render_millwork
    table                              → render_furniture_2view("table")
    bedding / wall_panel               → render_generic
    everything else                    → render_generic

Usage:
    from .renderer_registry import get_renderer, get_business_unit, get_title_block
    renderer = get_renderer("chesterfield")  # → sofa renderer
    unit = get_business_unit("banquette")     # → "woodcraft"
"""

from .drawing_service import (
    render_window, render_cushion, render_headboard,
    render_millwork, render_generic, render_furniture_2view,
)
from .bench_renderer import (
    render_straight as _render_bench_straight,
    render_l_shape as _render_bench_l,
    render_u_shape as _render_bench_u,
)
from .product_catalog import (
    PRODUCT_CATALOG, get_business_unit as _catalog_business_unit,
    get_styles, get_all_types, get_total_styles, find_type_for_style,
)


# ── Wrapper functions for render_furniture_2view ──────────────────

def _render_chair(params):
    return render_furniture_2view("chair", params)

def _render_sofa(params):
    return render_furniture_2view("sofa", params)

def _render_ottoman(params):
    return render_furniture_2view("ottoman", params)

def _render_table(params):
    return render_furniture_2view("table", params)

def _render_slipcover(params):
    return render_furniture_2view("chair", params)

def _render_bedding(params):
    return render_generic(params)

def _render_wall_panel(params):
    return render_generic(params)

def _render_commercial(params):
    return render_millwork(params)


# ── Category → renderer function mapping ──────────────────────────
# Each item_type from the catalog maps to its best available renderer.

_CATEGORY_RENDERER = {
    "sofa": _render_sofa,
    "chair": _render_chair,
    "ottoman": _render_ottoman,
    "headboard": render_headboard,
    "cushion": render_cushion,
    "pillow": render_cushion,
    "window": render_window,
    "bedding": _render_bedding,
    "slipcover": _render_slipcover,
    "wall_panel": _render_wall_panel,
    "banquette": _render_bench_straight,   # default; L/U resolved by style
    "shelving": render_millwork,
    "murphy_bed": render_millwork,
    "desk": render_millwork,
    "storage_bench": render_millwork,
    "table": _render_table,
    "millwork": render_millwork,
    "commercial": _render_commercial,
}

# ── Special banquette style overrides ─────────────────────────────
_BANQUETTE_STYLE_MAP = {
    "l_shape": _render_bench_l,
    "u_shape": _render_bench_u,
}


# ── Build the comprehensive RENDERER_MAP ──────────────────────────
# Every style slug from the product catalog gets its own entry.

RENDERER_MAP: dict[str, callable] = {}

for _cat, _config in PRODUCT_CATALOG.items():
    # Map the category name itself
    base_renderer = _CATEGORY_RENDERER.get(_cat, render_generic)
    RENDERER_MAP[_cat] = base_renderer

    # Map every style within the category
    for _style in _config.get("styles", []):
        if _cat == "banquette" and _style in _BANQUETTE_STYLE_MAP:
            RENDERER_MAP[_style] = _BANQUETTE_STYLE_MAP[_style]
        else:
            RENDERER_MAP[_style] = base_renderer

# ── Legacy / alias entries (backward compat with old item_type strings) ──
_ALIASES = {
    # Sofa aliases
    "couch": _render_sofa, "loveseat": _render_sofa, "chaise": _render_sofa,
    # Chair aliases
    "stool": _render_chair, "barstool": _render_chair, "bar_stool": _render_chair,
    "dining_chair": _render_chair, "accent_chair": _render_chair,
    "armchair": _render_chair, "recliner": _render_chair, "arm_chair": _render_chair,
    # Ottoman aliases
    "footstool": _render_ottoman,
    # Cushion aliases
    "seat_pad": render_cushion, "throw_pillow": render_cushion,
    # Window aliases
    "shade": render_window, "blind": render_window, "curtain": render_window,
    "drape": render_window, "drapery": render_window, "cornice": render_window,
    "valance": render_window, "roman_shade": render_window,
    "roller_shade": render_window, "shutter": render_window, "sheer": render_window,
    # Bench/banquette aliases
    "bench": _render_bench_straight, "booth": _render_bench_straight,
    # Millwork aliases
    "cabinet": render_millwork, "bookcase": render_millwork,
    "bookshelf": render_millwork, "shelf": render_millwork,
    "built_in": render_millwork, "builtin": render_millwork,
    "entertainment_center": render_millwork, "closet": render_millwork,
    "vanity": render_millwork, "wardrobe": render_millwork,
    "credenza": render_millwork, "hutch": render_millwork,
    "pantry": render_millwork, "mudroom": render_millwork,
}

# Merge aliases (don't overwrite catalog entries)
for _alias, _fn in _ALIASES.items():
    if _alias not in RENDERER_MAP:
        RENDERER_MAP[_alias] = _fn


# ── Public API ────────────────────────────────────────────────────

def _normalize(item_type: str) -> str:
    """Normalize item type / style string for lookup."""
    return item_type.lower().strip().replace(" ", "_").replace("-", "_")


def get_renderer(item_type: str):
    """Get the appropriate renderer for an item type or style. Falls back to generic."""
    return RENDERER_MAP.get(_normalize(item_type), render_generic)


def get_business_unit(item_type: str) -> str:
    """Get the business unit for title block branding.

    Checks the product catalog first, then falls back to the legacy woodcraft set.
    """
    norm = _normalize(item_type)
    # Check catalog directly
    unit = _catalog_business_unit(norm)
    if unit != "workroom" or norm in PRODUCT_CATALOG:
        return unit
    # Check if it's a style that belongs to a woodcraft category
    cat = find_type_for_style(norm)
    if cat != "generic":
        return _catalog_business_unit(cat)
    # Legacy fallback
    if norm in _LEGACY_WOODCRAFT_TYPES:
        return "woodcraft"
    return "workroom"


# Legacy set preserved for aliases not in the catalog
_LEGACY_WOODCRAFT_TYPES = frozenset([
    "cabinet", "bookcase", "bookshelf", "shelf", "shelving", "built_in", "builtin",
    "entertainment_center", "closet", "vanity", "wardrobe", "credenza", "hutch",
    "pantry", "mudroom", "desk", "table",
])


def get_title_block(item_type: str) -> dict:
    """Get title block info based on business unit."""
    if get_business_unit(item_type) == "woodcraft":
        return {
            "company": "EMPIRE WOODCRAFT",
            "tagline": "Custom Woodwork &amp; CNC Fabrication",
            "address": "5124 Frolich Ln, Hyattsville, MD 20781",
            "contact": "(703) 213-6484 | woodcraft@empirebox.store",
        }
    return {
        "company": "EMPIRE WORKROOM",
        "tagline": "Custom Upholstery &amp; Window Treatments",
        "address": "5124 Frolich Ln, Hyattsville, MD 20781",
        "contact": "(703) 213-6484 | workroom@empirebox.store",
    }


def get_supported_styles(item_type: str) -> list[str]:
    """Return all recognized style slugs for a given item type.

    Delegates to the product catalog.
    """
    return get_styles(_normalize(item_type))


def get_all_renderable_types() -> list[str]:
    """Return every key in the RENDERER_MAP (item types + styles + aliases)."""
    return sorted(RENDERER_MAP.keys())


def get_catalog_types() -> list[str]:
    """Return just the top-level category names from the product catalog."""
    return get_all_types()


def get_renderer_stats() -> dict:
    """Summary stats for diagnostics."""
    return {
        "catalog_categories": len(PRODUCT_CATALOG),
        "total_styles": get_total_styles(),
        "renderer_map_entries": len(RENDERER_MAP),
        "renderable_types": sorted(RENDERER_MAP.keys()),
    }
