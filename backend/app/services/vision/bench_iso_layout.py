"""Isometric bench face closure checks (SVG)."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

_SVG_NS = {"svg": "http://www.w3.org/2000/svg"}
_MIN_ISO_FACES_WITH_BACK = 9
_MIN_ISO_FACES_NO_BACK = 5


def _parse_points(raw: str) -> list[tuple[float, float]]:
    pts: list[tuple[float, float]] = []
    for pair in re.findall(r"([\d.+-]+)\s*,\s*([\d.+-]+)", raw or ""):
        pts.append((float(pair[0]), float(pair[1])))
    return pts


def validate_bench_iso_faces_closed(svg: str, has_back: bool = True) -> None:
    """Every iso face polygon must have 3+ vertices (SVG closes implicitly)."""
    root = ET.fromstring(svg)
    iso_polys: list[list[tuple[float, float]]] = []
    for g in root.findall(".//svg:g", _SVG_NS):
        if g.get("data-panel") != "iso":
            continue
        for poly in g.findall(".//svg:polygon", _SVG_NS):
            if poly.get("data-iso-face") != "1":
                continue
            pts = _parse_points(poly.get("points", ""))
            if len(pts) < 3:
                raise AssertionError(f"iso face has fewer than 3 vertices: {pts}")
            iso_polys.append(pts)
    if not iso_polys:
        raise AssertionError("no data-iso-face polygons under data-panel=iso")
    need = _MIN_ISO_FACES_WITH_BACK if has_back else _MIN_ISO_FACES_NO_BACK
    if len(iso_polys) < need:
        raise AssertionError(
            f"expected at least {need} iso faces, got {len(iso_polys)}"
        )
