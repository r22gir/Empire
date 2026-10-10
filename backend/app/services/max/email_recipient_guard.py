"""IMP-0004 — Outbound email recipient lock (Rafael, 2026-10-10, mandatory).

MAX may send email ONLY to empirebox2026@gmail.com. No cc or bcc
(including rafa22giraldo@gmail.com), and never to clients or any other
address, from voice or any path, until Rafael explicitly says otherwise.

Enforced server-side in the send path: allowlist of exactly one address;
anything else — including cc/bcc/reply-to overrides — is rejected with a
clear error. Quotes/client emails remain drafts only. Non-founder calls keep
full safety (this lock applies to EVERYONE, founder sessions included).
"""
from __future__ import annotations

from email.utils import parseaddr


#: The single address MAX is allowed to send to. Lowercase canonical form.
FOUNDER_RECIPIENT_ALLOWLIST: frozenset[str] = frozenset({"empirebox2026@gmail.com"})

#: Human-readable allowlist for error messages (kept static on purpose —
#: never echo untrusted input back as if it were allowed).
ALLOWED_RECIPIENT_LABEL = "empirebox2026@gmail.com"


class RecipientRejected(ValueError):
    """Raised when an outbound email recipient violates the recipient lock."""


def normalize_address(raw: object) -> str:
    """Extract and normalize a single mailbox from a raw header value."""
    _display, address = parseaddr(str(raw or ""))
    candidate = (address or str(raw or "")).strip().lower()
    return candidate


def _split_candidates(raw: object) -> list[str]:
    """Split a To/Cc/Bcc value on common separators for multi-address check."""
    text = str(raw or "").strip()
    if not text:
        return []
    parts: list[str] = []
    for chunk in text.replace(";", ",").split(","):
        chunk = chunk.strip()
        if chunk:
            parts.append(chunk)
    return parts


def validate_outbound_email(
    to: object,
    cc: object = None,
    bcc: object = None,
    reply_to: object = None,
) -> str:
    """Validate an outbound send against the recipient lock.

    Returns the normalized allowed recipient on success.
    Raises RecipientRejected with a clear, safe error otherwise.

    Rules:
      - `to` must be exactly one address: empirebox2026@gmail.com
        (case-insensitive; display-name wrapping tolerated).
      - `cc` / `bcc` must be empty — no copies to anyone, ever.
      - `reply_to` per-call overrides are rejected (the sender's default
        Reply-To configured in env is unaffected; only explicit per-send
        overrides are blocked since they can redirect replies to clients).
    """
    candidates = _split_candidates(to)
    if not candidates:
        raise RecipientRejected("Email recipient is required")
    if len(candidates) > 1:
        raise RecipientRejected(
            "Multiple email recipients are not allowed: "
            f"MAX may only send to {ALLOWED_RECIPIENT_LABEL} "
            "(one recipient, no cc, no bcc)."
        )
    normalized = normalize_address(candidates[0])
    if not normalized or "@" not in normalized:
        raise RecipientRejected(
            f"Email to {candidates[0]!r} blocked: "
            f"MAX may only send to {ALLOWED_RECIPIENT_LABEL}."
        )
    if normalized not in FOUNDER_RECIPIENT_ALLOWLIST:
        raise RecipientRejected(
            f"Email to '{normalized}' blocked: MAX may only send to "
            f"{ALLOWED_RECIPIENT_LABEL} (founder lock). "
            "Quotes/client emails remain drafts only — nothing is sent to clients."
        )
    for label, value in (("cc", cc), ("bcc", bcc)):
        if str(value or "").strip():
            raise RecipientRejected(
                f"Email {label} is not allowed: MAX may only send to "
                f"{ALLOWED_RECIPIENT_LABEL} with no cc and no bcc."
            )
    if str(reply_to or "").strip():
        raise RecipientRejected(
            "Email reply-to overrides are not allowed: MAX may only send to "
            f"{ALLOWED_RECIPIENT_LABEL} with no reply-to overrides."
        )
    return normalized


def is_allowed_recipient(raw: object) -> bool:
    """Non-raising check: True only for the single allowlisted address."""
    try:
        validate_outbound_email(raw)
    except RecipientRejected:
        return False
    return True
