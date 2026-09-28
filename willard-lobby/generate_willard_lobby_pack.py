#!/usr/bin/env python3
"""Regenerate the Willard lobby McLean house pack.

Writes two DRAFT PDFs and one PNG preview per page:

  output/Willard_Lobby_Existing_vs_Proposed_DRAFT.pdf
  output/Willard_Lobby_Installation_Drawings_DRAFT.pdf
  output/previews/*.png

Local ReportLab house format. Not the Max live engine.
Does not send email.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pymupdf
from PIL import Image
from reportlab.pdfgen import canvas

from elevations import (
    draw_lincoln_window,
    draw_lobby_pair,
    draw_office_opening,
    draw_passway,
)
from house import (
    CONTENT_LEFT,
    CONTENT_RIGHT,
    CONTENT_W,
    CREAM,
    CREAM_DEEP,
    GLASS,
    GOLD,
    GOLD_DEEP,
    GOLD_PALE,
    INK,
    INK2,
    MUTED,
    PAGE_H,
    PAGE_W,
    PANEL,
    S_SMALL,
    SHEER,
    VOID,
    WHITE,
    draw_para,
    draw_table,
    money,
    paint_page,
    section_label,
)

ASSETS = ROOT / "assets"
OUT = ROOT / "output"
PREVIEWS = OUT / "previews"

# Est 838 submitted figures. Printed as submitted. Not a new price lock.
EST_TOTAL = 4824.09
EST_DEPOSIT = 2412.05
LOB = 1074.75
LIN1 = 1210.02
LIN2 = 1464.57
ADD_TOTAL = 5266.34
ADD_DEPOSIT = 2633.17
COMBINED = 10090.43
BALLPARK_SUM = 2531.00
INV_SUM = 2735.34
HOLDBACK_CREDIT = 143.76


def photo(name: str) -> Path:
    path = ASSETS / name
    if not path.exists():
        raise SystemExit(f"Missing asset {path}")
    return path


def draw_photo(c, path: Path, x, y, w, h):
    im = Image.open(path)
    iw, ih = im.size
    scale = min(w / iw, h / ih)
    dw, dh = iw * scale, ih * scale
    c.setFillColor(CREAM_DEEP)
    c.rect(x, y, w, h, fill=1, stroke=0)
    c.drawImage(
        str(path),
        x + (w - dw) / 2.0,
        y + (h - dh) / 2.0,
        dw,
        dh,
        preserveAspectRatio=True,
        mask="auto",
    )
    c.setStrokeColor(INK)
    c.setLineWidth(0.7)
    c.rect(x, y, w, h, fill=0, stroke=1)


def swatch(c, x, y, color, label):
    c.setFillColor(color)
    c.setStrokeColor(INK)
    c.setLineWidth(0.4)
    c.rect(x, y, 8, 8, fill=1, stroke=1)
    c.setFillColor(INK2)
    c.setFont("Sans", 6.5)
    c.drawString(x + 11, y + 1, label)


def price_box(c, x, y, w, h, kicker, amount, note):
    c.setFillColor(WHITE)
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.7)
    c.rect(x, y, w, h, fill=1, stroke=1)
    c.setFillColor(GOLD)
    c.rect(x, y + h - 4, w, 4, fill=1, stroke=0)
    c.setFillColor(GOLD_DEEP)
    c.setFont("Sans", 6.5)
    c.drawString(x + 6, y + h - 16, kicker.upper())
    c.setFillColor(INK)
    c.setFont("Serif-Bold", 11)
    c.drawString(x + 6, y + h - 32, amount)
    c.setFillColor(INK2)
    c.setFont("Serif", 7)
    # wrap note roughly
    words = note.split()
    line = ""
    yy = y + h - 46
    for word in words:
        trial = (line + " " + word).strip()
        if c.stringWidth(trial, "Serif", 7) > w - 12:
            c.drawString(x + 6, yy, line)
            yy -= 9
            line = word
        else:
            line = trial
    if line and yy > y + 4:
        c.drawString(x + 6, yy, line)


def page_overview(c, page, total):
    paint_page(c, "Presentation", "Willard Lobby  ·  Existing vs Proposed", page, total)
    c.setFillColor(INK)
    c.setFont("Serif-Bold", 15)
    c.drawString(CONTENT_LEFT, 686, "Willard InterContinental  —  Lobby Soft Goods")
    c.setFillColor(INK2)
    c.setFont("Serif-Italic", 8.5)
    c.drawString(
        CONTENT_LEFT,
        672,
        "Existing vs proposed  ·  Maggie O'Neill / Mariella Cruzado  ·  Splendor Styling",
    )
    c.setFillColor(MUTED)
    c.setFont("Sans", 7.5)
    c.drawString(
        CONTENT_LEFT,
        660,
        "28 September 2026   ·   Est 838 issued 18 September 2026   ·   Addendum still DRAFT",
    )

    # Four reference crops
    y_cap = 646
    section_label(c, CONTENT_LEFT, y_cap, "Openings 1–4  ·  Mariella labeled photograph")
    names = [
        ("window_1_concierge.png", "1  ·  Concierge", "LOB-1"),
        ("window_2_reception.png", "2  ·  Reception", "LOB-2"),
        ("window_3_lincoln.png", "3  ·  Lincoln window", "LIN-1"),
        ("window_4_passway.png", "4  ·  Passway", "LIN-2"),
    ]
    gap = 8
    pw = (CONTENT_W - gap * 3) / 4
    ph = 108
    top = 628
    for i, (fn, cap, ref) in enumerate(names):
        x = CONTENT_LEFT + i * (pw + gap)
        draw_photo(c, photo(fn), x, top - ph, pw, ph)
        c.setFillColor(INK)
        c.setFont("Sans", 6.5)
        c.drawString(x, top - ph - 11, cap)
        c.setFillColor(MUTED)
        c.drawString(x + 78, top - ph - 11, ref)

    y = top - ph - 26
    section_label(c, CONTENT_LEFT, y, "Proposed scope  ·  Est 838 base plus addendum intent")
    y -= 14
    scope = [
        "<b>1 · LOB-1 Concierge.</b> Ripplefold pair, inside mount. Add a single wide swag with center tassel and bottom trim, leading-edge fringe, bullion tiebacks, and a sheer layer.",
        "<b>2 · LOB-2 Reception.</b> Same pair. Add double overlapping swags with center tassel and bottom trim, leading-edge fringe, bullion, and a sheer layer.",
        "<b>3 · LIN-1 Lincoln window.</b> Two stationary panels. Add a formal valance with tassel and trim — style not chosen — plus leading-edge fringe and bullion. No sheers.",
        "<b>4 · LIN-2 Passway.</b> Two double-sided panels. Leading-edge fringe and bullion only. No valance. No sheers.",
    ]
    for line in scope:
        y = draw_para(c, line, CONTENT_LEFT, y, CONTENT_W, S_SMALL) - 3

    y -= 6
    section_label(c, CONTENT_LEFT, y, "Field sheet vs Est 838  ·  submitted prices control")
    y -= 8
    rows = [
        ["Item", "June field sheet", "Est 838 submitted", "How this pack treats it"],
        [
            "Lobby make",
            "2 pairs @ 2W × 105\" L",
            "Each pair @ 2W × 106\" L",
            "Length not reconciled. Do not cut.",
        ],
        [
            "Lobby opening",
            "72 3/16\" W × 105 5/8\" H, one outside size",
            "Opening size not stated",
            "Same field size shown on 1 and 2.",
        ],
        [
            "Lobby yardage",
            "Main 27 yd · lining 23 yd",
            "Main 13 1/2 + 13 1/2 yd · lining 25 yd",
            "Main matches. Lining field is 2 yd less.",
        ],
        [
            "Lincoln window",
            "2 panels, non-operable, 1 1/2 W, 73\" × 125 1/2\", 12 yd with lining",
            "LIN-1 matches that make. Lining priced separate, 11 yd",
            "Match. Field yardage is one scribble.",
        ],
        [
            "Passway",
            "102 1/2\" H, double-sided, 10 rings/panel, 2 @ 3W, 20 yd",
            "LIN-2 matches. Width not on the estimate either",
            "Match. Width still not measured.",
        ],
        [
            "Inside office",
            "68 1/4\" × 104 1/4\", tracks 8 ft × 2, 72 carriers",
            "Not on Est 838",
            "Gap. Out of this lobby pack.",
        ],
    ]
    y = draw_table(c, rows, [78, 148, 156, 166], CONTENT_LEFT, y, font_size=6.5) - 8

    section_label(c, CONTENT_LEFT, y, "Money  ·  Est 838 figures as submitted  ·  addendum not locked")
    y -= 6
    bw = (CONTENT_W - 12) / 3
    bh = 62
    price_box(
        c, CONTENT_LEFT, y - bh, bw, bh,
        "Est 838 submitted",
        money(EST_TOTAL),
        "Nelma estimate 18 Sep 2026. Deposit printed " + money(EST_DEPOSIT) + ".",
    )
    price_box(
        c, CONTENT_LEFT + bw + 6, y - bh, bw, bh,
        "Addendum lines · draft",
        money(ADD_TOTAL),
        "BALLPARK " + money(BALLPARK_SUM) + " · INV 909 anchor " + money(INV_SUM) + ".",
    )
    price_box(
        c, CONTENT_LEFT + (bw + 6) * 2, y - bh, bw, bh,
        "Combined if approved",
        money(COMBINED),
        "Not a client total. 50% of addendum lines " + money(ADD_DEPOSIT) + " is draft.",
    )
    y = y - bh - 12
    y = draw_para(
        c,
        "Fabric scribbles on the June 9 sheet — Madalyn 30.50 and 49.95, Holloway 15.40 and 29.95 — are notes only. No COM is selected. Face fabric on Est 838 is client supplied, 58 1/2 yd.",
        CONTENT_LEFT,
        y,
        CONTENT_W,
        S_SMALL,
    )


def _column_block(c, x, y, w, title, lines):
    section_label(c, x, y, title)
    yy = y - 12
    for line in lines:
        yy = draw_para(c, line, x, yy, w, S_SMALL) - 2
    return yy


def page_opening(c, page, total, spec):
    paint_page(c, "Presentation", spec["crumb"], page, total)
    c.setFillColor(INK)
    c.setFont("Serif-Bold", 14)
    c.drawString(CONTENT_LEFT, 686, spec["title"])
    c.setFillColor(INK2)
    c.setFont("Serif-Italic", 8)
    c.drawString(CONTENT_LEFT, 672, spec["subtitle"])

    top = 658
    strip_top = 208
    gap = 10
    left_w = 246
    right_x = CONTENT_LEFT + left_w + gap
    right_w = CONTENT_RIGHT - right_x
    frame_bottom = strip_top + 8
    frame_h = top - 16 - frame_bottom

    section_label(c, CONTENT_LEFT, top, "Existing  ·  photograph")
    section_label(c, right_x, top, "Proposed  ·  schematic elevation")
    draw_photo(c, photo(spec["photo"]), CONTENT_LEFT, frame_bottom, left_w, frame_h)
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.5)
    c.setFillColor(CREAM)
    c.rect(right_x, frame_bottom, right_w, frame_h, fill=1, stroke=1)
    spec["draw"](c, (right_x, frame_bottom, right_w, frame_h))

    # legend along the bottom inside the schematic frame
    lx = right_x + 6
    ly = frame_bottom + 5
    swatch(c, lx, ly, PANEL, "Face")
    swatch(c, lx + 42, ly, spec["fill"], spec["fill_name"])
    swatch(c, lx + 96, ly, GOLD, "New trim")

    col_w = (CONTENT_W - 12) / 3
    y0 = strip_top - 4
    _column_block(c, CONTENT_LEFT, y0, col_w, "Field", spec["field"])
    _column_block(c, CONTENT_LEFT + col_w + 6, y0, col_w, "Est 838", spec["est"])
    _column_block(c, CONTENT_LEFT + (col_w + 6) * 2, y0, col_w, "Addendum", spec["add"])


def page_office_presentation(c, page, total):
    paint_page(c, "Presentation", "Not on Est 838  ·  Concierge Office", page, total)
    c.setFillColor(INK)
    c.setFont("Serif-Bold", 14)
    c.drawString(CONTENT_LEFT, 686, "Concierge Office  —  inside office, not a lobby opening")
    c.setFillColor(INK2)
    c.setFont("Serif-Italic", 8.5)
    c.drawString(
        CONTENT_LEFT,
        672,
        "Recorded on the same June sheet as the outside lobby drapery. Omitted from Est 838.",
    )

    c.setFillColor(GOLD_PALE)
    c.setStrokeColor(GOLD_DEEP)
    c.setLineWidth(0.8)
    c.rect(CONTENT_LEFT, 636, CONTENT_W, 28, fill=1, stroke=1)
    c.setFillColor(INK)
    c.setFont("Sans-Bold", 8)
    c.drawString(
        CONTENT_LEFT + 8,
        646,
        "GAP  ·  NOT ON EST 838  ·  OUT OF THIS LOBBY PACK  ·  NO PRICE  ·  NO PROPOSED TREATMENT",
    )

    box = (CONTENT_LEFT, 250, 300, 370)
    c.setFillColor(CREAM)
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.4)
    c.rect(*box, fill=1, stroke=1)
    draw_office_opening(c, box)

    nx = CONTENT_LEFT + 316
    nw = CONTENT_RIGHT - nx
    y = 618
    section_label(c, nx, y, "What the sheet says")
    y -= 14
    lines = [
        "Outer width 68 1/4\".",
        "Height 104 1/4\".",
        "A second figure, 68 13/16\", is marked VALANCE? The sheet does not say whether that is an inner width, a valance width, or a mis-measure.",
        "Hardware note: tracks at 8 ft × 2, and 72 carriers.",
        "A circled rate, $95 per width. That is a field scribble. It is not Invoice 894 and it is not on Est 838.",
        "The sheet does not give a pair count, a finished length, a lining yardage, or a fabric.",
    ]
    for line in lines:
        y = draw_para(c, line, nx, y, nw, S_SMALL) - 4

    y -= 6
    section_label(c, nx, y, "What this pack does not do")
    y -= 14
    lines = [
        "It does not fold this opening into LOB-1. LOB-1 is the lobby concierge window in the labeled photograph.",
        "It does not invent a ripplefold, a swag, a sheer, or a price.",
        "It does not treat $95 per width as a submitted rate. Lobby ripplefold labor on Est 838 is $114.00 per width, from Invoice 894.",
        "A separate line is possible later, if Rafael wants it measured and priced on its own.",
    ]
    for line in lines:
        y = draw_para(c, line, nx, y, nw, S_SMALL) - 4

    y -= 8
    section_label(c, CONTENT_LEFT, 232, "Why it is easy to mix up with window 1")
    draw_para(
        c,
        "Both notes say concierge. Window 1 is the outside lobby window (photograph 1, LOB-1, wood surround, existing swag and sheers). This opening is marked INSIDE OFFICE on the same sheet, with its own width, height, and track count. The sizes do not match: 68 1/4\" × 104 1/4\" here, against 72 3/16\" × 105 5/8\" on the outside lobby opening.",
        CONTENT_LEFT,
        216,
        CONTENT_W,
        S_SMALL,
    )


def _legend_line(c, x, y, items):
    xx = x
    for color, label in items:
        swatch(c, xx, y, color, label)
        xx += 70


def page_install_index(c, page, total):
    paint_page(c, "Installation drawing", "Index  ·  WL-INS-00", page, total)
    c.setFillColor(INK)
    c.setFont("Serif-Bold", 14)
    c.drawString(CONTENT_LEFT, 686, "Installation set  —  Willard lobby")
    c.setFont("Serif-Italic", 8.5)
    c.setFillColor(INK2)
    c.drawString(
        CONTENT_LEFT,
        672,
        "Measure / shop intent for openings 1–4. Elevations are schematic and not to scale.  Est 838 submitted "
        + money(EST_TOTAL)
        + ".",
    )

    y = 656
    section_label(c, CONTENT_LEFT, y, "Sheet index")
    y -= 8
    rows = [
        ["Dwg", "Opening", "Use this sheet for"],
        ["WL-INS-01", "1 · LOB-1 Concierge window", "Inside-mount ripplefold, field opening, addendum layers"],
        ["WL-INS-02", "2 · LOB-2 Reception window", "Same opening note as 1, double swag"],
        ["WL-INS-03", "3 · LIN-1 Lincoln window", "Stationary panels, valance style open, holdbacks"],
        ["WL-INS-04", "4 · LIN-2 Passway", "Double-sided panels, rings, no valance"],
        ["WL-INS-05", "Inside office", "Field record only. Not on Est 838. Do not fabricate."],
    ]
    y = draw_table(c, rows, [70, 170, 308], CONTENT_LEFT, y, font_size=7) - 8

    section_label(c, CONTENT_LEFT, y, "Hardware already on Est 838  ·  do not price again")
    y -= 8
    rows = [
        ["Opening", "On the estimate", "Amount"],
        ["LOB-1", "Ripplefold track 10 ft, carriers, endcaps, batons. Removal and installation.", money(300 + 180)],
        ["LOB-2", "Same track and removal / installation.", money(300 + 180)],
        ["LIN-1", "Rod, brackets, rings, batons, finish TBD. Two holdback cylinders. Removal and installation.", money(420 + 71.88 + 150)],
        ["LIN-2", "Rod set, 20 rings (10 per panel), two holdback cylinders. Removal and installation.", money(420 + 71.88 + 90)],
    ]
    y = draw_table(c, rows, [70, 390, 88], CONTENT_LEFT, y, font_size=7) - 6
    y = draw_para(
        c,
        "The 10 ft track is the priced hardware unit from Invoice 894. It is not a field measurement of the opening. The opening on the sheet is 72 3/16\" wide.",
        CONTENT_LEFT,
        y,
        CONTENT_W,
        S_SMALL,
    ) - 6

    section_label(c, CONTENT_LEFT, y, "Open before cut")
    y -= 12
    questions = [
        "Finished length 105\" on the field sheet, 106\" on Est 838. Show both. Do not pick one on the bench.",
        "Lobby lining 23 yd on the sheet, 25 yd napped on Est 838 (12 1/2 + 12 1/2). Submitted quantity stands until Nelma revises it.",
        "Only one outside opening was measured. It is drawn on both window 1 and window 2.",
        "Est 838 says the ripplefold replaces the swag valance. The addendum prices a new swag with the pair. Confirm the layers before cut.",
        "Window 3 valance: single swag or double. The lobby photograph is too far to decide. The elevation uses a neutral scallop marked STYLE TBC.",
        "Window 4 has no valance in the photograph. Confirm bullion and leading edge still belong there.",
        "Holdback cylinders are already on LIN-1 and LIN-2, four at $35.94. If bullion replaces them, the credit is " + money(HOLDBACK_CREDIT) + ". No credit is taken here.",
        "Sheers are windows 1 and 2 only, assumed at 4 widths each, about the Est 838 length. That fullness is a ballpark assumption.",
        "Passway width was not written down. Leading edge is priced once per panel. Both faces of a double-sided panel are still a question.",
        "Inside office stays off this lobby price. The circled $95 per width is not a submitted rate.",
        "COM is open: face, sheer, fringe, valance trim, bullion finish. Madalyn and Holloway figures are not a selection.",
    ]
    col_w = (CONTENT_W - 12) / 2
    left = questions[:6]
    right = questions[6:]
    y_left = y
    y_right = y
    for i, q in enumerate(left, 1):
        y_left = draw_para(c, f"<b>{i}.</b>  {q}", CONTENT_LEFT, y_left, col_w, S_SMALL) - 3
    for i, q in enumerate(right, 7):
        y_right = draw_para(c, f"<b>{i}.</b>  {q}", CONTENT_LEFT + col_w + 12, y_right, col_w, S_SMALL) - 3


def page_install_opening(c, page, total, spec):
    paint_page(c, "Installation drawing", spec["crumb"], page, total)
    c.setFillColor(INK)
    c.setFont("Serif-Bold", 13)
    c.drawString(CONTENT_LEFT, 686, spec["title"])
    c.setFillColor(MUTED)
    c.setFont("Sans", 7.5)
    c.drawString(CONTENT_LEFT, 672, spec["dwg"] + "   ·   NOT TO SCALE   ·   DRAFT A   ·   28 Sep 2026")

    draw_box = (CONTENT_LEFT, 168, 360, 490)
    c.setFillColor(CREAM)
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.6)
    c.rect(*draw_box, fill=1, stroke=1)
    spec["draw"](c, draw_box)
    _legend_line(c, draw_box[0] + 8, draw_box[1] + 6, spec["legend"])

    nx = CONTENT_LEFT + 372
    nw = CONTENT_RIGHT - nx
    y = 658
    section_label(c, nx, y, "Install notes")
    y -= 13
    for i, note in enumerate(spec["notes"], 1):
        y = draw_para(c, f"<b>{i}.</b>  {note}", nx, y, nw, S_SMALL) - 3

    # Title block sits under the elevation, clear of the footer rule at y=40.
    bx, by, bw, bh = CONTENT_LEFT, 52, CONTENT_W, 100
    c.setFillColor(WHITE)
    c.setStrokeColor(INK)
    c.setLineWidth(0.8)
    c.rect(bx, by, bw, bh, fill=1, stroke=1)
    c.setFillColor(GOLD)
    c.rect(bx, by + bh - 3, bw, 3, fill=1, stroke=0)
    pairs = spec["block"]
    col_w = bw / 3.0
    mid_y = by + bh / 2.0
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.4)
    c.line(bx, mid_y, bx + bw, mid_y)
    for col in (1, 2):
        c.line(bx + col * col_w, by + 4, bx + col * col_w, by + bh - 4)
    for i, (lab, val) in enumerate(pairs):
        col = i % 3
        row = i // 3
        cx = bx + col * col_w + 8
        cell_top = by + bh - 4 - row * (bh / 2.0)
        c.setFillColor(GOLD_DEEP)
        c.setFont("Sans", 6)
        c.drawString(cx, cell_top - 12, lab.upper())
        c.setFillColor(INK)
        c.setFont("Serif", 8)
        c.drawString(cx, cell_top - 26, val)


def page_install_office(c, page, total):
    paint_page(c, "Installation drawing", "Inside office  ·  WL-INS-05", page, total)
    c.setFillColor(INK)
    c.setFont("Serif-Bold", 13)
    c.drawString(CONTENT_LEFT, 686, "Concierge Office  —  measure record only")
    c.setFillColor(MUTED)
    c.setFont("Sans", 7.5)
    c.drawString(CONTENT_LEFT, 672, "WL-INS-05   ·   NOT TO SCALE   ·   DO NOT FABRICATE FROM THIS SHEET")

    c.setFillColor(GOLD_PALE)
    c.setStrokeColor(GOLD_DEEP)
    c.rect(CONTENT_LEFT, 646, CONTENT_W, 18, fill=1, stroke=1)
    c.setFillColor(INK)
    c.setFont("Sans-Bold", 8)
    c.drawString(CONTENT_LEFT + 8, 651, "NOT ON EST 838  ·  NO LINE  ·  NO COM  ·  NO LABOR")

    box = (CONTENT_LEFT, 200, 330, 430)
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.6)
    c.setFillColor(CREAM)
    c.rect(*box, fill=1, stroke=1)
    draw_office_opening(c, box)

    nx = CONTENT_LEFT + 346
    nw = CONTENT_RIGHT - nx
    notes = [
        "Distinct from LOB-1, the lobby concierge window.",
        "Outer width 68 1/4\". Height 104 1/4\".",
        "68 13/16\" is written with the word VALANCE? Do not build a valance from that word.",
        "Tracks: 8 ft × 2. Carriers: 72. Recorded as written. Not checked against a track schedule.",
        "Circled $95 per width stays a scribble. Lobby labor on Est 838 is $114.00 per width.",
        "No finished length, no pair count, no lining, no fabric, no removal line.",
        "If this opening is wanted, it needs its own measure and its own estimate line.",
    ]
    y = 630
    section_label(c, nx, y, "Field record")
    y -= 14
    for i, note in enumerate(notes, 1):
        y = draw_para(c, f"<b>{i}.</b>  {note}", nx, y, nw, S_SMALL) - 4

    y = 180
    y = draw_para(
        c,
        "Scratch on the June 9 Lincoln sheet (139×, 140×, 75× W, and the figures 46, 420, 36) is not interpreted and is not a price. Hardware at $420.00 on LIN-1 and LIN-2 is an Est 838 line, not a reading of that scratch.",
        CONTENT_LEFT,
        y,
        CONTENT_W,
        S_SMALL,
    )


def build_specs():
    w1_draw = lambda c, box: draw_lobby_pair(
        c, box, "single", "wood", '72 3/16" W', '105 5/8" H'
    )
    w2_draw = lambda c, box: draw_lobby_pair(
        c, box, "double", "stone", '72 3/16" W', '105 5/8" H'
    )
    w3_draw = lambda c, box: draw_lincoln_window(c, box, '73" W', '125 1/2" H')
    w4_draw = lambda c, box: draw_passway(c, box, '102 1/2" H')

    field_lobby = [
        "Outside opening 72 3/16\" W × 105 5/8\" H.",
        "Inside mount, ripplefold.",
        "Main fabric only, plus lining.",
        "Sheet totals 2 pairs @ 2W × 105\" L.",
        "This window is one of those pairs.",
        "Main 27 yd and lining 23 yd are for both pairs together.",
    ]
    est_lobby = [
        "Submitted " + money(LOB) + ".",
        "1 pair @ 2W × 106\" L, up to 120\".",
        "Labor 4 widths @ $114.00.",
        "Main 13 1/2 yd, client supplied.",
        "Napped lining 12 1/2 yd @ $11.10.",
        "Track 10 ft unit, " + money(300) + ". Rem / install " + money(180) + ".",
        "Line note: replaces swag valance.",
    ]
    return {
        "w1": {
            "crumb": "Opening 1  ·  LOB-1",
            "title": "Opening 1  ·  Concierge Window",
            "subtitle": "LOB-1  ·  single wide swag, ripplefold pair, sheers",
            "photo": "window_1_concierge.png",
            "draw": w1_draw,
            "fill": SHEER,
            "fill_name": "Sheer",
            "field": field_lobby,
            "est": est_lobby,
            "add": [
                "ADD-V1 swag / valance make " + money(425) + " BALLPARK.",
                "ADD-VT center tassel " + money(95.94) + " INV 909 unit.",
                "ADD-VF bottom trim " + money(125) + " BALLPARK. Trim COM.",
                "ADD-BT two bullion tiebacks @ " + money(95.94) + " INV 909.",
                "ADD-LE two leading edges @ " + money(210) + " INV 909. Trim COM.",
                "ADD-SH 4 sheer widths @ " + money(72) + " BALLPARK.",
                "ADD-SI sheer rem / install " + money(90) + " BALLPARK.",
            ],
        },
        "w2": {
            "crumb": "Opening 2  ·  LOB-2",
            "title": "Opening 2  ·  Reception Window",
            "subtitle": "LOB-2  ·  double overlapping swags, ripplefold pair, sheers",
            "photo": "window_2_reception.png",
            "draw": w2_draw,
            "fill": SHEER,
            "fill_name": "Sheer",
            "field": [
                "No separate reception size on the sheet.",
                "The one outside opening is used here: 72 3/16\" × 105 5/8\".",
                "Inside mount, ripplefold.",
                "Second pair of the sheet’s 2 pairs @ 2W × 105\" L.",
                "Confirm this window matches before cut.",
            ],
            "est": est_lobby,
            "add": [
                "ADD-V2 double swags " + money(525) + " BALLPARK.",
                "ADD-VT center tassel " + money(95.94) + " INV 909 unit.",
                "ADD-VF bottom trim " + money(125) + " BALLPARK. Trim COM.",
                "ADD-BT two bullion tiebacks @ " + money(95.94) + " INV 909.",
                "ADD-LE two leading edges @ " + money(210) + " INV 909.",
                "ADD-SH 4 sheer widths @ " + money(72) + " BALLPARK.",
                "ADD-SI sheer rem / install " + money(90) + " BALLPARK.",
            ],
        },
        "w3": {
            "crumb": "Opening 3  ·  LIN-1",
            "title": "Opening 3  ·  Lincoln Lobby Window",
            "subtitle": "LIN-1  ·  stationary panels, formal valance still open, no sheers",
            "photo": "window_3_lincoln.png",
            "draw": w3_draw,
            "fill": GLASS,
            "fill_name": "Glass",
            "field": [
                "2 panels, non-operable.",
                "73\" W × 125 1/2\" H.",
                "1 1/2 W per panel. Sheet wrote this as one-and-a-half widths.",
                "12 yd with lining — one scribble, not a split.",
            ],
            "est": [
                "Submitted " + money(LIN1) + ".",
                "2 panels @ 1 1/2 W × 125 1/2\" L.",
                "Labor 3 widths @ $150.00, over 120\" length.",
                "Main 12 yd, client supplied.",
                "Lining 11 yd @ $10.74.",
                "Two holdback cylinders @ $35.94.",
                "Hardware set " + money(420) + ", finish TBD.",
                "Removal and installation " + money(150) + ".",
            ],
            "add": [
                "ADD-V3 formal valance " + money(450) + " BALLPARK. Style TBC.",
                "ADD-VT center tassel " + money(95.94) + " INV 909 unit.",
                "ADD-VF bottom trim " + money(125) + " BALLPARK.",
                "ADD-BT two bullion @ " + money(95.94) + " INV 909.",
                "ADD-LE two leading edges @ " + money(210) + " INV 909.",
                "No sheers on this opening.",
                "Holdback vs bullion is open. No credit taken.",
            ],
        },
        "w4": {
            "crumb": "Opening 4  ·  LIN-2",
            "title": "Opening 4  ·  Lincoln Lobby Passway",
            "subtitle": "LIN-2  ·  double-sided panels. No valance. No sheers.",
            "photo": "window_4_passway.png",
            "draw": w4_draw,
            "fill": VOID,
            "fill_name": "Opening",
            "field": [
                "Doorway / passway.",
                "Height 102 1/2\". Width was not written.",
                "Double-sided. 1 1/2 W per face.",
                "10 rings per panel.",
                "2 panels @ 3W × 102 1/2\".",
                "20 yd beside that make.",
            ],
            "est": [
                "Submitted " + money(LIN2) + ".",
                "2 panels @ 3W × 102 1/2\" L.",
                "1 1/2 W per face. Labor 6 widths @ $114.00.",
                "Main 20 yd, client supplied.",
                "Lining 18 1/2 yd @ $10.74.",
                "20 rings. Two holdback cylinders @ $35.94.",
                "Hardware set " + money(420) + ".",
                "Removal and installation " + money(90) + ".",
            ],
            "add": [
                "No valance line. Photograph shows none.",
                "No sheer line.",
                "ADD-BT two bullion @ " + money(95.94) + " INV 909.",
                "ADD-LE two leading edges @ " + money(210) + " INV 909.",
                "Priced as one edge per panel, lobby face.",
                "Both faces of the double-sided panel: open.",
                "Holdback vs bullion: open. No credit taken.",
            ],
        },
    }


INSTALL_NOTES = {
    "w1": [
        "Inside mount. Ripplefold. Elevation shows the dressed-back day position, sheers in the center.",
        "Field opening 72 3/16\" × 105 5/8\". Finished length on the sheet is 105\". Est 838 length is 106\". Do not cut until those agree.",
        "Track on Est 838 is a 10 ft unit with carriers, endcaps, and batons. Cut the track to the opening. Do not treat 10 ft as the window width.",
        "Pair is 2W, four labor widths. Main 13 1/2 yd COM. Napped premiere sateen lining 12 1/2 yd on the estimate. The sheet’s 23 yd lining covers both lobby pairs, against 25 yd on Est 838.",
        "Removal and installation of the pair is already on Est 838 at " + money(180) + ".",
        "New single swag is ADD-V1, BALLPARK. Est 838 says this pair replaces the swag valance. Layering is not confirmed.",
        "Center drop tassel and bottom trim are separate addendum lines. Trim is COM.",
        "Leading-edge fringe on each panel’s inner edge. Bullion tiebacks, finish TBD.",
        "Sheers: 4 widths, BALLPARK, this window only (with window 2). Sheer removal / installation is incremental to the pair.",
        "Face fabric, sheer, fringe, and bullion finish are COM. Nothing is selected.",
    ],
    "w2": [
        "Same field opening as window 1, because the sheet recorded one outside size for the two pairs. Confirm on site.",
        "Inside mount ripplefold. Dressed-back day position with sheers.",
        "Finished length 105\" field / 106\" Est 838. Not reconciled.",
        "Track, labor, lining, and removal match LOB-1. Submitted subtotal " + money(LOB) + ".",
        "Double overlapping swags are ADD-V2, BALLPARK, to match photograph 2. Not a second swag line on top of a valance.",
        "Center tassel, bottom trim, leading edge, and bullion match window 1’s addendum lines.",
        "Sheers on this window and window 1 only.",
        "Same open layering question: Est 838 note says the pair replaces the swag valance.",
    ],
    "w3": [
        "Stationary, non-operable. Two panels @ 1 1/2 W × 125 1/2\" finished length.",
        "Field opening 73\" W × 125 1/2\" H. This one matches Est 838.",
        "Main 12 yd COM. The sheet says 12 yd with lining in one note. Est 838 prices lining apart, 11 yd premiere sateen. Do not drop the lining.",
        "Rod, brackets, rings, batons, finish TBD, already on Est 838 at " + money(420) + ".",
        "Two holdback cylinders are on the estimate. Bullion is on the addendum. Keep both, or credit " + money(71.88) + " on this opening, is not decided.",
        "Formal valance ADD-V3 is BALLPARK. The scallop on the elevation is a placeholder. Style TBC against photographs 1 and 2.",
        "No sheers. Photograph 3 is a distant lobby view; do not invent detail from it.",
        "Leading edge on each panel. Center tassel and bottom trim are addendum lines. Trim COM.",
        "Removal and installation " + money(150) + " is already on Est 838.",
    ],
    "w4": [
        "Double-sided panels. 1 1/2 W each face, 3W per panel, two panels. Finished length 102 1/2\".",
        "Height matches the field sheet and Est 838. Width was not measured. The elevation proportion is diagrammatic and has no width figure.",
        "10 rings per panel, 20 rings on the estimate. Drawn gathered on each panel.",
        "Main 20 yd COM matches the sheet. Lining 18 1/2 yd is the Est 838 quantity, separate from the 20 yd.",
        "Hardware set and removal / installation are on Est 838. Removal is " + money(90) + ".",
        "No valance. No sheers. Do not borrow the lobby swag.",
        "Two holdback cylinders are on the estimate. Bullion may replace them. No credit taken.",
        "Leading edge is drawn on the lobby face, one per panel, which is the priced count. Trim on the reverse face is not priced.",
        "Bullion finish and fringe are COM.",
    ],
}


def _install_block(dwg, opening):
    return [
        ("Project", "Willard InterContinental"),
        ("Client", "Maggie O'Neill / Mariella"),
        ("Designer", "Splendor Styling"),
        ("Drawing", dwg),
        ("Opening", opening),
        ("Revision", "DRAFT A  ·  28 Sep 2026"),
    ]


def build_presentation(path: Path):
    specs = build_specs()
    c = canvas.Canvas(str(path), pagesize=(PAGE_W, PAGE_H))
    c.setTitle("Willard Lobby — Existing vs Proposed — DRAFT")
    c.setAuthor("Empire Workroom / Nelma's Workroom")
    total = 6
    page_overview(c, 1, total)
    c.showPage()
    for key in ("w1", "w2", "w3", "w4"):
        page_opening(c, {"w1": 2, "w2": 3, "w3": 4, "w4": 5}[key], total, specs[key])
        c.showPage()
    page_office_presentation(c, 6, total)
    c.save()


def build_installation(path: Path):
    specs = build_specs()
    c = canvas.Canvas(str(path), pagesize=(PAGE_W, PAGE_H))
    c.setTitle("Willard Lobby — Installation Drawings — DRAFT")
    c.setAuthor("Empire Workroom / Nelma's Workroom")
    total = 6
    page_install_index(c, 1, total)
    c.showPage()
    sequence = [
        (2, "w1", "WL-INS-01", "1  ·  LOB-1 Concierge", [
            (PANEL, "Face"), (SHEER, "Sheer"), (GOLD, "New trim"),
        ]),
        (3, "w2", "WL-INS-02", "2  ·  LOB-2 Reception", [
            (PANEL, "Face"), (SHEER, "Sheer"), (GOLD, "New trim"),
        ]),
        (4, "w3", "WL-INS-03", "3  ·  LIN-1 Window", [
            (PANEL, "Face"), (GLASS, "Glass"), (GOLD, "New trim"),
        ]),
        (5, "w4", "WL-INS-04", "4  ·  LIN-2 Passway", [
            (PANEL, "Face"), (VOID, "Opening"), (GOLD, "New trim"),
        ]),
    ]
    for page, key, dwg, opening, legend in sequence:
        spec = {
            "crumb": f"{opening}  ·  {dwg}",
            "title": specs[key]["title"],
            "dwg": dwg,
            "draw": specs[key]["draw"],
            "legend": legend,
            "notes": INSTALL_NOTES[key],
            "block": _install_block(dwg, opening),
        }
        page_install_opening(c, page, total, spec)
        c.showPage()
    page_install_office(c, 6, total)
    c.save()


def rasterize(pdf: Path, prefix: str):
    doc = pymupdf.open(pdf)
    paths = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=pymupdf.Matrix(140 / 72, 140 / 72), alpha=False)
        out = PREVIEWS / f"{prefix}-{i+1:02d}.png"
        pix.save(str(out))
        paths.append(out)
    return paths


def verify(pdf: Path, expect_pages: int):
    doc = pymupdf.open(pdf)
    if doc.page_count != expect_pages:
        raise SystemExit(f"{pdf.name}: expected {expect_pages} pages, got {doc.page_count}")
    text = "\n".join(page.get_text() for page in doc)
    required = [
        "DRAFT",
        "DO NOT EMAIL",
        "NUMBERS NOT LOCKED",
        "72 3/16",
        "105 5/8",
        "125 1/2",
        "102 1/2",
        "68 1/4",
        "68 13/16",
        "104 1/4",
        "BALLPARK",
        "4,824.09",
        "NOT ON EST 838" if "Installation" in pdf.name or "Existing" in pdf.name else "GAP",
        "Nelma",
        "EMPIRE WORKROOM",
    ]
    # Office gap phrase differs. Check both packs for the office dimensions and the gap idea.
    missing = [r for r in required if r not in text]
    # Decimal inch leaks
    leaks = re.findall(r"\d+\.\d+\s*\"", text)
    if leaks:
        missing.append(f"decimal inches: {leaks}")
    if "1.5" in text:
        missing.append("found 1.5")
    for i, page in enumerate(doc):
        if "DRAFT" not in page.get_text():
            missing.append(f"page {i+1} missing DRAFT")
    if missing:
        raise SystemExit(f"{pdf.name} failed checks: {missing}")
    return text


def copy_artifacts(files):
    dest = Path("/opt/cursor/artifacts/willard-lobby")
    try:
        dest.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    copied = []
    for f in files:
        target = dest / f.name
        shutil.copy2(f, target)
        copied.append(target)
    preview_dest = dest / "previews"
    preview_dest.mkdir(exist_ok=True)
    for f in PREVIEWS.glob("*.png"):
        shutil.copy2(f, preview_dest / f.name)
        copied.append(preview_dest / f.name)
    return copied


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    pres = OUT / "Willard_Lobby_Existing_vs_Proposed_DRAFT.pdf"
    inst = OUT / "Willard_Lobby_Installation_Drawings_DRAFT.pdf"
    build_presentation(pres)
    build_installation(inst)
    verify(pres, 6)
    verify(inst, 6)
    # Installation text must mention the office gap in those words.
    inst_text = "\n".join(page.get_text() for page in pymupdf.open(inst))
    for phrase in ("NOT ON EST 838", "WL-INS-05", "DO NOT FABRICATE"):
        if phrase not in inst_text:
            raise SystemExit(f"installation missing {phrase}")
    pres_paths = rasterize(pres, "presentation")
    inst_paths = rasterize(inst, "installation")
    copy_artifacts([pres, inst])
    print(pres)
    print(inst)
    for p in pres_paths + inst_paths:
        print(p)


if __name__ == "__main__":
    main()
