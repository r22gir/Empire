"""Voice notes → draft documents.

Spoken playback of a draft (avatar / Simli voice session) must use the same
lip-sync offset as ``/avatar/simli/lipsync``. Otherwise the mouth leads or
lags the TTS that reads the document back.

The full ingest pipeline lives on other checkouts. This router always
exposes the lip-sync contract and, when the pipeline is present, attaches
it to every document response.
"""
from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.services.simli_lipsync import (
    apply_lip_sync_offset,
    attach_lipsync,
    estimate_word_timestamps,
    lipsync_payload,
    pcm_duration_ms,
)

router = APIRouter()


class TranscriptIn(BaseModel):
    transcript: str = ""
    session_id: str = ""
    session_key: str = ""
    channel: str = "cc"
    edition: str = "workroom"


class ChoiceIn(BaseModel):
    option_id: str
    choice_id: str


class ConfirmIn(BaseModel):
    confirmed: bool = False
    to_email: str = ""


class SpokenIn(BaseModel):
    text: str = ""
    duration_seconds: float = 0
    timestamps: list[dict] | None = None


def spoken_document_lipsync(
    text: str,
    duration_seconds: float = 0,
    timestamps: list[dict] | None = None,
) -> dict:
    """Timing for reading a document aloud through the Simli / avatar face."""
    words = timestamps or estimate_word_timestamps(text, duration_seconds, offset_seconds=0.0)
    aligned = apply_lip_sync_offset(words)
    payload = lipsync_payload(surface="voice_documents")
    return {
        **payload,
        "timestamps": aligned,
        "text": text,
        "duration_seconds": duration_seconds,
    }


def _with_pipeline():
    try:
        from app.services.voice_documents.pipeline import (  # type: ignore
            choose_option,
            dispatch_confirmed_send,
            ingest_transcript,
        )
        from app.services.voice_documents.send_gate import DraftSendBlocked  # type: ignore

        return ingest_transcript, choose_option, dispatch_confirmed_send, DraftSendBlocked
    except Exception:
        return None


@router.get("/voice/documents/lipsync")
async def voice_documents_lipsync():
    return lipsync_payload(surface="voice_documents")


@router.post("/voice/documents/spoken")
async def voice_documents_spoken(body: SpokenIn):
    """Align word times for avatar read-back of a draft document."""
    return spoken_document_lipsync(body.text, body.duration_seconds, body.timestamps)


@router.post("/voice/documents")
async def voice_documents(body: TranscriptIn):
    loaded = _with_pipeline()
    if loaded is None:
        return attach_lipsync({
            "ok": False,
            "pipeline": False,
            "sent": False,
            "reason": "Voice-document pipeline is not on this checkout. Lip-sync offset is still published.",
            "transcript": body.transcript,
        }, surface="voice_documents")
    ingest_transcript, *_rest = loaded
    result = ingest_transcript(
        body.transcript,
        channel=body.channel,
        session_key=body.session_key or f"{body.channel}:default",
        edition_id=body.edition,
        session_id=body.session_id,
    )
    return attach_lipsync(result, surface="voice_documents")


@router.post("/voice/documents/audio")
async def voice_documents_audio(
    audio: UploadFile = File(...),
    session_id: str = "",
    session_key: str = "",
    channel: str = "cc",
    edition: str = "workroom",
    language: str = "en",
):
    loaded = _with_pipeline()
    if loaded is None:
        data = await audio.read()
        return attach_lipsync({
            "ok": False,
            "pipeline": False,
            "sent": False,
            "audio_bytes": len(data),
            "duration_hint_ms": pcm_duration_ms(data) if data[:4] != b"RIFF" else 0,
            "reason": "Voice-document pipeline is not on this checkout.",
        }, surface="voice_documents")
    from app.services.max.stt_service import stt_service
    import tempfile
    from pathlib import Path

    if not stt_service.is_configured:
        raise HTTPException(status_code=503, detail="STT not configured — GROQ_API_KEY missing")
    suffix = Path(audio.filename or "audio.webm").suffix or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await audio.read())
        tmp_path = Path(tmp.name)
    try:
        from app.services.voice_documents.pipeline import ingest_audio

        result = await ingest_audio(
            tmp_path,
            channel=channel,
            session_key=session_key or f"{channel}:default",
            edition_id=edition,
            session_id=session_id,
            language=language,
        )
    finally:
        tmp_path.unlink(missing_ok=True)
    return attach_lipsync(result, surface="voice_documents")


@router.post("/voice/documents/{session_id}/choose")
async def voice_documents_choose(session_id: str, body: ChoiceIn):
    loaded = _with_pipeline()
    if loaded is None:
        raise HTTPException(status_code=503, detail="Voice-document pipeline is not on this checkout")
    _ing, choose_option, _disp, _blocked = loaded
    return attach_lipsync(choose_option(session_id, body.option_id, body.choice_id), surface="voice_documents")


@router.post("/voice/documents/{session_id}/confirm-send")
async def voice_documents_confirm(session_id: str, body: ConfirmIn):
    loaded = _with_pipeline()
    if loaded is None:
        raise HTTPException(status_code=503, detail="Voice-document pipeline is not on this checkout")
    _ing, _choose, dispatch_confirmed_send, DraftSendBlocked = loaded
    try:
        result = await dispatch_confirmed_send(
            session_id,
            confirmed=body.confirmed,
            to_email=body.to_email,
        )
    except DraftSendBlocked as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if isinstance(result, dict):
        result = attach_lipsync(result, surface="voice_documents")
        result["sent"] = False if not result.get("sent") else result["sent"]
    return result
