"""Workroom LeadForge intake.

One inbound becomes a ForgeCRM customer (upsert by email), a new LeadForge
lead event, a linked prospect, and one founder notification. Creating the
Workroom quote is a separate action so the shop still opens the draft.

LuxeForge is not a second CRM. Rich designer intake posts here with
``capture_surface=luxeforge`` and an optional ``luxeforge`` object. Those
fields ride on the same customer, lead, and quote.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Literal, Optional

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

CONTACT_EMAIL = "workroom@empirebox.store"
DEFAULT_CAMPAIGN = "workroom_national_48h"
BUSINESS = "workroom"

JOB_TYPES = (
    "drapery_romans",
    "banquette",
    "soft_seating",
    "headboard",
    "mixed",
    "other",
)
SOURCES = (
    "meta_ad",
    "instagram",
    "houzz",
    "outreach",
    "web",
    "referral",
    "other",
)
CAPTURE_SURFACES = ("workroom_form", "command_center", "luxeforge", "api")

JOB_LABELS = {
    "drapery_romans": "Drapery and Romans",
    "banquette": "Banquette",
    "soft_seating": "Soft seating",
    "headboard": "Headboard",
    "mixed": "Mixed soft goods",
    "other": "Workroom project",
}

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_HITS: dict[str, list[float]] = {}

IDEMPOTENCY_NOTE = (
    "One ForgeCRM customer per email (case-insensitive upsert). "
    "Each submit inserts a new LeadForge lead and a new prospect so repeat "
    "inquiries stay visible. Founder notification fires once per submit."
)

INTAKE_CONTRACT = {
    "business": BUSINESS,
    "contact_email": CONTACT_EMAIL,
    "idempotency": IDEMPOTENCY_NOTE,
    "paths": {
        "intake": "POST /api/v1/leads/intake",
        "intake_alias": "POST /api/v1/leadforge/intake",
        "contract": "GET /api/v1/leads/intake/contract",
        "workroom_quote": "POST /api/v1/leads/{lead_id}/workroom-quote",
    },
    "required": ["full_name", "email", "job_type", "message", "source", "consent_contact"],
    "job_type": list(JOB_TYPES),
    "source": list(SOURCES),
    "capture_surface": list(CAPTURE_SURFACES),
    "tags": ["business=workroom", "source=<source>", "campaign=<campaign>", "utm_campaign=<utm>"],
    "default_campaign": DEFAULT_CAMPAIGN,
    "luxeforge_handoff": {
        "capture_surface": "luxeforge",
        "same_customer_lead_quote_path": True,
        "optional_object": "luxeforge",
        "fields": [
            "brief",
            "room_count",
            "measure_urls",
            "designer_portfolio_url",
            "project_timeline",
            "photo_notes",
        ],
        "note": (
            "Send the shared room notes in message. Put richer measure/brief "
            "fields on luxeforge. Unknown extra keys are stored on the lead "
            "intake payload. Do not create a second CRM."
        ),
    },
    "quote_prefill": [
        "customer_name",
        "customer_email",
        "customer_phone",
        "notes",
        "project_description",
        "photos",
        "customer_id",
        "lead_id",
        "source",
        "utm_campaign",
    ],
    "public_host": (
        "Do not point ads at workroom./cc. hosts while they return 521 or sit "
        "behind Cloudflare Access. Command Center and this API are the intake. "
        f"Human fallback is mailto:{CONTACT_EMAIL}."
    ),
}


class LuxeForgeHandoff(BaseModel):
    """Optional rich fields from the LuxeForge capture surface."""

    model_config = ConfigDict(extra="allow")

    brief: Optional[str] = None
    room_count: Optional[int] = None
    measure_urls: Optional[list[str]] = None
    designer_portfolio_url: Optional[str] = None
    project_timeline: Optional[str] = None
    photo_notes: Optional[str] = None


class WorkroomIntake(BaseModel):
    """Thin Workroom ad/CC form, also the LuxeForge handoff body."""

    model_config = ConfigDict(extra="allow")

    full_name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=320)
    phone: Optional[str] = Field(default=None, max_length=40)
    firm_name: Optional[str] = Field(default=None, max_length=200)
    city_region: Optional[str] = Field(default=None, max_length=200)
    job_type: Literal[
        "drapery_romans",
        "banquette",
        "soft_seating",
        "headboard",
        "mixed",
        "other",
    ]
    message: str = Field(min_length=1, max_length=4000)
    photo_urls: Optional[list[str]] = None
    source: Literal[
        "meta_ad",
        "instagram",
        "houzz",
        "outreach",
        "web",
        "referral",
        "other",
    ]
    utm_campaign: Optional[str] = Field(default=None, max_length=200)
    consent_contact: bool
    business: str = BUSINESS
    campaign: Optional[str] = Field(default=None, max_length=120)
    capture_surface: Literal[
        "workroom_form", "command_center", "luxeforge", "api"
    ] = "workroom_form"
    luxeforge: Optional[LuxeForgeHandoff] = None
    # Honeypot. Real clients leave this empty. Bots that fill it are dropped.
    fax_number: Optional[str] = None


def intake_contract() -> dict:
    return INTAKE_CONTRACT


def reset_intake_state_for_tests() -> None:
    _HITS.clear()


def _leadforge():
    from app.routers import leadforge

    return leadforge


def _split_name(full_name: str) -> tuple[str, str]:
    parts = full_name.strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def _parse_tags(raw: Any) -> list:
    if not raw:
        return []
    if isinstance(raw, list):
        return list(raw)
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return []
        return data if isinstance(data, list) else []
    return []


def _clean_urls(urls: Optional[list[str]]) -> list[str]:
    cleaned = []
    for url in urls or []:
        text = (url or "").strip()
        if not text:
            continue
        if len(text) > 500:
            raise HTTPException(400, "photo_urls entries must be 500 characters or fewer")
        cleaned.append(text)
    if len(cleaned) > 12:
        raise HTTPException(400, "photo_urls accepts at most 12 urls")
    return cleaned


def _rate_limit(email: str) -> None:
    if os.getenv("LEADFORGE_INTAKE_RATE_LIMIT", "1") == "0":
        return
    now = time.time()
    window = 600
    hits = [stamp for stamp in _HITS.get(email, []) if now - stamp < window]
    if len(hits) >= 8:
        raise HTTPException(
            429,
            f"Too many submissions for this email. Email {CONTACT_EMAIL} instead.",
        )
    hits.append(now)
    _HITS[email] = hits


def _ensure_customers_table(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS customers (
            id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            address TEXT,
            company TEXT,
            type TEXT DEFAULT 'residential',
            tags TEXT,
            notes TEXT,
            total_revenue REAL DEFAULT 0,
            lifetime_quotes INTEGER DEFAULT 0,
            source TEXT DEFAULT 'direct',
            business TEXT DEFAULT 'empire',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
        """
    )


