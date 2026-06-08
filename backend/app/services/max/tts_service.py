"""
MAX TTS Service — Text-to-Speech with MiniMax primary, xAI fallback.

One voice for MAX everywhere: Telegram voice replies, Command Center audio.

Primary provider:  MiniMax TTS (speech-01, voice from MINIMAX_TTS_VOICE env,
                   defaults to a value compatible with the existing
                   minimax_tts tool in minimax_tools.py). Uses the existing
                   MINIMAX_API_KEY + MINIMAX_BASE_URL.

Fallback provider: xAI Grok TTS (Rex voice) — only fires when MiniMax
                   returns success=False or raises. xAI's voice list
                   (ara/rex/sal/eve/leo) is preserved for the fallback path.

Why this design:
    MiniMax TTS is on the active subscription and is not currently
    rate-limited. xAI TTS started returning HTTP 429 (team monthly
    credit cap) on 2026-06-07. To keep Telegram voice replies working
    without depending on the xAI billing relationship, MiniMax is now
    primary. The xAI path is retained for redundancy and is exercised
    only when MiniMax fails.
"""
import os
import logging
import tempfile
from pathlib import Path
from typing import Optional

import httpx

from .token_tracker import token_tracker

logger = logging.getLogger("max.tts")

# MAX voice config — one voice everywhere
# Available xAI voices: ara, rex, sal, eve, leo
TTS_VOICE = "rex"
TTS_API_URL = "https://api.x.ai/v1/tts"
MAX_TEXT_LENGTH = 4096

# MiniMax TTS config — primary
# Default voice matches the existing minimax_tts tool in minimax_tools.py so
# the two paths produce interchangeable audio characteristics.
MINIMAX_TTS_DEFAULT_VOICE = os.getenv("MINIMAX_TTS_VOICE", "male-qn-qingque")
MINIMAX_TTS_DEFAULT_MODEL = os.getenv("MINIMAX_TTS_MODEL", "speech-01")
MINIMAX_TTS_API_PATH = "/audio/speech"


