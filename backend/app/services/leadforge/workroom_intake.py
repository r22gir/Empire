"""Shared Workroom capture for LeadForge and LuxeForge.

One door, one CRM, one quote create path:

* ``submit_workroom_intake`` upserts a ForgeCRM ``customers`` row (email),
  a LeadForge ``prospects`` row (email + business=workroom), and one
  ``lf_leads`` row (email + business_unit=workroom).
* Each submit appends an intake event and an ``lf_activities`` note, and
  writes one founder inbox notification. A repeat email does not create a
  second customer, prospect, or lead.
* ``create_workroom_quote_from_lead`` calls ``quotes.create_quote`` so the
  draft is the same Workroom quote record the rest of the shop uses.

LuxeForge is the rich brief (measure notes, photo URLs, firm). LeadForge
thin ads call the same function with ``capture_channel='leadforge'``.

Public-host note: Command Center routes ``/luxe`` and ``/luxeforge`` render
the brief. ``luxe.empirebox.store`` still redirects those paths to ``/intake``
(the account portal). Studio / cc hosts are often behind Cloudflare Access,
and public API hosts have been 521. Do not point ads here until that host
returns 200 without an Access wall.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from typing import Any, Optional

logger = logging.getLogger(__name__)

WORKROOM_CONTACT = "workroom@empirebox.store"
BUSINESS = "workroom"
AD_CAMPAIGN = "workroom_national_48h"

JOB_TYPES = (
    "drapery_romans",
    "banquette",
    "soft_seating",
    "headboard",
    "mixed",
    "other",
)

JOB_LABELS = {
    "drapery_romans": "Drapery & Romans",
    "banquette": "Banquette",
    "soft_seating": "Soft seating",
    "headboard": "Headboard",
    "mixed": "Mixed",
    "other": "Other",
}

SOURCES = (
    "meta_ad",
    "instagram",
    "houzz",
    "outreach",
    "web",
    "referral",
    "other",
)

CAPTURE_CHANNELS = ("luxeforge", "leadforge")


class IntakeError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


_LEAD_SCHEMA = """
CREATE TABLE IF NOT EXISTS lf_leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_unit TEXT NOT NULL DEFAULT 'empire_saas'
        CHECK(business_unit IN ('workroom','woodcraft','empire_saas')),
    first_name TEXT,
    last_name TEXT,
    company TEXT,
    email TEXT,
    phone TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    zip TEXT,
    source TEXT,
    source_url TEXT,
    score INTEGER DEFAULT 0 CHECK(score BETWEEN 0 AND 100),
    score_factors TEXT DEFAULT '{}',
    status TEXT DEFAULT 'new'
        CHECK(status IN ('new','contacted','responded','qualified',
              'proposal_sent','negotiating','won','lost','nurture')),
    temperature TEXT DEFAULT 'cold'
        CHECK(temperature IN ('cold','warm','hot')),
    estimated_value REAL DEFAULT 0,
    assigned_to TEXT,
    tags TEXT DEFAULT '[]',
    notes TEXT,
    next_action TEXT,
    next_action_date TEXT,
    last_contacted TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS lf_activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL REFERENCES lf_leads(id) ON DELETE CASCADE,
    type TEXT NOT NULL
        CHECK(type IN ('email_sent','email_received','call_made','call_received',
              'sms_sent','social_dm','site_visit','proposal_sent','meeting','note')),
    channel TEXT,
    subject TEXT,
    content TEXT,
    ai_generated INTEGER DEFAULT 0,
    status TEXT DEFAULT 'completed',
    scheduled_at TEXT,
    completed_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS prospects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    business_name TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    zip TEXT,
    phone TEXT,
    website TEXT,
    email TEXT,
    location TEXT,
    platform TEXT,
    source TEXT,
    external_id TEXT,
    rating REAL DEFAULT 0,
    review_count INTEGER DEFAULT 0,
    categories TEXT DEFAULT '[]',
    description TEXT,
    score INTEGER DEFAULT 0,
    status TEXT DEFAULT 'new',
    client_type TEXT,
    designer_fit INTEGER DEFAULT 0,
    window_treatments_fit INTEGER DEFAULT 0,
    outreach_ready INTEGER DEFAULT 0,
    card_summary TEXT,
    recommended_units TEXT DEFAULT '[]',
    first_seen_at TEXT DEFAULT (datetime('now')),
    last_seen_at TEXT DEFAULT (datetime('now')),
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS prospect_pipeline (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id INTEGER NOT NULL UNIQUE REFERENCES prospects(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'new',
    notes TEXT,
    next_action TEXT,
    assigned_unit TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS lf_workroom_intake_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL,
    prospect_id INTEGER,
    customer_id TEXT,
    email TEXT NOT NULL,
    full_name TEXT,
    phone TEXT,
    firm_name TEXT,
    city_region TEXT,
    job_type TEXT,
    message TEXT,
    measure_notes TEXT,
    photo_urls TEXT DEFAULT '[]',
    source TEXT,
    utm_campaign TEXT,
    capture_channel TEXT DEFAULT 'leadforge',
    consent_contact INTEGER DEFAULT 0,
    business TEXT DEFAULT 'workroom',
    tags TEXT DEFAULT '[]',
    notified_at TEXT,
    quote_id TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
"""


def _db_path() -> str:
    from app.db import database

    return os.getenv("EMPIRE_TASK_DB", database.DB_PATH)


@contextmanager
def _db():
    path = _db_path()
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, decl: str) -> None:
    if column not in _columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_LEAD_SCHEMA)
    customer = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='customers'"
    ).fetchone()
    if not customer:
        raise IntakeError(
            500,
            "ForgeCRM customers table is not initialized. Workroom intake will not create a second CRM.",
        )
    for table, column, decl in (
        ("customers", "business", "TEXT DEFAULT 'empire'"),
        ("customers", "company", "TEXT"),
        ("customers", "tags", "TEXT"),
        ("customers", "source", "TEXT"),
        ("lf_leads", "customer_id", "TEXT"),
        ("lf_leads", "utm_campaign", "TEXT"),
        ("lf_leads", "job_type", "TEXT"),
        ("lf_leads", "capture_channel", "TEXT"),
        ("prospects", "business", "TEXT DEFAULT 'workroom'"),
        ("lf_workroom_intake_events", "quote_id", "TEXT"),
    ):
        _ensure_column(conn, table, column, decl)


def _split_name(full_name: str) -> tuple[str, Optional[str]]:
    parts = [p for p in (full_name or "").split() if p]
    if not parts:
        return "", None
    if len(parts) == 1:
        return parts[0], None
    return parts[0], " ".join(parts[1:])


def _clean_urls(urls: Optional[list]) -> list[str]:
    cleaned = []
    for url in urls or []:
        text = str(url).strip()
        if text and text not in cleaned:
            cleaned.append(text)
    return cleaned[:20]


def _tags(payload: dict) -> list[str]:
    capture = payload["capture_channel"]
    tags = [
        "business=workroom",
        f"capture={capture}",
        f"job_type={payload['job_type']}",
        f"source={payload['source']}",
    ]
    utm = payload.get("utm_campaign") or ""
    if utm:
        tags.append(f"utm={utm}")
        tags.append(f"campaign={utm}")
    elif capture == "leadforge":
        tags.append(f"campaign={AD_CAMPAIGN}")
    else:
        tags.append("campaign=luxeforge_designer_brief")
    return tags


def _brief_notes(payload: dict) -> str:
    parts = [payload["message"].strip()]
    measure = (payload.get("measure_notes") or "").strip()
    if measure:
        parts.append(f"Measure notes:\n{measure}")
    photos = payload.get("photo_urls") or []
    if photos:
        parts.append("Photos:\n" + "\n".join(photos))
    return "\n\n".join(parts)


def quote_prefill_from_payload(payload: dict) -> dict:
    """Fields the Workroom quote create path should receive. No second model."""
    label = JOB_LABELS.get(payload["job_type"], payload["job_type"])
    firm = (payload.get("firm_name") or "").strip() or payload["full_name"]
    return {
        "customer_name": payload["full_name"],
        "customer_email": payload["email"],
        "customer_phone": payload.get("phone") or "",
        "customer_address": payload.get("city_region") or "",
        "project_name": f"{firm} — {label}",
        "project_description": payload["message"],
        "notes": _brief_notes(payload),
        "business_unit": BUSINESS,
        "valid_days": 30,
        "line_items": [
            {
                "description": f"{label} — designer brief",
                "quantity": 1,
                "unit": "ea",
                "rate": 0.0,
                "amount": 0.0,
                "category": "labor",
            }
        ],
        "photos": [
            {"url": url, "source": payload["capture_channel"], "original_name": url}
            for url in payload.get("photo_urls") or []
        ],
        "job_type": payload["job_type"],
        "measure_notes": payload.get("measure_notes") or "",
        "capture_channel": payload["capture_channel"],
    }


def _normalize(raw: dict) -> dict:
    business = (raw.get("business") or BUSINESS).strip().lower()
    if business != BUSINESS:
        raise IntakeError(
            400,
            "Workroom intake only accepts business=workroom. Apostille and contractor leads use their own doors.",
        )
    if raw.get("consent_contact") is not True:
        raise IntakeError(400, "consent_contact is required")

    capture = (raw.get("capture_channel") or "leadforge").strip().lower()
    if capture not in CAPTURE_CHANNELS:
        raise IntakeError(400, "capture_channel must be luxeforge or leadforge")

    job_type = (raw.get("job_type") or "").strip()
    if job_type not in JOB_TYPES:
        raise IntakeError(400, f"job_type must be one of: {', '.join(JOB_TYPES)}")

    source = (raw.get("source") or "").strip()
    if source not in SOURCES:
        raise IntakeError(400, f"source must be one of: {', '.join(SOURCES)}")

    full_name = (raw.get("full_name") or "").strip()
    email = (raw.get("email") or "").strip().lower()
    message = (raw.get("message") or "").strip()
    if not full_name or not email or not message:
        raise IntakeError(400, "full_name, email, and message are required")
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise IntakeError(400, "email is invalid")

    return {
        "full_name": full_name,
        "email": email,
        "phone": (raw.get("phone") or "").strip() or None,
        "firm_name": (raw.get("firm_name") or "").strip() or None,
        "city_region": (raw.get("city_region") or "").strip() or None,
        "job_type": job_type,
        "message": message,
        "measure_notes": (raw.get("measure_notes") or "").strip() or None,
        "photo_urls": _clean_urls(raw.get("photo_urls")),
        "source": source,
        "utm_campaign": (raw.get("utm_campaign") or "").strip() or None,
        "consent_contact": True,
        "capture_channel": capture,
        "business": BUSINESS,
    }


def _row(row: sqlite3.Row | None) -> Optional[dict]:
    if row is None:
        return None
    data = dict(row)
    for key in ("tags", "photo_urls", "categories", "recommended_units", "score_factors"):
        if key in data and isinstance(data[key], str):
            try:
                data[key] = json.loads(data[key])
            except json.JSONDecodeError:
                pass
    return data


def _upsert_customer(conn: sqlite3.Connection, payload: dict, notes: str) -> tuple[str, str]:
    row = conn.execute(
        "SELECT * FROM customers WHERE LOWER(email) = LOWER(?) ORDER BY updated_at DESC LIMIT 1",
        (payload["email"],),
    ).fetchone()
    customer_type = "designer" if payload["capture_channel"] == "luxeforge" else "residential"
    tags = json.dumps(_tags(payload))
    if row:
        current = dict(row)
        business = (current.get("business") or "").strip()
        next_business = business
        if business in ("", "empire", BUSINESS):
            next_business = BUSINESS
        existing_notes = (current.get("notes") or "").strip()
        combined_notes = notes if not existing_notes or notes in existing_notes else f"{existing_notes}\n\n{notes}"
        conn.execute(
            """UPDATE customers
               SET name = CASE WHEN COALESCE(name, '') = '' THEN ? ELSE name END,
                   phone = CASE WHEN COALESCE(phone, '') = '' THEN ? ELSE phone END,
                   company = CASE WHEN COALESCE(company, '') = '' THEN ? ELSE company END,
                   address = CASE WHEN COALESCE(address, '') = '' THEN ? ELSE address END,
                   type = CASE WHEN type IN ('residential', '') AND ? = 'designer' THEN 'designer' ELSE type END,
                   source = ?,
                   tags = ?,
                   notes = ?,
                   business = ?,
                   updated_at = datetime('now')
               WHERE id = ?""",
            (
                payload["full_name"],
                payload["phone"],
                payload["firm_name"],
                payload["city_region"],
                customer_type,
                payload["source"],
                tags,
                combined_notes[-4000:],
                next_business,
                current["id"],
            ),
        )
        return current["id"], "matched"

    cur = conn.execute(
        """INSERT INTO customers
           (name, email, phone, address, company, type, tags, notes, source, business)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            payload["full_name"],
            payload["email"],
            payload["phone"],
            payload["city_region"],
            payload["firm_name"],
            customer_type,
            tags,
            notes[:4000],
            payload["source"],
            BUSINESS,
        ),
    )
    inserted = conn.execute(
        "SELECT id FROM customers WHERE rowid = ?",
        (cur.lastrowid,),
    ).fetchone()
    return inserted["id"], "created"


