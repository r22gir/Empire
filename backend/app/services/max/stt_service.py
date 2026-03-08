"""
Speech-to-Text service using Groq Whisper API.
Replaces local Whisper model with Groq's fast cloud API.
Free tier: 28,800 audio-seconds/day.
"""
import os
import httpx
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"


class STTService:
    """Transcribe audio files using Groq Whisper API."""

    @property
    def is_configured(self) -> bool:
        return bool(GROQ_API_KEY)

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
            return "[STT unavailable — GROQ_API_KEY not set]"

        # Check cache
        cache_path = audio_path.with_suffix(audio_path.suffix + '.transcript.txt')
        if cache_path.exists():
            return cache_path.read_text().strip()

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                with open(audio_path, 'rb') as f:
                    files = {'file': (audio_path.name, f, 'audio/mpeg')}
                    data = {'model': 'whisper-large-v3-turbo', 'response_format': 'text'}
                    if language:
                        data['language'] = language

                    response = await client.post(
                        GROQ_STT_URL,
                        headers={'Authorization': f'Bearer {GROQ_API_KEY}'},
                        files=files,
                        data=data,
                    )

            if response.status_code == 200:
                transcript = response.text.strip()
                # Cache result
                cache_path.write_text(transcript)
                logger.info(f"Transcribed {audio_path.name}: {len(transcript)} chars")
                return transcript
            else:
                logger.error(f"Groq STT error {response.status_code}: {response.text[:200]}")
                return f"[Transcription failed: HTTP {response.status_code}]"

        except httpx.TimeoutException:
            return "[Transcription timed out — audio may be too long]"
        except Exception as e:
            logger.error(f"STT error: {e}")
            return f"[Transcription failed: {e}]"

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
            with httpx.Client(timeout=120) as client:
                with open(audio_path, 'rb') as f:
                    files = {'file': (audio_path.name, f, 'audio/mpeg')}
                    data = {'model': 'whisper-large-v3-turbo', 'response_format': 'text'}
                    if language:
                        data['language'] = language

                    response = client.post(
                        GROQ_STT_URL,
                        headers={'Authorization': f'Bearer {GROQ_API_KEY}'},
                        files=files,
                        data=data,
                    )

            if response.status_code == 200:
                transcript = response.text.strip()
                cache_path.write_text(transcript)
                logger.info(f"Transcribed {audio_path.name}: {len(transcript)} chars")
                return transcript
            else:
                logger.error(f"Groq STT error {response.status_code}: {response.text[:200]}")
                return f"[Transcription failed: HTTP {response.status_code}]"

        except httpx.TimeoutException:
            return "[Transcription timed out — audio may be too long]"
        except Exception as e:
            logger.error(f"STT error: {e}")
            return f"[Transcription failed: {e}]"


# Singleton
stt_service = STTService()
