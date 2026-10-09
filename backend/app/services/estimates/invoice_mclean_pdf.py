"""Client invoice PDF in the estimate's design (McLean landscape chrome).

Same dark header bar, cream paper, fonts, area bands, subtotal bars, totals panel,
notes panel and footer as mclean_estimate_pdf. Title is 'Invoice INV-xxxx'.
Covers deposit, change-order and final invoices: payments & credits applied,
balance due, and the Stripe pay link + QR (balance only) inside the PDF.
"""
from __future__ import annotations

import json
import re
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from app.services.drawing.max_sheet_chrome import GOLD, HAIR, PW, PH, render_chrome_bands
from app.services.estimates import mclean_estimate_pdf as E

_DRY_TEXT = "DRY RUN — NOT ISSUED, NOT SENT"


def _mdy(v: str) -> str:
    v = str(v or "")[:10]
    return f"{v[5:7]}/{v[8:10]}/{v[0:4]}" if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v) else v


def _money(x: float) -> str:
    return f"${float(x or 0):,.2f}"


def _qr_png(url: str):
    try:
        import qrcode
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=6, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        buf = BytesIO()
        qr.make_image().save(buf, format="PNG")
        buf.seek(0)
        return ImageReader(buf)
    except Exception:
        return None


def _snap(inv: dict) -> dict:
    s = inv.get("pricing_snapshot_json") or {}
    if isinstance(s, str):
        try:
            s = json.loads(s)
        except (TypeError, ValueError):
            s = {}
    return s if isinstance(s, dict) else {}


def _title_suffix(inv: dict) -> str:
    snap = _snap(inv)
    co = snap.get("change_order")
    if snap.get("final_settlement"):
        return "Final invoice"
    if isinstance(co, dict) and co.get("number"):
        return f"Change Order {co['number']}"
    stage = str(inv.get("invoice_stage") or "").lower()
    return {"deposit": "Deposit invoice", "progress": "Progress invoice"}.get(stage, "")


def sans_stringwidth(text: str, font: str, size: float) -> float:
    from reportlab.pdfbase.pdfmetrics import stringWidth
    return stringWidth(text or "", font, size)


def _total_rows(inv: dict, accent_pay: Optional[dict]) -> List[Tuple[str, str, str]]:
    """(label, amount text, kind) rows for the totals panel."""
    from app.services import invoice_pdf_service as S
    total = float(inv.get("total") or 0)
    rows: List[Tuple[str, str, str]] = [("Subtotal", _money(inv.get("subtotal")), "n")]
    tax = float(inv.get("tax_amount") or 0)
    rate = float(inv.get("tax_rate") or 0)
    rows.append((f"Tax ({rate * 100:g}%)", _money(tax), "n"))
    rows.append(("Total", _money(total), "total"))
    snap = _snap(inv)
    co = S._change_order(inv)
    schedule = S.uses_job_deposit_schedule(inv)
    if S.final_settlement(inv):
        credits, _prior = S._ledger_for_pdf(inv)
        rows.append(("PAYMENTS & CREDITS APPLIED", "", "head"))
        if not credits:
            rows.append(("No payments received yet", "$0.00", "n"))
        for cr in credits:
            bits = [str(cr.get("label") or "Payment received")]
            if cr.get("payment_date"):
                bits.append(_mdy(cr["payment_date"]))
            if cr.get("invoice_number"):
                bits.append(str(cr["invoice_number"]))
            rows.append((" · ".join(bits), "-" + _money(cr.get("amount")), "n"))
        own = float(inv.get("amount_paid") or 0)
        if own > 0:
            rows.append(("Paid on this invoice", "-" + _money(own), "n"))
        ctotal = round(sum(float(c.get("amount") or 0) for c in credits) + own, 2)
        rows.append(("Total payments & credits", "-" + _money(ctotal), "n"))
        bal = round(total - ctotal, 2)
        rows.append(("Balance due", _money(max(bal, 0)), "due"))
        if bal < 0:
            rows.append(("Credit balance", _money(-bal), "n"))
    else:
        credit = S.credit_schedule(inv) if (co and not schedule) else None
        if credit:
            pct = inv.get("deposit_percent") or co.get("deposit_percent") or 50
            ref = f" · {co['credit_ref']}" if co.get("credit_ref") else ""
            rows.append(("PAYMENTS & CREDITS APPLIED", "", "head"))
            rows.append((f"Deposit received {credit['received_date']}{ref}", "-" + _money(credit["received"]), "n"))
            rows.append((f"Deposit required ({float(pct):g}%)", _money(credit["required"]), "n"))
            rows.append(("Deposit due now", _money(credit["due_now"]), "due"))
            rows.append(("Balance on completion", _money(credit["balance_on_completion"]), "n"))
        elif schedule:
            dep, bal = S.job_deposit_amounts(total)
            rows.append(("50% deposit due", _money(dep), "due"))
            rows.append(("Balance on completion", _money(bal), "n"))
        else:
            paid = float(inv.get("amount_paid") or 0)
            if paid > 0:
                rows.append(("PAYMENTS & CREDITS APPLIED", "", "head"))
                rows.append(("Payments received", "-" + _money(paid), "n"))
            rows.append(("Balance due", _money(float(inv.get("balance_due") if inv.get("balance_due") is not None else total)), "due"))
    return rows


