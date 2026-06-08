"""Tests for the MiniMax-primary / xAI-fallback TTS pipeline.

The previous tts_service was xAI-only and started failing on 2026-06-07
with HTTP 429 (team monthly credit cap). This test pins the new
behaviour: MiniMax TTS is the primary path; xAI TTS is the fallback
when MiniMax fails; both providers must fail cleanly (None + clear
last_error) when both are unavailable.
"""
import os
import asyncio
import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

# Ensure the live venv is importable
LIVE_VENV = "/home/rg/empire-repo/backend/venv/lib/python3.12/site-packages"
if LIVE_VENV not in sys.path:
    sys.path.insert(0, LIVE_VENV)


# ── Helper: build a mock httpx response ────────────────────────────────────

def _httpx_resp(status_code: int, body: bytes = b"", text: str = ""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = body
    resp.text = text or (body.decode("utf-8", errors="ignore") if body else "")
    # async context manager protocol
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=None)
    return resp


def _mock_client(resp):
    """Build a context manager that returns the given response for any post()."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=cm)
    cm.__aexit__ = AsyncMock(return_value=None)
    client = MagicMock()
    client.post = AsyncMock(return_value=resp)
    # The synthesize path uses async with httpx.AsyncClient(...) as client
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


# ── 1. Both providers unconfigured ────────────────────────────────────────

def test_neither_provider_configured_returns_none(monkeypatch):
    """When no API key is set for either provider, synthesize() must
    return None and surface a clear last_error. Also, is_configured
    must be False so the voice_capability_truth endpoint reports
    correctly.
    """
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    # Reload the module to pick up the env change
    import importlib
    import app.services.max.tts_service as tts_mod
    importlib.reload(tts_mod)
    svc = tts_mod.TTSService()
    result = asyncio.run(svc.synthesize("hello world", output_format="mp3"))
    assert result is None
    assert svc.last_status == "unconfigured"
    assert "not configured" in svc.last_error.lower() or "no minimax_api_key" in svc.last_error.lower()
    assert svc.is_configured is False
    assert svc.last_provider is None


# ── 2. MiniMax primary success ────────────────────────────────────────────

def test_minimax_primary_success(monkeypatch):
    """When MiniMax TTS is configured and returns 200 + audio bytes,
    synthesize() must return the audio path, mark last_status=ok, and
    last_provider='minimax'. xAI must not be called at all.
    """
    monkeypatch.setenv("MINIMAX_API_KEY", "test-mm-key")
    monkeypatch.setenv("MINIMAX_BASE_URL", "https://api.test-minimax.io/v1")
    monkeypatch.delenv("XAI_API_KEY", raising=False)

    # Reload to pick up env
    import importlib
    import app.services.max.tts_service as tts_mod
    importlib.reload(tts_mod)
    svc = tts_mod.TTSService()

    fake_audio = b"\x00\x01\x02" * 2000  # ~6KB, > 500 byte threshold
    success_resp = _httpx_resp(200, body=fake_audio)

    with patch("app.services.max.tts_service.httpx.AsyncClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=success_resp)
        mock_client_cls.return_value = mock_client
        result = asyncio.run(svc.synthesize("hello from minimax", output_format="mp3"))

    assert result is not None, f"synthesize returned None; last_error={svc.last_error!r}"
    assert Path(result).exists()
    assert svc.last_status == "ok"
    assert svc.last_error == ""
    assert svc.last_provider == "minimax"
    # xAI must not have been called
    assert mock_client.post.call_count == 1
    # Cleanup
    try:
        Path(result).unlink(missing_ok=True)
    except Exception:
        pass


# ── 3. MiniMax failure → xAI fallback ────────────────────────────────────

def test_minimax_failure_falls_back_to_xai(monkeypatch):
    """If MiniMax returns 5xx, synthesize() must automatically try xAI.
    If xAI returns 200 + audio, the final result must be the xAI audio,
    last_provider='xai', and last_status='ok'.
    """
    monkeypatch.setenv("MINIMAX_API_KEY", "test-mm-key")
    monkeypatch.setenv("XAI_API_KEY", "test-xai-key")
    monkeypatch.setenv("MINIMAX_BASE_URL", "https://api.test-minimax.io/v1")

    import importlib
    import app.services.max.tts_service as tts_mod
    importlib.reload(tts_mod)
    svc = tts_mod.TTSService()

    minimax_fail = _httpx_resp(500, text="server down")
    xai_success = _httpx_resp(200, body=b"\x00\x01" * 1500)  # 3KB

    with patch("app.services.max.tts_service.httpx.AsyncClient") as mock_client_cls:
        # The client.post will be called twice (MiniMax fail, xAI success)
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=[minimax_fail, xai_success])
        mock_client_cls.return_value = mock_client
        result = asyncio.run(svc.synthesize("fallback test", output_format="mp3"))

    assert result is not None
    assert svc.last_status == "ok"
    assert svc.last_provider == "xai"
    assert mock_client.post.call_count == 2, f"expected 2 calls, got {mock_client.post.call_count}"
    # The first call must have been to MiniMax, the second to xAI
    first_url = mock_client.post.call_args_list[0].args[0]
    second_url = mock_client.post.call_args_list[1].args[0]
    assert "/audio/speech" in first_url, f"first call should be MiniMax, got {first_url}"
    assert "api.x.ai" in second_url, f"second call should be xAI, got {second_url}"
    # Cleanup
    try:
        Path(result).unlink(missing_ok=True)
    except Exception:
        pass


# ── 4. Both providers fail ───────────────────────────────────────────────

def test_both_providers_fail(monkeypatch):
    """If MiniMax returns 5xx and xAI also returns 5xx, synthesize() must
    return None, set last_status='failed', and last_error mentions both
    providers so an operator can diagnose.
    """
    monkeypatch.setenv("MINIMAX_API_KEY", "test-mm-key")
    monkeypatch.setenv("XAI_API_KEY", "test-xai-key")

    import importlib
    import app.services.max.tts_service as tts_mod
    importlib.reload(tts_mod)
    svc = tts_mod.TTSService()

    minimax_fail = _httpx_resp(500, text="mm down")
    xai_fail = _httpx_resp(429, text="xai quota exceeded")

    with patch("app.services.max.tts_service.httpx.AsyncClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=[minimax_fail, xai_fail])
        mock_client_cls.return_value = mock_client
        result = asyncio.run(svc.synthesize("both fail", output_format="mp3"))

    assert result is None
    assert svc.last_status == "failed"
    assert "minimax" in svc.last_error and "xai" in svc.last_error
    assert svc.last_provider is None


# ── 5. is_configured contract preserved ─────────────────────────────────

def test_is_configured_true_if_either_provider(monkeypatch):
    """is_configured must be True if EITHER provider has its key, to
    preserve the original xAI-only contract while not lying about
    MiniMax-only deployments.
    """
    monkeypatch.setenv("MINIMAX_API_KEY", "mm")
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    import importlib
    import app.services.max.tts_service as tts_mod
    importlib.reload(tts_mod)
    svc = tts_mod.TTSService()
    assert svc.is_configured is True
    assert svc.is_minimax_configured is True
    assert svc.is_xai_configured is False

    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    monkeypatch.setenv("XAI_API_KEY", "xai")
    importlib.reload(tts_mod)
    svc = tts_mod.TTSService()
    assert svc.is_configured is True
    assert svc.is_minimax_configured is False
    assert svc.is_xai_configured is True


# ── 6. synthesize_for_telegram preserves the public API ─────────────────

def test_synthesize_for_telegram_calls_synthesize(monkeypatch):
    """synthesize_for_telegram() must continue to return Optional[Path]
    and delegate to synthesize() with output_format='mp3'. The Telegram
    bot calls this method directly.
    """
    monkeypatch.setenv("MINIMAX_API_KEY", "test-mm-key")
    monkeypatch.setenv("MINIMAX_BASE_URL", "https://api.test-minimax.io/v1")
    monkeypatch.delenv("XAI_API_KEY", raising=False)

    import importlib
    import app.services.max.tts_service as tts_mod
    importlib.reload(tts_mod)
    svc = tts_mod.TTSService()

    fake_audio = b"\x00" * 2000
    success_resp = _httpx_resp(200, body=fake_audio)

    with patch("app.services.max.tts_service.httpx.AsyncClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=success_resp)
        mock_client_cls.return_value = mock_client
        result = asyncio.run(svc.synthesize_for_telegram("voice note test"))

    assert result is not None
    assert svc.last_provider == "minimax"
    # Cleanup
    try:
        Path(result).unlink(missing_ok=True)
    except Exception:
        pass


# ── 7. get_status surfaces provider detail ───────────────────────────────

def test_get_status_surfaces_both_providers(monkeypatch):
    """get_status() must report per-provider configured state and the
    last_provider used. The voice_capability_truth endpoint and the
    ContinuityPanel UI both rely on this.
    """
    monkeypatch.setenv("MINIMAX_API_KEY", "mm")
    monkeypatch.setenv("XAI_API_KEY", "xai")
    import importlib
    import app.services.max.tts_service as tts_mod
    importlib.reload(tts_mod)
    svc = tts_mod.TTSService()
    status = svc.get_status()
    assert status["configured"] is True
    assert "providers" in status
    assert status["providers"]["minimax"]["configured"] is True
    assert status["providers"]["xai"]["configured"] is True
    # The voice_id default is from MINIMAX_TTS_VOICE or the hardcoded fallback
    assert "voice" in status["providers"]["minimax"]
    assert "model" in status["providers"]["minimax"]
    assert status["providers"]["xai"]["voice"] == "rex"
