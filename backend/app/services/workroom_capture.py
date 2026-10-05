"""Workroom manual capture — one door from inbox to LeadForge, ForgeCRM, and a quote draft.

Same field set as the LeadForge Workroom intake spec. This service does not
send email, Telegram, or any other outbound message. The founder replies
from the workroom mailbox by hand.

Idempotency: one ForgeCRM customer per email (case-insensitive). Each submit
creates a new lead event and a new intake row, so two emails from the same
designer stay two events on one contact.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from app.db.database import resolve_task_db_path

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
CONSENT_VALUES = ("yes", "no", "unknown")
INTAKE_STATUSES = (
    "new",
    "needs_info",
    "quoting",
    "quoted",
    "won",
    "lost",
    "hold",
)
DEFAULT_CAMPAIGN = "workroom_national_48h"
DEFAULT_OWNER = "Rafael"
BUSINESS = "workroom"
GMAIL_SEARCH = (
    "https://mail.google.com/mail/u/0/#search/to%3Aworkroom%40empirebox.store"
)

JOB_LABELS = {
    "drapery_romans": "Drapery / Romans",
    "banquette": "Banquette",
    "soft_seating": "Soft seating",
    "headboard": "Headboard",
    "mixed": "Mixed workroom job",
    "other": "Workroom job",
}

_LEAD_STATUS = {
    "new": "new",
    "needs_info": "nurture",
    "quoting": "qualified",
    "quoted": "proposal_sent",
    "won": "won",
    "lost": "lost",
    "hold": "nurture",
}

_SCHEMA = """
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
);

CREATE TABLE IF NOT EXISTS lf_leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_unit TEXT NOT NULL DEFAULT 'empire_saas',
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
    score INTEGER DEFAULT 0,
    score_factors TEXT DEFAULT '{}',
    status TEXT DEFAULT 'new',
    temperature TEXT DEFAULT 'cold',
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
    lead_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    channel TEXT,
    subject TEXT,
    content TEXT,
    ai_generated INTEGER DEFAULT 0,
    status TEXT DEFAULT 'completed',
    scheduled_at TEXT,
    completed_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS lf_workroom_intakes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    received_at TEXT NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT,
    firm_name TEXT,
    city_region TEXT,
    job_type TEXT NOT NULL,
    message TEXT NOT NULL,
    photo_urls TEXT DEFAULT '[]',
    source TEXT NOT NULL,
    utm_campaign TEXT,
    consent_contact TEXT NOT NULL,
    business TEXT NOT NULL DEFAULT 'workroom',
    campaign TEXT NOT NULL DEFAULT 'workroom_national_48h',
    owner TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    last_contacted_at TEXT,
    next_action TEXT,
    crm_contact_id TEXT,
    lead_id INTEGER,
    quote_id TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_lf_workroom_intakes_email
    ON lf_workroom_intakes(email);
