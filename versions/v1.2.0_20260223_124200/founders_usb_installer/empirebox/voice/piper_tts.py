"""Text-to-Speech using piper-tts."""

import io
import logging
import os
import subprocess
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)

# Cache loaded voice objects to avoid re-initialisation on every request
_voices: dict = {}

MODELS_DIR = os.environ.get("PIPER_MODELS_DIR", "/app/models/piper")


def _get_voice(voice_name: str):
    """Return a cached piper Voice instance, loading it if necessary."""
    if voice_name not in _voices:
        try:
            from piper import PiperVoice  # type: ignore
            model_path = os.path.join(MODELS_DIR, f"{voice_name}.onnx")
            config_path = os.path.join(MODELS_DIR, f"{voice_name}.onnx.json")
            if not os.path.exists(model_path):
                raise FileNotFoundError(
                    f"Piper model not found: {model_path}. "
                    "Download it with: python -m piper.download --voice "
                    f"{voice_name} --output-dir {MODELS_DIR}"
                )
            logger.info("Loading Piper voice '%s' …", voice_name)
            _voices[voice_name] = PiperVoice.load(model_path, config_path=config_path)
            logger.info("Piper voice '%s' loaded.", voice_name)
        except ImportError:
            # Fallback: invoke the piper binary via subprocess
            _voices[voice_name] = None
    return _voices[voice_name]


def synthesise(
    text: str,
    voice: str = "en_US-amy-medium",
    output_format: str = "mp3",
    speed: float = 1.0,
) -> bytes:
    """Convert *text* to audio bytes.

    Tries the Python piper library first; falls back to the ``piper``
    command-line binary if the library is unavailable.

    Args:
        text: Input text to synthesise.
        voice: Piper voice identifier.
        output_format: ``"mp3"`` or ``"ogg"``.
        speed: Playback speed multiplier (1.0 = normal).

    Returns:
        Audio data as bytes.
    """
    piper_voice = _get_voice(voice)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_tmp:
        wav_path = wav_tmp.name

    try:
        if piper_voice is not None:
            # Library path: synthesise to WAV in memory
            with open(wav_path, "wb") as wav_file:
                import wave
                with wave.open(wav_file, "wb") as wf:
                    piper_voice.synthesize(text, wf, length_scale=1.0 / speed)
        else:
            # CLI fallback
            model_path = os.path.join(MODELS_DIR, f"{voice}.onnx")
            result = subprocess.run(
                ["piper", "--model", model_path, "--output_file", wav_path],
                input=text.encode(),
                capture_output=True,
                timeout=60,
                check=True,
            )

        return _convert_wav(wav_path, output_format)
    finally:
        if os.path.exists(wav_path):
            os.unlink(wav_path)


def _convert_wav(wav_path: str, output_format: str) -> bytes:
    """Convert a WAV file to *output_format* and return bytes."""
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_wav(wav_path)
        buf = io.BytesIO()
        fmt = "mp3" if output_format == "mp3" else "ogg"
        audio.export(buf, format=fmt)
        return buf.getvalue()
    except ImportError:
        # Return raw WAV if pydub is unavailable
        with open(wav_path, "rb") as fh:
            return fh.read()
