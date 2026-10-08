"""Client estimate PDF — McLean landscape chrome (founder gold standard).

Drawing/field-measurement golden remains reference/max-golden/ (11-sheet
field set). Client **estimates** share that same landscape letter geometry
+ header/footer chrome (cream paper, dark bands, Nelma/Empire language)
via max_sheet_chrome.render_chrome_bands.

Body content stays estimate-shaped (line items, totals, notes) — this is
NOT a field-measurement sheet. Body chrome borrows field-sheet vocabulary
(cream panels, gold corner ticks, mono section labels, three-zone NOTES
band) without inventing measurement geometry. Prior Willard EST-2026-110
portrait layout is retired for Max client estimates.

Canonical chrome: backend/app/services/drawing/max_sheet_chrome.py
Golden doc: reference/max-golden/GOLDEN.md
"""
from __future__ import annotations

import logging
import re
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

from app.config.workroom_billing import WorkroomBilling, get_workroom_billing
from app.services.pricing.dimensions import quote_item_dimension_text
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
# Warm zebra tint for estimate-table detail rows; subtotal rows stay unshaded.
ROW_SHADE = HexColor("#efe8dc")

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


def _scrub_client_facing_desc(desc: str) -> str:
    """Strip brand / SKU / yardage; keep F-IDs and workroom language only."""
    s = (desc or "").strip()
    if not s:
        return s
    # Yardage stays on the line (qty + yd). Do not strip it here.
    # Known brand / mill / SKU tokens → keep preceding F-id only
    brand_bits = [
        r"Fabricut\s+Hill\s+Stripe\s+Blue\s*\d*",
        r"Hill\s+Stripe\s+Blue\s*\d*",
        r"Schumacher\s+Bixi\s+Velvet\s+Celestine\s*\d*",
        r"Bixi\s+Velvet\s+Celestine\s*\d*",
        r"Bixi\s+Celestine",
        r"Abnormals\s+Supernaturally\s+Ebb\s+Tide",
        r"Ferrick\s+Mason\s+FM\d+\s+Slate\s+Blue\s+Mineral",
        r"Ferrick\s+Mason\s+FM\d+",
        r"FM\d+\s+Slate\s+Blue\s+Mineral",
        r"Kristy\s+Stafford\s+Lilly\s+Blue",
        r"Lilly\s+Blue",
        r"\b624660\b",
        r"\b73973\b",
        r"\bFM5958\b",
    ]
    for pat in brand_bits:
        s = re.sub(pat, "", s, flags=re.I)
    # Collapse separators left empty
    s = re.sub(r"\s*·\s*·\s*", " · ", s)
    s = re.sub(r"\s{2,}", " ", s)
    s = re.sub(r"\s*·\s*$", "", s)
    s = re.sub(r"^\s*·\s*", "", s)
    return s.strip()


def _title_detail(it: Dict[str, Any]) -> Tuple[str, List[str]]:
    desc = _scrub_client_facing_desc(it.get("description") or "Item")
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
    # HOTFIX 5 parity: founder override lives in final_price when
    # price_overridden is set — customer-facing PDF must match canonical total.
    is_override = bool(it.get("price_overridden"))
    final_price = it.get("final_price")
    if is_override and final_price is not None:
        amount = final_price
    else:
        amount = it.get("subtotal")
        if amount is None:
            amount = it.get("amount")
        if amount is None:
            amount = final_price
        if amount is None or float(amount or 0) == 0:
            qty = float(it.get("quantity") or 1)
            unit_price = it.get("unit_price")
            if unit_price is None:
                unit_price = it.get("rate")
            if unit_price is not None:
                try:
                    amount = round(qty * float(unit_price), 2)
                except (TypeError, ValueError):
                    pass
    try:
        amt_f = float(amount or 0)
    except (TypeError, ValueError):
        amt_f = 0.0
    unit = (it.get("unit") or "").lower()
    low = title.lower()
    if amt_f == 0 and ("tbd" in low or "open question" in low or unit == "note"):
        return "TBD"
    return _money(amt_f)




def _line_amount_value(it: Dict[str, Any]) -> float:
    """Numeric line amount used for band subtotals (honors founder override)."""
    is_override = bool(it.get("price_overridden"))
    final_price = it.get("final_price")
    if is_override and final_price is not None:
        try:
            return float(final_price)
        except (TypeError, ValueError):
            return 0.0
    amount = it.get("subtotal")
    if amount is None:
        amount = it.get("amount")
    if amount is None:
        amount = final_price
    try:
        amt_f = float(amount or 0)
    except (TypeError, ValueError):
        amt_f = 0.0
    if amt_f == 0:
        qty = float(it.get("quantity") or 1)
        unit_price = it.get("unit_price")
        if unit_price is None:
            unit_price = it.get("rate")
        if unit_price is not None:
            try:
                amt_f = round(qty * float(unit_price), 2)
            except (TypeError, ValueError):
                pass
    return amt_f


def _is_section_row(it: Dict[str, Any]) -> bool:
    unit = (it.get("unit") or "").lower()
    cat = (it.get("category") or "").lower()
    desc = (it.get("description") or "").strip().upper()
    if unit == "section" or cat in ("section_header", "section"):
        return True
    return desc.startswith("SECTION —") or desc.startswith("§ ")


def _is_subtotal_row(it: Dict[str, Any]) -> bool:
    unit = (it.get("unit") or "").lower()
    cat = (it.get("category") or "").lower()
    desc = (it.get("description") or "").strip().upper()
    if unit == "subtotal" or cat in ("subtotal", "subtotal_row"):
        return True
    return desc.startswith("SUBTOTAL —") or desc.startswith("SUBTOTAL ")


def _is_com_meta_line(it: Dict[str, Any]) -> bool:
    """COM yardage / goods meta — hide from client body (yardage upon request)."""
    cat = (it.get("category") or "").lower()
    unit = (it.get("unit") or "").lower()
    desc = (it.get("description") or "").upper()
    if cat == "com_fabric":
        return True
    if unit in ("yd", "yard", "yards") and desc.startswith("COM "):
        return True
    return False


def _is_extra_band(it: Dict[str, Any]) -> bool:
    """Extra / not-yet-priced band (show TBD — never invent dollars)."""
    if _is_section_row(it) or _is_subtotal_row(it) or _is_com_meta_line(it):
        return False
    cat = (it.get("category") or "").lower()
    unit = (it.get("unit") or "").lower()
    desc = (it.get("description") or "")
    low = desc.lower()
    if cat in ("open_tbd", "extra_tbd", "tbd"):
        # Package-included $0 detail lines stay in Quoted when they say so
        if ("part of package" in low) or ("part of" in low and "quoted" in low):
            if "tbd" not in low and "excluded" not in low:
                return False
        if "labor tbd" in low or "excluded" in low or "not received" in low or "tbd" in low:
            return True
        if _line_amount_value(it) == 0:
            return True
    if "labor tbd" in low or ("excluded" in low and "tbd" in low):
        return True
    if unit == "tbd":
        return True
    return False


