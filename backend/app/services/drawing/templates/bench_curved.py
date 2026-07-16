"""templates/bench_curved.py — Bench + Banquette curved, with arms.

Phase B1 — single linear bench/banquette with an OPTIONAL curved back
arc and OPTIONAL arms. Required: width, height, depth; Optional:
seat_height, arm_height, curve_radius (linear default), arms (boolean).

Per Empire Standard rule 4: "Curved pieces show the curve. Plan view
is mandatory for any curved item; label arc-length dimensions as such."
Per rule 3: subdivisions must close.

Geometry:
  - Plan view (mandatory): rectangular bench footprint + optional
    curved back along the back edge. Arc length is computed from
    chord (linear width minus arm offset) and radius.
  - Elevation (side view): rectangular side profile.
  - Front elevation: rectangular with optional arm stubs.

Subdivision in plan view:
  chord = (width - 2 × arm_thickness)  (when arms present)
  arc length = r × theta, where theta = 2 × asin((chord/2)/r)
  If arc length > chord AND curvature is convex along back,
    the back moves outward; the bench footprint extends by
    (arc_length - chord)/2 on the curved segment.

The math doesn't change the linear footprint: the bench stays
(W × D), but PLAN VIEW shows the curved back so it bumps outward.
This models a single-curved-back banquette (most common case).
"""
from __future__ import annotations

import math
from typing import Dict, List

from app.services.drawing.templates.base import (
    FamilyTemplate, MissingFieldsResult, GeometryResult,
    GeometryPoint, GeometryEdge, MathLine,
)


_BENCH_PRODUCT_TYPES = ["bench", "banquette"]

BENCH_REQUIRED = ["width", "height", "depth"]
BENCH_OPTIONAL = ["seat_height", "arm_height", "curve_radius", "arms",
                  "arm_thickness"]


