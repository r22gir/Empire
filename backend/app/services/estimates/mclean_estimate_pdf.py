"""Client estimate PDF (portrait) — branding aligned to Max McLean golden.

Drawing/field-measurement golden is reference/max-golden/ (landscape).
This module is the separate portrait estimate path (Willard EST-2026-110
geometry). Header language uses NELMA'S WORKROOM / POWERED BY EMPIRE
WORKROOM; do not invent a field-measurement layout here.

Canonical layout reference: backend/app/services/drawing/golden_estimate.pdf
"""
from __future__ import annotations

import logging
import os
import textwrap
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

from reportlab.lib.colors import HexColor, black
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)

MCLEAN_FORMAT_NAME = "mclean_gold"

PAGE_W, PAGE_H = letter
CAR = HexColor("#B98A50")
DK = HexColor("#333333")
GRAY = HexColor("#777777")
RULE = HexColor("#CCCCCC")
DETAIL = HexColor("#555555")

# Brand language aligned to Max drawing golden (McLean) — portrait estimate
# layout remains Willard/EST-2026-110 style, NOT the landscape field set.
COMPANY = "NELMA'S WORKROOM"
TAGLINE = "POWERED BY EMPIRE WORKROOM · CUSTOM UPHOLSTERY & FABRICATION"
ADDRESS = "5124 Frolich Ln, Hyattsville, MD 20781"
PHONE_EMAIL = "(703) 213-6484   |   workroom@empirebox.store"


def _hr(c: canvas.Canvas, y: float, weight: float = 1, col=RULE) -> None:
    c.setStrokeColor(col)
    c.setLineWidth(weight)
    c.line(54, y, PAGE_W - 54, y)


def _money(v: Any) -> str:
    try:
        return f"${float(v):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def _wrap(text: str, width: int = 95) -> List[str]:
    text = (text or "").replace("\n", " ").strip()
    if not text:
        return []
    return textwrap.wrap(text, width=width)


def _fmt_date(raw: Any) -> str:
    if not raw:
        return datetime.now().strftime("%B %d, %Y")
    s = str(raw)
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:26].rstrip("Z"), fmt).strftime("%B %d, %Y")
        except ValueError:
            continue
    return s[:10]


def _title_detail(it: Dict[str, Any]) -> Tuple[str, List[str]]:
    desc = (it.get("description") or "Item").strip()
    if "\n" in desc:
        parts = [p.strip() for p in desc.split("\n") if p.strip()]
        title, details = parts[0], []
        for r in parts[1:]:
            details.extend(_wrap(r, 95))
    elif len(desc) > 78 and ". " in desc:
        idx = desc.find(". ")
        title = desc[: idx + 1]
        details = _wrap(desc[idx + 2 :], 95)
    elif len(desc) > 78:
        title = desc[:75].rstrip() + "…"
        details = _wrap(desc, 95)
    else:
        title, details = desc, []

    fabric = it.get("fabric_name")
    unit = (it.get("unit") or "").lower()
    qty = it.get("quantity")
    rate = it.get("unit_price")
    if rate is None:
        rate = it.get("rate")
    if fabric:
        details.append(f"Fabric: {fabric}")
    if unit in ("yd", "yard", "yards") and qty and rate is not None:
        try:
            details.append(f"{float(qty):g} yd @ {_money(rate)}/yd")
        except (TypeError, ValueError):
            pass
    return title, details


def _amount_label(it: Dict[str, Any], title: str) -> str:
    amount = it.get("subtotal")
    if amount is None:
        amount = it.get("amount")
    if amount is None:
        amount = it.get("final_price")
    try:
        amt_f = float(amount or 0)
    except (TypeError, ValueError):
        amt_f = 0.0
    unit = (it.get("unit") or "").lower()
    low = title.lower()
    if amt_f == 0 and ("tbd" in low or "open question" in low or unit == "note"):
        return "TBD"
    return _money(amt_f)