def _partition_estimate_items(
    items: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Split into quoted band, extra band, and skipped COM/meta note rows."""
    quoted: List[Dict[str, Any]] = []
    extra: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    for it in items:
        unit = (it.get("unit") or "").lower()
        if unit == "note" and not _is_section_row(it) and not _is_subtotal_row(it):
            skipped.append(it)
            continue
        if _is_com_meta_line(it):
            skipped.append(it)
            continue
        if _is_section_row(it) or _is_subtotal_row(it):
            # Explicit structure rows: keep order by placing into bands later
            # via description keywords; default to quoted if ambiguous.
            desc = (it.get("description") or "").upper()
            if "EXTRA" in desc:
                extra.append(it)
            else:
                quoted.append(it)
            continue
        if _is_extra_band(it):
            extra.append(it)
        else:
            quoted.append(it)
    return quoted, extra, skipped


def _quoted_subtotal(items: List[Dict[str, Any]]) -> float:
    total = 0.0
    for it in items:
        if _is_section_row(it) or _is_subtotal_row(it) or _is_com_meta_line(it):
            continue
        if _is_extra_band(it):
            continue
        total += _line_amount_value(it)
    return round(total, 2)

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
    # Client copies hide internal version tags and allow the clean project
    # label to fit in the chrome header. Internal/draft copies retain legacy
    # truncation behavior.
    client_safe = _client_safe(quote)
    if client_safe:
        project = re.sub(r"\s+v\d+\s*$", "", project, flags=re.IGNORECASE)
    if len(client) > 36:
        client = client[:33] + "…"
    project_limit = 60 if client_safe else 40
    if len(project) > project_limit:
        project = project[:project_limit - 3] + "…"
    return client, project


def _client_safe(quote: Dict[str, Any]) -> bool:
    metadata = quote.get("metadata") or {}
    return isinstance(metadata, dict) and bool(metadata.get("client_safe_pdf"))


def _status_banner(quote: Dict[str, Any]) -> str:
    if _client_safe(quote):
        return "CLIENT COPY"
    status = (quote.get("status") or "draft").upper()
    if status in ("DRAFT", "PROPOSAL"):
        return "DRAFT — NOT FOR CLIENT ISSUE"
    # founder_review / sent / accepted → actual estimate chrome (no DRAFT)
    return "ESTIMATE"


def _estimate_bill() -> WorkroomBilling:
    """Client estimates bill as Empire Workroom. Never a person's name."""
    base = get_workroom_billing(None)
    return WorkroomBilling(
        billed_by="empire_workroom",
        name="Empire Workroom",
        address=base.address,
        phone=base.phone,
        email=base.email,
        website=base.website,
        tagline=base.tagline,
    )


def _paint_page_chrome(c: canvas.Canvas, quote: Dict[str, Any], page: int, pages: int) -> None:
    client, project = _client_project(quote)
    qn = quote.get("quote_number") or quote.get("id") or "ESTIMATE"
    created = _fmt_date(quote.get("created_at") or quote.get("updated_at"))
    bill = _estimate_bill()
    render_chrome_bands(
        c,
        sheet_no=page,
        total=pages,
        right_title="ESTIMATE",
        letterhead=bill.letterhead_upper,
        powered_by=bill.chrome_subheader_upper,
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


def _section_label(c: canvas.Canvas, x: float, y: float, text: str, mono: str) -> None:
    """Gold mono section label — same language as field-sheet LAYOUT MATH."""
    c.setFont(mono, 7)
    c.setFillColor(GOLD)
    c.drawString(x, y, text.upper())


def _panel(c: canvas.Canvas, x: float, y_bottom: float, w: float, h: float) -> None:
    """Cream panel with gold hairline — field-sheet callout vocabulary."""
    c.setFillColor(PANEL)
    c.rect(x, y_bottom, w, h, fill=1, stroke=0)
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.7)
    c.rect(x, y_bottom, w, h, fill=0, stroke=1)
    # corner ticks (field-sheet viewport cue)
    tick = 6.0
    c.setLineWidth(1.0)
    for tx, ty, dx, dy in (
        (x, y_bottom + h, tick, -tick),
        (x + w, y_bottom + h, -tick, -tick),
        (x, y_bottom, tick, tick),
        (x + w, y_bottom, -tick, tick),
    ):
        c.line(tx, ty, tx + dx, ty)
        c.line(tx, ty, tx, ty + dy)


def _draw_client_block(c: canvas.Canvas, quote: Dict[str, Any], y: float) -> float:
    _, sans, sans_b, mono = _ensure_body_fonts()
    panel_h = 58.0
    _panel(c, MARGIN_L, y - panel_h, CONTENT_W, panel_h)

    _section_label(c, MARGIN_L + 8, y - 12, "PREPARED FOR", mono)
    _section_label(c, MARGIN_L + CONTENT_W * 0.52, y - 12, "PROJECT SITE", mono)

    c.setFont(sans, 10)
    c.setFillColor(DK)
    client = quote.get("customer_name") or "Client"
    # "PROJECT SITE": the job address when the quote has one (designer jobs bill the designer
    # but install at the client's home); otherwise the customer address as before.
    site = quote.get("project_address") or quote.get("customer_address") or ""
    c.drawString(MARGIN_L + 8, y - 26, str(client)[:56])
    c.drawString(MARGIN_L + CONTENT_W * 0.52, y - 26, str(site)[:56])

    c.setFont(sans, 8.5)
    c.setFillColor(MUTE)
    phone = quote.get("customer_phone") or ""
    attn = ""
    for line in str(quote.get("notes") or "").splitlines():
        if line.lower().startswith("attn"):
            attn = line.strip()
            break
    left2 = attn or (f"Tel: {phone}" if phone else "")
    project = _client_project(quote)[1] if _client_safe(quote) else (quote.get("project_name") or "")
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
        c.drawString(MARGIN_L + 8, y - 40, left2[:56])
    if material:
        c.drawString(MARGIN_L + 8, y - 52, material[:56])
    if project:
        c.drawString(MARGIN_L + CONTENT_W * 0.52, y - 40, str(project)[:56])

    return y - panel_h - 14


def _draw_totals(
    c: canvas.Canvas,
    quote: Dict[str, Any],
    y: float,
    *,
    quoted_subtotal: float | None = None,
    has_extra_tbd: bool = False,
) -> float:
    """Totals panel: Quoted subtotal → Extra TBD → Grand total (priced only)."""
    _, sans, sans_b, _ = _ensure_body_fonts()
    items = list(quote.get("line_items") or quote.get("items") or [])
    if quoted_subtotal is None:
        quoted_subtotal = _quoted_subtotal(items)
    # Priced / due-now total = locked quoted dollars only (never invent TBD $)
    total = float(quoted_subtotal)
    # Prefer quote.total when it matches quoted (legacy single-band quotes)
    q_total = quote.get("total")
    try:
        q_total_f = float(q_total) if q_total is not None else None
    except (TypeError, ValueError):
        q_total_f = None
    if q_total_f is not None and abs(q_total_f - total) < 0.02:
        total = q_total_f

    deposit = quote.get("deposit_required")
    # Respect explicit 0 — `or 50` would treat 0 as missing (falsy).
    _raw_pct = quote.get("deposit_percent")
    pct = 50.0 if _raw_pct is None else float(_raw_pct)
    # Deposit is pct% of PRICED only (quoted), never of invented TBD
    expected_deposit = round(total * pct / 100.0, 2)
    try:
        deposit_f = float(deposit) if deposit is not None else expected_deposit
    except (TypeError, ValueError):
        deposit_f = expected_deposit
    # If stale deposit equals old full-total math, snap to priced deposit
    if abs(deposit_f - expected_deposit) > 0.02:
        deposit_f = expected_deposit
    if pct == 0:
        deposit_f = 0.0
    balance = round(total - deposit_f, 2)
    show_deposit = pct > 0
    client_safe = _client_safe(quote)
    no_extra_client_copy = client_safe and not has_extra_tbd

    _hr(c, y, weight=1.0, col=GOLD)
    y -= 18
    panel_x = PW - MARGIN_R - 280
    panel_h = 88 if has_extra_tbd else 72
    if not show_deposit:
        panel_h = 56 if has_extra_tbd else 44
    c.setFillColor(PANEL)
    c.roundRect(panel_x, y - (panel_h - 16), 280, panel_h, 4, fill=1, stroke=0)
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.9)
    c.roundRect(panel_x, y - (panel_h - 16), 280, panel_h, 4, fill=0, stroke=1)

    row = y - 4
    c.setFont(sans, 8.5)
    c.setFillColor(MUTE)
    quoted_label = "Addendum items" if no_extra_client_copy else "SUBTOTAL — Quoted / already given"
    c.drawString(panel_x + 12, row, quoted_label)
    c.setFont(sans_b, 10)
    c.setFillColor(DK)
    c.drawRightString(PW - MARGIN_R - 12, row, _money(quoted_subtotal))

    if has_extra_tbd:
        row -= 14
        c.setFont(sans, 8.5)
        c.setFillColor(MUTE)
        c.drawString(panel_x + 12, row, "SUBTOTAL — Extra work (not priced)")
        c.setFont(sans_b, 10)
        c.setFillColor(DK)
        c.drawRightString(PW - MARGIN_R - 12, row, "TBD")

    row -= 14
    c.setFont(sans, 8.5)
    c.setFillColor(MUTE)
    total_label = "Addendum subtotal" if no_extra_client_copy else "GRAND TOTAL (priced / quoted only)"
    c.drawString(panel_x + 12, row, total_label)
    c.setFont(sans_b, 12)
    c.setFillColor(DK)
    c.drawRightString(PW - MARGIN_R - 12, row, _money(total))

    if show_deposit:
        row -= 14
        c.setFont(sans, 8)
        c.setFillColor(MUTE)
        deposit_label = (f"Deposit to begin ({pct:.0f}%)" if client_safe
                         else f"Deposit to begin ({pct:.0f}% of priced)")
        c.drawString(panel_x + 12, row, deposit_label)
        c.setFont(sans_b, 9)
        c.setFillColor(DK)
        c.drawRightString(PW - MARGIN_R - 12, row, _money(deposit_f))

        row -= 12
        c.setFont(sans, 8)
        c.setFillColor(MUTE)
        c.drawString(panel_x + 12, row, "Balance on completion" if client_safe else "Balance on completion (priced)")
        c.setFont(sans, 8.5)
        c.drawRightString(PW - MARGIN_R - 12, row, _money(balance))

    if has_extra_tbd:
        c.setFont(sans, 7)
        c.setFillColor(MUTE)
        c.drawString(
            MARGIN_L,
            y - (panel_h - 10),
            "Extra work is TBD — not included in total due now / deposit. Do not invent prices.",
        )
    return y - panel_h - 10


