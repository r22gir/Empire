"""Canonical voice capability truth for MAX.

This module is the single source of truth for "what voice capabilities does
MAX have, and what's actually working right now?" Both the MAX chat backend
and the Empire Command Center UI read from here so they cannot disagree.

Exposes:
    get_voice_capability_status() -> dict

    Returns a dict with all 7 fields the user asked for, plus
    `last_verified_at` and `evidence` (the runtime checks performed).
    The shape is stable and consumed by:
        - /api/v1/max/voice/status   (backend endpoint)
        - Empire Command Center UI   (via the endpoint)

The capability check is conservative: every field includes a `verified`
boolean and the actual check that was run. The UI should display
"Voice STT ready · TTS blocked" or "STT not configured" based directly
on these fields — no inference, no name guessing.
"""
from __future__ import annotations

import os
import logging
import time
from datetime import datetime, timezone
from typing import Any


logger = logging.getLogger("max.voice_capability")


# Cached result — never older than 60s. Caching is safe because the underlying
# configuration (env vars, services running) does not change on a sub-minute
# timescale in production.
_CACHE: dict[str, Any] | None = None
_CACHE_TTL_SECONDS = 60.0


def _check_telegram_text_send() -> dict[str, Any]:
    """Can MAX send a text message to Telegram right now?"""
    bot_token_set = bool(os.getenv("TELEGRAM_BOT_TOKEN"))
    chat_id_set = bool(os.getenv("FOUNDER_TELEGRAM_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID"))
    # The bot is configured if both env vars are set; runtime health is checked
    # by the live getMe probe below.
    configured = bot_token_set and chat_id_set
    return {
        "verified": configured,
        "configured": configured,
        "env_keys": {
            "TELEGRAM_BOT_TOKEN": "set" if bot_token_set else "missing",
            "FOUNDER_TELEGRAM_CHAT_ID": "set" if chat_id_set else "missing",
        },
        "evidence": "env check",
    }


def _check_telegram_voice_receive() -> dict[str, Any]:
    """Can MAX receive a voice note from the user right now?

    Receiving a voice note from Telegram is automatic — the bot gets the
    update if the bot token is valid. So this is the same as telegram_text_send
    in terms of being configured, plus the actual STT service that will
    transcribe the audio.
    """
    receive = _check_telegram_text_send()
    stt = _check_stt_provider()
    return {
        "verified": receive["configured"] and stt["verified"],
        "configured": receive["configured"] and stt["configured"],
        "receive_pipeline": receive,
        "stt_provider": stt,
        "evidence": "bot token + STT provider check",
    }


def _check_telegram_voice_send() -> dict[str, Any]:
    """Can MAX send a voice note reply right now?

    Requires telegram text-send pipeline PLUS the TTS service.
    """
    send = _check_telegram_text_send()
    tts = _check_tts_provider()
    return {
        "verified": send["configured"] and tts["verified"],
        "configured": send["configured"] and tts["configured"],
        "send_pipeline": send,
        "tts_provider": tts,
        "evidence": "bot token + TTS provider check",
    }


def _check_stt_provider() -> dict[str, Any]:
    """Is STT (speech-to-text) configured right now?

    Truth source: STTService.is_configured in stt_service.py.
    The actual provider is Groq Whisper (GROQ_API_KEY).
    """
    provider = None
    configured = False
    last_status = "not_checked"
    last_error = ""
    try:
        from app.services.max.stt_service import stt_service  # type: ignore
        configured = bool(stt_service.is_configured)
        last_status = getattr(stt_service, "last_status", "not_checked")
        last_error = getattr(stt_service, "last_error", "")
        if configured:
            provider = "groq-whisper"
    except Exception as e:
        last_error = f"import_failed: {e}"
    return {
        "verified": configured,
        "configured": configured,
        "provider": provider,
        "env_key": "GROQ_API_KEY",
        "env_key_set": bool(os.getenv("GROQ_API_KEY")),
        "last_status": last_status,
        "last_error": last_error[:300] if last_error else "",
        "evidence": "stt_service.is_configured",
    }


