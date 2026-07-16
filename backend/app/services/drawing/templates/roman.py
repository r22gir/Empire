"""templates/roman.py — Roman Shades family.

Phase B1 — 9 styles: flat_fold, hobbled_teardrop, european_relaxed,
balloon, austrian, london, cascade, waterfall, tulip.

Required: (width, height). Optional: mounting_depth.

Subdivision is HORIZONTAL — the height is divided into slats. For
flat_fold the slats collapse when raised; for hobbled/european they
keep their soft folds and stack accordion-style. Geometry is the same
for all 9 styles; style only affects the front-elevation profile
(which I model by varying the slat spacing in a stylistic ratio).

Math closure (flat_fold 60" wide, 48" tall, 8" slats):

    6 × 8.000" slats = 48.000" — FLUSH BOTH ENDS

Austrian/london add ASSUMED rings every Nth slat — listed in
assumptions() per Rule 1.
"""
from __future__ import annotations

from typing import Dict, List

from app.services.drawing.templates.base import (
    FamilyTemplate, MissingFieldsResult, GeometryResult,
    GeometryPoint, GeometryEdge, MathLine,
)


_ROMAN_STYLES = {
    "flat_fold", "hobbled_teardrop", "european_relaxed", "balloon",
    "austrian", "london", "cascade", "waterfall", "tulip",
}

# Default slat height (inches). Austrian + cascade hang in narrower
# folds; the rest use a flat-ish fold.
_DEFAULT_SLAT_HEIGHTS = {
    "flat_fold": 7.0,
    "hobbled_teardrop": 9.0,
    "european_relaxed": 9.0,
    "balloon": 8.0,
    "austrian": 6.0,
    "london": 7.5,
    "cascade": 6.5,
    "waterfall": 8.0,
    "tulip": 7.0,
}

# Styles with assumed rings every Nth slat (for ASSUMED label).
_RINGED_STYLES = {
    "austrian": 2,    # ring every 2 slats
    "london": 3,
    "cascade": 2,
    "tulip": 3,
}


ROMAN_PRODUCT_TYPES = list(_ROMAN_STYLES)

ROMAN_REQUIRED = ["width", "height"]
ROMAN_OPTIONAL = ["mounting_depth"]


