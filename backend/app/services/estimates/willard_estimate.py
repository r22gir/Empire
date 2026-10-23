"""Willard area-layout estimate PDF (Rafael 2026-10-23).

Default client (client_simple): one short line per area + price.
Detailed client: ITEM · DESCRIPTION · QTY · TOTAL.
Internal: ITEM · DESCRIPTION · QTY · RATE · AMOUNT · MARKUP · TOTAL.

Layout knobs live on ``WillardLayout``. Never embed live client jobs here.
"""
from __future__ import annotations

from io import BytesIO

from reportlab.pdfgen import canvas

from app.config.workroom_billing import resolve_quote_billing
from app.services.drawing.max_sheet_chrome import (
    FTR_H,
    GOLD,
    HAIR,
    HDR_H,
    INK,
    MUTE,
    PH,
    PW,
    render_chrome_bands,
)
from app.services.estimates.header_b import billing_for, body_fonts
from app.services.estimates.rafael_format import (
    FORMAT_ID,
    VARIANT_CLIENT,
    VARIANT_CLIENT_SIMPLE,
    VARIANT_DEFAULT,
    VARIANT_INTERNAL,
    WillardLayout,
    DEFAULT_LAYOUT,
    apply_client,
    format_measurement_text,
    format_rate_label,
    is_com_line,
    item_label,
    markup_label,
    money,
    money_round,
    normalize_variant,
    packet_to_areas,
    quote_to_areas,
    scrub_brands,
    simple_area_blurb,
    simple_com_line,
    simple_includes_line,
    totals_from_areas,
)
from app.services.fabric_codes import client_fabric_line


def _bill_for(doc: dict):
    if doc.get("rooms") or doc.get("prepared_for"):
        return billing_for(doc)
    return resolve_quote_billing(doc)


def _wrap(text: str, limit: int) -> list[str]:
    words = format_measurement_text(scrub_brands(text or "")).split()
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


def _line_base(line: dict) -> float | None:
    if is_com_line(line):
        return None
    if line.get("base_amount") is not None:
        try:
            return float(line["base_amount"])
        except (TypeError, ValueError):
            return None
    for key in ("amount", "subtotal"):
        if line.get(key) is not None:
            try:
                return float(line[key])
            except (TypeError, ValueError):
                continue
    try:
        qty = float(line.get("quantity") or 1)
        rate = line.get("base_rate", line.get("rate", line.get("unit_price")))
        if rate is None:
            return None
        return money_round(qty * float(rate))
    except (TypeError, ValueError):
        return None


def _qty_text(line: dict) -> str:
    qty = line.get("quantity")
    unit = str(line.get("unit") or "").strip()
    try:
        qty_txt = f"{float(qty):g}" if qty not in (None, "") else ""
    except (TypeError, ValueError):
        qty_txt = str(qty or "")
    return f"{qty_txt} {unit}".strip()


def _money_or_com(value: float | None) -> str:
    if value is None:
        return "COM"
    return money(value)


def _areas(doc: dict) -> list[dict]:
    if doc.get("areas") or doc.get("rooms"):
        return packet_to_areas(doc)
    return quote_to_areas(doc)


def _chrome_meta(doc: dict, variant: str, page: int, pages: int, bill) -> None:
    pass


