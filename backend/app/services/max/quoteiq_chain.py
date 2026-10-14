"""QuoteIQ-style multi-step tool chain for Max.

When a job request arrives (WhatsApp / chat), run these steps as real tool
calls, passing each result forward so the founder never re-enters data:

  intake → CRM lookup/upsert → dimension parse → Pricing Studio rates → DRAFT quote

The result is always a DRAFT. Nothing is emailed or sent on WhatsApp to a
client. Measurements are shop fractions (26 3/4"), never decimals. Channel
cuts state wood/foam and fabric separately (wood = true size, foam matches
wood, fabric is the labeled allowance cut).
"""
from __future__ import annotations

import logging
import re
from typing import Any, Optional

from app.config.fabric_cut_allowance import NEEDS_FOAM_THICKNESS, lookup_fabric_allowance
from app.services.max.whatsapp_format import has_real_job_signals, is_link_or_article_message
from app.services.pricing.dimensions import plain_fractions
from app.services.pricing.rate_cards import lookup_rate
from app.services.vision.bench_cut_list import format_cut_inches
from app.services.voice_documents.extract import extract_transcript
from app.services.workroom_quote_commerce import parse_fraction_inches

logger = logging.getLogger("max.quoteiq_chain")

CHAIN_STEPS = (
    "quoteiq_intake",
    "quoteiq_crm_upsert",
    "quoteiq_parse_dimensions",
    "quoteiq_price",
    "quoteiq_draft_quote",
)

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

_SEATING = frozenset({"bench", "banquette", "seat_cushion", "back_cushion"})


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


def should_run_quoteiq_chain(
    message: str,
    *,
    desk: Optional[str] = None,
    has_image: bool = False,
) -> bool:
    """True when inbound text is a new job request, not a lookup/greeting/link."""
    if desk or has_image:
        return False
    raw = (message or "").strip()
    if not raw or is_link_or_article_message(raw):
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
    if _WXH_RE.search(raw):
        has_dims = True
    return bool(has_item or has_dims)


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
    client = (params.get("customer_name") or params.get("client_name") or probe.client_name or "").strip()
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


def _find_customer(conn, *, email: str, phone: str, name: str) -> Optional[dict]:
    if email:
        row = conn.execute(
            """SELECT * FROM customers
               WHERE email IS NOT NULL AND trim(email) != ''
                 AND lower(email) = lower(?)
               ORDER BY updated_at DESC LIMIT 1""",
            (email,),
        ).fetchone()
        if row:
            return dict(row)
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) >= 7:
        row = conn.execute(
            "SELECT * FROM customers WHERE phone IS NOT NULL AND phone != ''"
        ).fetchall()
        for candidate in row:
            existing = re.sub(r"\D", "", str(candidate["phone"] or ""))
            if existing and existing[-10:] == digits[-10:]:
                return dict(candidate)
    if name:
        row = conn.execute(
            "SELECT * FROM customers WHERE lower(name) = lower(?) ORDER BY updated_at DESC LIMIT 1",
            (name,),
        ).fetchone()
        if row:
            return dict(row)
    return None


