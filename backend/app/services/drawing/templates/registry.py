"""templates/registry.py — product_type → FamilyTemplate lookup.

Phase B1 registry. Maps every Phase-A-spec product_type listed in
MEASUREMENT_REQUIREMENTS (app/data/product_catalog.py) to one of the
6 family templates shipped in B1:

  - DraperyTemplate       (15 styles)
  - RomanTemplate         (9 styles)
  - ValanceTemplate       (14 styles)
  - CorniceTemplate       (5 styles)
  - BenchCurvedTemplate   (bench, banquette — 2 styles)
  - HeadboardChannelTemplate (headboard_channel — 1 style)

All other product_types (cushions, upholstery_wall_panel, dining_chair,
chaise, daybed, settee, sectional, ottoman, plan_table, plan_desk,
murphy_bed, etc.) intentionally raise on lookup — they land in Phase B2
(families 7-12) per the B plan.

The router/printer call `get_template(product_type)` and never deal
with registry internals directly. Adding a B2 family is a one-line
edit here.
"""
from __future__ import annotations

from typing import Optional

from app.services.drawing.templates.base import FamilyTemplate
from app.services.drawing.templates.drapery import DraperyTemplate
from app.services.drawing.templates.roman import RomanTemplate
from app.services.drawing.templates.valance import ValanceTemplate
from app.services.drawing.templates.cornice import CorniceTemplate
from app.services.drawing.templates.bench_curved import BenchCurvedTemplate
from app.services.drawing.templates.headboard_channel import (
    HeadboardChannelTemplate,
)


# Master registry — single source of truth for which product_type
# routes to which family. The order of entries is irrelevant; this is
# read as a dict at lookup time.
_REGISTRY: dict[str, FamilyTemplate] = {
    # ── Drapery (15 styles)
    **{pt: DraperyTemplate() for pt in [
        "pinch_pleat", "french_pleat", "euro_pleat", "cartridge_pleat",
        "box_pleat", "inverted_box_pleat", "goblet_pleat", "butterfly_pleat",
        "ripplefold", "rod_pocket", "tab_top", "grommet", "pencil_pleat",
        "smocked", "fan_pleat",
    ]},
    # ── Roman Shades (9 styles)
    **{pt: RomanTemplate() for pt in [
        "flat_fold", "hobbled_teardrop", "european_relaxed", "balloon",
        "austrian", "london", "cascade", "waterfall", "tulip",
    ]},
    # ── Valance (14 styles)
    **{pt: ValanceTemplate() for pt in [
        "kingston", "cambridge", "scalloped", "arched", "serpentine",
        "flat_board_mounted", "shaped", "pleated", "gathered",
        "swag_and_jabot", "cascades", "empire", "tab", "cornice_with_fabric",
    ]},
    # ── Cornice (5 styles)
    **{pt: CorniceTemplate() for pt in [
        "straight", "double_serpentine", "pagoda", "stepped", "custom_profile",
    ]},
    # ── Bench / Banquette curved (2 styles)
    **{
        "bench": BenchCurvedTemplate(),
        "banquette": BenchCurvedTemplate(),
    },
    # ── Headboard (1 style; Phase B1 — see HeadboardChannelTemplate docs)
    **{
        "headboard_channel": HeadboardChannelTemplate(),
    },
}


def get_template(product_type: str) -> FamilyTemplate:
    """Look up the FamilyTemplate for a product_type. Raises KeyError
    if the type is not yet implemented — the caller (router/printer)
    should catch and surface a 'not implemented' answer to the user."""
    if product_type not in _REGISTRY:
        raise KeyError(
            f"product_type {product_type!r} has no Phase B1 template. "
            f"Implemented types: {sorted(_REGISTRY)}"
        )
    return _REGISTRY[product_type]


def try_get_template(product_type: str) -> Optional[FamilyTemplate]:
    """Convenience wrapper: returns None instead of raising. The router
    can use this to ask 'do you have a template for this style?'"""
    return _REGISTRY.get(product_type)


def implemented_product_types() -> list[str]:
    """Sorted list of every product_type Phase B1 has a template for."""
    return sorted(_REGISTRY)


def family_for(product_type: str) -> str:
    """Return the human-readable family name without instantiating the
    class. Useful for the printer's title-block and for the intake
    route's pre-flight check."""
    tpl = _REGISTRY.get(product_type)
    return tpl.family if tpl else "(unknown)"