def _draw_letterhead(c: canvas.Canvas, quote: Dict[str, Any]) -> float:
    c.setFillColor(CAR)
    c.rect(0, PAGE_H - 8, PAGE_W, 8, stroke=0, fill=1)

    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(54, PAGE_H - 64, COMPANY)
    c.setFont("Helvetica", 8.5)
    c.setFillColor(GRAY)
    c.drawString(54, PAGE_H - 78, TAGLINE)
    c.drawString(54, PAGE_H - 90, ADDRESS)
    c.drawString(54, PAGE_H - 102, PHONE_EMAIL)

    qn = quote.get("quote_number") or quote.get("id") or ""
    created = _fmt_date(quote.get("created_at") or quote.get("updated_at"))
    valid_days = int(quote.get("valid_days") or 30)
    status = (quote.get("status") or "draft").upper()

    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(DK)
    c.drawRightString(PAGE_W - 54, PAGE_H - 64, "ESTIMATE")
    c.setFont("Helvetica", 10)
    c.drawRightString(PAGE_W - 54, PAGE_H - 82, f"No. {qn}")
    c.drawRightString(PAGE_W - 54, PAGE_H - 96, f"Date: {created}")
    c.drawRightString(PAGE_W - 54, PAGE_H - 110, f"Valid: {valid_days} days")
    if status in ("DRAFT", "PROPOSAL"):
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(CAR)
        c.drawRightString(PAGE_W - 54, PAGE_H - 124, f"STATUS: {status} — NOT SENT")

    y = PAGE_H - 138
    _hr(c, y)
    return y - 16


def _draw_footer(c: canvas.Canvas, quote: Dict[str, Any], page: int, pages: int) -> None:
    c.setFillColor(CAR)
    c.rect(0, 0, PAGE_W, 6, stroke=0, fill=1)
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(GRAY)
    c.drawCentredString(PAGE_W / 2, 20, "Thank you for the opportunity — Empire Workroom")
    qn = quote.get("quote_number") or ""
    status = (quote.get("status") or "draft").upper()
    stamp = f"Empire Workroom · {qn} · Page {page} of {pages}"
    if status in ("DRAFT", "PROPOSAL"):
        stamp += " · DRAFT — NOT SENT"
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(PAGE_W / 2, 10, stamp)


def _draw_client_block(c: canvas.Canvas, quote: Dict[str, Any], y: float) -> float:
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(GRAY)
    c.drawString(54, y, "PREPARED FOR")
    c.drawString(320, y, "PROJECT SITE")

    c.setFont("Helvetica", 11)
    c.setFillColor(DK)
    client = quote.get("customer_name") or "Client"
    site = quote.get("customer_address") or ""
    c.drawString(54, y - 16, str(client)[:42])
    c.drawString(320, y - 16, str(site)[:42])

    c.setFont("Helvetica", 9.5)
    c.setFillColor(GRAY)
    phone = quote.get("customer_phone") or ""
    attn = ""
    for line in str(quote.get("notes") or "").splitlines():
        if line.lower().startswith("attn"):
            attn = line.strip()
            break
    left2 = attn or (f"Tel: {phone}" if phone else "")
    project = quote.get("project_name") or ""
    material = ""
    for it in quote.get("line_items") or []:
        fab = it.get("fabric_name")
        desc = (it.get("description") or "").lower()
        if fab:
            material = f"Material: {fab}"
            break
        if "apex" in desc:
            material = "Material: Apex Softside Vinyl"
            break
    if left2:
        c.drawString(54, y - 32, left2[:48])
    if material:
        c.drawString(54, y - 46, material[:48])
    if project:
        c.drawString(320, y - 32, str(project)[:48])

    y_rule = y - (60 if material else 48)
    _hr(c, y_rule)
    return y_rule - 20


