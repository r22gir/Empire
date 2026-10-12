"""Channel-aware text for founder-facing alerts.

Telegram can render a small HTML subset. The Studio Inbox and email
bodies must not show raw ``<b>`` tags. Keep one source string and
render per channel.
"""
from __future__ import annotations

import html
import re

_TAG_RE = re.compile(r"</?(?:b|strong|i|em|u|code|pre|s|a)(?:\s[^>]*)?>", re.I)
_ANY_TAG_RE = re.compile(r"<[^>]+>")
_BR_RE = re.compile(r"<br\s*/?>", re.I)


def strip_telegram_html(text: str | None) -> str:
    """Turn Telegram HTML into plain text (no raw tags)."""
    if not text:
        return ""
    out = _BR_RE.sub("\n", str(text))
    out = _TAG_RE.sub("", out)
    out = _ANY_TAG_RE.sub("", out)
    return html.unescape(out).strip()


def to_markdown(text: str | None) -> str:
    """Convert Telegram HTML emphasis to markdown for the app."""
    if not text:
        return ""
    out = str(text)
    out = _BR_RE.sub("\n", out)
    out = re.sub(r"</?(?:b|strong)>", "**", out, flags=re.I)
    out = re.sub(r"</?(?:i|em)>", "_", out, flags=re.I)
    out = re.sub(r"</?(?:u|s)>", "", out, flags=re.I)
    out = re.sub(r"</?code>", "`", out, flags=re.I)
    out = _ANY_TAG_RE.sub("", out)
    return html.unescape(out).strip()


def for_channel(text: str | None, channel: str = "app") -> str:
    """Render text for a delivery channel.

    - ``telegram``: keep HTML
    - ``email`` / ``html``: keep HTML (email already wraps newlines)
    - ``app`` / ``markdown``: markdown (no raw tags)
    - ``plain`` (default fallback): stripped
    """
    raw = text or ""
    ch = (channel or "app").lower()
    if ch == "telegram":
        return raw
    if ch in ("email", "html"):
        return raw
    if ch in ("app", "markdown"):
        return to_markdown(raw)
    return strip_telegram_html(raw)
