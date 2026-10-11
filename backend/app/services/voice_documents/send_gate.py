"""Drafts never email or send unless a caller passes confirmed=True."""
from __future__ import annotations

from typing import Any, Callable, Optional


class DraftSendBlocked(PermissionError):
    """Raised when a send is attempted without explicit confirmation."""


def assert_may_send(*, confirmed: bool, auto_send: bool = False) -> None:
    """Block every send that is not an explicit confirmation.

    Edition config cannot turn auto_send on. The flag is recorded so a
    future edition cannot silently flip it.
    """
    if auto_send:
        raise DraftSendBlocked("edition auto_send is disabled")
    if confirmed is not True:
        raise DraftSendBlocked(
            "drafts are not emailed or sent without explicit confirmation"
        )


def deliver_client_email(
    *,
    to: str,
    subject: str,
    html_body: str,
    confirmed: bool,
    sender: Optional[Callable[..., Any]] = None,
) -> dict:
    """Send only after assert_may_send. Default sender is the house mailer."""
    assert_may_send(confirmed=confirmed, auto_send=False)
    recipient = (to or "").strip()
    if not recipient:
        return {"sent": False, "reason": "no recipient"}
    if sender is None:
        from app.services.email.sender import send_email

        sender = send_email
    result = sender(recipient, subject, html_body)
    return {"sent": bool(result), "to": recipient}
