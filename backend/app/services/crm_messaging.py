"""
ForgeCRM unified WhatsApp/SMS thread.

Invariants (hard):
  * One thread per customer, WhatsApp + SMS in a single timeline.
  * Inbound messages are stored and displayed. Ingest never replies.
  * Outbound messages are ALWAYS created as drafts.
  * Sending requires an explicit owner approve on THAT message.
  * No automatic replies. Ever.
  * After approve, transport is sandbox-local only (no live WhatsApp/SMS).
"""
from __future__ import annotations

import json
import re
import secrets
from datetime import datetime, timezone
from typing import Optional

from app.db.database import dict_row, dict_rows

CHANNELS = frozenset({"whatsapp", "sms"})
INBOUND_STATUS = "received"
OUTBOUND_DRAFT = "draft"
OUTBOUND_APPROVED = "approved"
OUTBOUND_SENT = "sent_sandbox"
OUTBOUND_REJECTED = "rejected"
OUTBOUND_BLOCKED = "blocked"

POLICY = {
    "unified_thread": True,
    "channels": ["whatsapp", "sms"],
    "inbound_displayed": True,
    "outbound_default": "draft",
    "owner_approval_required": True,
    "approval_scope": "per_message",
    "automatic_replies": False,
    "live_send": False,
    "transport": "sandbox_local",
}

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS crm_threads (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    customer_id TEXT NOT NULL UNIQUE,
    phone_digits TEXT,
    last_inbound_at TEXT,
    last_outbound_at TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE IF NOT EXISTS crm_thread_messages (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    thread_id TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    channel TEXT NOT NULL CHECK (channel IN ('whatsapp', 'sms')),
    direction TEXT NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    body TEXT NOT NULL,
    status TEXT NOT NULL,
    auto_generated INTEGER NOT NULL DEFAULT 0,
    approved_at TEXT,
    approved_by TEXT,
    sent_at TEXT,
    rejected_at TEXT,
    provider_message_id TEXT,
    from_address TEXT,
    to_address TEXT,
    metadata_json TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (thread_id) REFERENCES crm_threads(id),
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE INDEX IF NOT EXISTS idx_crm_threads_customer ON crm_threads(customer_id);
CREATE INDEX IF NOT EXISTS idx_crm_threads_phone ON crm_threads(phone_digits);
CREATE INDEX IF NOT EXISTS idx_crm_msgs_thread ON crm_thread_messages(thread_id, created_at);
CREATE INDEX IF NOT EXISTS idx_crm_msgs_customer ON crm_thread_messages(customer_id, created_at);
CREATE INDEX IF NOT EXISTS idx_crm_msgs_provider ON crm_thread_messages(provider_message_id);
"""


class CrmMessagingError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def ensure_schema(conn) -> None:
    conn.executescript(SCHEMA_SQL)


def normalize_phone(raw: Optional[str]) -> str:
    if not raw:
        return ""
    return re.sub(r"\D+", "", str(raw))


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_meta(raw: Optional[str]) -> dict:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def serialize_message(row: dict) -> dict:
    meta = _parse_meta(row.get("metadata_json"))
    return {
        "id": row["id"],
        "thread_id": row["thread_id"],
        "customer_id": row["customer_id"],
        "channel": row["channel"],
        "direction": row["direction"],
        "body": row["body"],
        "status": row["status"],
        "auto_generated": bool(row.get("auto_generated")),
        "approved_at": row.get("approved_at"),
        "approved_by": row.get("approved_by"),
        "sent_at": row.get("sent_at"),
        "rejected_at": row.get("rejected_at"),
        "provider_message_id": row.get("provider_message_id"),
        "from_address": row.get("from_address"),
        "to_address": row.get("to_address"),
        "metadata": meta,
        "created_at": row.get("created_at"),
        "needs_owner_approval": (
            row.get("direction") == "outbound" and row.get("status") == OUTBOUND_DRAFT
        ),
        "live_send": False,
    }


def _get_customer(conn, customer_id: str) -> dict:
    row = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
    if not row:
        raise CrmMessagingError("Customer not found", 404)
    return dict_row(row)


def get_or_create_thread(conn, customer_id: str, phone_hint: Optional[str] = None) -> dict:
    ensure_schema(conn)
    customer = _get_customer(conn, customer_id)
    phone = normalize_phone(phone_hint or customer.get("phone"))
    existing = conn.execute(
        "SELECT * FROM crm_threads WHERE customer_id = ?", (customer_id,)
    ).fetchone()
    if existing:
        thread = dict_row(existing)
        if phone and not thread.get("phone_digits"):
            conn.execute(
                "UPDATE crm_threads SET phone_digits = ?, updated_at = datetime('now') WHERE id = ?",
                (phone, thread["id"]),
            )
            thread["phone_digits"] = phone
        return thread
    thread_id = secrets.token_hex(8)
    conn.execute(
        """INSERT INTO crm_threads (id, customer_id, phone_digits)
           VALUES (?, ?, ?)""",
        (thread_id, customer_id, phone or None),
    )
    return dict_row(
        conn.execute(
            "SELECT * FROM crm_threads WHERE id = ?", (thread_id,)
        ).fetchone()
    )


def find_customer_by_phone(conn, phone: str) -> Optional[dict]:
    digits = normalize_phone(phone)
    if len(digits) < 7:
        return None
    ensure_schema(conn)
    thread = conn.execute(
        "SELECT customer_id FROM crm_threads WHERE phone_digits = ?", (digits,)
    ).fetchone()
    if thread:
        return _get_customer(conn, thread["customer_id"])
    rows = conn.execute("SELECT * FROM customers WHERE phone IS NOT NULL").fetchall()
    for row in rows:
        cust = dict_row(row)
        if normalize_phone(cust.get("phone")) == digits:
            return cust
    suffix = digits[-10:] if len(digits) >= 10 else digits
    for row in rows:
        cust = dict_row(row)
        other = normalize_phone(cust.get("phone"))
        if other and (other.endswith(suffix) or suffix.endswith(other)):
            return cust
    return None


def list_messages(conn, thread_id: str) -> list[dict]:
    rows = dict_rows(
        conn.execute(
            """SELECT * FROM crm_thread_messages
               WHERE thread_id = ?
               ORDER BY created_at ASC, rowid ASC""",
            (thread_id,),
        ).fetchall()
    )
    return [serialize_message(r) for r in rows]


def get_thread_payload(conn, customer_id: str) -> dict:
    thread = get_or_create_thread(conn, customer_id)
    messages = list_messages(conn, thread["id"])
    inbound = [m for m in messages if m["direction"] == "inbound"]
    drafts = [m for m in messages if m["needs_owner_approval"]]
    return {
        "thread": {
            "id": thread["id"],
            "customer_id": thread["customer_id"],
            "phone_digits": thread.get("phone_digits"),
            "created_at": thread.get("created_at"),
            "updated_at": thread.get("updated_at"),
        },
        "messages": messages,
        "counts": {
            "total": len(messages),
            "inbound": len(inbound),
            "outbound_drafts": len(drafts),
            "outbound_sent": len([m for m in messages if m["status"] == OUTBOUND_SENT]),
        },
        "policy": POLICY,
    }


def list_threads(conn, limit: int = 100) -> list[dict]:
    ensure_schema(conn)
    rows = dict_rows(
        conn.execute(
            """SELECT t.*, c.name AS customer_name, c.phone AS customer_phone,
                      (SELECT COUNT(*) FROM crm_thread_messages m
                        WHERE m.thread_id = t.id AND m.direction = 'inbound') AS inbound_count,
                      (SELECT COUNT(*) FROM crm_thread_messages m
                        WHERE m.thread_id = t.id AND m.status = 'draft') AS draft_count,
                      (SELECT body FROM crm_thread_messages m
                        WHERE m.thread_id = t.id
                        ORDER BY m.created_at DESC, m.id DESC LIMIT 1) AS last_body
               FROM crm_threads t
               JOIN customers c ON c.id = t.customer_id
               ORDER BY t.updated_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
    )
    return rows


def ingest_inbound(
    conn,
    *,
    channel: str,
    body: str,
    from_address: str,
    to_address: Optional[str] = None,
    customer_id: Optional[str] = None,
    provider_message_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> dict:
    """Store an incoming WhatsApp/SMS message. NEVER replies."""
    channel = (channel or "").strip().lower()
    if channel not in CHANNELS:
        raise CrmMessagingError("channel must be whatsapp or sms")
    text = (body or "").strip()
    if not text:
        raise CrmMessagingError("body is required")

    if provider_message_id:
        existing = conn.execute(
            "SELECT * FROM crm_thread_messages WHERE provider_message_id = ?",
            (provider_message_id,),
        ).fetchone()
        if existing:
            return {
                "message": serialize_message(dict_row(existing)),
                "created": False,
                "auto_reply": False,
                "auto_reply_sent": False,
                "policy": POLICY,
            }

    customer = None
    if customer_id:
        customer = _get_customer(conn, customer_id)
    else:
        customer = find_customer_by_phone(conn, from_address)
    if not customer:
        raise CrmMessagingError("No customer matched this phone number", 404)

    thread = get_or_create_thread(conn, customer["id"], from_address)
    now = _now()
    message_id = secrets.token_hex(8)
    meta = {
        "source": "inbound_webhook",
        "auto_reply": False,
        **(metadata or {}),
    }
    conn.execute(
        """INSERT INTO crm_thread_messages
           (id, thread_id, customer_id, channel, direction, body, status,
            auto_generated, provider_message_id, from_address, to_address, metadata_json)
           VALUES (?, ?, ?, ?, 'inbound', ?, ?, 0, ?, ?, ?, ?)""",
        (
            message_id,
            thread["id"],
            customer["id"],
            channel,
            text,
            INBOUND_STATUS,
            provider_message_id,
            from_address,
            to_address,
            json.dumps(meta),
        ),
    )
    conn.execute(
        """UPDATE crm_threads
           SET last_inbound_at = ?, updated_at = datetime('now')
           WHERE id = ?""",
        (now, thread["id"]),
    )
    row = dict_row(
        conn.execute(
            "SELECT * FROM crm_thread_messages WHERE id = ?",
            (message_id,),
        ).fetchone()
    )
    return {
        "message": serialize_message(row),
        "created": True,
        "auto_reply": False,
        "auto_reply_sent": False,
        "reply": None,
        "policy": POLICY,
    }


def compose_draft(
    conn,
    *,
    customer_id: str,
    body: str,
    channel: str = "sms",
    to_address: Optional[str] = None,
) -> dict:
    """Create an outbound DRAFT. Does not send. Does not auto-approve."""
    channel = (channel or "sms").strip().lower()
    if channel not in CHANNELS:
        raise CrmMessagingError("channel must be whatsapp or sms")
    text = (body or "").strip()
    if not text:
        raise CrmMessagingError("body is required")

    thread = get_or_create_thread(conn, customer_id, to_address)
    message_id = secrets.token_hex(8)
    meta = {
        "source": "owner_compose",
        "auto_reply": False,
        "live_send": False,
        "requires_owner_approval": True,
    }
    conn.execute(
        """INSERT INTO crm_thread_messages
           (id, thread_id, customer_id, channel, direction, body, status,
            auto_generated, to_address, from_address, metadata_json)
           VALUES (?, ?, ?, ?, 'outbound', ?, ?, 0, ?, 'owner', ?)""",
        (
            message_id,
            thread["id"],
            customer_id,
            channel,
            text,
            OUTBOUND_DRAFT,
            to_address or thread.get("phone_digits"),
            json.dumps(meta),
        ),
    )
    conn.execute(
        "UPDATE crm_threads SET updated_at = datetime('now') WHERE id = ?",
        (thread["id"],),
    )
    row = dict_row(
        conn.execute(
            "SELECT * FROM crm_thread_messages WHERE id = ?",
            (message_id,),
        ).fetchone()
    )
    return {
        "message": serialize_message(row),
        "sent": False,
        "status": OUTBOUND_DRAFT,
        "policy": POLICY,
    }


def _load_outbound(conn, message_id: str, customer_id: Optional[str] = None) -> dict:
    ensure_schema(conn)
    row = conn.execute(
        "SELECT * FROM crm_thread_messages WHERE id = ?", (message_id,)
    ).fetchone()
    if not row:
        raise CrmMessagingError("Message not found", 404)
    msg = dict_row(row)
    if customer_id and msg["customer_id"] != customer_id:
        raise CrmMessagingError("Message not found", 404)
    if msg["direction"] != "outbound":
        raise CrmMessagingError("Only outbound drafts can be approved or rejected")
    return msg


def reject_draft(conn, message_id: str, customer_id: Optional[str] = None) -> dict:
    msg = _load_outbound(conn, message_id, customer_id)
    if msg["status"] != OUTBOUND_DRAFT:
        raise CrmMessagingError(f"Message is {msg['status']}, not a draft")
    now = _now()
    conn.execute(
        """UPDATE crm_thread_messages
           SET status = ?, rejected_at = ?
           WHERE id = ?""",
        (OUTBOUND_REJECTED, now, message_id),
    )
    updated = dict_row(
        conn.execute("SELECT * FROM crm_thread_messages WHERE id = ?", (message_id,)).fetchone()
    )
    return {"message": serialize_message(updated), "sent": False, "policy": POLICY}


def approve_and_sandbox_send(
    conn,
    message_id: str,
    *,
    customer_id: Optional[str] = None,
    owner_id: str = "owner",
) -> dict:
    """Owner-explicit per-message approve. Sandbox transport only. No live send."""
    owner = (owner_id or "").strip()
    if not owner:
        raise CrmMessagingError("owner_id is required for approval")

    msg = _load_outbound(conn, message_id, customer_id)
    if msg["status"] != OUTBOUND_DRAFT:
        raise CrmMessagingError(
            f"Message is {msg['status']}; only drafts can be approved",
        )
    if msg.get("auto_generated"):
        raise CrmMessagingError("Auto-generated outbound messages are forbidden", 409)

    now = _now()
    meta = _parse_meta(msg.get("metadata_json"))
    meta.update(
        {
            "approved": True,
            "transport": "sandbox_local",
            "live_send": False,
            "auto_reply": False,
        }
    )
    conn.execute(
        """UPDATE crm_thread_messages
           SET status = ?, approved_at = ?, approved_by = ?, sent_at = ?, metadata_json = ?
           WHERE id = ?""",
        (OUTBOUND_SENT, now, owner, now, json.dumps(meta), message_id),
    )
    conn.execute(
        """UPDATE crm_threads
           SET last_outbound_at = ?, updated_at = datetime('now')
           WHERE id = ?""",
        (now, msg["thread_id"]),
    )
    updated = dict_row(
        conn.execute("SELECT * FROM crm_thread_messages WHERE id = ?", (message_id,)).fetchone()
    )
    return {
        "message": serialize_message(updated),
        "sent": True,
        "live_send": False,
        "transport": "sandbox_local",
        "policy": POLICY,
    }


def send_without_approval_blocked(conn, message_id: str) -> dict:
    """Guard used by any send-shaped route: refuse unless already approved."""
    msg = _load_outbound(conn, message_id)
    if msg["status"] == OUTBOUND_DRAFT:
        raise CrmMessagingError(
            "Owner must explicitly approve this draft before sending",
            403,
        )
    if msg["status"] == OUTBOUND_SENT:
        return {"message": serialize_message(msg), "already_sent": True, "live_send": False}
    raise CrmMessagingError(f"Message cannot be sent from status {msg['status']}", 403)


def assert_no_auto_reply(result: dict) -> None:
    if result.get("auto_reply") or result.get("auto_reply_sent") or result.get("reply"):
        raise CrmMessagingError("Automatic replies are forbidden", 409)


def webhook_ingest_only(result: dict) -> dict:
    """Strip any reply-shaped keys so inbound handlers cannot leak a send."""
    assert_no_auto_reply(result)
    return {
        "ok": True,
        "stored": True,
        "created": result.get("created", True),
        "message": result.get("message"),
        "auto_reply": False,
        "auto_reply_sent": False,
        "reply": None,
        "policy": POLICY,
    }
