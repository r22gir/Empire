"""Chief e support webhook + inbound reply for family editions.

Extends the existing Pedir ayuda / family-help ticket store. Tickets stay
in this edition's own inbox (never Workroom / Rafael's DB). Creating a
ticket optionally POSTs a JSON payload to SUPPORT_WEBHOOK_URL. Chief e
posts replies back to POST /api/support/tickets/{ticket_id}/reply using
SUPPORT_REPLY_SECRET. No email is sent from this bridge.
"""
from __future__ import annotations

import hmac
import os
import uuid
from typing import Any, Optional

from app.edition import AMP_COACH_NAME, MAXINE_OWNER_NAME, edition_name, is_family_edition
from app.services.family_help import _connect, _iso, edition_owner_name, get_ticket, redact_text

DEFAULT_AUTH_HEADER = "Authorization: Bearer <key>"


def webhook_edition_label(edition: Optional[str] = None) -> str:
    key = (edition or edition_name() or "").strip().lower()
    if key == "amp":
        return "max-e"
    return key or "max-e"


def webhook_brother(edition: Optional[str] = None) -> str:
    key = (edition or edition_name() or "").strip().lower()
    if key == "amp":
        return AMP_COACH_NAME
    if key == "maxine":
        return MAXINE_OWNER_NAME
    return edition_owner_name(key)


def webhook_auth_header(key: str) -> tuple[str, str]:
    """Parse SUPPORT_WEBHOOK_AUTH_HEADER.

    Default template is ``Authorization: Bearer <key>``. A bare header name
    (``Authorization`` or ``X-Support-Key``) sends the key as the value;
    ``Authorization`` alone still uses the Bearer prefix.
    """
    raw = (os.getenv("SUPPORT_WEBHOOK_AUTH_HEADER") or DEFAULT_AUTH_HEADER).strip()
    if not raw:
        raw = DEFAULT_AUTH_HEADER
    if "<key>" in raw:
        left, _sep, _right = raw.partition(":")
        if _sep:
            name = left.strip() or "Authorization"
            value = raw.split(":", 1)[1].strip().replace("<key>", key)
            return name, value
        return raw.replace("<key>", "").strip() or "Authorization", key
    if raw.lower() == "authorization":
        return "Authorization", f"Bearer {key}"
    return raw, key


def build_webhook_payload(ticket: dict) -> dict[str, Any]:
    edition = webhook_edition_label(ticket.get("edition"))
    return {
        "ticket_id": ticket.get("id") or "",
        "edition": edition,
        "brother": (ticket.get("sender") or webhook_brother(ticket.get("edition"))).strip(),
        "question": (ticket.get("message") or ticket.get("transcript") or "").strip(),
        "current_screen": (ticket.get("current_screen") or "").strip(),
        "last_error": (ticket.get("last_error") or "").strip(),
        "created_at": ticket.get("created_at") or "",
    }


def post_support_webhook(payload: dict) -> dict:
    url = (os.getenv("SUPPORT_WEBHOOK_URL") or "").strip()
    key = (os.getenv("SUPPORT_WEBHOOK_KEY") or "").strip()
    if not url or not key:
        return {"ok": False, "reason": "unconfigured"}
    name, value = webhook_auth_header(key)
    try:
        import httpx

        response = httpx.post(
            url,
            json=payload,
            headers={name: value, "Content-Type": "application/json"},
            timeout=10.0,
        )
        return {
            "ok": response.is_success,
            "status": response.status_code,
            "reason": None if response.is_success else (response.text or "")[:240],
        }
    except Exception as exc:
        return {"ok": False, "reason": str(exc)[:240]}


def notify_support_webhook(ticket: dict) -> dict:
    payload = build_webhook_payload(ticket)
    result = post_support_webhook(payload)
    ticket["support_webhook"] = result
    return result


def secrets_match(provided: str, expected: str) -> bool:
    """Constant-time compare; length mismatch still returns False."""
    left = (provided or "").encode("utf-8")
    right = (expected or "").encode("utf-8")
    if not right:
        return False
    if len(left) != len(right):
        hmac.compare_digest(right, right)
        return False
    return hmac.compare_digest(left, right)


def extract_reply_secret(authorization: Optional[str], extra: Optional[str] = None) -> str:
    auth = (authorization or "").strip()
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    if extra:
        return extra.strip()
    return auth


def verify_reply_secret(authorization: Optional[str] = None, extra: Optional[str] = None) -> bool:
    expected = (os.getenv("SUPPORT_REPLY_SECRET") or "").strip()
    provided = extract_reply_secret(authorization, extra)
    return secrets_match(provided, expected)


def add_inbound_reply(ticket_id: str, body: str, *, author: str = "Chief e") -> dict:
    """Append a reply on this edition's ticket only. No email, no founder gate."""
    if not is_family_edition():
        raise PermissionError("solo Max-e y Maxine reciben respuestas de Chief e aquí")
    ticket = get_ticket(ticket_id)
    if not ticket or ticket.get("edition") != edition_name():
        raise FileNotFoundError("ticket no encontrado")
    text = redact_text((body or "").strip(), edition=ticket["edition"])
    if not text:
        raise ValueError("la respuesta está vacía")
    now = _iso()
    reply_id = f"sr-{uuid.uuid4().hex[:10]}"
    conn = _connect(ticket["edition"])
    try:
        conn.execute(
            """
            INSERT INTO replies (id, ticket_id, author, body, draft, created_at, usage_tokens)
            VALUES (?, ?, ?, ?, 0, ?, 0)
            """,
            (reply_id, ticket_id, (author or "Chief e").strip() or "Chief e", text, now),
        )
        conn.execute(
            "UPDATE tickets SET status = 'answered', updated_at = ? WHERE id = ?",
            (now, ticket_id),
        )
        conn.commit()
    finally:
        conn.close()
    return get_ticket(ticket_id) or ticket
