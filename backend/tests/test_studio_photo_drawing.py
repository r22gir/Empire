"""Studio chat: photo + 'Give a drawing' must keep the image.

No real MiniMax/Telegram sends. No writes under ~/empire-data.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

_ROUTER_PY = Path(__file__).resolve().parents[1] / "app" / "routers" / "max" / "router.py"


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
    assert refers_to_last_image("esa") is False
    assert refers_to_last_image("ese") is False
    assert resolve_turn_image("c1", "you have it", None) == "window.jpg"
    assert resolve_turn_image("c-other", "that one", None) is None


def test_last_image_and_vision_persist_in_data_dir_db():
    from app.services.max import image_turn

    image_turn.remember_conversation_image(
        "persist-1", "IMG_2265.jpeg", vision_text="Width: 160\"\nHeight: 120\"\nStyle: unknown",
    )
    image_turn._LAST_IMAGE.clear()
    assert image_turn.last_conversation_image("persist-1") == "IMG_2265.jpeg"
    assert "160" in (image_turn.last_conversation_vision("persist-1") or "")


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
    # H57: bare "drawing" / "plan" stay off the text-only path.
    # "sketch" is already a DRAWING_KEYWORD (text-only routes too).
    if msg.strip().lower() in {"drawing", "plan"}:
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
    from app.services.max.image_turn import drawing_intent_active

    assert drawing_intent_active("Give a drawing", "window.jpg") is True
    assert drawing_intent_active("drawing", "window.jpg") is True
    assert drawing_intent_active("dame un dibujo", "window.jpg") is True
    assert drawing_intent_active("hello", None) is False


# ── timeout must not cancel the image reply ───────────────────────


def test_image_turn_uses_60_second_chunk_timeout():
    from app.services.max.image_turn import (
        STREAM_IMAGE_CHUNK_TIMEOUT_S,
        stream_chunk_timeout,
    )

    assert stream_chunk_timeout("window.jpg") == 60.0
    assert STREAM_IMAGE_CHUNK_TIMEOUT_S == 60.0
    assert stream_chunk_timeout(None) == 15.0


def test_next_stream_chunk_does_not_cancel_slow_first_chunk():
    """asyncio.wait_for would cancel; our waiter must keep the task."""
    from app.services.max.image_turn import next_stream_chunk as _next_stream_chunk

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
    src = _ROUTER_PY.read_text(encoding="utf-8")
    # The image-bearing first chunk must use the non-cancelling helper.
    assert "_next_stream_chunk" in src
    assert "skip_vision=bool(vision_text)" in src
    assert "image_filename=_turn_image" in src
    assert "asyncio.wait_for(_initial_iter.__anext__()" not in src


# ── empty image-turn retry keeps the photo ────────────────────────


def test_empty_image_retry_passes_image_filename():
    src = _ROUTER_PY.read_text(encoding="utf-8")
    assert "image_filename=_turn_image" in src
    assert "image-turn empty retry" in src
    assert "skip_vision=bool(vision_text)" in src
    from app.services.max.image_turn import image_turn_reply_is_empty
    assert image_turn_reply_is_empty("") is True
    assert image_turn_reply_is_empty("   ") is True
    assert image_turn_reply_is_empty("I see the window.") is False


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
    assert "Width:" in image_turn.DRAWING_VISION_PROMPT
    assert "Height:" in image_turn.DRAWING_VISION_PROMPT
    assert "Style:" in image_turn.DRAWING_VISION_PROMPT
    assert "pinch pleat" not in image_turn.DRAWING_VISION_PROMPT.lower()
    assert "euro" not in image_turn.DRAWING_VISION_PROMPT.lower()
    assert "ripplefold" not in image_turn.DRAWING_VISION_PROMPT.lower()


def test_vision_for_request_mocked(monkeypatch):
    from app.services.max import image_turn

    sent = {"n": 0}

    async def fake_describe(image_filename, *, for_drawing=False, upload_path=None):
        sent["n"] += 1
        assert image_filename == "window.jpg"
        assert for_drawing is True
        return "Window 72 inches wide by 90 inches high.", None, {"success": True}

    monkeypatch.setattr(image_turn, "describe_attached_image", fake_describe)
    desc, err, raw = asyncio.run(
        image_turn.describe_attached_image("window.jpg", for_drawing=True)
    )
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


# ── size parsing: markdown table + 160" x 120" ────────────────────


HAND_SKETCH_TABLE = """
Hand sketch on graph paper. Top panel and lining noted in a table.

