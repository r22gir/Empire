"""templates/cornice.py — Cornice family (5 styles).

Phase B1 — straight, double_serpentine, pagoda, stepped, custom_profile.

Required: (width, depth, drop). Optional: (returns).

The cornice is a 3D box (a hard architectural cornice, NOT a soft
valance with fabric). Geometry must be in PLAN (because the top profile
has depth, not just a straight bottom) plus ELEVATION (front face).

Plan view closure: width = (n × body_w) + (2 × returns), where n is
the number of bodywork segments (each ≤ 24"). Returns close flush
against the wall.

Elevation closure: drop = n_steps × step_h (for "stepped" / "pagoda")
OR drop = drop (single panel for "straight" / "double_serpentine").

For "double_serpentine", the elevation shows an undulating front; I
model this as N cosine-wave lobes along width.

For all OTHER styles we lay a straight elevation with style hints in
the assumptions() block.
"""
from __future__ import annotations

from typing import Dict, List

from app.services.drawing.templates.base import (
    FamilyTemplate, MissingFieldsResult, GeometryResult,
    GeometryPoint, GeometryEdge, MathLine,
)


_CORNICE_STYLES = {
    "straight", "double_serpentine", "pagoda", "stepped", "custom_profile",
}

_CORNICE_PRODUCT_TYPES = list(_CORNICE_STYLES)

CORNICE_REQUIRED = ["width", "depth", "drop"]
CORNICE_OPTIONAL = ["returns"]


