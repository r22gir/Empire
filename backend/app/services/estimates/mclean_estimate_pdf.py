"""Client estimate PDF — McLean landscape chrome (founder gold standard).

Drawing/field-measurement golden remains reference/max-golden/ (11-sheet
field set). Client **estimates** share that same landscape letter geometry
+ header/footer chrome (cream paper, dark bands, Nelma/Empire language)
via max_sheet_chrome.render_chrome_bands.

Body content stays estimate-shaped (line items, totals, notes) — this is
NOT a field-measurement sheet. Prior Willard EST-2026-110 portrait layout
is retired for Max client estimates.

Canonical chrome: backend/app/services/drawing/max_sheet_chrome.py
Golden doc: reference/max-golden/GOLDEN.md
"""
from __future__ import annotations

import logging
import os
import textwrap
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Tuple

from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app.services.drawing.max_sheet_chrome import (
    FTR_H,
    GOLD,
    HAIR,
    HDR_H,
    INK,
    MUTE,
    PAPER,
    PH,
    PW,
    render_chrome_bands,
)

logger = logging.getLogger(__name__)

MCLEAN_FORMAT_NAME = "mclean_gold_landscape"

MARGIN_L = 30.0
MARGIN_R = 30.0
CONTENT_TOP = PH - HDR_H - 16.0
CONTENT_BOTTOM = FTR_H + 16.0
CONTENT_W = PW - MARGIN_L - MARGIN_R

RULE = HAIR
DETAIL = MUTE
DK = INK
PANEL = HexColor("#efe9dc")

_FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
_FONTS_READY = False


def _ensure_body_fonts() -> Tuple[str, str, str, str]:
    """Serif bold / sans / sans bold / mono for estimate body."""
    global _FONTS_READY
    serif_b = "DejaVuSerif-Bold"
    sans = "DejaVuSans"
    sans_b = "DejaVuSans-Bold"
    mono = "DejaVuSansMono"
    if not _FONTS_READY:
        for name, fn in (
            (serif_b, "DejaVuSerif-Bold.ttf"),
            (sans, "DejaVuSans.ttf"),
            (sans_b, "DejaVuSans-Bold.ttf"),
            (mono, "DejaVuSansMono.ttf"),
        ):
            p = _FONT_DIR / fn
            if p.is_file():
                try:
                    pdfmetrics.registerFont(TTFont(name, str(p)))
                except Exception:
                    pass
        _FONTS_READY = True

    def pick(preferred: str, fallback: str) -> str:
        try:
            pdfmetrics.getFont(preferred)
            return preferred
        except Exception:
            return fallback

    return (
        pick(serif_b, "Times-Bold"),
        pick(sans, "Helvetica"),
        pick(sans_b, "Helvetica-Bold"),
        pick(mono, "Courier"),
    )


def _money(v: Any) -> str:
    try:
        return f"${float(v):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def _wrap(text: str, width: int = 110) -> List[str]:
    text = (text or "").replace("\n", " ").strip()
    if not text:
        return []
    return textwrap.wrap(text, width=width)


def _fmt_date(raw: Any) -> str:
    if not raw:
        return datetime.now().strftime("%d %b %Y").upper()
    s = str(raw)
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:26].rstrip("Z"), fmt).strftime("%d %b %Y").upper()
        except ValueError:
            continue
    return s[:10]


def _fmt_date_long(raw: Any) -> str:
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
            details.extend(_wrap(r, 110))
    elif len(desc) > 90 and ". " in desc:
        idx = desc.find(". ")
        title = desc[: idx + 1]
        details = _wrap(desc[idx + 2 :], 110)
    elif len(desc) > 90:
        title = desc[:87].rstrip() + "…"
        details = _wrap(desc, 110)
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


def _hr(c: canvas.Canvas, y: float, weight: float = 0.8, col=RULE) -> None:
    c.setStrokeColor(col)
    c.setLineWidth(weight)
    c.line(MARGIN_L, y, PW - MARGIN_R, y)


def _client_project(quote: Dict[str, Any]) -> Tuple[str, str]:
    client = str(quote.get("customer_name") or "CLIENT").strip()
    project = str(
        quote.get("project_name")
        or quote.get("customer_address")
        or quote.get("quote_number")
        or "ESTIMATE"
    ).strip()
    # Keep header project line readable
    if len(client) > 36:
        client = client[:33] + "…"
    if len(project) > 40:
        project = project[:37] + "…"
    return client, project


def _status_banner(quote: Dict[str, Any]) -> str:
    status = (quote.get("status") or "draft").upper()
    if status in ("DRAFT", "PROPOSAL"):
        return "DRAFT — NOT FOR CLIENT ISSUE"
    return "FOR DISCUSSION - NOT FOR CONSTRUCTION"


