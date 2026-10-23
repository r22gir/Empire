"""Bounded text layout for Max shop-drawing PDFs.

Notes and captions wrap inside frames, shrink if they still overflow,
then flow into the next frame. Measurement tokens (7 3/4") stay intact.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from reportlab.pdfgen import canvas

# Keep mixed numbers and inch marks together while wrapping.
_MEASURE_JOIN = re.compile(r'(\d+)\s+(\d+/\d+"?)')
_DECIMAL_INCH = re.compile(r'\d+\.\d+"')


@dataclass
class Frame:
    """PDF-space box. ``top`` is the upper edge (y grows up)."""

    name: str
    x: float
    top: float
    width: float
    height: float

    @property
    def bottom(self) -> float:
        return self.top - self.height

    @property
    def right(self) -> float:
        return self.x + self.width

    def inset(self, pad: float = 6.0) -> "Frame":
        return Frame(
            self.name,
            self.x + pad,
            self.top - pad,
            max(8.0, self.width - 2 * pad),
            max(8.0, self.height - 2 * pad),
        )


@dataclass
class LayoutIssue:
    kind: str
    page: int
    detail: str
    a: str = ""
    b: str = ""


@dataclass
class LayoutReport:
    issues: list[LayoutIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues

    def overflow(self) -> list[LayoutIssue]:
        return [i for i in self.issues if i.kind == "overflow"]

    def overlaps(self) -> list[LayoutIssue]:
        return [i for i in self.issues if i.kind == "overlap"]


def protect_measures(text: str) -> str:
    """Join mixed-number inch tokens so wrap does not split 7 3/4\"."""
    return _MEASURE_JOIN.sub(lambda m: f"{m.group(1)}\u00a0{m.group(2)}", text or "")


def wrap_text(
    c: canvas.Canvas,
    text: str,
    font: str,
    size: float,
    max_w: float,
) -> list[str]:
    raw = protect_measures((text or "").strip())
    if not raw:
        return []
    words = raw.split()
    lines: list[str] = []
    cur = ""
    for word in words:
        trial = (cur + " " + word).strip()
        if c.stringWidth(trial, font, size) <= max_w:
            cur = trial
            continue
        if cur:
            lines.append(cur.replace("\u00a0", " "))
        if c.stringWidth(word, font, size) <= max_w:
            cur = word
            continue
        chunk = word
        while chunk:
            lo, hi = 1, len(chunk)
            fit = 1
            while lo <= hi:
                mid = (lo + hi) // 2
                if c.stringWidth(chunk[:mid], font, size) <= max_w:
                    fit = mid
                    lo = mid + 1
                else:
                    hi = mid - 1
            lines.append(chunk[:fit].replace("\u00a0", " "))
            chunk = chunk[fit:]
        cur = ""
    if cur:
        lines.append(cur.replace("\u00a0", " "))
    return lines


def wrap_paragraphs(
    c: canvas.Canvas,
    paragraphs: Iterable[str],
    font: str,
    size: float,
    max_w: float,
) -> list[str]:
    lines: list[str] = []
    for i, para in enumerate(paragraphs):
        wrapped = wrap_text(c, para, font, size, max_w)
        if i and lines and lines[-1] != "" and wrapped:
            lines.append("")
        lines.extend(wrapped or ([""] if para == "" else []))
    while lines and lines[-1] == "":
        lines.pop()
    return lines


def fit_size(
    c: canvas.Canvas,
    paragraphs: list[str],
    font: str,
    size: float,
    max_w: float,
    max_h: float,
    *,
    leading_ratio: float = 1.35,
    min_size: float = 5.5,
) -> tuple[float, float, list[str]]:
    """Shrink until wrapped lines fit in max_h, or hit min_size."""
    use = float(size)
    while use >= min_size:
        leading = use * leading_ratio
        lines = wrap_paragraphs(c, paragraphs, font, use, max_w)
        need = max(leading, len(lines) * leading)
        if need <= max_h or use <= min_size + 0.05:
            return use, leading, lines
        use = round(use - 0.4, 2)
    leading = min_size * leading_ratio
    return min_size, leading, wrap_paragraphs(c, paragraphs, font, min_size, max_w)


def _flow_leftover(
    c: canvas.Canvas,
    paragraphs: list[str],
    frames: list[Frame],
    font: str,
    size: float,
    title: str | None,
    pad: float,
    leading_ratio: float,
) -> list[str]:
    leftover = wrap_paragraphs(c, list(paragraphs), font, size, frames[0].inset(pad).width)
    leading = size * leading_ratio
    for idx, frame in enumerate(frames):
        inner = frame.inset(pad)
        if idx:
            leftover = wrap_paragraphs(c, leftover, font, size, inner.width)
        yy = inner.top
        if title:
            yy -= size + 4
        fit_n = 0
        for text in leftover:
            if yy - size < inner.bottom:
                break
            fit_n += 1
            yy -= leading
        leftover = leftover[fit_n:]
        if not leftover:
            return []
    return leftover