def _draw_notes(c: canvas.Canvas, quote: Dict[str, Any], y: float) -> float:
    if _client_safe(quote):
        return y - 8
    _, sans, sans_b, mono = _ensure_body_fonts()
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
            lines.extend(_wrap(raw, 110))
    if terms:
        lines.extend(_wrap(terms, 110))
    # Client-facing: no invented body notes / deposit wording when empty.
    if not lines:
        return y

    # Three-zone field-sheet band: NOTES | TERMS | STATUS (estimate analogue)
    band_h = 18.0 + 10.0 * min(len(lines), 6)
    band_h = min(band_h, max(y - CONTENT_BOTTOM - 4, 36))
    if y - band_h < CONTENT_BOTTOM:
        band_h = max(y - CONTENT_BOTTOM, 28)
    _panel(c, MARGIN_L, y - band_h, CONTENT_W, band_h)

    zone_w = CONTENT_W / 3.0
    c.setStrokeColor(HAIR)
    c.setLineWidth(0.5)
    c.line(MARGIN_L + zone_w, y - 2, MARGIN_L + zone_w, y - band_h + 2)
    c.line(MARGIN_L + 2 * zone_w, y - 2, MARGIN_L + 2 * zone_w, y - band_h + 2)

    _section_label(c, MARGIN_L + 6, y - 12, "NOTES", mono)
    _section_label(c, MARGIN_L + zone_w + 6, y - 12, "TERMS / SCOPE", mono)
    _section_label(c, MARGIN_L + 2 * zone_w + 6, y - 12, "FIELD CHECK", mono)

    c.setFont(sans, 7.5)
    c.setFillColor(DETAIL)
    note_lines = lines[:4]
    term_lines = lines[4:8] if len(lines) > 4 else [
        "Deposit before fabrication.",
        "Balance on completion.",
    ]
    status = (quote.get("status") or "draft").upper()
    check_lines = [
        f"Status: {status}",
        "Do not invent missing dims.",
        "Confirm fabric before cut.",
    ]
    yy = y - 24
    for ln in note_lines:
        c.drawString(MARGIN_L + 6, yy, ln[:42])
        yy -= 9
    yy = y - 24
    for ln in term_lines:
        c.drawString(MARGIN_L + zone_w + 6, yy, ln[:42])
        yy -= 9
    yy = y - 24
    c.setFillColor(MUTE)
    for ln in check_lines:
        c.drawString(MARGIN_L + 2 * zone_w + 6, yy, ln[:42])
        yy -= 9
    return y - band_h - 8


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



