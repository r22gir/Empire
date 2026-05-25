import asyncio
from pathlib import Path


def _write_png(path: Path) -> None:
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x01\x01\x01\x00"
        b"\x18\xdd\x8d\xb0\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def test_max_image_input_uses_mmx_vision_context_without_raw_image_payload(monkeypatch, tmp_path):
    from app.services.max import minimax_tools
    from app.services.max.ai_router import AIRouter, AIMessage, AIModel

    uploads = tmp_path / "uploads" / "images"
    uploads.mkdir(parents=True)
    image_path = uploads / "sample.png"
    _write_png(image_path)

    calls = {"vision": 0, "chat": 0}
    captured = {}

    async def fake_understand(path, prompt):
        calls["vision"] += 1
        assert path == str(image_path)
        assert "Do not generate a new image" in prompt
        return {
            "success": True,
            "model": "mmx_vision",
            "data": {"summary": "A red square with the word TEST centered on it."},
        }

    async def fake_minimax_chat(self, messages, image_path=None):
        calls["chat"] += 1
        assert image_path is None
        captured["last_message"] = messages[-1].content
        return "The image shows a red square with TEST text."

    async def fail_text_to_image(*args, **kwargs):
        raise AssertionError("image generation must not be called for MAX image understanding")

    monkeypatch.setattr(minimax_tools, "minimax_understand_image", fake_understand)
    monkeypatch.setattr(minimax_tools, "minimax_text_to_image", fail_text_to_image)
    monkeypatch.setattr(AIRouter, "_minimax_chat", fake_minimax_chat)

    router = AIRouter()
    router.upload_dirs = [tmp_path / "uploads"]
    router.upload_dir = tmp_path / "uploads"
    router.minimax_key = "configured-for-test"
    router.primary_model = AIModel.MINIMAX
    router.xai_key = ""
    router.anthropic_key = ""
    router.groq_key = ""
    router.openai_key = ""
    router.gemini_key = ""

    result = asyncio.run(
        router.chat(
            [AIMessage(role="user", content="Describe this image in one sentence. Do not generate a new image.")],
            image_filename="sample.png",
            source="web",
        )
    )

    assert calls == {"vision": 1, "chat": 1}
    assert result.model_used == f"minimax-{router.minimax_model}"
    assert "IMAGE_NOT_AVAILABLE" not in result.content
    assert "Image understanding via MiniMax mmx_cli" in captured["last_message"]
    assert "A red square with the word TEST" in captured["last_message"]
    assert "Image generation used: false" in captured["last_message"]
    assert "Answer the user directly" in captured["last_message"]


def test_max_image_vision_failure_returns_safe_error(monkeypatch, tmp_path):
    from app.services.max import minimax_tools
    from app.services.max.ai_router import AIRouter, AIMessage, AIModel

    uploads = tmp_path / "uploads" / "images"
    uploads.mkdir(parents=True)
    image_path = uploads / "sample.png"
    _write_png(image_path)

    async def fake_understand(path, prompt):
        return {
            "success": False,
            "error": "usage limit exceeded for sk-testsecret1234567890",
        }

    async def fail_chat(*args, **kwargs):
        raise AssertionError("chat provider must not run after image understanding failure")

    monkeypatch.setattr(minimax_tools, "minimax_understand_image", fake_understand)
    monkeypatch.setattr(AIRouter, "_minimax_chat", fail_chat)

    router = AIRouter()
    router.upload_dirs = [tmp_path / "uploads"]
    router.upload_dir = tmp_path / "uploads"
    router.minimax_key = "configured-for-test"
    router.primary_model = AIModel.MINIMAX

    result = asyncio.run(
        router.chat(
            [AIMessage(role="user", content="Describe this image.")],
            image_filename="sample.png",
            source="web",
        )
    )

    assert result.model_used == "mmx-vision"
    assert result.fallback_used is False
    assert "MiniMax vision verification failed" in result.content
    assert "[KEY_REDACTED]" in result.content
    assert "sk-testsecret" not in result.content


def test_max_stream_image_input_uses_mmx_vision_context(monkeypatch, tmp_path):
    from app.services.max import minimax_tools
    from app.services.max.ai_router import AIRouter, AIMessage, AIModel

    uploads = tmp_path / "uploads" / "images"
    uploads.mkdir(parents=True)
    image_path = uploads / "stream.png"
    _write_png(image_path)

    captured = {}

    async def fake_understand(path, prompt):
        return {
            "success": True,
            "model": "mmx_vision",
            "data": {"summary": "A blue sample image used for streaming tests."},
        }

    async def fake_minimax_stream(self, messages, image_path=None):
        assert image_path is None
        captured["last_message"] = messages[-1].content
        yield "The image is a blue sample."

    monkeypatch.setattr(minimax_tools, "minimax_understand_image", fake_understand)
    monkeypatch.setattr(AIRouter, "_minimax_chat_stream", fake_minimax_stream)

    router = AIRouter()
    router.upload_dirs = [tmp_path / "uploads"]
    router.upload_dir = tmp_path / "uploads"
    router.minimax_key = "configured-for-test"
    router.primary_model = AIModel.MINIMAX
    router.xai_key = ""
    router.anthropic_key = ""
    router.groq_key = ""
    router.openai_key = ""
    router.gemini_key = ""

    async def collect():
        return [
            item
            async for item in router.chat_stream(
                [AIMessage(role="user", content="Describe this image. Do not generate a new image.")],
                image_filename="stream.png",
                source="web",
            )
        ]

    chunks = asyncio.run(collect())

    assert chunks == [("The image is a blue sample.", router.minimax_model)]
    assert "Image understanding via MiniMax mmx_cli" in captured["last_message"]
    assert "A blue sample image" in captured["last_message"]
    assert "Image generation used: false" in captured["last_message"]
    assert "Answer the user directly" in captured["last_message"]


def test_minimax_response_sanitizer_removes_image_self_talk_before_final_answer():
    from app.services.max.ai_router import AIRouter

    router = AIRouter()
    raw = (
        "Wait - there is already text there.\n"
        "Actually, looking at this more carefully, I should answer plainly.\n"
        "Let me do that.\n\n"
        "A bright dining room with a wood table and black-framed windows."
    )

    cleaned = router._sanitize_minimax_content(raw)

    assert cleaned == "A bright dining room with a wood table and black-framed windows."
    assert "Wait -" not in cleaned
    assert "Actually," not in cleaned
    assert "Let me" not in cleaned


def test_minimax_response_sanitizer_preserves_normal_answer():
    from app.services.max.ai_router import AIRouter

    router = AIRouter()
    raw = "Actually, the image shows a dining room with black-framed windows."

    assert router._sanitize_minimax_content(raw) == raw


def test_minimax_response_sanitizer_strips_think_tags():
    from app.services.max.ai_router import AIRouter

    router = AIRouter()
    raw = "<think>I should reason privately.</think>\nThe image shows a dining room."

    cleaned = router._sanitize_minimax_content(raw)

    assert cleaned == "The image shows a dining room."
    assert "<think>" not in cleaned


def test_max_router_accepts_canonical_upload_path(monkeypatch, tmp_path):
    import importlib

    max_router = importlib.import_module("app.routers.max.router")

    data_dir = tmp_path / "data"
    image_dir = data_dir / "uploads" / "images"
    image_dir.mkdir(parents=True)
    image_path = image_dir / "canonical.png"
    _write_png(image_path)

    monkeypatch.setenv("EMPIRE_DATA_DIR", str(data_dir))

    assert max_router._image_upload_path("canonical.png") == image_path