def _upsert_lead(conn: sqlite3.Connection, payload: dict, customer_id: str, notes: str, tags: list[str]) -> tuple[int, str]:
    first, last = _split_name(payload["full_name"])
    row = conn.execute(
        """SELECT * FROM lf_leads
           WHERE LOWER(email) = LOWER(?) AND business_unit = ?
           ORDER BY id DESC LIMIT 1""",
        (payload["email"], BUSINESS),
    ).fetchone()
    tag_json = json.dumps(tags)
    if row:
        conn.execute(
            """UPDATE lf_leads
               SET first_name = ?,
                   last_name = ?,
                   company = COALESCE(?, company),
                   phone = COALESCE(?, phone),
                   city = COALESCE(?, city),
                   source = ?,
                   utm_campaign = ?,
                   job_type = ?,
                   capture_channel = ?,
                   customer_id = ?,
                   tags = ?,
                   notes = ?,
                   temperature = 'warm',
                   next_action = 'Create Workroom quote',
                   updated_at = datetime('now')
               WHERE id = ?""",
            (
                first,
                last,
                payload["firm_name"],
                payload["phone"],
                payload["city_region"],
                payload["source"],
                payload["utm_campaign"],
                payload["job_type"],
                payload["capture_channel"],
                customer_id,
                tag_json,
                notes,
                row["id"],
            ),
        )
        return row["id"], "updated"

    cur = conn.execute(
        """INSERT INTO lf_leads
           (business_unit, first_name, last_name, company, email, phone, city,
            source, score, status, temperature, tags, notes, next_action,
            customer_id, utm_campaign, job_type, capture_channel)
           VALUES ('workroom', ?, ?, ?, ?, ?, ?, ?, 70, 'new', 'warm', ?, ?,
                   'Create Workroom quote', ?, ?, ?, ?)""",
        (
            first,
            last,
            payload["firm_name"],
            payload["email"],
            payload["phone"],
            payload["city_region"],
            payload["source"],
            tag_json,
            notes,
            customer_id,
            payload["utm_campaign"],
            payload["job_type"],
            payload["capture_channel"],
        ),
    )
    return int(cur.lastrowid), "created"


