"""Shared layout for quote idea-sheets.

Bench SVG sheets and B1 story sheets (valance, cornice, banquette,
headboard, and any later family still on the story printer) take
margins, type sizes, title-block rows, and view gutters from here.
Roman and drapery keep the golden vector frames; those sheets already
run through the B2 overlap gate.

Coordinates for ``layout_title_block`` are top-down inside the block:
y = 0 at the top edge, baseline y grows downward. SVG renderers add
the block origin. PDF renderers flip from the block top.
"""
from __future__ import annotations

from dataclasses import dataclass


# Landscape idea sheet, SVG user units. Drawn onto letter landscape.
SHEET_W = 1200.0
SHEET_H = 850.0

# Type ladder. SVG sizes are user units on the 1200-wide sheet
# (weasyprint scales that onto letter). PDF sizes are points.
SVG_TYPE = {
    "company": 18.0,
    "tagline": 11.0,
    "meta": 10.0,
    "caption": 13.0,
    "label": 11.0,
    "value": 12.0,
    "dim": 12.0,
    "chip": 11.5,
    "footer": 9.0,
}
PDF_TYPE = {
    "company": 13.0,
    "tagline": 8.0,
    "meta": 7.5,
    "caption": 9.0,
    "label": 8.0,
    "value": 8.5,
    "dim": 8.0,
    "chip": 8.0,
    "section": 9.0,
    "body": 8.0,
    "note": 7.5,
    "footer": 7.0,
}

# Average glyph width / font size for Helvetica/Arial. Used for wrap
# and for the overlap heuristic. Slightly wide so the test catches
# collisions before they are visible.
CHAR_FACTOR = 0.56

CAPTION_H = 26.0
IDEA_FOOTER = "NOT TO SCALE  ·  IDEA SHEET  ·  NOT FOR CONSTRUCTION"


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    w: float
    h: float

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h

    def inset(self, left: float = 0, top: float = 0,
              right: float = 0, bottom: float = 0) -> "Rect":
        return Rect(
            self.x + left,
            self.y + top,
            max(0.0, self.w - left - right),
            max(0.0, self.h - top - bottom),
        )


def estimate_title_height(n_rows: int, sizes: dict | None = None) -> float:
    """Block height that fits the header, chip, rows, and footer."""
    s = sizes or SVG_TYPE
    header = 14 + s["company"] + 8 + s["tagline"] + 6 + s["meta"] * 2 + 18
    chip = s["chip"] + 18
    rows = max(1, n_rows) * (s["value"] + 10)
    footer = 34
    return header + chip + rows + footer + 12


def idea_sheet_regions(title_rows: int = 9,
                       sheet_w: float = SHEET_W,
                       sheet_h: float = SHEET_H) -> dict[str, Rect]:
    """Views on the wide left, iso over a content-sized title block.

    Dimension gutters sit inside each orthographic frame so leaders
    cannot cross into the next view.
    """
    margin = 26.0
    gutter = 16.0
    header_h = 36.0
    dim_left = 56.0
    dim_right = 82.0
    dim_bottom = 38.0

    header = Rect(margin, margin, sheet_w - 2 * margin, header_h)
    top = header.bottom + 12
    bottom = sheet_h - margin
    left = margin
    content_h = bottom - top
    content_w = sheet_w - 2 * margin

    title_h = estimate_title_height(title_rows)
    title_h = min(max(title_h, 248.0), content_h * 0.58)
    left_w = round(content_w * 0.64)
    right_x = left + left_w + gutter
    right_w = (sheet_w - margin) - right_x

    plan_h = round((content_h - gutter) * 0.42)
    plan = Rect(left, top, left_w, plan_h)
    elev = Rect(left, plan.bottom + gutter, left_w, bottom - (plan.bottom + gutter))
    title = Rect(right_x, bottom - title_h, right_w, title_h)
    iso = Rect(right_x, top, right_w, max(80.0, title.y - gutter - top))

    def gutters(frame: Rect) -> dict[str, Rect]:
        return {
            "frame": frame,
            "safe": frame.inset(dim_left, CAPTION_H + 6, dim_right, dim_bottom),
            "dim_left": Rect(
                frame.x, frame.y + CAPTION_H,
                dim_left, max(0.0, frame.h - CAPTION_H - dim_bottom),
            ),
            "dim_right": Rect(
                frame.right - dim_right, frame.y + CAPTION_H,
                dim_right, max(0.0, frame.h - CAPTION_H - dim_bottom),
            ),
            "dim_bottom": Rect(
                frame.x + dim_left, frame.bottom - dim_bottom,
                max(0.0, frame.w - dim_left - dim_right), dim_bottom,
            ),
        }

    out: dict[str, Rect] = {
        "sheet": Rect(0, 0, sheet_w, sheet_h),
        "header": header,
        "plan": plan,
        "elev": elev,
        "iso": iso,
        "title": title,
    }
    for name, frame in (("plan", plan), ("elev", elev)):
        for key, rect in gutters(frame).items():
            out[f"{name}_{key}"] = rect
    out["iso_draw"] = iso.inset(8, CAPTION_H + 4, 4, 4)
    return out


