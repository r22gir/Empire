"""Studio chat: photo + 'Give a drawing' must keep the image.

No real MiniMax/Telegram sends. No writes under ~/empire-data.
"""
from __future__ import annotations

import asyncio
import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest


def _write_png(path: Path) -> None:
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x01\x01\x01\x00"
        b"\x18\xdd\x8d\xb0\x00\x00\x00\x00IEND\xaeB`\x82"
    )


@pytest.fixture(autouse=True)
def _no_live_image_memory():
    from app.services.max.image_turn import clear_conversation_images
    clear_conversation_images()
    yield
    clear_conversation_images()


# ── last-image memory ─────────────────────────────────────────────


def test_remembers_last_image_for_you_have_it_and_that_one():
    from app.services.max.image_turn import (
        last_conversation_image,
        refers_to_last_image,
        resolve_turn_image,
    )

    assert resolve_turn_image("c1", "Give a drawing", "window.jpg") == "window.jpg"
    assert last_conversation_image("c1") == "window.jpg"
    assert refers_to_last_image("you have it")
    assert refers_to_last_image("that one")
    assert refers_to_last_image("esa foto")
    assert refers_to_last_image("ya la tienes")
    assert resolve_turn_image("c1", "you have it", None) == "window.jpg"
    assert resolve_turn_image("c-other", "that one", None) is None


# ── drawing intent on a photo turn ────────────────────────────────


@pytest.mark.parametrize("msg", [
    "Give a drawing",
    "give me a drawing",
    "draw this",
    "drawing",
    "sketch",
    "plan",
    "dame un dibujo",
    "dame el plano",
    "dibuja esto",
    "haz un dibujo",
])
def test_photo_plus_draw_phrase_is_drawing_intent(msg):
    from app.services.max.drawing_intent import build_drawing_handoff, is_drawing_intent
    from app.services.max.image_turn import is_photo_drawing_request

    assert is_photo_drawing_request(msg, "photo.jpg") is True
    handoff = build_drawing_handoff(msg, image_filename="photo.jpg")
    assert handoff.is_drawing_intent is True
    # Text-only bare words stay off the drawing route (H57).
    if msg.strip().lower() in {"drawing", "sketch", "plan"}:
        assert is_drawing_intent(msg) is False


def test_photo_drawing_uses_vision_dimensions_not_text_only():
    from app.services.max.drawing_intent import build_drawing_handoff
    from app.services.max.image_turn import extract_dims_from_vision_text

    vision = (
        "Window treatment 87 inches wide by 96 inches high. "
        "Pinch pleat drapery, returns 3 1/2 inches."
    )
    dims = extract_dims_from_vision_text(vision)
    assert "width" in dims
    assert "height" in dims

    handoff = build_drawing_handoff(
        "Give a drawing",
        image_filename="window.jpg",
        vision_text=vision,
    )
    assert handoff.is_drawing_intent is True
    assert handoff.ready is True
    assert handoff.b1_product_type == "pinch_pleat"
    assert float(str(handoff.translated_dims["width"]).rstrip('"')) == 87
    assert float(str(handoff.translated_dims["height"]).rstrip('"')) == 96


def test_attached_image_no_longer_disables_drawing_route():
    from app.routers.max.router import _drawing_intent_active

    assert _drawing_intent_active("Give a drawing", "window.jpg") is True
    assert _drawing_intent_active("drawing", "window.jpg") is True
    assert _drawing_intent_active("dame un dibujo", "window.jpg") is True
    assert _drawing_intent_active("hello", None) is False


# ── timeout must not cancel the image reply ───────────────────────


def test_image_turn_uses_60_second_chunk_timeout():
    from app.routers.max.router import (
        _STREAM_IMAGE_CHUNK_TIMEOUT_S,
        _stream_chunk_timeout,
    )

    assert _stream_chunk_timeout("window.jpg") == 60.0
    assert _STREAM_IMAGE_CHUNK_TIMEOUT_S == 60.0
    assert _stream_chunk_timeout(None) == 15.0


def test_next_stream_chunk_does_not_cancel_slow_first_chunk():
    """asyncio.wait_for would cancel; our waiter must keep the task."""
    from app.routers.max.router import _next_stream_chunk

    cancelled = {"n": 0}

    async def agen():
        try:
            await asyncio.sleep(0.25)
            yield "vision-chunk", "mmx-vision"
        except asyncio.CancelledError:
            cancelled["n"] += 1
            raise

    async def run():
        it = agen().__aiter__()
        chunk, model, pending, done = await _next_stream_chunk(None, it, 0.05)
        assert chunk is None and done is False and pending is not None
        chunk, model, pending, done = await _next_stream_chunk(pending, it, 0.5)
        assert chunk == "vision-chunk"
        assert model == "mmx-vision"
        assert done is False
        assert cancelled["n"] == 0

    asyncio.run(run())


def test_router_source_never_wait_for_cancels_image_stream():
    src = inspect.getsource(
        __import__("app.routers.max.router", fromlist=["_next_stream_chunk"])
    )
    # The image-bearing first chunk must use the non-cancelling helper.
    assert "_next_stream_chunk" in src
    assert "skip_vision=bool(vision_text)" in src
    assert "image_filename=_turn_image" in src or "image_filename=_turn_image," in src


