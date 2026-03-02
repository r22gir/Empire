"""EmpireBox Voice Service – FastAPI application.

Endpoints:
    POST /stt     Upload audio file → transcript
    POST /tts     Send text        → audio file
    GET  /voices  List available TTS voices
    GET  /health  Service health check
"""

import logging
import os
from typing import Optional

import yaml
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

import piper_tts
import whisper_stt

logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)

# ── Configuration ──────────────────────────────────────────────────────────────

CONFIG_PATH = os.environ.get("CONFIG_PATH", "/app/config.yaml")

_cfg: dict = {}


def _load_config() -> dict:
    global _cfg
    if _cfg:
        return _cfg
    try:
        with open(CONFIG_PATH) as fh:
            _cfg = yaml.safe_load(fh) or {}
    except FileNotFoundError:
        logger.warning("Config not found at %s – using defaults.", CONFIG_PATH)
        _cfg = {}
    return _cfg


def _voice_cfg() -> dict:
    return _load_config().get("voice", {})


def _stt_cfg() -> dict:
    return _voice_cfg().get("stt", {})


def _tts_cfg() -> dict:
    return _voice_cfg().get("tts", {})


def _api_cfg() -> dict:
    return _voice_cfg().get("api", {})


# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(title="EmpireBox Voice Service", version="1.0.0")

SUPPORTED_AUDIO_TYPES = {
    "audio/ogg",
    "audio/mpeg",
    "audio/wav",
    "audio/x-wav",
    "audio/mp4",
    "audio/m4a",
    "application/octet-stream",
}


# ── Health ──────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> dict:
    """Return service health status."""
    return {"status": "ok", "service": "voice"}


# ── STT ────────────────────────────────────────────────────────────────────────

@app.post("/stt")
async def speech_to_text(
    file: UploadFile = File(...),
    language: Optional[str] = Form(default=None),
) -> dict:
    """Transcribe uploaded audio to text.

    Args:
        file: Audio file (.ogg, .mp3, .wav, .m4a).
        language: Optional ISO language code (e.g. ``"en"``).
                  Omit or pass ``"auto"`` for automatic detection.

    Returns:
        ``{"text": "...", "language": "en", "confidence": 0.95}``
    """
    cfg = _stt_cfg()
    max_mb = _api_cfg().get("max_audio_size_mb", 25)

    audio_bytes = await file.read()
    if len(audio_bytes) > max_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"Audio file exceeds {max_mb} MB limit.",
        )

    lang = language or cfg.get("language", "auto")
    try:
        result = whisper_stt.transcribe(
            audio_bytes=audio_bytes,
            model_size=cfg.get("model", "base"),
            device=cfg.get("device", "cpu"),
            language=lang,
        )
    except Exception as exc:
        logger.exception("STT error: %s", exc)
        raise HTTPException(status_code=500, detail="Transcription failed.") from exc

    return result


# ── TTS ────────────────────────────────────────────────────────────────────────

@app.post("/tts")
async def text_to_speech(
    text: str = Form(...),
    voice: Optional[str] = Form(default=None),
    speed: Optional[float] = Form(default=None),
) -> Response:
    """Convert text to an audio file.

    Args:
        text: The text to synthesise.
        voice: Piper voice identifier (e.g. ``"en_US-amy-medium"``).
        speed: Playback speed multiplier (1.0 = normal).

    Returns:
        Audio file bytes (mp3 or ogg depending on config).
    """
    cfg = _tts_cfg()
    selected_voice = voice or cfg.get("default_voice", "en_US-amy-medium")
    selected_speed = speed if speed is not None else cfg.get("speed", 1.0)
    output_format = cfg.get("output_format", "mp3")

    available = cfg.get("available_voices", [])
    if available and selected_voice not in available:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown voice '{selected_voice}'. "
                   f"Available: {', '.join(available)}",
        )

    try:
        audio_bytes = piper_tts.synthesise(
            text=text,
            voice=selected_voice,
            output_format=output_format,
            speed=selected_speed,
        )
    except FileNotFoundError as exc:
        logger.error("TTS model missing: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("TTS error: %s", exc)
        raise HTTPException(status_code=500, detail="Speech synthesis failed.") from exc

    media_type = "audio/mpeg" if output_format == "mp3" else "audio/ogg"
    return Response(content=audio_bytes, media_type=media_type)


# ── Voices ──────────────────────────────────────────────────────────────────────

@app.get("/voices")
async def list_voices() -> dict:
    """Return the list of available TTS voices."""
    cfg = _tts_cfg()
    return {
        "voices": cfg.get("available_voices", []),
        "default": cfg.get("default_voice", "en_US-amy-medium"),
    }


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    api_cfg = _api_cfg()
    uvicorn.run(
        app,
        host=api_cfg.get("host", "0.0.0.0"),
        port=api_cfg.get("port", 8200),
    )
