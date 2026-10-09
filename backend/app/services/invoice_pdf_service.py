"""Client-facing Workroom / WoodCraft invoice PDF (HTML → WeasyPrint)."""
from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path
from typing import Optional

from app.config.workroom_billing import client_facing_website, get_workroom_billing

JOB_DEPOSIT_SCHEDULE_NOTE = (
    "50% deposit due to begin work. Balance due on completion."
)

_INTERNAL_NOTE_LINE = re.compile(
    r"^\s*(split\s+from|project\s*/\s*reference|reference\s*:)\b",
    re.IGNORECASE,
)
_SPLIT_FROM_INV = re.compile(r"split\s+from\s+INV[-\s]?", re.IGNORECASE)
_ALLOCATION_LINE = re.compile(
    r"^(?:[UL]\s+)?share\s*,?\s*\d+(?:\.\d+)?%\s+of\s+",
    re.IGNORECASE,
)
_ALLOCATION_TAIL = re.compile(
    r"(?:\s*[-–—,;]\s*)(?:[UL]\s+)?share\s*,?\s*\d+(?:\.\d+)?%\s+of\s+[\d.]+\s*(?:yd|yds|yards?|sf|sq\.?\s*ft\.?)?.*",
    re.IGNORECASE,
)
_ALLOCATION_PCT = re.compile(
    r"\s*\d+(?:\.\d+)?%\s+of\s+[\d.]+\s*(?:yd|yds|yards?|sf|sq\.?\s*ft\.?)\b.*",
    re.IGNORECASE,
)


