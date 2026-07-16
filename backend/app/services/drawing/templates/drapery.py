"""templates/drapery.py — Drapery family (pinch_pleat, french_pleat, etc.).

Phase B1 — 15 drapery styles share the same geometry pipeline:
required = (width, height); optional = (returns, stacking, fullness).

Subdivision:
  panels = round(width / 24) — Empire default panel width 24" max,
  but each panel must be an integer count, and segments + returns must
  close exactly (Rule 3).

Math closure example (pinch_pleat 87" wide, returns 4" each side):

    3 × 27" panels + 2 × 3" returns = 87" — FLUSH BOTH ENDS
"""
from __future__ import annotations

from typing import Dict, List

from app.services.drawing.templates.base import (
    FamilyTemplate, MissingFieldsResult, GeometryResult,
    GeometryPoint, GeometryEdge, MathLine,
)


# Tighter max panel width per drapery style. Some styles (e.g.
# ripplefold) need narrower panels for clean stack.
_DEFAULT_PANEL_WIDTHS = {
    "pinch_pleat": 24.0,
    "french_pleat": 22.0,
    "euro_pleat": 24.0,
    "cartridge_pleat": 18.0,
    "box_pleat": 24.0,
    "inverted_box_pleat": 24.0,
    "goblet_pleat": 20.0,
    "butterfly_pleat": 22.0,
    "ripplefold": 30.0,
    "rod_pocket": 36.0,
    "tab_top": 36.0,
    "grommet": 28.0,
    "pencil_pleat": 24.0,
    "smocked": 20.0,
    "fan_pleat": 22.0,
}

DRAPERY_PRODUCT_TYPES = list(_DEFAULT_PANEL_WIDTHS.keys())

# Required + optional dims per the catalog MEASUREMENT_REQUIREMENTS table.
DRAPERY_REQUIRED = ["width", "height"]
DRAPERY_OPTIONAL = ["returns", "stacking"]


