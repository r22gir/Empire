"""Make Telegram text encodable as UTF-8.

A valid surrogate pair is one emoji that arrived split into two code points.
Those are joined back into the real character. A lone surrogate cannot be
encoded, so it is dropped. Emoji that are already real characters stay.
"""
from __future__ import annotations


def sanitize_telegram_text(text) -> str:
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    out: list[str] = []
    i = 0
    while i < len(text):
        code = ord(text[i])
        if 0xD800 <= code <= 0xDBFF and i + 1 < len(text):
            nxt = ord(text[i + 1])
            if 0xDC00 <= nxt <= 0xDFFF:
                point = 0x10000 + ((code - 0xD800) << 10) + (nxt - 0xDC00)
                out.append(chr(point))
                i += 2
                continue
            i += 1
            continue
        if 0xDC00 <= code <= 0xDFFF:
            i += 1
            continue
        out.append(text[i])
        i += 1
    cleaned = "".join(out)
    return cleaned.encode("utf-8", errors="strict").decode("utf-8")


def install_outbound_sanitizer() -> None:
    """Sanitize text and captions on the python-telegram-bot send path."""
    try:
        from telegram import Bot
    except Exception:
        return
    if getattr(Bot.send_message, "_empire_sanitized", False):
        return

    def _wrap(method_name: str, text_index: int | None, fields: tuple[str, ...]):
        original = getattr(Bot, method_name, None)
        if original is None:
            return

        async def wrapped(self, *args, **kwargs):
            if text_index is not None and len(args) > text_index and isinstance(args[text_index], str):
                args = list(args)
                args[text_index] = sanitize_telegram_text(args[text_index])
                args = tuple(args)
            for field in fields:
                if isinstance(kwargs.get(field), str):
                    kwargs[field] = sanitize_telegram_text(kwargs[field])
            return await original(self, *args, **kwargs)

        wrapped._empire_sanitized = True
        setattr(Bot, method_name, wrapped)

    _wrap("send_message", 1, ("text", "caption"))
    _wrap("send_photo", None, ("caption",))
    _wrap("edit_message_text", None, ("text",))
    Bot.send_message._empire_sanitized = True
