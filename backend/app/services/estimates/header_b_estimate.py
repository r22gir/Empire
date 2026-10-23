"""Portrait estimate, header option B. Draft document. Never a payment link."""
from __future__ import annotations

from io import BytesIO

from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

from app.services.drawing.max_sheet_chrome import GOLD, HAIR, INK, MUTE, PAPER
from app.services.estimates.header_b import (
    CREAM,
    billing_for,
    body_fonts,
    brand_lines,
    money,
    paint_footer,
    paint_header_b,
)

PW, PH = 612.0, 792.0
_GROUPS = {
    "Installation": "1",
    "Preparation": "2",
    "Construction": "3",
    "Materials": "4",
}


def _card(c, x, y, w, h, title, rows, font, font_b) -> None:
    c.setFillColor(HexColor("#fbf8f1"))
    c.setStrokeColor(HAIR)
    c.setLineWidth(0.8)
    c.roundRect(x, y - h, w, h, 4, fill=1, stroke=1)
    c.setFillColor(GOLD)
    c.rect(x, y - 16, w, 16, fill=1, stroke=0)
    c.setFillColor(HexColor("#16191c"))
    c.setFont(font_b, 7)
    c.drawString(x + 8, y - 11, title)
    cursor = y - 30
    c.setFont(font, 7.4)
    for row in rows:
        if not row:
            continue
        c.setFillColor(INK)
        c.drawString(x + 8, cursor, str(row)[:64])
        cursor -= 11


def _prepared_rows(party: dict) -> list[str]:
    rows = []
    if party.get("company"):
        rows.append(party["company"])
    if party.get("attn"):
        rows.append(f"Attn: {party['attn']}")
    if party.get("email"):
        rows.append(party["email"])
    if party.get("phone"):
        rows.append(party["phone"])
    if party.get("address"):
        rows.append(party["address"])
    return rows or ["NOT GIVEN"]


def _project_rows(project: dict) -> list[str]:
    rows = []
    if project.get("name"):
        rows.append(project["name"])
    if project.get("phase"):
        rows.append(project["phase"])
    if project.get("address"):
        rows.append(project["address"])
    if project.get("sidemark"):
        rows.append(f"Sidemark: {project['sidemark']}")
    if project.get("scope"):
        rows.append(project["scope"])
    return rows or ["NOT GIVEN"]


def _wrap(text: str, limit: int = 86) -> list[str]:
    words = str(text or "").split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = word if not current else f"{current} {word}"
        if current and len(trial) > limit:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines or [""]


