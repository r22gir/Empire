"""Studio chat image-turn helpers.

Photo + drawing asks used to miss the image: the stream 15-second
first-chunk wait cancelled MiniMax vision, then the empty-reply
fallback regenerated from text only. This module:

  1. Remembers the last image in a conversation so "you have it" /
     "that one" / "esa foto" can refer back to it. Memory is persisted
     per conversation in the data-dir SQLite DB so it survives restarts.
  2. Detects drawing intent on a photo turn (English + Spanish).
  3. Extracts width/height from a (mocked or live) vision description
     so Drawing Studio can use the photo's measurements.

No live I/O lives here except the optional MiniMax describe call,
which tests replace with a mock, and the last-image DB under the
redirected data dir.
"""
from __future__ import annotations

import asyncio
import os
import re
import sqlite3
from pathlib import Path
from typing import Any

# In-process last-image memory. Tests redirect EMPIRE_TASK_DB / EMPIRE_DATA_DIR.
# Each value is {"image": filename, "vision": stored description or ""}.
_LAST_IMAGE: dict[str, dict[str, str]] = {}

# Stream first-chunk wait. wait_for() cancels the producer — MiniMax
# vision is ~12s+ so a 15s cap used to drop the image-bearing reply.
STREAM_CHUNK_TIMEOUT_S = 15.0
STREAM_IMAGE_CHUNK_TIMEOUT_S = 60.0


def stream_chunk_timeout(image_filename: str | None) -> float:
    """60s when an image is on the turn so vision is never cancelled."""
    return STREAM_IMAGE_CHUNK_TIMEOUT_S if image_filename else STREAM_CHUNK_TIMEOUT_S


async def next_stream_chunk(pending, aiter, timeout: float):
    """Wait for the next stream chunk without cancelling the producer.

    ``asyncio.wait_for`` cancels the awaited coroutine on timeout. The
    reply that holds the image description must stay alive; ``asyncio.wait``
    only times out the waiter.

    Returns ``(chunk, model, next_pending, finished)``.
    """
    task = pending or asyncio.ensure_future(aiter.__anext__())
    done, _ = await asyncio.wait({task}, timeout=timeout)
    if not done:
        return None, None, task, False
    try:
        chunk, model = task.result()
    except StopAsyncIteration:
        return None, None, None, True
    return chunk, model, None, False


def image_turn_reply_is_empty(text: str | None) -> bool:
    return not (text or "").strip()

_IMAGE_REFERRAL_RE = re.compile(
    r"(?i)\b("
    r"you have it|you have the (?:photo|image|picture|pic)|"
    r"that one|that photo|that image|that picture|that pic|"
    r"the photo|the image|the picture|"
    r"same (?:photo|image|picture|one)|"
    r"ya la tienes|ya lo tienes|ya la tiene|ya lo tiene|"
    r"esa foto|esa imagen|"
    r"la foto|la imagen|la misma"
    r")\b"
)

# Photo + any of these words/phrases routes to Drawing Studio.
# Bare "drawing" / "plan" stay off the text-only path (H57); they
# only count when an image is on the turn or remembered.
_PHOTO_DRAW_PHRASE = (
    "give a drawing",
    "give me a drawing",
    "give drawing",
    "give me a sketch",
    "give a sketch",
    "give me a plan",
    "dame un dibujo",
    "dame el dibujo",
    "dame un plano",
    "dame el plano",
    "dame un boceto",
    "haz un dibujo",
    "hazme un dibujo",
    "hazme el dibujo",
    "haz un plano",
    "quiero un dibujo",
    "necesito un dibujo",
)

_PHOTO_DRAW_WORD = re.compile(
    r"(?i)(?<![A-Za-z0-9])("
    r"draw|drawing|sketch|plan|"
    r"dibujo|dibuja|dibujar|dibújame|dibujame|"
    r"boceto|plano"
    r")(?![A-Za-z0-9])"
)

_PHOTO_DRAW_NEGATION = (
    "not asking you to draw",
    "don't draw",
    "do not draw",
    "not a drawing",
    "no drawing needed",
    "no necesito dibujo",
    "no quiero dibujo",
)

# Vision prompt for a photo that is becoming a shop drawing.
# Fixed lines so the parser does not have to guess a markdown table.
# Do not name heading styles — that made MiniMax invent pinch/euro/pencil.
DRAWING_VISION_PROMPT = (
    "Describe this photo for a workroom shop drawing. "
    "Write every readable measurement as fractions of an inch "
    "on these exact lines:\n"
    "Width: …\n"
    "Height: …\n"
    "Style: … or unknown\n"
    "If a heading style is written on the photo, copy it after Style. "
    "If no heading is written, write Style: unknown. "
    "Do not guess a heading. "
    "Do not generate a new image."
)