def _looks_like_allocation_only(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return True
    if _ALLOCATION_LINE.match(t):
        return True
    return bool(
        re.search(r"share\s*,?\s*\d+(?:\.\d+)?%\s+of\s+", t, re.IGNORECASE)
        and re.search(r"%\s+of\s+[\d.]", t, re.IGNORECASE)
    )


def client_visible_line_description(item: dict) -> str:
    """Client invoice line text — no internal yardage/share allocation math."""
    for key in ("client_description", "display_description", "public_description"):
        val = item.get(key)
        if val and str(val).strip():
            return str(val).strip().split("\n")[0].strip()

    raw = (item.get("description") or "").strip()
    if not raw:
        return ""

    lines = [ln.strip() for ln in raw.replace("\r\n", "\n").split("\n") if ln.strip()]
    for line in lines:
        if _looks_like_allocation_only(line):
            continue
        cleaned = _ALLOCATION_TAIL.sub("", line)
        cleaned = _ALLOCATION_PCT.sub("", cleaned).strip(" ,;–—-")
        if cleaned and not _looks_like_allocation_only(cleaned):
            return cleaned

    first = lines[0]
    first = _ALLOCATION_TAIL.sub("", first)
    first = _ALLOCATION_PCT.sub("", first).strip(" ,;–—-")
    return first or lines[0]


def uses_job_deposit_schedule(invoice: dict) -> bool:
    """New-job / split-child invoices show 50% deposit + balance due on the PDF."""
    flag = invoice.get("client_job_deposit_schedule")
    if flag in (1, True, "1", "true"):
        return True
    return False


def job_deposit_amounts(total: float) -> tuple[float, float]:
    """Return (deposit_due, balance_due) as equal halves of invoice total."""
    half = round(float(total or 0) * 0.5, 2)
    remainder = round(float(total or 0) - half, 2)
    return half, remainder


def client_visible_notes(notes: Optional[str]) -> Optional[str]:
    """Strip internal-only reference lines from notes shown on client PDFs."""
    if not notes or not str(notes).strip():
        return None
    kept: list[str] = []
    for line in str(notes).replace("\r\n", "\n").split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if _INTERNAL_NOTE_LINE.match(stripped):
            continue
        if _SPLIT_FROM_INV.search(stripped):
            continue
        kept.append(stripped)
    text = "\n".join(kept).strip()
    return text or None


def _line_amount(item: dict) -> float:
    for key in ("total", "amount"):
        if item.get(key) is not None:
            try:
                return float(item[key])
            except (TypeError, ValueError):
                pass
    try:
        qty = float(item.get("quantity", 1) or 1)
        rate = float(item.get("unit_price", item.get("rate", 0)) or 0)
        return round(qty * rate, 2)
    except (TypeError, ValueError):
        return 0.0


def _plain(text: str) -> str:
    try:
        from app.services.pricing.dimensions import plain_fractions
        return plain_fractions(text)
    except Exception:
        return text


def _item_sqft(item: dict) -> tuple[Optional[float], Optional[float]]:
    """(sq_ft, price_per_sqft) from the line or its pricing snapshot; (None, None) when not a sq-ft line."""
    snap = item.get("pricing_snapshot") or item.get("pricing_snapshot_json") or {}
    if isinstance(snap, str):
        try:
            snap = json.loads(snap)
        except (TypeError, ValueError):
            snap = {}
    for src in (item, snap if isinstance(snap, dict) else {}):
        try:
            sq = src.get("sq_ft")
            rate = src.get("price_per_sqft")
            if sq not in (None, "") and rate not in (None, ""):
                return float(sq), float(rate)
        except (TypeError, ValueError, AttributeError):
            continue
    return None, None


def _change_order(invoice: dict) -> dict:
    snap = invoice.get("pricing_snapshot_json") or {}
    if isinstance(snap, str):
        try:
            snap = json.loads(snap)
        except (TypeError, ValueError):
            snap = {}
    co = snap.get("change_order") if isinstance(snap, dict) else None
    return co if isinstance(co, dict) else {}


def _mdy(value: str) -> str:
    v = str(value or "")[:10]
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
        return f"{v[5:7]}/{v[8:10]}/{v[0:4]}"
    return v


def credit_schedule(invoice: dict) -> Optional[dict]:
    """Deposit already received elsewhere (e.g. a change order applying an earlier deposit):
    total, less deposit received, deposit required, deposit due now, balance on completion."""
    try:
        total = float(invoice.get("total") or 0)
        received = float(invoice.get("deposit_received") or 0)
        required = float(invoice.get("deposit_required") or 0)
    except (TypeError, ValueError):
        return None
    if not (total > 0 and received > 0 and required > 0 and required <= total):
        return None
    return {
        "total": round(total, 2),
        "received": round(received, 2),
        "received_date": _mdy(invoice.get("deposit_date") or ""),
        "required": round(required, 2),
        "due_now": round(max(required - received, 0), 2),
        "balance_on_completion": round(total - required, 2),
    }


def final_settlement(invoice: dict) -> dict:
    snap = invoice.get("pricing_snapshot_json") or {}
    if isinstance(snap, str):
        try:
            snap = json.loads(snap)
        except (TypeError, ValueError):
            snap = {}
    fs = snap.get("final_settlement") if isinstance(snap, dict) else None
    return fs if isinstance(fs, dict) else {}


def _ledger_for_pdf(invoice: dict) -> tuple[list, list]:
    """(credits, prior invoices) for a final invoice; uses data attached by the caller,
    else reads the job ledger."""
    credits = invoice.get("_ledger_credits")
    prior = invoice.get("_ledger_prior")
    if credits is not None:
        return list(credits), list(prior or [])
    try:
        from app.db.database import get_db
        from app.services.job_ledger import final_credits, job_ledger
        with get_db() as conn:
            credits = final_credits(conn, invoice)
            led = job_ledger(conn, invoice["id"])
        prior = [i for i in led["invoices"] if i["id"] != invoice.get("id") and not i["void"]]
        return credits, prior
    except Exception:
        return [], []


def _settlement_rows(invoice: dict, accent: str) -> str:
    credits, prior = _ledger_for_pdf(invoice)
    total = float(invoice.get("total") or 0)
    credit_total = round(sum(float(c.get("amount") or 0) for c in credits), 2)
    balance = round(total - credit_total - float(invoice.get("amount_paid") or 0), 2)
    rows = ['<tr><td colspan="2" style="padding-top:12px;font-weight:700;text-transform:uppercase;'
            f'font-size:9pt;letter-spacing:.06em;color:{accent}">Payments &amp; credits applied</td></tr>']
    if not credits:
        rows.append('<tr><td style="color:#777">No payments received yet</td><td style="text-align:right">$0.00</td></tr>')
    for c in credits:
        bits = [escape(str(c.get("label") or "Payment received"), quote=False)]
        if c.get("payment_date"):
            bits.append(_mdy(c["payment_date"]))
        if c.get("invoice_number"):
            bits.append(escape(str(c["invoice_number"]), quote=False))
        if c.get("method"):
            bits.append(escape(str(c["method"]), quote=False))
        rows.append(f'<tr><td>{" &middot; ".join(bits)}</td>'
                    f'<td style="text-align:right">-${float(c.get("amount") or 0):,.2f}</td></tr>')
    own = float(invoice.get("amount_paid") or 0)
    if own > 0:
        rows.append(f'<tr><td>Paid on this invoice</td><td style="text-align:right">-${own:,.2f}</td></tr>')
    rows.append(f'<tr><td>Total payments &amp; credits</td><td style="text-align:right">-${credit_total + own:,.2f}</td></tr>')
    rows.append(f'<tr class="deposit-due-row"><td><strong>Balance due</strong></td>'
                f'<td style="text-align:right;font-weight:700;color:{accent}">${max(balance, 0):,.2f}</td></tr>')
    if balance < 0:
        rows.append(f'<tr><td>Credit balance</td><td style="text-align:right">${-balance:,.2f}</td></tr>')
    if prior:
        names = []
        for p in prior:
            names.append(f'{escape(str(p.get("invoice_number") or ""), quote=False)} (${float(p.get("total") or 0):,.2f}, '
                         f'paid ${float(p.get("paid") or 0):,.2f})')
        rows.append('<tr><td colspan="2" style="font-size:8.5pt;color:#777;padding-top:6px">Earlier invoices on this job: '
                    + "; ".join(names) + ". Their payments are applied above; their open balances are replaced by this invoice.</td></tr>")
    return "\n  ".join(rows)


_OPEN_LINK_STATUSES = {"link_ready", "awaiting_confirmation", "unpaid", ""}


def deposit_pay_link(invoice: dict) -> Optional[dict]:
    """Deposit-stage invoice with an open Stripe Checkout URL -> {url, amount}; else None."""
    if str(invoice.get("invoice_stage") or "").strip().lower() != "deposit":
        return None
    link = invoice_pay_link(invoice)
    return {"url": link["url"], "amount": link["amount"]} if link else None


def invoice_pay_link(invoice: dict) -> Optional[dict]:
    """Deposit or final invoice with an open Stripe Checkout URL -> {url, amount, label}.
    The amount is always the balance due now (never the gross total)."""
    url = str(invoice.get("stripe_checkout_url") or "").strip()
    if not url.startswith("https://buy.stripe.com/"):
        return None  # only non-expiring Payment Links; 24-hour Checkout Session URLs never go on a PDF
    stage = str(invoice.get("invoice_stage") or "").strip().lower()
    if stage not in ("deposit", "final", "progress"):
        return None
    if str(invoice.get("status") or "").lower() in ("paid", "cancelled"):
        return None
    if str(invoice.get("payment_status") or "").strip().lower() not in _OPEN_LINK_STATUSES:
        return None
    try:
        amount = float(invoice.get("balance_due") if invoice.get("balance_due") is not None else invoice.get("total") or 0)
    except (TypeError, ValueError):
        return None
    if amount <= 0:
        return None
    label = "Pay deposit online" if stage == "deposit" else "Pay balance online"
    return {"url": url, "amount": round(amount, 2), "label": label}


def _qr_data_uri(url: str) -> str:
    """PNG QR code of the URL as a data: URI (empty string if the QR library is missing)."""
    try:
        import base64
        import io
        import qrcode
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=6, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return ""


def _pay_link_html(invoice: dict, accent: str) -> str:
    link = invoice_pay_link(invoice)
    if not link:
        return ""
    url = escape(link["url"], quote=True)
    qr = _qr_data_uri(link["url"])
    qr_html = (f'<img src="{qr}" alt="Pay online QR code" style="width:140px;height:140px;display:block">'
               if qr else "")
    return f"""<div style="margin:14px 0;padding:10px 14px;border:2px solid {accent};page-break-inside:avoid;border-radius:8px;display:flex;align-items:center;gap:16px">
  {qr_html}
  <div style="font-size:10.5pt">
    <a href="{url}" style="color:{accent};font-weight:700;font-size:13pt;text-decoration:underline">{link['label']}: ${link['amount']:,.2f}</a><br>
    <span style="font-size:8.5pt;color:#666">Click the link or scan the code to pay securely by card (Stripe).</span>
  </div>
</div>"""


def _load_biz_cfg(is_woodcraft: bool) -> dict:
    config_dir = Path(__file__).resolve().parent.parent / "config"
    path = config_dir / ("woodcraft_business.json" if is_woodcraft else "business.json")
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def resolve_invoice_branding(invoice: dict, is_woodcraft: bool) -> dict:
    if is_woodcraft:
        cfg = _load_biz_cfg(True)
        return {
            "name": cfg.get("business_name", "WoodCraft by Empire"),
            "tagline": cfg.get("business_tagline", "Custom Woodwork & CNC"),
            "phone": cfg.get("business_phone", ""),
            "email": cfg.get("business_email", ""),
            "address": cfg.get("business_address", ""),
            "website": client_facing_website(cfg.get("business_website", "")),
            "accent": "#d4a636",
            "header_bg": "#3d2e1a",
        }
    billing = get_workroom_billing(invoice.get("billed_by"))
    return {
        "name": billing.name,
        "tagline": billing.tagline,
        "phone": billing.phone,
        "email": billing.email,
        "address": billing.address,
        "website": billing.website,
        "accent": "#b8960c",
        "header_bg": "#2c2416",
    }


def render_client_invoice_html(
    invoice: dict,
    *,
    customer: Optional[dict] = None,
    is_woodcraft: bool = False,
) -> str:
    """Minimal client invoice: Bill To, meta, line table, totals, optional note."""
    brand = resolve_invoice_branding(invoice, is_woodcraft)
    accent = brand["accent"]

    client_name = (
        invoice.get("client_name")
        or (customer or {}).get("name")
        or "Customer"
    )
    client_email = invoice.get("client_email") or (customer or {}).get("email", "")
    client_phone = invoice.get("client_phone") or (customer or {}).get("phone", "")
    client_addr = (
        invoice.get("client_address")
        or invoice.get("billing_address")
        or (customer or {}).get("address", "")
    )

    client_block = f"<strong>{client_name}</strong>"
    if client_email:
        client_block += f"<br>{client_email}"
    if client_phone:
        client_block += f"<br>{client_phone}"
    if client_addr:
        client_block += f"<br>{client_addr}"

    items = list(invoice.get("line_items") or [])
    rows_html = ""
    has_rooms = any(str(it.get("room") or "").strip() for it in items)
    sqft_mode = any(_item_sqft(it)[0] is not None for it in items)
    ncols = 6 if sqft_mode else 5
    current_room = None
    room_total = 0.0
    td = "padding:5px 8px;border-bottom:1px solid #e8e4dd;font-size:9.5pt;line-height:1.3"

    def _room_subtotal(name: str, amount: float) -> str:
        return (f'<tr><td colspan="{ncols - 1}" style="padding:7px 12px;font-weight:700;background:#f3eee4">'
                f'Subtotal &mdash; {escape(name, quote=False)}</td>'
                f'<td style="padding:7px 12px;text-align:right;font-weight:700;background:#f3eee4">${amount:,.2f}</td></tr>')

    for idx, item in enumerate(items):
        if has_rooms:
            # room section headers, same grouping as the in-app invoice page (items are saved in room order)
            room = str(item.get("room") or "").strip() or "Job-wide"
            if room != current_room:
                if sqft_mode and current_room is not None:
                    rows_html += _room_subtotal(current_room, room_total)
                current_room = room
                room_total = 0.0
                rows_html += f"""<tr><td colspan="{ncols}" style="padding:{'6px 8px 4px' if sqft_mode else '9px 12px 6px'};border-bottom:2px solid #c9a04a;font-weight:700;letter-spacing:.06em;text-transform:uppercase;font-size:9.5pt;background:#f3eee4">{escape(room, quote=False)}</td></tr>"""
        bg = "#f9f7f3" if idx % 2 == 0 else "#ffffff"
        desc = escape(_plain(client_visible_line_description(item)), quote=False)
        unit = (item.get("unit") or "ea").strip() or "ea"
        qty = item.get("quantity", 1)
        unit_price = item.get("unit_price", item.get("rate", 0))
        amount = _line_amount(item)
        room_total += amount
        if sqft_mode:
            try:
                qf = float(qty)
                qty = int(qf) if qf.is_integer() else qty
            except (TypeError, ValueError):
                pass
            raw_lines = [ln.strip() for ln in str(item.get("description") or "").split("\n") if ln.strip()]
            sub = escape(_plain(raw_lines[1]), quote=False) if len(raw_lines) > 1 else ""
            sub_html = f'<div style="font-size:8.5pt;color:#777;margin-top:2px">{sub}</div>' if sub else ""
            sq, rate = _item_sqft(item)
            sq_txt = f"{sq:,.2f}" if sq is not None else ""
            rate_txt = f"{rate:,.2f}" if rate is not None else f"{float(unit_price or 0):,.2f}"
            rows_html += f"""<tr style="background:{bg}">
            <td style="{td}"><strong>{desc}</strong>{sub_html}</td>
            <td style="{td};text-align:center">{qty}</td>
            <td style="{td};text-align:center">{unit}</td>
            <td style="{td};text-align:right">{sq_txt}</td>
            <td style="{td};text-align:right">{rate_txt}</td>
            <td style="{td};text-align:right">${amount:,.2f}</td>
        </tr>"""
            continue
        rows_html += f"""<tr style="background:{bg}">
            <td style="padding:10px 12px;border-bottom:1px solid #e8e4dd">{desc}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #e8e4dd;text-align:center">{qty}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #e8e4dd;text-align:center">{unit}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #e8e4dd;text-align:right">${float(unit_price or 0):,.2f}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #e8e4dd;text-align:right">${amount:,.2f}</td>
        </tr>"""
    if sqft_mode and has_rooms and current_room is not None:
        rows_html += _room_subtotal(current_room, room_total)

    if not rows_html:
        sub = float(invoice.get("subtotal", 0) or 0)
        rows_html = f"""<tr style="background:#f9f7f3">
            <td style="padding:10px 12px" colspan="4">Services as quoted</td>
            <td style="padding:10px 12px;text-align:right">${sub:,.2f}</td>
        </tr>"""

    inv_num = invoice.get("invoice_number", "")
    inv_date = (invoice.get("invoice_date") or invoice.get("created_at") or "")[:10]
    due = invoice.get("due_date", "N/A")
    terms = invoice.get("terms", "Net 30")
    tax_rate = float(invoice.get("tax_rate", 0) or 0)
    subtotal = float(invoice.get("subtotal", 0) or 0)
    tax_amount = float(invoice.get("tax_amount", 0) or 0)
    total = float(invoice.get("total", 0) or 0)

    schedule = uses_job_deposit_schedule(invoice) and not is_woodcraft
    deposit_due, balance_due = job_deposit_amounts(total) if schedule else (0.0, 0.0)

    note_parts: list[str] = []
    if schedule:
        note_parts.append(JOB_DEPOSIT_SCHEDULE_NOTE)
    client_note = client_visible_notes(invoice.get("notes"))
    if client_note:
        note_parts.append(client_note)
    note_html = ""
    if note_parts:
        body = "<br>".join(escape(_plain(p), quote=False) for p in note_parts)
        note_html = (
            f'<div style="margin:24px 0;padding:12px;background:#f5f3ef;'
            f'border-radius:8px;font-size:10pt">{body}</div>'
        )

    totals_deposit_rows = ""
    co = _change_order(invoice)
    credit = credit_schedule(invoice) if (co and not schedule) else None
    if credit:
        ref = f" &middot; {escape(str(co.get('credit_ref')), quote=False)}" if co.get("credit_ref") else ""
        pct = invoice.get("deposit_percent") or co.get("deposit_percent") or 50
        totals_deposit_rows = f"""
  <tr><td>Less deposit received {credit['received_date']}{ref}</td><td style="text-align:right">-${credit['received']:,.2f}</td></tr>
  <tr><td>Deposit required ({float(pct):g}%)</td><td style="text-align:right">${credit['required']:,.2f}</td></tr>
  <tr class="deposit-due-row"><td><strong>Deposit due now</strong></td>
      <td style="text-align:right;font-weight:700;color:{accent}">${credit['due_now']:,.2f}</td></tr>
  <tr><td>Balance on completion</td><td style="text-align:right">${credit['balance_on_completion']:,.2f}</td></tr>"""
    elif final_settlement(invoice) and not is_woodcraft:
        totals_deposit_rows = _settlement_rows(invoice, accent)
    elif schedule:
        totals_deposit_rows = f"""
  <tr class="deposit-due-row"><td><strong>50% Deposit Due</strong></td>
      <td style="text-align:right;font-weight:700;color:{accent}">${deposit_due:,.2f}</td></tr>
  <tr><td>Balance Due</td><td style="text-align:right">${balance_due:,.2f}</td></tr>"""

    head_mid = ('<th style="text-align:right">Sq ft</th><th style="text-align:right">Price</th><th style="text-align:right">Total</th>'
                if sqft_mode else
                '<th style="text-align:right">Unit Price</th><th style="text-align:right">Amount</th>')
    totals_width = 460 if final_settlement(invoice) else (420 if credit else 300)
    co_title = ""
    if co.get("number"):
        co_title = f'<div class="invoice-number" style="font-weight:700">Change Order {escape(str(co.get("number")), quote=False)}</div>'

    pay_html = _pay_link_html(invoice, accent) if not is_woodcraft else ""
    page_margin = "0.55in" if sqft_mode else "0.75in"

    contact_bits = [b for b in (brand["phone"], brand["email"], brand["address"]) if b]
    contact_html = "<br>".join(contact_bits)

    logo_html = brand["name"]
    if is_woodcraft:
        logo_html = '<span style="color:#d4a636">Wood</span>Craft'

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  @page {{ size: letter; margin: {page_margin}; }}
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #1a1a2e; font-size: 11pt; line-height: 1.5; }}
  .header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 28px; padding-bottom: 18px; border-bottom: 3px solid {accent}; }}
  .logo {{ font-size: 22pt; font-weight: 800; color: #1a1a2e; }}
  .tagline {{ font-size: 9pt; color: #666; margin-top: 4px; }}
  .invoice-title {{ text-align: right; }}
  .invoice-title h1 {{ margin: 0; font-size: 26pt; color: {accent}; letter-spacing: 2px; }}
  .invoice-number {{ font-size: 11pt; color: #666; margin-top: 4px; }}
  .info-grid {{ display: flex; justify-content: space-between; margin: 20px 0; gap: 24px; }}
  .info-box h3 {{ margin: 0 0 6px; font-size: 9pt; text-transform: uppercase; color: {accent}; letter-spacing: 1px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
  thead {{ background: #f5f3ef; }}
  tr {{ page-break-inside: avoid; }}
  th {{ white-space: nowrap; padding: 10px 12px; text-align: left; font-size: 9pt; text-transform: uppercase; color: #666; letter-spacing: 0.5px; border-bottom: 2px solid {accent}; }}
  .totals {{ margin-left: auto; width: {totals_width}px; }}
  .totals tr td {{ padding: 6px 12px; }}
  .totals .total-row {{ font-size: 14pt; font-weight: 700; border-top: 2px solid {accent}; }}
  .totals .deposit-due-row td {{ padding-top: 10px; }}
  .footer {{ margin-top: 18px; padding-top: 10px; page-break-inside: avoid; border-top: 1px solid #e8e4dd; font-size: 9pt; color: #888; text-align: center; }}
</style></head><body>
<title>INVOICE</title>
{('<div style="border:2px dashed #b00;color:#b00;text-align:center;font-weight:700;padding:6px;margin-bottom:12px">DRY RUN &mdash; not issued, not sent</div>' if invoice.get("_dry_run") else "")}

<div class="header">
  <div>
    <div class="logo">{logo_html}</div>
    <div class="tagline">{brand["tagline"]}</div>
    <div style="font-size:9pt;color:#666;margin-top:6px;line-height:1.6">{contact_html}</div>
  </div>
  <div class="invoice-title">
    <h1>INVOICE</h1>
    <div class="invoice-number">{inv_num}</div>
    {co_title}{('<div class="invoice-number" style="font-weight:700">Final invoice</div>' if final_settlement(invoice) else "")}
  </div>
</div>

<div class="info-grid">
  <div class="info-box">
    <h3>Bill To</h3>
    <p style="margin:0">{client_block}</p>
  </div>
  <div class="info-box" style="text-align:right">
    <h3>Invoice Details</h3>
    <p style="margin:0">
      <strong>Date:</strong> {inv_date}<br>
      <strong>Due:</strong> {due}<br>
      <strong>Terms:</strong> {terms}
    </p>
  </div>
</div>

<table>
  <thead><tr>
    <th>Description</th>
    <th style="text-align:center">Qty</th>
    <th style="text-align:center">Unit</th>
    {head_mid}
  </tr></thead>
  <tbody>{rows_html}</tbody>
</table>

<table class="totals">
  <tr><td>Subtotal</td><td style="text-align:right">${subtotal:,.2f}</td></tr>
  <tr><td>Tax ({tax_rate * 100:.1f}%)</td><td style="text-align:right">${tax_amount:,.2f}</td></tr>
  <tr class="total-row"><td>Total</td><td style="text-align:right">${total:,.2f}</td></tr>
  {totals_deposit_rows}
</table>

{pay_html}

{note_html}

<div class="footer">
  {brand["name"]} &mdash; Thank you for your business<br>
  {brand["phone"]} &bull; {brand["email"]} &bull; {brand["website"]}
</div>

</body></html>"""


def generate_client_invoice_pdf_bytes(
    invoice: dict,
    *,
    customer: Optional[dict] = None,
    is_woodcraft: bool = False,
) -> bytes:
    if not is_woodcraft:
        try:
            from app.services.estimates.invoice_mclean_pdf import render_invoice_bytes
            return render_invoice_bytes(invoice, customer)
        except Exception:  # never fail an invoice over layout: fall back to the plain template
            import logging
            logging.getLogger(__name__).exception("estimate-style invoice render failed; using plain template")
    import weasyprint

    html = render_client_invoice_html(invoice, customer=customer, is_woodcraft=is_woodcraft)
    return weasyprint.HTML(string=html).write_pdf()


def subtotal_from_line_items(line_items: list[dict]) -> float:
    return round(sum(_line_amount(item) for item in (line_items or [])), 2)