"""


class CaptureError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def _db_path() -> str:
    path = resolve_task_db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    try:
        from app.db import database

        database.DB_PATH = path
    except Exception:
        pass
    try:
        from app.routers import leadforge

        leadforge.DB_PATH = path
    except Exception:
        pass
    return path


@contextmanager
def _db():
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        _ensure(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _ensure(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(lf_leads)").fetchall()}
    if "customer_id" not in cols:
        conn.execute("ALTER TABLE lf_leads ADD COLUMN customer_id TEXT")


def _clean(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _require_choice(value: Optional[str], allowed: tuple, field: str) -> str:
    text = (_clean(value) or "").lower()
    if text not in allowed:
        raise CaptureError(400, f"{field} must be one of: {', '.join(allowed)}")
    return text


def _split_name(full_name: str) -> tuple[str, Optional[str]]:
    parts = full_name.split()
    first = parts[0]
    last = " ".join(parts[1:]) or None
    return first, last


def _photo_list(value) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        parts = value.replace(",", "\n").splitlines()
    elif isinstance(value, list):
        parts = value
    else:
        raise CaptureError(400, "photo_urls must be a list of links")
    urls = []
    for part in parts:
        text = _clean(str(part))
        if text:
            urls.append(text)
    if len(urls) > 20:
        raise CaptureError(400, "photo_urls accepts at most 20 links")
    return urls


def _intake_from_row(row: sqlite3.Row) -> dict:
    data = dict(row)
    raw = data.get("photo_urls") or "[]"
    try:
        data["photo_urls"] = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError:
        data["photo_urls"] = []
    return data


def _links(intake_id: int, quote_id: Optional[str] = None) -> dict:
    return {
        "capture": f"/workroom/capture?intake={intake_id}",
        "quote": f"/quote/{quote_id}" if quote_id else None,
        "gmail_search": GMAIL_SEARCH,
    }


def _envelope(intake: dict, **extra) -> dict:
    return {
        "intake": intake,
        "lead_id": intake.get("lead_id"),
        "customer_id": intake.get("crm_contact_id"),
        "quote_id": intake.get("quote_id"),
        "outbound_email": "not_sent",
        "notification": "in_app_only",
        "idempotency": "one_crm_contact_per_email_new_lead_event_per_submit",
        "links": _links(intake["id"], intake.get("quote_id")),
        **extra,
    }


def _log_activity(conn, lead_id: int, activity_type: str, channel: str, subject: str, content: str) -> None:
    conn.execute(
        """INSERT INTO lf_activities
           (lead_id, type, channel, subject, content, ai_generated, status, completed_at)
           VALUES (?,?,?,?,?,0,'completed', datetime('now'))""",
        (lead_id, activity_type, channel, subject, content),
    )


def _upsert_customer(conn, payload: dict) -> tuple[str, str]:
    email = payload["email"]
    existing = conn.execute(
        "SELECT * FROM customers WHERE LOWER(email) = LOWER(?) LIMIT 1",
        (email,),
    ).fetchone()
    if existing:
        conn.execute(
            """UPDATE customers
               SET phone = CASE WHEN COALESCE(phone, '') = '' THEN ? ELSE phone END,
                   company = CASE WHEN COALESCE(company, '') = '' THEN ? ELSE company END,
                   address = CASE WHEN COALESCE(address, '') = '' THEN ? ELSE address END,
                   business = CASE
                       WHEN COALESCE(business, '') IN ('', 'empire') THEN 'workroom'
                       ELSE business
                   END,
                   updated_at = datetime('now')
               WHERE id = ?""",
            (
                payload.get("phone"),
                payload.get("firm_name"),
                payload.get("city_region"),
                existing["id"],
            ),
        )
        return existing["id"], "matched"

    import secrets

    customer_id = secrets.token_hex(8)
    conn.execute(
        """INSERT INTO customers
           (id, name, email, phone, address, company, type, tags, notes, source, business)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (
            customer_id,
            payload["full_name"],
            email,
            payload.get("phone"),
            payload.get("city_region"),
            payload.get("firm_name"),
            "designer",
            json.dumps(["business:workroom", f"campaign:{payload['campaign']}"]),
            "Workroom manual capture. No outbound email was sent.",
            payload["source"],
            BUSINESS,
        ),
    )
    return customer_id, "created"