class CorniceTemplate(FamilyTemplate):
    family = "Cornice"

    product_types = _CORNICE_PRODUCT_TYPES

    def validate_spec(self, spec: Dict) -> MissingFieldsResult:
        dims = spec.get("dims", {}) or {}
        product_type = spec.get("product_type")
        if product_type not in _CORNICE_STYLES:
            return MissingFieldsResult(missing_required=["product_type"])
        missing_req = [d for d in CORNICE_REQUIRED
                       if d not in dims or dims[d] is None]
        missing_opt = [d for d in CORNICE_OPTIONAL
                       if d not in dims or dims[d] is None]
        extras = [d for d in dims
                  if d not in (set(CORNICE_REQUIRED + CORNICE_OPTIONAL))]
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
            out.append("Returns: ASSUMED 3\" each side (typical workroom).")
        if product_type == "stepped":
            out.append(
                "Step heights: ASSUMED 4 equal risers across drop "
                "(founder must confirm sequence)."
            )
        if product_type == "pagoda":
            out.append(
                "Tier heights: ASSUMED 3 equal tiers + capping ledge "
                "(founder must confirm tier count)."
            )
        if product_type == "double_serpentine":
            n = max(2, round(float(dims.get("width", 24)) / 24))
            out.append(
                f"Serpentine lobe count: ASSUMED {n} full lobes across width."
            )
        out.append(
            "Material: ASSUMED furniture-grade plywood + fabric wrap; "
            "founder must confirm before cutting."
        )
        return out

    def geometry(self, spec: Dict) -> GeometryResult:
        dims = spec["dims"]
        width = float(dims["width"])
        depth = float(dims["depth"])
        drop = float(dims["drop"])
        returns = float(dims.get("returns", 3.0))
        product_type = spec.get("product_type", "straight")
        points: List[GeometryPoint] = []
        edges: List[GeometryEdge] = []

        # ── PLAN VIEW (mandatory for cornice — has depth and returns)
        plan_origin_x = 0.0
        plan_origin_y = 0.0
        # Wall line: along bottom edge of plan view (returns extend up,
        # cornice body sits above the wall line).
        for name, (x, y) in (
            ("plan_TL", (plan_origin_x, depth + depth * 0.4)),
            ("plan_TR", (width, depth + depth * 0.4)),
            ("plan_BL", (plan_origin_x, 0.0)),
            ("plan_BR", (width, 0.0)),
        ):
            points.append(GeometryPoint(name, x, y, "plan"))
        edges.append(GeometryEdge("plan_TL", "plan_TR", "plan"))
        edges.append(GeometryEdge("plan_BL", "plan_BR", "plan"))
        edges.append(GeometryEdge("plan_TL", "plan_BL", "plan"))
        edges.append(GeometryEdge("plan_TR", "plan_BR", "plan"))
        # Returns (small side mounts at each end)
        ret_top = depth + depth * 0.4 - returns
        points.append(GeometryPoint("ret_L", 0.0, ret_top, "plan"))
        points.append(GeometryPoint("ret_R", width, ret_top, "plan"))
        edges.append(GeometryEdge("ret_L", "plan_TL", "plan", weight="channel"))
        edges.append(GeometryEdge("ret_R", "plan_TR", "plan", weight="channel"))
        # Bodywork plan view: 24" max width segments, dashed centerline
        max_seg = 24.0
        body_total = width - 2 * returns
        if body_total <= 0:
            body_total = width
        n_body = max(1, round(body_total / max_seg))
        body_w = body_total / n_body
        for i in range(1, n_body):
            x = returns + i * body_w
            points.append(GeometryPoint(f"body_seam_{i}", x, 0.0, "plan"))
            points.append(GeometryPoint(f"body_seam_{i}_top", x, depth * 0.4,
                                         "plan"))
            edges.append(GeometryEdge(f"body_seam_{i}", f"body_seam_{i}_top",
                                       "plan", weight="channel"))

        # ── ELEVATION VIEW (front face)
        # Lay below the plan by an offset so they don't overlap.
        el_y = -drop - drop * 0.4
        for name, (x, y) in (
            ("el_TL", (0.0, el_y + drop)),
            ("el_TR", (width, el_y + drop)),
            ("el_BL", (0.0, el_y)),
            ("el_BR", (width, el_y)),
        ):
            points.append(GeometryPoint(name, x, y, "elevation"))
        edges.append(GeometryEdge("el_TL", "el_TR", "elevation"))
        edges.append(GeometryEdge("el_BL", "el_BR", "elevation"))
        edges.append(GeometryEdge("el_TL", "el_BL", "elevation"))
        edges.append(GeometryEdge("el_TR", "el_BR", "elevation"))

        if product_type == "stepped":
            # Drop into n equal risers; the front face steps down at
            # each body seam.
            n_steps = 4
            step_h = drop / n_steps
            points.append(GeometryPoint("el_step_0", 0.0, el_y + drop,
                                         "elevation"))
            for i in range(n_steps - 1, -1, -1):
                y = el_y + i * step_h
                x_offset = 0.0 if i == n_steps - 1 else returns + body_w
                points.append(GeometryPoint(f"step_seam_{i}",
                                             x_offset, y, "elevation"))
                edges.append(GeometryEdge(f"step_seam_{i}",
                                           f"step_seam_{i}", "elevation",
                                           weight="channel"))

        if product_type == "double_serpentine":
            # Add a few control points along a cosine wave for the
            # front edge (decorative / dimensional only).
            n = max(2, round(width / 24))
            for k in range(1, n):
                import math as _math
                phase = 2 * _math.pi * k / n
                dip = -drop * 0.18
                peak = drop * 0.05
                y = el_y + drop / 2 + (peak + dip) / 2 + (
                    peak - dip) / 2 * _math.cos(phase * 2)
                x = returns + k * body_w
                points.append(GeometryPoint(f"sine_{k}", x, y, "elevation"))

        return GeometryResult(
            points=points,
            edges=edges,
            bbox=(0.0, el_y, width, depth + depth * 0.4),
            views=["plan", "elevation"],
        )

    def layout_math(self, spec: Dict) -> List[MathLine]:
        dims = spec["dims"]
        width = float(dims["width"])
        drop = float(dims["drop"])
        depth = float(dims["depth"])
        returns = float(dims.get("returns", 3.0))
        max_seg = 24.0
        body_total = width - 2 * returns
        if body_total <= 0:
            body_total = width
        n_body = max(1, round(body_total / max_seg))
        body_w = body_total / n_body
        lines: List[MathLine] = [
            MathLine(
                label="Width closure (plan view, bodywork)",
                target_in=width,
                segments=[(n_body, body_w)],
                gaps=[(2, returns)],
                total=n_body * body_w + 2 * returns,
                note=(
                    "FLUSH BOTH ENDS"
                    if abs(n_body * body_w + 2 * returns - width) < (1 / 64)
                    else "WARN: closure off > 1/64\""
                ),
            ),
            MathLine(
                label="Drop (elevation, full height)",
                target_in=drop,
                segments=[(1, drop)],
                gaps=[],
                total=drop,
                note="Single elevation; depth dimensioned separately.",
            ),
            MathLine(
                label="Depth (plan view)",
                target_in=depth,
                segments=[(1, depth)],
                gaps=[],
                total=depth,
                note="Sole depth dimension.",
            ),
        ]
        if spec.get("product_type") == "stepped":
            n_steps = 4
            step_h = drop / n_steps
            lines.append(MathLine(
                label="Step heights",
                target_in=drop,
                segments=[(n_steps, step_h)],
                gaps=[],
                total=n_steps * step_h,
                note=(
                    "ASSUMED 4 equal risers"
                    if abs(n_steps * step_h - drop) < (1 / 64)
                    else "WARN: closure off > 1/64\""
                ),
            ))
        return lines

    def title_block(self, spec: Dict) -> Dict[str, str]:
        dims = spec["dims"]
        product_type = spec.get("product_type", "—")
        return {
            "ITEM": product_type.replace("_", " ").title(),
            "DIMENSIONS": (
                f'{dims["width"]:.2f}" W × {dims["depth"]:.2f}" D × '
                f'{dims["drop"]:.2f}" drop'
            ),
            "RETURNS": (
                f'{dims.get("returns"):.1f}"' if "returns" in dims
                else "ASSUMED 3\" each side"
            ),
            "MATERIAL": "ASSUMED furniture-grade plywood + fabric wrap",
            "MOUNT": "Wall-mounted (height AFF NOT in spec)",
        }