def b1_page_regions(page_w: float = 792.0, page_h: float = 612.0,
                    title_rows: int = 10) -> dict[str, Rect]:
    """Landscape letter regions for a B1 idea sheet, in points."""
    margin = 28.0
    gutter = 12.0
    header_h = 46.0
    title_w = 230.0
    header = Rect(margin, margin, page_w - 2 * margin, header_h)
    top = header.bottom + 10
    bottom = page_h - margin
    left = margin
    title = Rect(page_w - margin - title_w, top, title_w, bottom - top)
    views = Rect(left, top, title.x - gutter - left, (bottom - top) * 0.58)
    notes = Rect(left, views.bottom + gutter, views.w, bottom - (views.bottom + gutter))
    return {
        "header": header,
        "title": title,
        "views": views,
        "notes": notes,
    }


def wrap_text(text: str, max_width: float, size: float,
              factor: float = CHAR_FACTOR) -> list[str]:
    """Wrap on spaces. A single token wider than the column is kept whole."""
    raw = " ".join((text or "").split())
    if not raw:
        return []
    if max_width <= 0:
        return [raw]
    limit = max(4.0, max_width)
    words = raw.split(" ")
    lines: list[str] = []
    cur = ""
    for word in words:
        trial = word if not cur else f"{cur} {word}"
        if len(trial) * size * factor <= limit:
            cur = trial
            continue
        if cur:
            lines.append(cur)
        cur = word
    if cur:
        lines.append(cur)
    return lines or [raw]


def text_bbox(x: float, y: float, text: str, size: float,
              anchor: str = "start", factor: float = CHAR_FACTOR) -> tuple[float, float, float, float]:
    """Axis-aligned box for one horizontal text run. ``y`` is the baseline."""
    width = max(len(text), 1) * size * factor
    height = size
    if anchor == "middle":
        x0 = x - width / 2
    elif anchor == "end":
        x0 = x - width
    else:
        x0 = x
    y0 = y - height * 0.82
    return (x0, y0, x0 + width, y0 + height)


def boxes_overlap(a: tuple, b: tuple, min_px: float = 2.0) -> bool:
    ix = min(a[2], b[2]) - max(a[0], b[0])
    iy = min(a[3], b[3]) - max(a[1], b[1])
    return ix > min_px and iy > min_px


def split_contact(contact: str) -> list[str]:
    parts = [p.strip() for p in (contact or "").split("|")]
    return [p for p in parts if p]