def _insert_lead(conn, payload: dict, customer_id: str) -> int:
    first, last = _split_name(payload["full_name"])
    tags = [
        "business:workroom",
        f"campaign:{payload['campaign']}",
        f"job_type:{payload['job_type']}",
        f"consent:{payload['consent_contact']}",
    ]
    if payload.get("utm_campaign"):
        tags.append(f"utm:{payload['utm_campaign']}")
    notes = payload["message"]
    if payload.get("notes"):
        notes = f"{notes}\n\n{payload['notes']}"
    cur = conn.execute(
        """INSERT INTO lf_leads
           (business_unit, first_name, last_name, company, email, phone, city,
            source, source_url, score, score_factors, status, temperature,
            estimated_value, assigned_to, tags, notes, next_action, customer_id)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            BUSINESS,
            first,
            last,
            payload.get("firm_name"),
            payload["email"],
            payload.get("phone"),
            payload.get("city_region"),
            payload["source"],
            payload.get("utm_campaign"),
            0,
            "{}",
            "new",
            "warm",
            0,
            payload.get("owner") or DEFAULT_OWNER,
            json.dumps(tags),
            notes,
            payload.get("next_action"),
            customer_id,
        ),
    )
    return int(cur.lastrowid)


def normalize_intake(data: dict) -> dict:
    """Validate one capture payload. Missing optional fields stay empty."""
    full_name = _clean(data.get("full_name"))
    if not full_name:
        raise CaptureError(400, "full_name is required")
    email = _clean(data.get("email"))
    if not email or "@" not in email or email.startswith("@") or email.endswith("@"):
        raise CaptureError(400, "email is required")
    message = _clean(data.get("message"))
    if not message:
        raise CaptureError(400, "message is required")

    business = (_clean(data.get("business")) or BUSINESS).lower()
    if business != BUSINESS:
        raise CaptureError(400, "This door only accepts business=workroom")

    campaign = _clean(data.get("campaign")) or DEFAULT_CAMPAIGN
    owner = _clean(data.get("owner")) or DEFAULT_OWNER
    next_action = _clean(data.get("next_action")) or (
        "Acknowledge the designer today and collect measures, fabric, photos, and install date."
    )
    return {
        "received_at": _clean(data.get("received_at")) or datetime.utcnow().isoformat(timespec="seconds"),
        "full_name": full_name,
        "email": email,
        "phone": _clean(data.get("phone")),
        "firm_name": _clean(data.get("firm_name")),
        "city_region": _clean(data.get("city_region")),
        "job_type": _require_choice(data.get("job_type"), JOB_TYPES, "job_type"),
        "message": message,
        "photo_urls": _photo_list(data.get("photo_urls")),
        "source": _require_choice(data.get("source"), SOURCES, "source"),
        "utm_campaign": _clean(data.get("utm_campaign")),
        "consent_contact": _require_choice(data.get("consent_contact"), CONSENT_VALUES, "consent_contact"),
        "business": BUSINESS,
        "campaign": campaign,
        "owner": owner,
        "next_action": next_action,
        "notes": _clean(data.get("notes")),
    }


def create_intake(data: dict) -> dict:
    payload = normalize_intake(data)
    with _db() as conn:
        customer_id, crm_outcome = _upsert_customer(conn, payload)
        lead_id = _insert_lead(conn, payload, customer_id)
        activity_type = "social_dm" if payload["source"] in {"instagram", "houzz"} else "email_received"
        channel = "social" if activity_type == "social_dm" else "email"
        _log_activity(
            conn,
            lead_id,
            activity_type,
            channel,
            f"Workroom inbound ({payload['source']})",
            payload["message"],
        )
        cur = conn.execute(
            """INSERT INTO lf_workroom_intakes
               (received_at, full_name, email, phone, firm_name, city_region, job_type,
                message, photo_urls, source, utm_campaign, consent_contact, business,
                campaign, owner, status, next_action, crm_contact_id, lead_id, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'new',?,?,?,?)""",
            (
                payload["received_at"],
                payload["full_name"],
                payload["email"],
                payload["phone"],
                payload["firm_name"],
                payload["city_region"],
                payload["job_type"],
                payload["message"],
                json.dumps(payload["photo_urls"]),
                payload["source"],
                payload["utm_campaign"],
                payload["consent_contact"],
                BUSINESS,
                payload["campaign"],
                payload["owner"],
                payload["next_action"],
                customer_id,
                lead_id,
                payload["notes"],
            ),
        )
        row = conn.execute(
            "SELECT * FROM lf_workroom_intakes WHERE id = ?",
            (cur.lastrowid,),
        ).fetchone()
    intake = _intake_from_row(row)
    return _envelope(intake, crm_outcome=crm_outcome, lead_event="created")


def list_intakes(status: Optional[str] = None, limit: int = 50) -> dict:
    if status:
        status = _require_choice(status, INTAKE_STATUSES, "status")
    limit = max(1, min(int(limit or 50), 200))
    with _db() as conn:
        if status:
            rows = conn.execute(
                """SELECT * FROM lf_workroom_intakes
                   WHERE status = ? ORDER BY received_at DESC, id DESC LIMIT ?""",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM lf_workroom_intakes
                   ORDER BY received_at DESC, id DESC LIMIT ?""",
                (limit,),
            ).fetchall()
    intakes = [_intake_from_row(row) for row in rows]
    return {
        "intakes": intakes,
        "total": len(intakes),
        "outbound_email": "not_sent",
        "gmail_search": GMAIL_SEARCH,
        "schema": {
            "job_type": list(JOB_TYPES),
            "source": list(SOURCES),
            "consent_contact": list(CONSENT_VALUES),
            "status": list(INTAKE_STATUSES),
            "business": BUSINESS,
            "campaign": DEFAULT_CAMPAIGN,
        },
    }


