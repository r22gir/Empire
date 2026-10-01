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


def validate_bench_side_back_rake_rearward(svg: str) -> None:
    """Side back: vertical when angle 0; rearward rake when angle > 0."""
    root = ET.fromstring(svg)
    for g in root.findall(".//svg:g", _SVG_NS):
        if g.get("data-panel") != "side-elev":
            continue
        tx, ty = _parse_translate(g.get("transform", ""))
        for poly in g.findall(".//svg:polygon", _SVG_NS):
            if poly.get("data-side-back") != "1":
                continue
            pts = [(x + tx, y + ty) for x, y in _parse_points(poly.get("points", ""))]
            if len(pts) < 4:
                raise AssertionError("side back polygon missing corners")
            by_y = sorted(pts, key=lambda p: p[1])
            bottom = by_y[-2:]
            top = by_y[:2]
            bottom_max_x = max(p[0] for p in bottom)
            top_max_x = max(p[0] for p in top)
            angle_raw = poly.get("data-back-angle-deg", "")
            try:
                angle = float(angle_raw) if angle_raw != "" else None
            except ValueError:
                angle = None
            if angle is not None and angle <= 0.05:
                if abs(top_max_x - bottom_max_x) > 1.0:
                    raise AssertionError(
                        f"vertical back expected top x ≈ bottom x; "
                        f"got top={top_max_x:.1f} bottom={bottom_max_x:.1f}"
                    )
            else:
                if top_max_x <= bottom_max_x + 0.5:
                    raise AssertionError(
                        "side back top must lean rearward (top x > bottom x)"
                    )
            return
    raise AssertionError("no side back polygon (data-side-back) in side-elev panel")


def _side_elev_panel(root) -> tuple[float, float, ET.Element] | None:
    for g in root.findall(".//svg:g", _SVG_NS):
        if g.get("data-panel") == "side-elev":
            tx, ty = _parse_translate(g.get("transform", ""))
            return tx, ty, g
    return None


def validate_bench_side_seat_dim_stack(svg: str) -> None:
    """Side elevation seat dims: DK/CUSH/SH must not extend below floor."""
    root = ET.fromstring(svg)
    panel = _side_elev_panel(root)
    if panel is None:
        raise AssertionError("no side-elev panel")
    tx, ty, g = panel
    floor_y: float | None = None
    for el in g.findall(".//svg:line", _SVG_NS):
        if el.get("data-side-floor") == "1":
            y1, y2 = _float_attr(el, "y1"), _float_attr(el, "y2")
            if y1 is not None:
                floor_y = ty + y1
                break
    if floor_y is None:
        raise AssertionError("side floor line (data-side-floor) missing")

    for el in g.iter():
        tag = el.tag.split("}")[-1]
        if tag != "line" or el.get("data-dim-stroke") != "1":
            continue
        x1, y1 = _float_attr(el, "x1"), _float_attr(el, "y1")
        x2, y2 = _float_attr(el, "x2"), _float_attr(el, "y2")
        if None in (x1, y1, x2, y2):
            continue
        y1, y2 = ty + y1, ty + y2
        if abs(y1 - y2) < 2 or abs(x1 - x2) > 2:
            continue
        if max(y1, y2) > floor_y + 1.0:
            raise AssertionError(
                f"vertical seat dim extends below floor ({max(y1, y2):.1f} > {floor_y:.1f})"
            )


def validate_bench_side_tufts_inside_back(svg: str) -> None:
    """Tuft circles/lines on side back must lie inside the back polygon."""
    root = ET.fromstring(svg)
    panel = _side_elev_panel(root)
    if panel is None:
        return
    tx, ty, g = panel
    back_poly: list[tuple[float, float]] = []
    for poly in g.findall(".//svg:polygon", _SVG_NS):
        if poly.get("data-side-back") == "1":
            back_poly = [(x + tx, y + ty) for x, y in _parse_points(poly.get("points", ""))]
            break
    if not back_poly:
        return
    tuft_g = None
    for child in g.findall(".//svg:g", _SVG_NS):
        if child.get("data-side-back-tuft") == "1":
            tuft_g = child
            break
    if tuft_g is None:
        return
    if tuft_g.get("clip-path"):
        return
    for circle in tuft_g.findall(".//svg:circle", _SVG_NS):
        cx = _float_attr(circle, "cx")
        cy = _float_attr(circle, "cy")
        r = _float_attr(circle, "r") or 0
        if cx is None or cy is None:
            continue
        cx, cy = tx + cx, ty + cy
        if not _point_in_poly(cx, cy, back_poly):
            raise AssertionError("tuft circle center outside side back polygon")
        for ang in range(0, 360, 90):
            rad = math.radians(ang)
            px = cx + r * math.cos(rad)
            py = cy + r * math.sin(rad)
            if not _point_in_poly(px, py, back_poly):
                raise AssertionError("tuft circle extends outside side back polygon")
    for line in tuft_g.findall(".//svg:line", _SVG_NS):
        x1, y1 = _float_attr(line, "x1"), _float_attr(line, "y1")
        x2, y2 = _float_attr(line, "x2"), _float_attr(line, "y2")
        if None in (x1, y1, x2, y2):
            continue
        for px, py in ((tx + x1, ty + y1), (tx + x2, ty + y2)):
            if not _point_in_poly(px, py, back_poly):
                raise AssertionError("tuft line endpoint outside side back polygon")


