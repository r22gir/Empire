"""Studio chat must pass attached photos to the model / drawing tools."""
import asyncio
import importlib
from pathlib import Path

from fastapi import BackgroundTasks, Response

from app.services.max.ai_router import AIResponse
from app.services.max.chat_attachments import (
    claims_photo_missing,
    sanitize_attached_photo_reply,
)
from app.services.max.tool_executor import ToolResult


PNG = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde"
    b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x01\x01\x01\x00"
    b"\x18\xdd\x8d\xb0\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _write_photo(tmp_path, monkeypatch, name="IMG_2265.jpeg") -> Path:
    data = tmp_path / "empire-data"
    img_dir = data / "uploads" / "images"
    img_dir.mkdir(parents=True)
    path = img_dir / name
    path.write_bytes(PNG)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(data))
    return path


def test_sanitize_never_claims_missing_photo_when_turn_has_one():
    raw = "I don't see the photo or reference attached in this thread"
    assert claims_photo_missing(raw)
    out = sanitize_attached_photo_reply(raw, "IMG_2265.jpeg")
    assert "don't see the photo" not in out.lower()
    assert "IMG_2265.jpeg" in out
    assert sanitize_attached_photo_reply("The panels are ripplefold.", "IMG_2265.jpeg") == (
        "The panels are ripplefold."
    )


def test_studio_chat_turn_with_image_reaches_model(monkeypatch, tmp_path):
    _write_photo(tmp_path, monkeypatch)
    max_router = importlib.import_module("app.routers.max.router")
    captured = {}

    async def fake_chat(messages, model=None, image_filename=None, **kwargs):
        captured["messages"] = messages
        captured["image_filename"] = image_filename
        return AIResponse(
            content="Send a photo or describe the item...",
            model_used="minimax-MiniMax-M3.1-Flash-Preview",
        )

    monkeypatch.setattr(max_router.ai_router, "chat", fake_chat)

    request = max_router.ChatRequest(
        message="What fabric notes are on this photo?",
        image_filename="IMG_2265.jpeg",
        history=[],
        channel="dashboard",
        conversation_id="studio-photo-1",
    )
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert captured.get("image_filename") == "IMG_2265.jpeg"
    user_text = " ".join(
        getattr(m, "content", "") or ""
        for m in captured.get("messages") or []
        if getattr(m, "role", None) == "user"
    )
    assert "IMG_2265.jpeg" in user_text
    assert "Attached photo on this turn" in user_text
    assert "send a photo" not in response.response.lower()
    assert "don't see the photo" not in response.response.lower()
    assert "not attached in this thread" not in response.response.lower()


def test_give_a_drawing_with_photo_routes_to_drawing_tool(monkeypatch, tmp_path):
    photo = _write_photo(tmp_path, monkeypatch)
    max_router = importlib.import_module("app.routers.max.router")
    calls = []

    async def fail_chat(*args, **kwargs):
        raise AssertionError("drawing+photo must not fall through to the text model")

    def fake_execute(tool_call, **kwargs):
        calls.append(tool_call)
        return ToolResult(
            tool="sketch_to_drawing",
            success=True,
            result={
                "svg": "<svg><text>plan</text></svg>",
                "pdf_url": "/api/v1/drawings/files/from-photo.pdf",
                "item_type": "window",
            },
        )

    monkeypatch.setattr(max_router.ai_router, "chat", fail_chat)
    monkeypatch.setattr(max_router, "execute_tool", fake_execute)

    request = max_router.ChatRequest(
        message="Give a drawing",
        image_filename="IMG_2265.jpeg",
        history=[],
        channel="dashboard",
        conversation_id="studio-photo-draw",
    )
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert response.model_used == "drawing-router"
    assert calls, "drawing tool must run with the attached photo"
    tc = calls[0]
    assert tc.get("tool") == "sketch_to_drawing"
    assert tc.get("image") == "IMG_2265.jpeg" or tc.get("image_filename") == "IMG_2265.jpeg"
    assert "IMG_2265.jpeg" in str(tc.get("image_path") or photo)
    assert "don't see the photo" not in (response.response or "").lower()
    assert "send a photo" not in (response.response or "").lower()