def _upsert_prospect(conn: sqlite3.Connection, payload: dict, notes: str) -> tuple[int, str]:
    cols = _columns(conn, "prospects")
    business_clause = ""
    params: list[Any] = [payload["email"]]
    if "business" in cols:
        business_clause = " AND COALESCE(business, '') IN ('', 'workroom')"
    row = conn.execute(
        f"""SELECT * FROM prospects
            WHERE LOWER(email) = LOWER(?){business_clause}
            ORDER BY id DESC LIMIT 1""",
        params,
    ).fetchone()
    summary = f"{payload['full_name']} — {JOB_LABELS[payload['job_type']]}. {payload['message'][:180]}"
    categories = json.dumps(["business=workroom", f"job_type={payload['job_type']}", "designer"])
    units = json.dumps(["workroom"])
    window_fit = 1 if payload["job_type"] in {"drapery_romans", "mixed"} else 0
    fields = {
        "name": payload["full_name"],
        "business_name": payload["firm_name"],
        "email": payload["email"],
        "phone": payload["phone"],
        "city": payload["city_region"],
        "location": payload["city_region"],
        "source": payload["source"],
        "platform": payload["capture_channel"],
        "description": notes,
        "status": "new",
        "client_type": "designer" if payload["capture_channel"] == "luxeforge" else "inbound",
        "designer_fit": 1 if payload["capture_channel"] == "luxeforge" else 0,
        "window_treatments_fit": window_fit,
        "outreach_ready": 1,
        "card_summary": summary,
        "categories": categories,
        "recommended_units": units,
        "business": BUSINESS,
    }
    if row:
        sets = []
        values = []
        for key, value in fields.items():
            if key not in cols or key == "email" or value is None:
                continue
            sets.append(f"{key} = ?")
            values.append(value)
        if "last_seen_at" in cols:
            sets.append("last_seen_at = datetime('now')")
        values.append(row["id"])
        conn.execute(f"UPDATE prospects SET {', '.join(sets)} WHERE id = ?", values)
        prospect_id = row["id"]
        outcome = "updated"
    else:
        use = {key: value for key, value in fields.items() if key in cols}
        keys = list(use)
        cur = conn.execute(
            f"INSERT INTO prospects ({', '.join(keys)}) VALUES ({', '.join('?' for _ in keys)})",
            [use[key] for key in keys],
        )
        prospect_id = int(cur.lastrowid)
        outcome = "created"

    existing = conn.execute(
        "SELECT id FROM prospect_pipeline WHERE prospect_id = ?",
        (prospect_id,),
    ).fetchone()
    if existing:
        conn.execute(
            """UPDATE prospect_pipeline
               SET notes = ?,
                   next_action = 'Create Workroom quote',
                   assigned_unit = CASE
                       WHEN COALESCE(assigned_unit, '') IN ('', 'workroom') THEN 'workroom'
                       ELSE assigned_unit
                   END,
                   updated_at = datetime('now')
               WHERE prospect_id = ?""",
            (notes[:2000], prospect_id),
        )
    else:
        conn.execute(
            """INSERT INTO prospect_pipeline
               (prospect_id, status, notes, next_action, assigned_unit)
               VALUES (?, 'new', ?, 'Create Workroom quote', 'workroom')""",
            (prospect_id, notes[:2000]),
        )
    return prospect_id, outcome