def lookup_or_upsert_client(params: dict[str, Any]) -> dict[str, Any]:
    """Step 2 — ForgeCRM lookup/upsert. Reuses upsert_forgecrm_customer."""
    params = _params(params)
    intake = params.get("intake") if isinstance(params.get("intake"), dict) else params
    name = (intake.get("customer_name") or intake.get("client_name") or intake.get("name") or "").strip()
    email = (intake.get("customer_email") or intake.get("email") or "").strip()
    phone = (intake.get("customer_phone") or intake.get("phone") or "").strip()
    address = (intake.get("customer_address") or intake.get("address") or "").strip()
    business = (intake.get("business_unit") or "workroom").strip() or "workroom"
    if not name and not email and not phone:
        return {
            "ok": True,
            "upsert_outcome": "skipped",
            "reason": "no client identity in the job request",
            "customer": None,
            "customer_id": None,
            "customer_name": "",
            "customer_email": email,
            "customer_phone": phone,
            "customer_address": address,
        }
    try:
        from app.routers.customer_mgmt import upsert_forgecrm_customer
        from app.db.database import get_db

        with get_db() as conn:
            existing = _find_customer(conn, email=email, phone=phone, name=name)
            payload = {
                "name": name or (existing or {}).get("name") or "Customer",
                "email": email or (existing or {}).get("email"),
                "phone": phone or (existing or {}).get("phone"),
                "address": address or (existing or {}).get("address"),
                "business": business,
                "source": f"quoteiq_{_channel(intake)}",
                "notes": "QuoteIQ job-request chain",
            }
            if existing:
                payload["customer_id"] = existing["id"]
            result = upsert_forgecrm_customer(payload, conn=conn)
        customer = result.get("customer") or {}
        return {
            "ok": True,
            "upsert_outcome": result.get("upsert_outcome") or "created",
            "customer_id": result.get("customer_id") or customer.get("id"),
            "customer": {
                "id": customer.get("id"),
                "name": customer.get("name"),
                "email": customer.get("email"),
                "phone": customer.get("phone"),
                "address": customer.get("address"),
                "business": customer.get("business"),
            },
            "customer_name": customer.get("name") or name,
            "customer_email": customer.get("email") or email,
            "customer_phone": customer.get("phone") or phone,
            "customer_address": customer.get("address") or address,
            "business_unit": customer.get("business") or business,
            "ask_founder": False,
        }
    except Exception:
        logger.debug("ForgeCRM router upsert unavailable; using customers table directly", exc_info=True)
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
    """ForgeCRM customers table lookup/upsert without importing the API router."""
    import uuid

    from app.db.database import get_db

    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    with get_db() as conn:
        existing = _find_customer(conn, email=email, phone=phone, name=name)
        if existing:
            conn.execute(
                """UPDATE customers
                   SET name = COALESCE(NULLIF(?, ''), name),
                       email = COALESCE(NULLIF(?, ''), email),
                       phone = COALESCE(NULLIF(?, ''), phone),
                       address = COALESCE(NULLIF(?, ''), address),
                       business = COALESCE(NULLIF(?, ''), business),
                       updated_at = ?
                   WHERE id = ?""",
                (name, email, phone, address, business, now, existing["id"]),
            )
            row = conn.execute("SELECT * FROM customers WHERE id = ?", (existing["id"],)).fetchone()
            outcome = "matched"
        else:
            cid = uuid.uuid4().hex[:12]
            conn.execute(
                """INSERT INTO customers
                   (id, name, email, phone, address, type, source, business, notes, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 'residential', ?, ?, 'QuoteIQ job-request chain', ?, ?)""",
                (cid, name or "Customer", email or None, phone or None, address or None,
                 f"quoteiq_{channel}", business, now, now),
            )
            row = conn.execute("SELECT * FROM customers WHERE id = ?", (cid,)).fetchone()
            outcome = "created"
        customer = dict(row)
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
        "customer_name": customer.get("name") or name,
        "customer_email": customer.get("email") or email,
        "customer_phone": customer.get("phone") or phone,
        "customer_address": customer.get("address") or address,
        "business_unit": customer.get("business") or business,
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


def _channel_cuts(intake: dict[str, Any], dims: dict[str, str]) -> list[dict[str, str]]:
    style = str(intake.get("panel_style") or "")
    sections = intake.get("seat_sections") or intake.get("back_sections")
    text = str(intake.get("message") or "")
    channel_width = _inches(intake.get("channel_width_in"))
    if "channel" not in style and not sections and not channel_width and "channel" not in text.lower():
        return []
    width = _inches(intake.get("width_in")) or _inches(dims.get("width"))
    height = (
        _inches(intake.get("height_in"))
        or _inches(intake.get("back_height_in"))
        or _inches(dims.get("height"))
        or _inches(dims.get("back height"))
    )
    ch_h = height or _inches(intake.get("depth_in")) or _inches(dims.get("depth")) or width
    if channel_width:
        ch_w = channel_width
        count = int(sections) if sections else (max(1, int(round((width or channel_width) / channel_width))) if width else 1)
    elif width and sections:
        count = int(sections)
        ch_w = width / count
    elif width and "channel" in text.lower():
        count = 1
        ch_w = width
    else:
        return []
    if not ch_w:
        return []
    foam_th = _inches(intake.get("foam_thickness_in"))
    allowance = lookup_fabric_allowance(foam_th)
    extra = allowance.get("allowance_in")
    wood = f"{_as_fraction(ch_w)} x {_as_fraction(ch_h)}"
    foam = wood
    if extra is None:
        fabric = NEEDS_FOAM_THICKNESS
    else:
        fabric = f"{_as_fraction(ch_w + float(extra))} x {_as_fraction(ch_h + float(extra))}"
    cuts = []
    for idx in range(count):
        cuts.append({
            "channel": f"Ch {idx + 1}",
            "wood_cut": wood,
            "foam_cut": foam,
            "fabric_cut": fabric,
        })
    return cuts


