"""Per-sheet yield PDF. Every printed size is a shop fraction."""
from __future__ import annotations

import io
from typing import Any

from reportlab.lib.colors import Color, black, white
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from app.services.cnc.inches import format_inches, parse_inches

GOLD = Color(0.72, 0.59, 0.05)
SLATE = Color(0.22, 0.22, 0.22)
RULE = Color(0.75, 0.72, 0.64)
WOOD = Color(0.85, 0.74, 0.52)
FOAM = Color(0.78, 0.86, 0.95)
FABRIC = Color(0.86, 0.78, 0.92)
MARK = Color(0.75, 0.12, 0.12)


def _fill_sheet_drawing(c: canvas.Canvas, sheet: dict[str, Any], x: float, y: float, w: float, h: float) -> None:
    sw = parse_inches(sheet["sheet_width"])
    sl = parse_inches(sheet["sheet_length"])
    if sw <= 0 or sl <= 0:
        return
    scale = min(w / sw, h / sl)
    dw, dh = sw * scale, sl * scale
    ox = x + (w - dw) / 2
    oy = y + (h - dh) / 2
    fill = {"wood": WOOD, "foam": FOAM, "fabric": FABRIC}.get(sheet.get("material"), WOOD)
    c.setStrokeColor(SLATE)
    c.setFillColor(fill)
    c.setLineWidth(0.8)
    c.rect(ox, oy, dw, dh, fill=1, stroke=1)
    c.setFillColor(SLATE)
    c.setFont("Times-Roman", 8)
    c.drawString(ox, oy + dh + 6, f'{sheet["material"].upper()}  {sheet["sheet_width"]} x {sheet["sheet_length"]}  yield {sheet["yield"]}')
    for part in sheet.get("parts") or []:
        pw = parse_inches(part["width"]) * scale
        pl = parse_inches(part["length"]) * scale
        px = ox + parse_inches(part["x"]) * scale
        py = oy + parse_inches(part["y"]) * scale
        c.setFillColor(white)
        c.setStrokeColor(SLATE)
        c.rect(px, py, pw, pl, fill=1, stroke=1)
        c.setFillColor(SLATE)
        c.setFont("Helvetica", 7)
        label = f'{part["name"]}  {part["width"]} x {part["length"]}'
        c.drawString(px + 3, py + max(3, pl / 2 - 3), label[:48])
    for mark in sheet.get("registration_marks") or []:
        mx = ox + parse_inches(mark["x"]) * scale
        my = oy + parse_inches(mark["y"]) * scale
        arm = max(4, parse_inches(mark["mark_size"]) * scale / 2)
        c.setStrokeColor(MARK)
        c.setLineWidth(1.2)
        c.line(mx - arm, my, mx + arm, my)
        c.line(mx, my - arm, mx, my + arm)
        c.circle(mx, my, 2, stroke=1, fill=0)
        c.setFillColor(MARK)
        c.setFont("Helvetica", 6)
        c.drawString(mx + 4, my + 4, mark["name"])


