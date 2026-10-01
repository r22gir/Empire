"""Roman shade side-section layout QA (whole-panel text vs text / strokes)."""
from __future__ import annotations

from dataclasses import dataclass

from app.services.drawing.templates.b2_renderers import (
    PAGE_H_IN,
    PAGE_W_IN,
    SIDE_H_IN,
    SIDE_W_IN,
    SIDE_X_IN,
    SIDE_Y_IN,
    _P,
)


@dataclass
class _Box:
    x0: float
    y0: float
    x1: float
    y1: float
    label: str = ""

    def intersects(self, other: "_Box", pad: float = 0.5) -> bool:
        return not (
            self.x1 + pad <= other.x0
            or other.x1 + pad <= self.x0
            or self.y1 + pad <= other.y0
            or other.y1 + pad <= self.y0
        )


def _lines_in_region(page, x0: float, y0: float, x1: float, y1: float) -> list[_Box]:
    """Text line bboxes (PDF points) inside the side-section panel."""
    boxes: list[_Box] = []
    data = page.get_text("dict") or {}
    for block in data.get("blocks") or []:
        for line in block.get("lines") or []:
            spans = line.get("spans") or []
            text = "".join(s.get("text", "") for s in spans).strip()
            if not text:
                continue
            bbs = [s.get("bbox") for s in spans if s.get("bbox")]
            if not bbs:
                continue
            bx0 = min(b[0] for b in bbs)
            by0 = min(b[1] for b in bbs)
            bx1 = max(b[2] for b in bbs)
            by1 = max(b[3] for b in bbs)
            cx = (bx0 + bx1) / 2
            cy = (by0 + by1) / 2
            if not (x0 <= cx <= x1 and y0 <= cy <= y1):
                continue
            boxes.append(_Box(bx0, by0, bx1, by1, text[:48]))
    return boxes


def _detail_a_frame_pts(wall_y_in: float) -> _Box:
    """DETAIL A callout frame in PDF points (PyMuPDF: y from page top)."""
    dx0 = SIDE_X_IN + 0.30
    dy0 = wall_y_in + 0.42
    dw, dh = 1.65, 2.20
    y_top = _P(PAGE_H_IN - (dy0 + dh))
    y_bot = _P(PAGE_H_IN - dy0)
    return _Box(_P(dx0), y_top, _P(dx0 + dw), y_bot, "DETAIL_A_FRAME")


def _side_panel_pts() -> tuple[float, float, float, float]:
    """Side viewport in PDF points (PyMuPDF top-left origin)."""
    x0 = _P(SIDE_X_IN)
    x1 = _P(SIDE_X_IN + SIDE_W_IN)
    y_top = _P(PAGE_H_IN - (SIDE_Y_IN + SIDE_H_IN))
    y_bot = _P(PAGE_H_IN - SIDE_Y_IN)
    return x0, y_top, x1, y_bot


def find_roman_side_layout_conflicts(
    pdf_path: str,
    wall_y_in: float = 0.0,
    min_overlap_ratio: float = 0.06,
) -> list[str]:
    """Text-text and text-stroke conflicts in the side section."""
    import fitz

    doc = fitz.open(pdf_path)
    if not doc:
        return ["empty pdf"]
    page = doc[0]
    px0, py0, px1, py1 = _side_panel_pts()
    texts = _lines_in_region(page, px0, py0, px1, py1)
    frame = _detail_a_frame_pts(wall_y_in)
    issues: list[str] = []

    def _area(b: _Box) -> float:
        return max(0.0, (b.x1 - b.x0) * (b.y1 - b.y0))

    for i, a in enumerate(texts):
        for b in texts[i + 1 :]:
            if not a.intersects(b):
                continue
            inter_x0 = max(a.x0, b.x0)
            inter_y0 = max(a.y0, b.y0)
            inter_x1 = min(a.x1, b.x1)
            inter_y1 = min(a.y1, b.y1)
            inter = max(0.0, inter_x1 - inter_x0) * max(0.0, inter_y1 - inter_y0)
            denom = min(_area(a), _area(b)) or 1.0
            if inter / denom >= min_overlap_ratio:
                issues.append(f"text overlap {a.label!r} / {b.label!r} ({inter/denom:.0%})")

    stroke_pad = 2.0
    for t in texts:
        cx = (t.x0 + t.x1) / 2
        cy = (t.y0 + t.y1) / 2
        if frame.x0 <= cx <= frame.x1 and frame.y0 <= cy <= frame.y1:
            continue
        if frame.intersects(t, pad=stroke_pad):
            issues.append(f"text {t.label!r} intersects DETAIL A frame")

    doc.close()
    return issues


def assert_roman_side_labels_clear(pdf_path: str, wall_y_in: float = 0.0) -> None:
    issues = find_roman_side_layout_conflicts(pdf_path, wall_y_in=wall_y_in)
    if issues:
        raise AssertionError("; ".join(issues[:6]))