def render_willard_estimate(
    doc: dict,
    *,
    variant: str = VARIANT_DEFAULT,
    layout: WillardLayout | None = None,
) -> bytes:
    layout = layout or DEFAULT_LAYOUT
    variant = normalize_variant(variant)
    if variant == VARIANT_CLIENT_SIMPLE:
        return render_willard_simple(doc, layout=layout)
    bill = _bill_for(doc)
    areas = _areas(doc)
    totals = totals_from_areas(areas, doc)
    number = doc.get("quote_number") or doc.get("id") or "EST-DRAFT"
    rev = str(doc.get("rev") or (doc.get("metadata") or {}).get("revision") or "C")
    date = str(doc.get("date") or str(doc.get("created_at") or "23 OCT 2026"))
    if re_iso := __import__("re").match(r"(\d{4})-(\d{2})-(\d{2})", date):
        months = "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split()
        date = f"{int(re_iso.group(3)):02d} {months[int(re_iso.group(2)) - 1]} {re_iso.group(1)}"
    title_right = "ESTIMATE · REV C"
    if variant == VARIANT_INTERNAL:
        title_right += " · INTERNAL"
    client = str(
        (doc.get("prepared_for") or {}).get("company")
        or doc.get("customer_name")
        or "CLIENT"
    )
    project = str(
        (doc.get("project") or {}).get("name")
        or doc.get("project_name")
        or "PROJECT"
    )
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(PW, PH))
    c.setTitle(f"{title_right} {number}")
    c.setAuthor(bill.pdf_author if hasattr(bill, "pdf_author") else bill.name)
    c.setCreator(bill.name)
    c.setSubject(f"{title_right} — {FORMAT_ID}")
    serif, sans, sans_b, mono = body_fonts()
    try:
        from reportlab.pdfbase.pdfmetrics import getFont
        getFont("DejaVuSansMono-Bold")
        mono_b = "DejaVuSansMono-Bold"
    except Exception:
        mono_b = sans_b
    floor = FTR_H + 16

    specs = list(doc.get("specifications") or [])
    notes = format_measurement_text(scrub_brands(str(doc.get("notes") or "")))
    pending = list(doc.get("pending") or doc.get("internal_notes") or [])

    # Paginate: one area can split; last page gets rollup + totals.
    pages: list[list] = [[]]
    y = PH - layout.body_start_y

    def new_page() -> float:
        pages.append([])
        return PH - 66.0

    def room(need: float) -> None:
        nonlocal y
        if y - need < floor + 10:
            y = new_page()

    if specs:
        pages[-1].append(("title",))
        pages[-1].append(("specs", specs))
        y -= 50 + 10.4 * len(specs)
    else:
        pages[-1].append(("title",))
        y -= 28

    for area in areas:
        room(36)
        pages[-1].append(("area", area["name"]))
        y -= 14
        for group in area.get("groups") or []:
            room(20)
            pages[-1].append(("group", group["name"]))
            y -= 10
            for line in group.get("lines") or []:
                wrapped = _wrap(str(line.get("description") or "Item"), layout.wrap_chars)
                fabric = client_fabric_line(line)
                if fabric:
                    wrapped.append(f"Fabric: {fabric}")
                need = layout.line_leading * len(wrapped) + 2.5
                room(need + 4)
                pages[-1].append(("line", line, wrapped))
                y -= need
            room(16)
            pages[-1].append(("gsub", group["name"], group["subtotal"]))
            y -= 14
        room(18)
        pages[-1].append(("asub", area["name"], area["subtotal"]))
        y -= 16

    room(64)
    pages[-1].append(("rollup", areas, totals))
    if variant == VARIANT_INTERNAL and pending:
        pages[-1].append(("pending", pending))
    elif notes or variant == VARIANT_CLIENT:
        pages[-1].append(("notes", notes or "Measurements in fractions. Fabric COM uses internal codes only."))

    total_pages = len(pages)
    for index, ops in enumerate(pages, start=1):
        status = (
            "PRELIMINARY"
            if (doc.get("status") or "draft").lower() in {"draft", "proposal", ""}
            else "FOR DISCUSSION"
        )
        render_chrome_bands(
            c,
            sheet_no=index,
            total=total_pages,
            right_title=title_right,
            letterhead=bill.letterhead_upper,
            powered_by=bill.chrome_subheader_upper,
            client=client,
            project=project,
            rev=rev,
            date=date,
            status=status,
            locale=bill.chrome_locale,
        )
        y = PH - layout.title_y
        heading = str(
            (doc.get("project") or {}).get("phase")
            or doc.get("project_name")
            or "ESTIMATE"
        )
        if index > 1:
            heading = f"{heading} - PRICING (CONT.)"
        c.setFillColor(INK)
        c.setFont(serif, 15 if index == 1 else 13)
        c.drawString(layout.margin_l, y, heading.upper() if heading.isupper() or index == 1 else heading)
        y = PH - layout.subtitle_y
        if index == 1:
            c.setFillColor(MUTE)
            c.setFont(sans, 8.2)
            scope = (doc.get("project") or {}).get("scope") or doc.get("project_description") or ""
            if scope:
                c.drawString(layout.margin_l, y, format_measurement_text(str(scope))[:140])
            y = PH - layout.body_start_y
        else:
            y = PH - 82

        def section(label: str, y0: float) -> float:
            c.setFillColor(GOLD)
            c.setFont(mono_b, 7.0)
            spaced = "  ".join(label.upper())
            c.drawString(layout.margin_l, y0, spaced)
            c.setStrokeColor(GOLD)
            c.setLineWidth(0.8)
            c.line(layout.margin_l, y0 - 3, layout.content_right, y0 - 3)
            return y0 - 14

        def col_headers(y0: float) -> float:
            c.setFillColor(MUTE)
            c.setFont(mono, 5.8)
            if variant == VARIANT_INTERNAL:
                cols = (
                    (layout.col_item, "ITEM", "start"),
                    (layout.col_desc, "DESCRIPTION", "start"),
                    (layout.col_qty, "QTY", "end"),
                    (layout.col_rate, "RATE", "end"),
                    (layout.col_amount, "AMOUNT", "end"),
                    (layout.col_markup, "MARKUP", "end"),
                    (layout.col_total, "TOTAL", "end"),
                )
            else:
                cols = (
                    (layout.col_item, "ITEM", "start"),
                    (layout.col_desc, "DESCRIPTION", "start"),
                    (layout.col_qty, "QTY", "end"),
                    (layout.col_total, "TOTAL", "end"),
                )
            for x, t, an in cols:
                if an == "end":
                    c.drawRightString(x, y0, t)
                else:
                    c.drawString(x, y0, t)
            y1 = y0 - 5
            c.setStrokeColor(INK)
            c.setLineWidth(0.8)
            c.line(layout.margin_l, y1, layout.content_right, y1)
            return y1 - 10

        def draw_money_row(y0: float, base: float | None, *, bold: bool = False) -> None:
            font = mono_b if bold else mono
            size = 7.4 if bold else 6.8
            c.setFont(font, size)
            c.setFillColor(INK)
            if variant == VARIANT_INTERNAL:
                c.drawRightString(layout.col_amount, y0, _money_or_com(base))
                c.drawRightString(
                    layout.col_total, y0,
                    "COM" if base is None else money(apply_client(base, doc)),
                )
            else:
                c.drawRightString(
                    layout.col_total, y0,
                    "COM" if base is None else money(apply_client(base, doc)),
                )

        showed_cols = False
        for op in ops:
            kind = op[0]
            if kind == "title":
                y = section("PRICING" if index == 1 else "PRICING (CONT.)", y)
                y = col_headers(y)
                showed_cols = True
            elif kind == "specs":
                y = section("SPECIFICATIONS", PH - layout.body_start_y)
                c.setFont(sans, 6.8)
                for spec in op[1]:
                    c.setFillColor(GOLD)
                    c.drawString(layout.margin_l, y, "▪")
                    c.setFillColor(INK)
                    for ln in _wrap(str(spec), 150):
                        c.drawString(layout.margin_l + 10, y, ln)
                        y -= 8.4
                    y -= 2
                y = section("PRICING", y + 2)
                y = col_headers(y)
                showed_cols = True
            elif kind == "area":
                if not showed_cols:
                    y = col_headers(y)
                    showed_cols = True
                c.setFillColor(INK)
                c.setFont(serif, 8.0)
                c.drawString(layout.margin_l, y, str(op[1]))
                y -= 11
            elif kind == "group":
                c.setFillColor(GOLD)
                c.setFont(mono_b, 6.4)
                c.drawString(layout.col_desc, y, str(op[1]).upper())
                y -= 9
            elif kind == "line":
                line, wrapped = op[1], op[2]
                base = _line_base(line)
                c.setFillColor(MUTE)
                c.setFont(mono, 6.8)
                c.drawString(layout.col_item, y, item_label(line)[:14])
                c.setFillColor(INK)
                c.setFont(sans, 6.9)
                for i, ln in enumerate(wrapped):
                    c.drawString(layout.col_desc, y - i * layout.line_leading, ln[:92])
                c.setFont(mono, 6.8)
                c.drawRightString(layout.col_qty, y, _qty_text(line))
                if variant == VARIANT_INTERNAL:
                    c.drawRightString(layout.col_rate, y, format_rate_label(line) if base is not None or is_com_line(line) else "")
                    if is_com_line(line) or base is None:
                        c.drawRightString(layout.col_amount, y, "COM")
                        c.drawRightString(layout.col_total, y, "COM")
                    else:
                        c.drawRightString(layout.col_amount, y, money(base))
                        c.setFillColor(MUTE)
                        c.drawRightString(layout.col_markup, y, markup_label(line, doc))
                        c.setFillColor(INK)
                        c.setFont(mono_b, 7.0)
                        c.drawRightString(layout.col_total, y, money(apply_client(base, doc)))
                else:
                    c.setFont(mono_b, 7.0)
                    c.drawRightString(
                        layout.col_total, y,
                        "COM" if is_com_line(line) or base is None else money(apply_client(base, doc)),
                    )
                y -= layout.line_leading * len(wrapped) + 2.5
            elif kind == "gsub":
                c.setFillColor(MUTE)
                c.setFont(mono_b, 6.6)
                c.drawString(layout.col_desc, y, f"{str(op[1]).title()} subtotal")
                draw_money_row(y, float(op[2]), bold=True)
                y -= 4
                c.setStrokeColor(HAIR)
                c.setLineWidth(0.5)
                c.line(450, y, layout.content_right, y)
                y -= 9
            elif kind == "asub":
                label = str(op[1]).split(" (")[0] + " - AREA TOTAL"
                c.setFillColor(GOLD)
                c.setFont(mono_b, 7.4)
                c.drawString(layout.col_desc, y, label)
                c.setFillColor(INK)
                draw_money_row(y, float(op[2]), bold=True)
                y -= 14
            elif kind == "rollup":
                y -= 4
                for area in op[1]:
                    c.setFillColor(INK)
                    c.setFont(mono, 7.0)
                    c.drawString(layout.col_desc, y, str(area["name"]).split(" (")[0])
                    draw_money_row(y, float(area["subtotal"]))
                    y -= 12
                y -= 12
                c.setStrokeColor(INK)
                c.setLineWidth(0.8)
                c.line(450, y, layout.content_right, y)
                y -= 18
                t = op[2]
                c.setFillColor(GOLD)
                c.setFont(mono_b, 7.2)
                c.drawString(layout.col_desc, y, "GRAND TOTAL")
                c.setFillColor(INK)
                if variant == VARIANT_INTERNAL:
                    c.setFont(mono_b, 8.6)
                    c.drawRightString(layout.col_amount, y, money(t["base"]))
                    c.setFont(mono_b, 10.0)
                    c.drawRightString(layout.col_total, y, money(t["client"]))
                else:
                    c.setFont(mono_b, 10.0)
                    c.drawRightString(layout.col_total, y, money(t["client"]))
                y -= 16
                if variant == VARIANT_INTERNAL:
                    share = doc.get("designer_share_20pct")
                    if share is None:
                        share = money_round(t["client"] - t["base"])
                    else:
                        share = money_round(float(share))
                    c.setFillColor(GOLD)
                    c.setFont(mono_b, 7.2)
                    c.drawString(layout.col_desc, y, "MARKUP 20% (DESIGNER)")
                    c.setFillColor(INK)
                    c.setFont(mono_b, 8.6)
                    c.drawRightString(layout.col_total, y, money(share))
                    y -= 16
                c.setFillColor(INK)
                c.setFont(mono, 7.2)
                c.drawString(layout.col_desc, y, f"DEPOSIT ({t['deposit_percent']:.0f}%)")
                c.drawRightString(layout.col_total, y, money(t["deposit"]))
                y -= 14
                c.setFont(mono_b, 7.2)
                c.drawString(layout.col_desc, y, "BALANCE")
                c.drawRightString(layout.col_total, y, money(t["balance"]))
                y -= 16
            elif kind == "notes":
                y = section("NOTES", y + 4)
                c.setFont(sans, 6.8)
                for bullet in [b for b in str(op[1]).splitlines() if b.strip()] or [str(op[1])]:
                    c.setFillColor(GOLD)
                    c.drawString(layout.margin_l, y, "▪")
                    c.setFillColor(INK)
                    for ln in _wrap(bullet, 150):
                        c.drawString(layout.margin_l + 10, y, ln)
                        y -= 8.4
                    y -= 2
            elif kind == "pending":
                y = section("PENDING - INTERNAL", y + 4)
                c.setFont(sans, 6.8)
                for bullet in op[1]:
                    c.setFillColor(GOLD)
                    c.drawString(layout.margin_l, y, "▪")
                    c.setFillColor(INK)
                    for ln in _wrap(str(bullet), 150):
                        c.drawString(layout.margin_l + 10, y, ln)
                        y -= 8.4
                    y -= 2
        c.showPage()
    c.save()
    return buf.getvalue()