def _draw_band_header(c: canvas.Canvas, y: float, label: str, mono: str, sans_b: str) -> float:
    """Gold section header for Quoted / Extra bands."""
    _section_label(c, MARGIN_L, y, label, mono)
    y -= 4
    _hr(c, y, weight=0.7, col=GOLD)
    return y - 12


def _draw_band_subtotal(
    c: canvas.Canvas,
    y: float,
    label: str,
    amount_text: str,
    sans_b: str,
    sans: str,
) -> float:
    """Inline SUBTOTAL row under a band."""
    c.setFillColor(PANEL)
    c.rect(MARGIN_L, y - 4, CONTENT_W, 16, fill=1, stroke=0)
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.6)
    c.line(MARGIN_L, y - 4, PW - MARGIN_R, y - 4)
    c.setFont(sans_b, 9)
    c.setFillColor(DK)
    c.drawString(MARGIN_L + 4, y + 2, label)
    c.drawRightString(PW - MARGIN_R - 4, y + 2, amount_text)
    return y - 18


def _draw_one_line_item(
    c: canvas.Canvas,
    it: Dict[str, Any],
    y: float,
    *,
    sans: str,
    sans_b: str,
    display_num: int | None = None,
    detail_limit: int = 5,
) -> float:
    """Draw one estimate line; section/subtotal rows get special treatment."""
    title, details = _title_detail(it)
    if _is_section_row(it):
        # Already painted via band headers when auto-banding; skip duplicates
        return y
    if _is_subtotal_row(it):
        amt = _amount_label(it, title)
        return _draw_band_subtotal(c, y, title[:80], amt, sans_b, sans)

    num = display_num if display_num is not None else it.get("line_number") or ""
    c.setFont(sans_b, 9.5)
    c.setFillColor(DK)
    c.drawString(MARGIN_L, y, str(num))
    c.drawString(MARGIN_L + 22, y, title[:100])
    # Included $0 package detail → "incl." instead of $0.00
    low = title.lower()
    amt_f = _line_amount_value(it)
    if amt_f == 0 and ("part of package" in low or "part of" in low and "quoted" in low) and "tbd" not in low:
        amt_txt = "incl."
    else:
        amt_txt = _amount_label(it, title)
    c.drawRightString(PW - MARGIN_R, y, amt_txt)
    y -= 12
    c.setFont(sans, 8)
    c.setFillColor(DETAIL)
    for ln in details[:detail_limit]:
        c.drawString(MARGIN_L + 22, y, ln[:120])
        y -= 10.5
    return y - 8


