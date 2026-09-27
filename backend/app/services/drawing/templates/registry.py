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


def get_template(product_type: str, family: str | None = None) -> FamilyTemplate:
    """Look up the FamilyTemplate for a product_type.

    A bare slug uses the flat B1 registry (historical winner when the
    slug is shared). Pass `family`, or a `family/style` catalog id, to
    hit the catalog family — that is how valance `box_pleat` and cornice
    `arched` stay off the drapery and valance sheets.

    Vision aliases (`flat_roman`, `arched_cornice`, `pinch-pleat`,
    `headboard`) resolve through the same catalog namespace.

    Raises KeyError if the type is not yet implemented — the caller
    (router/printer) should catch and surface a 'not implemented' answer.
    """
    namespaced = bool(family and str(family).strip()) or (
        isinstance(product_type, str) and "/" in product_type
    )
    if namespaced or product_type not in _REGISTRY:
        from app.services.drawing.templates.catalog_namespace import (
            resolve_catalog_style,
            template_instance,
        )
        try:
            resolved = resolve_catalog_style(product_type, family=family)
        except KeyError:
            if namespaced:
                raise
            raise KeyError(
                f"product_type {product_type!r} has no Phase B1 template. "
                f"Implemented types: {sorted(_REGISTRY)}"
            ) from None
        return template_instance(resolved)
    return _REGISTRY[product_type]


def try_get_template(
    product_type: str, family: str | None = None,
) -> Optional[FamilyTemplate]:
    """Convenience wrapper: returns None instead of raising. The router
    can use this to ask 'do you have a template for this style?'"""
    try:
        return get_template(product_type, family=family)
    except KeyError:
        return None


def implemented_product_types() -> list[str]:
    """Sorted list of every product_type Phase B1 has a template for."""
    return sorted(_REGISTRY)


def family_for(product_type: str, family: str | None = None) -> str:
    """Return the human-readable family name without instantiating the
    class. Useful for the printer's title-block and for the intake
    route's pre-flight check.

    Bare slugs use the flat registry. `family` or a `family/style` id
    uses the catalog namespace so a shared slug reports the family the
    caller named.
    """
    namespaced = bool(family and str(family).strip()) or (
        isinstance(product_type, str) and "/" in product_type
    )
    if namespaced or product_type not in _REGISTRY:
        from app.services.drawing.templates.catalog_namespace import (
            resolve_catalog_style,
        )
        try:
            return resolve_catalog_style(
                product_type, family=family,
            ).template_family
        except KeyError:
            if not namespaced and product_type in _REGISTRY:
                return _REGISTRY[product_type].family
            return "(unknown)"
    tpl = _REGISTRY.get(product_type)
    return tpl.family if tpl else "(unknown)"