DESCRIBE_VISION_PROMPT = (
    "Describe this image for MAX in factual operational terms. "
    "Mention visible objects, text, layout, materials, colors, and any "
    "business-relevant details. Do not generate a new image."
)


def _memory_db_path() -> Path:
    """SQLite file under the data dir (EMPIRE_TASK_DB / EMPIRE_DATA_DIR)."""
    env = os.getenv("EMPIRE_TASK_DB")
    if env:
        return Path(env)
    data = os.getenv("EMPIRE_DATA_DIR")
    if data:
        return Path(data) / "empire.db"
    try:
        from app.services.data_paths import data_root
        return data_root() / "empire.db"
    except Exception:
        return Path.home() / "empire-data" / "empire.db"


def _connect_memory() -> sqlite3.Connection:
    path = _memory_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_memory_table() -> None:
    with _connect_memory() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_last_images (
                conversation_id TEXT PRIMARY KEY,
                image_filename TEXT NOT NULL,
                vision_text TEXT,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.commit()


def _load_memory_row(conversation_id: str) -> dict[str, str] | None:
    try:
        _ensure_memory_table()
        with _connect_memory() as conn:
            row = conn.execute(
                "SELECT image_filename, vision_text FROM conversation_last_images "
                "WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()
        if not row:
            return None
        rec = {
            "image": str(row["image_filename"] or ""),
            "vision": str(row["vision_text"] or ""),
        }
        if rec["image"]:
            _LAST_IMAGE[conversation_id] = rec
            return rec
    except Exception:
        return None
    return None


def _persist_memory_row(conversation_id: str, image: str, vision: str) -> None:
    try:
        _ensure_memory_table()
        with _connect_memory() as conn:
            conn.execute(
                """
                INSERT INTO conversation_last_images
                    (conversation_id, image_filename, vision_text, updated_at)
                VALUES (?, ?, ?, datetime('now'))
                ON CONFLICT(conversation_id) DO UPDATE SET
                    image_filename = excluded.image_filename,
                    vision_text = excluded.vision_text,
                    updated_at = datetime('now')
                """,
                (conversation_id, image, vision),
            )
            conn.commit()
    except Exception:
        pass


def clear_conversation_images() -> None:
    """Test helper — drop in-process and isolated-DB last-image memory."""
    _LAST_IMAGE.clear()
    try:
        _ensure_memory_table()
        with _connect_memory() as conn:
            conn.execute("DELETE FROM conversation_last_images")
            conn.commit()
    except Exception:
        pass


def remember_conversation_image(
    conversation_id: str | None,
    image_filename: str | None,
    vision_text: str | None = None,
) -> None:
    if not conversation_id or not image_filename:
        return
    cid = str(conversation_id)
    name = Path(str(image_filename)).name
    existing = _LAST_IMAGE.get(cid) or {}
    vision = vision_text if vision_text is not None else existing.get("vision", "")
    if existing.get("image") != name and vision_text is None:
        vision = ""
    rec = {"image": name, "vision": vision or ""}
    _LAST_IMAGE[cid] = rec
    _persist_memory_row(cid, rec["image"], rec["vision"])


def last_conversation_record(conversation_id: str | None) -> dict[str, str] | None:
    if not conversation_id:
        return None
    cid = str(conversation_id)
    rec = _LAST_IMAGE.get(cid)
    if rec and rec.get("image"):
        return rec
    return _load_memory_row(cid)


def last_conversation_image(conversation_id: str | None) -> str | None:
    rec = last_conversation_record(conversation_id)
    if not rec:
        return None
    return rec.get("image") or None


def last_conversation_vision(conversation_id: str | None) -> str | None:
    rec = last_conversation_record(conversation_id)
    if not rec:
        return None
    text = (rec.get("vision") or "").strip()
    return text or None


def refers_to_last_image(message: str | None) -> bool:
    text = (message or "").strip()
    if not text:
        return False
    return bool(_IMAGE_REFERRAL_RE.search(text))


def resolve_turn_image(
    conversation_id: str | None,
    message: str | None,
    image_filename: str | None,
) -> str | None:
    """Current upload wins; otherwise a referral to the last photo."""
    if image_filename:
        remember_conversation_image(conversation_id, image_filename)
        return Path(str(image_filename)).name
    if refers_to_last_image(message):
        return last_conversation_image(conversation_id)
    return None


def drawing_intent_active(message: str | None, image_filename: str | None) -> bool:
    """True when this turn should take the Drawing Studio path."""
    from app.services.max.drawing_intent import (
        is_drawing_intent,
        is_text_measurement_drawing_request,
    )
    text = message or ""
    if image_filename:
        return (
            is_photo_drawing_request(text, image_filename)
            or is_drawing_intent(text)
            or is_text_measurement_drawing_request(text)
        )
    return is_drawing_intent(text) or is_text_measurement_drawing_request(text)


def is_photo_drawing_request(
    text: str | None,
    image_filename: str | None = None,
) -> bool:
    """True when a photo (this turn or remembered) plus a draw/sketch/plan ask."""
    if not image_filename or not text:
        return False
    lowered = text.lower()
    if any(neg in lowered for neg in _PHOTO_DRAW_NEGATION):
        return False
    if any(phrase in lowered for phrase in _PHOTO_DRAW_PHRASE):
        return True
    return bool(_PHOTO_DRAW_WORD.search(text))


def vision_summary(result: dict | None) -> str:
    if not isinstance(result, dict):
        return ""
    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    text = (
        (data or {}).get("summary")
        or (data or {}).get("full_response")
        or (data or {}).get("text")
        or result.get("summary")
        or ""
    )
    return str(text).strip()


def extract_dims_from_vision_text(text: str | None) -> dict[str, str]:
    """Parse width/height (and friends) from a vision description."""
    if not text:
        return {}
    from app.services.max.drawing_intent import extract_all_dimensions
    return extract_all_dimensions(text)


def inject_vision_context(
    messages: list,
    description: str,
    image_filename: str | None,
) -> list:
    """Prepend the verified image description onto the last user turn."""
    if not messages or not description:
        return list(messages)
    from app.services.max.ai_router import AIMessage

    last = messages[-1]
    name = Path(image_filename or "image").name
    vision_context = (
        "[Image understanding via MiniMax mmx_cli]\n"
        f"File: {name}\n"
        "Transport: mmx_cli\n"
        "Quota bucket: mcp_understand_image\n"
        "Image generation used: false\n"
        "Instruction: Answer the user directly from the description. "
        "The user attached this image to the message below. Base the answer "
        "on what it shows: first say in one line what you see, then answer "
        "about that. Do not give generic instructions that ignore the image.\n"
        f"Description:\n{description}\n\n"
    )
    content = getattr(last, "content", "") or ""
    updated = list(messages)
    if isinstance(last, AIMessage):
        updated[-1] = AIMessage(role=last.role, content=vision_context + content)
    elif isinstance(last, dict):
        updated[-1] = {**last, "content": vision_context + content}
    return updated


def _resolve_upload_path(image_filename: str | None) -> Path | None:
    """Find an uploaded file without importing the MAX router (cycle-safe)."""
    if not image_filename:
        return None
    safe = Path(image_filename).name
    try:
        from app.services.data_paths import data_root
        roots = [data_root() / "uploads"]
    except Exception:
        roots = []
    roots.extend([
        Path.home() / "empire-data" / "uploads",
        Path.home() / "empire-repo" / "backend" / "data" / "uploads",
    ])
    for root in roots:
        for cat in ("images", "documents", "audio", "other", "code"):
            candidate = root / cat / safe
            if candidate.is_file():
                return candidate
        candidate = root / safe
        if candidate.is_file():
            return candidate
    return None


async def describe_attached_image(
    image_filename: str,
    *,
    for_drawing: bool = False,
    upload_path: Path | None = None,
) -> tuple[str, str | None, dict | None]:
    """Run MiniMax vision. Tests mock this function — no real send.

    Returns (description, error, raw_result).
    """
    from app.services.max.minimax_tools import minimax_understand_image

    path = upload_path
    if path is None:
        path = _resolve_upload_path(image_filename)
    if path is None:
        return "", "IMAGE_NOT_AVAILABLE", None

    prompt = DRAWING_VISION_PROMPT if for_drawing else DESCRIBE_VISION_PROMPT
    try:
        result = await minimax_understand_image(str(path), prompt=prompt)
    except Exception as exc:
        return "", str(exc), None

    if not isinstance(result, dict) or not result.get("success"):
        err = ""
        if isinstance(result, dict):
            err = str(result.get("error") or "")
        return "", err or "MiniMax image understanding failed", result if isinstance(result, dict) else None

    description = vision_summary(result)
    if not description:
        return "", "MiniMax image understanding returned no verified description", result
    return description, None, result