def _draw_grouped_client_copy(quote: Dict[str, Any], grouping: Dict[str, Any]) -> bytes:
    """Render a client-safe addendum grouped by area.

    This is metadata-driven so future addendum quotes can supply original
    items and add-ons per opening without changing the renderer. Each area
    is shown as Original items → Add-ons → three subtotals; the final page
    carries the original/add-on/grand totals and optional hardware.
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(PW, PH))
    qn = quote.get("quote_number") or quote.get("id") or "estimate"
    _bill = _estimate_bill()
    c.setTitle(f"Estimate {qn} — {_bill.name}")
    c.setAuthor(_bill.pdf_author)
    c.setCreator(_bill.name)
    c.setSubject("Client addendum estimate grouped by area")
    serif_b, sans, sans_b, mono = _ensure_body_fonts()
    areas = list(grouping.get("areas") or [])
    # Give each area its own table block/page. This prevents orphaned area
    # headers and guarantees the ruled rows stay above the footer.
    area_pages = max(1, len(areas))
    total_pages = area_pages + 1
    page = 1
    _paint_page_chrome(c, quote, page, total_pages)
    y = CONTENT_TOP - 22
    y = _draw_client_block(c, quote, y)
    _section_label(c, MARGIN_L, y, "AREA BREAKDOWN", mono)
    y -= 16

    # Estimate-table columns: # | Description | Qty | Unit | Unit Price | Amount.
    desc_x = MARGIN_L + 22
    qty_x = PW - MARGIN_R - 272
    unit_x = PW - MARGIN_R - 222
    rate_x = PW - MARGIN_R - 142
    amount_x = PW - MARGIN_R
    row_number = [1]

    def table_header(y0: float) -> float:
        c.setFont(sans_b, 7.5)
        c.setFillColor(GOLD)
        c.drawString(MARGIN_L, y0, "#")
        c.drawString(desc_x, y0, "Description")
        c.drawRightString(qty_x, y0, "Qty")
        c.drawString(unit_x, y0, "Unit")
        c.drawRightString(rate_x, y0, "Unit Price")
        c.drawRightString(amount_x, y0, "Amount")
        c.setStrokeColor(HAIR)
        c.setLineWidth(0.6)
        c.line(MARGIN_L, y0 - 5, amount_x, y0 - 5)
        return y0 - 16

    def table_row(item: Dict[str, Any], y0: float) -> float:
        desc = str(item.get("description") or "Item")
        if desc.startswith("Valance add-on"):
            desc = "Valance add-on"
        elif desc.startswith("Tassel tiebacks"):
            desc = "Tassel tiebacks (pairs)"
        elif desc.startswith("Leading-edge trim application"):
            desc = "Leading-edge trim application"
        elif desc.startswith("Center tassels"):
            desc = "Center tassels (2 per swag)"
        elif desc.startswith("Sheer panels"):
            desc = "Sheer panels"
        qty = float(item.get("quantity") or 1)
        unit = str(item.get("unit") or "ea")
        amount = float(item.get("amount") or 0)
        rate = float(item.get("unit_price") or (amount / qty if qty else 0))
        qty_text = str(int(qty)) if qty.is_integer() else f"{qty:g}"
        c.setStrokeColor(HAIR)
        c.setLineWidth(0.35)
        # Shade every other detail row across the full table width. Subtotal
        # rows use their own rule treatment and are never shaded.
        if row_number[0] % 2 == 0:
            c.setFillColor(ROW_SHADE)
            c.rect(MARGIN_L, y0 - 10, amount_x - MARGIN_L, 14, fill=1, stroke=0)
        c.line(MARGIN_L, y0 + 4, amount_x, y0 + 4)
        c.setFont(sans, 8)
        c.setFillColor(DETAIL)
        c.drawString(MARGIN_L, y0 - 5, str(row_number[0]))
        c.drawString(desc_x, y0 - 5, desc[:72])
        c.drawRightString(qty_x, y0 - 5, qty_text)
        c.drawString(unit_x, y0 - 5, unit)
        c.drawRightString(rate_x, y0 - 5, _money(rate))
        c.drawRightString(amount_x, y0 - 5, _money(amount))
        c.line(MARGIN_L, y0 - 10, amount_x, y0 - 10)
        row_number[0] += 1
        return y0 - 14

    def subtotal_row(label: str, amount: float, y0: float) -> float:
        c.setFont(sans_b, 8)
        c.setFillColor(DK)
        c.drawString(desc_x, y0 - 5, label)
        c.drawRightString(amount_x, y0 - 5, _money(amount))
        c.setStrokeColor(GOLD)
        c.setLineWidth(0.55)
        c.line(MARGIN_L, y0 + 4, amount_x, y0 + 4)
        c.line(MARGIN_L, y0 - 10, amount_x, y0 - 10)
        return y0 - 24

    def draw_area(area: Dict[str, Any], y0: float) -> float:
        name = str(area.get("name") or "Area")
        c.setFillColor(PANEL)
        c.rect(MARGIN_L, y0 - 12, CONTENT_W, 18, fill=1, stroke=0)
        c.setFont(sans_b, 10)
        c.setFillColor(DK)
        c.drawString(MARGIN_L + 6, y0 - 5, name[:100])
        y0 -= 22
        y0 = table_header(y0)
        for label, key in (("Original items", "original_items"), ("Add-ons", "addons")):
            c.setFont(sans_b, 8.5)
            c.setFillColor(GOLD)
            c.drawString(desc_x, y0, label)
            y0 -= 12
            for item in list(area.get(key) or []):
                y0 = table_row(item, y0)
            subtotal_key = "original_subtotal" if key == "original_items" else "addons_subtotal"
            subtotal_label = "Original subtotal" if key == "original_items" else "Add-ons subtotal"
            y0 = subtotal_row(subtotal_label, float(area.get(subtotal_key) or 0), y0)
        y0 = subtotal_row("Area total", float(area.get("total") or 0), y0)
        return y0 - 10

    for idx, area in enumerate(areas):
        # One complete area per page keeps headers with their first rows and
        # guarantees no table row can enter the footer band. Every new page
        # repeats the column header through draw_area/table_header.
        if idx:
            c.showPage()
            page += 1
            _paint_page_chrome(c, quote, page, total_pages)
            y = CONTENT_TOP - 22
            _section_label(c, MARGIN_L, y, "AREA BREAKDOWN", mono)
            y -= 16
        y = draw_area(area, y)

    c.showPage()
    page += 1
    _paint_page_chrome(c, quote, page, total_pages)
    y = CONTENT_TOP - 22
    _section_label(c, MARGIN_L, y, "ADDENDUM TOTALS", mono)
    y -= 20
    original_total = float(grouping.get("original_total") or 0)
    addons_total = float(grouping.get("addons_total") or 0)
    grand_total = float(grouping.get("grand_total") or (original_total + addons_total))
    rows = [
        ("Original total", original_total),
        ("Add-ons total", addons_total),
        ("Grand total", grand_total),
    ]
    for label, amount in rows:
        c.setFont(sans_b if label == "Grand total" else sans, 10)
        c.setFillColor(DK)
        c.drawString(MARGIN_L + 8, y, label)
        c.drawRightString(PW - MARGIN_R, y, _money(amount))
        y -= 18
    optional = (quote.get("metadata") or {}).get("optional_hardware") or {}
    optional_total = float(optional.get("total", 0) or 0)
    if optional_total > 0:
        y -= 8
        _hr(c, y, col=GOLD)
        y -= 20
        _section_label(c, MARGIN_L, y, "OPTIONAL PASSWAY HARDWARE", mono)
        y -= 18
        y = table_header(y)
        optional_rows = [
            {"description": '2" rings, 8-pack', "quantity": 3, "unit": "pack", "unit_price": 74.95, "amount": optional.get("rings", 224.85)},
            {"description": '2" reeded pole, 8 ft', "quantity": 1, "unit": "ea", "unit_price": 210.82, "amount": optional.get("pole", 210.82)},
            {"description": '2" single brackets, 3½" return', "quantity": 3, "unit": "ea", "unit_price": 32.08, "amount": optional.get("brackets", 96.24)},
        ]
        for item in optional_rows:
            y = table_row(item, y)
        y = subtotal_row("Optional passway hardware", optional_total, y)
        y -= 6
        c.setFont(sans_b, 10)
        c.setFillColor(DK)
        c.drawString(desc_x, y, "Total with optional hardware")
        c.drawRightString(amount_x, y, _money(grand_total + optional_total))
    c.save()
    return buf.getvalue()


_QTY_UNIT_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(widths?|yards?|yds?|each|ea|pieces?|pcs?)\b",
    re.I,
)
_DESC_FONT = 8.0
_DESC_LEADING = 13.0
_ROW_GAP = 6.0


def _canon_unit(unit: str, qty: float | None) -> str:
    u = (unit or "").strip().lower().rstrip(".")
    if u in {"width", "widths"}:
        return "width" if qty == 1 else "widths"
    if u in {"yd", "yds", "yard", "yards"}:
        return "yd"
    if u in {"ea", "each"}:
        return "ea"
    if u in {"pc", "pcs", "piece", "pieces"}:
        return "pc" if qty == 1 else "pcs"
    return (unit or "").strip()


def _parsed_unit(description: str, qty: float | None) -> str:
    """Unit written on the line, such as '8 widths' or '32 yd'."""
    text = description or ""
    chosen = ""
    for match in _QTY_UNIT_RE.finditer(text):
        word = match.group(2)
        if qty is None:
            chosen = word
            continue
        try:
            if abs(float(match.group(1)) - float(qty)) < 0.02:
                return _canon_unit(word, qty)
        except ValueError:
            continue
    if chosen:
        return _canon_unit(chosen, qty)
    low = text.lower()
    if "per width" in low:
        return "width" if qty == 1 else "widths"
    if "per yard" in low or "per yd" in low:
        return "yd"
    return ""


def _qty_number(it: Dict[str, Any]) -> tuple[float | None, str]:
    raw_qty = it.get("quantity")
    if raw_qty in (None, "") and it.get("yards_needed") not in (None, "", 0, 0.0):
        raw_qty = it.get("yards_needed")
    if raw_qty in (None, ""):
        return None, ""
    try:
        qty = float(raw_qty)
    except (TypeError, ValueError):
        return None, str(raw_qty)
    text = str(int(qty)) if qty.is_integer() else f"{qty:g}"
    return qty, text


def _qty_with_unit(it: Dict[str, Any]) -> str:
    """Qty plus the line's unit. Generic 'ea' yields to widths/yd in the description."""
    qty, text = _qty_number(it)
    field = str(it.get("unit") or it.get("uom") or "").strip()
    field_unit = _canon_unit(field, qty) if field else ""
    parsed = _parsed_unit(str(it.get("description") or ""), qty)
    if parsed and parsed != "ea" and field_unit in {"", "ea"}:
        shown = parsed
    elif field_unit:
        shown = field_unit
    else:
        shown = parsed
    if not text:
        return shown
    return f"{text} {shown}".strip()