def layout_title_block(width: float, height: float, chrome: dict,
                       rows: list[tuple[str, str]], chip: str = "",
                       sizes: dict | None = None) -> list[dict]:
    """Title-block draw ops in top-down block coordinates.

    Rows never enter the footer band. Long values wrap inside the
    value column. Empty values are omitted.
    """
    s = dict(sizes or SVG_TYPE)
    pad = 12.0
    label_col = max(96.0, s["label"] * 11 * CHAR_FACTOR + 8)
    value_w = max(40.0, width - pad * 2 - label_col)
    footer_h = 28.0
    footer_top = height - footer_h

    ops: list[dict] = []
    y = 16.0

    def text(x, baseline, value, size, anchor="start", weight="normal", fill="ink"):
        ops.append({
            "kind": "text", "x": x, "y": baseline, "text": value,
            "size": size, "anchor": anchor, "weight": weight, "fill": fill,
        })

    def rule(y_line):
        ops.append({
            "kind": "rule", "x1": pad, "x2": width - pad, "y": y_line,
        })

    company = (chrome.get("company") or "EMPIRE WORKROOM").strip()
    text(width / 2, y + s["company"] * 0.8, company, s["company"],
         anchor="middle", weight="bold")
    y += s["company"] + 6
    tagline = (chrome.get("tagline") or "").strip()
    if tagline:
        text(width / 2, y + s["tagline"] * 0.8, tagline, s["tagline"],
             anchor="middle", fill="mute")
        y += s["tagline"] + 3
    address = (chrome.get("address") or "").strip()
    if address:
        text(width / 2, y + s["meta"] * 0.8, address, s["meta"],
             anchor="middle", fill="mute")
        y += s["meta"] + 2
    for line in split_contact(chrome.get("contact") or ""):
        text(width / 2, y + s["meta"] * 0.8, line, s["meta"],
             anchor="middle", fill="mute")
        y += s["meta"] + 2
    y += 4
    rule(y)
    y += 8

    chip = (chip or "").strip()
    if chip:
        chip_lines = wrap_text(chip, width - pad * 2 - 8, s["chip"])
        bar_h = 8 + len(chip_lines) * (s["chip"] + 2)
        ops.append({
            "kind": "rect", "x": pad, "y": y, "w": width - pad * 2, "h": bar_h,
            "fill": "chip",
        })
        line_y = y + 4 + s["chip"] * 0.8
        for line in chip_lines:
            text(width / 2, line_y, line, s["chip"], anchor="middle", weight="bold")
            line_y += s["chip"] + 2
        y += bar_h + 6
        rule(y)
        y += 10

    clean_rows = [(str(l), str(v)) for l, v in rows if str(v or "").strip()]
    # Shrink value size until the rows sit above the footer.
    value_size = s["value"]
    label_size = s["label"]
    gap = 7.0
    wrapped: list[tuple[str, list[str]]] = []

    def fit_lines(value: str, vsize: float):
        """Stay on one line when a modest shrink fits. Wrap only past that."""
        size = vsize
        while size > 8 and len(value) * size * CHAR_FACTOR > value_w:
            size -= 0.5
        if len(value) * size * CHAR_FACTOR <= value_w:
            return [value], size
        return wrap_text(value, value_w, size) or [value], size

    def measure(vsize: float, lead: float):
        packed = []
        total = 0.0
        for label, value in clean_rows:
            lines, size = fit_lines(value, vsize)
            packed.append((label, lines, size))
            total += max(1, len(lines)) * (size + 3) + lead
        return packed, total

    for _ in range(10):
        wrapped, total = measure(value_size, gap)
        if y + total <= footer_top - 6:
            break
        if gap > 2:
            gap -= 1
            continue
        if value_size > 8:
            value_size -= 0.5
            label_size = min(label_size, value_size)
            continue
        break
    wrapped, _ = measure(value_size, gap)

    for label, lines, row_size in wrapped:
        line_h = row_size + 3
        block_h = max(line_h, len(lines) * line_h)
        text(pad, y + label_size * 0.8, label, label_size, weight="bold")
        vy = y + row_size * 0.8
        for line in lines:
            text(pad + label_col, vy, line, row_size)
            vy += line_h
        y += block_h + gap

    rule(footer_top)
    text(width / 2, footer_top + 18, IDEA_FOOTER, s.get("footer", 9),
         anchor="middle", fill="mute")
    return ops


def project_view(points, edges, view: str, width: float, height: float,
                 gutter: float = 28.0, width_label: str | None = None,
                 height_label: str | None = None) -> dict:
    """Fit one existing view's edges into a panel. No new geometry.

    Returns top-down coordinates. Dimension labels sit in the gutter
    outside the linework.
    """
    pts = [p for p in points if getattr(p, "view", None) == view]
    eds = [e for e in edges if getattr(e, "view", None) == view]
    if len(pts) < 2 or width <= 0 or height <= 0:
        return {"lines": [], "labels": [], "empty": True}
    by_name = {p.name: p for p in pts}
    xs = [p.x for p in pts]
    ys = [p.y for p in pts]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    span_x = max(maxx - minx, 0.01)
    span_y = max(maxy - miny, 0.01)
    inner_w = max(8.0, width - gutter * 2)
    inner_h = max(8.0, height - gutter * 2)
    scale = min(inner_w / span_x, inner_h / span_y)
    drawn_w = span_x * scale
    drawn_h = span_y * scale
    ox = gutter + (inner_w - drawn_w) / 2
    oy = gutter + (inner_h - drawn_h) / 2

    def map_pt(p):
        sx = ox + (p.x - minx) * scale
        # Top-down: larger model y is higher on the sheet.
        sy = oy + (maxy - p.y) * scale
        return sx, sy

    lines = []
    for edge in eds:
        a = by_name.get(edge.frm)
        b = by_name.get(edge.to)
        if a is None or b is None or edge.frm == edge.to:
            continue
        x1, y1 = map_pt(a)
        x2, y2 = map_pt(b)
        if abs(x1 - x2) < 0.2 and abs(y1 - y2) < 0.2:
            continue
        lines.append({
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "weight": getattr(edge, "weight", "outline") or "outline",
        })
    # Caller supplies the quote dims. The point bbox is not a spec
    # dimension (some families pad the view), so it is not labeled.
    labels = []
    if width_label:
        labels.append({
            "text": width_label,
            "x": ox + drawn_w / 2,
            "y": min(height - 12, oy + drawn_h + 14),
            "anchor": "middle",
        })
    if height_label:
        labels.append({
            "text": height_label,
            "x": 8,
            "y": oy + drawn_h / 2,
            "anchor": "start",
        })
    return {"lines": lines, "labels": labels, "empty": False}

