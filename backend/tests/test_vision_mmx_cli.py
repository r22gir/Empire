"""Regression tests for /api/v1/vision MiniMax image-understanding transport."""
import asyncio
import base64
import json
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


def _quote_review_items(data: dict) -> list:
    """Same selector as QuoteReviewScreen.handleAnalyze (Found N item(s))."""
    analysis = data.get("analysis") if isinstance(data.get("analysis"), dict) else {}
    return data.get("items") or analysis.get("items") or data.get("analyzed_items") or []


def _items_mmx_result(items: list, **extra) -> dict:
    payload = {
        "room_type": "residential_living",
        "style": "traditional",
        "items": items,
        "overall_notes": "Floor-length pinch pleat panels.",
        "questions": [],
    }
    payload.update(extra)
    return {
        "success": True,
        "model": "mmx_vision",
        "data": {
            "full_response": (
                "<think>hidden</think>\n```json\n"
                + json.dumps(payload)
                + "\n```"
            )
        },
    }


def test_mockup_schema_still_keeps_proposal_json(monkeypatch):
    """The mockup endpoint must still accept proposal JSON without the items formatter."""
    from app.routers import vision

    async def forbidden_items(*args, **kwargs):
        raise AssertionError("mockup path must not use the items formatter")

    monkeypatch.setattr(vision, "_format_mmx_prose_to_items_schema", forbidden_items)

    result = asyncio.run(vision._parsed_json_from_minimax_result({
        "success": True,
        "model": "mmx_vision",
        "data": {"full_response": json.dumps({
            "room_assessment": {"room_type": "living room"},
            "proposals": [{"tier": "Elegant Essential"}],
        })},
    }))

    assert result["proposals"][0]["tier"] == "Elegant Essential"
    assert result["_vision_runtime"]["format_status"] == "direct_parse"
    assert "result_schema" not in result["_vision_runtime"]


def test_items_schema_drops_mockup_proposals_when_items_are_present():
    """A mixed MiniMax payload keeps line items and does not stay proposals-only."""
    from app.routers import vision

    result = asyncio.run(vision._parsed_json_from_minimax_result(
        _items_mmx_result(
            [{
                "name": "Roman shade",
                "type": "roman_shade",
                "quantity": 1,
                "dimensions": {"width": 48, "height": 60, "depth": 0},
            }],
            proposals=[{"tier": "Elegant Essential"}],
            room_assessment={"room_type": "living room"},
        ),
        result_schema="items",
    ))

    assert "proposals" not in result
    assert len(result["items"]) == 1
    assert result["items"][0]["type"] == "roman_shade"
    assert result["_vision_runtime"]["format_status"] == "direct_parse"


def test_analyze_items_does_not_rewrite_minimax_items_into_mockup_proposals(monkeypatch, tmp_path):
    """MiniMax JSON that already has items[] must not become proposals-only."""
    from app.routers import vision

    async def fake_understand(image, prompt="Describe what you see in this image in detail.", model=""):
        return _items_mmx_result([{
            "name": "Pinch pleat drapery",
            "type": "drapery_panel",
            "quantity": 2,
            "dimensions": {"width": 48, "height": 96, "depth": 0},
            "notes": "Left window, floor length",
        }])

    async def forbidden_formatter(*args, **kwargs):
        raise AssertionError("mockup formatter must not rewrite analyze-items JSON that already has items")

    async def forbidden_chat(*args, **kwargs):
        raise AssertionError("chat formatter must not run when MiniMax already returned items")

    monkeypatch.setattr(vision, "VISION_INPUT_DIR", tmp_path)
    monkeypatch.setattr(vision, "minimax_understand_image", fake_understand)
    monkeypatch.setattr(vision, "_format_mmx_prose_to_schema", forbidden_formatter)
    monkeypatch.setattr(vision, "_format_mmx_prose_to_items_schema", forbidden_formatter)
    monkeypatch.setattr(vision.ai_router, "chat", forbidden_chat)

    result = asyncio.run(vision.analyze_items(vision.AnalyzeItemsRequest(
        image=_png_data_uri(),
        prompt="Return items JSON",
    )))

    assert "proposals" not in result
    assert result["_vision_runtime"]["format_status"] == "direct_parse"
    assert result["_vision_runtime"]["result_schema"] == "items"
    item = result["items"][0]
    assert item["name"] == "Pinch pleat drapery"
    assert item["type"] == "drapery_panel"
    assert item["quantity"] == 2
    assert item["description"] == "Pinch pleat drapery"
    assert item["width"] == 48
    assert item["height"] == 96

    # Quote Review toasts Found ${items.length} from analysis.items.
    wrapped = {"analysis": result, "quote": {}, "verification": {}}
    found = _quote_review_items(wrapped)
    assert len(found) == 1