def _paint_page_chrome(c: canvas.Canvas, quote: Dict[str, Any], page: int, pages: int) -> None:
    client, project = _client_project(quote)
    qn = quote.get("quote_number") or quote.get("id") or "ESTIMATE"
    created = _fmt_date(quote.get("created_at") or quote.get("updated_at"))
    render_chrome_bands(
        c,
        sheet_no=page,
        total=pages,
        right_title="ESTIMATE",
        client=client,
        project=project,
        rev="A",
        date=created,
        status=_status_banner(quote),
    )
    # Estimate meta strip under header
    serif_b, sans, sans_b, mono = _ensure_body_fonts()
    y = CONTENT_TOP
    c.setFillColor(DK)
    c.setFont(serif_b, 13)
    c.drawString(MARGIN_L, y - 2, f"Estimate  {qn}")
    c.setFont(sans, 8)
    c.setFillColor(MUTE)
    valid_days = int(quote.get("valid_days") or 30)
    c.drawRightString(
        PW - MARGIN_R,
        y - 2,
        f"Date: {_fmt_date_long(quote.get('created_at') or quote.get('updated_at'))}"
        f"   ·   Valid: {valid_days} days",
    )
    _hr(c, y - 10, weight=1.0, col=GOLD)


def _draw_client_block(c: canvas.Canvas, quote: Dict[str, Any], y: float) -> float:
    _, sans, sans_b, mono = _ensure_body_fonts()
    c.setFont(sans_b, 7.5)
    c.setFillColor(GOLD)
    c.drawString(MARGIN_L, y, "PREPARED FOR")
    c.drawString(MARGIN_L + CONTENT_W * 0.52, y, "PROJECT SITE")

    c.setFont(sans, 10)
    c.setFillColor(DK)
    client = quote.get("customer_name") or "Client"
    site = quote.get("customer_address") or ""
    c.drawString(MARGIN_L, y - 14, str(client)[:56])
    c.drawString(MARGIN_L + CONTENT_W * 0.52, y - 14, str(site)[:56])

    c.setFont(sans, 8.5)
    c.setFillColor(MUTE)
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
    yy = y - 28
    if left2:
        c.drawString(MARGIN_L, yy, left2[:56])
        yy -= 12
    if material:
        c.drawString(MARGIN_L, yy, material[:56])
    if project:
        c.drawString(MARGIN_L + CONTENT_W * 0.52, y - 28, str(project)[:56])

    y_rule = y - (52 if material else 40)
    _hr(c, y_rule)
    return y_rule - 14


def _draw_totals(c: canvas.Canvas, quote: Dict[str, Any], y: float) -> float:
    _, sans, sans_b, _ = _ensure_body_fonts()
    total = float(quote.get("total") or quote.get("subtotal") or 0)
    deposit = quote.get("deposit_required")
    pct = float(quote.get("deposit_percent") or 50)
    if deposit is None:
        deposit = round(total * pct / 100.0, 2)
    else:
        deposit = float(deposit)
    computed_balance = round(total - deposit, 2)
    raw_balance = quote.get("balance_due")
    try:
        raw_f = float(raw_balance) if raw_balance is not None else None
    except (TypeError, ValueError):
        raw_f = None
    # Prefer computed remainder; ignore stale balance_due that equals total
    # or is otherwise inconsistent with deposit.
    if raw_f is None or abs(raw_f - total) < 0.005 or abs(raw_f - computed_balance) > 0.02:
        balance = computed_balance
    else:
        balance = raw_f

    _hr(c, y, weight=1.0, col=GOLD)
    y -= 18
    # totals panel on the right
    panel_x = PW - MARGIN_R - 260
    c.setFillColor(PANEL)
    c.roundRect(panel_x, y - 48, 260, 64, 4, fill=1, stroke=0)
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.9)
    c.roundRect(panel_x, y - 48, 260, 64, 4, fill=0, stroke=1)

    c.setFont(sans, 9)
    c.setFillColor(MUTE)
    c.drawString(panel_x + 12, y - 6, "TOTAL")
    c.setFont(sans_b, 12)
    c.setFillColor(DK)
    c.drawRightString(PW - MARGIN_R - 12, y - 6, _money(total))

    c.setFont(sans, 8.5)
    c.setFillColor(MUTE)
    c.drawString(panel_x + 12, y - 24, f"Deposit to begin ({pct:.0f}%)")
    c.setFont(sans_b, 10)
    c.setFillColor(DK)
    c.drawRightString(PW - MARGIN_R - 12, y - 24, _money(deposit))

    c.setFont(sans, 8.5)
    c.setFillColor(MUTE)
    c.drawString(panel_x + 12, y - 40, "Balance on completion")
    c.setFont(sans, 9)
    c.drawRightString(PW - MARGIN_R - 12, y - 40, _money(balance))
    return y - 70


