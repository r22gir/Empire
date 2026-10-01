"""Bench shop-sheet SVG text overlap QA."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from app.services.drawing.quote_sheet_layout import Rect, idea_sheet_regions

_SVG_NS = {"svg": "http://www.w3.org/2000/svg"}
_CHAR_W = 0.55  # width factor × font-size per character
_PANEL_PAD = 6.0
_GEOM_PAD = 1.5
_ELEV_GAP = 22.0


def _parse_translate(transform: str) -> tuple[float, float]:
    m = re.search(r"translate\(\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\)", transform or "")
    if not m:
        return 0.0, 0.0
    return float(m.group(1)), float(m.group(2))


def _text_boxes_local(el) -> list[tuple[float, float, float, float, str]]:
    boxes: list[tuple[float, float, float, float, str]] = []
    size = float(el.get("font-size", 10))
    anchor = el.get("text-anchor", "middle")
    text = (el.text or "").strip()
    if not text:
        return boxes
    x = float(el.get("x", 0))
    y = float(el.get("y", 0))
    w = len(text) * size * _CHAR_W
    if anchor == "end":
        x0, x1 = x - w, x
    elif anchor == "start":
        x0, x1 = x, x + w
    else:
        x0, x1 = x - w / 2, x + w / 2
    y0, y1 = y - size, y + 2
    boxes.append((x0, y0, x1, y1, text[:40]))
    return boxes


def _shift_box(box, tx: float, ty: float):
    x0, y0, x1, y1, label = box
    return (x0 + tx, y0 + ty, x1 + tx, y1 + ty, label)


def _panel_text_boxes(
    svg: str,
) -> list[tuple[str | None, tuple[float, float, float, float, str]]]:
    root = ET.fromstring(svg)
    parent_map: dict = {child: parent for parent in root.iter() for child in parent}
    out: list[tuple[str | None, tuple[float, float, float, str]]] = []
    for el in root.findall(".//svg:text", _SVG_NS):
        panel: str | None = None
        tx = ty = 0.0
        node = el
        while node is not None and node is not root:
            tag = node.tag.split("}")[-1] if "}" in node.tag else node.tag
            if tag == "g" and node.get("data-panel"):
                panel = node.get("data-panel")
                dx, dy = _parse_translate(node.get("transform", ""))
                tx += dx
                ty += dy
                break
            node = parent_map.get(node)
        for box in _text_boxes_local(el):
            out.append((panel, _shift_box(box, tx, ty)))
    return out


def _text_boxes(svg: str) -> list[tuple[float, float, float, float, str]]:
    return [box for _, box in _panel_text_boxes(svg)]


def _intersects(a, b, pad: float = 2.0) -> bool:
    ax0, ay0, ax1, ay1, _ = a
    bx0, by0, bx1, by1, _ = b
    return not (ax1 + pad <= bx0 or bx1 + pad <= ax0 or ay1 + pad <= by0 or by1 + pad <= ay0)


def _crosses_border(box, frame: Rect, slack: float = 4.0) -> bool:
    x0, y0, x1, y1, _ = box
    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2
    if not (frame.x <= cx <= frame.right and frame.y <= cy <= frame.bottom):
        return True
    return (
        x0 < frame.x - slack
        or x1 > frame.right + slack
        or y0 < frame.y - slack
        or y1 > frame.bottom + slack
    )


def _box_outside_frame(box, frame: Rect, pad: float) -> bool:
    x0, y0, x1, y1, _ = box
    fx0, fy0 = frame.x + pad, frame.y + pad
    fx1, fy1 = frame.right - pad, frame.bottom - pad
    return x0 < fx0 or x1 > fx1 or y0 < fy0 or y1 > fy1


def _seg_intersects_box(x1, y1, x2, y2, bx0, by0, bx1, by1, pad: float) -> bool:
    """True if segment (x1,y1)-(x2,y2) meets expanded text box."""
    bx0 -= pad
    by0 -= pad
    bx1 += pad
    by1 += pad

    def inside(px, py):
        return bx0 <= px <= bx1 and by0 <= py <= by1

    if inside(x1, y1) or inside(x2, y2):
        return True

    edges = (
        (bx0, by0, bx1, by0),
        (bx1, by0, bx1, by1),
        (bx1, by1, bx0, by1),
        (bx0, by1, bx0, by0),
    )

    def orient(ax, ay, bx, by, cx, cy):
        return (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)

    for ex1, ey1, ex2, ey2 in edges:
        d1 = orient(x1, y1, x2, y2, ex1, ey1)
        d2 = orient(x1, y1, x2, y2, ex2, ey2)
        d3 = orient(ex1, ey1, ex2, ey2, x1, y1)
        d4 = orient(ex1, ey1, ex2, ey2, x2, y2)
        if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and (
            (d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)
        ):
            return True
    return False


def _float_attr(el, name: str) -> float | None:
    raw = el.get(name)
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _geom_segments(el, tx: float, ty: float) -> list[tuple[float, float, float, float]]:
    tag = el.tag.split("}")[-1]
    segs: list[tuple[float, float, float, float]] = []
    if el.get("data-geom") != "1":
        return segs
    if tag == "line":
        x1, y1 = _float_attr(el, "x1"), _float_attr(el, "y1")
        x2, y2 = _float_attr(el, "x2"), _float_attr(el, "y2")
        if None not in (x1, y1, x2, y2):
            segs.append((tx + x1, ty + y1, tx + x2, ty + y2))
    elif tag == "rect":
        x, y = _float_attr(el, "x"), _float_attr(el, "y")
        w = _float_attr(el, "width")
        h = _float_attr(el, "height")
        if None not in (x, y, w, h):
            x0, y0, x1, y1 = tx + x, ty + y, tx + x + w, ty + y + h
            segs.extend([
                (x0, y0, x1, y0),
                (x1, y0, x1, y1),
                (x1, y1, x0, y1),
                (x0, y1, x0, y0),
            ])
    elif tag == "polygon":
        pts_raw = el.get("points", "")
        nums = [float(v) for v in re.findall(r"[-\d.]+", pts_raw)]
        if len(nums) >= 4:
            points = [(tx + nums[i], ty + nums[i + 1]) for i in range(0, len(nums) - 1, 2)]
            for i in range(len(points)):
                x1, y1 = points[i]
                x2, y2 = points[(i + 1) % len(points)]
                segs.append((x1, y1, x2, y2))
    return segs


def _bench_panel_frames(layout: dict) -> dict[str, Rect]:
    elev_safe = layout.get("elev_safe")
    if elev_safe is None:
        elev = layout["elev"]
        elev_safe = elev.inset(36, 28, 36, 36)
    gap = max(18.0, elev_safe.w * 0.04)
    front_w = elev_safe.w * 0.34
    side_w = elev_safe.w - gap - front_w
    return {
        "iso": layout["iso_draw"],
        "front-elev": Rect(elev_safe.x + 4, elev_safe.y, front_w - 4, elev_safe.h),
        "side-elev": Rect(
            elev_safe.x + front_w + gap, elev_safe.y, side_w - 4, elev_safe.h,
        ),
    }


def _validate_panel_geometry_text(svg: str, layout: dict) -> None:
    root = ET.fromstring(svg)
    frames = _bench_panel_frames(layout)
    checked_panels = ("iso", "front-elev", "side-elev")

    for g in root.findall(".//svg:g", _SVG_NS):
        panel = g.get("data-panel")
        if panel not in checked_panels:
            continue
        frame = frames[panel]
        tx, ty = _parse_translate(g.get("transform", ""))
        text_boxes: list[tuple[float, float, float, float, str]] = []
        segments: list[tuple[float, float, float, float]] = []
        for child in g.iter():
            if child is g:
                continue
            tag = child.tag.split("}")[-1]
            if tag == "text":
                for box in _text_boxes_local(child):
                    text_boxes.append(_shift_box(box, tx, ty))
            else:
                segments.extend(_geom_segments(child, tx, ty))

        for box in text_boxes:
            if _box_outside_frame(box, frame, _PANEL_PAD):
                raise AssertionError(
                    f"{panel} text {box[4]!r} outside panel bbox (pad {_PANEL_PAD})"
                )
            label = box[4]
            if '"' not in label and " SH" not in label.upper() and " BH" not in label.upper():
                continue
            if " D" in label.upper():
                continue
            if panel == "iso":
                continue
            for seg in segments:
                x1, y1, x2, y2 = seg
                bx0, by0, bx1, by1 = box[0], box[1], box[2], box[3]
                if _seg_intersects_box(x1, y1, x2, y2, bx0, by0, bx1, by1, _GEOM_PAD):
                    raise AssertionError(
                        f"{panel} dim text {box[4]!r} intersects geometry stroke"
                    )


def validate_bench_side_elev_text_layout(svg: str, layout: dict | None = None) -> None:
    """Side elevation only: dim labels must not overlap each other or bench geometry."""
    layout = layout or idea_sheet_regions(title_rows=12)
    frames = _bench_panel_frames(layout)
    base = frames["side-elev"]
    # Depth dims sit below the floor line; height dims sit to the right of geometry.
    frame = Rect(base.x, base.y, base.w + 40, base.h + 54)
    root = ET.fromstring(svg)
    panel_g = None
    for g in root.findall(".//svg:g", _SVG_NS):
        if g.get("data-panel") == "side-elev":
            panel_g = g
            break
    if panel_g is None:
        raise AssertionError("no side-elev panel in SVG")

    tx, ty = _parse_translate(panel_g.get("transform", ""))
    text_boxes: list[tuple[float, float, float, float, str]] = []
    segments: list[tuple[float, float, float, float]] = []
    for child in panel_g.iter():
        if child is panel_g:
            continue
        tag = child.tag.split("}")[-1]
        if tag == "text":
            for box in _text_boxes_local(child):
                text_boxes.append(_shift_box(box, tx, ty))
        else:
            segments.extend(_geom_segments(child, tx, ty))

    def _drawing_label(text: str) -> bool:
        t = text.upper()
        return (
            '"' in text
            or " SH" in t
            or " BH" in t
            or " DK" in t
            or " CUSH" in t
            or " SEAT" in t
            or " OH" in t
        )

    labeled = [b for b in text_boxes if _drawing_label(b[4])]
    for i, a in enumerate(labeled):
        for b in labeled[i + 1 :]:
            if _intersects(a, b, pad=1.5):
                raise AssertionError(f"text overlap {a[4]!r} vs {b[4]!r}")

    for box in text_boxes:
        if _box_outside_frame(box, frame, _PANEL_PAD):
            raise AssertionError(
                f"side-elev text {box[4]!r} outside panel bbox (pad {_PANEL_PAD})"
            )
        label = box[4]
        if not _drawing_label(label):
            continue
        for seg in segments:
            x1, y1, x2, y2 = seg
            bx0, by0, bx1, by1 = box[0], box[1], box[2], box[3]
            if _seg_intersects_box(x1, y1, x2, y2, bx0, by0, bx1, by1, _GEOM_PAD):
                raise AssertionError(
                    f"side-elev dim text {box[4]!r} intersects geometry stroke"
                )


def validate_bench_svg_text_layout(svg: str, layout: dict | None = None) -> None:
    layout = layout or idea_sheet_regions(title_rows=12)
    boxes = _text_boxes(svg)
    if not boxes:
        return
    title = layout["title"]
    for box in boxes:
        x0, y0, x1, y1, label = box
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if title.x <= cx <= title.right and title.y <= cy <= title.bottom:
            if _crosses_border(box, title, slack=2.0):
                raise AssertionError(f"text {label!r} escapes title block")

    def _drawing_label(text: str) -> bool:
        t = text.upper()
        if '"' in text or " SH" in t or " BH" in t or " FL" in t:
            return True
        if any(w in t for w in ("PLAN", "FRONT", "SIDE", "ISOMETRIC", "ELEVATION", "VIEW")):
            return True
        return False

    labeled: list[tuple[str | None, tuple[float, float, float, float, str]]] = [
        (panel, box)
        for panel, box in _panel_text_boxes(svg)
        if _drawing_label(box[4])
    ]
    for i, (pa, a) in enumerate(labeled):
        for pb, b in labeled[i + 1 :]:
            if pa != pb:
                continue
            if _intersects(a, b, pad=1.5):
                raise AssertionError(
                    f"text overlap {a[4]!r} vs {b[4]!r}"
                )

    _validate_panel_geometry_text(svg, layout)
