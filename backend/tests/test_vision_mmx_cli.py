"""Regression tests for /api/v1/vision MiniMax image-understanding transport."""
import asyncio
import base64
import os
import sys
import types
from io import BytesIO

import pytest
from fastapi import HTTPException
from PIL import Image

# D43 1d — opt-in env var controls access to the bad-payload fixture.
# Without opt-in, only real PNGs are produced by the default helpers, and
# the bad-payload helper skips its test. This prevents the 136-byte
# "PNG-magic + 128 'x'" fixture from being a vector for accidental
# production writes via test code. See reports/2026-08-27_d43_step0.md §0b.
_BAD_PAYLOAD_ENV = "EMPIRE_VISION_TEST_BAD_PAYLOAD_ALLOWED"


def _png_data_uri(width: int = 4, height: int = 3, color=(200, 100, 50)) -> str:
    """Default fixture: a real, valid PNG that PIL.Image.verify() accepts.

    D43 1a adds a decode-verify guard that rejects bare-byte padding.
    The default helpers construct a real PNG so routing tests can run
    unconditionally.
    """
    img = Image.new("RGB", (width, height), color)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _raw_png_base64(width: int = 4, height: int = 3, color=(200, 100, 50)) -> str:
    """Default fixture: bare base64 of a real PNG."""
    img = Image.new("RGB", (width, height), color)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _bad_png_payload() -> bytes:
    """Gated 136-byte "PNG-magic + 128 'x'" fixture.

    Returns the bytes only when EMPIRE_VISION_TEST_BAD_PAYLOAD_ALLOWED is
    set. Otherwise skips the calling test. The guard exists so this
    fixture cannot be invoked from production by accident — even via
    `from tests.test_vision_mmx_cli import _bad_png_payload`.
    """
    if not os.environ.get(_BAD_PAYLOAD_ENV):
        pytest.skip(
            f"Bad-payload fixture gated by {_BAD_PAYLOAD_ENV}=1 "
            f"(D43 1d — see reports/2026-08-27_d43_step0.md §0b)"
        )
    return b"\x89PNG\r\n\x1a\n" + (b"x" * 128)


def test_call_vision_uses_mmx_cli_wrapper_for_data_uri(monkeypatch, tmp_path):
    from app.routers import vision

    calls = []

    async def fake_understand(image, prompt="Describe what you see in this image in detail.", model=""):
        calls.append({"image": image, "prompt": prompt, "model": model})
        return {
            "success": True,
            "provider": "minimax",
            "model": "mmx_vision",
            "data": {
                "full_response": '{"width_inches": 42, "height_inches": 84, "confidence": 91}'
            },
        }

    monkeypatch.setattr(vision, "VISION_INPUT_DIR", tmp_path)
    monkeypatch.setattr(vision, "minimax_understand_image", fake_understand)

    result = asyncio.run(vision.call_vision("Return JSON", _png_data_uri()))

    assert result["width_inches"] == 42
    assert result["_vision_runtime"]["provider"] == "minimax"
    assert result["_vision_runtime"]["transport"] == "mmx_cli"
    assert result["_vision_runtime"]["quota_bucket"] == "mcp_understand_image"
    assert result["_vision_runtime"]["image_generation_used"] is False
    assert len(calls) == 1
    assert calls[0]["image"].endswith(".png")
    assert tmp_path.joinpath(calls[0]["image"].split("/")[-1]).exists()


def test_call_vision_does_not_use_minimax_chat_completions(monkeypatch, tmp_path):
    from app.routers import vision

    class ForbiddenAsyncClient:
        def __init__(self, *args, **kwargs):
            raise AssertionError("vision endpoint must not use chat/completions image payloads")

    async def fake_understand(image, prompt="Describe what you see in this image in detail.", model=""):
        return {
            "success": True,
            "provider": "minimax",
            "model": "mmx_vision",
            "data": {"full_response": '{"ok": true}'},
        }

    monkeypatch.setattr(vision, "VISION_INPUT_DIR", tmp_path)
    monkeypatch.setattr(vision, "minimax_understand_image", fake_understand)
    monkeypatch.setattr(vision.httpx, "AsyncClient", ForbiddenAsyncClient)

    result = asyncio.run(vision.call_vision("Return JSON", _png_data_uri()))

    assert result["ok"] is True


def test_call_vision_materializes_raw_base64_without_statting_as_path(monkeypatch, tmp_path):
    from app.routers import vision

    calls = []

    async def fake_understand(image, prompt="Describe what you see in this image in detail.", model=""):
        calls.append(image)
        return {
            "success": True,
            "provider": "minimax",
            "model": "mmx_vision",
            "data": {"full_response": '{"raw_base64": true}'},
        }

    monkeypatch.setattr(vision, "VISION_INPUT_DIR", tmp_path)
    monkeypatch.setattr(vision, "minimax_understand_image", fake_understand)

    result = asyncio.run(vision.call_vision("Return JSON", _raw_png_base64()))

    assert result["raw_base64"] is True
    assert calls and calls[0].endswith(".png")
    assert tmp_path.joinpath(calls[0].split("/")[-1]).exists()


