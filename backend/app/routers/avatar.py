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

from fastapi import APIRouter, UploadFile, File as FileParam
from pydantic import BaseModel

logger = logging.getLogger("max.avatar")
router = APIRouter(prefix="/avatar", tags=["avatar"])


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

    if req.mode in ("text", "compact"):
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
    if req.voice and req.mode == "full":
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
        chat_req = ChatRequest(message=transcript, voice=(mode == "full"), mode=mode)
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
        "desks_active": 13,
        "quality_engine": True,
    }
