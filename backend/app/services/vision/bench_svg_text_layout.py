"""Bench shop-sheet SVG text overlap QA."""
from __future__ import annotations

import xml.etree.ElementTree as ET

from app.services.drawing.quote_sheet_layout import Rect, idea_sheet_regions

_SVG_NS = {"svg": "http://www.w3.org/2000/svg"}
_CHAR_W = 0.55  # width factor × font-size per character


def _text_boxes(svg: str) -> list[tuple[float, float, float, float, str]]:
    root = ET.fromstring(svg)
    boxes: list[tuple[float, float, float, float, str]] = []
    for el in root.findall(".//svg:text", _SVG_NS):
        x = float(el.get("x", 0))
        y = float(el.get("y", 0))
        size = float(el.get("font-size", 10))
        anchor = el.get("text-anchor", "middle")
        text = (el.text or "").strip()
        if not text:
            continue
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

    draw_boxes = [b for b in boxes if _drawing_label(b[4])]
    for i, a in enumerate(draw_boxes):
        for b in draw_boxes[i + 1 :]:
            if _intersects(a, b, pad=1.5):
                raise AssertionError(
                    f"text overlap {a[4]!r} vs {b[4]!r}"
                )