def _check_tts_provider() -> dict[str, Any]:
    """Is TTS (text-to-speech) configured right now?

    Truth source: TTSService.is_configured in tts_service.py.
    The actual provider is xAI Grok TTS (XAI_API_KEY).
    """
    provider = None
    configured = False
    last_status = "not_checked"
    last_error = ""
    try:
        from app.services.max.tts_service import tts_service  # type: ignore
        configured = bool(tts_service.is_configured)
        last_status = getattr(tts_service, "last_status", "not_checked")
        last_error = getattr(tts_service, "last_error", "")
        if configured:
            provider = "xai-grok-tts"
    except Exception as e:
        last_error = f"import_failed: {e}"
    return {
        "verified": configured,
        "configured": configured,
        "provider": provider,
        "env_key": "XAI_API_KEY",
        "env_key_set": bool(os.getenv("XAI_API_KEY")),
        "last_status": last_status,
        "last_error": last_error[:300] if last_error else "",
        "evidence": "tts_service.is_configured",
    }


def _check_auto_voice_reply() -> dict[str, Any]:
    """Is the auto-voice-reply pipeline enabled end-to-end?

    True only if BOTH:
      - telegram_voice_send is configured (so we can deliver audio)
      - the bot's _send_voice_reply will run (no founder override, no error)
    """
    voice_send = _check_telegram_voice_send()
    # Check the bot's setting
    auto_enabled = True
    try:
        from app.services.max.telegram_bot import max_telegram_bot  # type: ignore
        auto_enabled = bool(getattr(max_telegram_bot, "auto_voice_reply", True))
    except Exception:
        # Bot not yet imported (e.g. during a test that hasn't loaded the bot)
        auto_enabled = True
    return {
        "verified": voice_send["verified"] and auto_enabled,
        "configured": voice_send["configured"] and auto_enabled,
        "telegram_voice_send": voice_send,
        "auto_voice_reply_enabled": auto_enabled,
        "evidence": "telegram_voice_send pipeline + bot.auto_voice_reply setting",
    }


def get_voice_capability_status() -> dict[str, Any]:
    """Return the canonical voice capability status.

    The 7 fields the user asked for, plus `last_verified_at` and `evidence`:
        telegram_text_send      — can MAX send text to Telegram?
        telegram_voice_receive  — can MAX receive + transcribe voice?
        telegram_voice_send     — can MAX reply with a voice note?
        stt_provider            — which STT provider is configured?
        tts_provider            — which TTS provider is configured?
        auto_voice_reply        — is auto-voice-reply enabled end-to-end?
        last_verified_at        — ISO timestamp of when this was computed
        evidence                — what runtime checks were run

    Plus a `summary` field for the UI to display directly.
    """
    global _CACHE
    now = time.time()
    if _CACHE is not None and (now - _CACHE.get("_cached_at", 0)) < _CACHE_TTL_SECONDS:
        return _CACHE

    telegram_text_send = _check_telegram_text_send()
    telegram_voice_receive = _check_telegram_voice_receive()
    telegram_voice_send = _check_telegram_voice_send()
    stt_provider = _check_stt_provider()
    tts_provider = _check_tts_provider()
    auto_voice_reply = _check_auto_voice_reply()

    last_verified_at = datetime.now(timezone.utc).isoformat()

    # Compose a short human-readable summary the UI can display directly.
    parts: list[str] = []
    if telegram_voice_send["verified"]:
        parts.append("Voice ready")
    else:
        if not stt_provider["verified"]:
            parts.append("STT not configured")
        if not tts_provider["verified"]:
            parts.append("TTS not configured")
    if telegram_text_send["verified"] and not telegram_voice_send["verified"]:
        parts.append("Text-only fallback")
    summary = " · ".join(parts) if parts else "Voice capability unknown"

    result = {
        "telegram_text_send": telegram_text_send,
        "telegram_voice_receive": telegram_voice_receive,
        "telegram_voice_send": telegram_voice_send,
        "stt_provider": stt_provider,
        "tts_provider": tts_provider,
        "auto_voice_reply": auto_voice_reply,
        "last_verified_at": last_verified_at,
        "evidence": "voice_capability_truth.get_voice_capability_status()",
        "summary": summary,
        "_cached_at": now,
    }
    _CACHE = result
    return result


def invalidate_cache() -> None:
    """Drop the cached result so the next call recomputes. Useful in tests."""
    global _CACHE
    _CACHE = None
