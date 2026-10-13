"""Simli session + lip-sync timing.

The API key never leaves this process. Lip-sync offset is always published
so voice sessions can delay local playback to match the mouth, even when
SIMLI_API_KEY is unset (TalkingHead still needs the same delay if the
parent plays TTS while the iframe animates).
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.services.simli_lipsync import (
    AUDIO_FORMAT,
    LIVE_VOICE_SAMPLE_RATE,
    SIMLI_SAMPLE_RATE,
    align_pcm_for_simli,
    apply_lip_sync_offset,
    attach_lipsync,
    estimate_word_timestamps,
    lipsync_payload,
)

router = APIRouter()


class AlignIn(BaseModel):
    """PCM as base64 is optional; timestamps-only alignment is enough for tests."""
    pcm_b64: str = ""
    from_rate: int = LIVE_VOICE_SAMPLE_RATE
    text: str = ""
    duration_seconds: float = 0
    timestamps: Optional[list[dict[str, Any]]] = None
    apply_offset_to_timestamps: bool = True


def _require_avatar_access(request: Request) -> None:
    try:
        from app.services.max.voice_live import authorize_websocket
    except Exception:
        return
    ok, _via, _user = authorize_websocket(request, surface="http")
    if not ok:
        raise HTTPException(status_code=401, detail="unauthorized")


@router.get("/avatar/simli/lipsync")
async def simli_lipsync_config():
    """Public timing contract. No secrets. No session mint."""
    return lipsync_payload(surface="simli")


@router.get("/avatar/simli/status")
async def simli_avatar_status(request: Request, edition: str = Query("workroom")):
    del edition
    _require_avatar_access(request)
    try:
        from app.services.max.simli_avatar import running_avatar_edition, simli_status

        status = simli_status(running_avatar_edition())
    except Exception:
        status = {
            "enabled": False,
            "status": "disabled",
            "renderer": "talkinghead",
            "reason": "Simli session module is not on this checkout. Lip-sync offset still applies.",
            "fallback": "talkinghead",
            "audio_format": AUDIO_FORMAT,
            "sample_rate": SIMLI_SAMPLE_RATE,
        }
    return attach_lipsync(status, surface="simli")


@router.post("/avatar/simli/align")
async def simli_align_audio(body: AlignIn):
    """Resample / chunk PCM and shift word times for a voice session."""
    pcm = b""
    if body.pcm_b64:
        import base64

        try:
            pcm = base64.b64decode(body.pcm_b64)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="invalid pcm_b64") from exc
    if pcm:
        aligned = align_pcm_for_simli(pcm, body.from_rate)
    else:
        timing = lipsync_payload()
        aligned = {
            "sample_rate": SIMLI_SAMPLE_RATE,
            "audio_format": AUDIO_FORMAT,
            "bytes": 0,
            "samples": 0,
            "duration_ms": 0.0,
            "chunk_bytes": 6000,
            "chunk_count": 0,
            "chunks": [],
            "playback_delay_ms": timing["playback_delay_ms"],
            "lip_sync_offset_ms": timing["lip_sync_offset_ms"],
        }
    duration_s = body.duration_seconds or (aligned["duration_ms"] / 1000.0)
    words = body.timestamps or estimate_word_timestamps(body.text, duration_s, offset_seconds=0.0)
    if body.apply_offset_to_timestamps and not body.timestamps:
        # Client that plays immediately: mouth cues start after the delay.
        words = apply_lip_sync_offset(words)
    elif body.apply_offset_to_timestamps and body.timestamps:
        words = apply_lip_sync_offset(body.timestamps)
    # Do not echo raw PCM chunks in the HTTP response (payload size).
    public = {k: v for k, v in aligned.items() if k != "chunks"}
    public["timestamps"] = words
    public["lipsync"] = lipsync_payload(surface="simli")
    return public


class SessionIn(BaseModel):
    edition: str = "workroom"


class UsageIn(BaseModel):
    edition: str = "workroom"
    seconds: float = Field(default=0)
    source: str = "simli"


@router.post("/avatar/simli/session")
async def simli_avatar_session(body: SessionIn, request: Request):
    _require_avatar_access(request)
    try:
        from app.services.max.simli_avatar import create_session, running_avatar_edition

        result = await create_session(running_avatar_edition())
    except Exception:
        result = {
            "enabled": False,
            "session_token": "",
            "ice_servers": [],
            "reason": "Simli session module is not on this checkout.",
            "renderer": "talkinghead",
        }
    return attach_lipsync(result, surface="simli")


@router.get("/avatar/simli/usage")
async def simli_avatar_usage(request: Request, edition: str = Query("")):
    del edition
    _require_avatar_access(request)
    try:
        from app.services.max.simli_avatar import running_avatar_edition, usage_card

        card = usage_card(running_avatar_edition())
    except Exception:
        card = {"minutes": 0, "seconds": 0, "sessions": 0, "simli_enabled": False}
    return attach_lipsync(card, surface="simli")


@router.post("/avatar/simli/usage")
async def simli_avatar_usage_log(body: UsageIn, request: Request):
    _require_avatar_access(request)
    try:
        from app.services.max.simli_avatar import record_usage, running_avatar_edition

        entry = record_usage(running_avatar_edition(), body.seconds, body.source)
    except Exception:
        entry = {"seconds": 0, "minutes": 0, "source": body.source}
    return attach_lipsync(entry, surface="simli")
