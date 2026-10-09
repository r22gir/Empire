"""Verified founder session (main edition only).

2026-10-05: Rafael was blocked by the founder-PIN card on his own Studio
session. The PIN gate now steps aside when the request carries a
*verified* founder identity:

  * Cloudflare Access JWT (``Cf-Access-Jwt-Assertion`` header or the
    ``CF_Authorization`` cookie), signature/aud/iss/exp checked against
    the Access JWKS (same verifier Live Voice uses), and
  * the JWT email is in FOUNDER_ACCESS_EMAILS (fallback: FOUNDER_EMAIL).

Never trusted: the body ``channel`` field, ``chat_id``, any client flag,
or the plain ``Cf-Access-Authenticated-User-Email`` header on its own.
Family editions (EMPIRE_EDITION set to anything other than "main") never
get a founder session. Tool calls made after untrusted inbound content
entered the turn (email, web pages, WhatsApp/Telegram from others) lose
the bypass and go back to the PIN gate. Outbound sends keep their own
"no send without Rafael's yes" gates; this module does not touch them.
"""
from __future__ import annotations

import contextvars
import logging
import os
from typing import Any

logger = logging.getLogger("max.founder_session")

# Set by the HTTP chat endpoints for the duration of one request.
_CURRENT: contextvars.ContextVar[dict | None] = contextvars.ContextVar(
    "max_founder_session", default=None
)

# Tools whose results carry content written by someone other than Rafael.
# After one of these returns in a turn, restricted tools need the PIN again.
UNTRUSTED_CONTENT_TOOLS = frozenset({
    "check_email", "check_outlook", "web_read", "web_search", "search_images",
    "read_whatsapp", "whatsapp_inbox", "read_telegram", "search_conversations",
    "browse", "browser_read", "research", "deep_research",
})


def is_family_edition() -> bool:
    ed = (os.getenv("EMPIRE_EDITION") or "main").strip().lower()
    return ed not in ("", "main")


def founder_emails() -> set[str]:
    """Cloudflare Access logins that count as Rafael.

    FOUNDER_ACCESS_EMAILS (comma list, set in the systemd drop-in
    founder-access.conf) wins. Without it only FOUNDER_EMAIL counts.
    FOUNDER_EMAILS is NOT used: it also lists shared mailboxes
    (max@, workroom@) that are not a person's login.
    """
    raw = os.getenv("FOUNDER_ACCESS_EMAILS")
    if raw is None or not raw.strip():
        raw = os.getenv("FOUNDER_EMAIL") or ""
    return {p.strip().lower() for p in raw.split(",") if p.strip()}


def resolve_founder_session(http_request: Any) -> dict:
    """Return {"verified": bool, "email": str, "via": str, "why": str}.

    Never raises. Never logs the token.
    """
    out = {"verified": False, "email": "", "via": "", "why": ""}
    if http_request is None:
        out["why"] = "no http request"
        return out
    if is_family_edition():
        out["why"] = "family edition"
        return out
    try:
        headers = http_request.headers
        token = (headers.get("cf-access-jwt-assertion") or "").strip()
        if not token:
            token = (http_request.cookies.get("CF_Authorization") or "").strip()
    except Exception:
        token = ""
    if not token:
        out["why"] = "no Cloudflare Access token"
        return out
    try:
        from app.services.max.voice_live import verify_access_jwt
        ok, why, email = verify_access_jwt(token)
    except Exception as exc:  # verifier import/JWKS failure: fail closed
        out["why"] = f"verifier error ({type(exc).__name__})"
        return out
    email = (email or "").strip().lower()
    if not ok:
        out["why"] = why
        return out
    allowed = founder_emails()
    if not allowed or email not in allowed:
        out.update(email=email, why="access identity is not a founder email")
        return out
    out.update(verified=True, email=email, via="cloudflare_access", why="ok")
    return out


def set_current(session: dict | None):
    return _CURRENT.set(session)


def reset_current(token) -> None:
    try:
        _CURRENT.reset(token)
    except Exception:
        pass


def current() -> dict | None:
    return _CURRENT.get()


def current_verified() -> bool:
    s = _CURRENT.get()
    return bool(s and s.get("verified"))


def apply_to_access_context(ctx: dict | None, session: dict | None = None) -> dict | None:
    """Return an access context that carries the server-verified flag."""
    session = session if session is not None else _CURRENT.get()
    if not (session and session.get("verified")):
        return ctx
    new = dict(ctx or {})
    new["founder_session"] = True
    new["founder_session_email"] = session.get("email") or ""
    return new


def mark_untrusted(ctx: dict | None, tool_name: str | None) -> None:
    """Drop the founder-session bypass for the rest of the turn once
    content from outside (email, web, other people's messages) came in."""
    if isinstance(ctx, dict) and ctx.get("founder_session") and tool_name in UNTRUSTED_CONTENT_TOOLS:
        if not ctx.get("untrusted_content"):
            logger.info("Founder session: untrusted content from %s; restricted tools need the PIN for the rest of this turn", tool_name)
        ctx["untrusted_content"] = True


def founder_session_allows(access_context: dict | None, founder: bool) -> bool:
    """True when a restricted tool may run without the PIN."""
    if not founder or not isinstance(access_context, dict):
        return False
    if is_family_edition():
        return False
    return bool(access_context.get("founder_session") is True and not access_context.get("untrusted_content"))