def _rate_text(it: Dict[str, Any]) -> str:
    """$0 lines are marked RATE NEEDED. That marker is not a section."""
    rate = _line_rate(it)
    amount = _line_amount_value(it)
    if (rate is None or abs(rate) < 0.005) and abs(amount) < 0.005:
        return "RATE NEEDED"
    if rate is None:
        return ""
    return _money(rate)


def _line_rate(it: Dict[str, Any]) -> float | None:
    if it.get("rate") is not None:
        try:
            return float(it.get("rate"))
        except (TypeError, ValueError):
            return None
    if it.get("unit_price") is not None:
        try:
            return float(it.get("unit_price"))
        except (TypeError, ValueError):
            return None
    unit = (it.get("unit") or "").lower()
    if unit in {"yd", "yard", "yards", "yds"} and it.get("fabric_price_per_yard") is not None:
        try:
            return float(it.get("fabric_price_per_yard"))
        except (TypeError, ValueError):
            return None
    return None


def _explicit_extra_line(it: Dict[str, Any]) -> bool:
    """Only lines the quote itself marks as unpriced extra work."""
    unit = (it.get("unit") or "").lower()
    low = (it.get("description") or "").lower()
    if unit == "tbd":
        return True
    if "labor tbd" in low and _line_amount_value(it) == 0:
        return True
    return False


def _is_rate_marker(text: str) -> bool:
    """'Rate needed' is a missing-price flag, not a section or room."""
    low = re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()
    return low in {
        "rate needed",
        "rates needed",
        "estimate",
        "estimate rate needed",
        "tbd",
        "open tbd",
        "extra tbd",
    }


def _header_section_name(it: Dict[str, Any]) -> str:
    desc = (it.get("description") or "").strip()
    for prefix in ("SECTION —", "SECTION -", "§"):
        if desc.upper().startswith(prefix):
            name = desc[len(prefix):].strip()
            return name or "Section"
    return desc or "Section"


def _phase_heading(description: str) -> str:
    """'Phase 1 — Downstairs Living Room: Remove…' → the phase/room."""
    desc = (description or "").strip()
    if ":" not in desc:
        return ""
    head = desc.split(":", 1)[0].strip()
    if not head or head == desc or _is_rate_marker(head) or len(head) > 90:
        return ""
    return head


def _line_section_name(it: Dict[str, Any], header: str | None) -> str:
    """Section for one line.

    A real section, room, or phase wins. Fabric and materials use their
    category. An open SECTION header applies only when this line does not
    name its own. 'Rate needed' is never a section.
    """
    for key in ("section", "section_name", "room"):
        raw = it.get(key)
        if isinstance(raw, str) and raw.strip() and not _is_rate_marker(raw):
            return raw.strip()
    phase = _phase_heading(str(it.get("description") or ""))
    if phase:
        return phase
    if header and not _is_rate_marker(header):
        return header
    if _explicit_extra_line(it):
        return "Extra work"
    cat = str(it.get("category") or "").strip()
    if cat and not _is_rate_marker(cat) and cat.lower() not in {"com_fabric", "manual_line", "note"}:
        return cat.replace("_", " ").title()
    return "Quoted"


def group_estimate_sections(items: List[Dict[str, Any]]) -> List[Tuple[str, List[Dict[str, Any]]]]:
    """Group by each line's phase, room, or real section.

    'Rate needed' never becomes a section. A $0 line stays with its phase
    and is marked on that row. Subtotals are the sum of that section only.
    """
    sections: List[Tuple[str, List[Dict[str, Any]]]] = []
    current: str | None = None
    header: str | None = None
    bucket: List[Dict[str, Any]] = []

    def flush() -> None:
        nonlocal bucket
        if bucket:
            sections.append((current or "Quoted", bucket))
        bucket = []

    for it in items or []:
        if not isinstance(it, dict):
            continue
        unit = (it.get("unit") or "").lower()
        if unit == "note" and not _is_section_row(it):
            continue
        if _is_subtotal_row(it):
            continue
        if _is_section_row(it):
            flush()
            named = _header_section_name(it)
            header = None if _is_rate_marker(named) else named
            current = header
            continue
        name = _line_section_name(it, header)
        if bucket and name != (current or "Quoted"):
            flush()
        current = name
        bucket.append(it)
    flush()
    return sections


# ── 2026-10-08 (Rafael): upholstery estimate format ─────────────────────────────
# Grouped by area (U banquette, L banquette, material); columns
# Description | Qty | Unit | Sq ft | Price | Total; subtotal per area, then grand total,
# deposit, balance; measurements in the sub-text, in fractions (never decimals).
_SQFT_DESC_RE = re.compile(
    r"\s*[-–—·,]?\s*(\d+(?:\.\d+)?)\s*(?:sq\.?\s*ft|sf|sqft|ft²)\s*(?:[x×@]|at)\s*\$?\s*(\d+(?:\.\d+)?)"
    r"(?:\s*/\s*(?:sq\.?\s*ft|sf))?",
    re.I)
_SQFT_UNITS = {"sqft", "sq ft", "sq. ft", "sq.ft", "sf", "ft2", "ft²", "square feet", "sq_ft"}
_DEC_INCH_RE = re.compile(r"(?<![\d.])(\d+\.\d+)\s*(\"|''|”|in\b\.?|inch(?:es)?\b)")


def _num(v: Any) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None


def _line_sqft(it: Dict[str, Any]) -> Tuple[float | None, float | None]:
    """(sq ft per item, price per sq ft) for a line priced by area, else (None, None)."""
    snap = it.get("pricing_snapshot")
    if isinstance(snap, str):
        try:
            import json as _json
            snap = _json.loads(snap)
        except Exception:
            snap = None
    for src in (it, it.get("inputs") if isinstance(it.get("inputs"), dict) else None,
                snap if isinstance(snap, dict) else None):
        if not src:
            continue
        sq = next((_num(src.get(k)) for k in ("sq_ft", "sqft", "square_feet") if _num(src.get(k)) is not None), None)
        pps = next((_num(src.get(k)) for k in ("price_per_sqft", "rate_per_sqft", "price_per_sq_ft")
                    if _num(src.get(k)) is not None), None)
        if sq is not None:
            return sq, pps
    unit = str(it.get("unit") or "").strip().lower()
    if unit in _SQFT_UNITS:
        return _num(it.get("quantity")), _line_rate(it)
    m = _SQFT_DESC_RE.search(str(it.get("description") or ""))
    if m:
        return float(m.group(1)), float(m.group(2))
    return None, None


