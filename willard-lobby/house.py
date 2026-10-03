"""McLean house chrome for Empire Workroom / Nelma's Workroom sheets.

Cream paper, ink, gold. DRAFT on every page. Inch sizes stay fractions.
This is local house format — not the Max live engine.
"""

from __future__ import annotations

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

PAGE_W, PAGE_H = letter

CREAM = HexColor("#F4EFE4")
CREAM_DEEP = HexColor("#E9E0D0")
INK = HexColor("#1C1915")
INK2 = HexColor("#3F382F")
MUTED = HexColor("#6E6458")
GOLD = HexColor("#B08D3E")
GOLD_DEEP = HexColor("#8C6A2A")
GOLD_PALE = HexColor("#E7D7B0")
WHITE = HexColor("#FBF7F0")
RULE = HexColor("#C4A15A")

PANEL = HexColor("#7A6248")
PANEL_LINE = HexColor("#4E3B2A")
SHEER = HexColor("#F7F3EA")
SHEER_LINE = HexColor("#E0D5C4")
GLASS = HexColor("#E6EAEE")
VOID = HexColor("#2A3036")
SWAG = HexColor("#8A7052")
JABOT = HexColor("#6B533C")
WALL = HexColor("#E4DCCE")

FONT_DIR = "/usr/share/fonts/truetype/liberation"
pdfmetrics.registerFont(TTFont("Serif", f"{FONT_DIR}/LiberationSerif-Regular.ttf"))
pdfmetrics.registerFont(TTFont("Serif-Bold", f"{FONT_DIR}/LiberationSerif-Bold.ttf"))
pdfmetrics.registerFont(TTFont("Serif-Italic", f"{FONT_DIR}/LiberationSerif-Italic.ttf"))
pdfmetrics.registerFont(TTFont("Serif-BoldItalic", f"{FONT_DIR}/LiberationSerif-BoldItalic.ttf"))
pdfmetrics.registerFont(TTFont("Sans", f"{FONT_DIR}/LiberationSans-Regular.ttf"))
pdfmetrics.registerFont(TTFont("Sans-Bold", f"{FONT_DIR}/LiberationSans-Bold.ttf"))
registerFontFamily(
    "Serif",
    normal="Serif",
    bold="Serif-Bold",
    italic="Serif-Italic",
    boldItalic="Serif-BoldItalic",
)
registerFontFamily("Sans", normal="Sans", bold="Sans-Bold", italic="Sans", boldItalic="Sans-Bold")

ML = 32
MR = 32
CONTENT_LEFT = 32
CONTENT_RIGHT = PAGE_W - 32
CONTENT_W = CONTENT_RIGHT - CONTENT_LEFT
CONTENT_TOP = 700
CONTENT_BOTTOM = 46


def money(amount: float) -> str:
    return f"${amount:,.2f}"


def style(name, font, size, leading, color=INK, align=TA_LEFT, tracking=0):
    return ParagraphStyle(
        name,
        fontName=font,
        fontSize=size,
        leading=leading,
        textColor=color,
        alignment=align,
        encoding="utf-8",
    )


S_BODY = style("body", "Serif", 8.5, 11)
S_SMALL = style("small", "Serif", 7.5, 9.5)
S_TINY = style("tiny", "Sans", 7, 9, INK)
S_TINY_CREAM = style("tinycream", "Sans", 7, 9, CREAM)
S_LABEL = style("label", "Sans", 7, 9, GOLD_DEEP)
S_CENTER = style("center", "Serif", 8, 10, INK, TA_CENTER)
S_BOLD = style("bold", "Serif-Bold", 8.5, 11)


def draw_para(c, text, x, y, w, st=S_BODY):
    """Draw a paragraph with its top at y. Return the baseline y under it."""
    p = Paragraph(text, st)
    _, h = p.wrap(w, 800)
    p.drawOn(c, x, y - h)
    return y - h