def render_willard_simple(doc: dict, *, layout: WillardLayout | None = None) -> bytes:
    """Easy-read client sheet: one line per area, includes, COM, totals."""
    layout = layout or DEFAULT_LAYOUT
    bill = _bill_for(doc)
    areas = _areas(doc)
    totals = totals_from_areas(areas, doc)
    number = doc.get("quote_number") or doc.get("id") or "EST-DRAFT"
    rev = str(doc.get("rev") or (doc.get("metadata") or {}).get("revision") or "C")
    date = str(doc.get("date") or str(doc.get("created_at") or "23 OCT 2026"))
    if re_iso := __import__("re").match(r"(\d{4})-(\d{2})-(\d{2})", date):
        months = "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split()
        date = f"{int(re_iso.group(3)):02d} {months[int(re_iso.group(2)) - 1]} {re_iso.group(1)}"
    client = str(
        (doc.get("prepared_for") or {}).get("company")
        or doc.get("customer_name")
        or "CLIENT"
    )
    project = str(
        (doc.get("project") or {}).get("name")
        or doc.get("project_name")
        or "PROJECT"
    )
    heading = str(
        (doc.get("project") or {}).get("phase")
        or doc.get("project_name")
        or "ESTIMATE"
    )
    scope = (doc.get("project") or {}).get("scope") or doc.get("project_description") or ""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(PW, PH))
    title_right = "ESTIMATE · REV C"
    c.setTitle(f"{title_right} {number}")
    c.setAuthor(bill.pdf_author if hasattr(bill, "pdf_author") else bill.name)
    c.setCreator(bill.name)
    c.setSubject(f"{title_right} — {FORMAT_ID} — client_simple")
    serif, sans, sans_b, mono = body_fonts()
    try:
        from reportlab.pdfbase.pdfmetrics import getFont
        getFont("DejaVuSansMono-Bold")
        mono_b = "DejaVuSansMono-Bold"
    except Exception:
        mono_b = sans_b
    status = (
        "PRELIMINARY"
        if (doc.get("status") or "draft").lower() in {"draft", "proposal", ""}
        else "FOR DISCUSSION"
    )
    render_chrome_bands(
        c,
        sheet_no=1,
        total=1,
        right_title=title_right,
        letterhead=bill.letterhead_upper,
        powered_by=bill.chrome_subheader_upper,
        client=client,
        project=project,
        rev=rev,
        date=date,
        status=status,
        locale=bill.chrome_locale,
    )
    y = PH - 78
    c.setFillColor(INK)
    c.setFont(serif, 16)
    c.drawString(layout.margin_l, y, heading.upper())
    y -= 20
    if scope:
        c.setFillColor(MUTE)
        c.setFont(sans, 9)
        c.drawString(layout.margin_l, y, format_measurement_text(str(scope))[:140])
        y -= 36
    else:
        y -= 28

    for area in areas:
        blurb = simple_area_blurb(area)
        wrapped = _wrap(blurb, 118)
        price = apply_client(float(area.get("subtotal") or 0), doc)
        c.setFillColor(INK)
        c.setFont(serif, 11)
        for i, ln in enumerate(wrapped):
            c.drawString(layout.margin_l, y - i * 16, ln)
        c.setFont(mono_b, 12)
        c.drawRightString(layout.content_right, y, money(price))
        y -= 16 * len(wrapped) + 22

    y -= 8
    includes = simple_includes_line(areas)
    com = simple_com_line(areas)
    c.setFillColor(MUTE)
    c.setFont(sans, 9.5)
    if includes:
        c.drawString(layout.margin_l, y, includes)
        y -= 16
    if com:
        c.drawString(layout.margin_l, y, com)
        y -= 28
    else:
        y -= 16

    y -= 10
    c.setStrokeColor(INK)
    c.setLineWidth(0.9)
    c.line(450, y, layout.content_right, y)
    y -= 20
    c.setFillColor(GOLD)
    c.setFont(mono_b, 8.2)
    c.drawString(layout.margin_l, y, "GRAND TOTAL")
    c.setFillColor(INK)
    c.setFont(mono_b, 14)
    c.drawRightString(layout.content_right, y, money(totals["client"]))
    y -= 24
    c.setFillColor(INK)
    c.setFont(sans, 10)
    c.drawString(layout.margin_l, y, f"Deposit ({totals['deposit_percent']:.0f}%)")
    c.setFont(mono_b, 11)
    c.drawRightString(layout.content_right, y, money(totals["deposit"]))
    y -= 20
    c.setFont(sans_b, 10)
    c.drawString(layout.margin_l, y, "Balance")
    c.setFont(mono_b, 11)
    c.drawRightString(layout.content_right, y, money(totals["balance"]))
    c.showPage()
    c.save()
    return buf.getvalue()


def render_willard_pair(doc: dict, *, layout: WillardLayout | None = None) -> tuple[bytes, bytes]:
    return (
        render_willard_estimate(doc, variant=VARIANT_CLIENT_SIMPLE, layout=layout),
        render_willard_estimate(doc, variant=VARIANT_INTERNAL, layout=layout),
    )


def render_max_estimate_pdf(doc: dict, *, variant: str = VARIANT_DEFAULT) -> bytes:
    return render_willard_estimate(doc, variant=variant)