def _side_dim_labels(svg: str) -> list[str]:
    root = ET.fromstring(svg)
    panel = _side_elev_panel(root)
    if not panel:
        return []
    tx, ty, g = panel
    labels: list[str] = []
    for el in g.findall(".//svg:text", _SVG_NS):
        t = (el.text or "").strip()
        if t:
            labels.append(t.replace("&quot;", '"'))
    return labels


def validate_bench_seat_cushion_consistency(
    svg: str,
    *,
    cushion_in: float,
    deck_in: float,
    seat_h_in: float,
) -> None:
    """Side elevation must show matching SH, DK, and CUSH inch values."""
    labels = " ".join(_side_dim_labels(svg))
    cush_s = _fmt_in_label(cushion_in)
    deck_s = _fmt_in_label(deck_in)
    sh_s = _fmt_in_label(seat_h_in)
    if f'{cush_s} CUSH' not in labels and f'{cushion_in:g}" CUSH' not in labels:
        raise AssertionError(f'missing {cushion_in}" CUSH in side labels: {labels[:120]}')
    if f'{deck_s} DK' not in labels and f'{deck_in:g}" DK' not in labels:
        raise AssertionError(f'missing {deck_in}" DK in side labels')
    if f'{sh_s} SH' not in labels and f'{seat_h_in:g}" SH' not in labels:
        raise AssertionError(f'missing {seat_h_in}" SH in side labels')


def _fmt_in_label(val: float) -> str:
    if abs(val - round(val)) < 0.01:
        return f'{int(round(val))}"'
    return f'{val:g}"'


def validate_bench_seat_overhang_dim(svg: str, overhang_in: float) -> None:
    labels = " ".join(_side_dim_labels(svg))
    oh = _fmt_in_label(overhang_in)
    if f'{oh} OH' not in labels and overhang_in <= 0:
        return
    if f'{oh} OH' not in labels:
        raise AssertionError(f'missing {overhang_in}" overhang (OH) dim on side elevation')


def validate_bench_raked_bh_parallel_to_back(svg: str) -> None:
    """When back is raked, BH dim must be oblique (not vertical)."""
    root = ET.fromstring(svg)
    panel = _side_elev_panel(root)
    if not panel:
        return
    tx, ty, g = panel
    angle_deg: float | None = None
    for poly in g.findall(".//svg:polygon", _SVG_NS):
        if poly.get("data-side-back") == "1":
            try:
                angle_deg = float(poly.get("data-back-angle-deg", "0") or 0)
            except ValueError:
                angle_deg = 0.0
            break
    if not angle_deg or angle_deg <= 0.05:
        return
    has_oblique_bh = False
    for el in g.iter():
        if el.tag.split("}")[-1] != "line" or el.get("data-dim-stroke") != "1":
            continue
        if el.get("data-dim-oblique") == "1" or el.get("data-side-bh") == "1":
            has_oblique_bh = True
            break
    if not has_oblique_bh:
        raise AssertionError("raked back requires oblique BH dimension on side elevation")