def _merge_tags(existing: list, incoming: list[str]) -> list:
    merged = list(existing)
    for tag in incoming:
        if tag not in merged:
            merged.append(tag)
    return merged


def _upsert_customer(conn, *, name: str, email: str, phone: Optional[str], company: Optional[str], city_region: Optional[str], message: str, source: str, tags: list[str]) -> tuple[str, str]:
    row = conn.execute(
        "SELECT * FROM customers WHERE LOWER(email) = LOWER(?) LIMIT 1",
        (email,),
    ).fetchone()
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    note_line = f"[workroom intake {stamp}] {message.strip()}"

    if row is None:
        values = (
            name,
            email,
            phone,
            city_region,
            company,
            json.dumps(tags),
            note_line,
            source,
            BUSINESS,
        )
        insert_sql = """INSERT INTO customers
               (name, email, phone, address, company, type, tags, notes, source, business)
               VALUES (?,?,?,?,?,?,?,?,?,?)"""
        conn.execute("SAVEPOINT customer_insert")
        try:
            cur = conn.execute(insert_sql, values[:5] + ("designer",) + values[5:])
            conn.execute("RELEASE SAVEPOINT customer_insert")
        except Exception:
            conn.execute("ROLLBACK TO SAVEPOINT customer_insert")
            conn.execute("RELEASE SAVEPOINT customer_insert")
            cur = conn.execute(insert_sql, values[:5] + ("residential",) + values[5:])
        inserted = conn.execute(
            "SELECT id FROM customers WHERE rowid = ?",
            (cur.lastrowid,),
        ).fetchone()
        return inserted["id"], "created"

    existing_tags = _merge_tags(_parse_tags(row["tags"]), tags)
    prior_notes = (row["notes"] or "").strip()
    notes = f"{prior_notes}\n{note_line}".strip() if prior_notes else note_line
    if len(notes) > 8000:
        notes = notes[-8000:]
    existing_business = (row["business"] or "").strip()
    business = BUSINESS if existing_business in ("", "empire", "workroom") else existing_business
    conn.execute(
        """UPDATE customers
           SET name = ?,
               phone = CASE WHEN ? IS NOT NULL AND ? != '' THEN ? ELSE phone END,
               address = CASE WHEN ? IS NOT NULL AND ? != '' THEN ? ELSE address END,
               company = CASE WHEN ? IS NOT NULL AND ? != '' THEN ? ELSE company END,
               tags = ?,
               notes = ?,
               business = ?,
               updated_at = datetime('now')
           WHERE id = ?""",
        (
            name or row["name"],
            phone, phone, phone,
            city_region, city_region, city_region,
            company, company, company,
            json.dumps(existing_tags),
            notes,
            business,
            row["id"],
        ),
    )
    return row["id"], "updated"


