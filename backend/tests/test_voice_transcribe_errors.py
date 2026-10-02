"""Voice transcription failures are HTTP errors, not chat text.

Does not import app.main (that path warns when FOUNDER_PIN is unset).
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.testclient import TestClient

from app.services.max.stt_http import normalize_stt_language, transcript_is_failure
from app.services.max.stt_service import STTService, stt_service

_SAFE = "Could not transcribe that recording"
_AUDIO = b"\x00" * 400


def _client() -> TestClient:
    app = FastAPI()

    @app.post("/api/v1/voice/transcribe")
    async def route(audio: UploadFile = File(...), language: str | None = None):
        from app.services.max.stt_http import transcribe_upload

        return await transcribe_upload(audio, language)

    return TestClient(app)


def _patch_stt(monkeypatch, result="hola, una cotización", *, configured=True, boom: Exception | None = None):
    seen: dict = {}

    async def fake_transcribe(path, language=None):
        seen["path"] = str(path)
        seen["language"] = language
        if boom is not None:
            raise boom
        return result

    monkeypatch.setattr(STTService, "is_configured", property(lambda self: configured))
    monkeypatch.setattr(stt_service, "transcribe", fake_transcribe)
    return seen


def test_language_blank_and_auto_do_not_become_english():
    assert normalize_stt_language(None) is None
    assert normalize_stt_language("") is None
    assert normalize_stt_language("auto") is None
    assert normalize_stt_language("en") == "en"
    assert normalize_stt_language("es") == "es"
    assert transcript_is_failure("[Transcription failed: could not process file]") is True
    assert transcript_is_failure("necesito tela de lino") is False


def test_groq_failure_string_is_502_without_a_text_field(monkeypatch):
    _patch_stt(monkeypatch, "[Transcription failed: could not process file]")
    res = _client().post(
        "/api/v1/voice/transcribe",
        files={"audio": ("recording.mp4", _AUDIO, "audio/mp4")},
    )
    body = res.json()
    assert res.status_code == 502
    assert "text" not in body
    assert body["detail"] == _SAFE
    assert "Transcription failed" not in res.text
    assert "could not process" not in res.text


def test_groq_exception_is_502_and_does_not_leak_the_error(monkeypatch):
    _patch_stt(monkeypatch, boom=RuntimeError("could not process file LEAKED_GROQ_DETAIL"))
    res = _client().post(
        "/api/v1/voice/transcribe",
        files={"audio": ("recording.webm", _AUDIO, "audio/webm")},
    )
    assert res.status_code == 502
    assert res.json() == {"detail": _SAFE}
    assert "LEAKED_GROQ_DETAIL" not in res.text


def test_unconfigured_stt_is_503(monkeypatch):
    _patch_stt(monkeypatch, configured=False)
    res = _client().post(
        "/api/v1/voice/transcribe",
        files={"audio": ("recording.mp4", _AUDIO, "audio/mp4")},
    )
    assert res.status_code == 503
    assert "text" not in res.json()


def test_tiny_upload_is_400(monkeypatch):
    seen = _patch_stt(monkeypatch)
    res = _client().post(
        "/api/v1/voice/transcribe",
        files={"audio": ("recording.mp4", b"tiny", "audio/mp4")},
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "Recording was too short"
    assert "path" not in seen


def test_omitted_language_is_autodetect_and_spanish_is_passed(monkeypatch):
    seen = _patch_stt(monkeypatch, "hola")
    client = _client()
    ok = client.post(
        "/api/v1/voice/transcribe",
        files={"audio": ("recording.mp4", _AUDIO, "audio/mp4")},
    )
    assert ok.status_code == 200
    assert ok.json()["text"] == "hola"
    assert ok.json()["language"] is None
    assert seen["language"] is None
    assert seen["path"].endswith(".mp4")

    seen.clear()
    es = client.post(
        "/api/v1/voice/transcribe?language=es",
        files={"audio": ("clip.m4a", _AUDIO, "audio/mp4")},
    )
    assert es.status_code == 200
    assert es.json()["language"] == "es"
    assert seen["language"] == "es"

    auto = client.post(
        "/api/v1/voice/transcribe?language=auto",
        files={"audio": ("recording.mp4", _AUDIO, "audio/mp4")},
    )
    assert auto.status_code == 200
    assert auto.json()["language"] is None


def test_transcribe_routes_do_not_default_language_to_english():
    main = (Path(__file__).resolve().parents[1] / "app" / "main.py").read_text()
    start = main.index("async def _do_transcribe")
    block = main[start:start + 900]
    assert "transcribe_upload" in block
    assert 'language: str = "en"' not in block
    assert "language: str | None = None" in block