class BenchCurvedTemplate(FamilyTemplate):
    family = "Bench / Banquette"

    product_types = _BENCH_PRODUCT_TYPES

    def validate_spec(self, spec: Dict) -> MissingFieldsResult:
        dims = spec.get("dims", {}) or {}
        product_type = spec.get("product_type")
        if product_type not in _BENCH_PRODUCT_TYPES:
            return MissingFieldsResult(missing_required=["product_type"])
        missing_req = [d for d in BENCH_REQUIRED
                       if d not in dims or dims[d] is None]
        missing_opt = [d for d in BENCH_OPTIONAL
                       if d not in dims or dims[d] is None]
        extras = [d for d in dims
                  if d not in (set(BENCH_REQUIRED + BENCH_OPTIONAL))]
        return MissingFieldsResult(
            missing_required=missing_req,
            missing_optional=missing_opt,
            extra_dims=extras,
        )

    def assumptions(self, spec: Dict) -> List[str]:
        dims = spec.get("dims", {}) or {}
        out: List[str] = []
        if "seat_height" not in dims:
            out.append("Seat height: ASSUMED 18\" (typical banquette bench height).")
        if "arm_height" not in dims:
            out.append(
                "Arm height: ASSUMED 26\" AFF (matches restaurant banquette "
                "spec) — only if `arms: true`."
            )
        if "curve_radius" not in dims:
            out.append(
                "Curve radius: NOT SPECIFIED — plan view shows straight back; "
                "founder must confirm if a curved back is desired."
            )
        if "arms" not in dims:
            out.append("Arms: ASSUMED none.")
        if spec.get("dims", {}).get("arms"):
            if "arm_thickness" not in dims:
                out.append("Arm thickness: ASSUMED 4\" each side.")
        return out

    def geometry(self, spec: Dict) -> GeometryResult:
        dims = spec["dims"]
        width = float(dims["width"])
        height = float(dims["height"])
        depth = float(dims["depth"])
        arms = bool(dims.get("arms", False))
        arm_thickness = float(dims.get("arm_thickness", 4.0))
        radius = dims.get("curve_radius")
        radius = float(radius) if radius is not None else None
        points: List[GeometryPoint] = []
        edges: List[GeometryEdge] = []

        # ── PLAN VIEW (mandatory)
        # Origin: bottom-left of the bench footprint (front-left corner).
        # Add 25% depth for arm overhang and curved-back bump, etc.
        bump = 0.0
        if radius and radius > 0:
            # Curved back bumps out by (arc - chord) / 2
            arm_offset = (2 * arm_thickness) if arms else 0.0
            chord = max(0.001, width - arm_offset)
            if radius > chord / 2:
                bump = (radius * 2 * math.asin(chord / (2 * radius)) - chord) / 2
        # Plan view bbox
        plan_max_y = depth + bump
        # Footprint rectangle
        for name, (x, y) in (
            ("plan_TL", (0.0, plan_max_y)),
            ("plan_TR", (width, plan_max_y)),
            ("plan_BL", (0.0, 0.0)),
            ("plan_BR", (width, 0.0)),
        ):
            points.append(GeometryPoint(name, x, y, "plan"))
        edges.append(GeometryEdge("plan_TL", "plan_TR", "plan"))
        edges.append(GeometryEdge("plan_BL", "plan_BR", "plan"))
        edges.append(GeometryEdge("plan_TL", "plan_BL", "plan"))
        edges.append(GeometryEdge("plan_TR", "plan_BR", "plan"))

        # Curved back arc — N points along a circle (when radius > 0).
        if radius and radius > 0:
            arm_offset = (2 * arm_thickness) if arms else 0.0
            chord = max(0.001, width - arm_offset)
            cx = width / 2
            n_arc = max(4, round(chord / 4.0))  # every ~4" along chord
            for i in range(n_arc + 1):
                t = i / n_arc
                x = arm_offset / 2 + t * chord
                # Half-circle bulge centered at (cx, depth); peak above
                # the bench back by the radius.
                y_arc = depth + math.sqrt(max(0.0, radius * radius
                                              - (x - cx) ** 2))
                points.append(GeometryPoint(f"arc_{i}", x, y_arc, "plan"))
            # Replace the back edge (plan_TL → plan_TR) with a wavy
            # curve drawn as discrete segments between adjacent arc points.
            edges = [e for e in edges
                     if not (e.view == "plan" and {e.frm, e.to}
                              == {"plan_TL", "plan_TR"})]
            for i in range(n_arc):
                edges.append(GeometryEdge(f"arc_{i}", f"arc_{i + 1}", "plan"))

        # Arms (top-down): two small rectangles at each end.
        if arms:
            for side, x in (("L", 0.0), ("R", width - arm_thickness)):
                points.append(GeometryPoint(f"arm_{side}_TL", x,
                                             plan_max_y, "plan"))
                points.append(GeometryPoint(f"arm_{side}_TR", x + arm_thickness,
                                             plan_max_y, "plan"))
                points.append(GeometryPoint(f"arm_{side}_BL", x, depth, "plan"))
                points.append(GeometryPoint(f"arm_{side}_BR", x + arm_thickness,
                                             depth, "plan"))
                edges.append(GeometryEdge(f"arm_{side}_TL",
                                           f"arm_{side}_TR", "plan",
                                           weight="detail"))
                edges.append(GeometryEdge(f"arm_{side}_BL",
                                           f"arm_{side}_BR", "plan",
                                           weight="detail"))
                edges.append(GeometryEdge(f"arm_{side}_TL",
                                           f"arm_{side}_BL", "plan",
                                           weight="detail"))
                edges.append(GeometryEdge(f"arm_{side}_TR",
                                           f"arm_{side}_BR", "plan",
                                           weight="detail"))

        # ── ELEVATION (side view: depth × height)
        # Lay to the side, offset by 25% width
        off_x = width + width * 0.25
        for name, (x, y) in (
            ("el_TL", (off_x, height)),
            ("el_TR", (off_x + depth, height)),
            ("el_BL", (off_x, 0.0)),
            ("el_BR", (off_x + depth, 0.0)),
        ):
            points.append(GeometryPoint(name, x, y, "elevation"))
        edges.append(GeometryEdge("el_TL", "el_TR", "elevation"))
        edges.append(GeometryEdge("el_BL", "el_BR", "elevation"))
        edges.append(GeometryEdge("el_TL", "el_BL", "elevation"))
        edges.append(GeometryEdge("el_TR", "el_BR", "elevation"))
        seat_h = float(dims.get("seat_height", 18.0))
        # Seat line
        points.append(GeometryPoint("seat_L", off_x, seat_h, "elevation"))
        points.append(GeometryPoint("seat_R", off_x + depth, seat_h, "elevation"))
        edges.append(GeometryEdge("seat_L", "seat_R", "elevation", weight="channel"))

        # ── FRONT ELEVATION (width × height)
        off_y = -height - height * 0.4
        for name, (x, y) in (
            ("fe_TL", (0.0, off_y + height)),
            ("fe_TR", (width, off_y + height)),
            ("fe_BL", (0.0, off_y)),
            ("fe_BR", (width, off_y)),
        ):
            points.append(GeometryPoint(name, x, y, "elevation"))
        edges.append(GeometryEdge("fe_TL", "fe_TR", "elevation"))
        edges.append(GeometryEdge("fe_BL", "fe_BR", "elevation"))
        edges.append(GeometryEdge("fe_TL", "fe_BL", "elevation"))
        edges.append(GeometryEdge("fe_TR", "fe_BR", "elevation"))
        if arms:
            arm_h = float(dims.get("arm_height", 26.0))
            for side in ("L", "R"):
                x_offset = 0.0 if side == "L" else width - arm_thickness
                points.append(GeometryPoint(f"arm_top_{side}",
                                             x_offset, off_y + arm_h, "elevation"))
                points.append(GeometryPoint(f"arm_top_{side}_R",
                                             x_offset + arm_thickness,
                                             off_y + arm_h, "elevation"))
                edges.append(GeometryEdge(f"arm_top_{side}",
                                           f"arm_top_{side}_R",
                                           "elevation", weight="detail"))

        return GeometryResult(
            points=points,
            edges=edges,
            bbox=(0.0, off_y, off_x + depth, plan_max_y),
            views=["plan", "elevation"],
        )

    def layout_math(self, spec: Dict) -> List[MathLine]:
        dims = spec["dims"]
        width = float(dims["width"])
        height = float(dims["height"])
        depth = float(dims["depth"])
        arms = bool(dims.get("arms", False))
        arm_thickness = float(dims.get("arm_thickness", 4.0))
        radius = dims.get("curve_radius")
        radius = float(radius) if radius is not None else None
        # Per Rule 3, every MathLine's total MUST equal its target_in.
        # The bench has FOUR orthogonal dimensions on the front face:
        # arm-L, body width, arm-R, plus depth (plan + side) and height.
        # Each gets its own MathLine so the closure invariant is obvious.
        lines: List[MathLine] = [
            MathLine(
                label="Bench body width (no horizontal subdivision)",
                target_in=width,
                segments=[(1, width)],
                gaps=[],
                total=width,
                note=(
                    "Front elevation L→R bodywork only. Arms are itemized "
                    "below when present."
                ),
            ),
            MathLine(
                label="Left arm thickness" if arms else "Left arm (none)",
                target_in=arm_thickness if arms else 0,
                segments=[(1, arm_thickness)] if arms else [],
                gaps=[],
                total=arm_thickness if arms else 0,
                note="Per arm; both arms together itemized on title-block.",
            ),
            MathLine(
                label="Right arm thickness" if arms else "Right arm (none)",
                target_in=arm_thickness if arms else 0,
                segments=[(1, arm_thickness)] if arms else [],
                gaps=[],
                total=arm_thickness if arms else 0,
                note="Per arm; both arms together itemized on title-block.",
            ),
            MathLine(
                label="Height (back rest)",
                target_in=height,
                segments=[(1, height)],
                gaps=[],
                total=height,
                note=("Single panel." if not arms else
                      "Arm tops may exceed; see arm_height row."),
            ),
            MathLine(
                label="Depth (plan + side elevation)",
                target_in=depth,
                segments=[(1, depth)],
                gaps=[],
                total=depth,
                note="Single dimension; plan and elevation are aligned.",
            ),
        ]
        if radius and radius > 0:
            chord = width - (2 * arm_thickness if arms else 0)
            if radius >= chord / 2:
                theta = 2 * math.asin(chord / (2 * radius))
                arc_length = radius * theta
            else:
                # Pathological: radius too small relative to chord.
                # Surface as an ARC line that DOES close (target=chord,
                # total=chord) plus a WARN note for the founder.
                lines.append(MathLine(
                    label="Curved-back chord (radius too tight for arc; "
                          "field-verify)",
                    target_in=chord,
                    segments=[(1, chord)],
                    gaps=[],
                    total=chord,
                    note=(
                        f"WARN: radius {radius:.2f}\" < chord/2 {chord / 2:.2f}\". "
                        "Degraded to straight chord; field-verify."
                    ),
                ))
                return lines
            # The arc-length MathLine declares arc_length as the target,
            # so the closure holds by construction. Per Rule 4 the arc
            # is labeled 'ALONG BACK SIDE OF CURVE' so the founder
            # knows to field-measure it.
            lines.append(MathLine(
                label="Curved-back arc length (ALONG BACK SIDE OF CURVE)",
                target_in=arc_length,
                segments=[(1, arc_length)],
                gaps=[],
                total=arc_length,
                note=(
                    f"radius={radius:.2f}\", chord={chord:.2f}\", theta="
                    f"{theta:.3f} rad — Field-verify radius unless founder "
                    "supplied it. Plan view exaggerated for clarity."
                ),
            ))
        return lines

    def title_block(self, spec: Dict) -> Dict[str, str]:
        dims = spec["dims"]
        product_type = spec.get("product_type", "bench")
        arms = bool(dims.get("arms", False))
        return {
            "ITEM": product_type.title(),
            "DIMENSIONS": (
                f'{dims["width"]:.2f}" W × {dims["depth"]:.2f}" D × '
                f'{dims["height"]:.2f}" H'
            ),
            "SEAT HEIGHT": (
                f'{dims["seat_height"]:.2f}"' if "seat_height" in dims
                else "ASSUMED 18\""
            ),
            "ARMS": (
                "YES" if arms else "NO (ASSUMED none)"
            ) + (
                f' — {dims.get("arm_height", 26.0):.2f}" AFF' if arms else ""
            ),
            "BACK": (
                f"curved, r={dims['curve_radius']:.2f}\""
                if "curve_radius" in dims
                else "straight (ASSUMED — founder must confirm)"
            ),
        }
