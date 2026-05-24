"""Runtime-configured sender authorization for MAX email intake."""
from __future__ import annotations

import os
from email.utils import parseaddr


ENV_NAME = "MAX_EMAIL_ALLOWED_SENDERS"


def normalize_sender_address(sender: str | None) -> str:
    """Extract and normalize the sender mailbox from a raw From value."""
    _display_name, address = parseaddr(sender or "")
    return (address or sender or "").strip().lower()


def allowed_sender_addresses() -> set[str]:
    """Return allowed sender mailboxes from runtime config.

    An unset or empty whitelist intentionally returns an empty set. Live email
    processing must treat that as a block, not as allow-all.
    """
    raw = os.getenv(ENV_NAME, "")
    senders: set[str] = set()
    for item in raw.split(","):
        normalized = normalize_sender_address(item)
        if normalized and "@" in normalized:
            senders.add(normalized)
    return senders


def sender_whitelist_status() -> dict:
    allowed = allowed_sender_addresses()
    return {
        "email_sender_whitelist_configured": bool(allowed),
        "allowed_sender_count": len(allowed),
    }


def authorize_email_sender(sender: str | None) -> dict:
    """Authorize an inbound email sender without exposing the allow-list."""
    address = normalize_sender_address(sender)
    allowed = allowed_sender_addresses()
    configured = bool(allowed)
    authorized = bool(address and address in allowed)
    if authorized:
        blocked_reason = None
    elif not configured:
        blocked_reason = "sender_whitelist_missing"
    else:
        blocked_reason = "non_whitelisted_sender"
    return {
        "sender_address": address,
        "sender_authorized": authorized,
        "blocked_reason": blocked_reason,
        "email_sender_whitelist_configured": configured,
        "allowed_sender_count": len(allowed),
    }