def test_analyze_items_prose_uses_items_formatter_not_mockup_schema(monkeypatch, tmp_path):
    """When mmx returns prose, analyze-items formats items[] — not 3 mockup proposals."""
    from app.routers import vision

    prompts = []

    async def fake_understand(image, prompt="Describe what you see in this image in detail.", model=""):
        return {
            "success": True,
            "model": "mmx_vision",
            "data": {"full_response": "Two floor-length pinch-pleat drapery panels cover a wide living-room window."},
        }

    async def fake_chat(messages, model=None, system_prompt=None, source="", **kwargs):
        prompts.append({"content": messages[0].content, "system": system_prompt, "source": source})
        body = {
            "room_type": "residential_living",
            "style": "traditional",
            "items": [{
                "name": "Living room window panels",
                "type": "drapery_panel",
                "quantity": 2,
                "dimensions": {"width": 48, "height": 96, "depth": 0},
            }],
            "overall_notes": "Estimated from the photo description.",
            "questions": [],
        }
        return types.SimpleNamespace(content=json.dumps(body), model_used="minimax-test")

    async def forbidden_mockup_formatter(*args, **kwargs):
        raise AssertionError("analyze-items must not use the mockup proposal formatter")

    monkeypatch.setattr(vision, "VISION_INPUT_DIR", tmp_path)
    monkeypatch.setattr(vision, "minimax_understand_image", fake_understand)
    monkeypatch.setattr(vision, "_format_mmx_prose_to_schema", forbidden_mockup_formatter)
    monkeypatch.setattr(vision.ai_router, "chat", fake_chat)

    result = asyncio.run(vision.analyze_items(vision.AnalyzeItemsRequest(
        image=_png_data_uri(),
        prompt="Identify quotable items",
    )))

    assert prompts and prompts[0]["source"] == "vision_items_formatter"
    assert "Elegant Essential" not in prompts[0]["content"]
    assert '"items"' in prompts[0]["content"]
    assert "proposals" not in result
    assert result["_vision_runtime"]["format_status"] == "items_formatter"
    assert len(_quote_review_items({"analysis": result})) == 1
    assert result["items"][0]["type"] == "drapery_panel"


def test_analyze_items_does_not_return_proposals_only_formatter_output(monkeypatch, tmp_path):
    """A mockup-shaped formatter reply must not become the analyze-items body."""
    from app.routers import vision

    async def fake_understand(image, prompt="Describe what you see in this image in detail.", model=""):
        return {
            "success": True,
            "model": "mmx_vision",
            "data": {"full_response": "Tan drapes on a living room window."},
        }

    async def mockup_shaped_chat(messages, **kwargs):
        body = {
            "room_assessment": {"room_type": "living room", "style": "traditional"},
            "window_info": {"type": "double-hung", "estimated_width": 48, "estimated_height": 60},
            "proposals": [
                {"tier": "Elegant Essential", "treatment_type": "drapery"},
                {"tier": "Designer's Choice", "treatment_type": "roman shade"},
                {"tier": "Ultimate Luxury", "treatment_type": "layered drapery"},
            ],
            "confidence": 78,
            "notes": "Color palette inferred from a traditional style brief",
        }
        return types.SimpleNamespace(content=json.dumps(body), model_used="minimax-test")

    async def forbidden_notify(*args, **kwargs):
        raise AssertionError("items path must not fire mockup F4")

    monkeypatch.setattr(vision, "VISION_INPUT_DIR", tmp_path)
    monkeypatch.setattr(vision, "minimax_understand_image", fake_understand)
    monkeypatch.setattr(vision.ai_router, "chat", mockup_shaped_chat)
    monkeypatch.setattr(vision, "_notify_f4_fallback", forbidden_notify)

    result = asyncio.run(vision.analyze_items(vision.AnalyzeItemsRequest(
        image=_png_data_uri(),
        prompt="Identify quotable items",
    )))

    assert result.get("items") == []
    assert "proposals" not in result
    assert "room_assessment" not in result
    assert result["_vision_runtime"]["format_status"] == "items_formatter_fallback"
    assert _quote_review_items({"analysis": result}) == []