def inches_to_fractions(text: str) -> str:
    """'26.75"' -> '26 3/4"' (nearest 1/16). Measurements are never shown as decimals."""
    from app.services.pricing.dimensions import format_inches

    def _sub(m: "re.Match[str]") -> str:
        out = format_inches(float(m.group(1)))
        return out if m.group(2).startswith(('"', "''", "”")) else out.rstrip('"') + " " + m.group(2).strip()
    return _DEC_INCH_RE.sub(_sub, text or "")


def _sqft_layout(sections: List[Tuple[str, List[Dict[str, Any]]]]) -> bool:
    return any(_line_sqft(it)[0] is not None for _n, lines in sections for it in lines)


def _unit_text(it: Dict[str, Any]) -> str:
    qty, _t = _qty_number(it)
    unit = str(it.get("unit") or "").strip()
    if unit.lower() in _SQFT_UNITS:
        return "ea"
    return _canon_unit(unit, qty) if unit else "ea"


def _qty_text(it: Dict[str, Any]) -> str:
    unit = str(it.get("unit") or "").strip().lower()
    if unit in _SQFT_UNITS:
        return "1"
    _q, text = _qty_number(it)
    return text or "1"


def _description_max_width() -> float:
    """Description column stops short of the right-aligned qty."""
    qty_x = PW - MARGIN_R - 200
    return max(220.0, qty_x - 88 - MARGIN_L)


def _wrap_to_width(text: str, font: str, size: float, max_width: float) -> List[str]:
    words = (text or "").split()
    if not words:
        return []
    lines: List[str] = []
    current = ""
    for word in words:
        trial = word if not current else f"{current} {word}"
        if current and pdfmetrics.stringWidth(trial, font, size) > max_width:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines


def _description_lines(it: Dict[str, Any], max_width: float | None = None) -> List[str]:
    _serif, sans, _sans_b, _mono = _ensure_body_fonts()
    width = max_width or _description_max_width()
    raw_desc = str(it.get("description") or "Item")
    if _line_sqft(it)[0] is not None:
        raw_desc = _SQFT_DESC_RE.sub("", raw_desc)
    raw_desc = inches_to_fractions(raw_desc)
    lines: List[str] = []
    for part in [p for p in raw_desc.split("\n") if p.strip()] or ["Item"]:
        lines.extend(_wrap_to_width(" ".join(part.split()), sans, _DESC_FONT, width))
    lines = lines or ["Item"]
    dim = quote_item_dimension_text(it)
    if dim and all(dim not in line for line in lines):
        lines.append(dim)
    fabric = it.get("fabric_name")
    if fabric:
        lines.append(f"Fabric: {fabric}")
    return lines


_SQFT_DESC_W = None  # set per render (narrower description column in the sq-ft layout)


def _line_block_height(it: Dict[str, Any]) -> float:
    """Row height grows with every wrapped description line."""
    return _DESC_LEADING * len(_description_lines(it, _SQFT_DESC_W)) + _ROW_GAP