def get_intake(intake_id: int) -> dict:
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM lf_workroom_intakes WHERE id = ?",
            (intake_id,),
        ).fetchone()
    if not row:
        raise CaptureError(404, f"Intake {intake_id} not found")
    return _envelope(_intake_from_row(row))


def update_intake(intake_id: int, data: dict) -> dict:
    """Record triage progress. Does not send email."""
    status = data.get("status")
    if status is not None:
        status = _require_choice(status, INTAKE_STATUSES, "status")
    sets = []
    params = []
    if status is not None:
        sets.append("status = ?")
        params.append(status)
    for field in ("next_action", "notes", "owner", "last_contacted_at"):
        if field in data and data[field] is not None:
            sets.append(f"{field} = ?")
            params.append(_clean(data[field]))
    if not sets:
        raise CaptureError(400, "No fields to update")
    sets.append("updated_at = datetime('now')")
    params.append(intake_id)
    with _db() as conn:
        existing = conn.execute(
            "SELECT * FROM lf_workroom_intakes WHERE id = ?",
            (intake_id,),
        ).fetchone()
        if not existing:
            raise CaptureError(404, f"Intake {intake_id} not found")
        conn.execute(
            f"UPDATE lf_workroom_intakes SET {', '.join(sets)} WHERE id = ?",
            params,
        )
        if status and existing["lead_id"]:
            conn.execute(
                "UPDATE lf_leads SET status = ?, updated_at = datetime('now') WHERE id = ?",
                (_LEAD_STATUS[status], existing["lead_id"]),
            )
        if data.get("last_contacted_at") and existing["lead_id"]:
            conn.execute(
                """UPDATE lf_leads
                   SET last_contacted = ?, updated_at = datetime('now')
                   WHERE id = ?""",
                (_clean(data["last_contacted_at"]), existing["lead_id"]),
            )
            _log_activity(
                conn,
                existing["lead_id"],
                "note",
                "internal",
                "Founder recorded contact",
                "last_contacted_at updated from the manual capture page. No email was sent by this action.",
            )
        row = conn.execute(
            "SELECT * FROM lf_workroom_intakes WHERE id = ?",
            (intake_id,),
        ).fetchone()
    return _envelope(_intake_from_row(row))


def _quote_dir() -> Path:
    from app.services.data_paths import quotes_data_dir

    path = quotes_data_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _next_quote_number(qdir: Path) -> str:
    year = datetime.utcnow().year
    prefix = f"EST-{year}-"
    seq = 0
    counter_path = qdir / "_counter.json"
    if counter_path.exists():
        try:
            counter = json.loads(counter_path.read_text())
            if counter.get("year") == year:
                seq = int(counter.get("seq") or 0)
        except (json.JSONDecodeError, TypeError, ValueError):
            seq = 0
    for fname in qdir.glob("*.json"):
        if fname.name.startswith("_") or "_verification" in fname.name:
            continue
        try:
            number = json.loads(fname.read_text()).get("quote_number") or ""
        except (json.JSONDecodeError, OSError):
            continue
        if number.startswith(prefix):
            try:
                seq = max(seq, int(number.rsplit("-", 1)[-1]))
            except ValueError:
                continue
    seq += 1
    counter_path.write_text(json.dumps({"year": year, "seq": seq}))
    return f"{prefix}{seq:03d}"


def _quote_brief(intake: dict) -> str:
    photos = intake.get("photo_urls") or []
    photo_block = "\n".join(f"- {url}" for url in photos) if photos else "- none yet"
    utm = intake.get("utm_campaign") or "—"
    firm = intake.get("firm_name") or "—"
    city = intake.get("city_region") or "—"
    return (
        f"Workroom manual capture #{intake['id']}\n"
        f"Source: {intake['source']}\n"
        f"Campaign: {intake['campaign']}\n"
        f"UTM: {utm}\n"
        f"Consent to contact: {intake['consent_contact']}\n"
        f"Firm: {firm}\n"
        f"City/region: {city}\n"
        f"Job type: {intake['job_type']}\n"
        f"Owner: {intake.get('owner') or DEFAULT_OWNER}\n\n"
        f"Brief:\n{intake['message']}\n\n"
        f"Photo links:\n{photo_block}\n\n"
        "Still needed before a real price: piece and job type, measures, "
        "fabric or COM, finish, install location, photos, and install date.\n"
        "Opened by the founder from manual capture. No email was sent."
    )