def parse_job_dimensions(params: dict[str, Any]) -> dict[str, Any]:
    """Step 3 — dimensions as fractions; channel wood/foam vs fabric separately."""
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
    channels = _channel_cuts(intake, dimensions)
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
        "channel_rules": [
            "Wood / board cut is true size.",
            "Foam cut equals the wood cut.",
            "Fabric cut is labeled separately. Allowance depends on foam thickness.",
        ],
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


def price_with_studio(params: dict[str, Any]) -> dict[str, Any]:
    """Step 4 — price from Pricing Studio rate cards / engine. No invented dims."""
    params = _params(params)
    intake = params.get("intake") if isinstance(params.get("intake"), dict) else params
    dims = params.get("dimensions") if isinstance(params.get("dimensions"), dict) else {}
    if not dims and isinstance(params.get("parse"), dict):
        dims = params["parse"].get("dimensions") or params["parse"]
    business = (intake.get("business_unit") or params.get("business_unit") or "workroom").strip() or "workroom"
    item_type = str(intake.get("item_type") or "")
    studio_rates: dict[str, float] = {}
    try:
        studio_rates["labor_rate"] = lookup_rate(business, "labor_rate")
    except KeyError:
        studio_rates["labor_rate"] = lookup_rate("workroom", "labor_rate")
    category, inputs = _catalog_inputs(item_type, intake, dims)
    line: dict[str, Any] = {
        "category": category or "",
        "description": _line_description(intake, dims),
        "quantity": 1,
        "inputs": dict(inputs),
        "rate_source": "pricing_studio",
    }
    priced = None
    error = None
    if category in ("drapery", "roman_shade") and inputs:
        try:
            from app.services.pricing.engine import price_workroom_line

            priced = price_workroom_line(category, inputs, business_unit=business)
            line["category"] = category
            line["inputs"] = inputs
            line["proposed_price"] = priced.get("proposed_price")
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            priced = None
    if priced is None and item_type in _SEATING:
        try:
            from app.services.pricing.engine import price_workroom_item

            hours = _inches(params.get("labor_hours") or intake.get("labor_hours"))
            studio_inputs = {
                "labor_rate": studio_rates["labor_rate"],
                "quantity": 1,
            }
            if hours:
                studio_inputs["labor_hours"] = hours
            priced = price_workroom_item("upholstery", studio_inputs)
            line["category"] = ""
            line["unit_price"] = studio_rates["labor_rate"]
            line["inputs"] = {
                "description": line["description"],
                "unit_price": studio_rates["labor_rate"],
                "quantity": 1,
            }
            line["proposed_price"] = priced.get("final_price") if hours else studio_rates["labor_rate"]
            line["note"] = (
                "Pricing Studio labor_rate applied. Hours not in the request — founder confirms hours."
                if not hours
                else "Priced from Pricing Studio labor_rate."
            )
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
    if priced is None and not line.get("unit_price"):
        line["unit_price"] = studio_rates["labor_rate"]
        line["inputs"] = {
            "description": line["description"],
            "unit_price": studio_rates["labor_rate"],
            "quantity": 1,
        }
        line["proposed_price"] = studio_rates["labor_rate"]
        line["note"] = "Pricing Studio labor_rate. Confirm quantity/hours before sending."
    return {
        "ok": True,
        "engine": "pricing_studio",
        "business_unit": business,
        "studio_rates": studio_rates,
        "line_items": [line],
        "priced": {
            "final_price": (priced or {}).get("final_price") or (priced or {}).get("proposed_price"),
            "product_category": (priced or {}).get("product_category"),
            "rate_table_version": (priced or {}).get("rate_table_version"),
        } if priced else None,
        "pricing_error": error,
        "ask_founder": False,
    }


def _line_description(intake: dict[str, Any], dims: dict[str, Any]) -> str:
    name = (intake.get("item_name") or intake.get("item_type") or "Item").strip() or "Item"
    parts = []
    for key in ("width", "height", "depth", "seat_height", "back_height"):
        value = dims.get(key) or _as_fraction(intake.get(f"{key}_in") or intake.get(key))
        if value:
            parts.append(f"{value} {key.replace('_', ' ')}")
    if parts:
        return f"{name}\n" + " · ".join(parts)
    return name