def _draw_totals(c: canvas.Canvas, quote: Dict[str, Any], y: float) -> float:
    total = float(quote.get("total") or quote.get("subtotal") or 0)
    deposit = quote.get("deposit_required")
    pct = float(quote.get("deposit_percent") or 50)
    if deposit is None:
        deposit = round(total * pct / 100.0, 2)
    else:
        deposit = float(deposit)
    balance = float(quote.get("balance_due") or round(total - deposit, 2))

    _hr(c, y)
    y -= 22
    c.setFont("Helvetica", 10.5)
    c.setFillColor(DK)
    c.drawRightString(PAGE_W - 170, y, "Total")
    c.setFont("Helvetica-Bold", 13)
    c.drawRightString(PAGE_W - 54, y, _money(total))
    y -= 18
    c.setFont("Helvetica", 10)
    c.drawRightString(PAGE_W - 170, y, f"Deposit to begin ({pct:.0f}%)")
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(PAGE_W - 54, y, _money(deposit))
    y -= 16
    c.setFont("Helvetica", 10)
    c.setFillColor(GRAY)
    c.drawRightString(PAGE_W - 170, y, "Balance on completion")
    c.drawRightString(PAGE_W - 54, y, _money(balance))
    return y - 28


def _draw_notes(c: canvas.Canvas, quote: Dict[str, Any], y: float) -> float:
    notes = (quote.get("notes") or "").strip()
    terms = (quote.get("terms") or quote.get("payment_terms") or "").strip()
    lines: List[str] = []
    if notes:
        for raw in notes.splitlines():
            raw = raw.strip()
            if not raw:
                continue
            if raw.startswith("═") or raw.startswith("="):
                break
            if raw.upper().startswith("OPEN QUESTIONS"):
                break
            lines.extend(_wrap(raw, 100))
    if terms:
        lines.extend(_wrap(terms, 100))
    if not lines:
        lines = [
            "50% deposit required before work begins. Balance due upon completion.",
            "Estimate covers fabrication and materials as listed.",
        ]

    _hr(c, y)
    y -= 18
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(GRAY)
    c.drawString(54, y, "NOTES")
    y -= 14
    c.setFont("Helvetica", 8.5)
    c.setFillColor(DETAIL)
    for ln in lines[:12]:
        if y < 60:
            break
        c.drawString(54, y, ln[:110])
        y -= 11
    return y


