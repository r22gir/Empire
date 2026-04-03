"""
Renderer Registry — maps item types to renderer functions and business units.

Usage:
    from .renderer_registry import get_renderer, get_business_unit, get_title_block
    renderer = get_renderer("bookcase")  # → render_millwork
    unit = get_business_unit("bookcase")  # → "woodcraft"
    title = get_title_block("bookcase")   # → {"company": "EMPIRE WOODCRAFT", ...}
"""

from .drawing_service import (
    render_window, render_cushion, render_headboard,
    render_millwork, render_generic, render_furniture_2view,
)
from .bench_renderer import render_straight as render_bench


def _render_chair(params):
    return render_furniture_2view("chair", params)


def _render_sofa(params):
    return render_furniture_2view("sofa", params)


def _render_ottoman(params):
    return render_furniture_2view("ottoman", params)


def _render_table(params):
    return render_furniture_2view("table", params)


# ── Item type → renderer function ──
RENDERER_MAP: dict[str, callable] = {
    # Upholstery / Soft Furnishings (bench_renderer)
    "bench": render_bench, "banquette": render_bench, "booth": render_bench,
    "sofa": _render_sofa, "couch": _render_sofa, "loveseat": _render_sofa,
    "sectional": _render_sofa, "settee": _render_sofa, "daybed": _render_sofa,
    "chaise": _render_sofa,
    "ottoman": _render_ottoman, "footstool": _render_ottoman, "pouf": _render_ottoman,
    "cushion": render_cushion, "pillow": render_cushion, "bolster": render_cushion,
    "headboard": render_headboard,

    # Window Treatments
    "window": render_window, "shade": render_window, "blind": render_window,
    "curtain": render_window, "drape": render_window, "drapery": render_window,
    "cornice": render_window, "valance": render_window, "roman_shade": render_window,
    "roller_shade": render_window, "shutter": render_window, "sheer": render_window,

    # Seating
    "chair": _render_chair, "stool": _render_chair, "barstool": _render_chair,
    "dining_chair": _render_chair, "accent_chair": _render_chair,
    "armchair": _render_chair, "recliner": _render_chair, "bar_stool": _render_chair,

    # Millwork / Woodwork
    "cabinet": render_millwork, "bookcase": render_millwork, "bookshelf": render_millwork,
    "shelf": render_millwork, "shelving": render_millwork, "built_in": render_millwork,
    "builtin": render_millwork, "entertainment_center": render_millwork,
    "closet": render_millwork, "vanity": render_millwork, "wardrobe": render_millwork,
    "credenza": render_millwork, "hutch": render_millwork, "pantry": render_millwork,
    "mudroom": render_millwork, "desk": render_millwork, "table": _render_table,
}

# ── Item type → business unit ──
_WOODCRAFT_TYPES = frozenset([
    "cabinet", "bookcase", "bookshelf", "shelf", "shelving", "built_in", "builtin",
    "entertainment_center", "closet", "vanity", "wardrobe", "credenza", "hutch",
    "pantry", "mudroom", "desk", "table",
])


def _normalize(item_type: str) -> str:
    return item_type.lower().strip().replace(" ", "_").replace("-", "_")


def get_renderer(item_type: str):
    """Get the appropriate renderer for an item type. Falls back to generic."""
    return RENDERER_MAP.get(_normalize(item_type), render_generic)


def get_business_unit(item_type: str) -> str:
    """Get the business unit for title block branding."""
    return "woodcraft" if _normalize(item_type) in _WOODCRAFT_TYPES else "workroom"


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