class RomanTemplate(FamilyTemplate):
    family = "Roman Shades"

    product_types = ROMAN_PRODUCT_TYPES

    def validate_spec(self, spec: Dict) -> MissingFieldsResult:
        dims = spec.get("dims", {}) or {}
        product_type = spec.get("product_type")
        if product_type not in _ROMAN_STYLES:
            return MissingFieldsResult(missing_required=["product_type"])
        missing_req = [d for d in ROMAN_REQUIRED
                       if d not in dims or dims[d] is None]
        missing_opt = [d for d in ROMAN_OPTIONAL
                       if d not in dims or dims[d] is None]
        extras = [d for d in dims
                  if d not in (set(ROMAN_REQUIRED + ROMAN_OPTIONAL))]
        return MissingFieldsResult(
            missing_required=missing_req,
            missing_optional=missing_opt,
            extra_dims=extras,
        )

    def assumptions(self, spec: Dict) -> List[str]:
        dims = spec.get("dims", {}) or {}
        product_type = spec.get("product_type", "flat_fold")
        out: List[str] = [
            f"Slat height: ASSUMED {_DEFAULT_SLAT_HEIGHTS.get(product_type, 7):.1f}\" "
            f"per slat for style {product_type}.",
        ]
        if "mounting_depth" not in dims:
            out.append(
                "Mounting depth: ASSUMED 2-1/2\" inside mount — founder must "
                "confirm before fabrication."
            )
        if product_type in _RINGED_STYLES:
            n = _RINGED_STYLES[product_type]
            out.append(
                f"Ring/tassel placement: ASSUMED every {n}nd slat for "
                f"{product_type} style."
            )
        return out

    def geometry(self, spec: Dict) -> GeometryResult:
        dims = spec["dims"]
        width = float(dims["width"])
        height = float(dims["height"])
        product_type = spec.get("product_type", "flat_fold")
        slat = _DEFAULT_SLAT_HEIGHTS[product_type]
        n_slats = max(1, round(height / slat))
        actual_slat = height / n_slats  # snap to evenly spaced
        points: List[GeometryPoint] = []
        edges: List[GeometryEdge] = []
        # Outer frame (4 corners)
        for name, (x, y) in (
            ("TL", (0.0, height)),
            ("TR", (width, height)),
            ("BL", (0.0, 0.0)),
            ("BR", (width, 0.0)),
        ):
            points.append(GeometryPoint(name, x, y, "elevation"))
        edges.append(GeometryEdge("TL", "TR", "elevation"))
        edges.append(GeometryEdge("BL", "BR", "elevation"))
        edges.append(GeometryEdge("TL", "BL", "elevation"))
        edges.append(GeometryEdge("TR", "BR", "elevation"))
        # Horizontal slat seams
        for i in range(1, n_slats):
            y = i * actual_slat
            name = f"slat_{i}"
            points.append(GeometryPoint(f"{name}_L", 0.0, y, "elevation"))
            points.append(GeometryPoint(f"{name}_R", width, y, "elevation"))
            edges.append(GeometryEdge(f"{name}_L", f"{name}_R",
                                       "elevation", weight="channel"))
        # Ring/tassel markers for styles that have them
        if product_type in _RINGED_STYLES:
            ring_every = _RINGED_STYLES[product_type]
            for i in range(1, n_slats, ring_every):
                y = i * actual_slat
                # Symmetric ring pairs (one at 25% width, one at 75%)
                points.append(GeometryPoint(f"ring_{i}_L",
                                             width * 0.25, y, "elevation"))
                points.append(GeometryPoint(f"ring_{i}_R",
                                             width * 0.75, y, "elevation"))
        return GeometryResult(
            points=points,
            edges=edges,
            bbox=(0.0, 0.0, width, height),
            views=["elevation"],
        )

    def layout_math(self, spec: Dict) -> List[MathLine]:
        dims = spec["dims"]
        width = float(dims["width"])
        height = float(dims["height"])
        product_type = spec.get("product_type", "flat_fold")
        slat = _DEFAULT_SLAT_HEIGHTS[product_type]
        n_slats = max(1, round(height / slat))
        actual_slat = height / n_slats
        return [
            MathLine(
                label="Width (single panel; no subdivision)",
                target_in=width,
                segments=[(1, width)],
                gaps=[],
                total=width,
                note="Single panel, Roman shade.",
            ),
            MathLine(
                label="Height closure (slats)",
                target_in=height,
                segments=[(n_slats, actual_slat)],
                gaps=[],
                total=n_slats * actual_slat,
                note=(
                    "FLUSH BOTH ENDS"
                    if abs(n_slats * actual_slat - height) < (1 / 64)
                    else "WARN: closure off > 1/64\" — review slat count"
                ),
            ),
        ]

    def title_block(self, spec: Dict) -> Dict[str, str]:
        dims = spec["dims"]
        product_type = spec.get("product_type", "—")
        slat = _DEFAULT_SLAT_HEIGHTS[product_type]
        n_slats = max(1, round(float(dims["height"]) / slat))
        return {
            "ITEM": product_type.replace("_", " ").title(),
            "DIMENSIONS": f'{dims["width"]:.2f}" W × {dims["height"]:.2f}" H',
            "SLATS": f'{n_slats} @ {dims["height"] / n_slats:.2f}\" each',
            "MOUNTING": (
                f'{dims.get("mounting_depth"):.2f}"' if "mounting_depth" in dims
                else "ASSUMED 2-1/2\" inside mount"
            ),
        }
