"""Max default drawing / field-measurement sheet chrome.

Locked 2026-09-25 to the McLean Whittington REV A golden:
  reference/max-golden/McLean_Whittington_REV_A.pdf
  md5 f882144aefc03745533fdaae95ea86b4

Marleys empire-house-format pack is NOT golden (see
reference/empire-house-format/NOT_GOLDEN.md).

This module is the single source for default chrome strings and a
reportlab chrome proof page so Max drawing paths (and operators) can
verify header/footer language without regenerating the full 11-sheet set.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Tuple

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, Color

# ── Geometry (landscape letter, points) ─────────────────────────────
PW, PH = 792.0, 612.0
HDR_H, FTR_H = 44.0, 26.0

# ── Palette (exact McLean) ──────────────────────────────────────────
PAPER = HexColor("#f7f3ea")
INK = HexColor("#20241f")
GOLD = HexColor("#b8912f")
BAND = HexColor("#16191c")
HAIR = HexColor("#cdc4b0")
MUTE = HexColor("#7b7466")
CREAM_TEXT = HexColor("#f4efe2")
MUTE_BAND = HexColor("#a49b88")

# ── Default brand language (Max drawing / client sheets) ────────────
LETTERHEAD = "NELMA'S WORKROOM"
POWERED_BY = "POWERED BY EMPIRE WORKROOM"
LOCALE = "HYATTSVILLE MD"
STATUS_DISCUSSION = "FOR DISCUSSION - NOT FOR CONSTRUCTION"
PDF_AUTHOR = "Nelma's Workroom - Powered by Empire Workroom"
PDF_CREATOR = "Nelma's Workroom"

# Estimate path: same brand words, different layout (portrait). Do not
# invent a field-measurement layout for estimates.
ESTIMATE_COMPANY = "NELMA'S WORKROOM"
ESTIMATE_TAGLINE = "POWERED BY EMPIRE WORKROOM · CUSTOM UPHOLSTERY & FABRICATION"
ESTIMATE_ADDRESS = "5124 Frolich Ln, Hyattsville, MD 20781"

GOLDEN_PDF_REL = "reference/max-golden/McLean_Whittington_REV_A.pdf"
GOLDEN_MD5 = "f882144aefc03745533fdaae95ea86b4"
GOLDEN_DOC = "reference/max-golden/GOLDEN.md"

_FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
_FONTS_READY = False


def brand_footer(letterhead: str = LETTERHEAD,
                 powered_by: str = POWERED_BY,
                 locale: str = LOCALE) -> str:
    """Footer left zone — matches McLean golden string."""
    return f"{letterhead}  ·  {powered_by}  ·  {locale}"


def project_line(client: str, project: str) -> str:
    """Header project line under POWERED BY (CLIENT · PROJECT)."""
    return f"{(client or '').strip().upper()}  ·  {(project or '').strip().upper()}"


def sheet_stamp(sheet_no: int, total: int, rev: str, date: str) -> str:
    return f"SHEET {sheet_no:02d} OF {total:02d}   ·   REV {rev}   ·   {date}"


def sheet_footer_right(sheet_no: int, total: int) -> str:
    return f"SHEET {sheet_no} / {total}"


def _ensure_fonts() -> Tuple[str, str, str, str]:
    global _FONTS_READY
    serif_b = "DejaVuSerif-Bold"
    mono = "DejaVuSansMono"
    mono_b = "DejaVuSansMono-Bold"
    sans_i = "DejaVuSans-Oblique"
    if not _FONTS_READY:
        mapping = {
            serif_b: "DejaVuSerif-Bold.ttf",
            mono: "DejaVuSansMono.ttf",
            mono_b: "DejaVuSansMono-Bold.ttf",
            sans_i: "DejaVuSans-Oblique.ttf",
        }
        for name, fn in mapping.items():
            path = _FONT_DIR / fn
            if path.is_file():
                try:
                    pdfmetrics.registerFont(TTFont(name, str(path)))
                except Exception:
                    pass
        _FONTS_READY = True
    # Fallbacks if TTF missing
    def pick(preferred: str, fallback: str) -> str:
        try:
            pdfmetrics.getFont(preferred)
            return preferred
        except Exception:
            return fallback
    return (
        pick(serif_b, "Times-Bold"),
        pick(mono, "Courier"),
        pick(mono_b, "Courier-Bold"),
        pick(sans_i, "Helvetica-Oblique"),
    )


def _ls_draw(c: canvas.Canvas, x: float, y: float, text: str,
             font: str, size: float, color: Color,
             tracking: float = 0.0, align: str = "left") -> float:
    """Draw letterspaced text; return advance width."""
    c.setFont(font, size)
    c.setFillColor(color)
    text = text or ""
    widths = [c.stringWidth(ch, font, size) + tracking for ch in text]
    if widths:
        widths[-1] -= tracking
    total = sum(widths)
    if align == "right":
        cursor = x - total
    elif align == "center":
        cursor = x - total / 2
    else:
        cursor = x
    for ch, w in zip(text, widths):
        c.drawString(cursor, y, ch)
        cursor += w
    return total


def render_chrome_bands(
    c: canvas.Canvas,
    *,
    sheet_no: int = 1,
    total: int = 1,
    right_title: str = "CHROME PROOF",
    letterhead: str = LETTERHEAD,
    powered_by: str = POWERED_BY,
    client: str = "WHITTINGTON DESIGN",
    project: str = "MCLEAN",
    rev: str = "A",
    date: str = "19 AUG 2026",
    status: str = STATUS_DISCUSSION,
    locale: str = LOCALE,
) -> None:
    """Paint McLean-matching header + footer on the current page."""
    serif_b, mono, mono_b, sans_i = _ensure_fonts()

    # Paper
    c.setFillColor(PAPER)
    c.rect(0, 0, PW, PH, fill=1, stroke=0)

    # Header band (top) — reportlab Y is bottom-up; band sits at PH-HDR_H
    hy = PH - HDR_H
    c.setFillColor(BAND)
    c.rect(0, hy, PW, HDR_H, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.rect(0, hy - 2.2, PW, 2.2, fill=1, stroke=0)

    # Letterhead
    lh_w = _ls_draw(c, 30, hy + 17, letterhead, serif_b, 14.0, CREAM_TEXT, tracking=1.6)
    dv = 30 + lh_w + 14
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.2)
    c.line(dv, hy + 11, dv, hy + 33)

    _ls_draw(c, dv + 12, hy + 20.5 - 6.2, powered_by, mono_b, 6.2, GOLD, tracking=1.5)
    _ls_draw(
        c, dv + 12, hy + 31.5 - 6.0,
        project_line(client, project), mono, 6.0, MUTE_BAND, tracking=0.8,
    )

    _ls_draw(
        c, PW - 30, hy + 20.5 - 8.4,
        right_title.upper(), mono_b, 8.4, CREAM_TEXT, tracking=1.2, align="right",
    )
    # McLean places SHEET stamp on the UPPER right line (y≈32.5 in SVG TL coords)
    # SVG y is top-down; reportlab is bottom-up. SVG y=32.5 → from top → PH-32.5
    # but baseline sits near that. Mirror reference: stamp near top of band.
    _ls_draw(
        c, PW - 30, hy + 32.5 - 6.2,
        sheet_stamp(sheet_no, total, rev, date),
        mono, 6.2, MUTE_BAND, tracking=0.9, align="right",
    )

    # Footer
    c.setFillColor(BAND)
    c.rect(0, 0, PW, FTR_H, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.rect(0, FTR_H, PW, 1.6, fill=1, stroke=0)

    foot = brand_footer(letterhead, powered_by, locale)
    _ls_draw(c, 30, 10.3, foot, mono, 5.2, MUTE_BAND, tracking=0.35)
    _ls_draw(c, PW / 2, 10.1, status, mono_b, 6.4, GOLD, tracking=1.4, align="center")
    _ls_draw(
        c, PW - 30, 10.1,
        sheet_footer_right(sheet_no, total),
        mono_b, 6.4, CREAM_TEXT, tracking=1.0, align="right",
    )


def write_chrome_proof(
    out_path: str | Path,
    *,
    right_title: str = "CHROME PROOF",
    client: str = "WHITTINGTON DESIGN",
    project: str = "MCLEAN",
) -> Path:
    """Write a one-page landscape proof matching McLean header/footer language."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    serif_b, mono, mono_b, sans_i = _ensure_fonts()

    c = canvas.Canvas(str(out), pagesize=(PW, PH))
    c.setTitle("Max Golden Chrome Proof — McLean Whittington")
    c.setAuthor(PDF_AUTHOR)
    c.setCreator(PDF_CREATOR)
    c.setSubject(
        "Chrome proof — NELMA'S WORKROOM / POWERED BY EMPIRE WORKROOM — "
        "FOR DISCUSSION - NOT FOR CONSTRUCTION"
    )

    render_chrome_bands(
        c,
        sheet_no=2,
        total=11,
        right_title=right_title,
        client=client,
        project=project,
        rev="A",
        date="19 AUG 2026",
    )

    # Body sample — room title + LAYOUT MATH callout language
    c.setFillColor(INK)
    c.setFont(serif_b, 15)
    c.drawString(30, PH - 66, "FORMAL DINING")
    c.setFillColor(MUTE)
    c.setFont(sans_i, 8.2)
    c.drawString(
        30, PH - 84,
        'One opening - 99" wide - 105¾" floor to ceiling - 6½" header',
    )

    # Viewport frame
    x0, y0, x1, y1 = 30.0, 100.0, 762.0, PH - 226.0  # ~386 tall in SVG
    # McLean VP is (30,100)-(762,386) in top-down SVG → convert
    # SVG y=100 → PH-100=512 top of content? Wait: SVG origin top-left.
    # Viewport top at SVG y=100, bottom at 386 → height 286? Actually
    # room drawing area VP = (30, 100, 762, 386) as x0,y0,x1,y1 with
    # y0 top? Looking at room_sheet: RECT(x0,y0,x1-x0,y1-y0) with
    # y increasing downward in SVG. So top=100, bottom=386.
    # reportlab: top = PH-100 = 512, bottom = PH-386 = 226, height = 286
    top = PH - 100
    bot = PH - 386
    c.setStrokeColor(HAIR)
    c.setFillColor(HexColor("#fbf8f1"))
    c.setLineWidth(1.0)
    c.rect(30, bot, 732, top - bot, fill=1, stroke=1)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.6)
    for ax, ay, sx, sy in (
        (30, bot, 16, 16),
        (762, top, -16, -16),
    ):
        c.line(ax, ay, ax + sx, ay)
        c.line(ax, ay, ax, ay + sy)

    # LAYOUT MATH strip
    c.setFillColor(GOLD)
    c.setFont(mono_b, 7.2)
    c.drawString(40, bot + 28, "LAYOUT MATH")
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.9)
    c.line(40, bot + 24, 140, bot + 24)
    c.setFillColor(INK)
    c.setFont(mono, 7.0)
    c.drawString(
        40, bot + 12,
        'HEAD AT 99¼" AFF = 105¾" CEILING less 6½" HEADER - DERIVED, CONFIRM',
    )

    # Legend language
    c.setFillColor(GOLD)
    c.setFont(mono_b, 7.0)
    c.drawString(30, 78, "FIELD CHECK · BEFORE FABRICATION")
    c.setFillColor(INK)
    c.setFont(mono, 6.6)
    c.drawString(
        30, 64,
        "Gold dashed edge = head or sill not field-tagged · gold dim = closure open",
    )
    c.setFillColor(MUTE)
    c.setFont(mono, 6.0)
    c.drawString(
        30, 50,
        f"Golden: {GOLDEN_PDF_REL}  ·  md5 {GOLDEN_MD5}  ·  NOT Marleys house pack",
    )

    c.showPage()
    c.save()
    return out


def main(argv: Optional[list] = None) -> int:
    p = argparse.ArgumentParser(description="Emit Max McLean golden chrome proof PDF")
    p.add_argument(
        "--out",
        default=str(Path.home() / "Desktop" / "Max_Golden_Chrome_Proof.pdf"),
        help="Output path",
    )
    args = p.parse_args(argv)
    path = write_chrome_proof(args.out)
    print(f"wrote {path} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
