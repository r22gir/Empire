"""Owner-only family-help alerts for Rafael.

Juan (Max-e) and Camilo (Maxine) submit via 'Pedir ayuda a Max' / family-help.
Max notifies the owner only. Feature-flagged. No-op without credentials.
Reuses /data/{ed}/family-help/{ed}/help.db. Never writes to that store from tests
unless FAMILY_HELP_DB points at an isolated temp file.
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from pathlib import Path

from app.services.sprint_m.store import audit, get_store, now_iso, row_to_dict

OWNER_NAME = "Rafael"
OWNER_ROLE = "owner"

REQUESTER_AGENTS = {
    "juan": {"name": "Juan", "agent": "Max-e"},
    "juan diego": {"name": "Juan", "agent": "Max-e"},
    "max-e": {"name": "Juan", "agent": "Max-e"},
    "maxe": {"name": "Juan", "agent": "Max-e"},
    "camilo": {"name": "Camilo", "agent": "Maxine"},
    "maxine": {"name": "Camilo", "agent": "Maxine"},
}

ADJUST_WORDS = ("adjust", "ajuste", "change", "cambiar", "tweak", "fix measurement", "medida")
FIX_WORDS = ("fix", "arreglar", "broken", "bug", "error", "roto", "no funciona")
CREATE_WORDS = ("create", "crear", "new", "nuevo", "add", "agregar", "make")


def family_help_db_path() -> Path:
    override = os.getenv("FAMILY_HELP_DB")
    if override:
        return Path(override)
    ed = os.getenv("FAMILY_HELP_ED") or os.getenv("EMPIRE_ED") or "ed"
    return Path(f"/data/{ed}/family-help/{ed}/help.db")


def feature_enabled() -> bool:
    flag = (os.getenv("FAMILY_HELP_OWNER_ALERTS") or "").strip().lower()
    return flag in {"1", "true", "yes", "on"}


def owner_recipient() -> str | None:
    return (
        os.getenv("FAMILY_HELP_OWNER_PHONE")
        or os.getenv("OWNER_PHONE")
        or os.getenv("RAFAEL_PHONE")
        or None
    )


def owner_channel() -> str:
    raw = (os.getenv("FAMILY_HELP_OWNER_CHANNEL") or "sms").strip().lower()
    return "whatsapp" if raw in {"whatsapp", "wa"} else "sms"


def credentials_present(channel: str) -> bool:
    if channel == "whatsapp":
        return bool(
            os.getenv("WHATSAPP_ACCESS_TOKEN")
            or os.getenv("TWILIO_WHATSAPP_FROM")
            or os.getenv("FAMILY_HELP_WHATSAPP_TOKEN")
        )
    return bool(
        (os.getenv("TWILIO_ACCOUNT_SID") and os.getenv("TWILIO_AUTH_TOKEN"))
        or os.getenv("FAMILY_HELP_SMS_TOKEN")
    )


def classify_request(text: str) -> str:
    lowered = (text or "").lower()
    scores = {
        "adjust": sum(1 for w in ADJUST_WORDS if w in lowered),
        "fix": sum(1 for w in FIX_WORDS if w in lowered),
        "create": sum(1 for w in CREATE_WORDS if w in lowered),
    }
    if not any(scores.values()):
        return "adjust"
    return max(scores, key=scores.get)


def resolve_requester(raw: str | None) -> dict:
    key = (raw or "").strip().lower()
    return REQUESTER_AGENTS.get(key, {"name": raw or "family", "agent": "family-help"})


def ensure_help_schema(conn: sqlite3.Connection) -> None:
    """Compatible reader/writer for the family-help store. Isolated DBs only in tests."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS help_requests (
            id TEXT PRIMARY KEY,
            requester TEXT,
            requester_name TEXT,
            requester_agent TEXT,
            message TEXT,
            source TEXT DEFAULT 'family-help',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            classification TEXT,
            status TEXT DEFAULT 'open'
        )"""
    )
    conn.commit()


def _connect_help(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def submit_family_request(
    *,
    requester: str,
    message: str,
    source: str = "Pedir ayuda a Max",
    request_id: str | None = None,
) -> dict:
    """Write a family-help request into the (isolated or configured) help.db, then alert owner."""
    who = resolve_requester(requester)
    classification = classify_request(message)
    rid = request_id or str(uuid.uuid4())[:12]
    now = now_iso()
    path = family_help_db_path()
    conn = _connect_help(path)
    try:
        ensure_help_schema(conn)
        conn.execute(
            """INSERT INTO help_requests
               (id, requester, requester_name, requester_agent, message, source, created_at, classification, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open')""",
            (rid, requester, who["name"], who["agent"], message, source, now, classification),
        )
        conn.commit()
    finally:
        conn.close()
    return alert_owner_for_request(
        {
            "id": rid,
            "requester": who["name"],
            "requester_agent": who["agent"],
            "message": message,
            "classification": classification,
            "source": source,
        }
    )


