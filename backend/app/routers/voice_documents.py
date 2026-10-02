"""Voice notes → draft documents. Holds the same pipeline for chat and Telegram."""
from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.services.voice_documents.pipeline import (
    choose_option,
    dispatch_confirmed_send,
    ingest_transcript,
)
from app.services.voice_documents.send_gate import DraftSendBlocked

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


def _public(result: dict) -> dict:
    drawing = dict(result.get("drawing") or {})
    svg = drawing.pop("svg", "") or ""
    drawing["svg_chars"] = len(svg)
    drawing["has_svg"] = bool(svg)
    result = dict(result)
    result["drawing"] = drawing
    result["sent"] = False if not result.get("sent") else result["sent"]
    return result


@router.post("/voice/documents")
async def voice_documents(body: TranscriptIn):
    """Text entry. Audio uses /voice/documents/audio, which calls the STT service."""
    result = ingest_transcript(
        body.transcript,
        channel=body.channel,
        session_key=body.session_key or f"{body.channel}:default",
        edition_id=body.edition,
        session_id=body.session_id,
    )
    return _public(result)


@router.post("/voice/documents/audio")
async def voice_documents_audio(
    audio: UploadFile = File(...),
    session_id: str = "",
    session_key: str = "",
    channel: str = "cc",
    edition: str = "workroom",
    language: str = "en",
):
    """Transcribe with the Groq STT service, then the document pipeline."""
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
    return _public(result)


@router.post("/voice/documents/{session_id}/choose")
async def voice_documents_choose(session_id: str, body: ChoiceIn):
    return _public(choose_option(session_id, body.option_id, body.choice_id))


@router.post("/voice/documents/{session_id}/confirm-send")
async def voice_documents_confirm(session_id: str, body: ConfirmIn):
    try:
        result = await dispatch_confirmed_send(
            session_id,
            confirmed=body.confirmed,
            to_email=body.to_email,
        )
    except DraftSendBlocked as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return result
