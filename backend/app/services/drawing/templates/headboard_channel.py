"""templates/headboard_channel.py — Headboard with vertical channels.

Phase B1 — `headboard_channel` is the only headboard variant that gets
its own family because it's the one most-commonly-customized. Other
headboard geometries (plain rectangle, button-tufted, nailhead trim)
remain D6-deferred per the parametric_renderer plan.

Required: (width, height). Optional: (thickness, channels).

Subdivision: vertical channels evenly subdivide the width. The
seam-to-seam width must close exactly per Rule 3. Foam depth
(thickness) is shown in side section.

Channel math closure example (60" wide, 8 channels, 6" each):

    8 × 6.0" channels = 48.0" — but that leaves 12" unaccounted for.
    Per Rule 3, the channels + their fabric overlaps MUST equal width.
    Modeled as: 7 × 6.0" seams + 2 × 6.0" outer channels = 60.0"
    — but that's 9 channels. The convention used: take the actual
    `channels` count and evenly distribute. If `channels` not given,
    compute from width / 5" (ASSUMED channel pitch).
"""
from __future__ import annotations

from typing import Dict, List

from app.services.drawing.templates.base import (
    FamilyTemplate, MissingFieldsResult, GeometryResult,
    GeometryPoint, GeometryEdge, MathLine,
)


_HEADBOARD_PRODUCT_TYPES = ["headboard_channel"]

HEADBOARD_CHANNEL_REQUIRED = ["width", "height"]
HEADBOARD_CHANNEL_OPTIONAL = ["thickness", "channels"]


class HeadboardChannelTemplate(FamilyTemplate):
    family = "Channel Headboard"

    product_types = _HEADBOARD_PRODUCT_TYPES

    def validate_spec(self, spec: Dict) -> MissingFieldsResult:
        dims = spec.get("dims", {}) or {}
        product_type = spec.get("product_type")
        if product_type not in _HEADBOARD_PRODUCT_TYPES:
            return MissingFieldsResult(missing_required=["product_type"])
        missing_req = [d for d in HEADBOARD_CHANNEL_REQUIRED
                       if d not in dims or dims[d] is None]
        missing_opt = [d for d in HEADBOARD_CHANNEL_OPTIONAL
                       if d not in dims or dims[d] is None]
        extras = [d for d in dims
                  if d not in (set(HEADBOARD_CHANNEL_REQUIRED + HEADBOARD_CHANNEL_OPTIONAL))]
        return MissingFieldsResult(
            missing_required=missing_req,
            missing_optional=missing_opt,
            extra_dims=extras,
        )

    def assumptions(self, spec: Dict) -> List[str]:
        dims = spec.get("dims", {}) or {}
        out: List[str] = []
        if "thickness" not in dims:
            out.append("Foam thickness: ASSUMED 4\" — founder must confirm.")
        if "channels" not in dims:
            width = float(dims.get("width", 60))
            # 5" channel pitch is a typical workroom default.
            n = max(4, round(width / 5.0))
            out.append(
                f"Channel pitch: ASSUMED 5\" pitch → {n} channels across "
                f"width. Founder must confirm or supply exact count."
            )
        return out

    def geometry(self, spec: Dict) -> GeometryResult:
        dims = spec["dims"]
        width = float(dims["width"])
        height = float(dims["height"])
        thickness = float(dims.get("thickness", 4.0))
        n_channels = int(dims.get("channels", max(4, round(width / 5.0))))
        points: List[GeometryPoint] = []
        edges: List[GeometryEdge] = []

        # ── ELEVATION (front face)
        for name, (x, y) in (
            ("front_TL", (0.0, height)),
            ("front_TR", (width, height)),
            ("front_BL", (0.0, 0.0)),
            ("front_BR", (width, 0.0)),
        ):
            points.append(GeometryPoint(name, x, y, "elevation"))
        edges.append(GeometryEdge("front_TL", "front_TR", "elevation"))
        edges.append(GeometryEdge("front_BL", "front_BR", "elevation"))
        edges.append(GeometryEdge("front_TL", "front_BL", "elevation"))
        edges.append(GeometryEdge("front_TR", "front_BR", "elevation"))

        # Vertical channel seams
        pitch = width / n_channels
        for i in range(1, n_channels):
            x = i * pitch
            points.append(GeometryPoint(f"ch_seam_top_{i}", x, height, "elevation"))
            points.append(GeometryPoint(f"ch_seam_bot_{i}", x, 0.0, "elevation"))
            edges.append(GeometryEdge(f"ch_seam_top_{i}", f"ch_seam_bot_{i}",
                                       "elevation", weight="channel"))

        # ── SECTION (top-down to show thickness)
        # Lay below the elevation
        off_y = -thickness - thickness * 0.5
        for name, (x, y) in (
            ("sec_TL", (0.0, off_y + thickness)),
            ("sec_TR", (width, off_y + thickness)),
            ("sec_BL", (0.0, off_y)),
            ("sec_BR", (width, off_y)),
        ):
            points.append(GeometryPoint(name, x, y, "section"))
        edges.append(GeometryEdge("sec_TL", "sec_TR", "section"))
        edges.append(GeometryEdge("sec_BL", "sec_BR", "section"))
        edges.append(GeometryEdge("sec_TL", "sec_BL", "section"))
        edges.append(GeometryEdge("sec_TR", "sec_BR", "section"))

        return GeometryResult(
            points=points,
            edges=edges,
            bbox=(0.0, off_y, width, height),
            views=["elevation", "section"],
        )

    def layout_math(self, spec: Dict) -> List[MathLine]:
        dims = spec["dims"]
        width = float(dims["width"])
        height = float(dims["height"])
        thickness = float(dims.get("thickness", 4.0))
        n_channels = int(dims.get("channels", max(4, round(width / 5.0))))
        pitch = width / n_channels
        return [
            MathLine(
                label="Width closure (channel pitch)",
                target_in=width,
                segments=[(n_channels, pitch)],
                gaps=[],
                total=n_channels * pitch,
                note=(
                    "FLUSH BOTH ENDS"
                    if abs(n_channels * pitch - width) < (1 / 64)
                    else "WARN: closure off > 1/64\""
                ),
            ),
            MathLine(
                label="Height (front face; not subdivided)",
                target_in=height,
                segments=[(1, height)],
                gaps=[],
                total=height,
                note="Single panel; channels run vertically full height.",
            ),
            MathLine(
                label="Thickness (section)",
                target_in=thickness,
                segments=[(1, thickness)],
                gaps=[],
                total=thickness,
                note="Sole thickness dimension.",
            ),
        ]

    def title_block(self, spec: Dict) -> Dict[str, str]:
        dims = spec["dims"]
        n_channels = int(dims.get("channels", max(4, round(float(dims["width"]) / 5.0))))
        return {
            "ITEM": "Headboard (Vertical Channels)",
            "DIMENSIONS": f'{dims["width"]:.2f}" W × {dims["height"]:.2f}" H',
            "THICKNESS": (
                f'{dims["thickness"]:.2f}"' if "thickness" in dims
                else "ASSUMED 4\""
            ),
            "CHANNELS": f"{n_channels} @ {float(dims['width']) / n_channels:.2f}\" pitch",
            "MOUNT": "Wall-mounted (mounting hardware NOT in spec)",
        }