def _validate(body: WorkroomIntake) -> str:
    if (body.fax_number or "").strip():
        raise HTTPException(400, "Submission rejected")
    if (body.business or "").strip().lower() != BUSINESS:
        raise HTTPException(400, "This intake only accepts business=workroom")
    if not body.consent_contact:
        raise HTTPException(400, "consent_contact is required")
    email = body.email.strip()
    if not _EMAIL_RE.match(email):
        raise HTTPException(400, "email is not valid")
    _clean_urls(body.photo_urls)
    if body.luxeforge and body.luxeforge.measure_urls:
        _clean_urls(body.luxeforge.measure_urls)
    return email


async def submit_intake(body: WorkroomIntake) -> dict:
    email = _validate(body)
    _rate_limit(email.lower())

    campaign = (body.campaign or DEFAULT_CAMPAIGN).strip() or DEFAULT_CAMPAIGN
    capture_surface = body.capture_surface
    photos = _clean_urls(body.photo_urls)
    first_name, last_name = _split_name(body.full_name)
    utm = (body.utm_campaign or "").strip() or None
    tags = [
        "business=workroom",
        f"source={body.source}",
        f"campaign={campaign}",
        f"capture_surface={capture_surface}",
        f"job_type={body.job_type}",
    ]
    if utm:
        tags.append(f"utm_campaign={utm}")

    luxeforge_payload = body.luxeforge.model_dump() if body.luxeforge else None
    extra = dict(body.model_extra or {})
    payload = {
        "capture_surface": capture_surface,
        "luxeforge": luxeforge_payload,
        "extra": extra,
        "contact_email": CONTACT_EMAIL,
    }
    encoded_payload = json.dumps(payload)
    if len(encoded_payload) > 20000:
        raise HTTPException(400, "intake payload is too large")

    lf = _leadforge()
    with lf._db() as conn:
        _ensure_customers_table(conn)
        customer_id, customer_outcome = _upsert_customer(
            conn,
            name=body.full_name.strip(),
            email=email,
            phone=(body.phone or "").strip() or None,
            company=(body.firm_name or "").strip() or None,
            city_region=(body.city_region or "").strip() or None,
            message=body.message.strip(),
            source=body.source,
            tags=tags,
        )
        cur = conn.execute(
            """INSERT INTO lf_leads
               (business_unit, first_name, last_name, company, email, phone,
                city, source, status, temperature, score, tags, notes,
                next_action, customer_id, utm_campaign, job_type, city_region,
                photo_urls, consent_contact, capture_surface, intake_payload,
                campaign)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                BUSINESS,
                first_name,
                last_name,
                (body.firm_name or "").strip() or None,
                email,
                (body.phone or "").strip() or None,
                (body.city_region or "").strip() or None,
                body.source,
                "new",
                "warm",
                55,
                json.dumps(tags),
                body.message.strip(),
                "Create Workroom quote",
                customer_id,
                utm,
                body.job_type,
                (body.city_region or "").strip() or None,
                json.dumps(photos),
                1,
                capture_surface,
                encoded_payload,
                campaign,
            ),
        )
        lead_id = cur.lastrowid
        prospect = conn.execute(
            """INSERT INTO lf_prospects
               (name, business_name, email, phone, platform, location, category,
                converted_to_lead, lead_id)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                body.full_name.strip(),
                (body.firm_name or "").strip() or None,
                email,
                (body.phone or "").strip() or None,
                body.source,
                (body.city_region or "").strip() or None,
                body.job_type,
                1,
                lead_id,
            ),
        )
        prospect_id = prospect.lastrowid
        conn.execute(
            """INSERT INTO lf_activities
               (lead_id, type, channel, subject, content, ai_generated, status, completed_at)
               VALUES (?,?,?,?,?,?,?, datetime('now'))""",
            (
                lead_id,
                "note",
                "intake",
                "Workroom intake",
                (
                    f"customer_id={customer_id}; source={body.source}; "
                    f"utm_campaign={utm or ''}; campaign={campaign}; "
                    f"capture_surface={capture_surface}"
                ),
                0,
                "completed",
            ),
        )

    notification = _inbox_notify(
        lead_id=lead_id,
        customer_id=customer_id,
        name=body.full_name.strip(),
        email=email,
        job_type=body.job_type,
        source=body.source,
        utm=utm,
        message=body.message.strip(),
        capture_surface=capture_surface,
    )
    notification["telegram"] = await _telegram_notify(
        lead_id=lead_id,
        customer_id=customer_id,
        name=body.full_name.strip(),
        email=email,
        job_type=body.job_type,
        source=body.source,
        utm=utm,
        message=body.message.strip(),
    )

    return {
        "lead_id": lead_id,
        "prospect_id": prospect_id,
        "customer_id": customer_id,
        "customer_outcome": customer_outcome,
        "business": BUSINESS,
        "source": body.source,
        "utm_campaign": utm,
        "campaign": campaign,
        "capture_surface": capture_surface,
        "idempotency": IDEMPOTENCY_NOTE,
        "notification": notification,
        "quote_action": f"POST /api/v1/leads/{lead_id}/workroom-quote",
        "contact_email": CONTACT_EMAIL,
    }


