"""
MAX TTS Service — Text-to-Speech via OpenAI API.
One voice for MAX everywhere: Telegram voice replies, Command Center audio.

Uses OpenAI TTS API (gpt-4o-mini-tts model, 'onyx' voice — deep, authoritative).
Falls back gracefully if API key missing or call fails.
"""
import os
import logging
import tempfile
import httpx
from pathlib import Path
from typing import Optional

logger = logging.getLogger("max.tts")

# MAX voice config — one voice everywhere
TTS_MODEL = "gpt-4o-mini-tts"
TTS_VOICE = "onyx"  # deep, confident — fits MAX's personality
TTS_SPEED = 1.0
TTS_FORMAT = "opus"  # small file, Telegram-native
MAX_TEXT_LENGTH = 4096  # OpenAI TTS limit


class TTSService:
    """Text-to-Speech service using OpenAI API."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.api_url = "https://api.openai.com/v1/audio/speech"
        self.cache_dir = Path(tempfile.gettempdir()) / "max_tts_cache"
        self.cache_dir.mkdir(exist_ok=True)

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def synthesize(
        self,
        text: str,
        voice: str = TTS_VOICE,
        speed: float = TTS_SPEED,
        output_format: str = TTS_FORMAT,
    ) -> Optional[Path]:
        """Convert text to speech audio file.

        Returns path to audio file, or None on failure.
        """
        if not self.is_configured:
            logger.warning("TTS not configured — OPENAI_API_KEY not set")
            return None

        if not text or not text.strip():
            return None

        # Trim to API limit
        clean_text = text.strip()[:MAX_TEXT_LENGTH]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": TTS_MODEL,
                        "input": clean_text,
                        "voice": voice,
                        "speed": speed,
                        "response_format": output_format,
                    },
                )

                if resp.status_code != 200:
                    logger.error(f"TTS API error {resp.status_code}: {resp.text[:200]}")
                    return None

                # Save audio to temp file
                suffix = f".{output_format}" if output_format != "opus" else ".ogg"
                audio_path = Path(tempfile.mktemp(suffix=suffix, dir=str(self.cache_dir)))
                audio_path.write_bytes(resp.content)
                logger.info(f"TTS generated: {len(resp.content)} bytes → {audio_path.name}")
                return audio_path

        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            return None

    async def synthesize_for_telegram(self, text: str) -> Optional[Path]:
        """Generate voice note optimized for Telegram (opus/ogg format)."""
        return await self.synthesize(text, output_format="opus")

    async def synthesize_for_web(self, text: str) -> Optional[bytes]:
        """Generate audio bytes for web playback (mp3 format).

        Returns raw MP3 bytes for streaming to the browser.
        """
        if not self.is_configured or not text or not text.strip():
            return None

        clean_text = text.strip()[:MAX_TEXT_LENGTH]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": TTS_MODEL,
                        "input": clean_text,
                        "voice": TTS_VOICE,
                        "speed": TTS_SPEED,
                        "response_format": "mp3",
                    },
                )

                if resp.status_code != 200:
                    logger.error(f"TTS web error {resp.status_code}: {resp.text[:200]}")
                    return None

                return resp.content

        except Exception as e:
            logger.error(f"TTS web synthesis failed: {e}")
            return None


# Singleton
tts_service = TTSService()
