"""Studio-chat attachment helpers.

An image attached to a Max studio turn must be visible on the user
message, and Max must never claim the photo is missing when the turn
has one. HEIC / HEIF / BMP count as photos.

This module does not send raw image parts to the text model.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic", ".heif", ".bmp", ".svg"}

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


def attachment_notice(image_filename: str) -> str:
    name = Path(image_filename).name
    return (
        f"{PHOTO_MARKER} {name}. "
        "This request includes that photo as vision input and as a drawing-tool "
        "attachment. Do not say the photo is missing, unattached, or not in this "
        "thread. Use it.]\n\n"
    )


def looks_like_image(filename: Optional[str]) -> bool:
    if not filename:
        return False
    return Path(filename).suffix.lower() in IMAGE_EXTS


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
