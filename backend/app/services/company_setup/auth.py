"""Founder-only gate for company setup and WhatsApp key routes.

Uses founder_session.resolve_founder_session / current_verified.
edition.py treats studio/workroom as founder; founder_session treats any
EMPIRE_EDITION other than main/empty as family. Studio still has to work.
"""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request

from app.edition import is_family_edition, is_founder_edition
from app.services.max import founder_session as fs


def _jwt_founder_session(request: Request) -> dict[str, Any]:
    """Same JWT + founder-email check as resolve_founder_session, no family gate."""
    out = {"verified": False, "email": "", "via": "", "why": ""}
    try:
        headers = request.headers
        token = (headers.get("cf-access-jwt-assertion") or "").strip()
        if not token:
            token = (request.cookies.get("CF_Authorization") or "").strip()
    except Exception:
        token = ""
    if not token:
        out["why"] = "no Cloudflare Access token"
        return out
    try:
        from app.services.max.voice_live import verify_access_jwt

        ok, why, email = verify_access_jwt(token)
    except Exception as exc:
        out["why"] = f"verifier error ({type(exc).__name__})"
        return out
    email = (email or "").strip().lower()
    if not ok:
        out["why"] = why
        return out
    allowed = fs.founder_emails()
    if not allowed or email not in allowed:
        out.update(email=email, why="access identity is not a founder email")
        return out
    out.update(verified=True, email=email, via="cloudflare_access", why="ok")
    return out


def require_verified_founder(request: Request) -> dict[str, Any]:
    """Raise 403 unless this request is a server-verified founder session."""
    session = fs.resolve_founder_session(request)
    if session.get("verified"):
        fs.set_current(session)
        if fs.current_verified():
            return session
    # Studio / workroom are founder editions. Re-check the JWT when
    # resolve_founder_session bailed only because EMPIRE_EDITION=studio.
    if is_founder_edition() and not is_family_edition():
        session = _jwt_founder_session(request)
        if session.get("verified"):
            fs.set_current(session)
            if fs.current_verified():
                return session
    raise HTTPException(status_code=403, detail="Founder session required")
