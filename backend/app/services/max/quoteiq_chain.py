"""QuoteIQ-style multi-step tool chain for Max.

When a founder job request arrives (WhatsApp / chat), run these steps as
real tool calls, passing each result forward so the founder never
re-enters data:

  intake → dimension parse → Pricing Studio rates
  → (only if item + dims + a real catalog price)
  → CRM lookup/upsert → DRAFT quote

Trigger requires a request phrase (quote / estimate / cotización / price /
how much) AND an item AND at least one dimension. Bare "W x H" and casual
chat do not run the chain.

The result is always a DRAFT. Nothing is emailed or sent on WhatsApp to a
client. Measurements are shop fractions (26 3/4"), never decimals.

Channel cuts (current rule — the old "add 2 1/2\" / 12\" channel needs 18\""
add-on is gone):
  - Wood / board cut is true size with no add-ons.
  - Foam cut equals the wood cut.
  - Fabric cut is a separately labeled size.
  Leftover board after whole channels is reported, never silently dropped.

Fabric allowance table semantics (see fabric_cut_allowance.py):
  ``allowance_in`` is per side (Rafael 2026-10-14). Fabric = wood + 2 ×
  allowance. Table amounts stay confirm_with_rafael until signed off.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from app.config.fabric_cut_allowance import (
    CONFIRM_WITH_RAFAEL,
    NEEDS_FOAM_THICKNESS,
    fabric_dimension_in,
    lookup_fabric_allowance,
)
from app.config.workroom_billing import BILLED_BY_EMPIRE
from app.services.max.whatsapp_format import has_real_job_signals, is_link_or_article_message
from app.services.pricing.dimensions import plain_fractions
from app.services.vision.bench_cut_list import format_cut_inches
from app.services.voice_documents.extract import extract_transcript
from app.services.workroom_quote_commerce import parse_fraction_inches

logger = logging.getLogger("max.quoteiq_chain")

CHAIN_STEPS = (
    "quoteiq_intake",
    "quoteiq_parse_dimensions",
    "quoteiq_price",
    "quoteiq_crm_upsert",
    "quoteiq_draft_quote",
)

EMPIRE_WORKROOM_BRAND = "Empire Workroom"
DEDUPE_WINDOW_HOURS = 24
PLACEHOLDER_NAMES = frozenset({
    "customer", "client", "item", "unknown", "n/a", "na", "tbd", "none",
    "test", "user",
})

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(
    r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b"
)
_ADDRESS_RE = re.compile(
    r"\b(?:at|address)\s*:?\s+([0-9]{1,6}\s+[A-Za-z0-9 .#'\-]{4,60})",
    re.IGNORECASE,
)
_FRAC = r"(?:\d+\s+\d+\s*/\s*\d+|\d+\s*/\s*\d+|\d+(?:\.\d+)?)"
_WXH_RE = re.compile(
    rf"({_FRAC})\s*[xX×]\s*({_FRAC})",
)
_LABELED_DIM_RE = re.compile(
    rf"({_FRAC})\s*(?:inches|inch|in|\")\s*(?P<label>long|wide|length|width|deep|depth|high|tall|drop)",
    re.IGNORECASE,
)
_FOAM_RE = re.compile(
    rf"({_FRAC})\s*(?:inches|inch|in|\")\s*foam|foam\s*({_FRAC})",
    re.IGNORECASE,
)
_CHANNEL_WIDTH_RE = re.compile(
    rf"({_FRAC})\s*(?:inches|inch|in|\")\s*channels?",
    re.IGNORECASE,
)
_DECIMAL_INCH_RE = re.compile(r"\d+\.\d+\s*\"")
_REQUEST_PHRASE_RE = re.compile(
    r"\b("
    r"quote|quotes|quoted|quoting|"
    r"estimate|estimates|estimated|"
    r"cotizaci[oó]n|cotizar|cotizo|"
    r"presupuesto|"
    r"price|priced|pricing|"
    r"how\s+much|"
    r"cu[aá]nto(?:\s+cuesta|\s+vale)?"
    r")\b",
    re.IGNORECASE,
)
_DIM_HINT_RE = re.compile(
    rf"(?:"
    rf"{_FRAC}\s*[xX×]\s*{_FRAC}"
    rf"|{_FRAC}\s*(?:inches|inch|in\b|\")"
    rf")",
    re.IGNORECASE,
)

# SQLite last-10 phone compare without loading the table.
_PHONE_STRIP_SQL = (
    "replace(replace(replace(replace(replace(replace(replace("
    "coalesce(phone,''), '-', ''), ' ', ''), '(', ''), ')', ''),"
    "'+', ''), '.', ''), '/', '')"
)

_ITEM_TO_CATEGORY = {
    "drapery": "drapery",
    "roman_shade": "roman_shade",
    "throw_pillow": "pillow",
    "pillow": "pillow",
    "bench": "upholstery",
    "banquette": "upholstery",
    "seat_cushion": "cushions",
    "back_cushion": "cushions",
}

_CATALOG_CATEGORIES = frozenset({"drapery", "roman_shade"})


def _params(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    nested = raw.get("parameters")
    if isinstance(nested, dict):
        merged = {k: v for k, v in raw.items() if k != "parameters"}
        merged.update(nested)
        return merged
    return dict(raw)


def _text(params: dict[str, Any]) -> str:
    for key in ("message", "text", "transcript", "body"):
        value = params.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _channel(params: dict[str, Any]) -> str:
    return str(params.get("channel") or "chat").strip() or "chat"


def _as_fraction(value: Any) -> str:
    """Shop fraction with inch mark. Never a decimal inch string."""
    if value in (None, ""):
        return ""
    if isinstance(value, str):
        cleaned = plain_fractions(value.strip())
        if not cleaned:
            return ""
        if any(ch.isdigit() for ch in cleaned):
            inches = parse_fraction_inches(cleaned.replace('"', "").replace("in", "").strip())
            if inches:
                return format_cut_inches(inches)
        return cleaned
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    if number == 0:
        return ""
    return format_cut_inches(number)


def _inches(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value) if value else None
    parsed = parse_fraction_inches(str(value).replace('"', "").replace("in", "").strip())
    return parsed or None


def _email_from(text: str, params: dict[str, Any]) -> str:
    raw = str(params.get("email") or params.get("customer_email") or "").strip()
    if raw:
        return raw
    found = _EMAIL_RE.search(text or "")
    return found.group(0) if found else ""


def _phone_from(text: str, params: dict[str, Any]) -> str:
    raw = str(params.get("phone") or params.get("customer_phone") or "").strip()
    if raw:
        return raw
    found = _PHONE_RE.search(text or "")
    return found.group(0) if found else ""


def _address_from(text: str, params: dict[str, Any]) -> str:
    raw = str(params.get("address") or params.get("customer_address") or "").strip()
    if raw:
        return raw
    found = _ADDRESS_RE.search(text or "")
    return found.group(1).strip(" .,") if found else ""


def _phone_digits(phone: str) -> str:
    return re.sub(r"\D", "", phone or "")


def _last10(phone: str) -> str:
    digits = _phone_digits(phone)
    return digits[-10:] if len(digits) >= 10 else ""


def _is_real_name(name: str) -> bool:
    cleaned = (name or "").strip()
    if not cleaned or cleaned.lower() in PLACEHOLDER_NAMES:
        return False
    if "@" in cleaned:
        return False
    return any(ch.isalpha() for ch in cleaned)


def _item_label(intake: dict[str, Any]) -> str:
    return str(intake.get("item_name") or intake.get("item_type") or "").strip()


def looks_like_quote_request(message: str) -> bool:
    """Cheap regex prefilter: request phrase AND a dimension hint.

    Does not call extract_transcript. Bare 'W x H' or chat without a
    quote/estimate/price phrase returns False.
    """
    raw = (message or "").strip()
    if not raw:
        return False
    if not _REQUEST_PHRASE_RE.search(raw):
        return False
    if not _DIM_HINT_RE.search(raw):
        return False
    return True


def quoteiq_whatsapp_founder_phones() -> frozenset[str]:
    """WhatsApp QuoteIQ founder numbers only.

    Sources: WHATSAPP_FOUNDER_PHONES and business.json founder_phones /
    owner_phones. Not business_phone, not the phonebook, not is_allowlisted.
    """
    from app.services.max.whatsapp_channel import normalize_msisdn

    raw: list[str] = []
    env_phones = os.getenv("WHATSAPP_FOUNDER_PHONES") or ""
    if env_phones.strip():
        raw.extend(part.strip() for part in env_phones.split(",") if part.strip())
    path = Path(__file__).resolve().parents[2] / "config" / "business.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        data = {}
    for key in ("founder_phones", "owner_phones"):
        extra = data.get(key) or []
        if isinstance(extra, str):
            extra = [extra]
        if isinstance(extra, dict):
            extra = list(extra.values())
        if isinstance(extra, list):
            for item in extra:
                if isinstance(item, dict):
                    raw.append(str(item.get("phone") or item.get("number") or item.get("wa_id") or ""))
                else:
                    raw.append(str(item))
    return frozenset(n for n in (normalize_msisdn(item) for item in raw if str(item).strip()) if n)


def is_quoteiq_whatsapp_founder(wa_id: str | None) -> bool:
    from app.services.max.whatsapp_channel import normalize_msisdn

    number = normalize_msisdn(wa_id)
    if not number:
        return False
    allowed = quoteiq_whatsapp_founder_phones()
    if number in allowed:
        return True
    tail = number[-10:]
    return bool(tail) and any(item.endswith(tail) and len(tail) == 10 for item in allowed)


def quoteiq_founder_allowed(
    *,
    founder: Optional[bool] = None,
    **_ignored: Any,
) -> bool:
    """Fail closed unless the caller passed founder=True.

    Chat/stream must pass founder_session.current_verified() after
    resolve_founder_session is applied. WhatsApp must pass the
    founder-phones check. Body channel strings are never enough.
    """
    return founder is True


def should_run_quoteiq_chain(
    message: str,
    *,
    desk: Optional[str] = None,
    has_image: bool = False,
) -> bool:
    """True when inbound text is a founder job request, not casual chat."""
    if desk or has_image:
        return False
    raw = (message or "").strip()
    if not raw or is_link_or_article_message(raw):
        return False
    if not looks_like_quote_request(raw):
        return False
    try:
        from app.services.max.quick_replies import is_greeting, parse_quote_lookup

        if is_greeting(raw):
            return False
        if parse_quote_lookup(raw):
            return False
    except Exception:
        pass
    probe = extract_transcript(raw)
    if not has_real_job_signals(raw, probe):
        return False
    item = probe.items[0] if probe.items else None
    has_item = bool(item and (item.item_type or item.name))
    has_dims = bool(
        item
        and any(
            getattr(item, key, None)
            for key in ("width_in", "depth_in", "seat_height_in", "back_height_in")
        )
    )
    if _WXH_RE.search(raw) or _LABELED_DIM_RE.search(raw):
        has_dims = True
    return bool(has_item and has_dims)


def intake_job_request(params: dict[str, Any]) -> dict[str, Any]:
    """Step 1 — parse the inbound job request. Reuses voice extract + job signals."""
    params = _params(params)
    text = _text(params)
    channel = _channel(params)
    if not text:
        return {
            "ok": False,
            "error": "message is required",
            "channel": channel,
            "is_job_request": False,
        }
    probe = extract_transcript(text)
    item = probe.items[0] if probe.items else None
    is_job = has_real_job_signals(text, probe) and not is_link_or_article_message(text)
    labeled = {m.group("label").lower(): parse_fraction_inches(m.group(1)) for m in _LABELED_DIM_RE.finditer(text)}
    width = _inches(labeled.get("wide") or labeled.get("width") or labeled.get("long") or labeled.get("length"))
    height = _inches(labeled.get("high") or labeled.get("tall") or labeled.get("drop"))
    depth = _inches(labeled.get("deep") or labeled.get("depth"))
    if width is None:
        width = _inches(item.width_in if item else None)
    if height is None:
        height = _inches(item.back_height_in if item else None)
    if depth is None:
        depth = _inches(item.depth_in if item else None)
    pair = _WXH_RE.search(text)
    if pair:
        first = parse_fraction_inches(pair.group(1))
        second = parse_fraction_inches(pair.group(2))
        item_type_hint = (item.item_type if item else "") or ""
        if item_type_hint in ("drapery", "roman_shade"):
            width = width or first
            height = height or second
        else:
            width = width or first
            depth = depth or second
    foam = None
    foam_match = _FOAM_RE.search(text)
    if foam_match:
        foam = parse_fraction_inches(foam_match.group(1) or foam_match.group(2))
    if foam is None:
        foam = _inches(item.seat_cushion_thickness if item else None)
    channel_width = None
    ch_match = _CHANNEL_WIDTH_RE.search(text)
    if ch_match:
        channel_width = parse_fraction_inches(ch_match.group(1))
    raw_name = (params.get("customer_name") or params.get("client_name") or probe.client_name or "").strip()
    client = raw_name if _is_real_name(raw_name) else ""
    email = _email_from(text, params)
    phone = _phone_from(text, params)
    address = _address_from(text, params)
    item_type = (item.item_type if item else "") or ""
    item_name = (item.name if item else "") or ""
    return {
        "ok": True,
        "is_job_request": is_job,
        "channel": channel,
        "message": text,
        "client_name": client,
        "customer_name": client,
        "customer_email": email,
        "customer_phone": phone,
        "customer_address": address,
        "item_type": item_type,
        "item_name": item_name,
        "panel_style": (item.panel_style if item else "") or "",
        "shape": (item.shape if item else "") or "",
        "seat_sections": item.seat_sections if item else None,
        "back_sections": item.back_sections if item else None,
        "foam_thickness_in": foam,
        "channel_width_in": channel_width,
        "width_in": width,
        "height_in": height,
        "depth_in": depth,
        "seat_height_in": item.seat_height_in if item else None,
        "business_unit": (params.get("business_unit") or "workroom").strip() or "workroom",
        "document_kind": probe.document_kind,
        "ask_founder": False,
        "note": "Parsed from the inbound message. Do not ask the founder to re-enter these fields.",
    }


def _find_customer(conn, *, email: str, phone: str) -> Optional[dict]:
    """Match only on email or last-10 phone digits. SQL filter, never name-only."""
    if email:
        row = conn.execute(
            """SELECT * FROM customers
               WHERE email IS NOT NULL AND trim(email) != ''
                 AND lower(trim(email)) = lower(?)
               ORDER BY updated_at DESC LIMIT 1""",
            (email.strip(),),
        ).fetchone()
        if row:
            return dict(row)
    last10 = _last10(phone)
    if last10:
        row = conn.execute(
            f"""SELECT * FROM customers
                WHERE phone IS NOT NULL AND trim(phone) != ''
                  AND length({_PHONE_STRIP_SQL}) >= 10
                  AND substr({_PHONE_STRIP_SQL}, -10) = ?
                ORDER BY updated_at DESC LIMIT 1""",
            (last10,),
        ).fetchone()
        if row:
            return dict(row)
    return None


def _field_mismatch(field: str, existing: str, incoming: str) -> str:
    return f"{field} mismatch: kept {existing!r}, inbound {incoming!r}"


def _same_phone(a: str, b: str) -> bool:
    left, right = _last10(a), _last10(b)
    if left and right:
        return left == right
    return _phone_digits(a) == _phone_digits(b)


def lookup_or_upsert_client(params: dict[str, Any]) -> dict[str, Any]:
    """CRM lookup/upsert: email or last-10 phone only. Fill empty fields, never overwrite."""
    params = _params(params)
    intake = params.get("intake") if isinstance(params.get("intake"), dict) else params
    name = (intake.get("customer_name") or intake.get("client_name") or intake.get("name") or "").strip()
    email = (intake.get("customer_email") or intake.get("email") or "").strip()
    phone = (intake.get("customer_phone") or intake.get("phone") or "").strip()
    address = (intake.get("customer_address") or intake.get("address") or "").strip()
    business = (intake.get("business_unit") or "workroom").strip() or "workroom"
    skipped = {
        "ok": True,
        "upsert_outcome": "skipped",
        "customer": None,
        "customer_id": None,
        "customer_name": name if _is_real_name(name) else "",
        "customer_email": email,
        "customer_phone": phone,
        "customer_address": address,
        "mismatches": [],
    }
    if not email and not _last10(phone):
        skipped["reason"] = "CRM match requires email or last-10 phone digits"
        return skipped
    return _upsert_customer_direct(
        name=name, email=email, phone=phone, address=address, business=business, channel=_channel(intake),
    )


def _upsert_customer_direct(
    *,
    name: str,
    email: str,
    phone: str,
    address: str,
    business: str,
    channel: str,
) -> dict[str, Any]:
    """ForgeCRM customers table: SQL email/last-10 match, fill-empty only."""
    from app.db.database import get_db

    now = datetime.now(timezone.utc).isoformat()
    mismatches: list[str] = []
    with get_db() as conn:
        existing = _find_customer(conn, email=email, phone=phone)
        if existing:
            updates: dict[str, str] = {}
            for field, incoming, same in (
                ("email", email, lambda a, b: a.lower() == b.lower()),
                ("phone", phone, _same_phone),
                ("address", address, lambda a, b: a.strip().lower() == b.strip().lower()),
                ("name", name if _is_real_name(name) else "", lambda a, b: a.strip().lower() == b.strip().lower()),
            ):
                old = str(existing.get(field) or "").strip()
                incoming = (incoming or "").strip()
                if not incoming:
                    continue
                if not old:
                    updates[field] = incoming
                elif not same(old, incoming):
                    mismatches.append(_field_mismatch(field, old, incoming))
            if updates:
                sets = ", ".join(f"{col} = ?" for col in updates)
                conn.execute(
                    f"UPDATE customers SET {sets}, updated_at = ? WHERE id = ?",
                    (*updates.values(), now, existing["id"]),
                )
            row = conn.execute("SELECT * FROM customers WHERE id = ?", (existing["id"],)).fetchone()
            outcome = "matched"
        else:
            if not _is_real_name(name):
                return {
                    "ok": True,
                    "upsert_outcome": "skipped",
                    "reason": "no customer without a real name",
                    "customer": None,
                    "customer_id": None,
                    "customer_name": "",
                    "customer_email": email,
                    "customer_phone": phone,
                    "customer_address": address,
                    "mismatches": [],
                }
            cid = uuid.uuid4().hex[:12]
            conn.execute(
                """INSERT INTO customers
                   (id, name, email, phone, address, type, source, business, notes, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 'residential', ?, ?, 'QuoteIQ job-request chain', ?, ?)""",
                (cid, name, email or None, phone or None, address or None,
                 f"quoteiq_{channel}", business, now, now),
            )
            row = conn.execute("SELECT * FROM customers WHERE id = ?", (cid,)).fetchone()
            outcome = "created"
        customer = dict(row)
    real = customer.get("name") or ""
    if not _is_real_name(real):
        real = name if _is_real_name(name) else ""
    return {
        "ok": True,
        "upsert_outcome": outcome,
        "customer_id": customer.get("id"),
        "customer": {
            "id": customer.get("id"),
            "name": customer.get("name"),
            "email": customer.get("email"),
            "phone": customer.get("phone"),
            "address": customer.get("address"),
            "business": customer.get("business"),
        },
        "customer_name": real,
        "customer_email": customer.get("email") or email,
        "customer_phone": customer.get("phone") or phone,
        "customer_address": customer.get("address") or address,
        "business_unit": customer.get("business") or business,
        "mismatches": mismatches,
        "ask_founder": False,
    }


def _drawing_dims(text: str, item_type: str) -> dict[str, str]:
    try:
        from app.services.max.drawing_intent import _extract_dimensions

        raw = _extract_dimensions(text, item_type=item_type or None)
    except Exception:
        raw = {}
    out: dict[str, str] = {}
    for key, value in (raw or {}).items():
        inches = _inches(str(value).replace("ft", "").replace("'", ""))
        if str(value).endswith("ft") or str(value).endswith("'"):
            try:
                inches = float(re.sub(r"[^\d.]", "", str(value)) or 0) * 12.0
            except ValueError:
                inches = _inches(value)
        frac = _as_fraction(inches if inches is not None else value)
        if frac:
            out[key] = frac
    return out


def _channel_cuts(intake: dict[str, Any], dims: dict[str, str]) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Wood/foam = true size, fabric labeled separately. Leftover board is reported."""
    style = str(intake.get("panel_style") or "")
    sections = intake.get("seat_sections") or intake.get("back_sections")
    text = str(intake.get("message") or "")
    channel_width = _inches(intake.get("channel_width_in"))
    if "channel" not in style and not sections and not channel_width and "channel" not in text.lower():
        return [], {}
    width = _inches(intake.get("width_in")) or _inches(dims.get("width"))
    height = (
        _inches(intake.get("height_in"))
        or _inches(intake.get("back_height_in"))
        or _inches(dims.get("height"))
        or _inches(dims.get("back height"))
    )
    ch_h = height or _inches(intake.get("depth_in")) or _inches(dims.get("depth")) or width
    remainder_in = 0.0
    remainder_note = ""
    if channel_width and width and width + 1e-9 >= channel_width:
        ch_w = channel_width
        count = max(1, int(width // channel_width))
        remainder_in = round(width - (count * channel_width), 4)
        if remainder_in > 1e-6:
            remainder_note = (
                f"{_as_fraction(remainder_in)} leftover after {count} × {_as_fraction(channel_width)} "
                "channels — do not drop."
            )
    elif channel_width and width and width < channel_width:
        count = 1
        ch_w = width
        remainder_note = (
            f"board {_as_fraction(width)} is narrower than channel {_as_fraction(channel_width)} "
            "— one channel at true board size."
        )
    elif width and sections:
        count = int(sections)
        ch_w = width / count
    elif width and "channel" in text.lower():
        count = 1
        ch_w = width
    else:
        return [], {}
    if not ch_w:
        return [], {}
    foam_th = _inches(intake.get("foam_thickness_in"))
    allowance = lookup_fabric_allowance(foam_th)
    extra = allowance.get("allowance_in")
    status = allowance.get("status")
    wood = f"{_as_fraction(ch_w)} x {_as_fraction(ch_h)}"
    foam = wood
    if extra is None:
        fabric = NEEDS_FOAM_THICKNESS
    else:
        # allowance_in is per side (Rafael 2026-10-14): fabric = wood + 2 × allowance.
        fabric = (
            f"{_as_fraction(fabric_dimension_in(ch_w, extra))} x "
            f"{_as_fraction(fabric_dimension_in(ch_h, extra))}"
        )
        if status == CONFIRM_WITH_RAFAEL:
            fabric = f"{fabric} (allowance unconfirmed)"
    cuts = []
    for idx in range(count):
        cuts.append({
            "channel": f"Ch {idx + 1}",
            "wood_cut": wood,
            "foam_cut": foam,
            "fabric_cut": fabric,
            "allowance_status": status,
        })
    meta = {
        "channel_count": count,
        "channel_width": _as_fraction(ch_w),
        "channel_remainder": _as_fraction(remainder_in) if remainder_in > 1e-6 else "",
        "channel_remainder_note": remainder_note,
        "allowance_in": extra,
        "allowance_status": status,
        "allowance_semantics": (
            "allowance_in is per side (Rafael 2026-10-14): fabric = wood + 2 × allowance. "
            "Table amounts stay confirm_with_rafael until signed off. "
            "Row status is surfaced; confirm_with_rafael is labeled unconfirmed."
        ),
    }
    return cuts, meta


def parse_job_dimensions(params: dict[str, Any]) -> dict[str, Any]:
    """Step 2 — dimensions as fractions; channel wood/foam vs fabric separately."""
    params = _params(params)
    intake = params.get("intake") if isinstance(params.get("intake"), dict) else params
    text = _text(intake) or _text(params)
    item_type = str(intake.get("item_type") or "")
    labeled = _drawing_dims(text, item_type)
    width = _as_fraction(intake.get("width_in") or labeled.get("width"))
    height = _as_fraction(intake.get("height_in") or labeled.get("height") or labeled.get("drop"))
    depth = _as_fraction(intake.get("depth_in") or labeled.get("depth"))
    seat_h = _as_fraction(intake.get("seat_height_in") or labeled.get("seat height"))
    back_h = _as_fraction(intake.get("back_height_in") or labeled.get("back height") or height)
    dimensions = {k: v for k, v in labeled.items() if v}
    if width:
        dimensions["width"] = width
    if height:
        dimensions["height"] = height
    if depth:
        dimensions["depth"] = depth
    if seat_h:
        dimensions["seat_height"] = seat_h
    if back_h:
        dimensions["back_height"] = back_h
    channels, channel_meta = _channel_cuts(intake, dimensions)
    blob = " ".join([*dimensions.values(), *(c["wood_cut"] + c["foam_cut"] + c["fabric_cut"] for c in channels)])
    if _DECIMAL_INCH_RE.search(blob):
        raise ValueError("QuoteIQ dimensions leaked a decimal inch")
    return {
        "ok": True,
        "dimensions": dimensions,
        "width": width,
        "height": height,
        "depth": depth,
        "seat_height": seat_h,
        "back_height": back_h,
        "channel_cuts": channels,
        "channel_remainder": channel_meta.get("channel_remainder") or "",
        "channel_remainder_note": channel_meta.get("channel_remainder_note") or "",
        "allowance_status": channel_meta.get("allowance_status"),
        "channel_rules": [
            "Wood / board cut is true size with no add-ons.",
            "Foam cut equals the wood cut.",
            "Fabric cut is labeled separately. Allowance depends on foam thickness.",
            "allowance_in is per side (Rafael 2026-10-14): fabric = wood + 2 × allowance.",
            "Leftover board after whole channels is reported — never silently dropped.",
            "Never add 2 1/2\" or treat a 12\" channel as needing 18\".",
        ],
        "allowance_semantics": channel_meta.get("allowance_semantics") or (
            "allowance_in is per side (Rafael 2026-10-14): fabric = wood + 2 × allowance."
        ),
        "measurements_format": "fractions",
        "ask_founder": False,
    }


def _catalog_inputs(item_type: str, intake: dict[str, Any], dims: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    width = _inches(intake.get("width_in")) or _inches(dims.get("width"))
    height = _inches(intake.get("height_in")) or _inches(dims.get("height"))
    depth = _inches(intake.get("depth_in")) or _inches(dims.get("depth"))
    category = _ITEM_TO_CATEGORY.get(item_type, "")
    if item_type == "drapery" and width and (height or _inches(dims.get("drop"))):
        return "drapery", {
            "window_width_in": width,
            "length_in": height or _inches(dims.get("drop")),
        }
    if item_type == "roman_shade" and width and height:
        return "roman_shade", {"width_in": width, "height_in": height}
    if item_type in ("throw_pillow", "pillow"):
        return "", {}
    return category, {
        k: v
        for k, v in {
            "width_in": width,
            "height_in": height,
            "depth_in": depth,
        }.items()
        if v
    }


def _has_dimension(intake: dict[str, Any], dims: dict[str, Any]) -> bool:
    for key in ("width", "height", "depth", "seat_height", "back_height"):
        if dims.get(key) or _inches(intake.get(f"{key}_in") or intake.get(key)):
            return True
    return False


def _draft_ready(intake: dict[str, Any], dims: dict[str, Any], pricing: dict[str, Any]) -> list[str]:
    """Missing pieces before a draft may be created. Empty list = ready."""
    missing: list[str] = []
    if not _item_label(intake):
        missing.append("item")
    if not _has_dimension(intake, dims):
        missing.append("dimensions")
    if not pricing.get("has_real_price"):
        missing.append("a Pricing Studio price")
    return missing


def price_with_studio(params: dict[str, Any]) -> dict[str, Any]:
    """Step 3 — real Pricing Studio catalog price only. No invented lines."""
    params = _params(params)
    intake = params.get("intake") if isinstance(params.get("intake"), dict) else params
    dims = params.get("dimensions") if isinstance(params.get("dimensions"), dict) else {}
    if not dims and isinstance(params.get("parse"), dict):
        dims = params["parse"].get("dimensions") or params["parse"]
    business = (intake.get("business_unit") or params.get("business_unit") or "workroom").strip() or "workroom"
    item_type = str(intake.get("item_type") or "")
    category, inputs = _catalog_inputs(item_type, intake, dims)
    priced = None
    error = None
    line: dict[str, Any] = {}
    if category in _CATALOG_CATEGORIES and inputs:
        try:
            from app.services.pricing.engine import price_workroom_line

            priced = price_workroom_line(category, inputs, business_unit=business)
            amount = priced.get("proposed_price")
            if amount is None:
                priced = None
            else:
                line = {
                    "category": category,
                    "description": _line_description(intake, dims),
                    "quantity": 1,
                    "inputs": dict(inputs),
                    "rate_source": "pricing_studio",
                    "proposed_price": amount,
                }
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            priced = None
    has_real = bool(priced and line.get("proposed_price") is not None)
    return {
        "ok": True,
        "engine": "pricing_studio",
        "business_unit": business,
        "has_real_price": has_real,
        "studio_rates": {},
        "line_items": [line] if has_real else [],
        "priced": {
            "final_price": (priced or {}).get("final_price") or (priced or {}).get("proposed_price"),
            "proposed_price": (priced or {}).get("proposed_price"),
            "product_category": (priced or {}).get("product_category"),
            "rate_table_version": (priced or {}).get("rate_table_version"),
        } if has_real else None,
        "pricing_error": error,
        "need": None if has_real else "a Pricing Studio price",
        "ask_founder": False,
    }


def _line_description(intake: dict[str, Any], dims: dict[str, Any]) -> str:
    name = _item_label(intake)
    parts = []
    for key in ("width", "height", "depth", "seat_height", "back_height"):
        value = dims.get(key) or _as_fraction(intake.get(f"{key}_in") or intake.get(key))
        if value:
            parts.append(f"{value} {key.replace('_', ' ')}")
    if name and parts:
        return f"{name}\n" + " · ".join(parts)
    return name


def _norm_blob(*parts: str) -> str:
    return " ".join(" ".join(p or "" for p in parts).lower().split())


def _fingerprint(message: str, customer: str, item: str) -> str:
    blob = _norm_blob(message, customer, item)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]


def _parse_created(raw: Any) -> Optional[datetime]:
    if not raw:
        return None
    text = str(raw).strip()
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _find_recent_draft(fp: str) -> Optional[dict[str, Any]]:
    from app.db.database import get_db

    cutoff = datetime.now(timezone.utc) - timedelta(hours=DEDUPE_WINDOW_HOURS)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, quote_number, customer_name, notes, created_at, status, billed_by, total, subtotal
               FROM quotes_v2
               WHERE status = 'draft' AND notes LIKE ?
               ORDER BY created_at DESC""",
            (f"%quoteiq_fp:{fp}%",),
        ).fetchall()
    for row in rows:
        created = _parse_created(row["created_at"] if not isinstance(row, dict) else row.get("created_at"))
        if created is None or created >= cutoff:
            data = dict(row)
            return data
    return None


def _set_empire_brand(quote_id: str) -> None:
    from app.db.database import get_db
    from app.config.workroom_billing import ensure_billed_by_schema

    try:
        with get_db() as conn:
            ensure_billed_by_schema(conn)
            conn.execute(
                "UPDATE quotes_v2 SET billed_by = ? WHERE id = ?",
                (BILLED_BY_EMPIRE, quote_id),
            )
    except Exception:
        logger.debug("QuoteIQ billed_by brand write skipped", exc_info=True)


def draft_quote_only(params: dict[str, Any]) -> dict[str, Any]:
    """Step 5 — persist a DRAFT via quote_service.create_quote. Never send.

    Requires item + dims + a real Pricing Studio price. No invented lines,
    no labor_rate placeholder, no 'Customer'/'Item' names.
    """
    params = _params(params)
    intake = params.get("intake") if isinstance(params.get("intake"), dict) else params
    client = params.get("client") if isinstance(params.get("client"), dict) else {}
    dims = params.get("dimensions") if isinstance(params.get("dimensions"), dict) else {}
    if not dims and isinstance(params.get("parse"), dict):
        dims = params["parse"].get("dimensions") or {}
    pricing = params.get("pricing") if isinstance(params.get("pricing"), dict) else {}
    missing = _draft_ready(intake, dims, pricing)
    if missing:
        need = ", ".join(missing)
        return {
            "ok": True,
            "created": False,
            "sent": False,
            "status": "incomplete",
            "need": need,
            "reply_text": f"need {need}",
            "quote_id": None,
            "notice": f"need {need}. Nothing created.",
        }
    raw_name = (
        client.get("customer_name")
        or intake.get("customer_name")
        or client.get("name")
        or ""
    )
    name = raw_name if _is_real_name(str(raw_name)) else ""
    item = _item_label(intake)
    message = str(intake.get("message") or params.get("message") or "")
    fp = _fingerprint(message, name or str(client.get("customer_email") or intake.get("customer_email") or ""), item)
    existing = _find_recent_draft(fp)
    if existing:
        return {
            "ok": True,
            "created": False,
            "deduped": True,
            "sent": False,
            "status": "draft",
            "store": "quotes_v2",
            "quote_id": existing.get("id"),
            "quote_number": existing.get("quote_number"),
            "customer_name": existing.get("customer_name") or name,
            "customer_id": client.get("customer_id"),
            "total": existing.get("total"),
            "subtotal": existing.get("subtotal"),
            "billed_by": existing.get("billed_by") or BILLED_BY_EMPIRE,
            "brand": EMPIRE_WORKROOM_BRAND,
            "channel_cuts": params.get("channel_cuts")
            or (params.get("parse") or {}).get("channel_cuts")
            or [],
            "notice": "Existing DRAFT within 24h. Not sent.",
            "ask_founder": False,
        }
    lines = [row for row in (pricing.get("line_items") or params.get("line_items") or []) if row]
    if not lines:
        return {
            "ok": True,
            "created": False,
            "sent": False,
            "status": "incomplete",
            "need": "a Pricing Studio price",
            "reply_text": "need a Pricing Studio price",
            "quote_id": None,
        }
    notes = (
        f"quoteiq chain draft — not sent. Brand: {EMPIRE_WORKROOM_BRAND}. "
        f"quoteiq_fp:{fp}"
    )
    mismatches = client.get("mismatches") or []
    if mismatches:
        notes += " CRM: " + "; ".join(mismatches)
    body = {
        "customer_name": name,
        "customer_email": client.get("customer_email") or intake.get("customer_email") or "",
        "customer_phone": client.get("customer_phone") or intake.get("customer_phone") or "",
        "customer_address": client.get("customer_address") or intake.get("customer_address") or "",
        "business_unit": intake.get("business_unit") or "workroom",
        "billed_by": BILLED_BY_EMPIRE,
        "project_name": item,
        "project_description": message,
        "notes": notes,
        "line_items": lines,
        "measurements": {
            "format": "fractions",
            "brand": EMPIRE_WORKROOM_BRAND,
            "billed_by": BILLED_BY_EMPIRE,
            "dimensions": dims,
            "channel_cuts": params.get("channel_cuts")
            or (params.get("parse") or {}).get("channel_cuts")
            or [],
        },
    }
    from app.services.quote_service import create_quote

    quote = create_quote(body)
    status = str(quote.get("status") or "draft").lower()
    if status != "draft":
        raise RuntimeError(f"QuoteIQ must persist draft only, got {status!r}")
    quote_id = quote.get("id")
    if quote_id:
        _set_empire_brand(str(quote_id))
    return {
        "ok": True,
        "created": True,
        "deduped": False,
        "sent": False,
        "status": "draft",
        "store": "quotes_v2",
        "quote_id": quote_id,
        "quote_number": quote.get("quote_number"),
        "customer_name": quote.get("customer_name") or name,
        "customer_id": client.get("customer_id"),
        "total": quote.get("total"),
        "subtotal": quote.get("subtotal"),
        "line_items": quote.get("line_items") or [],
        "channel_cuts": body["measurements"]["channel_cuts"],
        "billed_by": BILLED_BY_EMPIRE,
        "brand": EMPIRE_WORKROOM_BRAND,
        "notice": "DRAFT only. Not sent to the client. Not emailed. Not WhatsApped.",
        "ask_founder": False,
    }


def _step_payload(name: str, ctx: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "tool": name,
        "message": ctx.get("message"),
        "channel": ctx.get("channel") or "chat",
        "intake": ctx.get("intake") or ctx,
        "client": ctx.get("client"),
        "parse": ctx.get("parse"),
        "dimensions": (ctx.get("parse") or {}).get("dimensions") if isinstance(ctx.get("parse"), dict) else ctx.get("dimensions"),
        "channel_cuts": (ctx.get("parse") or {}).get("channel_cuts") if isinstance(ctx.get("parse"), dict) else ctx.get("channel_cuts"),
        "pricing": ctx.get("pricing"),
        "line_items": (ctx.get("pricing") or {}).get("line_items") if isinstance(ctx.get("pricing"), dict) else None,
        "customer_name": ctx.get("customer_name"),
        "customer_email": ctx.get("customer_email"),
        "customer_phone": ctx.get("customer_phone"),
        "business_unit": ctx.get("business_unit") or "workroom",
    }
    return {k: v for k, v in payload.items() if v not in (None, "")}


def run_quoteiq_chain(params: dict[str, Any]) -> dict[str, Any]:
    """Run the chain. CRM + draft run only after item+dims+real price."""
    params = _params(params)
    text = _text(params)
    channel = _channel(params)
    if not text:
        return {
            "ok": False,
            "handled": False,
            "sent": False,
            "error": "message is required",
            "steps": [],
        }
    runners = {
        "quoteiq_intake": intake_job_request,
        "quoteiq_crm_upsert": lookup_or_upsert_client,
        "quoteiq_parse_dimensions": parse_job_dimensions,
        "quoteiq_price": price_with_studio,
        "quoteiq_draft_quote": draft_quote_only,
    }
    ctx: dict[str, Any] = {
        "message": text,
        "channel": channel,
        "business_unit": params.get("business_unit") or "workroom",
        "customer_name": params.get("customer_name"),
        "customer_email": params.get("customer_email"),
        "customer_phone": params.get("customer_phone"),
        "customer_address": params.get("customer_address"),
    }
    steps: list[dict[str, Any]] = []
    mapping = {
        "quoteiq_intake": "intake",
        "quoteiq_crm_upsert": "client",
        "quoteiq_parse_dimensions": "parse",
        "quoteiq_price": "pricing",
        "quoteiq_draft_quote": "quote",
    }

    def _run_step(name: str) -> dict[str, Any]:
        payload = runners[name](_step_payload(name, ctx))
        ok = bool(payload.get("ok", True))
        entry = {
            "tool": name,
            "success": ok,
            "result": payload if ok else None,
            "error": None if ok else payload.get("error") or f"{name} failed",
        }
        steps.append(entry)
        if ok:
            ctx[mapping[name]] = payload
            for key in (
                "customer_name",
                "customer_email",
                "customer_phone",
                "customer_address",
                "customer_id",
                "business_unit",
                "item_type",
                "item_name",
                "width_in",
                "height_in",
                "depth_in",
            ):
                if payload.get(key) not in (None, ""):
                    ctx[key] = payload[key]
        return entry

    for name in ("quoteiq_intake", "quoteiq_parse_dimensions", "quoteiq_price"):
        entry = _run_step(name)
        if not entry["success"]:
            return {
                "ok": False,
                "handled": True,
                "sent": False,
                "created": False,
                "status": "blocked",
                "error": entry.get("error") or f"{name} failed",
                "steps": steps,
                "tool_results": steps,
                "reply_text": _founder_reply({"ok": False, "error": entry.get("error"), "steps": steps}),
            }

    intake = ctx.get("intake") or {}
    parse = ctx.get("parse") or {}
    pricing = ctx.get("pricing") or {}
    dims = parse.get("dimensions") or {}
    missing = _draft_ready(intake, dims, pricing)
    if missing:
        need = ", ".join(missing)
        reply = {
            "ok": True,
            "handled": True,
            "sent": False,
            "created": False,
            "status": "incomplete",
            "need": need,
            "quote_id": None,
            "steps": steps,
            "tool_results": steps,
            "dimensions": dims,
            "channel_cuts": parse.get("channel_cuts") or [],
            "channel_remainder": parse.get("channel_remainder") or "",
            "notice": f"need {need}. Nothing created.",
            "ask_founder": False,
        }
        reply["reply_text"] = f"need {need}"
        return reply

    for name in ("quoteiq_crm_upsert", "quoteiq_draft_quote"):
        entry = _run_step(name)
        if not entry["success"]:
            return {
                "ok": False,
                "handled": True,
                "sent": False,
                "created": False,
                "status": "blocked",
                "error": entry.get("error") or f"{name} failed",
                "steps": steps,
                "tool_results": steps,
                "reply_text": _founder_reply({"ok": False, "error": entry.get("error"), "steps": steps}),
            }

    quote = ctx.get("quote") or {}
    if quote.get("status") == "incomplete" or not quote.get("quote_id"):
        need = quote.get("need") or "item"
        return {
            "ok": True,
            "handled": True,
            "sent": False,
            "created": False,
            "status": "incomplete",
            "need": need,
            "quote_id": None,
            "steps": steps,
            "tool_results": steps,
            "reply_text": f"need {need}",
            "ask_founder": False,
        }
    reply = {
        "ok": True,
        "handled": True,
        "sent": False,
        "created": bool(quote.get("created")),
        "deduped": bool(quote.get("deduped")),
        "status": "draft",
        "quote_id": quote.get("quote_id"),
        "quote_number": quote.get("quote_number"),
        "customer_name": quote.get("customer_name") or ctx.get("customer_name"),
        "customer_id": ctx.get("customer_id"),
        "total": quote.get("total"),
        "channel_cuts": (ctx.get("parse") or {}).get("channel_cuts") or [],
        "channel_remainder": (ctx.get("parse") or {}).get("channel_remainder") or "",
        "channel_remainder_note": (ctx.get("parse") or {}).get("channel_remainder_note") or "",
        "dimensions": (ctx.get("parse") or {}).get("dimensions") or {},
        "studio_rates": (ctx.get("pricing") or {}).get("studio_rates") or {},
        "billed_by": quote.get("billed_by") or BILLED_BY_EMPIRE,
        "brand": EMPIRE_WORKROOM_BRAND,
        "steps": steps,
        "tool_results": steps,
        "notice": "DRAFT only. Not sent to the client.",
        "ask_founder": False,
    }
    reply["reply_text"] = _founder_reply(reply)
    return reply


def _founder_reply(result: dict[str, Any]) -> str:
    if result.get("status") == "incomplete" or result.get("need"):
        return f"need {result.get('need')}"
    if not result.get("ok"):
        err = result.get("error") or "chain stopped"
        return f"QuoteIQ chain stopped: {err}. Nothing sent."
    number = result.get("quote_number") or "draft"
    name = result.get("customer_name") or "the job"
    total = result.get("total")
    try:
        money = f"${float(total):,.2f}" if total is not None else ""
    except (TypeError, ValueError):
        money = ""
    prefix = "Existing draft" if result.get("deduped") else "Draft"
    lines = [f"{prefix} {number} for {name}{f' · {money}' if money else ''}. Brand: {EMPIRE_WORKROOM_BRAND}. Not sent."]
    dims = result.get("dimensions") or {}
    if dims:
        shown = " · ".join(f"{k} {v}" for k, v in dims.items() if v)
        if shown:
            lines.append(plain_fractions(shown))
    for cut in result.get("channel_cuts") or []:
        lines.append(
            f"{cut.get('channel')}: wood/foam {cut.get('wood_cut')} · fabric {cut.get('fabric_cut')}"
        )
    leftover = result.get("channel_remainder_note") or ""
    if leftover:
        lines.append(leftover)
    elif result.get("channel_remainder"):
        lines.append(f"Leftover channel width: {result['channel_remainder']}")
    lines.append("CRM, dims, Pricing Studio rates, and the draft ran as one chain. Nothing went to the client.")
    return "\n".join(lines)


def try_handle_inbound(
    message: str,
    *,
    channel: str = "chat",
    desk: Optional[str] = None,
    has_image: bool = False,
    sender: Optional[str] = None,
    founder: Optional[bool] = None,
    chat_id: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Shared WhatsApp/chat door. None when this is not a founder job request."""
    if not quoteiq_founder_allowed(founder=founder):
        return None
    if not looks_like_quote_request(message):
        return None
    if not should_run_quoteiq_chain(message, desk=desk, has_image=has_image):
        return None
    try:
        result = run_quoteiq_chain({"message": message, "channel": channel})
    except Exception:
        logger.warning("QuoteIQ chain failed", exc_info=True)
        return None
    if not result.get("handled"):
        return None
    return result


def remember_whatsapp_session(wa_id: str, message: str, result: dict[str, Any]) -> None:
    """Keep the voice draft session so later 'send it' stays blocked, same quote."""
    try:
        from app.services.voice_documents.session import open_session, save_session

        session = open_session(key=f"whatsapp:{wa_id}", edition_id="workroom")
        if message and message not in (session.transcripts or []):
            session.transcripts.append(message)
        if result.get("quote_id"):
            session.quote_id = str(result["quote_id"])
        save_session(session)
    except Exception:
        logger.debug("QuoteIQ voice-session remember skipped", exc_info=True)
