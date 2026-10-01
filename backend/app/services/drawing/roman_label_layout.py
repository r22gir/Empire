"""Roman shade side-section label overlap checks (PDF text bboxes)."""
from __future__ import annotations

from typing import Iterable

ROMAN_SIDE_LABEL_MARKERS = (
    "FOLD STACK",
    "STACK",
    "HEM BAR",
    "FLAT TOP",
)


def _label_lines_on_page(page) -> list[dict]:
    """Line-level text boxes for roman side-section labels."""
    labels: list[dict] = []
    data = page.get_text("dict") or {}
    for block in data.get("blocks") or []:
        for line in block.get("lines") or []:
            spans = line.get("spans") or []
            text = "".join(s.get("text", "") for s in spans).strip()
            if not text or not _is_side_label(text):
                continue
            boxes = [s.get("bbox") for s in spans if s.get("bbox")]
            if not boxes:
                continue
            x0 = min(b[0] for b in boxes)
            y0 = min(b[1] for b in boxes)
            x1 = max(b[2] for b in boxes)
            y1 = max(b[3] for b in boxes)
            labels.append({"text": text, "x0": x0, "y0": y0, "x1": x1, "y1": y1})
    return labels


def _is_side_label(text: str) -> bool:
    up = text.upper()
    return any(m in up for m in ROMAN_SIDE_LABEL_MARKERS)


def _overlap_area(a: dict, b: dict) -> float:
    x0 = max(a["x0"], b["x0"])
    y0 = max(a["y0"], b["y0"])
    x1 = min(a["x1"], b["x1"])
    y1 = min(a["y1"], b["y1"])
    if x1 <= x0 or y1 <= y0:
        return 0.0
    return (x1 - x0) * (y1 - y0)


def _area(w: dict) -> float:
    return max(0.0, (w["x1"] - w["x0"]) * (w["y1"] - w["y0"]))


def find_roman_side_label_overlaps(pdf_path: str, min_overlap_ratio: float = 0.08) -> list[tuple[str, str, float]]:
    """Return overlapping label pairs on page 1 (ratio of smaller bbox area)."""
    import fitz

    doc = fitz.open(pdf_path)
    if not doc:
        return []
    page = doc[0]
    labels = _label_lines_on_page(page)
    pairs: list[tuple[str, str, float]] = []
    for i, a in enumerate(labels):
        for b in labels[i + 1:]:
            ov = _overlap_area(a, b)
            if ov <= 0:
                continue
            denom = min(_area(a), _area(b)) or 1.0
            ratio = ov / denom
            if ratio >= min_overlap_ratio:
                pairs.append((a["text"], b["text"], ratio))
    doc.close()
    return pairs


def assert_roman_side_labels_clear(pdf_path: str) -> None:
    overlaps = find_roman_side_label_overlaps(pdf_path)
    if overlaps:
        sample = ", ".join(f"{a!r}/{b!r} ({r:.0%})" for a, b, r in overlaps[:4])
        raise AssertionError(f"roman side labels overlap: {sample}")