def read_open_requests(limit: int = 20) -> list[dict]:
    path = family_help_db_path()
    if not path.exists():
        return []
    conn = _connect_help(path)
    try:
        ensure_help_schema(conn)
        rows = conn.execute(
            "SELECT * FROM help_requests ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [{k: r[k] for k in r.keys()} for r in rows]
    finally:
        conn.close()


def _delivery_decision() -> tuple[str, str | None, str | None, str | None]:
    """Return (status, channel, recipient, noop_reason). Recipient is owner only."""
    channel = owner_channel()
    recipient = owner_recipient()
    if not feature_enabled():
        return "noop", channel, recipient, "feature_flag_off"
    if not recipient:
        return "noop", channel, None, "missing_owner_recipient"
    if not credentials_present(channel):
        return "noop", channel, recipient, "missing_credentials"
    # Even when configured we do not actually transmit from this module.
    # Delivery is recorded as queued so a dedicated worker can send later.
    return "queued_not_sent", channel, recipient, None


def alert_owner_for_request(request: dict) -> dict:
    classification = request.get("classification") or classify_request(request.get("message") or "")
    summary = (
        f"{request.get('requester') or 'Family'} ({request.get('requester_agent') or 'family-help'}) "
        f"asked Max for help: {(request.get('message') or '')[:240]} "
        f"— needs a {classification} (adjust / fix / create)."
    )
    status, channel, recipient, noop_reason = _delivery_decision()
    alert_id = str(uuid.uuid4())[:12]
    now = now_iso()
    with get_store() as conn:
        conn.execute(
            """INSERT INTO sm_family_alerts (
                id, request_id, requester, requester_agent, summary, classification,
                needs, delivery_status, delivery_channel, recipient_role, recipient, noop_reason, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'owner', ?, ?, ?)""",
            (
                alert_id,
                request.get("id"),
                request.get("requester"),
                request.get("requester_agent"),
                summary,
                classification,
                classification,
                status,
                channel,
                recipient,
                noop_reason,
                now,
            ),
        )
        audit(conn, "family_alert", alert_id, status, "system", noop_reason)
    return {
        "id": alert_id,
        "request_id": request.get("id"),
        "requester": request.get("requester"),
        "requester_agent": request.get("requester_agent"),
        "summary": summary,
        "classification": classification,
        "needs": classification,
        "delivery_status": status,
        "delivery_channel": channel,
        "recipient_role": OWNER_ROLE,
        "recipient_name": OWNER_NAME,
        "recipient": recipient,
        "noop_reason": noop_reason,
        "owner_only": True,
        "sent_to_family": False,
        "max_sends_to_clients": False,
    }


def list_alerts(limit: int = 50) -> list[dict]:
    with get_store() as conn:
        rows = conn.execute(
            "SELECT * FROM sm_family_alerts ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    out = []
    for row in rows:
        item = row_to_dict(row)
        item["owner_only"] = True
        item["recipient_name"] = OWNER_NAME
        out.append(item)
    return out


def alert_status() -> dict:
    status, channel, recipient, noop_reason = _delivery_decision()
    return {
        "feature_enabled": feature_enabled(),
        "channel": channel,
        "recipient_role": OWNER_ROLE,
        "recipient_name": OWNER_NAME,
        "recipient_configured": bool(recipient),
        "credentials_present": credentials_present(channel),
        "family_help_db": str(family_help_db_path()),
        "delivery_would": status,
        "noop_reason": noop_reason,
        "owner_only": True,
        "amp_maxine_merged": False,
    }