def _public_quote(quote: dict) -> dict:
    return {
        "id": quote.get("id"),
        "quote_number": quote.get("quote_number"),
        "status": quote.get("status"),
        "customer_name": quote.get("customer_name"),
        "customer_email": quote.get("customer_email"),
        "customer_phone": quote.get("customer_phone"),
        "customer_address": quote.get("customer_address"),
        "project_name": quote.get("project_name"),
        "project_description": quote.get("project_description"),
        "notes": quote.get("notes"),
        "business_unit": quote.get("business_unit"),
        "source": quote.get("source"),
        "utm_campaign": quote.get("utm_campaign"),
        "photo_urls": quote.get("photo_urls") or [],
        "customer_id": quote.get("customer_id"),
        "capture_intake_id": quote.get("capture_intake_id"),
    }


def open_workroom_quote(intake_id: int) -> dict:
    """Open a draft Workroom quote prefilled from the intake. Does not send it."""
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM lf_workroom_intakes WHERE id = ?",
            (intake_id,),
        ).fetchone()
        if not row:
            raise CaptureError(404, f"Intake {intake_id} not found")
        intake = _intake_from_row(row)
        qdir = _quote_dir()
        if intake.get("quote_id"):
            existing_path = qdir / f"{intake['quote_id']}.json"
            if existing_path.exists():
                quote = json.loads(existing_path.read_text())
                return _envelope(
                    intake,
                    quote_outcome="already_open",
                    quote=_public_quote(quote),
                )

        import uuid

        now = datetime.utcnow().isoformat(timespec="seconds")
        quote_id = uuid.uuid4().hex[:8]
        quote_number = _next_quote_number(qdir)
        brief = _quote_brief(intake)
        quote = {
            "id": quote_id,
            "quote_number": quote_number,
            "status": "draft",
            "customer_name": intake["full_name"],
            "customer_email": intake["email"],
            "customer_phone": intake.get("phone") or "",
            "customer_address": intake.get("city_region") or "",
            "customer_id": intake.get("crm_contact_id"),
            "project_name": JOB_LABELS.get(intake["job_type"], "Workroom job"),
            "project_description": intake["message"],
            "line_items": [
                {
                    "description": "Scope pending — measures and fabric not priced",
                    "quantity": 1,
                    "unit": "ea",
                    "rate": 0,
                    "amount": 0,
                    "category": "labor",
                }
            ],
            "subtotal": 0,
            "tax_rate": 0,
            "tax_amount": 0,
            "discount_amount": 0,
            "discount_type": "dollar",
            "total": 0,
            "deposit": 0,
            "terms": (
                "Draft from Workroom manual capture. "
                "Price after measures, fabric, and install date are confirmed."
            ),
            "valid_days": 30,
            "notes": brief,
            "business_unit": BUSINESS,
            "business_name": "Empire Workroom",
            "pricing_mode": "flat",
            "source": intake["source"],
            "utm_campaign": intake.get("utm_campaign"),
            "photo_urls": intake.get("photo_urls") or [],
            "capture_intake_id": intake_id,
            "created_at": now,
            "updated_at": now,
            "sent_at": None,
            "accepted_at": None,
            "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat(timespec="seconds"),
        }
        (qdir / f"{quote_id}.json").write_text(json.dumps(quote, indent=2))
        next_action = (
            "Price the draft quote, then reply from the workroom mailbox. "
            "This page does not send email."
        )
        conn.execute(
            """UPDATE lf_workroom_intakes
               SET quote_id = ?, status = 'quoting', next_action = ?,
                   updated_at = datetime('now')
               WHERE id = ?""",
            (quote_id, next_action, intake_id),
        )
        if intake.get("lead_id"):
            conn.execute(
                """UPDATE lf_leads
                   SET status = 'qualified', next_action = ?, updated_at = datetime('now')
                   WHERE id = ?""",
                (next_action, intake["lead_id"]),
            )
            _log_activity(
                conn,
                intake["lead_id"],
                "note",
                "internal",
                f"Workroom quote draft {quote_number}",
                f"quote_id={quote_id}. Draft only. No email was sent.",
            )
        saved = conn.execute(
            "SELECT * FROM lf_workroom_intakes WHERE id = ?",
            (intake_id,),
        ).fetchone()
    return _envelope(
        _intake_from_row(saved),
        quote_outcome="created",
        quote=_public_quote(quote),
    )
