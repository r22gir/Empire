"""
MAX TTS Service — Text-to-Speech via edge-tts (free, no API key needed).
One voice for MAX everywhere: Telegram voice replies, Command Center audio.

Uses Microsoft Edge Neural TTS — AndrewMultilingual (warm, confident, bilingual EN/ES).
"""
import logging
import tempfile
import asyncio
from pathlib import Path
from typing import Optional

logger = logging.getLogger("max.tts")

# MAX voice config — one voice everywhere
TTS_VOICE = "en-US-AndrewMultilingualNeural"  # warm, confident, natural + bilingual EN/ES
TTS_RATE = "+0%"  # normal speed
MAX_TEXT_LENGTH = 4096
MAX_RETRIES = 2


class TTSService:
    """Text-to-Speech service using edge-tts (free, no API key)."""

    def __init__(self):
        self.cache_dir = Path(tempfile.gettempdir()) / "max_tts_cache"
        self.cache_dir.mkdir(exist_ok=True)
        self._available: Optional[bool] = None

    @property
    def is_configured(self) -> bool:
        """edge-tts needs no API key — always configured if the package is installed."""
        if self._available is None:
            try:
                import edge_tts  # noqa: F401
                self._available = True
            except ImportError:
                self._available = False
                logger.error("edge-tts not installed. Run: pip install edge-tts")
        return self._available

    async def _synthesize_with_retry(
        self, text: str, voice: str, rate: str, output_path: Path
    ) -> bool:
        """Try synthesis up to MAX_RETRIES times (edge-tts WebSocket can be flaky)."""
        import edge_tts

        for attempt in range(MAX_RETRIES + 1):
            try:
                communicate = edge_tts.Communicate(text, voice, rate=rate)
                await communicate.save(str(output_path))
                if output_path.exists() and output_path.stat().st_size > 0:
                    return True
            except Exception as e:
                if attempt < MAX_RETRIES:
                    logger.warning(f"TTS attempt {attempt + 1} failed: {e}, retrying...")
                    await asyncio.sleep(0.5)
                else:
                    logger.error(f"TTS failed after {MAX_RETRIES + 1} attempts: {e}")
        return False

    async def synthesize(
        self,
        text: str,
        voice: str = TTS_VOICE,
        rate: str = TTS_RATE,
        output_format: str = "mp3",
    ) -> Optional[Path]:
        """Convert text to speech audio file."""
        if not self.is_configured or not text or not text.strip():
            return None

        clean_text = text.strip()[:MAX_TEXT_LENGTH]

        try:
            suffix = ".ogg" if output_format == "opus" else f".{output_format}"
            audio_path = Path(tempfile.mktemp(suffix=suffix, dir=str(self.cache_dir)))

            if await self._synthesize_with_retry(clean_text, voice, rate, audio_path):
                logger.info(f"TTS generated: {audio_path.stat().st_size} bytes → {audio_path.name}")
                return audio_path
            return None

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

        try:
            audio_path = Path(tempfile.mktemp(suffix=".mp3", dir=str(self.cache_dir)))

            if await self._synthesize_with_retry(clean_text, TTS_VOICE, TTS_RATE, audio_path):
                data = audio_path.read_bytes()
                audio_path.unlink(missing_ok=True)
                return data
            return None

        except Exception as e:
            logger.error(f"TTS web synthesis failed: {e}")
            return None


# Singleton
tts_service = TTSService()