def validate_bench_side_seat_dim_parallel_stack(svg: str, min_sep: float = 6.0) -> None:
    """Side seat chain dims (CUSH/DK/SH) must be separate parallel vertical lines."""
    root = ET.fromstring(svg)
    panel = _side_elev_panel(root)
    if panel is None:
        return
    tx, ty, g = panel
    xs: list[float] = []
    for el in g.iter():
        if el.tag.split("}")[-1] != "line":
            continue
        if el.get("data-dim-stroke") != "1" or el.get("data-side-seat-dim") != "1":
            continue
        x1, x2 = _float_attr(el, "x1"), _float_attr(el, "x2")
        if x1 is None or x2 is None:
            continue
        if abs(x1 - x2) > 1.5:
            continue
        xs.append(tx + (x1 + x2) / 2)
    xs = sorted(set(round(x, 1) for x in xs))
    if len(xs) < 3:
        raise AssertionError(f"expected 3 parallel side seat dims, got {len(xs)}")
    for a, b in zip(xs, xs[1:]):
        if b - a < min_sep:
            raise AssertionError(f"side seat dim lines too close ({a:.1f} vs {b:.1f})")


def validate_bench_side_depth_inside_frame(
    svg: str,
    *,
    overall_depth_in: float,
    back_thickness_in: float,
    usable_seat_in: float,
) -> None:
    """Back cushion sits inside stated depth; rear face flush with frame back (vertical)."""
    root = ET.fromstring(svg)
    panel = _side_elev_panel(root)
    if panel is None:
        raise AssertionError("no side-elev panel")
    tx, ty, g = panel
    floor_x0 = floor_x1 = None
    for el in g.findall(".//svg:line", _SVG_NS):
        if el.get("data-side-floor") == "1":
            x1, x2 = _float_attr(el, "x1"), _float_attr(el, "x2")
            if x1 is not None and x2 is not None:
                floor_x0, floor_x1 = tx + min(x1, x2), tx + max(x1, x2)
                break
    if floor_x0 is None:
        raise AssertionError("side floor line missing")
    labels = " ".join(_side_dim_labels(svg))
    od = _fmt_in_label(overall_depth_in)
    us = _fmt_in_label(usable_seat_in)
    bt = _fmt_in_label(back_thickness_in)
    if od not in labels:
        raise AssertionError(f'missing overall depth label {od} on side elevation')
    if f'{us} SEAT' not in labels and f'{usable_seat_in:g}" SEAT' not in labels:
        raise AssertionError(f'missing usable seat label ({usable_seat_in}" SEAT)')
    if bt not in labels:
        raise AssertionError(f'missing back thickness label {bt} on side elevation')
    for poly in g.findall(".//svg:polygon", _SVG_NS):
        if poly.get("data-side-back") != "1":
            continue
        pts = [(x + tx, y + ty) for x, y in _parse_points(poly.get("points", ""))]
        if len(pts) < 4:
            continue
        by_y = sorted(pts, key=lambda p: p[1])
        bottom = by_y[-2:]
        rear_x = max(p[0] for p in bottom)
        front_x = min(p[0] for p in bottom)
        if abs(rear_x - floor_x1) > 2.0:
            raise AssertionError(
                f"back rear not flush with frame back ({rear_x:.1f} vs floor {floor_x1:.1f})"
            )
        scale = (floor_x1 - floor_x0) / max(overall_depth_in, 0.01)
        expected_front = floor_x1 - back_thickness_in * scale
        if abs(front_x - expected_front) > 2.5:
            raise AssertionError(
                f"back front face not {back_thickness_in}\" inside frame "
                f"({front_x:.1f} vs expected {expected_front:.1f})"
            )
        for p in pts:
            if p[0] > floor_x1 + 2.0 and p[1] > ty + 1:
                angle_raw = poly.get("data-back-angle-deg", "0")
                try:
                    angle = float(angle_raw or 0)
                except ValueError:
                    angle = 0.0
                if angle <= 0.05:
                    raise AssertionError("vertical back must not extend past frame rear at seat level")
        return


def validate_bench_depth_frame_note(svg: str, *, depth_in: float, seat_in: float, back_in: float) -> None:
    needle = (
        f'D {_fmt_in_label(depth_in)} frame: {_fmt_in_label(seat_in)} seat + '
        f'{_fmt_in_label(back_in)} back inside'
    )
    if needle not in svg.replace("&quot;", '"'):
        raise AssertionError(f"missing depth frame NOTE: {needle!r}")


def validate_bench_side_view_labels_clear(svg: str, layout: dict | None = None) -> None:
    """Side-elev dimension labels must not overlap each other or bench geometry."""
    from app.services.drawing.quote_sheet_layout import idea_sheet_regions
    from app.services.drawing.quote_sheet_layout import idea_sheet_regions
    from app.services.vision.bench_svg_text_layout import validate_bench_side_elev_text_layout

    validate_bench_side_elev_text_layout(svg, layout or idea_sheet_regions(title_rows=14))
    validate_bench_side_seat_dim_parallel_stack(svg)


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