def _notify_founder(event_id: int, payload: dict, lead_id: int, customer_id: str) -> dict:
    from app.services.data_paths import inbox_dir

    folder = inbox_dir()
    folder.mkdir(parents=True, exist_ok=True)
    label = JOB_LABELS[payload["job_type"]]
    text = (
        f"Workroom brief ({payload['capture_channel']})\n"
        f"{payload['full_name']} <{payload['email']}>\n"
        f"{label}\n"
        f"{payload['message'][:400]}\n"
        f"Lead #{lead_id} · CRM {customer_id}\n"
        f"Open /luxe · reply {WORKROOM_CONTACT}"
    )
    msg_id = f"wri-{event_id}"
    body = {
        "id": msg_id,
        "text": text,
        "source": payload["capture_channel"],
        "intent": "lead",
        "desk_target": "intake",
        "priority": 2,
        "status": "received",
        "lead_id": lead_id,
        "customer_id": customer_id,
        "event_id": event_id,
        "business": BUSINESS,
        "deep_link": "/luxe",
        "contact": WORKROOM_CONTACT,
    }
    (folder / f"{msg_id}.json").write_text(json.dumps(body, indent=2))
    telegram = _try_telegram(text)
    return {"inbox_id": msg_id, "telegram": telegram, "notified": True}