def _inbox_notify(*, lead_id: int, customer_id: str, name: str, email: str, job_type: str, source: str, utm: Optional[str], message: str, capture_surface: str) -> dict:
    from app.routers.notifications import notify_founder

    deep_link = f"/?product=lead&lead_id={lead_id}"
    utm_bit = f" · utm={utm}" if utm else ""
    entry = notify_founder(
        "Business",
        "business_event",
        f"Workroom lead: {name}",
        (
            f"{name} <{email}> · {job_type} · {source}{utm_bit}\n"
            f"{message[:500]}\n"
            f"CRM {customer_id} · LeadForge #{lead_id} · {capture_surface}\n"
            f"Open Command Center LeadForge and review lead #{lead_id}."
        ),
        "high",
        {
            "event": "workroom_lead_intake",
            "lead_id": lead_id,
            "customer_id": customer_id,
            "deep_link": deep_link,
            "email": email,
            "source": source,
            "utm_campaign": utm,
            "business": BUSINESS,
            "capture_surface": capture_surface,
        },
    )
    return {
        "id": entry["id"],
        "channel": "founder_inbox",
        "deep_link": deep_link,
        "telegram": "not_configured",
    }


async def _telegram_notify(*, lead_id: int, customer_id: str, name: str, email: str, job_type: str, source: str, utm: Optional[str], message: str) -> str:
    if not os.getenv("TELEGRAM_BOT_TOKEN") or not os.getenv("TELEGRAM_FOUNDER_CHAT_ID"):
        return "not_configured"
    utm_bit = f" utm={utm}" if utm else ""
    text = (
        f"Workroom lead #{lead_id}\n"
        f"{name} <{email}>\n"
        f"{job_type} · {source}{utm_bit}\n"
        f"{message[:400]}\n"
        f"CRM {customer_id}\n"
        f"Open LeadForge in Command Center (lead {lead_id})."
    )
    try:
        from app.services.max.telegram_bot import telegram_bot

        if not telegram_bot.is_configured:
            return "not_configured"
        sent = await telegram_bot.send_message(text)
        return "sent" if sent else "failed"
    except Exception:
        logger.exception("Workroom intake Telegram notify failed for lead %s", lead_id)
        return "failed"