def render_nest_pdf(result: dict[str, Any]) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter, pageCompression=0)
    width, height = letter

    def header(title: str) -> None:
        c.setFillColor(GOLD)
        c.rect(0, height - 36, width, 36, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont("Times-Bold", 14)
        c.drawString(36, height - 24, title)
        c.setFont("Helvetica", 8)
        c.drawRightString(width - 36, height - 22, "Empire WoodCraft  ·  X-Carve cut list")

    def footer(page_note: str) -> None:
        c.setStrokeColor(RULE)
        c.line(36, 40, width - 36, 40)
        c.setFillColor(SLATE)
        c.setFont("Helvetica", 8)
        c.drawString(36, 28, page_note)
        c.drawRightString(width - 36, 28, "Sizes as fractions. Never decimals. Wood = true size. Foam = wood. Fabric labeled separately.")

    header(str(result.get("title") or "CNC cut list"))
    c.setFillColor(SLATE)
    c.setFont("Times-Bold", 16)
    c.drawString(36, height - 64, str(result.get("title") or "CNC cut list"))
    c.setFont("Helvetica", 10)
    meta = [
        f'Machine: {result.get("machine")}   width max {result.get("machine_width")}   tile {result.get("tile_length")}',
        f'Kerf / blade width: {result.get("kerf")}   Job: {result.get("job_id") or "—"}',
        "Long panels tile along length. Registration marks on each seam — slide sheet, line up marks, continue.",
    ]
    y = height - 88
    for line in meta:
        c.drawString(36, y, line)
        y -= 14

    c.setFont("Times-Bold", 11)
    c.drawString(36, y - 6, "Cut list")
    y -= 24
    c.setFont("Helvetica", 8)
    headers = ["Part", "Wood (true)", "Foam (= wood)", "Fabric (labeled)", "Grain"]
    xs = [36, 170, 290, 410, 530]
    for htxt, hx in zip(headers, xs):
        c.drawString(hx, y, htxt)
    y -= 4
    c.setStrokeColor(RULE)
    c.line(36, y, width - 36, y)
    y -= 14
    for row in result.get("cut_list") or []:
        if y < 70:
            footer("Cover / cut list")
            c.showPage()
            header(str(result.get("title") or "CNC cut list"))
            y = height - 60
        wood = f'{row["wood_width"]} x {row["wood_length"]}'
        foam = f'{row["foam_width"]} x {row["foam_length"]}'
        fabric = (
            f'{row["fabric_width"]} x {row["fabric_length"]}'
            if row.get("fabric_width")
            else "—"
        )
        c.setFillColor(SLATE)
        c.setFont("Helvetica", 8)
        c.drawString(36, y, str(row.get("name") or row.get("id")))
        c.drawString(170, y, wood)
        c.drawString(290, y, foam)
        c.drawString(410, y, fabric)
        c.drawString(530, y, str(row.get("grain") or "with"))
        y -= 12

    y -= 10
    c.setFont("Times-Bold", 11)
    c.drawString(36, y, "Per-sheet yield")
    y -= 16
    c.setFont("Helvetica", 8)
    for group in ("wood", "foam", "fabric"):
        for item in (result.get("yields") or {}).get(group) or []:
            if y < 70:
                footer("Yield summary")
                c.showPage()
                header(str(result.get("title") or "CNC cut list"))
                y = height - 60
            tile = f'  tile {item["tile_index"]}/{item["tile_count"]}' if item.get("tiled") else ""
            parent = f'  ({item["parent_panel"]})' if item.get("parent_panel") else ""
            c.drawString(
                36,
                y,
                f'{group} sheet {item["index"]}: {item["sheet_width"]} x {item["sheet_length"]}  yield {item["yield"]}{tile}{parent}',
            )
            y -= 12

    footer("Cover / cut list")
    c.showPage()

    for group, key in (("Wood", "wood_sheets"), ("Foam", "foam_sheets"), ("Fabric", "fabric_sheets")):
        for sheet in result.get(key) or []:
            header(f'{group} sheet {sheet["index"]}  ·  yield {sheet["yield"]}')
            _fill_sheet_drawing(c, sheet, 48, 120, width - 96, height - 200)
            c.setFillColor(SLATE)
            c.setFont("Helvetica", 9)
            note = f'Kerf {sheet.get("kerf", result.get("kerf"))} reserved between parts.'
            if sheet.get("tiled"):
                note += (
                    f'  TILE {sheet["tile_index"]} of {sheet["tile_count"]} for {sheet.get("parent_panel")}. '
                    "Line up the red registration marks, clamp, then cut this pass."
                )
            c.drawString(36, 88, note)
            footer(f'{group} sheet {sheet["index"]} yield {sheet["yield"]}')
            c.showPage()

    c.save()
    pdf = buf.getvalue()
    # Guard: sheet sizes printed in the PDF body must not contain decimal inches.
    # ISO dates are not used on these pages.
    return pdf