def draw_flow(
    c: canvas.Canvas,
    paragraphs: list[str],
    frames: list[Frame],
    *,
    font: str = "Helvetica",
    size: float = 7.5,
    title: str | None = None,
    title_font: str = "Helvetica-Bold",
    fill=None,
    stroke=None,
    text_color=None,
    min_size: float = 5.5,
    leading_ratio: float = 1.35,
    pad: float = 7.0,
) -> list[str]:
    """Draw paragraphs into frames. Flow first; shrink if every frame overflows."""
    from reportlab.lib import colors as rl_colors

    if not frames:
        return list(paragraphs)
    body = text_color if text_color is not None else rl_colors.black
    use = float(size)
    leftover = list(paragraphs)
    while use >= min_size:
        leftover = _flow_leftover(
            c, paragraphs, frames, font, use, title, pad, leading_ratio,
        )
        if not leftover or use <= min_size + 0.05:
            break
        use = round(use - 0.4, 2)

    leading = use * leading_ratio
    room = wrap_paragraphs(c, list(paragraphs), font, use, frames[0].inset(pad).width)
    for idx, frame in enumerate(frames):
        if idx and not room:
            break
        inner = frame.inset(pad)
        if idx:
            room = wrap_paragraphs(c, room, font, use, inner.width)
        if fill is not None or stroke is not None:
            if fill is not None:
                c.setFillColor(fill)
            if stroke is not None:
                c.setStrokeColor(stroke)
                c.setLineWidth(0.6)
            c.rect(
                frame.x, frame.bottom, frame.width, frame.height,
                fill=1 if fill is not None else 0,
                stroke=1 if stroke is not None else 0,
            )
        yy = inner.top
        if title and idx == 0:
            c.setFillColor(stroke if stroke is not None else body)
            c.setFont(title_font, max(use, 6.5))
            c.drawString(inner.x, yy - use, title if idx == 0 else f"{title} (cont.)")
            yy -= use + 4
        elif title:
            c.setFillColor(stroke if stroke is not None else body)
            c.setFont(title_font, max(use, 6.0))
            c.drawString(inner.x, yy - use, f"{title} (cont.)")
            yy -= use + 4
        c.setFillColor(body)
        c.setFont(font, use)
        drawn: list[str] = []
        for text in room:
            if yy - use < inner.bottom:
                break
            if text:
                c.drawString(inner.x, yy - use, text)
            drawn.append(text)
            yy -= leading
        room = room[len(drawn):]
    return room


def caption_lines(
    c: canvas.Canvas,
    parts: list[str],
    font: str,
    size: float,
    max_w: float,
) -> list[str]:
    lines: list[str] = []
    for part in parts:
        lines.extend(wrap_text(c, part, font, size, max_w))
    return lines


def draw_caption_block(
    c: canvas.Canvas,
    parts: list[str],
    x: float,
    top: float,
    width: float,
    *,
    font: str = "Helvetica",
    size: float = 6.5,
    min_size: float = 5.0,
    max_height: float = 42.0,
    color=None,
) -> float:
    """Draw a caption under a view. Returns the lowest baseline used."""
    use, leading, lines = fit_size(
        c, parts, font, size, max(24.0, width), max_height,
        leading_ratio=1.28, min_size=min_size,
    )
    if color is not None:
        c.setFillColor(color)
    c.setFont(font, use)
    yy = top
    for line in lines:
        c.drawString(x, yy, line)
        yy -= leading
    return yy


def measurement_decimals(text: str) -> list[str]:
    return _DECIMAL_INCH.findall(text or "")


def _word_box(word: dict) -> tuple[float, float, float, float]:
    return float(word["x0"]), float(word["top"]), float(word["x1"]), float(word["bottom"])


def _overlap_area(a: dict, b: dict) -> tuple[float, float]:
    ox = min(a["x1"], b["x1"]) - max(a["x0"], b["x0"])
    oy = min(a["bottom"], b["bottom"]) - max(a["top"], b["top"])
    return ox, oy


def audit_drawing_layout(
    pdf_path: str,
    *,
    margin: float = 16.0,
    min_overlap_pt: float = 2.2,
    skip_short: int = 2,
) -> LayoutReport:
    """Measure extracted word bboxes against the page and each other."""
    import pdfplumber

    report = LayoutReport()
    with pdfplumber.open(pdf_path) as pdf:
        for page_i, page in enumerate(pdf.pages, start=1):
            pw, ph = float(page.width), float(page.height)
            words = page.extract_words(use_text_flow=False, keep_blank_chars=False) or []
            for word in words:
                x0, top, x1, bottom = _word_box(word)
                reasons = []
                if x0 < margin - 1:
                    reasons.append(f"left {x0:.1f}")
                if x1 > pw - margin + 1:
                    reasons.append(f"right {x1:.1f}>{pw - margin:.1f}")
                if top < 3:
                    reasons.append(f"top {top:.1f}")
                if bottom > ph - 3:
                    reasons.append(f"bottom {bottom:.1f}")
                if reasons:
                    report.issues.append(LayoutIssue(
                        "overflow", page_i,
                        f"{word['text']!r} {', '.join(reasons)}",
                        word["text"],
                    ))
            for i, a in enumerate(words):
                if len(a["text"]) < skip_short:
                    continue
                for b in words[i + 1 :]:
                    if len(b["text"]) < skip_short:
                        continue
                    if (
                        a["text"] == b["text"]
                        and abs(a["x0"] - b["x0"]) < 1
                        and abs(a["top"] - b["top"]) < 1
                    ):
                        continue
                    ox, oy = _overlap_area(a, b)
                    if ox > min_overlap_pt and oy > min_overlap_pt:
                        report.issues.append(LayoutIssue(
                            "overlap", page_i,
                            f"{a['text']!r} / {b['text']!r} ox={ox:.1f} oy={oy:.1f}",
                            a["text"], b["text"],
                        ))
    return report