def render_header_b_estimate(packet: dict) -> bytes:
    bill = billing_for(packet)
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(PW, PH))
    number = packet.get("quote_number") or "EST-DRAFT"
    c.setTitle(f"Estimate {number}")
    c.setAuthor(bill.name)
    c.setCreator(bill.name)
    serif, sans, sans_b, _mono = body_fonts()
    name, _sub = brand_lines(bill)
    authority = f"{name} by Empire" if "by Empire" in _sub else name

    pages: list[list] = [[("cards",)]]
    y = PH - 78 - 14 - 108
    floor = 48

    def new_page():
        pages.append([])
        return PH - 78 - 20

    def room(need: float) -> None:
        nonlocal y
        if y - need < floor:
            y = new_page()

    room(16)
    pages[-1].append(("title",))
    y -= 16
    for opening in packet.get("rooms") or []:
        room(28)
        pages[-1].append(("room", opening["room"].upper()))
        y -= 16
        for group in opening["groups"]:
            room(16)
            pages[-1].append(("group", group["name"]))
            y -= 14
            for line in group["lines"]:
                wrapped = _wrap(line["description"])
                need = 11 * len(wrapped) + 3
                room(need)
                pages[-1].append(("line", line, wrapped))
                y -= need
            room(14)
            pages[-1].append(("sub", group["subtotal"]))
            y -= 14
        y -= 6
    room(78)
    pages[-1].append(("totals",))
    y -= 70
    if packet.get("notes"):
        room(28)
        pages[-1].append(("notes", packet["notes"]))
        y -= 24
    room(70)
    pages[-1].append(("sign",))

    total_pages = len(pages)
    for index, ops in enumerate(pages, start=1):
        right = [
            ("ESTIMATE", 11, CREAM),
            (number, 9, GOLD),
            (f"Date {packet.get('date', '')}", 7, CREAM),
            (f"Valid until {packet.get('valid_until', '')}", 7, MUTE),
        ]
        body_top = paint_header_b(c, bill, page_w=PW, page_h=PH, right_lines=right)
        paint_footer(
            c, bill, page_w=PW,
            left="DRAFT — NOT SENT",
            right=f"{number}  ·  {index} / {total_pages}",
        )
        y = body_top
        if index == 1:
            _card(c, 28, y, 268, 96, "PREPARED FOR", _prepared_rows(packet.get("prepared_for") or {}), sans, sans_b)
            _card(c, 308, y, 276, 96, "PROJECT", _project_rows(packet.get("project") or {}), sans, sans_b)
            y -= 108
        for op in ops:
            kind = op[0]
            if kind == "cards":
                continue
            if kind == "title":
                c.setFillColor(INK)
                c.setFont(sans_b, 8)
                c.drawString(28, y, "ITEMIZED COST BREAKDOWN")
                c.setFillColor(MUTE)
                c.setFont(sans, 7)
                c.drawRightString(PW - 28, y, "QTY      RATE        AMOUNT")
                y -= 14
            elif kind == "room":
                c.setFillColor(INK)
                c.setFont(serif, 11)
                c.drawString(28, y, op[1])
                y -= 16
            elif kind == "group":
                label = f"{_GROUPS.get(op[1], '')}. {op[1]}".strip(". ")
                c.setFillColor(GOLD)
                c.setFont(sans_b, 8)
                c.drawString(28, y, label)
                y -= 12
            elif kind == "line":
                line, wrapped = op[1], op[2]
                c.setFillColor(GOLD)
                c.circle(32, y + 2, 2.1, fill=1, stroke=0)
                c.setFillColor(INK)
                c.setFont(sans, 7.2)
                c.drawRightString(430, y, f"{line['quantity']:g}")
                c.drawRightString(500, y, money(line["rate"]))
                c.drawRightString(PW - 28, y, money(line["amount"]))
                for row in wrapped:
                    c.drawString(40, y, row)
                    y -= 11
                y -= 2
            elif kind == "sub":
                c.setStrokeColor(HAIR)
                c.setLineWidth(0.4)
                c.line(36, y + 8, PW - 28, y + 8)
                c.setFillColor(INK)
                c.setFont(sans_b, 8)
                c.drawString(36, y, "Subtotal")
                c.drawRightString(PW - 28, y, money(op[1]))
                y -= 16
            elif kind == "totals":
                c.setStrokeColor(GOLD)
                c.setLineWidth(1)
                c.line(300, y + 10, PW - 28, y + 10)
                rows = (
                    ("Subtotal", packet["subtotal"]),
                    (f"Tax ({packet['tax_rate']:.1f}%)", packet["tax"]),
                    ("Total", packet["total"]),
                )
                c.setFont(sans, 8)
                for label, amount in rows:
                    c.setFillColor(INK)
                    c.drawString(320, y, label)
                    c.drawRightString(PW - 28, y, money(amount))
                    y -= 12
                c.setFillColor(GOLD)
                c.setFont(sans_b, 8)
                c.drawString(28, y, packet.get("payment_line") or "")
                c.drawRightString(PW - 28, y, f"{packet['deposit_percent']:.0f}% deposit {money(packet['deposit'])}")
                y -= 16
            elif kind == "notes":
                c.setFillColor(MUTE)
                c.setFont(sans, 7)
                c.drawString(28, y, f"Notes: {op[1][:140]}")
                y -= 16
            elif kind == "sign":
                c.setFillColor(INK)
                c.setFont(sans_b, 8)
                c.drawString(28, y, "TERMS & CONDITIONS")
                y -= 12
                c.setFont(sans, 7.5)
                c.drawString(28, y, str(packet.get("terms") or "")[:110])
                y -= 18
                c.setFont(sans_b, 8)
                c.drawString(28, y, "ACCEPTANCE")
                y -= 12
                c.setFont(sans, 7.2)
                c.drawString(28, y, f"By signing below, I accept this estimate and authorize {authority} to proceed.")
                y -= 28
                c.setStrokeColor(INK)
                c.line(28, y, 240, y)
                c.line(280, y, 420, y)
                c.setFillColor(MUTE)
                c.setFont(sans, 6.5)
                c.drawString(28, y - 10, "Client Signature")
                c.drawString(280, y - 10, "Date")
        c.showPage()
    c.save()
    return buf.getvalue()