def _draw_notes(c: canvas.Canvas, quote: Dict[str, Any], y: float) -> float:
    _, sans, sans_b, _ = _ensure_body_fonts()
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
            lines.extend(_wrap(raw, 120))
    if terms:
        lines.extend(_wrap(terms, 120))
    if not lines:
        lines = [
            "50% deposit required before work begins. Balance due upon completion.",
            "Estimate covers fabrication and materials as listed.",
        ]

    _hr(c, y)
    y -= 14
    c.setFont(sans_b, 7.5)
    c.setFillColor(GOLD)
    c.drawString(MARGIN_L, y, "NOTES")
    y -= 12
    c.setFont(sans, 8)
    c.setFillColor(DETAIL)
    for ln in lines[:10]:
        if y < CONTENT_BOTTOM + 8:
            break
        c.drawString(MARGIN_L, y, ln[:130])
        y -= 10
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
    """Render McLean gold landscape estimate PDF bytes from a quote dict."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(PW, PH))
    qn = quote.get("quote_number") or quote.get("id") or "estimate"
    c.setTitle(f"Estimate {qn} — Nelma's Workroom")
    c.setAuthor("Nelma's Workroom - Powered by Empire Workroom")
    c.setCreator("Nelma's Workroom")
    c.setSubject("Client estimate — McLean gold landscape chrome")

    serif_b, sans, sans_b, mono = _ensure_body_fonts()
    items = list(quote.get("line_items") or quote.get("items") or [])
    draw_items = [it for it in items if (it.get("unit") or "").lower() != "note"]
    note_items = [it for it in items if (it.get("unit") or "").lower() == "note"]
    if not draw_items:
        draw_items = items

    oq = _open_questions(quote)

    # Dry-run layout to decide page count before painting chrome stamps.
    y_probe = CONTENT_TOP - 22
    # client block roughly consumes ~66 pt
    y_probe -= 66
    y_probe -= 20  # column headers
    spilled: List[Dict[str, Any]] = []
    kept: List[Dict[str, Any]] = []
    for it in draw_items:
        title, details = _title_detail(it)
        need = 22 + 11 * min(len(details), 5)
        if y_probe - need < CONTENT_BOTTOM + 90:
            spilled.append(it)
        else:
            kept.append(it)
            y_probe -= need
    need_p2 = bool(spilled or oq or note_items)
    pages = 2 if need_p2 else 1

    _paint_page_chrome(c, quote, 1, pages)
    y = CONTENT_TOP - 22
    y = _draw_client_block(c, quote, y)

    c.setFont(sans_b, 7.5)
    c.setFillColor(GOLD)
    c.drawString(MARGIN_L, y, "#")
    c.drawString(MARGIN_L + 22, y, "DESCRIPTION")
    c.drawRightString(PW - MARGIN_R, y, "AMOUNT")
    y -= 6
    _hr(c, y)
    y -= 14

    for it in kept:
        title, details = _title_detail(it)
        c.setFont(sans_b, 9.5)
        c.setFillColor(DK)
        c.drawString(MARGIN_L, y, str(it.get("line_number") or ""))
        c.drawString(MARGIN_L + 22, y, title[:100])
        c.drawRightString(PW - MARGIN_R, y, _amount_label(it, title))
        y -= 12
        c.setFont(sans, 8)
        c.setFillColor(DETAIL)
        for ln in details[:5]:
            c.drawString(MARGIN_L + 22, y, ln[:120])
            y -= 10.5
        y -= 8

    y = _draw_totals(c, quote, y)
    y = _draw_notes(c, quote, y)

    if need_p2:
        c.showPage()
        _paint_page_chrome(c, quote, 2, 2)
        y = CONTENT_TOP - 22
        c.setFont(sans_b, 11)
        c.setFillColor(DK)
        c.drawString(MARGIN_L, y, f"{qn} — Details & Open Questions")
        y -= 14
        _hr(c, y, col=GOLD)
        y -= 16

        for it in spilled:
            title, details = _title_detail(it)
            c.setFont(sans_b, 9.5)
            c.setFillColor(DK)
            c.drawString(MARGIN_L, y, str(it.get("line_number") or ""))
            c.drawString(MARGIN_L + 22, y, title[:100])
            c.drawRightString(PW - MARGIN_R, y, _amount_label(it, title))
            y -= 12
            c.setFont(sans, 8)
            c.setFillColor(DETAIL)
            for ln in details[:7]:
                c.drawString(MARGIN_L + 22, y, ln[:120])
                y -= 10
            y -= 8
            if y < CONTENT_BOTTOM + 40:
                break

        if oq or note_items:
            c.setFont(sans_b, 8.5)
            c.setFillColor(GOLD)
            c.drawString(MARGIN_L, max(y, CONTENT_BOTTOM + 40), "OPEN QUESTIONS — DO NOT INVENT ANSWERS")
            y = max(y, CONTENT_BOTTOM + 40) - 14
            c.setFont(sans, 8)
            c.setFillColor(DETAIL)
            seen = set()
            for raw in list(oq) + [it.get("description") or "" for it in note_items]:
                for ln in _wrap(raw, 120):
                    key = ln[:80]
                    if key in seen:
                        continue
                    seen.add(key)
                    if y < CONTENT_BOTTOM + 8:
                        break
                    c.drawString(MARGIN_L, y, ln[:130])
                    y -= 11

        status = (quote.get("status") or "draft").upper()
        if status in ("DRAFT", "PROPOSAL"):
            c.setFont(sans_b, 8)
            c.setFillColor(MUTE)
            c.drawCentredString(
                PW / 2,
                CONTENT_BOTTOM + 4,
                "DRAFT — Not for client issue until open questions resolved",
            )

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
