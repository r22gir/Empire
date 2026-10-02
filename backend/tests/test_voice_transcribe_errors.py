"""A failed transcription is an HTTP error, not text for the model."""
from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path

import pytest
from fastapi import HTTPException

# app.services.max.__init__ imports Telegram. Load the STT module beside it.
_MAX = Path(__file__).resolve().parents[1] / "app" / "services" / "max"
if "app.services.max" not in sys.modules:
    _pkg = types.ModuleType("app.services.max")
    _pkg.__path__ = [str(_MAX)]
    _pkg.__package__ = "app.services.max"
    sys.modules["app.services.max"] = _pkg


def test_language_es_is_kept_and_english_is_not_the_default():
    from app.services.max.stt_http import normalize_stt_language, transcript_is_failure

    assert normalize_stt_language("es") == "es"
    assert normalize_stt_language("es-CO") == "es-co"
    assert normalize_stt_language(None) is None
    assert normalize_stt_language("auto") is None
    assert normalize_stt_language("") is None
    assert transcript_is_failure("[Transcription failed: could not process file]") is True
    assert transcript_is_failure("hola, una cotización") is False


def test_short_clip_and_groq_failure_are_not_success(monkeypatch):
    from app.services.max import stt_http
    from app.services.max import stt_service as stt_module

    class FakeUpload:
        filename = "recording.webm"
        content_type = "audio/webm"

        def __init__(self, payload: bytes):
            self._payload = payload

        async def read(self):
            return self._payload

    class FakeSTT:
        is_configured = True

        async def transcribe(self, _path, language=None):
            assert language == "es"
            return "[Transcription failed: could not process file]"

    monkeypatch.setattr(stt_module, "stt_service", FakeSTT())
    with pytest.raises(HTTPException) as short:
        asyncio.run(stt_http.transcribe_upload(FakeUpload(b"tiny"), "es"))
    assert short.value.status_code == 400

    with pytest.raises(HTTPException) as failed:
        asyncio.run(stt_http.transcribe_upload(FakeUpload(b"x" * 400), "es"))
    assert failed.value.status_code == 502
    assert "text" not in (failed.value.detail if isinstance(failed.value.detail, dict) else {})


def test_unconfigured_stt_is_503(monkeypatch):
    from app.services.max import stt_http
    from app.services.max import stt_service as stt_module

    monkeypatch.setattr(stt_module, "stt_service", types.SimpleNamespace(is_configured=False))

    class FakeUpload:
        filename = "recording.mp4"
        content_type = "audio/mp4"

        async def read(self):
            return b"x" * 400

    with pytest.raises(HTTPException) as exc:
        asyncio.run(stt_http.transcribe_upload(FakeUpload(), None))
    assert exc.value.status_code == 503


def test_voice_capture_helpers_match_the_chat_mic():
    import subprocess
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    script = r"""
import {
  HOLD_LONGER_HINT,
  clipTooShort,
  filenameForMime,
  micToast,
  pointerDownAction,
  recorderFormat,
  shouldStopOnPointerUp,
  sttLanguage,
  transcriptIsFailure,
} from './empire-command-center/app/lib/voiceCapture.mjs';
const iphone = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 Version/17.5 Mobile/15E148 Safari/604.1';
if (pointerDownAction({ touchDevice: true, alreadyRecording: false }) !== 'start') throw new Error('start');
if (shouldStopOnPointerUp({ touchDevice: true, holdArmed: false }) !== false) throw new Error('tap lift');
if (pointerDownAction({ touchDevice: true, alreadyRecording: true }) !== 'stop') throw new Error('stop');
if (shouldStopOnPointerUp({ touchDevice: false, holdArmed: true }) !== true) throw new Error('mouse');
if (clipTooShort(499) !== true || clipTooShort(500) !== false) throw new Error('clip');
if (HOLD_LONGER_HINT !== 'Hold longer') throw new Error('hint');
if (micToast('short', 'es') !== 'Mantén un poco más') throw new Error('es short');
if (micToast('failed', 'es') !== 'No pude transcribir esa grabación') throw new Error('es fail');
const safari = recorderFormat(iphone, () => false);
if (safari.mimeType !== 'audio/mp4' || safari.filename !== 'recording.mp4') throw new Error('safari');
if (filenameForMime('audio/mp4') !== 'recording.mp4') throw new Error('name');
if (sttLanguage('es') !== 'es' || sttLanguage('en') !== null || sttLanguage(null) !== null) throw new Error('lang');
if (transcriptIsFailure('[Transcription failed: could not process file]') !== true) throw new Error('fail');
if (transcriptIsFailure('hola, necesito una cotización') !== false) throw new Error('ok text');
process.stdout.write('ok');
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout == "ok"
    screen = (root / "empire-command-center" / "app" / "components" / "screens" / "ChatScreen.tsx").read_text(encoding="utf-8")
    assert "pointerDownAction" in screen
    assert "transcriptIsFailure" in screen
    assert "audio/webm" not in screen.split("startVoiceCapture")[1].split("stopVoiceCapture")[0]
