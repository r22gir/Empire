"""Landscape presentation sheets in the McLean header-B style.

One sheet per opening, a ripplefold sheet when the opening has sheers,
and an opening schedule. Drafts only.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

from app.services.drawing.inches import format_inches
from app.services.drawing.max_sheet_chrome import GOLD, HAIR, INK, MUTE, PAPER, PW, PH
from app.services.estimates.header_b import (
    CREAM,
    billing_for,
    body_fonts,
    paint_footer,
    paint_header_b,
)
from app.services.pricing.workroom_rules import rule


def _right(title: str, sheet_no: int, total: int, date_label: str):
    return [
        (title.upper(), 11, CREAM),
        (f"SHEET {sheet_no:02d} OF {total:02d}", 8, GOLD),
        (date_label, 7, MUTE),
    ]


def _photo(c, path: str | None, x, y, w, h, caption: str, font) -> None:
    c.setStrokeColor(HAIR)
    c.setFillColor(HexColor("#efe9dc"))
    c.setLineWidth(0.8)
    c.rect(x, y, w, h, fill=1, stroke=1)
    image = Path(path) if path else None
    if image and image.is_file():
        c.drawImage(str(image), x + 2, y + 14, w - 4, h - 18, preserveAspectRatio=True, anchor="c", mask="auto")
    else:
        c.setFillColor(MUTE)
        c.setFont(font, 8)
        c.drawCentredString(x + w / 2, y + h / 2, "PHOTO")
    c.setFillColor(INK)
    c.setFont(font, 6.5)
    c.drawString(x + 4, y + 4, caption[:42])


def _panel_sketch(c, opening: dict, x, y, w, h, font, font_b) -> None:
    width = opening["width"]
    height = opening["height"]
    scale = min((w - 36) / width, (h - 28) / height)
    pw = width * scale
    ph = height * scale
    ox = x + 16
    oy = y + 16
    c.setFillColor(HexColor("#d7e4ee"))
    c.setStrokeColor(INK)
    c.setLineWidth(1.1)
    c.rect(ox, oy, pw, ph, fill=1, stroke=1)
    panels = max(1, int(opening["panels"]))
    each = pw / panels
    cloth = opening["widths"]
    for i in range(panels):
        px = ox + i * each
        c.setFillColor(HexColor("#c4b49a"), alpha=0.85)
        c.rect(px + 2, oy + 2, each - 4, ph - 4, fill=1, stroke=0)
        c.setFillColor(INK)
        c.setFont(font_b, 6.5)
        c.drawCentredString(px + each / 2, oy + ph / 2, f"PANEL {i + 1}")
        c.setFont(font, 6)
        c.drawCentredString(px + each / 2, oy + ph / 2 - 10, f"{_w(cloth['per_panel'])} W")
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.7)
    c.line(ox, oy - 8, ox + pw, oy - 8)
    c.setFillColor(INK)
    c.setFont(font, 7)
    c.drawCentredString(ox + pw / 2, oy - 18, format_inches(width))
    c.drawString(ox + pw + 6, oy + ph / 2, format_inches(height))


def _w(value: float) -> str:
    text = format_inches(value)
    return text[:-1] if text.endswith('"') else text


def render_opening_sheet(packet: dict, opening: dict, sheet_no: int, total: int) -> bytes:
    bill = billing_for(packet)
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(PW, PH))
    c.setTitle(f"{opening['room']} — {packet.get('quote_number')}")
    c.setAuthor(bill.name)
    _serif, sans, sans_b, _mono = body_fonts()
    date_label = str(packet.get("date") or "")
    body = paint_header_b(
        c, bill, page_w=PW, page_h=PH,
        right_lines=_right(opening["room"], sheet_no, total, date_label),
        band_h=72,
    )
    paint_footer(
        c, bill, page_w=PW, left="FOR DISCUSSION — NOT FOR CONSTRUCTION",
        right=f"SHEET {sheet_no} / {total}",
    )
    cloth = opening["widths"]
    c.setFillColor(INK)
    c.setFont(sans_b, 12)
    c.drawString(28, body - 4, opening["room"].upper())
    c.setFillColor(MUTE)
    c.setFont(sans, 8)
    c.drawString(
        28, body - 18,
        f"{format_inches(opening['width'])} window × {format_inches(opening['height'])} finished length"
        f"  ·  {opening['panels']} panels  ·  {_w(cloth['per_panel'])} widths per panel",
    )
    _panel_sketch(c, opening, 28, 210, 360, 250, sans, sans_b)
    c.setFillColor(INK)
    c.setFont(sans_b, 8)
    c.drawString(28, 196, "LAYOUT MATH")
    c.setFont(sans, 7)
    math = (
        f"{format_inches(cloth['fabric_in'])} ÷ {opening['panels']} = "
        f"{format_inches(cloth['fabric_in'] / opening['panels'])} per panel ÷ "
        f"{format_inches(rule('fabric_width_in'))} = {_w(cloth['per_panel'])} widths"
        f"  ·  {opening['yards']:.1f} yd lining + {opening['yards']:.1f} yd bump"
    )
    c.drawString(28, 182, math[:110])

    c.setFont(sans_b, 8)
    c.drawString(410, body - 4, "FIELD DATA")
    rows = [
        ("WINDOW WIDTH", format_inches(opening["width"])),
        ("FINISHED LENGTH", format_inches(opening["height"])),
        ("PANELS", f"{opening['panels']} · CENTER DRAW · STATIONARY"),
        ("WIDTHS", f"{_w(cloth['per_panel'])} PER PANEL · {_w(cloth['total'])} TOTAL"),
        ("FABRIC @ 100%", f"{format_inches(opening['width'])} x 2 + {format_inches(rule('fullness_add_in'))}"),
        ("CUT LENGTH", format_inches(opening["cut_length"])),
    ]
    sheer = opening.get("sheer")
    if sheer and sheer.carrier_count:
        rows.append((
            "SHEERS",
            f"RIPPLEFOLD {sheer.fullness}% · {format_inches(sheer.coverage_width)} · "
            f"{sheer.carrier_count} CARRIERS",
        ))
    y = body - 22
    for label, value in rows:
        c.setFillColor(MUTE)
        c.setFont(sans, 6)
        c.drawString(410, y, label)
        c.setFillColor(INK)
        c.setFont(sans, 8)
        c.drawString(410, y - 11, value[:42])
        y -= 26

    src = opening["opening"]
    _photo(c, src.get("photo"), 28, 78, 200, 120, "Site photo — uncropped", sans)
    _photo(c, src.get("fabric_crop") or src.get("fabric_image"), 240, 78, 140, 120, "Existing fabric", sans)
    c.setFillColor(INK)
    c.setFont(sans_b, 7.5)
    c.drawString(400, 188, "FIELD CHECK")
    c.setFont(sans, 6.5)
    note_y = 174
    for note in (src.get("field_notes") or [])[:6]:
        c.drawString(400, note_y, f"· {note[:52]}")
        note_y -= 11
    c.showPage()
    c.save()
    return buf.getvalue()


def render_schedule_sheet(packet: dict, sheet_no: int, total: int) -> bytes:
    bill = billing_for(packet)
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(PW, PH))
    c.setTitle(f"Opening schedule — {packet.get('quote_number')}")
    c.setAuthor(bill.name)
    _serif, sans, sans_b, _mono = body_fonts()
    body = paint_header_b(
        c, bill, page_w=PW, page_h=PH,
        right_lines=_right("OPENING SCHEDULE", sheet_no, total, str(packet.get("date") or "")),
        band_h=72,
    )
    paint_footer(
        c, bill, page_w=PW, left="FOR DISCUSSION — NOT FOR CONSTRUCTION",
        right=f"SHEET {sheet_no} / {total}",
    )
    project = packet.get("project") or {}
    c.setFillColor(INK)
    c.setFont(sans_b, 12)
    c.drawString(28, body - 4, "OPENING SCHEDULE")
    c.setFillColor(MUTE)
    c.setFont(sans, 8)
    c.drawString(
        28, body - 18,
        f"{project.get('address') or 'Site not given'}  ·  {packet.get('quote_number')}",
    )
    headers = ("ROOM", "MARK", "QTY", "WIDTH", "HEIGHT", "CONDITION")
    xs = (28, 160, 210, 260, 340, 430)
    y = body - 42
    c.setFillColor(HexColor("#16191c"))
    c.rect(28, y - 6, PW - 56, 16, fill=1, stroke=0)
    c.setFillColor(CREAM)
    c.setFont(sans_b, 7)
    for label, x in zip(headers, xs):
        c.drawString(x, y - 1, label)
    y -= 22
    c.setFillColor(INK)
    c.setFont(sans, 7.5)
    for opening in packet.get("rooms") or []:
        src = opening["opening"]
        sheer = opening.get("sheer")
        condition = f"Pair, stationary · {_w(opening['widths']['total'])} widths"
        if sheer and sheer.carrier_count:
            condition += (
                f" · ripplefold sheers {format_inches(sheer.coverage_width)}, "
                f"{sheer.fullness}%, {sheer.carrier_count} carriers"
            )
        if src.get("batons"):
            condition += f", {src['batons']} batons"
        if src.get("pair_assumed"):
            condition += " · pair assumed"
        values = (
            opening["room"].upper(),
            str(opening.get("mark") or ""),
            "1",
            format_inches(opening["width"]),
            format_inches(opening["height"]),
            condition[:48],
        )
        for value, x in zip(values, xs):
            c.drawString(x, y, value)
        y -= 16
    c.setFont(sans_b, 8)
    c.drawString(28, y - 8, f"{len(packet.get('rooms') or [])} TOTAL OPENINGS RECORDED")

    party = packet.get("prepared_for") or {}
    c.setFillColor(GOLD)
    c.setFont(sans_b, 8)
    c.drawString(28, 150, "PREPARED FOR")
    c.drawString(400, 150, "PROJECT")
    c.setFillColor(INK)
    c.setFont(sans, 8)
    left = [party.get("company"), party.get("attn") and f"Attn: {party['attn']}", party.get("email"), party.get("phone"), party.get("address")]
    right = [project.get("name"), project.get("phase"), project.get("address"), project.get("sidemark") and f"Sidemark: {project['sidemark']}", project.get("scope")]
    yy = 134
    for row in left:
        if row:
            c.drawString(28, yy, str(row)[:48])
            yy -= 12
    yy = 134
    for row in right:
        if row:
            c.drawString(400, yy, str(row)[:48])
            yy -= 12
    c.showPage()
    c.save()
    return buf.getvalue()