class TTSService:
    """Text-to-Speech service with MiniMax primary and xAI fallback."""

    def __init__(self):
        self.cache_dir = Path(tempfile.gettempdir()) / "max_tts_cache"
        self.cache_dir.mkdir(exist_ok=True)
        self.last_status = "not_checked"
        self.last_error = ""
        # Track which provider produced the last successful synthesis
        self.last_provider: Optional[str] = None

    # ── Provider configuration ─────────────────────────────────────

    @property
    def is_configured(self) -> bool:
        """True if at least one provider is configured.

        The historical contract: ``is_configured`` returned True when
        XAI_API_KEY was set (xAI was the only provider). To preserve
        that contract for callers (e.g. voice_capability_truth), the
        service is "configured" if EITHER provider has its key. This
        matches the spirit of the original property.
        """
        return bool(self.is_minimax_configured or self.is_xai_configured)

    @property
    def is_minimax_configured(self) -> bool:
        return bool(os.getenv("MINIMAX_API_KEY"))

    @property
    def is_xai_configured(self) -> bool:
        return bool(os.getenv("XAI_API_KEY"))

    # ── Primary: MiniMax TTS ─────────────────────────────────────────

    async def _synthesize_minimax(
        self,
        text: str,
        voice: str,
        output_format: str,
    ) -> Optional[Path]:
        """Call MiniMax TTS, write audio to a temp file, return the path.

        Returns None on any failure (HTTP error, empty body, exception).
        Caller is responsible for trying the fallback.
        """
        api_key = os.getenv("MINIMAX_API_KEY", "")
        if not api_key:
            return None
        base_url = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1").rstrip("/")
        model = os.getenv("MINIMAX_TTS_MODEL", MINIMAX_TTS_DEFAULT_MODEL)
        clean_text = text.strip()[:MAX_TEXT_LENGTH]
        if not clean_text:
            return None
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{base_url}{MINIMAX_TTS_API_PATH}",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "text": clean_text,
                        "voice_id": voice,
                        "speed": 1.0,
                        "response_format": output_format,
                    },
                )
            if resp.status_code != 200:
                logger.warning(
                    f"MiniMax TTS HTTP {resp.status_code}: {resp.text[:200]}"
                )
                return None
            audio_data = resp.content
            if not audio_data or len(audio_data) < 500:
                logger.warning(f"MiniMax TTS returned empty/tiny audio ({len(audio_data)}b)")
                return None
            suffix = f".{output_format}"
            audio_path = Path(tempfile.mktemp(suffix=suffix, dir=str(self.cache_dir)))
            audio_path.write_bytes(audio_data)
            logger.info(
                f"TTS generated via MiniMax (model={model}, voice={voice}): "
                f"{len(audio_data)} bytes → {audio_path.name}"
            )
            try:
                token_tracker.log_fixed_cost("minimax-tts", feature="tts", source="tts_service")
            except Exception:
                pass
            return audio_path
        except Exception as e:
            logger.warning(f"MiniMax TTS synthesis failed: {type(e).__name__}: {e}")
            return None

    # ── Fallback: xAI Grok TTS ───────────────────────────────────────

    async def _synthesize_xai(
        self,
        text: str,
        voice: str,
        output_format: str,
    ) -> Optional[Path]:
        """Call xAI Grok TTS, write audio to a temp file, return the path.

        Returns None on any failure. Caller treats None as "give up".
        """
        api_key = os.getenv("XAI_API_KEY", "")
        if not api_key:
            return None
        clean_text = text.strip()[:MAX_TEXT_LENGTH]
        if not clean_text:
            return None
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
                        "language": "en",
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
            try:
                token_tracker.log_fixed_cost("grok-tts", feature="tts", source="tts_service")
            except Exception:
                pass
            return audio_path
        except Exception as e:
            logger.error(f"xAI TTS synthesis failed: {type(e).__name__}: {e}")
            return None

    # ── Public synthesis entry point ─────────────────────────────────

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        output_format: str = "mp3",
    ) -> Optional[Path]:
        """Convert text to speech audio file. MiniMax primary, xAI fallback.

        The historical contract: returns ``Optional[Path]`` to a cached
        audio file, or ``None`` if all providers fail. Callers do not
        need to know which provider was used; this method picks and
        records the choice in ``self.last_provider``.
        """
        if not text or not text.strip():
            self.last_status = "failed"
            self.last_error = "empty text"
            return None

        # Choose voices per provider: MiniMax voice is configurable via
        # MINIMAX_TTS_VOICE; xAI uses the historical default (rex). If
        # the caller didn't pass a voice we use the MiniMax default for
        # the primary attempt and fall back to xAI default.
        minimax_voice = voice or os.getenv("MINIMAX_TTS_VOICE", MINIMAX_TTS_DEFAULT_VOICE)
        xai_voice = TTS_VOICE  # "rex" — historical xAI default

        # Primary attempt: MiniMax
        if self.is_minimax_configured:
            result = await self._synthesize_minimax(text, minimax_voice, output_format)
            if result is not None:
                self.last_status = "ok"
                self.last_error = ""
                self.last_provider = "minimax"
                return result
            logger.info("MiniMax TTS failed; falling back to xAI")

        # Fallback attempt: xAI
        if self.is_xai_configured:
            result = await self._synthesize_xai(text, xai_voice, output_format)
            if result is not None:
                self.last_status = "ok"
                self.last_error = ""
                self.last_provider = "xai"
                return result

        # Both providers failed (or are unconfigured)
        if not self.is_minimax_configured and not self.is_xai_configured:
            self.last_status = "unconfigured"
            self.last_error = "TTS not configured (no MINIMAX_API_KEY, no XAI_API_KEY)"
        else:
            self.last_status = "failed"
            attempted = "minimax" if self.is_minimax_configured else ""
            if self.is_xai_configured and not self.is_minimax_configured:
                attempted = "xai"
            elif self.is_minimax_configured and self.is_xai_configured:
                attempted = "minimax+xai"
            self.last_error = f"all TTS providers failed (attempted: {attempted})"
        self.last_provider = None
        return None

    async def synthesize_for_telegram(self, text: str) -> Optional[Path]:
        """Generate voice note for Telegram (mp3 — Telegram accepts it as voice)."""
        return await self.synthesize(text, output_format="mp3")

    async def synthesize_for_web(self, text: str) -> Optional[bytes]:
        """Generate audio bytes for web playback (mp3 format)."""
        # Reuse synthesize() for the audio file, then read the bytes.
        # This keeps the synthesize_for_web return contract (Optional[bytes])
        # while routing through the new primary/fallback logic.
        if not text or not text.strip():
            self.last_status = "failed"
            self.last_error = "empty text"
            return None
        audio_path = await self.synthesize(text, output_format="mp3")
        if audio_path is None:
            return None
        try:
            data = audio_path.read_bytes()
            try:
                audio_path.unlink(missing_ok=True)
            except Exception:
                pass
            return data
        except Exception as e:
            logger.error(f"xAI TTS web synthesis failed: {e}")
            self.last_status = "failed"
            self.last_error = str(e)[:300]
            return None

    def get_status(self) -> dict:
        return {
            "configured": self.is_configured,
            "last_status": self.last_status,
            "last_error": self.last_error,
            "last_provider": self.last_provider,
            "providers": {
                "minimax": {
                    "configured": self.is_minimax_configured,
                    "voice": os.getenv("MINIMAX_TTS_VOICE", MINIMAX_TTS_DEFAULT_VOICE),
                    "model": os.getenv("MINIMAX_TTS_MODEL", MINIMAX_TTS_DEFAULT_MODEL),
                },
                "xai": {
                    "configured": self.is_xai_configured,
                    "voice": TTS_VOICE,
                    "model": "grok-tts",
                },
            },
        }


# Singleton
tts_service = TTSService()
