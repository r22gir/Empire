"""
Avatar API — MAX presentation mode voice & chat endpoints.
Three modes: full (TTS+lip-sync), compact (text only), text (text only).
Only 'full' mode incurs TTS cost. All interactions logged via token_tracker.
"""
import base64
import logging
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File as FileParam, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

logger = logging.getLogger("max.avatar")
router = APIRouter(prefix="/avatar", tags=["avatar"])

# PresentationScreen sends mode="presentation"; it is the voiced (TTS) mode,
# same as the legacy "full". Before 2026-09-29 only "full" triggered TTS, so
# the presentation avatar never spoke.
VOICED_MODES = {"full", "presentation", "voice"}


def _is_voiced(mode: Optional[str]) -> bool:
    return (mode or "").strip().lower() in VOICED_MODES


# ── Schemas ──────────────────────────────────────────────────────────

class SpeakRequest(BaseModel):
    text: str
    emotion: str = "neutral"  # neutral | happy | serious | thinking
    mode: str = "text"  # full | compact | text

class ChatRequest(BaseModel):
    message: str
    voice: bool = False
    channel: str = "avatar"
    mode: str = "text"  # full | compact | text

class SpeakResponse(BaseModel):
    text: str
    audio: Optional[str] = None  # base64 mp3 (only in full mode)
    timestamps: Optional[list] = None
    emotion: str = "neutral"

class ChatResponse(BaseModel):
    response: str
    audio: Optional[str] = None
    timestamps: Optional[list] = None
    emotion: str = "neutral"
    desk: str = "general"
    model_used: str = "none"


# ── Helpers ──────────────────────────────────────────────────────────

def _estimate_word_timestamps(text: str, audio_bytes: bytes) -> list:
    """Estimate word-level timestamps from text and audio duration.
    Assumes ~150 words/minute speaking rate for Rex voice."""
    words = text.split()
    if not words:
        return []
    # Estimate audio duration from mp3 size (~16kbps for speech)
    estimated_duration = len(audio_bytes) / 2000  # rough seconds estimate
    if estimated_duration < 0.5:
        estimated_duration = len(words) * 0.4  # fallback: 0.4s per word
    gap = estimated_duration / max(len(words), 1)
    timestamps = []
    for i, word in enumerate(words):
        timestamps.append({
            "word": word,
            "start": round(i * gap, 3),
            "end": round((i + 1) * gap, 3),
        })
    return timestamps


EMOTION_MAP = {
    "neutral": "neutral",
    "happy": "smile",
    "serious": "determined",
    "thinking": "look-up",
}


# ── Endpoints ────────────────────────────────────────────────────────

@router.post("/speak", response_model=SpeakResponse)
async def avatar_speak(req: SpeakRequest):
    """Generate speech for avatar. Only 'full' mode calls TTS (costs money)."""
    from app.services.max.token_tracker import token_tracker

    if not _is_voiced(req.mode):
        # Zero-cost: just return text
        token_tracker.log_usage(
            model="avatar-text", provider="local",
            input_tokens=0, output_tokens=0,
            endpoint="avatar/speak", feature="avatar",
            business="general", source="avatar_router",
        )
        return SpeakResponse(
            text=req.text,
            emotion=EMOTION_MAP.get(req.emotion, "neutral"),
        )

    # Full mode: call Grok TTS Rex
    from app.services.max.tts_service import tts_service

    audio_bytes = await tts_service.synthesize_for_web(req.text)
    if audio_bytes:
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        timestamps = _estimate_word_timestamps(req.text, audio_bytes)
        return SpeakResponse(
            text=req.text,
            audio=audio_b64,
            timestamps=timestamps,
            emotion=EMOTION_MAP.get(req.emotion, "neutral"),
        )

    # TTS failed — return text only
    logger.warning("TTS synthesis failed, returning text-only response")
    return SpeakResponse(
        text=req.text,
        emotion=EMOTION_MAP.get(req.emotion, "neutral"),
    )


