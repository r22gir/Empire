"""HTTP transcription for /api/v1/voice/transcribe.

A Groq failure is an HTTP error. It is not a 200 body whose text
the chat UI can forward to Max.
"""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from fastapi import HTTPException, UploadFile

logger = logging.getLogger("max.stt_http")

_MIN_AUDIO_BYTES = 256


def normalize_stt_language(language: str | None) -> str | None:
    """Empty, missing, or 'auto' means Whisper detects the language.

    English is not the default. An explicit code such as 'es' is kept.
    """
    if language is None:
        return None
    cleaned = language.strip().lower()
    if cleaned in {"", "auto", "und", "none"}:
        return None
    return cleaned


def transcript_is_failure(text: str | None) -> bool:
    value = (text or "").strip()
    if not value:
        return True
    if not value.startswith("["):
        return False
    lowered = value.lower()
    return (
        "transcription failed" in lowered
        or "stt unavailable" in lowered
        or "audio file not found" in lowered
        or "could not process" in lowered
    )


def _filename_for(upload_name: str | None, content_type: str | None) -> str:
    name = (upload_name or "").strip()
    if name and "." in Path(name).name:
        return Path(name).name
    mime = (content_type or "").lower()
    if "mp4" in mime or "m4a" in mime or "aac" in mime:
        return "recording.mp4"
    if "ogg" in mime:
        return "recording.ogg"
    if "wav" in mime:
        return "recording.wav"
    return "recording.webm"


async def transcribe_upload(upload: UploadFile, language: str | None = None) -> dict:
    """Transcribe one upload. Raises HTTPException on failure."""
    from app.services.max.stt_service import stt_service

    if not stt_service.is_configured:
        raise HTTPException(status_code=503, detail="STT not configured — GROQ_API_KEY missing")

    lang = normalize_stt_language(language)
    filename = _filename_for(upload.filename, upload.content_type)
    suffix = Path(filename).suffix or ".webm"
    content = await upload.read()
    if not content or len(content) < _MIN_AUDIO_BYTES:
        raise HTTPException(status_code=400, detail="Recording was too short")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        transcript = await stt_service.transcribe(tmp_path, language=lang)
    except Exception as exc:
        logger.error("STT request failed: %s", exc)
        raise HTTPException(status_code=502, detail="Could not transcribe that recording") from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    if transcript_is_failure(transcript):
        logger.error("STT returned a failure result for %s", filename)
        raise HTTPException(status_code=502, detail="Could not transcribe that recording")

    return {"text": transcript, "language": lang, "filename": filename}