def paint_page(c, kind: str, section: str, page: int, total: int):
    """Cream sheet, gold frame, letterhead, DRAFT chip, footer. Returns nothing."""
    c.setFillColor(CREAM)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    c.saveState()
    c.setFillColor(Color(0.55, 0.42, 0.18, alpha=0.10))
    c.translate(PAGE_W / 2, PAGE_H / 2)
    c.rotate(32)
    c.setFont("Serif-Bold", 86)
    c.drawCentredString(0, 0, "DRAFT")
    c.restoreState()

    c.setStrokeColor(GOLD)
    c.setLineWidth(1.15)
    c.rect(14, 14, PAGE_W - 28, PAGE_H - 28, fill=0, stroke=1)
    c.setLineWidth(0.35)
    c.rect(17, 17, PAGE_W - 34, PAGE_H - 34, fill=0, stroke=1)

    # Monogram
    c.setStrokeColor(GOLD_DEEP)
    c.setLineWidth(0.8)
    c.setFillColor(CREAM)
    c.rect(CONTENT_LEFT, 746, 26, 26, fill=1, stroke=1)
    c.setFillColor(INK)
    c.setFont("Serif-Bold", 8)
    c.drawCentredString(CONTENT_LEFT + 13, 755, "EW")

    c.setFillColor(INK)
    c.setFont("Serif-Bold", 13)
    c.drawString(CONTENT_LEFT + 32, 760, "EMPIRE WORKROOM")
    c.setFillColor(GOLD_DEEP)
    c.setFont("Sans", 7.5)
    c.drawString(CONTENT_LEFT + 32, 748, "NELMA'S WORKROOM  ·  MCLEAN HOUSE FORMAT")

    c.setFillColor(INK2)
    c.setFont("Sans", 7)
    right_lines = [
        "5124 Frolich Ln  ·  Hyattsville MD 20781",
        "Nelma Lucia  ·  nelmalucia@msn.com  ·  703.623.9203",
        "Powered by Empire Workroom",
    ]
    yy = 764
    for line in right_lines:
        c.drawRightString(CONTENT_RIGHT, yy, line)
        yy -= 10

    c.setStrokeColor(GOLD)
    c.setLineWidth(0.9)
    c.line(CONTENT_LEFT, 738, CONTENT_RIGHT, 738)
    c.setLineWidth(0.3)
    c.line(CONTENT_LEFT, 735, CONTENT_RIGHT, 735)

    c.setFillColor(INK)
    c.setFont("Sans", 8)
    c.drawString(CONTENT_LEFT, 720, kind.upper())
    c.setFillColor(MUTED)
    c.setFont("Sans", 8)
    c.drawString(CONTENT_LEFT + c.stringWidth(kind.upper(), "Sans", 8) + 8, 720, "·   " + section)

    chip = "DRAFT"
    c.setFont("Sans-Bold", 8)
    tw = c.stringWidth(chip, "Sans-Bold", 8)
    chip_w = tw + 14
    c.setFillColor(GOLD)
    c.rect(CONTENT_RIGHT - chip_w - 54, 714, chip_w, 13, fill=1, stroke=0)
    c.setFillColor(INK)
    c.drawString(CONTENT_RIGHT - chip_w - 47, 717, chip)
    c.setFillColor(MUTED)
    c.setFont("Sans", 8)
    c.drawRightString(CONTENT_RIGHT, 717, f"{page}  /  {total}")

    c.setStrokeColor(GOLD)
    c.setLineWidth(0.4)
    c.line(CONTENT_LEFT, 40, CONTENT_RIGHT, 40)
    c.setFillColor(INK2)
    c.setFont("Sans", 6.5)
    c.drawString(
        CONTENT_LEFT,
        28,
        "DRAFT  —  NOT FOR CLIENT  ·  NUMBERS NOT LOCKED  ·  DO NOT EMAIL",
    )
    c.setFillColor(MUTED)
    c.drawRightString(CONTENT_RIGHT, 28, "Schematic intent  ·  not a photoreal render")


def section_label(c, x, y, text):
    c.setFillColor(GOLD_DEEP)
    c.setFont("Sans", 7.5)
    c.drawString(x, y, text.upper())
    tw = c.stringWidth(text.upper(), "Sans", 7.5)
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.6)
    c.line(x, y - 3, x + max(tw, 36), y - 3)


def hairline(c, x, y, w):
    c.setStrokeColor(RULE)
    c.setLineWidth(0.4)
    c.line(x, y, x + w, y)


def draw_table(c, data, col_widths, x, y, font_size=7):
    """data is a list of lists of strings or Paragraphs. Top of table is y. Returns y under the table."""
    wrapped = []
    for r, row in enumerate(data):
        new = []
        for cell in row:
            if isinstance(cell, Paragraph):
                new.append(cell)
            else:
                st = S_TINY_CREAM if r == 0 else S_TINY
                if r == 0:
                    st = ParagraphStyle(
                        "th",
                        fontName="Sans",
                        fontSize=font_size,
                        leading=font_size + 2,
                        textColor=CREAM,
                    )
                else:
                    st = ParagraphStyle(
                        "td",
                        fontName="Serif",
                        fontSize=font_size,
                        leading=font_size + 2.2,
                        textColor=INK,
                    )
                new.append(Paragraph(str(cell), st))
        wrapped.append(new)
    table = Table(wrapped, colWidths=col_widths, repeatRows=0)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), INK),
                ("TEXTCOLOR", (0, 0), (-1, 0), CREAM),
                ("BACKGROUND", (0, 1), (-1, -1), WHITE),
                ("GRID", (0, 0), (-1, -1), 0.3, GOLD),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    _, h = table.wrap(sum(col_widths), 700)
    table.drawOn(c, x, y - h)
    return y - h


def dim_h(c, x1, x2, y, label):
    c.setStrokeColor(INK)
    c.setFillColor(INK)
    c.setLineWidth(0.55)
    c.line(x1, y, x2, y)
    c.line(x1, y - 3, x1, y + 3)
    c.line(x2, y - 3, x2, y + 3)
    c.setFont("Sans", 7.5)
    tw = c.stringWidth(label, "Sans", 7.5)
    mid = (x1 + x2) / 2.0
    c.setFillColor(CREAM)
    c.rect(mid - tw / 2 - 2, y - 3, tw + 4, 9, fill=1, stroke=0)
    c.setFillColor(INK)
    c.drawCentredString(mid, y - 1.5, label)


def dim_v(c, x, y1, y2, label):
    c.setStrokeColor(INK)
    c.setLineWidth(0.55)
    c.line(x, y1, x, y2)
    c.line(x - 3, y1, x + 3, y1)
    c.line(x - 3, y2, x + 3, y2)
    c.saveState()
    c.translate(x - 8, (y1 + y2) / 2.0)
    c.rotate(90)
    c.setFillColor(INK)
    c.setFont("Sans", 7.5)
    c.drawCentredString(0, 0, label)
    c.restoreState()


def extension(c, x1, y1, x2, y2):
    c.saveState()
    c.setStrokeColor(MUTED)
    c.setLineWidth(0.3)
    c.setDash(1, 1.2)
    c.line(x1, y1, x2, y2)
    c.restoreState()