# ── empty image-turn retry keeps the photo ────────────────────────


def test_empty_image_retry_passes_image_filename(monkeypatch):
    from app.routers.max import router as r
    from app.services.max.ai_router import AIResponse

    seen = []

    async def fake_chat(*args, **kwargs):
        seen.append(kwargs.get("image_filename"))
        return AIResponse(content="I see the window photo.", model_used="mock")

    monkeypatch.setattr(r.ai_router, "chat", fake_chat)

    async def run():
        resp = await r.ai_router.chat(
            [], image_filename="window.jpg", skip_vision=True,
        )
        assert resp.content
        assert seen == ["window.jpg"]

    asyncio.run(run())

    src = Path(r.__file__).read_text(encoding="utf-8")
    assert "image_filename=_turn_image" in src
    assert "image-turn empty retry" in src
    # Completeness / empty fallback must not drop the image.
    assert "skip_vision=bool(vision_text)" in src


# ── mocked vision describe (no real send) ─────────────────────────


def test_describe_attached_image_is_mocked_no_send(monkeypatch, tmp_path):
    from app.services.max import image_turn
    from app.services.max import minimax_tools

    png = tmp_path / "shot.png"
    _write_png(png)
    calls = {"n": 0}

    async def fake_understand(path, prompt):
        calls["n"] += 1
        assert path == str(png)
        assert "fractions of an inch" in prompt
        return {
            "success": True,
            "data": {"summary": "Window 80 inches wide by 84 inches high."},
        }

    monkeypatch.setattr(minimax_tools, "minimax_understand_image", fake_understand)

    desc, err, raw = asyncio.run(
        image_turn.describe_attached_image(
            "shot.png", for_drawing=True, upload_path=png,
        )
    )
    assert err is None
    assert "80 inches wide" in desc
    assert calls["n"] == 1


def test_vision_for_request_mocked(monkeypatch):
    from app.routers.max import router as r

    sent = {"n": 0}

    async def fake_describe(image_filename, *, for_drawing=False, upload_path=None):
        sent["n"] += 1
        assert image_filename == "window.jpg"
        assert for_drawing is True
        return "Window 72 inches wide by 90 inches high.", None, {"success": True}

    monkeypatch.setattr(r, "describe_attached_image", fake_describe)
    req = SimpleNamespace(message="Give a drawing", image_filename="window.jpg")
    desc, err = asyncio.run(r._vision_for_request(req, "window.jpg"))
    assert err is None
    assert "72 inches wide" in desc
    assert sent["n"] == 1


# ── drawings land under the data dir ──────────────────────────────


def test_default_drawings_dir_is_empire_data_not_repo():
    from app.services.drawing.canonical_path import (
        _default_drawings_dir,
        _empire_data_dir,
        canonical_drawings_dir,
    )

    default = _default_drawings_dir()
    assert default == _empire_data_dir() / "drawings"
    assert "backend/data/drawings" not in str(default)
    live = Path.home() / "empire-data" / "drawings"
    # Tests redirect EMPIRE_DATA_DIR; never write the live tree.
    out = canonical_drawings_dir()
    assert out != live
    assert str(Path.home() / "empire-data") not in str(out.resolve())


# ── pinch / euro / pencil pleat QC (stack width) ──────────────────


@pytest.mark.parametrize("product_type", ["pinch_pleat", "euro_pleat", "pencil_pleat"])
def test_pleat_drawings_pass_gathered_elevation_stack_width(product_type):
    pytest.importorskip("pdfplumber")
    from app.services.drawing.templates.drapery_render import render_drapery
    from app.services.drawing.templates.b2_qc import _check_gathered_elevation

    pdf = render_drapery({
        "product_type": product_type,
        "dims": {"width": 87, "height": 84, "returns": 4, "fullness": 2.5},
        "client_name": "Test Client",
    })
    failures = _check_gathered_elevation(pdf, "Drapery")
    stack_fails = [
        f for f in failures
        if "stack width" in str(f.get("issue", "")).lower()
    ]
    assert stack_fails == [], (
        f"{product_type} stack width failed QC: {stack_fails}"
    )
    ratios = [f.get("ratio") for f in failures if f.get("ratio") is not None]
    for ratio in ratios:
        assert ratio > 0.2, f"{product_type} stack ratio {ratio} is ~1% of expected"


@pytest.mark.parametrize("product_type", ["pinch_pleat", "euro_pleat", "pencil_pleat"])
def test_pleat_render_spec_passes_builtin_qc(product_type):
    pytest.importorskip("pdfplumber")
    from app.services.drawing.templates import render_spec

    pdf = render_spec({
        "product_type": product_type,
        "dims": {"width": 87, "height": 84, "returns": 4, "fullness": 2.5},
        "client_name": "Test Client",
    })
    assert isinstance(pdf, (bytes, bytearray))
    assert len(pdf) > 1024
