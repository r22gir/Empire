"""EmpireBox Voice Client SDK.

Usage in any product::

    from empirebox_sdk import VoiceClient

    voice = VoiceClient()

    # Text to Speech
    audio = voice.speak("Your order has shipped!")
    # Returns: bytes (audio file)

    # Speech to Text
    result = voice.transcribe(audio_bytes)
    # Returns: {"text": "...", "language": "en", "confidence": 0.95}

    # Check available voices
    voices = voice.list_voices()

    # Health check
    ok = voice.health_check()
"""

import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class VoiceClient:
    """HTTP client for the EmpireBox Voice Service."""

    def __init__(
        self,
        service_url: str = "http://voice-service:8200",
        timeout: int = 60,
    ):
        self.service_url = service_url.rstrip("/")
        self.timeout = timeout

    # ── Text to Speech ──────────────────────────────────────────────────────

    def speak(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
    ) -> bytes:
        """Convert *text* to speech and return the audio as bytes.

        Args:
            text: The text to synthesise.
            voice: Optional Piper voice name (e.g. ``"en_US-ryan-medium"``).
            speed: Optional playback speed multiplier.

        Returns:
            Audio file bytes (mp3 or ogg).

        Raises:
            requests.HTTPError: If the voice service returns an error.
        """
        data: dict = {"text": text}
        if voice is not None:
            data["voice"] = voice
        if speed is not None:
            data["speed"] = speed

        resp = requests.post(
            f"{self.service_url}/tts",
            data=data,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.content

    # ── Speech to Text ──────────────────────────────────────────────────────

    def transcribe(
        self,
        audio: bytes,
        language: str = "auto",
        filename: str = "audio.ogg",
    ) -> dict:
        """Transcribe *audio* bytes to text.

        Args:
            audio: Raw audio data (.ogg, .mp3, .wav, .m4a).
            language: ISO language code or ``"auto"`` for detection.
            filename: Hint for the content type (e.g. ``"audio.mp3"``).

        Returns:
            ``{"text": "...", "language": "en", "confidence": 0.95}``

        Raises:
            requests.HTTPError: If the voice service returns an error.
        """
        resp = requests.post(
            f"{self.service_url}/stt",
            files={"file": (filename, audio)},
            data={"language": language},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    # ── Voices ──────────────────────────────────────────────────────────────

    def list_voices(self) -> list:
        """Return the list of available TTS voice names.

        Raises:
            requests.HTTPError: If the voice service returns an error.
        """
        resp = requests.get(
            f"{self.service_url}/voices",
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json().get("voices", [])

    # ── Health ───────────────────────────────────────────────────────────────

    def health_check(self) -> bool:
        """Return ``True`` if the voice service is reachable and healthy."""
        try:
            resp = requests.get(
                f"{self.service_url}/health",
                timeout=5,
            )
            return resp.status_code == 200 and resp.json().get("status") == "ok"
        except requests.RequestException as exc:
            logger.debug("Voice service health check failed: %s", exc)
            return False
