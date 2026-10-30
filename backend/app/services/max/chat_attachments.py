"""Studio-chat attachment helpers.

An image attached to a Max studio turn must reach the model (vision
text and/or image parts) and the drawing tools. Max must never claim
the photo is missing when the turn has one.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

from app.services.data_paths import data_root

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic", ".heif", ".bmp", ".svg"}
_UPLOAD_CATEGORIES = ("images", "documents", "audio", "other", "code")

PHOTO_MARKER = "[Attached photo on this turn:"

_MISSING_PHOTO_RE = re.compile(
    r"(?i)("
    r"send a photo or describe"
    r"|don['’]t see the photo"
    r"|do not see the photo"
    r"|i don['’]t see (?:a |the )?(?:photo|image|picture|attachment|reference)"
    r"|i do not see (?:a |the )?(?:photo|image|picture|attachment|reference)"
    r"|no photo (?:or reference )?attached"
    r"|no (?:photo|image|picture|reference) attached in this thread"
    r"|not attached in this thread"
    r"|i don['’]t have (?:the |a )?(?:photo|image)"
    r"|i do not have (?:the |a )?(?:photo|image)"
    r"|please (?:send|attach|upload) (?:a |the )?(?:photo|image|picture)"
    r"|attach (?:a |the )?(?:photo|image)"
    r")"
)

_PHOTO_DRAW_RE = re.compile(
    r"(?i)\b("
    r"drawing|sketch|"
    r"draw(?:\s+(?:this|it|that|the))|"
    r"give(?:\s+me)?\s+a\s+drawing|"
    r"make(?:\s+me)?\s+a\s+drawing|"
    r"need a drawing|"
    r"want a drawing"
    r")\b"
)


def attachment_notice(image_filename: str) -> str:
    name = Path(image_filename).name
    return (
        f"{PHOTO_MARKER} {name}. "
        "This request includes that photo as vision input and as a drawing-tool "
        "attachment. Do not say the photo is missing, unattached, or not in this "
        "thread. Use it.]\n\n"
    )


def upload_candidates(filename: str) -> list[Path]:
    safe = Path(filename).name
    roots = [
        data_root() / "uploads",
        Path.home() / "empire-repo" / "backend" / "data" / "uploads",
        Path.home() / "empire-repo" / "uploads",
    ]
    out: list[Path] = []
    for root in roots:
        for cat in _UPLOAD_CATEGORIES:
            out.append(root / cat / safe)
        out.append(root / safe)
    return out


def resolve_chat_upload(filename: Optional[str]) -> Optional[Path]:
    if not filename:
        return None
    direct = Path(filename)
    if direct.is_absolute() and direct.is_file():
        return direct
    return next((p for p in upload_candidates(filename) if p.is_file()), None)


def looks_like_image(filename: Optional[str]) -> bool:
    if not filename:
        return False
    return Path(filename).suffix.lower() in IMAGE_EXTS


def is_photo_drawing_request(text: str | None, image_filename: str | None) -> bool:
    """A drawing/draw-this request that already has a photo on this turn."""
    if not image_filename or not text:
        return False
    stripped = text.strip()
    if not stripped or len(stripped) > 400:
        return False
    return bool(_PHOTO_DRAW_RE.search(stripped))


def apply_photo_context(messages: list, image_filename: Optional[str], image_path: Any = None) -> list:
    """Stamp the last user message so the model cannot miss the attachment."""
    if not image_filename or not messages:
        return messages
    notice = attachment_notice(image_filename)
    path_str = str(image_path) if image_path else None
    updated = list(messages)
    last = updated[-1]
    content = getattr(last, "content", None)
    if content is None and isinstance(last, dict):
        content = last.get("content") or ""
        if PHOTO_MARKER not in content:
            last = dict(last)
            last["content"] = notice + content
            if path_str:
                last["image_path"] = path_str
            updated[-1] = last
        return updated
    content = content or ""
    if PHOTO_MARKER not in content:
        content = notice + content
    cls = type(last)
    kwargs = {"role": last.role, "content": content}
    if hasattr(last, "image_path"):
        kwargs["image_path"] = path_str or last.image_path
    try:
        updated[-1] = cls(**kwargs)
    except TypeError:
        last.content = content
        if path_str and hasattr(last, "image_path"):
            last.image_path = path_str
    return updated


def claims_photo_missing(text: str | None) -> bool:
    if not text:
        return False
    return bool(_MISSING_PHOTO_RE.search(text))


def sanitize_attached_photo_reply(text: str | None, image_filename: Optional[str]) -> str:
    """If this turn has a photo, never let Max tell Rafael it does not."""
    body = text or ""
    if not image_filename or not claims_photo_missing(body):
        return body
    name = Path(image_filename).name
    return (
        f"The photo is attached to this turn ({name}). "
        "I have it and will use it — I will not ask you to send it again."
    )


def model_messages_include_photo(messages: list, image_filename: Optional[str]) -> bool:
    if not image_filename:
        return False
    name = Path(image_filename).name
    for msg in messages or []:
        content = getattr(msg, "content", None)
        if content is None and isinstance(msg, dict):
            content = msg.get("content")
        if name in str(content or "") and PHOTO_MARKER.split(":")[0] in str(content or ""):
            return True
        path = getattr(msg, "image_path", None)
        if path is None and isinstance(msg, dict):
            path = msg.get("image_path")
        if path and name in str(path):
            return True
        # OpenAI/MiniMax image parts
        if isinstance(content, list):
            dumped = str(content)
            if name in dumped or "image_url" in dumped or "image" in dumped:
                return True
    return False