def _lead_row(lead_id: int) -> dict:
    lf = _leadforge()
    with lf._db() as conn:
        row = conn.execute("SELECT * FROM lf_leads WHERE id = ?", (lead_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Lead not found")
    return lf._dict(row)


def _quote_notes(lead: dict) -> str:
    message = (lead.get("notes") or "").strip()
    payload = lead.get("intake_payload") or {}
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            payload = {}
    brief = ""
    photo_notes = ""
    if isinstance(payload, dict):
        lux = payload.get("luxeforge") or {}
        if isinstance(lux, dict):
            brief = (lux.get("brief") or "").strip()
            photo_notes = (lux.get("photo_notes") or "").strip()
    parts = [message]
    if brief and brief not in message:
        parts.append(f"LuxeForge brief: {brief}")
    if photo_notes and photo_notes not in message:
        parts.append(f"Photo notes: {photo_notes}")
    return "\n\n".join(part for part in parts if part)


def _quote_photos(lead: dict) -> list[dict]:
    photos = lead.get("photo_urls") or []
    if isinstance(photos, str):
        try:
            photos = json.loads(photos)
        except json.JSONDecodeError:
            photos = []
    entries = [
        {"url": url, "type": "reference", "source": "workroom_intake"}
        for url in photos
        if isinstance(url, str) and url
    ]
    payload = lead.get("intake_payload") or {}
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            payload = {}
    lux = payload.get("luxeforge") if isinstance(payload, dict) else None
    for url in (lux or {}).get("measure_urls") or []:
        if isinstance(url, str) and url:
            entries.append({"url": url, "type": "measure", "source": "luxeforge"})
    return entries


async def create_workroom_quote(lead_id: int) -> dict:
    lead = _lead_row(lead_id)
    if (lead.get("business_unit") or "") != BUSINESS:
        raise HTTPException(400, "Only workroom leads can open a Workroom quote")

    from app.routers.quotes import QuoteCreate, _load_quote, _save_quote, create_quote

    existing_id = lead.get("quote_id")
    if existing_id:
        try:
            existing = _load_quote(existing_id)
            return {
                "status": "existing",
                "quote": existing,
                "lead_id": lead_id,
                "customer_id": lead.get("customer_id"),
            }
        except HTTPException:
            pass

    full_name = " ".join(
        part for part in (lead.get("first_name"), lead.get("last_name")) if part
    ).strip() or "Workroom client"
    notes = _quote_notes(lead)
    job = lead.get("job_type") or "other"
    firm = lead.get("company") or ""
    project_name = JOB_LABELS.get(job, "Workroom project")
    if firm:
        project_name = f"{project_name} — {firm}"

    created = await create_quote(
        QuoteCreate(
            customer_name=full_name,
            customer_email=lead.get("email"),
            customer_phone=lead.get("phone"),
            customer_address=lead.get("city_region") or lead.get("city"),
            project_name=project_name,
            project_description=notes,
            notes=notes,
            business_unit=BUSINESS,
            business_name=firm or "Empire Workroom",
            pricing_mode="flat",
            line_items=[],
            desk_id="workroom",
        )
    )
    quote = created["quote"]
    quote["photos"] = _quote_photos(lead)
    quote["customer_id"] = lead.get("customer_id")
    quote["lead_id"] = lead_id
    quote["job_type"] = job
    quote["firm_name"] = firm or None
    quote["intake_source"] = lead.get("source")
    quote["utm_campaign"] = lead.get("utm_campaign")
    quote["campaign"] = lead.get("campaign")
    quote["capture_surface"] = lead.get("capture_surface")
    quote["city_region"] = lead.get("city_region")
    quote["business_unit"] = BUSINESS
    _save_quote(quote)

    lf = _leadforge()
    with lf._db() as conn:
        conn.execute(
            """UPDATE lf_leads
               SET quote_id = ?,
                   next_action = ?,
                   updated_at = datetime('now')
               WHERE id = ?""",
            (
                quote["id"],
                f"Review Workroom quote {quote.get('quote_number')}",
                lead_id,
            ),
        )
        conn.execute(
            """INSERT INTO lf_activities
               (lead_id, type, channel, subject, content, ai_generated, status, completed_at)
               VALUES (?,?,?,?,?,?,?, datetime('now'))""",
            (
                lead_id,
                "note",
                "internal",
                "Workroom quote created",
                f"quote_id={quote['id']}; quote_number={quote.get('quote_number')}",
                0,
                "completed",
            ),
        )

    return {
        "status": "created",
        "quote": quote,
        "lead_id": lead_id,
        "customer_id": lead.get("customer_id"),
    }
