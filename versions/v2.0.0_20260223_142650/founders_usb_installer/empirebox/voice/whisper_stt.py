"""Speech-to-Text using faster-whisper."""

import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_model = None


def _get_model(model_size: str = "base", device: str = "cpu"):
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        logger.info("Loading Whisper model '%s' on %s …", model_size, device)
        _model = WhisperModel(model_size, device=device, compute_type="int8")
        logger.info("Whisper model loaded.")
    return _model


def transcribe(
    audio_bytes: bytes,
    model_size: str = "base",
    device: str = "cpu",
    language: Optional[str] = None,
) -> dict:
    """Transcribe audio bytes and return transcript, language, and confidence.

    Args:
        audio_bytes: Raw audio data (.ogg, .mp3, .wav, .m4a).
        model_size: Whisper model variant.
        device: Compute device ("cpu" or "cuda").
        language: ISO language code or "auto" for detection.

    Returns:
        dict with keys ``text``, ``language``, ``confidence``.
    """
    model = _get_model(model_size, device)

    lang_param = None if (language is None or language == "auto") else language

    segments, info = model.transcribe(
        io.BytesIO(audio_bytes),
        language=lang_param,
        beam_size=5,
    )

    text_parts = [seg.text for seg in segments]
    transcript = " ".join(text_parts).strip()

    return {
        "text": transcript,
        "language": info.language,
        "confidence": round(float(info.language_probability), 4),
    }
