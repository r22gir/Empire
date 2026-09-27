"""Shared Empire client-sheet chrome.

Workroom estimates already paint this language in ReportLab
(``max_sheet_chrome``). WoodCraft quotes and Drawing Studio sheets
join the same black / gold letterhead, type ladder, and page margin
so a client does not receive three unrelated companies.

Page margin is large enough that a full letterhead never sits on the
trim. Drawing SVGs keep their viewBox; the PDF wrapper scales that
viewBox into the content box instead of letting an intrinsic pixel
width overflow the sheet and clip the header.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass

from app.services.drawing.inches import format_inches

# Match max_sheet_chrome palette. Hex strings stay here so WeasyPrint
# and SVG paths do not import ReportLab.
BAND = "#16191c"
GOLD = "#b8912f"
PAPER = "#f7f3ea"
INK = "#20241f"
CREAM = "#f4efe2"
MUTE_BAND = "#a49b88"
HAIR = "#cdc4b0"

# Letter landscape / portrait. 0.45in keeps header glyphs off the edge
# even when a renderer adds its own stroke.
PAGE_MARGIN_IN = 0.45
MIN_HEADER_INSET_UU = 36.0

LETTERHEAD_WC = "WOODCRAFT BY EMPIRE"
POWERED_BY = "POWERED BY EMPIRE WORKROOM"
LOCALE = "HYATTSVILLE MD"
DOC_KIND_ESTIMATE = "ESTIMATE"


def format_length_for_sheet(value, unit: str = "in") -> str:
    """Shop length for a client sheet.

    Inches print as whole inches or hyphen fractions (``72"``,
    ``14-1/2"``). Other units keep their unit word and drop a trailing
    ``.0``.
    """
    unit_norm = (unit or "in").strip().lower()
    if unit_norm in {"in", "inch", "inches", '"', "''"}:
        return format_inches(float(value))
    number = float(value)
    shown = str(int(number)) if number == int(number) else f"{number:g}"
    label = "in" if unit_norm in {"", "in"} else unit_norm
    return f"{shown} {label}"


@dataclass(frozen=True)
class SheetMeta:
    company: str
    doc_id: str
    doc_kind: str = DOC_KIND_ESTIMATE
    powered_by: str = POWERED_BY
    rev: str = "A"
    date_label: str = ""
    valid_label: str = ""
    contact_lines: tuple[str, ...] = ()
    locale: str = LOCALE
    orientation: str = "landscape"
    sheet_no: int = 1
    sheet_total: int = 1


def sheet_stamp(meta: SheetMeta) -> str:
    parts = [meta.doc_id, f"REV {meta.rev}"]
    if meta.date_label:
        parts.append(meta.date_label)
    parts.append(f"SHEET {meta.sheet_no:02d} OF {meta.sheet_total:02d}")
    return "  ·  ".join(p for p in parts if p)


def client_page_css(orientation: str = "landscape") -> str:
    orient = "portrait" if orientation == "portrait" else "landscape"
    return f"""
    @page {{ size: letter {orient}; margin: {PAGE_MARGIN_IN}in; }}
    html, body {{
      margin: 0; padding: 0;
      background: {PAPER}; color: {INK};
      font-family: Helvetica, Arial, sans-serif;
      font-size: 11px; line-height: 1.45;
    }}
    .empire-band {{
      background: {BAND}; color: {CREAM};
      display: flex; justify-content: space-between; align-items: flex-start;
      padding: 12px 18px 10px;
    }}
    .empire-letterhead {{
      font-size: 15px; font-weight: 700; letter-spacing: 0.14em;
    }}
    .empire-powered {{
      color: {GOLD}; font-size: 8px; font-weight: 700;
      letter-spacing: 0.16em; margin-top: 4px;
    }}
    .empire-kind {{
      text-align: right; font-size: 12px; font-weight: 700; letter-spacing: 0.18em;
    }}
    .empire-stamp {{
      text-align: right; color: {MUTE_BAND}; font-size: 8px;
      letter-spacing: 0.08em; margin-top: 4px;
    }}
    .empire-rule {{ height: 3px; background: {GOLD}; margin: 0 0 14px; }}
    .empire-contact {{
      color: #5c564c; font-size: 10px; margin: 0 0 12px; line-height: 1.5;
    }}
    .empire-footer {{
      margin-top: 22px; background: {BAND}; color: {MUTE_BAND};
      display: flex; justify-content: space-between; gap: 12px;
      padding: 8px 16px; font-size: 8px; letter-spacing: 0.08em;
    }}
    .empire-footer .status {{ color: {GOLD}; font-weight: 700; }}
    table {{ width: 100%; border-collapse: collapse; margin-bottom: 8px; }}
    th {{
      background: {BAND}; color: {CREAM};
      padding: 7px 6px; text-align: left;
      font-size: 9px; text-transform: uppercase; letter-spacing: 0.06em;
    }}
    """


def _e(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def client_document_html(body_html: str, meta: SheetMeta) -> str:
    """Full HTML document: McLean band, safe margin, then the caller body."""
    contact = "<br>".join(_e(line) for line in meta.contact_lines if str(line).strip())
    contact_html = f'<div class="empire-contact">{contact}</div>' if contact else ""
    valid = f"  ·  Valid { _e(meta.valid_label) }" if meta.valid_label else ""
    footer_left = f"{_e(meta.company)}  ·  {_e(meta.powered_by)}  ·  {_e(meta.locale)}"
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{_e(meta.doc_id)}</title>
<style>{client_page_css(meta.orientation)}</style>
</head><body>
<header class="empire-band">
  <div>
    <div class="empire-letterhead">{_e(meta.company)}</div>
    <div class="empire-powered">{_e(meta.powered_by)}</div>
  </div>
  <div>
    <div class="empire-kind">{_e(meta.doc_kind)}</div>
    <div class="empire-stamp">{_e(sheet_stamp(meta))}{valid}</div>
  </div>
</header>
<div class="empire-rule"></div>
{contact_html}
{body_html}
<footer class="empire-footer">
  <div>{footer_left}</div>
  <div class="status">{_e(meta.doc_kind)}  ·  {_e(meta.doc_id)}</div>
  <div>SHEET {meta.sheet_no} / {meta.sheet_total}</div>
</footer>
</body></html>"""


def _svg_font_size(text: str, max_width: float, size: float, minimum: float = 9.0) -> float:
    """Shrink a label so it stays inside max_width. Approximate Helvetica."""
    if not text or max_width <= 0:
        return size
    width = len(text) * size * 0.56
    if width <= max_width:
        return size
    fitted = max_width / (len(text) * 0.56)
    return max(minimum, fitted)


def svg_sheet_chrome(
    width: float,
    height: float,
    *,
    company: str,
    subtitle: str,
    right_title: str,
    right_sub: str = "",
    sheet_no: int = 1,
    sheet_total: int = 1,
    rev: str = "A",
) -> list[str]:
    """McLean header and footer bands inside an SVG viewBox.

    Text is inset by ``MIN_HEADER_INSET_UU`` and sized to the half of
    the sheet it owns, so a long style name cannot run off the right
    edge of the drawing.
    """
    inset = MIN_HEADER_INSET_UU
    header_h = 70.0
    footer_h = 26.0
    company_s = _svg_font_size(company, width * 0.46, 16.0)
    title_s = _svg_font_size(right_title, width * 0.46, 14.0)
    stamp = f"SHEET {sheet_no:02d} OF {sheet_total:02d}  ·  REV {rev}"
    if right_sub:
        stamp = f"{right_sub}  ·  {stamp}"
    sub_s = _svg_font_size(stamp, width * 0.5, 10.0, minimum=8.0)
    foot = f"{company}  ·  {POWERED_BY}  ·  {LOCALE}"
    foot_s = _svg_font_size(foot, width * 0.62, 8.0, minimum=7.0)

    def text(x, y, value, size, anchor, fill, weight="700") -> str:
        return (
            f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
            f'font-size="{size:.1f}" font-weight="{weight}" fill="{fill}">'
            f'{_e(value)}</text>'
        )

    return [
        f'<rect x="0" y="0" width="{width:.1f}" height="{height:.1f}" fill="{PAPER}"/>',
        f'<rect x="0" y="0" width="{width:.1f}" height="{header_h:.1f}" fill="{BAND}"/>',
        f'<rect x="0" y="{header_h:.1f}" width="{width:.1f}" height="3" fill="{GOLD}"/>',
        text(inset, 30, company, company_s, "start", CREAM, "800"),
        text(inset, 52, subtitle, 11, "start", GOLD, "700"),
        text(width - inset, 30, right_title, title_s, "end", CREAM, "800"),
        text(width - inset, 52, stamp, sub_s, "end", MUTE_BAND, "600"),
        f'<rect x="0" y="{height - footer_h:.1f}" width="{width:.1f}" height="{footer_h:.1f}" fill="{BAND}"/>',
        f'<rect x="0" y="{height - footer_h:.1f}" width="{width:.1f}" height="2" fill="{GOLD}"/>',
        text(inset, height - 9, foot, foot_s, "start", MUTE_BAND, "500"),
        text(width - inset, height - 9, f"SHEET {sheet_no} / {sheet_total}", 9, "end", CREAM, "700"),
    ]


_SVG_OPEN = re.compile(r"<svg\b[^>]*>", re.IGNORECASE)
_SIZE_ATTR = re.compile(r"""\s(?:width|height)\s*=\s*(?:"[^"]*"|'[^']*')""", re.IGNORECASE)


def prepare_svg_for_page(svg: str) -> str:
    """Drop intrinsic width/height so the viewBox scales into the page.

    A 1320px-wide SVG is wider than letter landscape. WeasyPrint honors
    that pixel size and the page clips both headers. Keeping the viewBox
    and sizing the element with CSS fits the whole sheet, including the
    letterhead.
    """
    def _open(match: re.Match) -> str:
        return _SIZE_ATTR.sub("", match.group(0))

    return _SVG_OPEN.sub(_open, svg, count=1)


def drawings_pdf_html(drawings: list[dict]) -> str:
    """Landscape letter HTML. Each drawing is one page, scaled to fit."""
    pages = []
    for drawing in drawings:
        svg = prepare_svg_for_page(drawing.get("svg") or "")
        pages.append(f'<div class="pg">{svg}</div>')
    body = "".join(pages)
    return (
        '<!DOCTYPE html><html><head><meta charset="utf-8"><style>'
        f'@page{{size:letter landscape;margin:{PAGE_MARGIN_IN}in}}'
        f'html,body{{margin:0;padding:0;background:{PAPER}}}'
        '.pg{page-break-after:always}'
        '.pg:last-child{page-break-after:auto}'
        '.pg svg{width:100%;height:auto;display:block}'
        f'</style></head><body>{body}</body></html>'
    )
