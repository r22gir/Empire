"""Bench / banquette fabrication params from typed dims + owner text."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Optional

from app.services.drawing.bench_quote_bridge import length_to_inches_from_text

DEFAULT_SEAT_CUSHION_THICKNESS_IN = 2.0
DEFAULT_BACK_THICKNESS_IN = 2.0
DEFAULT_BACK_ANGLE_DEG = 0.0
RAKED_BACK_DEFAULT_DEG = 8.0


@dataclass(frozen=True)
class BenchFabricationParams:
    seat_cushion_thickness_in: float
    back_thickness_in: float
    seat_sections: int
    back_sections: int
    back_angle_deg: float
    seat_section_width_in: float
    back_section_width_in: float

    @property
    def seat_deck_height_in(self) -> float:
        return max(0.0, 0.0)  # set via seat_height on render

    def seat_cushion_depth_in(self, overall_depth_in: float) -> float:
        return max(0.0, float(overall_depth_in) - self.back_thickness_in)

    def side_back_lean_px(self, back_h_in: float, scale: float) -> float:
        if self.back_angle_deg <= 0 or not back_h_in:
            return 0.0
        lean = float(back_h_in) * scale * math.tan(math.radians(self.back_angle_deg))
        return min(lean, 4.0 * scale)


def _int_from_match(m: re.Match | None) -> Optional[int]:
    if not m:
        return None
    try:
        return int(m.group(1))
    except (IndexError, ValueError):
        return None


def _float_from_text(raw: Any, default: float = 0.0) -> float:
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return length_to_inches_from_text(raw, default=default)


def parse_bench_fabrication_from_text(text: str) -> dict[str, Any]:
    """Extract fabrication knobs from natural-language bench descriptions."""
    t = (text or "").lower()
    out: dict[str, Any] = {}

    if re.search(r"one[\s-]?piece\s+back", t):
        out["back_sections"] = 1
    m = re.search(
        r"(\d+)\s*(?:seat|seat\s*cushions?|seat\s*sections?|seat\s*cushion\s*sections?)",
        t,
    )
    if m:
        out["seat_sections"] = int(m.group(1))
    m = re.search(
        r"seat\s+in\s+(\d+)\s+sections?",
        t,
    )
    if m:
        out["seat_sections"] = int(m.group(1))
    m = re.search(
        r"(\d+)\s*(?:back\s*cushions?|back\s*sections?|back\s*cushion\s*sections?)",
        t,
    )
    if m:
        out["back_sections"] = int(m.group(1))

    cush = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:\"|in|inch(?:es)?)?\s*(?:foam\s+)?(?:seat\s+)?cushion(?:\s+thickness)?",
        t,
    )
    if not cush:
        cush = re.search(
            r"(\d+(?:\.\d+)?)\s*(?:\"|in)\s*(?:thick\s+)?(?:foam\s+)?seat\s+cushions?",
            t,
        )
    if not cush:
        cush = re.search(r"(\d+(?:\.\d+)?)\s*\"\s*cushion\b", t)
    if cush:
        out["seat_cushion_thickness"] = float(cush.group(1))

    bt = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:\"|in)?\s*back\s+thickness",
        t,
    )
    if bt:
        out["back_thickness"] = float(bt.group(1))

    m = re.search(
        r"raked\s+back\s+(\d+(?:\.\d+)?)\s*(?:deg(?:rees)?)?",
        t,
    )
    if m:
        out["back_angle_deg"] = float(m.group(1))
    elif re.search(r"\braked\s+back\b|\breclined\b|back\s+lean", t):
        deg = re.search(
            r"(?:raked|recline|lean)\s*(?:back\s*)?(?:@|at)?\s*(\d+(?:\.\d+)?)\s*(?:deg|degree)",
            t,
        )
        if deg:
            out["back_angle_deg"] = float(deg.group(1))
        else:
            out["back_angle_deg"] = RAKED_BACK_DEFAULT_DEG
    m = re.search(r"back\s+lean\s+(\d+(?:\.\d+)?)\s*(?:deg|degree)", t)
    if m:
        out["back_angle_deg"] = float(m.group(1))

    return out


def resolve_bench_fabrication(
    *,
    width_in: float,
    overall_depth_in: float,
    seat_height_in: float,
    dims: Optional[dict] = None,
    params: Optional[dict] = None,
    notes: str = "",
    seat_sections_default: int = 1,
) -> BenchFabricationParams:
    """Merge explicit dims/params with parsed text; apply defaults."""
    dims = dict(dims or {})
    params = dict(params or {})
    parsed = parse_bench_fabrication_from_text(notes)
    merged: dict[str, Any] = {**parsed, **dims, **params}

    seat_cush = _float_from_text(
        merged.get("seat_cushion_thickness")
        or merged.get("seat_cushion_thickness_in")
        or merged.get("cushion_thickness"),
        DEFAULT_SEAT_CUSHION_THICKNESS_IN,
    )
    seat_cush = max(0.0, min(seat_cush, max(0.0, float(seat_height_in) - 0.25)))

    back_thk = _float_from_text(
        merged.get("back_thickness") or merged.get("back_thickness_in"),
        DEFAULT_BACK_THICKNESS_IN,
    )
    back_thk = max(0.25, back_thk)

    seat_n = merged.get("seat_sections") or merged.get("seat_section_count")
    if seat_n is not None:
        seat_sections = max(1, int(seat_n))
    else:
        seat_sections = max(1, int(seat_sections_default))

    back_n = merged.get("back_sections") or merged.get("back_section_count")
    if back_n is not None:
        back_sections = max(1, int(back_n))
    else:
        back_sections = seat_sections

    angle = merged.get("back_angle_deg")
    if angle is None:
        angle = DEFAULT_BACK_ANGLE_DEG
    else:
        angle = float(angle)

    seat_w = float(width_in) / seat_sections
    back_w = float(width_in) / back_sections

    return BenchFabricationParams(
        seat_cushion_thickness_in=seat_cush,
        back_thickness_in=back_thk,
        seat_sections=seat_sections,
        back_sections=back_sections,
        back_angle_deg=angle,
        seat_section_width_in=seat_w,
        back_section_width_in=back_w,
    )


def merge_fabrication_into_sketch(resolved: dict, notes: str = "", dims: Optional[dict] = None) -> dict:
    """Augment resolve_sketch_bench() output with fabrication fields."""
    width = float(resolved.get("width_in") or 0)
    depth = float(resolved.get("seat_depth") or 18)
    seat_h = float(resolved.get("seat_height") or 18)
    seat_default = max(
        1,
        int(math.ceil(width / float(resolved.get("cushion_width") or 24)))
        if width > 0
        else 1,
    )
    fab = resolve_bench_fabrication(
        width_in=width,
        overall_depth_in=depth,
        seat_height_in=seat_h,
        dims=dims,
        params=resolved,
        notes=notes,
        seat_sections_default=seat_default,
    )
    out = dict(resolved)
    out.update(
        seat_cushion_thickness=fab.seat_cushion_thickness_in,
        back_thickness=fab.back_thickness_in,
        seat_sections=fab.seat_sections,
        back_sections=fab.back_sections,
        back_angle_deg=fab.back_angle_deg,
        seat_section_width=fab.seat_section_width_in,
        back_section_width=fab.back_section_width_in,
        cushion_count=fab.seat_sections,
    )
    return out
