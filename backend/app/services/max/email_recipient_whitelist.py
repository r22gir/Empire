"""Hard outbound-recipient allowlist for MAX email tools.

HOTFIX 2026-07-16 (truth-gate hardening batch, item d):

  No MAX tool call may email a client / customer address under any
  circumstances. Outbound recipients are restricted to internal
  business addresses:

    - FOUNDER_EMAIL       (from .env)
    - WORKROOM_EMAIL      (from .env)
    - WOODCRAFT_EMAIL     (from .env)
    - any address listed in MAX_EMAIL_ALLOWED_RECIPIENTS (.env,
      comma-separated whitelist for additional internal addresses)

  An unset MAX_EMAIL_ALLOWED_RECIPIENTS is interpreted as 'no
  additional entries' — the three above remain allowed. There is NO
  path that opens the allowlist to non-founder/internal addresses;
  the user must explicitly add an address to the env var.

  The check happens INSIDE the executor (see tool_executor._send_email
  / _send_quote_email). Prompt guidance alone is insufficient per the
  audit directive.

  Failure mode: ToolResult(success=False, error='recipient_not_in_whitelist: <addr>').
  The error surfaces to the founder in the MAX chat as a clear,
  non-leaky refusal — no successful-send result object is ever
  returned for non-allowlisted recipients.
"""
from __future__ import annotations

import os
from typing import Iterable, Union
from email.utils import parseaddr


ENV_NAME = "MAX_EMAIL_ALLOWED_RECIPIENTS"

DEFAULT_ALLOWED_KEYS = (
    "FOUNDER_EMAIL",
    "WORKROOM_EMAIL",
    "WOODCRAFT_EMAIL",
)

# Hardcoded fail-closed internal addresses that are ALWAYS allowed in
# addition to the env-driven set. These exist because the env vars
# could be missing or empty in a misconfigured deploy; the audit
# directive requires fail-closed (NEVER send to client/customer),
# not fail-open.
_INTERNAL_FALLBACK_ADDRESSES = (
    "empirebox2026@gmail.com",  # FOUNDER_EMAIL default
    "workroom@empirebox.store",
    "woodcraft@empirebox.store",
)


def normalize_address(addr: str | None) -> str:
    """Extract + lowercase + strip the mailbox from a raw address."""
    if not addr:
        return ""
    _, address = parseaddr(addr)
    return (address or addr).strip().lower()


def _default_internal_addresses() -> set[str]:
    """Pull FOUNDER_EMAIL / WORKROOM_EMAIL / WOODCRAFT_EMAIL from env;
    fall back to the canonical internal defaults if any are missing.
    The result is ALWAYS a non-empty set so the allowlist is non-empty
    in every deploy state (fail-closed but usable)."""
    out: set[str] = set()
    for key in DEFAULT_ALLOWED_KEYS:
        a = normalize_address(os.getenv(key, ""))
        if a:
            out.add(a)
    # Always include the canonical defaults so a forgotten env var
    # doesn't silently disable emails to internal addresses.
    for a in _INTERNAL_FALLBACK_ADDRESSES:
        out.add(normalize_address(a))
    return out


def allowed_recipient_addresses() -> set[str]:
    """Returns the set of normalized recipient addresses that MAX is
    allowed to email. Always non-empty (fail-closed but usable)."""
    out = _default_internal_addresses()
    raw = os.getenv(ENV_NAME, "")
    for item in raw.split(","):
        a = normalize_address(item)
        if a:
            out.add(a)
    return out


def recipient_whitelist_status() -> dict:
    """Diagnostic — surfaces the whitelist state to /api/v1/system/*.
    Does not include any specific address (no leak)."""
    allowed = allowed_recipient_addresses()
    return {
        "email_recipient_whitelist_configured": bool(allowed),
        "allowed_recipient_count": len(allowed),
        "uses_env_var": ENV_NAME,
    }


def authorize_email_recipient(recipient: str | None) -> dict:
    """Authorize an OUTBOUND recipient address. Returns a structured
    verdict — the caller (send tool) MUST inspect `authorized` and
    refuse the send when False.

    The check is `recipient in allowed_recipient_addresses()` after
    normalization. We do NOT expose the allowlist in the error
    (information leak); we DO surface enough metadata for the
    founder to fix the misconfiguration."""
    address = normalize_address(recipient)
    allowed = allowed_recipient_addresses()
    configured = bool(allowed)
    authorized = bool(address and address in allowed)
    if authorized:
        reason = None
    elif not address:
        reason = "recipient_missing"
    elif not configured:
        # This shouldn't fire (allowed is non-empty in every state)
        # but defensively kept.
        reason = "recipient_whitelist_empty"
    else:
        reason = "recipient_not_in_whitelist"
    return {
        "recipient_address": address,
        "recipient_authorized": authorized,
        "blocked_reason": reason,
        "whitelist_configured": configured,
    }


def is_recipient_authorized(recipient: str | Iterable[str] | None) -> bool:
    """Convenience wrapper for the executor. Accepts a single address
    OR an iterable (for cc lists) — returns True iff EVERY address is
    authorized. Empty / None returns False (fail-closed)."""
    if recipient is None:
        return False
    if isinstance(recipient, str):
        return authorize_email_recipient(recipient)["recipient_authorized"]
    return all(
        authorize_email_recipient(a)["recipient_authorized"]
        for a in recipient
    )
