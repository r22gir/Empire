"""PHASE 2 · F4-A — live channel status probe.

The model needs to know which outbound channels are live BEFORE it
offers to do something on a channel. Pre-F4, the model offered
"email or Telegram" because the compact prompt had no signal. The
capability registry (`email_send: enabled`) was a static claim, not
a live probe.

This module does the live probe and returns a short status line for
inclusion in every prompt path the doors use. The probe is real:
  - SMTP: TCP-connect to smtp.gmail.com:587 with a 3s timeout
  - Telegram: HTTPS GET to api.telegram.org/bot<TOKEN>/getMe
  - SendGrid: presence of SENDGRID_API_KEY env var

Cached for 60s so the prompt-build hot path is fast. Real failures
(SMTP down, Telegram bot deleted) propagate within the cache window.

The status line is intentionally at the top of the prompt so the
model sees it on every turn.
"""
from __future__ import annotations

import json
import logging
import os
import socket
import time
import urllib.request

logger = logging.getLogger("max.channel_probe")

_CACHE: dict = {"data": None, "expires": 0.0}
_TTL_SECONDS = 60


def _probe_smtp() -> bool:
    """SMTP path is configured AND reachable. No email is sent."""
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    if not (smtp_user and smtp_pass):
        return False
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        sock.connect(("smtp.gmail.com", 587))
        sock.close()
        return True
    except Exception as exc:
        logger.debug(f"[channel_probe] SMTP connect failed: {exc}")
        return False


def _probe_telegram() -> bool:
    """Telegram bot is configured AND getMe responds ok=true."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        return False
    try:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/getMe",
            timeout=3,
        )
        with urllib.request.urlopen(req) as resp:
            payload = json.loads(resp.read().decode() or "{}")
            return payload.get("ok", False) is True
    except Exception as exc:
        logger.debug(f"[channel_probe] Telegram getMe failed: {exc}")
        return False


def _probe_sendgrid() -> bool:
    """SendGrid API key is set. (Live API probe is rate-limited; the
    env-var check is the right granularity for the prompt status.)"""
    return bool(os.getenv("SENDGRID_API_KEY"))


def _probe_status() -> str:
    email = _probe_smtp()
    telegram = _probe_telegram()
    sendgrid = _probe_sendgrid()
    return (
        f"channels: email {'✓' if email else '✗'} · "
        f"telegram {'✓' if telegram else '✗'} · "
        f"sendgrid {'✓' if sendgrid else '✗'}"
    )


def channel_status_line() -> str:
    """Return the live channel-status line. Cached for 60s.

    Format: ``channels: email ✓ · telegram ✗ · sendgrid ✗``
    """
    now = time.time()
    if _CACHE["data"] and now < _CACHE["expires"]:
        return _CACHE["data"]
    try:
        status = _probe_status()
    except Exception as exc:
        logger.warning(f"[channel_probe] probe failed: {exc}")
        status = "channels: email ? · telegram ? · sendgrid ?"
    _CACHE["data"] = status
    _CACHE["expires"] = now + _TTL_SECONDS
    return status


def invalidate_cache() -> None:
    """Force the next call to re-probe. Useful for tests."""
    _CACHE["data"] = None
    _CACHE["expires"] = 0.0