def draft_quote_only(params: dict[str, Any]) -> dict[str, Any]:
    """Step 5 — persist a DRAFT via quote_service.create_quote. Never send."""
    params = _params(params)
    intake = params.get("intake") if isinstance(params.get("intake"), dict) else params
    client = params.get("client") if isinstance(params.get("client"), dict) else {}
    dims = params.get("dimensions") if isinstance(params.get("dimensions"), dict) else {}
    if not dims and isinstance(params.get("parse"), dict):
        dims = params["parse"].get("dimensions") or {}
    pricing = params.get("pricing") if isinstance(params.get("pricing"), dict) else {}
    lines = pricing.get("line_items") or params.get("line_items") or []
    if not lines:
        lines = [{
            "category": "",
            "description": _line_description(intake, dims),
            "quantity": 1,
            "unit_price": (pricing.get("studio_rates") or {}).get("labor_rate") or lookup_rate("workroom", "labor_rate"),
        }]
    name = (
        client.get("customer_name")
        or intake.get("customer_name")
        or client.get("name")
        or "Customer"
    )
    body = {
        "customer_name": name,
        "customer_email": client.get("customer_email") or intake.get("customer_email") or "",
        "customer_phone": client.get("customer_phone") or intake.get("customer_phone") or "",
        "customer_address": client.get("customer_address") or intake.get("customer_address") or "",
        "business_unit": intake.get("business_unit") or "workroom",
        "project_name": intake.get("item_name") or intake.get("item_type") or "QuoteIQ draft",
        "project_description": intake.get("message") or "",
        "notes": "quoteiq chain draft — not sent",
        "line_items": lines,
        "measurements": {
            "format": "fractions",
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
    return {
        "ok": True,
        "sent": False,
        "status": "draft",
        "store": "quotes_v2",
        "quote_id": quote.get("id"),
        "quote_number": quote.get("quote_number"),
        "customer_name": quote.get("customer_name"),
        "customer_id": client.get("customer_id"),
        "total": quote.get("total"),
        "subtotal": quote.get("subtotal"),
        "line_items": quote.get("line_items") or [],
        "channel_cuts": body["measurements"]["channel_cuts"],
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
    """Run all five steps as execute_tool calls, carrying context forward."""
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
    for name in CHAIN_STEPS:
        payload = runners[name](_step_payload(name, ctx))
        ok = bool(payload.get("ok", True))
        entry = {
            "tool": name,
            "success": ok,
            "result": payload if ok else None,
            "error": None if ok else payload.get("error") or f"{name} failed",
        }
        steps.append(entry)
        if not ok:
            return {
                "ok": False,
                "handled": True,
                "sent": False,
                "status": "blocked",
                "error": entry.get("error") or f"{name} failed",
                "steps": steps,
                "tool_results": steps,
                "reply_text": _founder_reply({"ok": False, "error": entry.get("error"), "steps": steps}),
            }
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
    quote = ctx.get("quote") or {}
    reply = {
        "ok": True,
        "handled": True,
        "sent": False,
        "status": "draft",
        "quote_id": quote.get("quote_id"),
        "quote_number": quote.get("quote_number"),
        "customer_name": quote.get("customer_name") or ctx.get("customer_name"),
        "customer_id": ctx.get("customer_id"),
        "total": quote.get("total"),
        "channel_cuts": (ctx.get("parse") or {}).get("channel_cuts") or [],
        "dimensions": (ctx.get("parse") or {}).get("dimensions") or {},
        "studio_rates": (ctx.get("pricing") or {}).get("studio_rates") or {},
        "steps": steps,
        "tool_results": steps,
        "notice": "DRAFT only. Not sent to the client.",
        "ask_founder": False,
    }
    reply["reply_text"] = _founder_reply(reply)
    return reply


def _founder_reply(result: dict[str, Any]) -> str:
    if not result.get("ok"):
        err = result.get("error") or "chain stopped"
        return f"QuoteIQ chain stopped: {err}. Nothing sent."
    number = result.get("quote_number") or "draft"
    name = result.get("customer_name") or "the client"
    total = result.get("total")
    try:
        money = f"${float(total):,.2f}" if total is not None else ""
    except (TypeError, ValueError):
        money = ""
    lines = [f"Draft {number} for {name}{f' · {money}' if money else ''}. Not sent."]
    dims = result.get("dimensions") or {}
    if dims:
        shown = " · ".join(f"{k} {v}" for k, v in dims.items() if v)
        if shown:
            lines.append(plain_fractions(shown))
    for cut in result.get("channel_cuts") or []:
        lines.append(
            f"{cut.get('channel')}: wood/foam {cut.get('wood_cut')} · fabric {cut.get('fabric_cut')}"
        )
    lines.append("CRM, dims, Pricing Studio rates, and the draft ran as one chain. Nothing went to the client.")
    return "\n".join(lines)


def try_handle_inbound(
    message: str,
    *,
    channel: str = "chat",
    desk: Optional[str] = None,
    has_image: bool = False,
) -> Optional[dict[str, Any]]:
    """Shared WhatsApp/chat door. None when this is not a new job request."""
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
