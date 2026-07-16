"""templates/valance.py — Valance family (14 styles).

Phase B1 — valance styles:
  kingston, cambridge, scalloped, arched, serpentine,
  flat_board_mounted, shaped, pleated, gathered, swag_and_jabot,
  cascades, empire, tab, cornice_with_fabric.

Required: (width, drop). Optional: (returns).

Style behavior:
  - "flat" styles (flat_board_mounted, pleated, tab): straight bottom.
  - "scalloped/arched/serpentine/shaped/empire": the BOTTOM edge has
    scallops or arcs. I model N scallops equally spaced, where N is
    round(width / 14) and each scallop is the drop multiplied by 0.35
    (ASSUMED ratio).
  - swag_and_jabot: swag at top + two jabots hanging below; modeled
    as three measured points.

Subdivision: width closes to 14" max scallop width (or to full
flat-style width).
"""
from __future__ import annotations

from typing import Dict, List

from app.services.drawing.templates.base import (
    FamilyTemplate, MissingFieldsResult, GeometryResult,
    GeometryPoint, GeometryEdge, MathLine,
)


_VALANCE_STYLES = {
    "kingston", "cambridge", "scalloped", "arched", "serpentine",
    "flat_board_mounted", "shaped", "pleated", "gathered",
    "swag_and_jabot", "cascades", "empire", "tab", "cornice_with_fabric",
}

_FLAT_STYLES = {"flat_board_mounted", "pleated", "tab", "pleated", "gathered"}
_SCALLOW_STYLES = {"scalloped", "arched", "serpentine", "shaped", "empire"}

VALANCE_PRODUCT_TYPES = list(_VALANCE_STYLES)

VALANCE_REQUIRED = ["width", "drop"]
VALANCE_OPTIONAL = ["returns"]