def _open_questions(quote: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    capturing = False
    for raw in str(quote.get("notes") or "").splitlines():
        s = raw.strip()
        if "OPEN QUESTIONS" in s.upper():
            capturing = True
            continue
        if capturing:
            if s.startswith("═") or s.startswith("INTERNAL"):
                if out:
                    break
                continue
            if s:
                out.append(s)
    for it in quote.get("line_items") or []:
        desc = it.get("description") or ""
        if "OPEN QUESTION" in desc.upper():
            out.append(desc)
    return out


def render_mclean_estimate_bytes(quote: Dict[str, Any]) -> bytes:
    """Render McLean gold estimate PDF bytes from a quote dict."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    items = list(quote.get("line_items") or quote.get("items") or [])
    draw_items = [it for it in items if (it.get("unit") or "").lower() != "note"]
    note_items = [it for it in items if (it.get("unit") or "").lower() == "note"]
    if not draw_items:
        draw_items = items

    y = _draw_letterhead(c, quote)
    y = _draw_client_block(c, quote, y)

    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(GRAY)
    c.drawString(54, y, "#")
    c.drawString(76, y, "DESCRIPTION")
    c.drawRightString(PAGE_W - 54, y, "AMOUNT")
    y -= 8
    _hr(c, y)
    y -= 18

    spilled: List[Dict[str, Any]] = []
    for it in draw_items:
        title, details = _title_detail(it)
        need = 28 + 12.5 * min(len(details), 6)
        if y - need < 150:
            spilled.append(it)
            continue
        c.setFont("Helvetica-Bold", 10.5)
        c.setFillColor(DK)
        c.drawString(54, y, str(it.get("line_number") or ""))
        c.drawString(76, y, title[:78])
        c.drawRightString(PAGE_W - 54, y, _amount_label(it, title))
        y -= 14
        c.setFont("Helvetica", 9)
        c.setFillColor(DETAIL)
        for ln in details[:6]:
            c.drawString(76, y, ln[:95])
            y -= 12.5
        y -= 10

    y = _draw_totals(c, quote, y)
    y = _draw_notes(c, quote, y)

    oq = _open_questions(quote)
    need_p2 = bool(spilled or oq or note_items)
    pages = 2 if need_p2 else 1
    _draw_footer(c, quote, 1, pages)

    if need_p2:
        c.showPage()
        y = _draw_letterhead(c, quote)
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(DK)
        qn = quote.get("quote_number") or ""
        c.drawString(54, y, f"{qn} — Details & Open Questions")
        y -= 18
        _hr(c, y, col=CAR)
        y -= 20

        for it in spilled:
            title, details = _title_detail(it)
            c.setFont("Helvetica-Bold", 10.5)
            c.setFillColor(DK)
            c.drawString(54, y, str(it.get("line_number") or ""))
            c.drawString(76, y, title[:78])
            c.drawRightString(PAGE_W - 54, y, _amount_label(it, title))
            y -= 14
            c.setFont("Helvetica", 9)
            c.setFillColor(DETAIL)
            for ln in details[:8]:
                c.drawString(76, y, ln[:95])
                y -= 12
            y -= 8
            if y < 80:
                break

        if oq or note_items:
            c.setFont("Helvetica-Bold", 10)
            c.setFillColor(CAR)
            c.drawString(54, max(y, 80), "OPEN QUESTIONS — DO NOT INVENT ANSWERS")
            y = max(y, 80) - 16
            c.setFont("Helvetica", 9)
            c.setFillColor(DETAIL)
            seen = set()
            for raw in list(oq) + [it.get("description") or "" for it in note_items]:
                for ln in _wrap(raw, 100):
                    key = ln[:80]
                    if key in seen:
                        continue
                    seen.add(key)
                    if y < 60:
                        break
                    c.drawString(54, y, ln[:110])
                    y -= 12

        status = (quote.get("status") or "draft").upper()
        if status in ("DRAFT", "PROPOSAL"):
            c.setFont("Helvetica-Bold", 9)
            c.setFillColor(GRAY)
            c.drawCentredString(
                PAGE_W / 2,
                48,
                "DRAFT — Not for client issue until open questions resolved",
            )
        _draw_footer(c, quote, 2, 2)

    c.save()
    return buf.getvalue()


def generate_mclean_estimate_pdf(quote_id: str, save: bool = True) -> bytes:
    """Load quote and render McLean gold PDF. Optionally persist to disk."""
    from app.services.quote_service import get_quote
    from app.services.data_paths import quote_pdf_dir

    quote = get_quote(quote_id)
    if not quote:
        raise FileNotFoundError(f"Quote {quote_id} not found")

    pdf_bytes = render_mclean_estimate_bytes(quote)

    if save:
        pdf_dir = str(quote_pdf_dir())
        os.makedirs(pdf_dir, exist_ok=True)
        qn = quote.get("quote_number") or quote_id
        pdf_path = os.path.join(pdf_dir, f"{qn}.pdf")
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)

        alt = f"/home/rg/empire-data/quotes/pdf/{qn}.pdf"
        try:
            os.makedirs(os.path.dirname(alt), exist_ok=True)
            with open(alt, "wb") as f:
                f.write(pdf_bytes)
        except OSError as e:
            logger.warning("Could not mirror PDF to empire-data: %s", e)

        try:
            from app.db.database import get_db

            with get_db() as conn:
                cols = {r[1] for r in conn.execute("PRAGMA table_info(quotes_v2)").fetchall()}
                if "pdf_path" in cols:
                    conn.execute(
                        "UPDATE quotes_v2 SET pdf_path = ? WHERE id = ?",
                        (pdf_path, quote_id),
                    )
        except Exception as e:  # noqa: BLE001
            logger.debug("pdf_path update skipped: %s", e)

        logger.info(
            "McLean gold estimate PDF: %s (%s bytes) format=%s",
            pdf_path,
            len(pdf_bytes),
            MCLEAN_FORMAT_NAME,
        )

    return pdf_bytes
