"""Portal resume for a PIN-gated tool call.

The Chat PIN card posts the founder PIN to /max/verify-pin and then
here. The PIN stays in the request body for those two calls only.
It is not written to chat history, the unified message store, or logs.
"""
from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from typing import Any

logger = logging.getLogger("max.restricted_tool_resume")

_LOCK = threading.Lock()
_PENDING: dict[str, dict[str, Any]] = {}
_TTL_SECONDS = 15 * 60
_PIN_KEYS = {"pin", "founder_pin", "password"}


def needs_founder_pin_card(error: str | None) -> bool:
    """True when Chat should show the PIN card for this tool error."""
    if not error:
        return False
    low = error.lower()
    if "unset" in low and "founder_pin" in low:
        return False
    return "founder pin" in low or "invalid pin" in low


def founder_pin_matches(pin: str | None) -> bool:
    """Same comparison as POST /max/verify-pin. Does not log the PIN."""
    expected = os.getenv("FOUNDER_PIN", "")
    if not expected:
        return False
    return str(pin or "") == expected


def redact_secret(text: str, secret: str | None) -> str:
    if not text or not secret:
        return text
    return text.replace(str(secret), "••••")


def _redact_obj(obj: Any, secret: str) -> Any:
    if isinstance(obj, str):
        return redact_secret(obj, secret)
    if isinstance(obj, dict):
        return {k: _redact_obj(v, secret) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact_obj(v, secret) for v in obj]
    return obj


def _prune(now: float) -> None:
    expired = [key for key, row in _PENDING.items() if now - float(row.get("at") or 0) > _TTL_SECONDS]
    for key in expired:
        _PENDING.pop(key, None)


def stash_restricted_call(
    *,
    tool_call: dict,
    desk: str | None,
    founder: bool,
    channel: str | None,
) -> str:
    """Remember the blocked call so the PIN card can resume it."""
    safe = {
        k: v for k, v in (tool_call or {}).items()
        if str(k).lower() not in _PIN_KEYS
    }
    resume_id = uuid.uuid4().hex
    now = time.time()
    with _LOCK:
        _prune(now)
        _PENDING[resume_id] = {
            "tool_call": safe,
            "desk": desk,
            "founder": bool(founder),
            "channel": channel,
            "at": now,
        }
    logger.info(
        "Stashed restricted tool %s for portal PIN resume %s",
        safe.get("tool"),
        resume_id,
    )
    return resume_id


def resume_restricted_tool(
    resume_id: str,
    pin: str | None,
    founder_session: dict | None = None,
) -> dict[str, Any]:
    """Verify the founder PIN and re-run the stashed tool call.

    2026-10-05: a server-verified founder session (see founder_session.py)
    resumes without the PIN. Returns a dict the HTTP layer can send. The
    PIN is never included.
    """
    session_ok = bool(founder_session and founder_session.get("verified"))
    if not session_ok:
        if not os.getenv("FOUNDER_PIN", ""):
            logger.critical(
                "FOUNDER_PIN env var is UNSET. Restricted-tool resume refuses "
                "until it is configured."
            )
        if not founder_pin_matches(pin):
            logger.warning("Restricted-tool resume rejected: invalid PIN")
            return {"ok": False, "status": "invalid_pin"}

    with _LOCK:
        pending = _PENDING.pop(resume_id, None)
    if not pending:
        logger.info("Restricted-tool resume %s expired or unknown", resume_id)
        return {"ok": False, "status": "missing"}

    from app.services.max.tool_executor import execute_tool

    if session_ok:
        from app.services.max.founder_session import apply_to_access_context
        ctx = apply_to_access_context({}, founder_session)
        founder_flag = True
    else:
        ctx = {"pin": pin}
        founder_flag = bool(pending.get("founder"))
    result = execute_tool(
        pending["tool_call"],
        desk=pending.get("desk"),
        access_context=ctx,
        founder=founder_flag,
        channel=pending.get("channel"),
    )
    secret = str(pin or "")
    payload = _redact_obj(result.to_dict(), secret)
    if isinstance(payload, dict):
        payload.pop("pin", None)
        payload["ok"] = True
        payload["status"] = "resumed"
    logger.info(
        "Resumed restricted tool %s (%s)",
        getattr(result, "tool", None),
        "ok" if getattr(result, "success", False) else "failed",
    )
    return payload if isinstance(payload, dict) else {"ok": True, "status": "resumed"}