@router.post("/chat", response_model=ChatResponse)
async def avatar_chat(req: ChatRequest):
    """Chat with MAX via avatar. Routes through AI router with cost tracking."""
    from app.services.max.ai_router import ai_router, AIMessage
    from app.services.max.token_tracker import token_tracker

    messages = [AIMessage(role="user", content=req.message)]
    ai_resp = await ai_router.chat(messages)

    response_text = ai_resp.content
    model_used = ai_resp.model_used

    audio_b64 = None
    timestamps = None

    # Only generate TTS in full mode with voice=True
    if req.voice and _is_voiced(req.mode):
        from app.services.max.tts_service import tts_service
        audio_bytes = await tts_service.synthesize_for_web(response_text[:500])
        if audio_bytes:
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
            timestamps = _estimate_word_timestamps(response_text[:500], audio_bytes)

    # Log avatar interaction
    sub_channel = "tts" if audio_b64 else "text"
    token_tracker.log_usage(
        model=f"avatar-{sub_channel}", provider="local" if sub_channel == "text" else "cloud",
        input_tokens=len(req.message) // 4, output_tokens=len(response_text) // 4,
        endpoint="avatar/chat", feature="avatar",
        business="general", source="avatar_router",
    )

    return ChatResponse(
        response=response_text,
        audio=audio_b64,
        timestamps=timestamps,
        emotion="neutral",
        desk="general",
        model_used=model_used,
    )


@router.post("/listen")
async def avatar_listen(file: UploadFile = FileParam(...), mode: str = "text"):
    """Transcribe audio and forward to avatar chat."""
    from app.services.max.stt_service import stt_service
    from pathlib import Path as _Path

    suffix = _Path(file.filename or "audio.webm").suffix or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = _Path(tmp.name)

    try:
        # Transcribe
        if stt_service.is_configured:
            transcript = await stt_service.transcribe(tmp_path)
        else:
            transcript = "[STT not configured — GROQ_API_KEY missing]"

        # Forward to chat
        chat_req = ChatRequest(message=transcript, voice=_is_voiced(mode), mode=mode)
        chat_resp = await avatar_chat(chat_req)

        return {
            "transcript": transcript,
            "response": chat_resp.response,
            "audio": chat_resp.audio,
            "timestamps": chat_resp.timestamps,
            "emotion": chat_resp.emotion,
            "model_used": chat_resp.model_used,
        }
    finally:
        tmp_path.unlink(missing_ok=True)


@router.get("/status")
async def avatar_status():
    """Return avatar system status."""
    from app.services.max.tts_service import tts_service
    from app.services.max.stt_service import stt_service

    return {
        "avatar_ready": True,
        "tts_service": "grok" if tts_service.is_configured else "none",
        "stt_service": "groq-whisper" if stt_service.is_configured else "none",
        "mode": "text",
        "voiced_modes": sorted(VOICED_MODES),
        "desks_active": 13,
        "quality_engine": True,
        "live_voice": _live_voice_status(),
    }


def _live_voice_status() -> dict:
    try:
        from app.services.max.voice_live import voice_status
        return voice_status()
    except Exception as exc:  # pragma: no cover - defensive
        return {"enabled": False, "reason": f"voice_live unavailable: {type(exc).__name__}"}


@router.websocket("/live")
async def avatar_live(websocket: WebSocket):
    """Live back-and-forth voice with MAX (xAI Grok realtime), /api/v1/avatar/live.

    Auth mirrors the Command Center: Cloudflare Access JWT when proxied through
    the tunnel, loopback otherwise. The xAI key never leaves the server.
    """
    from app.services.max.voice_live import authorize_websocket, handle_live_call

    try:
        ok, via, user = authorize_websocket(websocket)
    except Exception as exc:
        ok, via, user = False, f"auth error ({type(exc).__name__})", ""
    if not ok:
        logger.warning("avatar/live: rejected websocket (%s)", via)
        await websocket.close(code=4401, reason="unauthorized")
        return
    await websocket.accept()
    try:
        await handle_live_call(websocket, auth_via=via, user=user)
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