class ValanceTemplate(FamilyTemplate):
    family = "Valance"

    product_types = VALANCE_PRODUCT_TYPES

    def validate_spec(self, spec: Dict) -> MissingFieldsResult:
        dims = spec.get("dims", {}) or {}
        product_type = spec.get("product_type")
        if product_type not in _VALANCE_STYLES:
            return MissingFieldsResult(missing_required=["product_type"])
        missing_req = [d for d in VALANCE_REQUIRED
                       if d not in dims or dims[d] is None]
        missing_opt = [d for d in VALANCE_OPTIONAL
                       if d not in dims or dims[d] is None]
        extras = [d for d in dims
                  if d not in (set(VALANCE_REQUIRED + VALANCE_OPTIONAL))]
        return MissingFieldsResult(
            missing_required=missing_req,
            missing_optional=missing_opt,
            extra_dims=extras,
        )

    def assumptions(self, spec: Dict) -> List[str]:
        dims = spec.get("dims", {}) or {}
        product_type = spec.get("product_type", "—")
        out: List[str] = []
        if "returns" not in dims:
            out.append("Returns: ASSUMED 3\" each side.")
        if product_type in _SCALLOW_STYLES:
            out.append(
                f"Scallop depth: ASSUMED 0.35 × drop ({0.35 * float(dims.get('drop', 12)):.2f}\") "
                f"for {product_type} style — founder must confirm."
            )
            out.append(
                f"Scallop pitch: ASSUMED 14\" max ({max(2, round(float(dims.get('width', 24)) / 14))} scallops)."
            )
        if product_type == "swag_and_jabot":
            out.append(
                "Swag drop: ASSUMED 0.7 × drop. Jabot drop: ASSUMED 1.2 × drop."
            )
        return out

    def geometry(self, spec: Dict) -> GeometryResult:
        dims = spec["dims"]
        width = float(dims["width"])
        drop = float(dims["drop"])
        returns = float(dims.get("returns", 3.0))
        product_type = spec.get("product_type", "flat_board_mounted")
        n_return = 2
        body_total = width - n_return * returns
        points: List[GeometryPoint] = []
        edges: List[GeometryEdge] = []

        # Frame
        for name, (x, y) in (
            ("TL", (0.0, drop)),
            ("TR", (width, drop)),
            ("BL", (0.0, 0.0)),
            ("BR", (width, 0.0)),
        ):
            points.append(GeometryPoint(name, x, y, "elevation"))
        edges.append(GeometryEdge("TL", "TR", "elevation"))
        edges.append(GeometryEdge("BL", "BR", "elevation"))
        edges.append(GeometryEdge("TL", "BL", "elevation"))
        edges.append(GeometryEdge("TR", "BR", "elevation"))

        if product_type in _FLAT_STYLES:
            # Flat bottom; body = full width × drop, no fancy shape.
            return GeometryResult(
                points=points,
                edges=edges,
                bbox=(0.0, 0.0, width, drop),
                views=["elevation"],
            )

        if product_type in _SCALLOW_STYLES:
            # N scallops equally spaced across body. Each scallop dips
            # to drop × 0.35 below the bottom edge.
            n = max(2, round(width / 14))
            pitch = body_total / n
            scallop_depth = drop * 0.35
            for i in range(n + 1):
                x = returns + i * pitch
                name = f"s{i}"
                points.append(GeometryPoint(f"{name}_top", x, drop, "elevation"))
                points.append(GeometryPoint(f"{name}_bot", x, -scallop_depth,
                                             "elevation"))
                if i > 0:
                    prev = f"s{i - 1}"
                    # Top to top of current seam
                    edges.append(GeometryEdge(f"{prev}_top", f"{name}_top",
                                               "elevation"))
                    # Scallop dip: previous bottom → top of current seam,
                    # via a mid-scallop point (at the bottom edge level)
                    mid_x = (x + (returns + (i - 1) * pitch)) / 2
                    points.append(GeometryPoint(f"mid_{i}",
                                                 mid_x, -scallop_depth,
                                                 "elevation"))
                    edges.append(GeometryEdge(f"{prev}_bot",
                                               f"mid_{i}", "elevation",
                                               weight="channel"))
                    edges.append(GeometryEdge(f"mid_{i}", f"{name}_bot",
                                               "elevation", weight="channel"))
            return GeometryResult(
                points=points,
                edges=edges,
                bbox=(0.0, -scallop_depth, width, drop),
                views=["elevation"],
            )

        if product_type == "swag_and_jabot":
            # Three control points: swag top-center, jabot left+right.
            swag_drop = drop * 0.7
            jabot_drop = drop * 1.2
            mid_x = width / 2
            # Two side jabots hang 1/4 and 3/4 of width
            for side, fx in (("L", 0.25), ("R", 0.75)):
                x = width * fx
                points.append(GeometryPoint(f"jabot_{side}_top", x, drop,
                                             "elevation"))
                points.append(GeometryPoint(f"jabot_{side}_bot", x,
                                             -jabot_drop + drop, "elevation"))
            points.append(GeometryPoint("swag_top", mid_x, swag_drop,
                                         "elevation"))
            edges.append(GeometryEdge("jabot_L_top", "swag_top",
                                       "elevation", weight="detail"))
            edges.append(GeometryEdge("swag_top", "jabot_R_top",
                                       "elevation", weight="detail"))
            return GeometryResult(
                points=points,
                edges=edges,
                bbox=(0.0, -jabot_drop + drop, width, drop),
                views=["elevation"],
            )

        # cascades / kingston / cambridge — modeled as flat with an
        # ASSUMED second row hidden behind, just the frame.
        return GeometryResult(
            points=points,
            edges=edges,
            bbox=(0.0, 0.0, width, drop),
            views=["elevation"],
        )

    def layout_math(self, spec: Dict) -> List[MathLine]:
        dims = spec["dims"]
        width = float(dims["width"])
        drop = float(dims["drop"])
        returns = float(dims.get("returns", 3.0))
        product_type = spec.get("product_type", "flat_board_mounted")
        body_total = width - 2 * returns
        lines: List[MathLine] = []
        if product_type in _SCALLOW_STYLES:
            n = max(2, round(width / 14))
            pitch = body_total / n
            lines.append(MathLine(
                label="Width closure (bodywork across scallops)",
                target_in=width,
                segments=[(n, pitch)],
                gaps=[(2, returns)],
                total=n * pitch + 2 * returns,
                note=(
                    "FLUSH BOTH ENDS"
                    if abs(n * pitch + 2 * returns - width) < (1 / 64)
                    else "WARN: closure off > 1/64\""
                ),
            ))
            lines.append(MathLine(
                label="Drop (flat — bodywork rises to top edge)",
                target_in=drop,
                segments=[(1, drop)],
                gaps=[],
                total=drop,
                note="Single panel; no subdivision.",
            ))
        else:
            lines.append(MathLine(
                label="Width (full — no body subdivision)",
                target_in=width,
                segments=[(1, width)],
                gaps=[],
                total=width,
                note="Single panel; no subdivision.",
            ))
            lines.append(MathLine(
                label="Drop",
                target_in=drop,
                segments=[(1, drop)],
                gaps=[],
                total=drop,
                note="Single panel; no subdivision.",
            ))
        return lines

    def title_block(self, spec: Dict) -> Dict[str, str]:
        dims = spec["dims"]
        product_type = spec.get("product_type", "—")
        return {
            "ITEM": product_type.replace("_", " ").title(),
            "DIMENSIONS": f'{dims["width"]:.2f}" W × {dims["drop"]:.2f}" drop',
            "RETURNS": (
                f'{dims.get("returns"):.1f}"' if "returns" in dims
                else "ASSUMED 3\" each side"
            ),
            "STYLE": self._style_label(product_type),
        }

    @staticmethod
    def _style_label(product_type: str) -> str:
        if product_type in _SCALLOW_STYLES:
            return "Scalloped bottom (ASSUMED 0.35× drop depth, 14\" pitch)"
        if product_type == "swag_and_jabot":
            return "Swag + jabot (ASSUMED 0.7×/1.2× drop)"
        return "Flat bottom"