def _estimate_note_lines(quote: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    notes = (quote.get("notes") or "").strip()
    terms = (quote.get("terms") or quote.get("payment_terms") or "").strip()
    if notes and not _client_safe(quote):
        for raw in notes.splitlines():
            raw = raw.strip()
            if not raw:
                continue
            if raw.startswith("═") or raw.startswith("="):
                break
            if raw.upper().startswith("OPEN QUESTIONS"):
                break
            lines.extend(_wrap(raw, 100))
    if terms and not _client_safe(quote):
        lines.extend(_wrap(terms, 100))
    return lines


def render_mclean_estimate_bytes(quote: Dict[str, Any]) -> bytes:
    """Render a McLean landscape estimate.

    Each section keeps its own lines. Every line shows description, qty
    with unit, rate, and amount. Notes start on a new page when they
    would otherwise run into the footer. The bill-to name is Empire Workroom.
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(PW, PH))
    qn = quote.get("quote_number") or quote.get("id") or "estimate"
    bill = _estimate_bill()
    c.setTitle(f"Estimate {qn} — {bill.name}")
    c.setAuthor(bill.pdf_author)
    c.setCreator(bill.name)
    c.setSubject("Client estimate — Empire Workroom")

    _serif_b, sans, sans_b, mono = _ensure_body_fonts()
    items = list(quote.get("line_items") or quote.get("items") or [])
    client_safe = _client_safe(quote)
    area_grouping = (quote.get("metadata") or {}).get("area_grouping")
    if client_safe and isinstance(area_grouping, dict) and area_grouping.get("areas"):
        return _draw_grouped_client_copy(quote, area_grouping)

    sections = group_estimate_sections(items)
    global _SQFT_DESC_W
    sqft_mode = _sqft_layout(sections)
    # Description | Qty | Unit | Sq ft | Price | Total
    total_x = PW - MARGIN_R
    price_x = total_x - 92
    sqft_x = price_x - 72
    unit_x = sqft_x - 58
    qty6_x = unit_x - 48
    _SQFT_DESC_W = (qty6_x - 40 - MARGIN_L) if sqft_mode else None
    notes = _estimate_note_lines(quote)
    section_h = 18.0
    columns_h = 16.0
    subtotal_h = 20.0
    totals_h = 130.0
    note_header = 16.0
    note_line = 11.0
    floor = CONTENT_BOTTOM + 8

    pages: List[List[tuple]] = [[("client",)]]
    y = CONTENT_TOP - 22 - 72

    def new_page() -> float:
        pages.append([])
        return CONTENT_TOP - 28

    def room(need: float) -> bool:
        nonlocal y
        if y - need < floor:
            y = new_page()
            return True
        return False

    for name, lines in sections:
        first_h = _line_block_height(lines[0]) if lines else 0
        room(section_h + columns_h + first_h)
        pages[-1].append(("section", name))
        y -= section_h
        pages[-1].append(("columns",))
        y -= columns_h
        sub = 0.0
        for it in lines:
            h = _line_block_height(it)
            if room(h):
                pages[-1].append(("columns",))
                y -= columns_h
            pages[-1].append(("line", it))
            y -= h
            sub += _line_amount_value(it)
        room(subtotal_h)
        pages[-1].append(("subtotal", name, round(sub, 2)))
        y -= subtotal_h

    grand = round(sum(
        _line_amount_value(it) for _name, lines in sections for it in lines
    ), 2)
    has_extra = any(name.lower().startswith("extra") for name, _lines in sections)
    room(totals_h)
    pages[-1].append(("totals", grand, has_extra))
    y -= totals_h

    if notes:
        if y - (note_header + note_line * len(notes)) < floor:
            y = new_page()
        while notes:
            capacity = int((y - floor - note_header) // note_line)
            if capacity < 1:
                y = new_page()
                capacity = int((y - floor - note_header) // note_line)
            take = notes[:max(1, capacity)]
            notes = notes[len(take):]
            pages[-1].append(("notes", take))
            y -= note_header + note_line * len(take) + 8
            if notes:
                y = new_page()

    qty_x = PW - MARGIN_R - 200
    rate_x = PW - MARGIN_R - 96
    amount_x = PW - MARGIN_R
    total_pages = len(pages)

    for index, ops in enumerate(pages, start=1):
        if index > 1:
            c.showPage()
        _paint_page_chrome(c, quote, index, total_pages)
        y = CONTENT_TOP - 22
        for op in ops:
            kind = op[0]
            if kind == "client":
                y = _draw_client_block(c, quote, y)
            elif kind == "section":
                _section_label(c, MARGIN_L, y, str(op[1]), mono)
                y -= section_h
            elif kind == "columns" and sqft_mode:
                c.setFont(sans_b, 7.5)
                c.setFillColor(GOLD)
                c.drawString(MARGIN_L, y, "Description")
                c.drawRightString(qty6_x, y, "Qty")
                c.drawRightString(unit_x, y, "Unit")
                c.drawRightString(sqft_x, y, "Sq ft")
                c.drawRightString(price_x, y, "Price")
                c.drawRightString(total_x, y, "Total")
                _hr(c, y - 4, weight=0.7, col=GOLD)
                y -= columns_h
            elif kind == "line" and sqft_mode:
                it = op[1]
                desc_lines = _description_lines(it, _SQFT_DESC_W)
                sq, pps = _line_sqft(it)
                for i, line in enumerate(desc_lines):
                    c.setFont(sans_b if i == 0 else sans, _DESC_FONT if i == 0 else _DESC_FONT - 0.5)
                    c.setFillColor(DK if i == 0 else DETAIL)
                    c.drawString(MARGIN_L + (0 if i == 0 else 8), y, line)
                    if i == 0:
                        c.setFont(sans, _DESC_FONT)
                        c.setFillColor(DK)
                        c.drawRightString(qty6_x, y, _qty_text(it))
                        c.drawRightString(unit_x, y, _unit_text(it))
                        c.drawRightString(sqft_x, y, f"{sq:,.2f}" if sq is not None else "")
                        if sq is not None and pps is not None:
                            c.drawRightString(price_x, y, f"{pps:,.2f}")
                        else:
                            c.drawRightString(price_x, y, _rate_text(it).replace("$", ""))
                        c.drawRightString(total_x, y, _money(_line_amount_value(it)))
                    y -= _DESC_LEADING
                y -= _ROW_GAP
            elif kind == "columns":
                c.setFont(sans_b, 7.5)
                c.setFillColor(GOLD)
                c.drawString(MARGIN_L, y, "Description")
                c.drawRightString(qty_x, y, "Qty")
                c.drawRightString(rate_x, y, "Rate")
                c.drawRightString(amount_x, y, "Amount")
                _hr(c, y - 4, weight=0.7, col=GOLD)
                y -= columns_h
            elif kind == "line":
                it = op[1]
                desc_lines = _description_lines(it)
                c.setFont(sans, _DESC_FONT)
                for i, line in enumerate(desc_lines):
                    c.setFillColor(DK if i == 0 else DETAIL)
                    c.drawString(MARGIN_L, y, line)
                    if i == 0:
                        c.setFillColor(DK)
                        c.drawRightString(qty_x, y, _qty_with_unit(it))
                        c.drawRightString(rate_x, y, _rate_text(it))
                        c.drawRightString(amount_x, y, _money(_line_amount_value(it)))
                    y -= _DESC_LEADING
                y -= _ROW_GAP
            elif kind == "subtotal":
                y = _draw_band_subtotal(
                    c, y, f"SUBTOTAL — {op[1]}"[:80], _money(op[2]), sans_b, sans,
                )
            elif kind == "totals":
                y = _draw_totals(
                    c, quote, y, quoted_subtotal=op[1], has_extra_tbd=bool(op[2]),
                )
            elif kind == "notes":
                _section_label(c, MARGIN_L, y, "NOTES", mono)
                y -= note_header
                c.setFont(sans, 8)
                c.setFillColor(DETAIL)
                for line in op[1]:
                    if y < floor:
                        break
                    c.drawString(MARGIN_L, y, line[:110])
                    y -= note_line
                y -= 8

    if client_safe:
        optional = (quote.get("metadata") or {}).get("optional_hardware") or {}
        c.showPage()
        _paint_page_chrome(c, quote, total_pages + 1, total_pages + 1)
        y = CONTENT_TOP - 22
        _section_label(c, MARGIN_L, y, "OPTIONAL PASSWAY HARDWARE", mono)
        y -= 18
        c.setFont(sans_b, 9.5)
        c.setFillColor(DK)
        c.drawString(MARGIN_L, y, '2" rings, 8-pack — 3 packs')
        c.drawRightString(PW - MARGIN_R, y, _money(optional.get("rings", 224.85)))
        y -= 16
        c.drawString(MARGIN_L, y, '2" reeded pole, 8 ft — 1')
        c.drawRightString(PW - MARGIN_R, y, _money(optional.get("pole", 210.82)))
        y -= 16
        c.drawString(MARGIN_L, y, '2" single brackets, 3½" return — 3')
        c.drawRightString(PW - MARGIN_R, y, _money(optional.get("brackets", 96.24)))
        y -= 22
        _hr(c, y, col=GOLD)
        y -= 18
        optional_total = float(optional.get("total", 531.91) or 531.91)
        base_total = float(optional.get("base", 4724.75) or 4724.75)
        core_total = float(quote.get("total") or quote.get("subtotal") or 0)
        c.setFont(sans_b, 10)
        c.drawString(MARGIN_L, y, "Optional hardware subtotal")
        c.drawRightString(PW - MARGIN_R, y, _money(optional_total))
        y -= 20
        c.setFont(sans, 9)
        c.drawString(MARGIN_L, y, "Addendum total (hardware excluded)")
        c.drawRightString(PW - MARGIN_R, y, _money(core_total))
        y -= 16
        c.drawString(MARGIN_L, y, "Base estimate + addendum")
        c.drawRightString(PW - MARGIN_R, y, _money(base_total + core_total))
        y -= 16
        c.drawString(MARGIN_L, y, "Base + addendum + optional hardware")
        c.drawRightString(PW - MARGIN_R, y, _money(base_total + core_total + optional_total))

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