| Item | Size |
| --- | --- |
| Top panel width | 160" |
| Top panel length | 120" |
| Lining width | 143 3/4" |
| Lining length | 119 3/4" |
"""


def test_vision_table_and_quote_x_form_parse_top_panel_not_lining():
    from app.services.max.drawing_intent import HEADING_ASK, build_drawing_handoff
    from app.services.max.image_turn import extract_dims_from_vision_text

    dims = extract_dims_from_vision_text(HAND_SKETCH_TABLE)
    assert float(str(dims["width"]).rstrip('"')) == 160
    assert float(str(dims["height"]).rstrip('"')) == 120

    quoted = extract_dims_from_vision_text('Face panel 160" x 120" over a lining 143 3/4" W x 119 3/4" L')
    assert float(str(quoted["width"]).rstrip('"')) == 160
    assert float(str(quoted["height"]).rstrip('"')) == 120

    handoff = build_drawing_handoff(
        "Give a drawing",
        image_filename="IMG_2265.jpeg",
        vision_text=HAND_SKETCH_TABLE + "\nStyle: unknown\n",
    )
    assert handoff.is_drawing_intent is True
    assert handoff.ready is False
    assert handoff.b1_product_type is None
    assert "heading" in handoff.missing
    assert HEADING_ASK in handoff.response
    assert float(str(handoff.dimensions["width"]).rstrip('"')) == 160
    assert float(str(handoff.dimensions["height"]).rstrip('"')) == 120


def test_photo_drawing_does_not_guess_pinch_pleat():
    from app.services.max.drawing_intent import HEADING_ASK, build_drawing_handoff

    handoff = build_drawing_handoff(
        "Give a drawing",
        image_filename="bench.jpg",
        vision_text='Width: 160"\nHeight: 120"\nStyle: unknown\n',
    )
    assert handoff.b1_product_type is None
    assert handoff.ready is False
    assert HEADING_ASK == handoff.response


def test_heading_answer_and_you_have_it_resume_pending_without_second_vision(monkeypatch):
    from app.services.max.drawing_intent import (
        HEADING_ASK,
        build_drawing_handoff,
        pending_should_resume,
        resume_drawing_handoff,
    )
    from app.services.max.drawing_pending import (
        get_pending,
        merge_founder_reply,
        set_pending,
        snapshot_from_handoff,
    )
    from app.services.max import image_turn

    vision_calls = {"n": 0}

    async def fail_describe(*args, **kwargs):
        vision_calls["n"] += 1
        raise AssertionError("resume must reuse stored vision, not call MiniMax")

    monkeypatch.setattr(image_turn, "describe_attached_image", fail_describe)

    vision = HAND_SKETCH_TABLE + "\nStyle: unknown\n"
    first = build_drawing_handoff(
        "Give a drawing",
        image_filename="IMG_2265.jpeg",
        vision_text=vision,
    )
    assert first.ready is False
    assert HEADING_ASK in first.response
    set_pending("conv-resume", "dashboard", snapshot_from_handoff(first, vision_text=vision))
    image_turn.remember_conversation_image(
        "conv-resume", "IMG_2265.jpeg", vision_text=vision,
    )

    pending = get_pending("conv-resume", "dashboard")
    assert pending is not None
    assert pending_should_resume("pinch", pending) is True
    assert pending_should_resume("you have it", pending) is True

    merged = merge_founder_reply(pending, "pinch")
    resumed = resume_drawing_handoff(merged, "pinch")
    assert resumed.ready is True
    assert resumed.b1_product_type == "pinch_pleat"
    assert resumed.source_image == "IMG_2265.jpeg"
    assert float(str(resumed.translated_dims["width"]).rstrip('"')) == 160
    assert float(str(resumed.translated_dims["height"]).rstrip('"')) == 120
    assert vision_calls["n"] == 0

    you_have_it = resume_drawing_handoff(pending, "you have it")
    assert you_have_it.source_image == "IMG_2265.jpeg"
    assert you_have_it.vision_text
    assert you_have_it.b1_product_type is None
    assert HEADING_ASK in you_have_it.response
    assert vision_calls["n"] == 0


# ── drapery plumb QC at 160x120 and 87x84 ─────────────────────────


@pytest.mark.parametrize("product_type", ["pinch_pleat", "euro_pleat", "pencil_pleat"])
@pytest.mark.parametrize("width,height", [(160, 120), (87, 84)])
def test_pleat_drawings_pass_plumb_qc_at_both_sizes(product_type, width, height):
    pytest.importorskip("pdfplumber")
    from app.services.drawing.templates.drapery_render import render_drapery
    from app.services.drawing.templates.b2_qc import _check_drapery_plumb

    pdf = render_drapery({
        "product_type": product_type,
        "dims": {"width": width, "height": height, "returns": 4, "fullness": 2.5},
        "client_name": "Test Client",
    })
    failures = _check_drapery_plumb(pdf, "Drapery")
    assert failures == [], (
        f"{product_type} {width}x{height} failed drapery-plumb QC: {failures}"
    )


# ── legacy drawings folder fallback ───────────────────────────────


def test_drawings_file_route_falls_back_to_legacy_repo_folder(tmp_path, monkeypatch):
    from app.services.drawing import canonical_path

    canon = tmp_path / "empire-data" / "drawings"
    legacy = tmp_path / "backend" / "data" / "drawings"
    canon.mkdir(parents=True)
    legacy.mkdir(parents=True)
    (legacy / "existing-533.pdf").write_bytes(b"%PDF-1.4 legacy")

    monkeypatch.setattr(canonical_path, "canonical_drawings_dir", lambda: str(canon))
    monkeypatch.setattr(canonical_path, "repo_legacy_drawings_dir", lambda: legacy)

    found = canonical_path.resolve_existing_drawing_file("existing-533.pdf")
    assert found == legacy / "existing-533.pdf"
    assert found.read_bytes().startswith(b"%PDF")


# ── PR #164 photo guard / HEIC (no raw-image-to-text-model) ───────


def test_sanitize_never_claims_missing_photo_when_turn_has_one():
    from app.services.max.chat_attachments import (
        claims_photo_missing,
        sanitize_attached_photo_reply,
        apply_photo_context,
        looks_like_image,
        PHOTO_MARKER,
    )

    raw = "I don't see the photo or reference attached in this thread"
    assert claims_photo_missing(raw)
    out = sanitize_attached_photo_reply(raw, "IMG_2265.jpeg")
    assert "don't see the photo" not in out.lower()
    assert "IMG_2265.jpeg" in out
    assert sanitize_attached_photo_reply("The panels are ripplefold.", "IMG_2265.jpeg") == (
        "The panels are ripplefold."
    )

    messages = [{"role": "user", "content": "Give a drawing"}]
    stamped = apply_photo_context(messages, "IMG_2265.jpeg")
    assert PHOTO_MARKER in stamped[-1]["content"]
    assert "IMG_2265.jpeg" in stamped[-1]["content"]

    assert looks_like_image("shot.heic")
    assert looks_like_image("shot.heif")
    assert looks_like_image("shot.bmp")
    assert looks_like_image("shot.jpg")


def test_router_wires_photo_guard_and_not_raw_image_to_text_model():
    src = _ROUTER_PY.read_text(encoding="utf-8")
    assert "sanitize_attached_photo_reply" in src
    assert "apply_photo_context" in src
    assert "skip_vision=bool(vision_text)" in src
    ai_src = (
        Path(__file__).resolve().parents[1] / "app" / "services" / "max" / "ai_router.py"
    ).read_text(encoding="utf-8")
    assert ".heic" in ai_src
    assert ".heif" in ai_src
    assert ".bmp" in ai_src