def test_measure_schema_keeps_flat_inches_without_mockup_formatter(monkeypatch):
    """A measure JSON object must not be rewritten into design proposals."""
    from app.routers import vision

    async def forbidden_formatter(*args, **kwargs):
        raise AssertionError("measure JSON with width_inches must not use the mockup formatter")

    monkeypatch.setattr(vision, "_format_mmx_prose_to_schema", forbidden_formatter)

    result = asyncio.run(vision._parsed_json_from_minimax_result({
        "success": True,
        "model": "mmx_vision",
        "data": {"full_response": json.dumps({
            "width_inches": 36,
            "height_inches": 60,
            "confidence": 80,
            "window_type": "double-hung",
        })},
    }, result_schema="measure"))

    assert result["width_inches"] == 36
    assert result["height_inches"] == 60
    assert result["window_type"] == "double-hung"
    assert result["_vision_runtime"]["format_status"] == "direct_parse"
    assert result["_vision_runtime"]["result_schema"] == "measure"


def test_measure_schema_lifts_nested_window_info_dims():
    """window_info.estimated_width/height become the flats Save-to-Quote reads."""
    from app.routers import vision

    result = asyncio.run(vision._parsed_json_from_minimax_result({
        "success": True,
        "model": "mmx_vision",
        "data": {"full_response": json.dumps({
            "window_info": {
                "type": "casement",
                "estimated_width": 48,
                "estimated_height": 72,
                "current_treatment": None,
            },
            "confidence": 70,
            "notes": "Scaled from a door.",
        })},
    }, result_schema="measure"))

    assert result["width_inches"] == 48
    assert result["height_inches"] == 72
    assert result["window_type"] == "casement"
    assert result["_vision_runtime"]["format_status"] == "direct_parse"


def test_measure_endpoint_lifts_nested_dims_and_skips_formatter(monkeypatch, tmp_path):
    from app.routers import vision

    async def fake_understand(image, prompt="Describe what you see in this image in detail.", model=""):
        return {
            "success": True,
            "model": "mmx_vision",
            "data": {"full_response": json.dumps({
                "window_info": {"type": "double-hung", "estimated_width": 32, "estimated_height": 54},
            })},
        }

    async def forbidden_formatter(*args, **kwargs):
        raise AssertionError("direct measure JSON must not call the mockup formatter")

    monkeypatch.setattr(vision, "VISION_INPUT_DIR", tmp_path)
    monkeypatch.setattr(vision, "minimax_understand_image", fake_understand)
    monkeypatch.setattr(vision, "_format_mmx_prose_to_schema", forbidden_formatter)

    result = asyncio.run(vision.measure(vision.ImageRequest(image=_png_data_uri())))

    assert result["width_inches"] == 32
    assert result["height_inches"] == 54
    assert result["window_type"] == "double-hung"


def test_normalize_measure_result_does_not_overwrite_positive_flats():
    from app.routers.vision import normalize_measure_result

    result = normalize_measure_result({
        "width_inches": 30,
        "height_inches": 40,
        "window_type": "picture",
        "window_info": {"type": "casement", "estimated_width": 99, "estimated_height": 99},
    })
    assert result["width_inches"] == 30
    assert result["height_inches"] == 40
    assert result["window_type"] == "picture"


def test_measure_prose_formatter_output_is_lifted(monkeypatch):
    """When mmx returns prose, the formatter's window_info still fills the flats."""
    from app.routers import vision

    async def fake_format(prose, source_model):
        return {
            "window_info": {"type": "awning", "estimated_width": 28, "estimated_height": 36},
            "proposals": [],
            "_vision_runtime": {"format_status": "two_stage_formatter", "model": source_model},
        }

    monkeypatch.setattr(vision, "_format_mmx_prose_to_schema", fake_format)

    result = asyncio.run(vision._parsed_json_from_minimax_result({
        "success": True,
        "model": "mmx_vision",
        "data": {"full_response": "A small awning window beside the door."},
    }, result_schema="measure"))

    assert result["width_inches"] == 28
    assert result["height_inches"] == 36
    assert result["window_type"] == "awning"
