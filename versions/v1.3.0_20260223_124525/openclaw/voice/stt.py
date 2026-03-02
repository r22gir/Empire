"""
Speech-to-text (STT) for OpenClaw using OpenAI Whisper (local or API).
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class WhisperSTT:
    """Speech-to-text transcription using OpenAI Whisper."""

    def __init__(self, model: str = "base", use_api: bool = False) -> None:
        self.model_name = model
        self.use_api = use_api
        self._model = None

    def _load_model(self):
        """Lazily load the Whisper model."""
        if self._model is not None:
            return
        try:
            import whisper  # type: ignore
            self._model = whisper.load_model(self.model_name)
            logger.info("Whisper model '%s' loaded", self.model_name)
        except ImportError:
            logger.warning("whisper package not installed; STT unavailable")
            self._model = None

    def transcribe(self, audio_path: str) -> Optional[str]:
        """
        Transcribe an audio file to text.

        Args:
            audio_path: Path to an audio file (wav, mp3, etc.)

        Returns:
            Transcribed text or None on error.
        """
        if not os.path.exists(audio_path):
            logger.error("Audio file not found: %s", audio_path)
            return None

        if self.use_api:
            return self._transcribe_api(audio_path)
        return self._transcribe_local(audio_path)

    def _transcribe_local(self, audio_path: str) -> Optional[str]:
        self._load_model()
        if self._model is None:
            return None
        try:
            result = self._model.transcribe(audio_path)
            return result.get("text", "").strip()
        except Exception as exc:  # noqa: BLE001
            logger.error("Whisper transcription failed: %s", exc)
            return None

    def _transcribe_api(self, audio_path: str) -> Optional[str]:
        try:
            import openai  # type: ignore
            with open(audio_path, "rb") as f:
                result = openai.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                )
            return result.text.strip()
        except Exception as exc:  # noqa: BLE001
            logger.error("OpenAI Whisper API transcription failed: %s", exc)
            return None
