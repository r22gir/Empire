"""
Speech-to-Text service using Groq Whisper API.
Uses the official Groq SDK for reliability.
Free tier: 28,800 audio-seconds/day.
"""
import os
import logging
from pathlib import Path

from .token_tracker import token_tracker

logger = logging.getLogger(__name__)


class STTService:
    """Transcribe audio files using Groq Whisper API."""

    def __init__(self):
        self._client = None
        self._init_attempted = False

    def _get_client(self):
        """Lazy-init the Groq client (key may be loaded after import time)."""
        if not self._init_attempted:
            self._init_attempted = True
            key = os.getenv("GROQ_API_KEY", "")
            if key:
                try:
                    from groq import Groq
                    self._client = Groq(api_key=key)
                    logger.info("Groq STT client initialized")
                except ImportError:
                    logger.warning("groq SDK not installed — falling back to httpx")
                except Exception as e:
                    logger.warning(f"Groq client init failed: {e}")
        return self._client

    @property
    def is_configured(self) -> bool:
        return self._get_client() is not None

    async def transcribe(self, audio_path: str | Path, language: str | None = None) -> str:
        """
        Transcribe an audio file to text.
        Supports: mp3, mp4, m4a, wav, ogg, flac, webm
        Max file size: 25MB
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            return f"[Audio file not found: {audio_path.name}]"

        if not self.is_configured:
            return "[STT unavailable — GROQ_API_KEY not set or groq SDK not installed]"

        # Check cache
        cache_path = audio_path.with_suffix(audio_path.suffix + '.transcript.txt')
        if cache_path.exists():
            return cache_path.read_text().strip()

        try:
            import asyncio
            result = await asyncio.get_event_loop().run_in_executor(
                None, self._transcribe_sync_internal, audio_path, language
            )
            if result and not result.startswith("["):
                cache_path.write_text(result)
                logger.info(f"Transcribed {audio_path.name}: {len(result)} chars")
                token_tracker.log_fixed_cost("groq-whisper", feature="stt", source="stt_service")
            return result
        except Exception as e:
            logger.error(f"STT error: {e}")
            return f"[Transcription failed: {e}]"

    def _transcribe_sync_internal(self, audio_path: Path, language: str | None = None) -> str:
        """Internal sync transcription using Groq SDK."""
        client = self._get_client()
        if not client:
            return "[STT unavailable]"

        with open(audio_path, "rb") as f:
            kwargs = {
                "file": (audio_path.name, f),
                "model": "whisper-large-v3-turbo",
                "response_format": "text",
                "temperature": 0.0,
            }
            if language:
                kwargs["language"] = language

            result = client.audio.transcriptions.create(**kwargs)

        # Groq SDK returns the text directly when response_format="text"
        if isinstance(result, str):
            return result.strip()
        # Some SDK versions return an object
        return getattr(result, 'text', str(result)).strip()

    def transcribe_sync(self, audio_path: str | Path, language: str | None = None) -> str:
        """Synchronous version for non-async contexts."""
        audio_path = Path(audio_path)
        if not audio_path.exists():
            return f"[Audio file not found: {audio_path.name}]"

        if not self.is_configured:
            return "[STT unavailable — GROQ_API_KEY not set]"

        cache_path = audio_path.with_suffix(audio_path.suffix + '.transcript.txt')
        if cache_path.exists():
            return cache_path.read_text().strip()

        try:
            result = self._transcribe_sync_internal(audio_path, language)
            if result and not result.startswith("["):
                cache_path.write_text(result)
                logger.info(f"Transcribed {audio_path.name}: {len(result)} chars")
            return result
        except Exception as e:
            logger.error(f"STT sync error: {e}")
            return f"[Transcription failed: {e}]"

    async def translate_to_english(self, audio_path: str | Path) -> str:
        """Translate any language audio to English text."""
        audio_path = Path(audio_path)
        if not audio_path.exists():
            return f"[Audio file not found: {audio_path.name}]"

        client = self._get_client()
        if not client:
            return "[Translation unavailable — GROQ_API_KEY not set]"

        try:
            import asyncio

            def _translate():
                with open(audio_path, "rb") as f:
                    return client.audio.translations.create(
                        file=(audio_path.name, f),
                        model="whisper-large-v3",
                        response_format="text",
                    )

            result = await asyncio.get_event_loop().run_in_executor(None, _translate)
            if isinstance(result, str):
                return result.strip()
            return getattr(result, 'text', str(result)).strip()
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return f"[Translation failed: {e}]"


# Singleton
stt_service = STTService()