def _try_telegram(text: str) -> str:
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        return "skipped_no_token"
    try:
        import asyncio
        from app.services.max.telegram_bot import telegram_bot

        asyncio.run(telegram_bot.send_message(text))
        return "sent"
    except Exception as exc:
        logger.info("Workroom intake Telegram notify skipped: %s", exc)
        return "skipped_error"


def _event_count(conn: sqlite3.Connection, email: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM lf_workroom_intake_events WHERE LOWER(email) = LOWER(?)",
        (email,),
    ).fetchone()[0]


def _load_event(conn: sqlite3.Connection, lead_id: int) -> Optional[dict]:
    row = conn.execute(
        """SELECT * FROM lf_workroom_intake_events
           WHERE lead_id = ? ORDER BY id DESC LIMIT 1""",
        (lead_id,),
    ).fetchone()
    return _row(row)


def _payload_from_event(event: dict) -> dict:
    return {
        "full_name": event.get("full_name") or "",
        "email": event.get("email") or "",
        "phone": event.get("phone"),
        "firm_name": event.get("firm_name"),
        "city_region": event.get("city_region"),
        "job_type": event.get("job_type") or "other",
        "message": event.get("message") or "",
        "measure_notes": event.get("measure_notes"),
        "photo_urls": event.get("photo_urls") or [],
        "source": event.get("source") or "other",
        "utm_campaign": event.get("utm_campaign"),
        "capture_channel": event.get("capture_channel") or "leadforge",
        "business": BUSINESS,
        "consent_contact": True,
    }


