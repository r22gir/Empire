"""Bench SVG dimension geometry QA (extension length, iso vs solid)."""
from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET

_SVG_NS = {"svg": "http://www.w3.org/2000/svg"}
_DIM_COLOR = "#333333"


def _parse_translate(transform: str) -> tuple[float, float]:
    m = re.search(r"translate\(\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\)", transform or "")
    if not m:
        return 0.0, 0.0
    return float(m.group(1)), float(m.group(2))


def _seg_len(x1, y1, x2, y2) -> float:
    return math.hypot(x2 - x1, y2 - y2)


def _float_attr(el, name: str) -> float | None:
    raw = el.get(name)
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _parse_points(raw: str) -> list[tuple[float, float]]:
    pts: list[tuple[float, float]] = []
    for pair in re.findall(r"([\d.+-]+)\s*,\s*([\d.+-]+)", raw or ""):
        pts.append((float(pair[0]), float(pair[1])))
    return pts


def _point_in_poly(px: float, py: float, poly: list[tuple[float, float]]) -> bool:
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if ((y1 > py) != (y2 > py)) and (
            px < (x2 - x1) * (py - y1) / (y2 - y1 + 1e-12) + x1
        ):
            inside = not inside
    return inside


def _segments_intersect(a, b, c, d) -> bool:
    def orient(ax, ay, bx, by, cx, cy):
        return (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)

    o1 = orient(a[0], a[1], b[0], b[1], c[0], c[1])
    o2 = orient(a[0], a[1], b[0], b[1], d[0], d[1])
    o3 = orient(c[0], c[1], d[0], d[1], a[0], a[1])
    o4 = orient(c[0], c[1], d[0], d[1], b[0], b[1])
    if o1 == 0 and o2 == 0 and o3 == 0 and o4 == 0:
        return False
    return (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0)


def _seg_hits_poly_interior(x1, y1, x2, y2, poly: list[tuple[float, float]]) -> bool:
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    if _point_in_poly(mx, my, poly):
        return True
    for i in range(len(poly)):
        px1, py1 = poly[i]
        px2, py2 = poly[(i + 1) % len(poly)]
        if _segments_intersect((x1, y1), (x2, y2), (px1, py1), (px2, py2)):
            if _point_in_poly(mx, my, poly):
                return True
            # Crossing boundary — treat as interior if either third point inside
            t1x, t1y = x1 + 0.25 * (x2 - x1), y1 + 0.25 * (y2 - y1)
            t2x, t2y = x1 + 0.75 * (x2 - x1), y1 + 0.75 * (y2 - y1)
            if _point_in_poly(t1x, t1y, poly) or _point_in_poly(t2x, t2y, poly):
                return True
    return False


def _line_in_checked_panels(root, el) -> bool:
    parent_map: dict = {child: parent for parent in root.iter() for child in parent}
    node = el
    while node is not None and node is not root:
        if node.tag.endswith("g") and node.get("data-panel") in (
            "iso", "front-elev", "side-elev",
        ):
            return True
        node = parent_map.get(node)
    return False


def validate_bench_extension_lines_max(svg: str, max_len: float = 30.0) -> None:
    root = ET.fromstring(svg)
    for el in root.findall(".//svg:line", _SVG_NS):
        if el.get("data-dim-ext") != "1":
            continue
        if not _line_in_checked_panels(root, el):
            continue
        x1, y1 = _float_attr(el, "x1"), _float_attr(el, "y1")
        x2, y2 = _float_attr(el, "x2"), _float_attr(el, "y2")
        if None in (x1, y1, x2, y2):
            continue
        ln = _seg_len(x1, y1, x2, y2)
        if ln > max_len + 0.5:
            raise AssertionError(
                f"extension line length {ln:.1f}px exceeds {max_len}px"
            )


def validate_bench_iso_dims_clear_faces(svg: str) -> None:
    """No iso dimension stroke may pass through an iso face polygon interior."""
    root = ET.fromstring(svg)
    faces: list[list[tuple[float, float]]] = []
    dim_segs: list[tuple[float, float, float, float]] = []

    for g in root.findall(".//svg:g", _SVG_NS):
        if g.get("data-panel") != "iso":
            continue
        tx, ty = _parse_translate(g.get("transform", ""))
        for poly in g.findall(".//svg:polygon", _SVG_NS):
            if poly.get("data-iso-face") == "1":
                faces.append(
                    [(x + tx, y + ty) for x, y in _parse_points(poly.get("points", ""))]
                )
        for el in g.iter():
            tag = el.tag.split("}")[-1]
            if tag != "line":
                continue
            if el.get("data-dim-ext") == "1":
                continue
            stroke = el.get("stroke", "")
            if stroke != _DIM_COLOR and el.get("data-dim-stroke") != "1":
                continue
            x1, y1 = _float_attr(el, "x1"), _float_attr(el, "y1")
            x2, y2 = _float_attr(el, "x2"), _float_attr(el, "y2")
            if None in (x1, y1, x2, y2):
                continue
            dim_segs.append((tx + x1, ty + y1, tx + x2, ty + y2))

    if not faces:
        raise AssertionError("no iso faces for dim clearance check")

    for seg in dim_segs:
        for face in faces:
            if _seg_hits_poly_interior(seg[0], seg[1], seg[2], seg[3], face):
                raise AssertionError(
                    "iso dimension segment intersects solid face interior"
                )