def render_invoice_bytes(invoice: dict, customer: Optional[dict] = None, *, dry_run: bool = False) -> bytes:
    from app.services import invoice_pdf_service as S
    customer = customer or {}
    inv = dict(invoice)
    dry = bool(dry_run or inv.get("_dry_run"))
    serif_b, sans, sans_b, mono = E._ensure_body_fonts()
    name = inv.get("client_name") or customer.get("name") or "Customer"
    email = inv.get("client_email") or customer.get("email") or ""
    phone = inv.get("client_phone") or customer.get("phone") or ""
    addr = inv.get("client_address") or inv.get("billing_address") or customer.get("address") or ""
    num = str(inv.get("invoice_number") or "")
    created = inv.get("invoice_date") or inv.get("created_at") or ""
    suffix = _title_suffix(inv)
    fake_q = {"customer_name": name, "quote_number": num, "created_at": created}
    pay = S.invoice_pay_link(inv)
    total_rows = _total_rows(inv, pay)

    # sections by area, in saved order
    items = list(inv.get("line_items") or [])
    sections: List[Tuple[str, List[dict]]] = []
    for it in items:
        room = str(it.get("room") or "").strip() or "Job-wide"
        if not sections or sections[-1][0] != room:
            sections.append((room, []))
        sections[-1][1].append(it)
    if not sections:
        sections = [("Services as quoted", [{"description": "Services as quoted", "quantity": 1, "unit": "lot",
                                              "total": float(inv.get("subtotal") or 0)}])]

    total_x = PW - E.MARGIN_R
    price_x = total_x - 92
    sqft_x = price_x - 72
    unit_x = sqft_x - 58
    qty_x = unit_x - 48
    desc_w = qty_x - 40 - E.MARGIN_L
    floor = E.CONTENT_BOTTOM + 8

    def chrome(c, page, pages):
        client, project = E._client_project(fake_q)
        render_chrome_bands(c, sheet_no=page, total=pages, right_title="INVOICE",
                            letterhead=E._estimate_bill().letterhead_upper,
                            powered_by=E._estimate_bill().chrome_subheader_upper,
                            client=client, project=num, rev="A", date=E._fmt_date(created),
                            status=_DRY_TEXT if dry else "INVOICE")
        y = E.CONTENT_TOP
        c.setFillColor(E.DK); c.setFont(serif_b, 13)
        title = f"Invoice  {num}" + (f"  ·  {suffix}" if suffix else "")
        c.drawString(E.MARGIN_L, y - 2, title)
        c.setFont(sans, 8); c.setFillColor(E.MUTE)
        due = inv.get("due_date")
        meta = f"Date: {E._fmt_date_long(created)}" + (f"   ·   Due: {_mdy(due)}" if due else "")
        c.drawRightString(PW - E.MARGIN_R, y - 2, meta)
        E._hr(c, y - 10, weight=1.0, col=GOLD)
        if dry:
            c.setFillColor(HexColor_red()); c.setFont(sans_b, 7)
            c.drawString(372, y - 2, _DRY_TEXT)

    def draw(total_pages: int) -> Tuple[bytes, int]:
        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=(PW, PH))
        c.setTitle(f"Invoice {num} — Empire Workroom"); c.setAuthor("Empire Workroom"); c.setCreator("Empire Workroom")
        page = 1
        chrome(c, page, total_pages)
        y = E.CONTENT_TOP - 22

        def new_page():
            nonlocal page, y
            c.showPage(); page += 1
            chrome(c, page, total_pages)
            y = E.CONTENT_TOP - 28

        def need(h):
            if y - h < floor:
                new_page()
                return True
            return False

        # bill-to panel
        ph = 58.0
        E._panel(c, E.MARGIN_L, y - ph, E.CONTENT_W, ph)
        E._section_label(c, E.MARGIN_L + 8, y - 12, "BILL TO", mono)
        E._section_label(c, E.MARGIN_L + E.CONTENT_W * 0.52, y - 12, "PROJECT SITE", mono)
        c.setFont(sans, 10); c.setFillColor(E.DK)
        c.drawString(E.MARGIN_L + 8, y - 26, str(name)[:64])
        c.drawString(E.MARGIN_L + E.CONTENT_W * 0.52, y - 26, str(addr)[:64])
        c.setFont(sans, 8.5); c.setFillColor(E.MUTE)
        if email: c.drawString(E.MARGIN_L + 8, y - 40, str(email)[:64])
        if phone: c.drawString(E.MARGIN_L + 8, y - 52, f"Tel: {phone}")
        terms = str(inv.get("terms") or "")
        if terms: c.drawString(E.MARGIN_L + E.CONTENT_W * 0.52, y - 40, f"Terms: {terms}"[:70])
        y -= ph + 14

        grand = 0.0
        for area, lines in sections:
            first_h = E._line_block_height(lines[0]) if False else 0
            need(18 + 16 + 40)
            E._section_label(c, E.MARGIN_L, y, area, mono); y -= 18
            def cols():
                nonlocal y
                c.setFont(sans_b, 7.5); c.setFillColor(GOLD)
                c.drawString(E.MARGIN_L, y, "Description")
                for x, t in ((qty_x, "Qty"), (unit_x, "Unit"), (sqft_x, "Sq ft"), (price_x, "Price"), (total_x, "Total")):
                    c.drawRightString(x, y, t)
                E._hr(c, y - 4, weight=0.7, col=GOLD); y -= 16
            cols()
            sub = 0.0
            for li, it in enumerate(lines):
                dl = E._description_lines(it, desc_w)
                h = E._DESC_LEADING * len(dl) + E._ROW_GAP
                if need(h + (22 if li == len(lines) - 1 else 0)):
                    cols()
                sq, pps = E._line_sqft(it)
                amt = E._line_amount_value(it)
                sub += amt
                for i, line in enumerate(dl):
                    c.setFont(sans_b if i == 0 else sans, E._DESC_FONT if i == 0 else E._DESC_FONT - 0.5)
                    c.setFillColor(E.DK if i == 0 else E.DETAIL)
                    c.drawString(E.MARGIN_L + (0 if i == 0 else 8), y, line)
                    if i == 0:
                        c.setFont(sans, E._DESC_FONT); c.setFillColor(E.DK)
                        c.drawRightString(qty_x, y, E._qty_text(it))
                        c.drawRightString(unit_x, y, E._unit_text(it))
                        c.drawRightString(sqft_x, y, E.sqft_fraction(sq))
                        price = f"{pps:,.2f}" if (sq is not None and pps is not None) else E._rate_text(it).replace("$", "")
                        c.drawRightString(price_x, y, price)
                        c.drawRightString(total_x, y, E._money(amt))
                    y -= E._DESC_LEADING
                y -= E._ROW_GAP
            need(20)
            y = E._draw_band_subtotal(c, y, f"SUBTOTAL — {area}"[:80], E._money(sub), sans_b, sans)
            grand += sub

        # totals panel
        row_h = 13.0
        panel_w = 330.0
        wrapped: List[Tuple[str, str, str]] = []
        for _l, _a, _k in total_rows:
            if _k == "n":
                avail = panel_w - 24 - sans_stringwidth(_a, sans, 9) - 10
                parts = E._wrap_to_width(_l, sans, 8.5, max(avail, 80)) or [_l]
                wrapped.append((parts[0], _a, "n"))
                wrapped.extend((f"   {x}", "", "n") for x in parts[1:])
            else:
                wrapped.append((_l, _a, _k))
        heights = sum(row_h + (4 if k in ("total", "due") else 0) for _l, _a, k in wrapped) + 14
        need(heights + 20)
        E._hr(c, y, weight=1.0, col=GOLD); y -= 8
        px = PW - E.MARGIN_R - panel_w
        top = y
        c.setFillColor(E.PANEL); c.roundRect(px, top - heights, panel_w, heights, 4, fill=1, stroke=0)
        c.setStrokeColor(GOLD); c.setLineWidth(0.9); c.roundRect(px, top - heights, panel_w, heights, 4, fill=0, stroke=1)
        ry = top - 16
        for label, amt, kind in wrapped:
            if kind == "head":
                c.setFont(mono, 7); c.setFillColor(GOLD); c.drawString(px + 12, ry, label)
            elif kind == "total":
                c.setFont(sans, 8.5); c.setFillColor(E.MUTE); c.drawString(px + 12, ry, label)
                c.setFont(sans_b, 12); c.setFillColor(E.DK); c.drawRightString(px + panel_w - 12, ry, amt); ry -= 4
            elif kind == "due":
                c.setFont(sans_b, 10); c.setFillColor(E.DK); c.drawString(px + 12, ry, label)
                c.setFont(sans_b, 12); c.setFillColor(GOLD); c.drawRightString(px + panel_w - 12, ry, amt); ry -= 4
            else:
                c.setFont(sans, 8.5); c.setFillColor(E.MUTE); c.drawString(px + 12, ry, label)
                c.setFont(sans_b if False else sans, 9); c.setFillColor(E.DK); c.drawRightString(px + panel_w - 12, ry, amt)
            ry -= row_h
        # earlier-invoice note to the left of the totals panel
        if S.final_settlement(inv):
            _credits, prior = S._ledger_for_pdf(inv)
            if prior:
                txt = "Earlier invoices on this job: " + "; ".join(
                    f"{p.get('invoice_number')} ({_money(p.get('total'))}, paid {_money(p.get('paid'))})" for p in prior
                ) + ". Their payments are applied; their open balances are replaced by this invoice."
                ly = top - 16
                c.setFont(sans, 7.5); c.setFillColor(E.MUTE)
                for ln in E._wrap_to_width(txt, sans, 7.5, px - E.MARGIN_L - 20):
                    c.drawString(E.MARGIN_L, ly, ln); ly -= 10
        y = top - heights - 14

        # pay box (balance only)
        if pay:
            bh = 84.0
            need(bh + 10)
            E._panel(c, E.MARGIN_L, y - bh, E.CONTENT_W, bh)
            qr = _qr_png(pay["url"])
            tx = E.MARGIN_L + 14
            if qr:
                c.drawImage(qr, E.MARGIN_L + 10, y - bh + 6, width=72, height=72)
                tx = E.MARGIN_L + 96
            E._section_label(c, tx, y - 16, "PAY ONLINE", mono)
            label = f"{pay['label']}: {_money(pay['amount'])}"
            c.setFont(sans_b, 13); c.setFillColor(GOLD)
            c.drawString(tx, y - 40, label)
            c.linkURL(pay["url"], (tx, y - 46, tx + c.stringWidth(label, sans_b, 13), y - 34), relative=0)
            c.setStrokeColor(GOLD); c.setLineWidth(0.6)
            c.line(tx, y - 43, tx + c.stringWidth(label, sans_b, 13), y - 43)
            c.setFont(sans, 8); c.setFillColor(E.MUTE)
            c.drawString(tx, y - 56, "Click the link or scan the code to pay securely by card (Stripe). Link does not expire.")
            url_font = 7.5
            while c.stringWidth(pay["url"], mono, url_font) > E.CONTENT_W - (tx - E.MARGIN_L) - 12 and url_font > 5:
                url_font -= 0.5
            c.setFont(mono, url_font); c.setFillColor(GOLD)
            c.drawString(tx, y - 70, pay["url"])
            c.linkURL(pay["url"], (tx, y - 74, tx + c.stringWidth(pay["url"], mono, url_font), y - 64), relative=0)
            if qr:
                c.linkURL(pay["url"], (E.MARGIN_L + 10, y - bh + 6, E.MARGIN_L + 82, y - bh + 78), relative=0)
            y -= bh + 12

        # notes panel
        note_parts: List[str] = []
        if S.uses_job_deposit_schedule(inv):
            note_parts.append(S.JOB_DEPOSIT_SCHEDULE_NOTE)
        cn = S.client_visible_notes(inv.get("notes"))
        if cn:
            note_parts.append(cn)
        lines: List[str] = []
        for part in note_parts:
            for raw in str(part).splitlines():
                lines.extend(E._wrap_to_width(E.inches_to_fractions(S._plain(raw)), sans, 8, E.CONTENT_W - 20))
        if lines:
            rem = lines
            while rem:
                cap = int((y - floor - 24) // 9.5)
                if cap < 2:
                    new_page(); continue
                take, rem = rem[:cap], rem[cap:]
                bh = 22 + 9.5 * len(take)
                E._panel(c, E.MARGIN_L, y - bh, E.CONTENT_W, bh)
                E._section_label(c, E.MARGIN_L + 8, y - 12, "NOTES", mono)
                c.setFont(sans, 8); c.setFillColor(E.DETAIL)
                ny = y - 24
                for ln in take:
                    c.drawString(E.MARGIN_L + 8, ny, ln); ny -= 9.5
                y -= bh + 8
                if rem:
                    new_page()
        c.save()
        return buf.getvalue(), page

    first, pages = draw(1)
    if pages == 1:
        return first
    return draw(pages)[0]


def HexColor_red():
    from reportlab.lib.colors import HexColor
    return HexColor("#b3261e")
