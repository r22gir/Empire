"""Workroom quotes & invoices commerce helpers.

Pure, fixture-friendly logic for:
  1. Optional add-on lines that update estimate total + deposit live
  2. Client portal Approve & Pay Deposit with e-signature + Stripe Payment Links
  3. Quote/invoice follow-up reminders (OFF by default; owner opt-in per client)
  4. Google review request after invoice paid (owner-approved before send)
  5. Inch measurements as fractions (e.g. 36 1/2)

Tests inject an isolated store. This module never opens the live empire.db.
Stripe is never called unless a client is injected.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Callable, Optional
from uuid import uuid4

MONEY_QUANT = Decimal("0.01")
DEFAULT_DEPOSIT_PERCENT = Decimal("50")
DEFAULT_GOOGLE_REVIEW_URL = ""
CONSENT_TEXT = (
    "I have reviewed this estimate, I approve the scope and pricing, "
    "and I authorize Empire Workroom to collect the listed deposit."
)

# Sixteenth-inch snap used by workroom tape measures.
_FRACTION_DENOM = 16
_FRACTION_RE = re.compile(
    r"""
    ^\s*
    (?P<sign>-)?
    (?:
        (?P<whole>\d+)\s+(?P<num>\d+)\s*/\s*(?P<den>\d+)   # 36 1/2
      | (?P<only_num>\d+)\s*/\s*(?P<only_den>\d+)           # 1/2
      | (?P<inches>\d+(?:\.\d+)?)                           # 36 or 36.5
    )
    \s*(?:in|inch|inches|")?
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _money(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0.00")
    if isinstance(value, Decimal):
        amount = value
    else:
        amount = Decimal(str(value))
    return amount.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _percent(value: Any, default: Decimal = DEFAULT_DEPOSIT_PERCENT) -> Decimal:
    if value is None or value == "":
        return default
    return Decimal(str(value))


def money_float(value: Any) -> float:
    return float(_money(value))


# ── Measurements in fractions ───────────────────────────────────────

def parse_fraction_inches(value: Any) -> float:
    """Parse workroom measurements: 36, 36.5, 36 1/2, 1/2, 36\".

    Invalid / empty input returns 0.0 so quote math stays safe.
    """
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    text = str(value).strip()
    if not text:
        return 0.0
    match = _FRACTION_RE.match(text)
    if not match:
        try:
            return float(text.replace('"', "").replace("in", "").strip())
        except ValueError:
            return 0.0
    sign = -1.0 if match.group("sign") else 1.0
    if match.group("whole") is not None:
        inches = float(match.group("whole")) + (
            float(match.group("num")) / float(match.group("den"))
        )
    elif match.group("only_num") is not None:
        inches = float(match.group("only_num")) / float(match.group("only_den"))
    else:
        inches = float(match.group("inches"))
    return sign * inches


def format_fraction_inches(value: Any, max_denominator: int = _FRACTION_DENOM) -> str:
    """Format inches as a workroom fraction, snapped to sixteenths."""
    inches = parse_fraction_inches(value)
    if inches == 0:
        return "0"
    sign = "-" if inches < 0 else ""
    inches = abs(inches)
    whole = int(math.floor(inches + 1e-9))
    frac = inches - whole
    sixteenths = int(round(frac * max_denominator))
    if sixteenths == max_denominator:
        whole += 1
        sixteenths = 0
    if sixteenths == 0:
        return f"{sign}{whole}"
    num, den = sixteenths, max_denominator
    while num % 2 == 0 and den % 2 == 0:
        num //= 2
        den //= 2
    if whole == 0:
        return f"{sign}{num}/{den}"
    return f"{sign}{whole} {num}/{den}"


def format_measurement_triple(width: Any, height: Any, depth: Any = None) -> str:
    parts = []
    for value in (width, height, depth):
        if value in (None, "", 0, 0.0, "0"):
            continue
        parts.append(f'{format_fraction_inches(value)}"')
    return " x ".join(parts)


# ── Add-on lines + live totals ──────────────────────────────────────

def normalize_addon(raw: dict) -> dict:
    quantity = parse_fraction_inches(raw.get("quantity", 1)) or 1.0
    rate = _money(raw.get("rate", raw.get("unit_price", raw.get("amount", 0))))
    selected = bool(raw.get("selected", False))
    amount = _money(Decimal(str(quantity)) * rate)
    return {
        "id": raw.get("id") or f"addon-{uuid4().hex[:8]}",
        "description": (raw.get("description") or "Add-on").strip() or "Add-on",
        "quantity": quantity,
        "unit": raw.get("unit") or "ea",
        "rate": money_float(rate),
        "amount": money_float(amount),
        "optional": bool(raw.get("optional", True)),
        "selected": selected,
        "category": raw.get("category") or "addon",
    }


def selected_addon_total(addons: list[dict] | None) -> Decimal:
    total = Decimal("0.00")
    for raw in addons or []:
        addon = normalize_addon(raw)
        if addon["selected"]:
            total += _money(addon["amount"])
    return total


def compute_estimate_totals(
    line_items: list[dict] | None = None,
    addons: list[dict] | None = None,
    tax_rate: Any = 0,
    discount_amount: Any = 0,
    discount_type: str = "dollar",
    deposit_percent: Any = DEFAULT_DEPOSIT_PERCENT,
    deposit_paid: Any = 0,
) -> dict:
    """Recalculate estimate subtotal, tax, total, and deposit from lines + add-ons.

    Optional add-ons only affect totals when selected=True.
    """
    items = []
    items_subtotal = Decimal("0.00")
    for raw in line_items or []:
        qty = parse_fraction_inches(raw.get("quantity", raw.get("qty", 1))) or 1.0
        rate = _money(raw.get("rate", raw.get("unit_price", raw.get("price", 0))))
        amount = _money(raw.get("amount") or raw.get("final_price") or (Decimal(str(qty)) * rate))
        items.append({
            **raw,
            "quantity": qty,
            "rate": money_float(rate),
            "amount": money_float(amount),
        })
        items_subtotal += amount

    normalized_addons = [normalize_addon(a) for a in (addons or [])]
    addon_total = selected_addon_total(normalized_addons)
    subtotal = _money(items_subtotal + addon_total)

    discount_raw = _money(discount_amount)
    if (discount_type or "dollar") == "percent" and discount_raw > 0:
        discount = _money(subtotal * (discount_raw / Decimal("100")))
    else:
        discount = discount_raw

    rate = Decimal(str(tax_rate or 0))
    if rate > 1:
        rate = rate / Decimal("100")
    tax_amount = _money(subtotal * rate)
    total = _money(subtotal + tax_amount - discount)
    if total < 0:
        total = Decimal("0.00")

    dep_pct = _percent(deposit_percent)
    deposit_amount = _money(total * dep_pct / Decimal("100"))
    paid = _money(deposit_paid)
    balance_due = _money(total - paid)

    return {
        "line_items": items,
        "addons": normalized_addons,
        "items_subtotal": money_float(items_subtotal),
        "addon_total": money_float(addon_total),
        "subtotal": money_float(subtotal),
        "tax_rate": float(rate),
        "tax_amount": money_float(tax_amount),
        "discount_amount": money_float(discount),
        "discount_type": discount_type or "dollar",
        "total": money_float(total),
        "deposit_percent": float(dep_pct),
        "deposit_amount": money_float(deposit_amount),
        "deposit_required": money_float(deposit_amount),
        "deposit_paid": money_float(paid),
        "balance_due": money_float(balance_due),
    }


def apply_totals_to_quote(quote: dict) -> dict:
    """Mutate a quote dict with live totals including selected add-ons."""
    deposit = quote.get("deposit") or {}
    totals = compute_estimate_totals(
        line_items=quote.get("line_items") or quote.get("items"),
        addons=quote.get("addons") or quote.get("add_ons"),
        tax_rate=quote.get("tax_rate", 0),
        discount_amount=quote.get("discount_amount", 0),
        discount_type=quote.get("discount_type") or "dollar",
        deposit_percent=deposit.get("deposit_percent", quote.get("deposit_percent", DEFAULT_DEPOSIT_PERCENT)),
        deposit_paid=quote.get("deposit_paid", 0),
    )
    quote["line_items"] = totals["line_items"]
    quote["addons"] = totals["addons"]
    quote["items_subtotal"] = totals["items_subtotal"]
    quote["addon_total"] = totals["addon_total"]
    quote["subtotal"] = totals["subtotal"]
    quote["tax_amount"] = totals["tax_amount"]
    quote["total"] = totals["total"]
    quote["deposit_percent"] = totals["deposit_percent"]
    quote["deposit_required"] = totals["deposit_required"]
    quote["deposit_amount"] = totals["deposit_amount"]
    quote["balance_due"] = totals["balance_due"]
    quote["deposit"] = {
        **deposit,
        "deposit_percent": totals["deposit_percent"],
        "deposit_amount": totals["deposit_amount"],
    }
    return quote


# ── E-signature ─────────────────────────────────────────────────────

def quote_document_hash(quote: dict) -> str:
    snapshot = {
        "id": quote.get("id"),
        "quote_number": quote.get("quote_number"),
        "total": quote.get("total"),
        "deposit_amount": (quote.get("deposit") or {}).get("deposit_amount") or quote.get("deposit_amount"),
        "line_items": quote.get("line_items") or [],
        "addons": quote.get("addons") or [],
    }
    payload = json.dumps(snapshot, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def capture_esignature(
    quote: dict,
    signer_name: str,
    signature_data: str,
    *,
    ip_address: str = "",
    user_agent: str = "",
    signed_at: Optional[str] = None,
) -> dict:
    name = (signer_name or "").strip()
    ink = (signature_data or "").strip()
    if not name:
        raise ValueError("signer_name is required")
    if not ink:
        raise ValueError("signature_data is required")
    if len(ink) < 8:
        raise ValueError("signature_data is too short to be a captured signature")
    return {
        "id": f"esign-{uuid4().hex[:12]}",
        "quote_id": quote.get("id"),
        "signer_name": name,
        "signature_data": ink,
        "consent_text": CONSENT_TEXT,
        "document_hash": quote_document_hash(quote),
        "signed_at": signed_at or datetime.now(timezone.utc).isoformat(),
        "ip_address": ip_address or "",
        "user_agent": user_agent or "",
    }


# ── Stripe Payment Links (non-expiring) ─────────────────────────────

def build_deposit_payment_link_params(
    quote: dict,
    *,
    success_url: Optional[str] = None,
    currency: str = "usd",
) -> dict:
    """Build Stripe PaymentLink.create kwargs. No expiration is set.

    Payment Links stay active until deactivated. Checkout Sessions expire;
    this path must not create a Checkout Session.
    """
    totals = compute_estimate_totals(
        line_items=quote.get("line_items"),
        addons=quote.get("addons"),
        tax_rate=quote.get("tax_rate", 0),
        discount_amount=quote.get("discount_amount", 0),
        discount_type=quote.get("discount_type") or "dollar",
        deposit_percent=(quote.get("deposit") or {}).get(
            "deposit_percent", quote.get("deposit_percent", DEFAULT_DEPOSIT_PERCENT)
        ),
        deposit_paid=quote.get("deposit_paid", 0),
    )
    amount_cents = int((Decimal(str(totals["deposit_amount"])) * 100).quantize(Decimal("1")))
    if amount_cents <= 0:
        raise ValueError("Deposit amount must be greater than zero")

    quote_number = quote.get("quote_number") or quote.get("id") or "estimate"
    params: dict[str, Any] = {
        "line_items": [
            {
                "price_data": {
                    "currency": currency,
                    "unit_amount": amount_cents,
                    "product_data": {
                        "name": f"Deposit — {quote_number}",
                        "description": f"Empire Workroom deposit for estimate {quote_number}",
                    },
                },
                "quantity": 1,
            }
        ],
        "metadata": {
            "flow": "workroom_deposit",
            "quote_id": str(quote.get("id") or ""),
            "quote_number": str(quote_number),
            "kind": "deposit",
        },
        "after_completion": {"type": "hosted_confirmation"},
        "inactive": False,
    }
    if success_url:
        params["after_completion"] = {
            "type": "redirect",
            "redirect": {"url": success_url},
        }
    return params


def assert_non_expiring_payment_link(params: dict) -> None:
    """Guardrail: Payment Links must not carry Checkout-style expiry."""
    forbidden = {"expires_at", "expires_after_days", "expires_after_seconds"}
    found = forbidden.intersection(params)
    if found:
        raise ValueError(f"Payment Link must not expire; unexpected keys: {sorted(found)}")
    restrictions = params.get("restrictions") or {}
    if restrictions.get("completed_sessions"):
        raise ValueError("Payment Link must not auto-expire via completed_sessions")


def create_payment_link(params: dict, stripe_client: Any = None) -> dict:
    """Create a Stripe Payment Link, or return an honest unconfigured result.

    Never falls back to Checkout Sessions (those expire).
    """
    assert_non_expiring_payment_link(params)
    if stripe_client is None:
        return {
            "created": False,
            "reason": "stripe_unconfigured",
            "url": None,
            "id": None,
            "expires_at": None,
            "params": params,
        }
    link = stripe_client.PaymentLink.create(**params)
    url = getattr(link, "url", None) or (link.get("url") if isinstance(link, dict) else None)
    link_id = getattr(link, "id", None) or (link.get("id") if isinstance(link, dict) else None)
    return {
        "created": True,
        "reason": None,
        "url": url,
        "id": link_id,
        "expires_at": None,
        "params": params,
    }


def approve_and_pay_deposit(
    quote: dict,
    signer_name: str,
    signature_data: str,
    *,
    ip_address: str = "",
    user_agent: str = "",
    stripe_client: Any = None,
    success_url: Optional[str] = None,
) -> dict:
    """One-tap portal action: capture e-sign, approve quote, issue Payment Link."""
    totals = apply_totals_to_quote(dict(quote))
    esign = capture_esignature(
        totals,
        signer_name,
        signature_data,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    params = build_deposit_payment_link_params(totals, success_url=success_url)
    payment_link = create_payment_link(params, stripe_client=stripe_client)
    return {
        "success": True,
        "quote_id": totals.get("id") or quote.get("id"),
        "status": "approved",
        "esignature": {k: v for k, v in esign.items() if k != "signature_data"} | {
            "signature_captured": True,
        },
        "esignature_record": esign,
        "deposit_amount": totals["deposit_amount"],
        "total": totals["total"],
        "payment_link": payment_link,
        "payment_url": payment_link.get("url"),
        "message": "Quote approved. Pay the deposit with the Payment Link.",
    }


# ── Follow-up reminders (opt-in, default OFF) ───────────────────────

DEFAULT_FOLLOWUP_PREFS = {
    "quote_reminders_enabled": False,
    "invoice_reminders_enabled": False,
    "enabled_by": None,
    "enabled_at": None,
}


def default_followup_prefs(customer_id: str) -> dict:
    return {
        "customer_id": customer_id,
        **DEFAULT_FOLLOWUP_PREFS,
    }


def set_followup_prefs(
    customer_id: str,
    *,
    quote_reminders_enabled: bool = False,
    invoice_reminders_enabled: bool = False,
    enabled_by: str = "owner",
    enabled_at: Optional[str] = None,
) -> dict:
    """Owner opt-in only. Defaults stay False unless explicitly enabled."""
    now = enabled_at or datetime.now(timezone.utc).isoformat()
    any_on = bool(quote_reminders_enabled or invoice_reminders_enabled)
    return {
        "customer_id": customer_id,
        "quote_reminders_enabled": bool(quote_reminders_enabled),
        "invoice_reminders_enabled": bool(invoice_reminders_enabled),
        "enabled_by": enabled_by if any_on else None,
        "enabled_at": now if any_on else None,
    }


def collect_due_followups(
    *,
    now: datetime,
    quotes: list[dict],
    invoices: list[dict],
    prefs_by_customer: dict[str, dict],
    quote_after_days: int = 3,
    invoice_after_days: int = 3,
) -> list[dict]:
    """Draft follow-ups. sendable is True only when the owner opted this client in."""
    drafts: list[dict] = []
    now = now if now.tzinfo else now.replace(tzinfo=timezone.utc)

    for quote in quotes:
        customer_id = str(quote.get("customer_id") or "")
        prefs = prefs_by_customer.get(customer_id) or default_followup_prefs(customer_id)
        sent_at = _parse_dt(quote.get("sent_at") or quote.get("created_at"))
        if not sent_at:
            continue
        if quote.get("status") in {"accepted", "approved", "cancelled", "in_production", "completed"}:
            continue
        age = (now - sent_at).days
        if age < quote_after_days:
            continue
        opted = bool(prefs.get("quote_reminders_enabled"))
        drafts.append({
            "kind": "quote_followup",
            "customer_id": customer_id,
            "document_id": quote.get("id"),
            "document_number": quote.get("quote_number"),
            "owner_opted_in": opted,
            "sendable": opted,
            "blocked_reason": None if opted else "owner_opt_in_required",
            "days_waiting": age,
        })

    for invoice in invoices:
        customer_id = str(invoice.get("customer_id") or "")
        prefs = prefs_by_customer.get(customer_id) or default_followup_prefs(customer_id)
        if invoice.get("status") in {"paid", "cancelled"}:
            continue
        due = _parse_dt(invoice.get("due_date") or invoice.get("sent_at") or invoice.get("created_at"))
        if not due:
            continue
        age = (now - due).days
        if age < invoice_after_days:
            continue
        opted = bool(prefs.get("invoice_reminders_enabled"))
        drafts.append({
            "kind": "invoice_followup",
            "customer_id": customer_id,
            "document_id": invoice.get("id"),
            "document_number": invoice.get("invoice_number"),
            "owner_opted_in": opted,
            "sendable": opted,
            "blocked_reason": None if opted else "owner_opt_in_required",
            "days_waiting": age,
        })
    return drafts


def dispatch_followups(
    drafts: list[dict],
    sender: Callable[[dict], dict] | None = None,
) -> dict:
    """Send only owner-opted-in drafts. Never auto-sends without opt-in."""
    sent: list[dict] = []
    blocked: list[dict] = []
    for draft in drafts:
        if not draft.get("owner_opted_in") or not draft.get("sendable"):
            blocked.append({**draft, "status": "blocked_no_opt_in"})
            continue
        if sender is None:
            blocked.append({**draft, "status": "blocked_no_sender"})
            continue
        result = sender(draft)
        sent.append({**draft, "status": "sent", "delivery": result})
    return {
        "sent_count": len(sent),
        "blocked_count": len(blocked),
        "sent": sent,
        "blocked": blocked,
    }


# ── Google review request (owner-approved) ──────────────────────────

def queue_review_request_after_paid(invoice: dict, *, review_url: str = "") -> dict:
    if invoice.get("status") != "paid" and not invoice.get("paid_at"):
        raise ValueError("Review request is only queued after an invoice is paid")
    return {
        "id": f"review-{uuid4().hex[:12]}",
        "customer_id": invoice.get("customer_id"),
        "invoice_id": invoice.get("id"),
        "invoice_number": invoice.get("invoice_number"),
        "status": "pending_owner_approval",
        "sendable": False,
        "review_url": review_url or DEFAULT_GOOGLE_REVIEW_URL,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "owner_approved_at": None,
        "owner_approved_by": None,
        "sent_at": None,
    }


def owner_approve_review_request(request: dict, *, approved_by: str = "owner") -> dict:
    updated = dict(request)
    updated["status"] = "owner_approved"
    updated["sendable"] = True
    updated["owner_approved_by"] = approved_by
    updated["owner_approved_at"] = datetime.now(timezone.utc).isoformat()
    return updated


def send_review_request(
    request: dict,
    sender: Callable[[dict], dict] | None = None,
) -> dict:
    if request.get("status") != "owner_approved" or not request.get("sendable"):
        return {
            "sent": False,
            "status": request.get("status") or "pending_owner_approval",
            "reason": "owner_approval_required",
        }
    if not request.get("review_url"):
        return {
            "sent": False,
            "status": "owner_approved",
            "reason": "review_url_not_configured",
        }
    if sender is None:
        return {
            "sent": False,
            "status": "owner_approved",
            "reason": "sender_not_configured",
        }
    delivery = sender(request)
    return {
        "sent": True,
        "status": "sent",
        "reason": None,
        "delivery": delivery,
    }


def _parse_dt(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        try:
            parsed = datetime.strptime(str(value)[:10], "%Y-%m-%d")
        except ValueError:
            return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


# ── Isolated fixture store (never the live DB) ──────────────────────

COMMERCE_SCHEMA = """
CREATE TABLE IF NOT EXISTS wqc_followup_prefs (
    customer_id TEXT PRIMARY KEY,
    quote_reminders_enabled INTEGER NOT NULL DEFAULT 0,
    invoice_reminders_enabled INTEGER NOT NULL DEFAULT 0,
    enabled_by TEXT,
    enabled_at TEXT,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS wqc_esignatures (
    id TEXT PRIMARY KEY,
    quote_id TEXT,
    signer_name TEXT NOT NULL,
    signature_data TEXT NOT NULL,
    consent_text TEXT,
    document_hash TEXT,
    signed_at TEXT,
    ip_address TEXT,
    user_agent TEXT
);
CREATE TABLE IF NOT EXISTS wqc_payment_links (
    id TEXT PRIMARY KEY,
    quote_id TEXT,
    invoice_id TEXT,
    stripe_payment_link_id TEXT,
    url TEXT,
    amount_cents INTEGER,
    kind TEXT,
    expires_at TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS wqc_review_requests (
    id TEXT PRIMARY KEY,
    customer_id TEXT,
    invoice_id TEXT,
    invoice_number TEXT,
    status TEXT NOT NULL DEFAULT 'pending_owner_approval',
    sendable INTEGER NOT NULL DEFAULT 0,
    review_url TEXT,
    created_at TEXT,
    owner_approved_at TEXT,
    owner_approved_by TEXT,
    sent_at TEXT
);
CREATE TABLE IF NOT EXISTS wqc_followup_log (
    id TEXT PRIMARY KEY,
    customer_id TEXT,
    kind TEXT,
    document_id TEXT,
    status TEXT,
    blocked_reason TEXT,
    created_at TEXT
);
"""


@dataclass
class FixtureStore:
    """SQLite store bound to a caller-supplied path. Tests pass tmp_path DBs."""

    db_path: str
    stripe_client: Any = None
    review_url: str = ""
    sender: Callable[[dict], dict] | None = None
    _mem_quotes: dict[str, dict] = field(default_factory=dict)
    _mem_invoices: dict[str, dict] = field(default_factory=dict)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.executescript(COMMERCE_SCHEMA)
        return conn

    def init(self) -> None:
        conn = self.connect()
        conn.commit()
        conn.close()

    def put_quote(self, quote: dict) -> dict:
        self._mem_quotes[str(quote["id"])] = apply_totals_to_quote(dict(quote))
        return self._mem_quotes[str(quote["id"])]

    def get_quote(self, quote_id: str) -> Optional[dict]:
        return self._mem_quotes.get(str(quote_id))

    def put_invoice(self, invoice: dict) -> dict:
        self._mem_invoices[str(invoice["id"])] = dict(invoice)
        return self._mem_invoices[str(invoice["id"])]

    def save_prefs(self, prefs: dict) -> dict:
        conn = self.connect()
        try:
            conn.execute(
                """
                INSERT INTO wqc_followup_prefs
                    (customer_id, quote_reminders_enabled, invoice_reminders_enabled,
                     enabled_by, enabled_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(customer_id) DO UPDATE SET
                    quote_reminders_enabled=excluded.quote_reminders_enabled,
                    invoice_reminders_enabled=excluded.invoice_reminders_enabled,
                    enabled_by=excluded.enabled_by,
                    enabled_at=excluded.enabled_at,
                    updated_at=excluded.updated_at
                """,
                (
                    prefs["customer_id"],
                    1 if prefs.get("quote_reminders_enabled") else 0,
                    1 if prefs.get("invoice_reminders_enabled") else 0,
                    prefs.get("enabled_by"),
                    prefs.get("enabled_at"),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return prefs

    def load_prefs(self, customer_id: str) -> dict:
        conn = self.connect()
        try:
            row = conn.execute(
                "SELECT * FROM wqc_followup_prefs WHERE customer_id = ?",
                (customer_id,),
            ).fetchone()
        finally:
            conn.close()
        if not row:
            return default_followup_prefs(customer_id)
        return {
            "customer_id": row["customer_id"],
            "quote_reminders_enabled": bool(row["quote_reminders_enabled"]),
            "invoice_reminders_enabled": bool(row["invoice_reminders_enabled"]),
            "enabled_by": row["enabled_by"],
            "enabled_at": row["enabled_at"],
        }

    def load_all_prefs(self) -> dict[str, dict]:
        conn = self.connect()
        try:
            rows = conn.execute("SELECT * FROM wqc_followup_prefs").fetchall()
        finally:
            conn.close()
        return {
            row["customer_id"]: {
                "customer_id": row["customer_id"],
                "quote_reminders_enabled": bool(row["quote_reminders_enabled"]),
                "invoice_reminders_enabled": bool(row["invoice_reminders_enabled"]),
                "enabled_by": row["enabled_by"],
                "enabled_at": row["enabled_at"],
            }
            for row in rows
        }

    def save_esignature(self, esign: dict) -> dict:
        conn = self.connect()
        try:
            conn.execute(
                """
                INSERT INTO wqc_esignatures
                    (id, quote_id, signer_name, signature_data, consent_text,
                     document_hash, signed_at, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    esign["id"], esign.get("quote_id"), esign["signer_name"],
                    esign["signature_data"], esign.get("consent_text"),
                    esign.get("document_hash"), esign.get("signed_at"),
                    esign.get("ip_address"), esign.get("user_agent"),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return esign

    def save_payment_link(self, quote_id: str, payment_link: dict, amount_cents: int) -> dict:
        conn = self.connect()
        record = {
            "id": f"plink-{uuid4().hex[:12]}",
            "quote_id": quote_id,
            "invoice_id": None,
            "stripe_payment_link_id": payment_link.get("id"),
            "url": payment_link.get("url"),
            "amount_cents": amount_cents,
            "kind": "deposit",
            "expires_at": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            conn.execute(
                """
                INSERT INTO wqc_payment_links
                    (id, quote_id, invoice_id, stripe_payment_link_id, url,
                     amount_cents, kind, expires_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["id"], record["quote_id"], record["invoice_id"],
                    record["stripe_payment_link_id"], record["url"],
                    record["amount_cents"], record["kind"], record["expires_at"],
                    record["created_at"],
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return record

    def save_review_request(self, request: dict) -> dict:
        conn = self.connect()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO wqc_review_requests
                    (id, customer_id, invoice_id, invoice_number, status, sendable,
                     review_url, created_at, owner_approved_at, owner_approved_by, sent_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request["id"], request.get("customer_id"), request.get("invoice_id"),
                    request.get("invoice_number"), request["status"],
                    1 if request.get("sendable") else 0, request.get("review_url"),
                    request.get("created_at"), request.get("owner_approved_at"),
                    request.get("owner_approved_by"), request.get("sent_at"),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return request

    def list_review_requests(self, status: Optional[str] = None) -> list[dict]:
        conn = self.connect()
        try:
            if status:
                rows = conn.execute(
                    "SELECT * FROM wqc_review_requests WHERE status = ? ORDER BY created_at DESC",
                    (status,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM wqc_review_requests ORDER BY created_at DESC"
                ).fetchall()
        finally:
            conn.close()
        return [dict(r) | {"sendable": bool(r["sendable"])} for r in rows]

    def get_review_request(self, request_id: str) -> Optional[dict]:
        conn = self.connect()
        try:
            row = conn.execute(
                "SELECT * FROM wqc_review_requests WHERE id = ?", (request_id,)
            ).fetchone()
        finally:
            conn.close()
        if not row:
            return None
        return dict(row) | {"sendable": bool(row["sendable"])}

    def run_due_followups(self, now: datetime) -> dict:
        prefs = self.load_all_prefs()
        drafts = collect_due_followups(
            now=now,
            quotes=list(self._mem_quotes.values()),
            invoices=list(self._mem_invoices.values()),
            prefs_by_customer=prefs,
        )
        result = dispatch_followups(drafts, sender=self.sender)
        conn = self.connect()
        try:
            for item in result["sent"] + result["blocked"]:
                conn.execute(
                    """
                    INSERT INTO wqc_followup_log
                        (id, customer_id, kind, document_id, status, blocked_reason, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"fulog-{uuid4().hex[:12]}",
                        item.get("customer_id"),
                        item.get("kind"),
                        item.get("document_id"),
                        item.get("status"),
                        item.get("blocked_reason"),
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
            conn.commit()
        finally:
            conn.close()
        return result

    def mark_invoice_paid(self, invoice_id: str, paid_at: Optional[str] = None) -> dict:
        invoice = self._mem_invoices.get(str(invoice_id))
        if not invoice:
            raise KeyError(f"invoice {invoice_id} not found in fixture store")
        invoice = dict(invoice)
        invoice["status"] = "paid"
        invoice["paid_at"] = paid_at or datetime.now(timezone.utc).isoformat()
        invoice["balance_due"] = 0
        self._mem_invoices[str(invoice_id)] = invoice
        request = queue_review_request_after_paid(invoice, review_url=self.review_url)
        self.save_review_request(request)
        return {"invoice": invoice, "review_request": request}
