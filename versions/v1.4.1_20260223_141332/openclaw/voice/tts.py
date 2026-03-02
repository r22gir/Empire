"""
Text-to-speech (TTS) for OpenClaw.

Supports pyttsx3 (local, offline) or OpenAI TTS API.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class TextToSpeech:
    """Text-to-speech synthesis."""

    def __init__(self, engine: str = "pyttsx3", voice: str = "default") -> None:
        """
        Args:
            engine: 'pyttsx3' for local TTS or 'openai' for OpenAI TTS API.
            voice: Voice identifier (engine-specific).
        """
        self.engine_name = engine
        self.voice = voice
        self._engine = None

    def _init_pyttsx3(self):
        if self._engine is not None:
            return
        try:
            import pyttsx3  # type: ignore
            self._engine = pyttsx3.init()
            logger.info("pyttsx3 TTS engine initialized")
        except ImportError:
            logger.warning("pyttsx3 not installed; TTS unavailable")
            self._engine = None

    def speak(self, text: str) -> bool:
        """
        Synthesize and play speech for the given text.

        Returns True on success, False on failure.
        """
        if self.engine_name == "openai":
            return self._speak_openai(text)
        return self._speak_pyttsx3(text)

    def synthesize_to_file(self, text: str, output_path: str) -> bool:
        """Save synthesized speech to a file."""
        if self.engine_name == "openai":
            return self._openai_to_file(text, output_path)
        return self._pyttsx3_to_file(text, output_path)

    def _speak_pyttsx3(self, text: str) -> bool:
        self._init_pyttsx3()
        if self._engine is None:
            return False
        try:
            self._engine.say(text)
            self._engine.runAndWait()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("pyttsx3 TTS failed: %s", exc)
            return False

    def _pyttsx3_to_file(self, text: str, output_path: str) -> bool:
        self._init_pyttsx3()
        if self._engine is None:
            return False
        try:
            self._engine.save_to_file(text, output_path)
            self._engine.runAndWait()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("pyttsx3 save_to_file failed: %s", exc)
            return False

    def _speak_openai(self, text: str) -> bool:
        try:
            import subprocess
            import tempfile

            import openai  # type: ignore
            response = openai.audio.speech.create(
                model="tts-1",
                voice=self.voice if self.voice != "default" else "alloy",
                input=text,
            )
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = tmp.name
            try:
                response.stream_to_file(tmp_path)
                subprocess.run(
                    ["ffplay", "-nodisp", "-autoexit", tmp_path],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            finally:
                os.unlink(tmp_path)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("OpenAI TTS failed: %s", exc)
            return False

    def _openai_to_file(self, text: str, output_path: str) -> bool:
        try:
            import openai  # type: ignore
            response = openai.audio.speech.create(
                model="tts-1",
                voice=self.voice if self.voice != "default" else "alloy",
                input=text,
            )
            response.stream_to_file(output_path)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("OpenAI TTS to file failed: %s", exc)
            return False