def submit_workroom_intake(raw: dict) -> dict:
    """Upsert CRM + LeadForge prospect/lead and record one intake event."""
    payload = _normalize(raw)
    notes = _brief_notes(payload)
    tags = _tags(payload)

    with _db() as conn:
        ensure_schema(conn)
        customer_id, crm_outcome = _upsert_customer(conn, payload, notes)
        lead_id, lead_outcome = _upsert_lead(conn, payload, customer_id, notes, tags)
        prospect_id, prospect_outcome = _upsert_prospect(conn, payload, notes)
        cur = conn.execute(
            """INSERT INTO lf_workroom_intake_events
               (lead_id, prospect_id, customer_id, email, full_name, phone, firm_name,
                city_region, job_type, message, measure_notes, photo_urls, source,
                utm_campaign, capture_channel, consent_contact, business, tags)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 'workroom', ?)""",
            (
                lead_id,
                prospect_id,
                customer_id,
                payload["email"],
                payload["full_name"],
                payload["phone"],
                payload["firm_name"],
                payload["city_region"],
                payload["job_type"],
                payload["message"],
                payload["measure_notes"],
                json.dumps(payload["photo_urls"]),
                payload["source"],
                payload["utm_campaign"],
                payload["capture_channel"],
                json.dumps(tags),
            ),
        )
        event_id = int(cur.lastrowid)
        activity = (
            f"source={payload['source']}; utm={payload['utm_campaign'] or ''}; "
            f"job_type={payload['job_type']}; capture={payload['capture_channel']}\n{notes}"
        )
        conn.execute(
            """INSERT INTO lf_activities
               (lead_id, type, channel, subject, content, ai_generated, status, completed_at)
               VALUES (?, 'note', ?, ?, ?, 0, 'completed', datetime('now'))""",
            (
                lead_id,
                payload["capture_channel"],
                f"Workroom brief from {payload['full_name']}",
                activity,
            ),
        )
        events_for_email = _event_count(conn, payload["email"])
        conn.execute(
            "UPDATE lf_workroom_intake_events SET notified_at = datetime('now') WHERE id = ?",
            (event_id,),
        )

    notice = _notify_founder(event_id, payload, lead_id, customer_id)
    prefill = quote_prefill_from_payload(payload)
    return {
        "lead_id": lead_id,
        "prospect_id": prospect_id,
        "customer_id": customer_id,
        "event_id": event_id,
        "business": BUSINESS,
        "capture_channel": payload["capture_channel"],
        "crm_outcome": crm_outcome,
        "lead_outcome": lead_outcome,
        "prospect_outcome": prospect_outcome,
        "events_for_email": events_for_email,
        "source": payload["source"],
        "utm_campaign": payload["utm_campaign"],
        "tags": tags,
        "notified": notice["notified"],
        "notification": notice,
        "quote_prefill": prefill,
        "contact": WORKROOM_CONTACT,
        "quote_path": f"/api/v1/leadforge/intake/{lead_id}/quote",
    }


