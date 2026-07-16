"""templates — Phase B1 registry package.

Public API:
    from app.services.drawing.templates import get_template
    from app.services.drawing.templates import render_spec

Per Empire Drawing Standard v1.0 every shop drawing must come from
this package. Phase B1 ships 6 families covering ~46 product_types
(listed in `implemented_product_types()`); Phase B2 will add the
remaining 12 (cushions, upholstery wall panels, lounge seating,
dining/bar, ottoman, bedding, table linens).

`render_spec` is the only end-to-end entry point — call it with a
spec dict and you get bytes back (the rendered PDF). It's wired here
in B1 for the B1-checkpoint acceptance; the print pipeline (chain
into MAX + customer-facing flows) lands in Phase D.
"""
from __future__ import annotations

from typing import Optional

from app.services.drawing.templates.base import (
    FamilyTemplate, GeometryFamilyResult, MissingFieldsResult,
    MathLine, GeometryPoint, GeometryEdge, GeometryResult,
)
from app.services.drawing.templates.registry import (
    _REGISTRY,
    get_template, try_get_template,
    implemented_product_types, family_for,
)
from app.services.drawing.templates.printer import (
    render_spec, render_spec_to_bytes,
)


__all__ = [
    "FamilyTemplate",
    "GeometryFamilyResult",
    "MissingFieldsResult",
    "MathLine",
    "GeometryPoint",
    "GeometryEdge",
    "GeometryResult",
    "get_template",
    "try_get_template",
    "implemented_product_types",
    "family_for",
    "render_spec",
    "render_spec_to_bytes",
]
