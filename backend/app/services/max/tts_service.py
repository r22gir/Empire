"""
MAX TTS Service — Text-to-Speech via xAI Grok TTS API.
One voice for MAX everywhere: Telegram voice replies, Command Center audio.

Voice: Rex (confident, professional). Supports 100+ languages including Spanish.
Requires XAI_API_KEY (same key used for Grok chat/vision).
"""
import os
import logging
import tempfile
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger("max.tts")

# MAX voice config — one voice everywhere
# Available voices: ara, rex, sal, eve, leo
TTS_VOICE = "rex"
TTS_API_URL = "https://api.x.ai/v1/tts"
MAX_TEXT_LENGTH = 4096


class TTSService:
    """Text-to-Speech service using xAI Grok TTS (Rex voice)."""

    def __init__(self):
        self.cache_dir = Path(tempfile.gettempdir()) / "max_tts_cache"
        self.cache_dir.mkdir(exist_ok=True)

    @property
    def is_configured(self) -> bool:
        return bool(os.getenv("XAI_API_KEY"))

    async def synthesize(
        self,
        text: str,
        voice: str = TTS_VOICE,
        output_format: str = "mp3",
    ) -> Optional[Path]:
        """Convert text to speech audio file via xAI TTS API."""
        if not self.is_configured or not text or not text.strip():
            return None

        clean_text = text.strip()[:MAX_TEXT_LENGTH]
        api_key = os.getenv("XAI_API_KEY")

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    TTS_API_URL,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "text": clean_text,
                        "voice_id": voice,
                    },
                )

            if resp.status_code != 200:
                logger.error(f"xAI TTS API error {resp.status_code}: {resp.text[:300]}")
                return None

            audio_data = resp.content
            if not audio_data or len(audio_data) < 100:
                logger.warning("xAI TTS returned empty or tiny audio")
                return None

            suffix = f".{output_format}"
            audio_path = Path(tempfile.mktemp(suffix=suffix, dir=str(self.cache_dir)))
            audio_path.write_bytes(audio_data)
            logger.info(f"TTS generated via xAI (Rex): {len(audio_data)} bytes → {audio_path.name}")
            return audio_path

        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            return None

    async def synthesize_for_telegram(self, text: str) -> Optional[Path]:
        """Generate voice note for Telegram (mp3 — Telegram accepts it as voice)."""
        return await self.synthesize(text, output_format="mp3")

    async def synthesize_for_web(self, text: str) -> Optional[bytes]:
        """Generate audio bytes for web playback (mp3 format)."""
        if not self.is_configured or not text or not text.strip():
            return None

        clean_text = text.strip()[:MAX_TEXT_LENGTH]
        api_key = os.getenv("XAI_API_KEY")

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    TTS_API_URL,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "text": clean_text,
                        "voice_id": TTS_VOICE,
                    },
                )

            if resp.status_code != 200:
                logger.error(f"xAI TTS API error {resp.status_code}: {resp.text[:300]}")
                return None

            audio_data = resp.content
            if not audio_data or len(audio_data) < 100:
                return None

            return audio_data

        except Exception as e:
            logger.error(f"TTS web synthesis failed: {e}")
            return None


# Singleton
tts_service = TTSService()