def get_workroom_lead(lead_id: int) -> dict:
    with _db() as conn:
        ensure_schema(conn)
        lead = _row(conn.execute("SELECT * FROM lf_leads WHERE id = ?", (lead_id,)).fetchone())
        if not lead or lead.get("business_unit") != BUSINESS:
            raise IntakeError(404, f"Workroom lead {lead_id} not found")
        event = _load_event(conn, lead_id)
        customer = None
        if lead.get("customer_id"):
            customer = _row(
                conn.execute("SELECT * FROM customers WHERE id = ?", (lead["customer_id"],)).fetchone()
            )
        prospect = None
        if event and event.get("prospect_id"):
            prospect = _row(
                conn.execute("SELECT * FROM prospects WHERE id = ?", (event["prospect_id"],)).fetchone()
            )
        events = [
            _row(row)
            for row in conn.execute(
                "SELECT * FROM lf_workroom_intake_events WHERE lead_id = ? ORDER BY id",
                (lead_id,),
            ).fetchall()
        ]
    prefill = quote_prefill_from_payload(_payload_from_event(event)) if event else None
    return {
        "lead": lead,
        "customer": customer,
        "prospect": prospect,
        "events": events,
        "source": lead.get("source"),
        "utm_campaign": lead.get("utm_campaign"),
        "quote_prefill": prefill,
        "business": BUSINESS,
        "contact": WORKROOM_CONTACT,
    }


async def create_workroom_quote_from_lead(lead_id: int) -> dict:
    """Open a Workroom quote through the existing quotes router."""
    record = get_workroom_lead(lead_id)
    event = (record.get("events") or [None])[-1]
    if not event or not record.get("quote_prefill"):
        raise IntakeError(404, f"Workroom lead {lead_id} has no brief to quote")

    if event.get("quote_id"):
        from app.routers import quotes as quotes_mod

        try:
            existing = quotes_mod._load_quote(event["quote_id"])
            return {
                "status": "existing",
                "quote_id": existing.get("id"),
                "quote_number": existing.get("quote_number"),
                "quote": existing,
                "lead_id": lead_id,
                "customer_id": record["lead"].get("customer_id"),
                "business": BUSINESS,
            }
        except Exception:
            pass

    prefill = record["quote_prefill"]
    from app.routers import quotes as quotes_mod

    payload = quotes_mod.QuoteCreate(
        customer_name=prefill["customer_name"],
        customer_email=prefill["customer_email"],
        customer_phone=prefill["customer_phone"],
        customer_address=prefill["customer_address"],
        project_name=prefill["project_name"],
        project_description=prefill["project_description"],
        notes=prefill["notes"],
        business_unit=BUSINESS,
        valid_days=prefill["valid_days"],
        line_items=prefill["line_items"],
    )
    result = await quotes_mod.create_quote(payload)
    quote = result.get("quote") or {}
    quote["photos"] = prefill["photos"]
    quote["customer_id"] = record["lead"].get("customer_id")
    quote["lead_id"] = lead_id
    quote["intake_event_id"] = event["id"]
    quote["capture_channel"] = prefill["capture_channel"]
    quote["job_type"] = prefill["job_type"]
    quote["measure_notes"] = prefill["measure_notes"]
    quote["business_unit"] = BUSINESS
    quotes_mod._save_quote(quote)

    with _db() as conn:
        ensure_schema(conn)
        conn.execute(
            "UPDATE lf_workroom_intake_events SET quote_id = ? WHERE id = ?",
            (quote.get("id"), event["id"]),
        )
        conn.execute(
            """INSERT INTO lf_activities
               (lead_id, type, channel, subject, content, ai_generated, status, completed_at)
               VALUES (?, 'proposal_sent', 'workroom', ?, ?, 0, 'completed', datetime('now'))""",
            (
                lead_id,
                f"Workroom quote {quote.get('quote_number')}",
                f"Prefilled from lead #{lead_id} for {prefill['customer_email']}",
            ),
        )

    return {
        "status": "created",
        "quote_id": quote.get("id"),
        "quote_number": quote.get("quote_number"),
        "quote": quote,
        "lead_id": lead_id,
        "customer_id": record["lead"].get("customer_id"),
        "business": BUSINESS,
        "prefill": {
            "customer_name": quote.get("customer_name"),
            "customer_email": quote.get("customer_email"),
            "customer_phone": quote.get("customer_phone"),
            "notes": quote.get("notes"),
            "photos": quote.get("photos") or [],
            "business_unit": quote.get("business_unit"),
        },
    }
