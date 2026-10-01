"""Bench idea-sheet SVG layout assertions (tests + QA)."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from app.services.drawing.quote_sheet_layout import Rect, idea_sheet_regions

_SVG_NS = {"svg": "http://www.w3.org/2000/svg"}
_SHEET_W = 1200.0
_SHEET_H = 850.0
_PAGE_MARGIN = 12.0


def _parse_translate(transform: str) -> tuple[float, float]:
    m = re.search(r"translate\(\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\)", transform or "")
    if not m:
        return 0.0, 0.0
    return float(m.group(1)), float(m.group(2))


def _float_attr(el, name: str) -> float | None:
    raw = el.get(name)
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _element_points(el, tx: float, ty: float) -> list[tuple[float, float]]:
    tag = el.tag.split("}")[-1]
    pts: list[tuple[float, float]] = []
    if tag == "rect":
        x, y = _float_attr(el, "x"), _float_attr(el, "y")
        w, h = _float_attr(el, "w") or _float_attr(el, "width"), _float_attr(el, "h") or _float_attr(el, "height")
        if x is not None and y is not None and w is not None and h is not None:
            pts.extend([(tx + x, ty + y), (tx + x + w, ty + y + h)])
    elif tag == "line":
        for a, b in (("x1", "y1"), ("x2", "y2")):
            x, y = _float_attr(el, a), _float_attr(el, b)
            if x is not None and y is not None:
                pts.append((tx + x, ty + y))
    elif tag == "circle":
        cx, cy = _float_attr(el, "cx"), _float_attr(el, "cy")
        r = _float_attr(el, "r") or 0.0
        if cx is not None and cy is not None:
            pts.extend([(tx + cx - r, ty + cy - r), (tx + cx + r, ty + cy + r)])
    return pts


def validate_bench_svg_layout(svg: str, layout: dict | None = None) -> None:
    """Raise AssertionError if bench geometry escapes the sheet or view panels."""
    layout = layout or idea_sheet_regions(title_rows=12)
    root = ET.fromstring(svg)
    sheet = layout["sheet"]
    plan_frame = layout["plan_frame"]
    elev_frame = layout["elev_frame"]

    all_pts: list[tuple[float, float]] = []
    panel_pts: dict[str, list[tuple[float, float]]] = {
        "plan": [],
        "front-elev": [],
        "side-elev": [],
    }

    for g in root.findall(".//svg:g", _SVG_NS):
        panel = g.get("data-panel")
        tx, ty = _parse_translate(g.get("transform", ""))
        for child in g:
            pts = _element_points(child, tx, ty)
            all_pts.extend(pts)
            if panel in panel_pts:
                panel_pts[panel].extend(pts)

    if not all_pts:
        raise AssertionError("bench SVG contained no measurable geometry")

    min_x = min(p[0] for p in all_pts)
    max_x = max(p[0] for p in all_pts)
    min_y = min(p[1] for p in all_pts)
    max_y = max(p[1] for p in all_pts)

    if min_x < _PAGE_MARGIN - 2:
        raise AssertionError(f"geometry left of page margin (min x={min_x})")
    if max_x > _SHEET_W - _PAGE_MARGIN + 2:
        raise AssertionError(f"geometry right of page (max x={max_x})")
    if min_y < _PAGE_MARGIN - 2:
        raise AssertionError(f"geometry above page (min y={min_y})")
    if max_y > _SHEET_H - _PAGE_MARGIN + 2:
        raise AssertionError(f"geometry below page (max y={max_y})")

    def _assert_in_panel(
        name: str,
        frame: Rect,
        pad_l: float = 4.0,
        pad_t: float = 4.0,
        pad_r: float = 4.0,
        pad_b: float = 4.0,
    ) -> None:
        pts = panel_pts.get(name) or []
        if not pts:
            raise AssertionError(f"missing geometry for panel {name}")
        px0, py0 = frame.x + pad_l, frame.y + pad_t
        px1, py1 = frame.right - pad_r, frame.bottom - pad_b
        for x, y in pts:
            if not (px0 <= x <= px1 and py0 <= y <= py1):
                raise AssertionError(
                    f"{name} geometry ({x:.1f},{y:.1f}) outside panel "
                    f"({px0:.0f},{py0:.0f})-({px1:.0f},{py1:.0f})"
                )

    _assert_in_panel("plan", plan_frame)
    if panel_pts["front-elev"] or panel_pts["side-elev"]:
        gap = max(18.0, elev_frame.w * 0.04)
        front_w = elev_frame.w * 0.40
        side_w = elev_frame.w - gap - front_w
        left_frame = Rect(elev_frame.x + 4, elev_frame.y, front_w - 4, elev_frame.h)
        right_frame = Rect(elev_frame.x + front_w + gap, elev_frame.y, side_w - 4, elev_frame.h)
        if panel_pts["front-elev"]:
            _assert_in_panel("front-elev", left_frame, pad_r=-20, pad_b=-48)
        if panel_pts["side-elev"]:
            _assert_in_panel(
                "side-elev", right_frame,
                pad_l=-14, pad_b=-54, pad_r=-38,
            )