def test_xai_fallback_is_disabled_without_explicit_policy(monkeypatch):
    from app.routers import vision

    async def fake_understand(image, prompt="Describe what you see in this image in detail.", model=""):
        return {"success": False, "error": "mmx unavailable", "data": {}}

    class ForbiddenAsyncClient:
        def __init__(self, *args, **kwargs):
            raise AssertionError("xAI fallback must not run unless explicitly enabled")

    monkeypatch.setenv("XAI_API_KEY", "xai-test-key")
    monkeypatch.delenv("VISION_ENABLE_XAI_FALLBACK", raising=False)
    monkeypatch.delenv("MAX_ENABLE_XAI_VISION_FALLBACK", raising=False)
    monkeypatch.setattr(vision, "minimax_understand_image", fake_understand)
    monkeypatch.setattr(vision.httpx, "AsyncClient", ForbiddenAsyncClient)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(vision.call_vision("Return JSON", _png_data_uri()))

    assert exc.value.status_code == 502
    assert "mmx unavailable" in str(exc.value.detail)


def test_call_vision_requires_image(monkeypatch):
    from app.routers import vision

    with pytest.raises(HTTPException) as exc:
        asyncio.run(vision.call_vision("Return JSON", ""))

    assert exc.value.status_code == 400
    assert "No image provided" in str(exc.value.detail)


def test_parsed_result_handles_think_blocks_and_keeps_quota_metadata():
    from app.routers.vision import _parsed_json_from_minimax_result

    result = _parsed_json_from_minimax_result({
        "success": True,
        "model": "mmx_vision",
        "data": {"full_response": '<think>hidden</think>\n{"summary": "Visible window", "confidence": 88}'},
    })

    assert result["summary"] == "Visible window"
    assert result["_vision_runtime"]["transport"] == "mmx_cli"
    assert result["_vision_runtime"]["quota_bucket"] == "mcp_understand_image"
    assert result["_vision_runtime"]["image_generation_used"] is False


def test_vision_status_separates_understanding_and_generation(monkeypatch):
    from app.routers import vision

    def fake_status():
        return {
            "tools": {
                "image_understanding": {
                    "configured": True,
                    "model": "mmx_vision",
                    "last_probe_status": "not_probed",
                    "last_error_category": None,
                    "last_error_message": None,
                },
                "image_generation": {"configured": True},
            }
        }

    monkeypatch.setattr(vision, "minimax_tools_status", fake_status)
    monkeypatch.delenv("VISION_LIVE_IMAGE_GENERATION_ALLOWED", raising=False)

    status = asyncio.run(vision.vision_status())

    assert status["vision_image_understanding"]["transport"] == "mmx_cli"
    assert status["vision_image_understanding"]["quota_bucket"] == "mcp_understand_image"
    assert status["vision_image_generation"]["quota_bucket"] == "image_generation"
    assert status["vision_image_generation"]["live_generation_allowed"] is False
    assert status["secrets_included"] is False


def test_measurements_pdf_uses_canonical_measurements_dir(monkeypatch, tmp_path):
    from app.routers import vision

    class FakeHTML:
        def __init__(self, string):
            self.string = string

        def write_pdf(self):
            return b"%PDF-1.4\nfake\n"

    monkeypatch.setitem(sys.modules, "weasyprint", types.SimpleNamespace(HTML=FakeHTML))
    monkeypatch.setattr(vision, "MEASUREMENTS_DIR", tmp_path)

    req = vision.MeasurementsPdfRequest(fileName="sample scan", measurements=[])
    response = asyncio.run(vision.measurements_pdf(req))

    assert response.media_type == "application/pdf"
    saved = list(tmp_path.glob("sample_scan_*.pdf"))
    assert saved
    assert b"%PDF" in saved[0].read_bytes()


def test_decode_image_input_rejects_lookalike_png_payload():
    """D43 1a — the 136-byte fixture (PNG-magic + 128 'x' padding) must raise.

    This is the bug that put 143 fake files in vision_inputs/. Without
    PIL.Image.verify() at the boundary, the magic-byte check accepted the
    payload. With 1a, the bytewise decoder rejects it as not decodable.

    The bad payload is gated by EMPIRE_VISION_TEST_BAD_PAYLOAD_ALLOWED;
    this test skips when the env var is unset.
    """
    from app.routers import vision

    payload = _bad_png_payload()  # gated — skips if env var unset
    uri = "data:image/png;base64," + base64.b64encode(payload).decode("ascii")

    with pytest.raises(HTTPException) as exc:
        vision._decode_image_input(uri)

    assert exc.value.status_code == 400
    assert "not a decodable image" in str(exc.value.detail).lower()
