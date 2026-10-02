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

from app.services.drawing.inches import format_inches
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

# Ripplefold keys the sheet understands. They are not pinch-pleat extras,
# and returns are not part of the job.
_RIPPLEFOLD_DIMS = {
    "width", "height", "window_width", "window_height",
    "coverage_width", "coverage", "track_length", "track",
    "coverage_align", "align", "track_align", "coverage_offset", "offset",
    "fullness", "fullness_pct", "fullness_percent",
    "carrier", "carrier_no", "carrier_number", "carrier_spacing", "spacing",
    "control", "draw", "draw_direction", "masters", "master",
    "stack", "stack_width", "stackback",
    "mount", "mount_type", "ceiling_height", "ceiling", "mount_height",
    "layer", "fabric_layer", "layered",
}


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
        if product_type == "ripplefold":
            extras = [d for d in dims if d not in _RIPPLEFOLD_DIMS]
            return MissingFieldsResult(
                missing_required=missing_req,
                missing_optional=[],
                extra_dims=extras,
            )
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
        if product_type == "ripplefold":
            return self._ripplefold_assumptions(spec)
        # Rule 1: every inferred value must surface here.
        out: List[str] = [
            f"Panel width: ASSUMED {format_inches(_DEFAULT_PANEL_WIDTHS.get(product_type, 24))} "
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
        if spec.get("product_type") == "ripplefold":
            return self._ripplefold_geometry(spec)
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
        if spec.get("product_type") == "ripplefold":
            return self._ripplefold_math(spec)
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
        if spec.get("product_type") == "ripplefold":
            return self._ripplefold_title(spec)
        dims = spec["dims"]
        product_type = spec.get("product_type", "—")
        return {
            "ITEM": product_type.replace("_", " ").title(),
            "DIMENSIONS": (
                f'{format_inches(dims["width"])} W × '
                f'{format_inches(dims["height"])} H'
            ),
            "RETURNS": (
                f'{format_inches(dims.get("returns", 3.0))} (assumed)'
                if "returns" not in dims
                else format_inches(dims["returns"])
            ),
            "FULLNESS": self._fullness_label(spec),
            "PLEATS": f'{self._pleat_count(spec)} panels',
        }

    def _ripplefold_job(self, spec: Dict):
        from app.services.drawing.templates.ripplefold_spec import resolve_ripplefold
        return resolve_ripplefold(spec)

    def _ripplefold_assumptions(self, spec: Dict) -> List[str]:
        try:
            job = self._ripplefold_job(spec)
        except ValueError:
            return ["Window width and height are required."]
        out: List[str] = []
        if job.track_equals_coverage:
            out.append("Track length: NOT GIVEN — track drawn equal to coverage.")
        if job.align is None:
            out.append("Coverage position: NOT GIVEN — track is not centered.")
        if job.stack_source == "kirsch chart" and job.stack is not None:
            out.append(
                f"Stack: {format_inches(job.stack)} from the Kirsch butt-master "
                f"chart at {job.carriers_per_panel} snaps."
            )
        if not out:
            out.append("No inferred dimensions. Mount and ceiling stay blank unless given.")
        return out

    def _ripplefold_geometry(self, spec: Dict) -> GeometryResult:
        job = self._ripplefold_job(spec)
        w, h = job.window_width, job.window_height
        points = [
            GeometryPoint("win_bl", 0.0, 0.0, "elevation"),
            GeometryPoint("win_br", w, 0.0, "elevation"),
            GeometryPoint("win_tl", 0.0, h, "elevation"),
            GeometryPoint("win_tr", w, h, "elevation"),
        ]
        edges = [
            GeometryEdge("win_bl", "win_br", "elevation"),
            GeometryEdge("win_br", "win_tr", "elevation"),
            GeometryEdge("win_tr", "win_tl", "elevation"),
            GeometryEdge("win_tl", "win_bl", "elevation"),
        ]
        if job.offset is not None:
            x0 = job.offset
            x1 = job.offset + job.coverage_width
            points.extend([
                GeometryPoint("track_l", x0, 0.0, "plan"),
                GeometryPoint("track_r", x1, 0.0, "plan"),
            ])
            edges.append(GeometryEdge("track_l", "track_r", "plan", weight="detail", label="track"))
        return GeometryResult(
            points=points, edges=edges, bbox=(0.0, 0.0, w, h),
            views=["elevation", "plan"],
        )

    def _ripplefold_math(self, spec: Dict) -> List[MathLine]:
        from app.services.drawing.templates.ripplefold_spec import (
            _CHART_BASE, _SPACING, chart_coverage,
        )
        job = self._ripplefold_job(spec)
        lines = [
            MathLine(
                label="Window width",
                target_in=job.window_width,
                segments=[(1, job.window_width)],
                gaps=[],
                total=job.window_width,
                note="FLUSH",
            ),
            MathLine(
                label="Window height",
                target_in=job.window_height,
                segments=[(1, job.window_height)],
                gaps=[],
                total=job.window_height,
                note="Single length.",
            ),
        ]
        if job.offset is not None:
            right = job.window_width - job.offset - job.coverage_width
            gaps = []
            if job.offset or right:
                gaps = [(1, job.offset), (1, right)]
            lines.append(MathLine(
                label="Coverage placement",
                target_in=job.window_width,
                segments=[(1, job.coverage_width)],
                gaps=gaps,
                total=job.offset + job.coverage_width + right,
                note="FLUSH BOTH ENDS",
            ))
        if job.carriers_per_panel and job.fullness and job.masters:
            snaps = job.carriers_per_panel
            covered = chart_coverage(snaps, job.fullness, job.masters)
            base = _CHART_BASE[job.masters][job.fullness]
            spacing = _SPACING[job.fullness]
            if snaps > 8:
                segments = [(snaps - 8, spacing)]
                gaps = [(1, base)]
            else:
                segments = [(1, base)]
                gaps = []
            lines.append(MathLine(
                label="Kirsch chart coverage",
                target_in=covered,
                segments=segments,
                gaps=gaps,
                total=covered,
                note=f"{snaps} snaps",
            ))
        return lines

    def _ripplefold_title(self, spec: Dict) -> Dict[str, str]:
        job = self._ripplefold_job(spec)
        return {
            "ITEM": "RIPPLEFOLD",
            "DIMENSIONS": (
                f"{format_inches(job.window_width)} W × "
                f"{format_inches(job.window_height)} H"
            ),
            "COVERAGE": format_inches(job.coverage_width),
            "TRACK": format_inches(job.track_length),
            "FULLNESS": f"{job.fullness}%" if job.fullness else "NOT GIVEN",
            "CARRIERS": str(job.carrier_count) if job.carrier_count else "NOT GIVEN",
            "MOUNT": job.mount or "NOT GIVEN",
            "CEILING": (
                format_inches(job.ceiling_height) if job.ceiling_height is not None
                else "NOT GIVEN"
            ),
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
