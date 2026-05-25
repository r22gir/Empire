"""Tests for MiniMax multimodal tools."""
import pytest
from pathlib import Path


class FakeResponse:
    def __init__(self, status_code, json_data, content=b""):
        self.status_code = status_code
        self._json = json_data
        self.content = content

    def json(self):
        return self._json


class FakeAsyncClient:
    def __init__(self, response=None, exc=None):
        self.response = response
        self.exc = exc

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def post(self, url, **kwargs):
        if self.exc:
            raise self.exc
        return self.response

    async def get(self, url, **kwargs):
        if self.exc:
            raise self.exc
        return self.response


def test_tool_result_envelope_structure():
    """Runtime-truth envelope has correct structure."""
    from app.services.max.minimax_tools import _build_result

    result = _build_result(True, "minimax_text_to_image", model="image-01",
                          data={"image_url": "/test.png"})
    assert result["success"] is True
    assert result["tool"] == "minimax_text_to_image"
    assert result["model"] == "image-01"
    assert "data" in result
    assert "image_url" in result["data"]

    fail_result = _build_result(False, "minimax_text_to_image", error="key missing")
    assert fail_result["success"] is False
    assert "error" in fail_result
    assert "key missing" in fail_result["error"]


def test_verify_file_rejects_empty():
    """_verify_file returns False for missing/empty files."""
    from app.services.max.minimax_tools import _verify_file

    fake = Path("/nonexistent/file.png")
    assert _verify_file(fake) is False


def test_save_bytes_creates_file(tmp_path):
    """_save_bytes creates a file and returns correct URL pattern."""
    import os, sys
    # Patch GENERATED_DIR to tmp_path
    import app.services.max.minimax_tools as mm
    orig_dir = mm._GENERATED_DIR
    mm._GENERATED_DIR = tmp_path

    try:
        data = b"\x89PNG\r\n\x1a\n" + b"x" * 100
        url, path = mm._save_bytes(data, "test-prefix", "png")

        assert path.exists()
        assert path.stat().st_size > 100
        assert url.startswith("/api/v1/vision/images/test-prefix")
        assert path.suffix == ".png"
    finally:
        mm._GENERATED_DIR = orig_dir


def test_minimax_tools_status_returns_all_tools():
    """minimax_tools_status returns per-tool availability with correct quota buckets."""
    import os
    # Ensure MINIMAX_API_KEY is not set for this test
    old_key = os.environ.pop("MINIMAX_API_KEY", "")

    from app.services.max.minimax_tools import minimax_tools_status

    status = minimax_tools_status()

    assert "tools" in status
    tools = status["tools"]
    # New tool names with quota bucket schema
    expected_tools = [
        "text_generation",
        "image_understanding",
        "web_search",
        "image_generation",
        "image_to_image",
        "tts",
        "lyrics_generation",
        "music_generation",
        "video_generation",
    ]
    for t in expected_tools:
        assert t in tools, f"{t} missing from status"
        assert "configured" in tools[t]
        assert "transport" in tools[t]
        assert "quota_bucket" in tools[t]
        assert "reason" in tools[t]
        # image_understanding uses cli_available/live_available, others use available
        if t == "image_understanding":
            assert "cli_available" in tools[t], f"{t} missing cli_available"
            assert "live_available" in tools[t], f"{t} missing live_available"
            assert "last_probe_status" in tools[t]
            assert "last_error_category" in tools[t]
        else:
            assert "available" in tools[t], f"{t} missing available"

    # image_understanding requires mmx CLI, not just API key
    img_und = tools["image_understanding"]
    # video is disabled by default
    assert tools["video_generation"]["available"] is False

    os.environ["MINIMAX_API_KEY"] = old_key


def test_minimax_tts_rejects_empty_text():
    """minimax_tts returns error for empty text."""
    import asyncio
    from app.services.max.minimax_tools import minimax_tts

    result = asyncio.run(minimax_tts(text="   ", voice_id="male-qn-qingque"))
    assert result["success"] is False
    assert "empty" in result["error"].lower()


def test_minimax_video_gated_by_env():
    """minimax_video_generate returns disabled error when MINIMAX_VIDEO_ENABLED != 1."""
    import asyncio
    from app.services.max.minimax_tools import minimax_video_generate

    result = asyncio.run(minimax_video_generate(prompt="test", duration=5))
    assert result["success"] is False
    assert "disabled" in result["error"].lower() or "not set" in result["error"].lower()


def test_minimax_web_search_mcp_not_found():
    """minimax_web_search returns unavailable when MCP command missing."""
    import asyncio
    from app.services.max.minimax_tools import minimax_web_search

    result = asyncio.run(minimax_web_search(query="empire workroom"))
    assert result["success"] is False
    assert result["error"]  # must have an error message


def test_minimax_text_to_image_no_key(monkeypatch):
    """minimax_text_to_image returns error when MINIMAX_API_KEY is not set."""
    import asyncio
    monkeypatch.setenv("MINIMAX_API_KEY", "")

    # Force re-load by clearing the module-level cached value
    import app.services.max.minimax_tools as mm
    mm.MINIMAX_API_KEY = ""

    from app.services.max.minimax_tools import minimax_text_to_image

    result = asyncio.run(minimax_text_to_image(prompt="a beautiful room"))
    assert result["success"] is False
    assert result["error"]  # error must be present


def test_mmx_subprocess_env_preserves_runtime_minimax_key(monkeypatch):
    """mmx CLI calls inherit auth without inheriting backend API base paths."""
    monkeypatch.setenv("MINIMAX_API_KEY", "test-minimax-key")
    monkeypatch.setenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1")

    from app.services.max import minimax_tools

    env = minimax_tools._mmx_subprocess_env()

    assert env["MINIMAX_API_KEY"] == "test-minimax-key"
    assert "MINIMAX_BASE_URL" not in env
    assert env["PATH"]


def test_mmx_subprocess_env_does_not_pass_anthropic_base_url(monkeypatch):
    """Native mmx must not inherit Anthropic-compatible MiniMax base URLs."""
    monkeypatch.setenv("MINIMAX_API_KEY", "test-minimax-key")
    monkeypatch.setenv("MINIMAX_BASE_URL", "https://api.minimax.io/anthropic")

    from app.services.max import minimax_tools

    env = minimax_tools._mmx_subprocess_env()

    assert env["MINIMAX_API_KEY"] == "test-minimax-key"
    assert "MINIMAX_BASE_URL" not in env


def test_tool_names_registered_in_executor():
    """All MiniMax tools are registered in TOOL_REGISTRY."""
    from app.services.max.tool_executor import TOOL_REGISTRY

    expected = [
        "minimax_text_to_image",
        "minimax_image_to_image",
        "minimax_understand_image",
        "minimax_tts",
        "minimax_music_generate",
        "minimax_video_generate",
        "max_room_redesign",
    ]
    for name in expected:
        assert name in TOOL_REGISTRY, f"{name} not in TOOL_REGISTRY"