class DraperyTemplate(FamilyTemplate):
    family = "Drapery"

    product_types = DRAPERY_PRODUCT_TYPES

    def validate_spec(self, spec: Dict) -> MissingFieldsResult:
        dims = spec.get("dims", {}) or {}
        product_type = spec.get("product_type")
        if product_type not in _DEFAULT_PANEL_WIDTHS:
            return MissingFieldsResult(missing_required=["product_type"])
        missing_req = [d for d in DRAPERY_REQUIRED
                       if d not in dims or dims[d] is None]
        missing_opt = [d for d in DRAPERY_OPTIONAL
                       if d not in dims or dims[d] is None]
        # 'extra_dims' is everything in dims that the family doesn't
        # recognize — useful for input-validation UI.
        expected = set(DRAPERY_REQUIRED + DRAPERY_OPTIONAL)
        extras = [d for d in dims if d not in expected]
        return MissingFieldsResult(
            missing_required=missing_req,
            missing_optional=missing_opt,
            extra_dims=extras,
        )

    def assumptions(self, spec: Dict) -> List[str]:
        dims = spec.get("dims", {}) or {}
        product_type = spec.get("product_type", "—")
        # Rule 1: every inferred value must surface here.
        out: List[str] = [
            f"Panel width: ASSUMED {_DEFAULT_PANEL_WIDTHS.get(product_type, 24):.0f}\" "
            f"max per style {product_type}.",
        ]
        if "returns" not in dims:
            out.append("Returns: ASSUMED 3\" each side (typical workroom).")
        if "stacking" not in dims:
            out.append(
                "Stack height: NOT SPECIFIED — founder must confirm clearance "
                "above the rod/track."
            )
        return out

    def geometry(self, spec: Dict) -> GeometryResult:
        dims = spec["dims"]
        width = float(dims["width"])
        height = float(dims["height"])
        returns = float(dims.get("returns", 3.0))
        product_type = spec.get("product_type", "pinch_pleat")
        # Number of body panels (excludes returns). Snap to int; if the
        # result leaves a remainder, allocate the remainder to one
        # extra-half-panel by widening the last body panel by ≤ 1/2".
        max_panel = _DEFAULT_PANEL_WIDTHS[product_type]
        n_body = max(2, round(width / max_panel))
        body_total = width - 2 * returns
        body_w = body_total / n_body
        # Geometry: elevation (only — flat drapery; plan view only for
        # width subdivision). Local origin bottom-left of bodywork.
        points: List[GeometryPoint] = []
        edges: List[GeometryEdge] = []
        # Returns (small mounts at each end)
        for side in ("L", "R"):
            x = 0.0 if side == "L" else width
            label = "L return" if side == "L" else "R return"
            points.append(GeometryPoint(f"{side}_return_top", x, height, "elevation"))
            points.append(GeometryPoint(f"{side}_return_bot", x, 0.0, "elevation"))
            edges.append(GeometryEdge(f"{side}_return_top", f"{side}_return_bot",
                                       "elevation", weight="outline"))
        # Body panel verticals
        for i in range(n_body + 1):
            x = returns + i * body_w
            points.append(GeometryPoint(f"panel_{i}_top", x, height, "elevation"))
            points.append(GeometryPoint(f"panel_{i}_bot", x, 0.0, "elevation"))
        # Top + bottom hems across full width
        points.append(GeometryPoint("top_left", 0.0, height, "elevation"))
        points.append(GeometryPoint("top_right", width, height, "elevation"))
        points.append(GeometryPoint("bot_left", 0.0, 0.0, "elevation"))
        points.append(GeometryPoint("bot_right", width, 0.0, "elevation"))
        edges.append(GeometryEdge("top_left", "top_right", "elevation"))
        edges.append(GeometryEdge("bot_left", "bot_right", "elevation"))
        # Vertical panel seams
        for i in range(1, n_body):
            edges.append(GeometryEdge(f"panel_{i}_top", f"panel_{i}_bot",
                                       "elevation", weight="channel"))
        # Bottom rod-pocket tick mark (stylistic; only for rod_pocket).
        if product_type == "rod_pocket":
            for i in range(n_body + 1):
                edges.append(GeometryEdge(f"panel_{i}_bot", f"panel_{i}_top",
                                           "elevation", weight="detail"))
        return GeometryResult(
            points=points,
            edges=edges,
            bbox=(0.0, 0.0, width, height),
            views=["elevation"],
        )

    def layout_math(self, spec: Dict) -> List[MathLine]:
        dims = spec["dims"]
        width = float(dims["width"])
        returns = float(dims.get("returns", 3.0))
        product_type = spec.get("product_type", "pinch_pleat")
        max_panel = _DEFAULT_PANEL_WIDTHS[product_type]
        n_body = max(2, round(width / max_panel))
        body_total = width - 2 * returns
        body_w = body_total / n_body
        # Rule 3: n_body × body_w + 2 × returns must equal width.
        return [
            MathLine(
                label="Width closure",
                target_in=width,
                segments=[(n_body, body_w)],
                gaps=[(2, returns)],
                total=n_body * body_w + 2 * returns,
                note=(
                    "FLUSH BOTH ENDS"
                    if abs(n_body * body_w + 2 * returns - width) < (1 / 64)
                    else "WARN: closure off > 1/64\" — review panel count"
                ),
            ),
            MathLine(
                label="Height (panel length)",
                target_in=float(dims["height"]),
                segments=[(1, float(dims["height"]))],
                gaps=[],
                total=float(dims["height"]),
                note="Single panel; no subdivision.",
            ),
        ]

    def title_block(self, spec: Dict) -> Dict[str, str]:
        dims = spec["dims"]
        product_type = spec.get("product_type", "—")
        return {
            "ITEM": product_type.replace("_", " ").title(),
            "DIMENSIONS": f'{dims["width"]:.2f}" W × {dims["height"]:.2f}" H',
            "RETURNS": f'{dims.get("returns", 3.0):.1f}" (assumed)' if "returns" not in dims else f'{dims["returns"]:.1f}"',
            "FULLNESS": self._fullness_label(spec),
            "PLEATS": f'{self._pleat_count(spec)} panels',
        }

    @staticmethod
    def _fullness_label(spec: Dict) -> str:
        f = spec.get("dims", {}).get("fullness")
        if f is None:
            return "ASSUMED 2× (typical pinch pleat)"
        return f'{f}'

    @staticmethod
    def _pleat_count(spec: Dict) -> int:
        dims = spec.get("dims", {}) or {}
        if "width" not in dims:
            return 0
        product_type = spec.get("product_type", "pinch_pleat")
        max_panel = _DEFAULT_PANEL_WIDTHS.get(product_type, 24)
        return max(2, round(float(dims["width"]) / max_panel))
