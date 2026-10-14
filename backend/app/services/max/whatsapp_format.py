"""WhatsApp founder-channel text: routing, markdown, sources, chunking.

Deterministic helpers used by the webhook and outbound send path.
Never talks to Graph, SMTP, or live data stores.
"""
from __future__ import annotations

import re
from typing import Any, Optional
from urllib.parse import urlparse

# Cloud API session-message body cap. Leave headroom for "(n/m)\\n".
WHATSAPP_TEXT_LIMIT = 4096
CHUNK_BODY_LIMIT = 4000

_URL_RE = re.compile(r"https?://[^\s<>\"')\]]+", re.IGNORECASE)
_ARTICLE_HOSTS = (
    "x.com",
    "twitter.com",
    "t.co",
    "mobile.twitter.com",
    "www.twitter.com",
    "nitter.net",
)
# Whole phrases only. Bare "link" also matches "linkedin".
_ARTICLE_PHRASE_RE = re.compile(
    r"(?:"
    r"\bread\s+this\s+link\b|"
    r"\bread\s+(?:the\s+)?article\b|"
    r"\bread\s+this\b|"
    r"\bthis\s+link\b|"
    r"\bthe\s+article\b|"
    r"\barticle\b|"
    r"\bsummar(?:y|ize|ise)\b|"
    r"\bwhat does this mean\b|"
    r"\banalys[ei]|"
    r"\bventurebeat\b"
    r")",
    re.IGNORECASE,
)
_FRUSTRATION_RE = re.compile(
    r"^\s*(?:"
    r"dude\b|"
    r"no+\b|"
    r"nope\b|"
    r"wrong\b|"
    r"not (?:that|it|this|what i)\b|"
    r"read(?:\s+the)?\s+article\b|"
    r"that(?:'s| is) not\b|"
    r"you (?:missed|didn't|did not|got (?:it )?wrong)\b|"
    r"try again\b|"
    r"re-?read\b|"
    r"i (?:said|asked) (?:to )?read\b"
    r")",
    re.IGNORECASE,
)
_JOB_ITEM_RE = re.compile(
    r"\b(?:bench|banquette|booth|cushion|cushions|pillow|drape|drapes|drapery|"
    r"shade|shades|roman|headboard|valance|cornice|upholster\w*|"
    r"chair|seat|ottoman|sofa|curtain|slipcover|foam)\b",
    re.IGNORECASE,
)
_JOB_DIM_RE = re.compile(
    r"(?:\d+\s+\d+\s*/\s*\d+|\d+\s*/\s*\d+|\d+(?:\.\d+)?)\s*"
    r"(?:inches|inch|in\b|\"|foot|feet|ft\b|yards?|yd\b)",
    re.IGNORECASE,
)
_JOB_CLIENT_RE = re.compile(
    r"\b(?:quote|estimate|invoice|drawing)\s+for\s+[A-Za-z]",
    re.IGNORECASE,
)
_JOB_CREATE_RE = re.compile(
    r"\b(?:new|make|create|start|draft|build|prepare|write up)\b[^.?!]{0,40}"
    r"\b(?:quote|estimate|invoice|drawing)\b",
    re.IGNORECASE,
)
_EMPTY_EMPHASIS_RE = re.compile(
    r"(\*{2,}|_{2,}|~{2,}|`{2,})\s*\1"
)
_EMPTY_BOLD_RUN_RE = re.compile(r"\*{3,}")
_MD_HEADING_RE = re.compile(r"(?m)^\s{0,3}#{1,6}\s+")
_MD_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
_SOURCES_HEADING_RE = re.compile(
    r"(?im)^(?:#{1,6}\s*)?(?:\*{0,2}|_{0,2})sources?(?:\*{0,2}|_{0,2})\s*:?\s*$"
)
_SOURCES_INLINE_RE = re.compile(r"(?im)^(?:#{1,6}\s*)?sources?\s*:\s+")


def first_url(text: str | None) -> str:
    if not text:
        return ""
    match = _URL_RE.search(text)
    if not match:
        return ""
    return match.group(0).rstrip(").,!?;:\"'")


def _host(url: str) -> str:
    try:
        return (urlparse(url).netloc or "").lower().split(":")[0]
    except Exception:
        return ""


def is_link_or_article_message(text: str | None) -> bool:
    """True for URL-only / article-share turns. Those are never quote intake.

    Job signals win: item + dimensions/client/create-verb is quote intake
    even when the message also has an X/twitter/Pinterest URL.
    """
    raw = (text or "").strip()
    if not raw:
        return False
    if _text_has_job_signals(raw):
        return False
    url = first_url(raw)
    if not url:
        return False
    leftover = _URL_RE.sub("", raw).strip(" \t\r\n-–—:.")
    leftover = re.sub(r"\s+", " ", leftover)
    if not leftover:
        return True
    if len(leftover) <= 24 and not _JOB_ITEM_RE.search(leftover) and not _JOB_DIM_RE.search(leftover):
        return True
    host = _host(url)
    if any(host == h or host.endswith("." + h) for h in _ARTICLE_HOSTS):
        return True
    return bool(_ARTICLE_PHRASE_RE.search(raw))


def is_frustration_correction(text: str | None) -> bool:
    """Founder saying the previous answer missed. Re-read; do not repeat."""
    raw = (text or "").strip()
    if not raw or len(raw) > 240:
        return False
    return bool(_FRUSTRATION_RE.search(raw))


def _text_has_job_signals(raw: str, extraction: Any = None) -> bool:
    """Item + (dims/client/create) or create + (item/dims/client). Ignores URLs."""
    item = False
    dims = False
    client = False
    create = bool(_JOB_CREATE_RE.search(raw) or _JOB_CLIENT_RE.search(raw))
    if extraction is not None:
        items = getattr(extraction, "items", None) or []
        if items:
            first = items[0]
            item = bool(getattr(first, "item_type", "") or getattr(first, "name", ""))
            dims = any(
                getattr(first, key, None)
                for key in ("width_in", "depth_in", "seat_height_in", "back_height_in")
            )
        client = bool(getattr(extraction, "client_name", "") or "")
    item = item or bool(_JOB_ITEM_RE.search(raw))
    dims = dims or bool(_JOB_DIM_RE.search(raw))
    if not client:
        client = bool(_JOB_CLIENT_RE.search(raw))
    if item and (dims or client or create):
        return True
    if create and (item or dims or client):
        return True
    return False


def has_real_job_signals(text: str | None, extraction: Any = None) -> bool:
    """Quote intake needs a real job: item and/or dimensions plus client or create-verb.

    A URL, a tweet, or a lone number is not enough. A job that happens to
    include a fabric/X/Pinterest URL still counts.
    """
    raw = (text or "").strip()
    if not raw:
        return False
    return _text_has_job_signals(raw, extraction)


def strip_empty_markdown(text: str) -> str:
    """Drop empty emphasis such as ``****`` / ``____`` left by a blank title."""
    out = text or ""
    out = _EMPTY_EMPHASIS_RE.sub("", out)
    out = _EMPTY_BOLD_RUN_RE.sub("", out)
    out = re.sub(r"(?m)^\s*[*_~`]+\s*$", "", out)
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def markdown_to_whatsapp(text: str) -> str:
    """Convert common markdown to WhatsApp markup. Empty bold becomes nothing."""
    out = text or ""
    # Strip **** / ** ** first so they cannot glue onto a later **bold**.
    out = strip_empty_markdown(out)
    out = _MD_LINK_RE.sub(_format_md_link, out)
    out = _MD_HEADING_RE.sub("", out)
    out = _MD_BOLD_RE.sub(lambda m: f"*{m.group(1).strip()}*" if m.group(1).strip() else "", out)
    out = strip_empty_markdown(out)
    out = re.sub(r"[ \t]{2,}", " ", out)
    return out.strip()


def _format_md_link(match: re.Match) -> str:
    label = (match.group(1) or "").strip()
    url = (match.group(2) or "").strip()
    if label and url and label != url:
        return f"{label} ({url})"
    return label or url


def compact_sources_footer(text: str, *, max_sources: int = 3) -> str:
    """Collapse a Sources list into one footer line, at most ``max_sources``."""
    raw = text or ""
    lines = raw.splitlines()
    start = None
    for i, line in enumerate(lines):
        if _SOURCES_HEADING_RE.match(line.strip()) or _SOURCES_INLINE_RE.match(line):
            start = i
            break
    if start is None:
        return raw.strip()
    heading = lines[start]
    inline = _SOURCES_INLINE_RE.match(heading)
    collected: list[str] = []
    if inline:
        rest = heading[inline.end():].strip()
        if rest:
            collected.extend(p.strip(" -•") for p in re.split(r"\s*[;|]\s*|,\s+(?=[A-Z0-9http])", rest) if p.strip())
    end = len(lines)
    for j in range(start + 1, len(lines)):
        stripped = lines[j].strip()
        if not stripped:
            if collected:
                end = j
                break
            continue
        if re.match(r"^(?:#{1,6}\s+|[A-Z][^:]{0,40}:\s*$)", stripped) and not re.match(
            r"^\d+[.)]\s+", stripped
        ) and not stripped.startswith(("-", "•", "*")):
            end = j
            break
        collected.append(re.sub(r"^\d+[.)]\s*", "", stripped).lstrip("-•* ").strip())
    names: list[str] = []
    for item in collected:
        if not item:
            continue
        label = item
        link = _MD_LINK_RE.search(item)
        if link and link.group(1).strip():
            label = link.group(1).strip()
        else:
            url = first_url(item)
            if url:
                host = _host(url) or url
                leftover = _URL_RE.sub("", item).strip(" -–—:.")
                label = leftover or host
        label = re.sub(r"\s+", " ", label).strip()
        if label and label not in names:
            names.append(label)
        if len(names) >= max_sources:
            break
    head = "\n".join(lines[:start]).rstrip()
    tail = "\n".join(lines[end:]).lstrip()
    footer = f"Sources: {', '.join(names)}" if names else ""
    parts = [p for p in (head, footer, tail) if p]
    return "\n\n".join(parts).strip()


def prepare_whatsapp_text(text: str) -> str:
    """Full outbound cleanup: markdown → WhatsApp, empty marks gone, sources compact."""
    return compact_sources_footer(markdown_to_whatsapp(text or ""))


def chunk_whatsapp_text(text: str, *, limit: int = CHUNK_BODY_LIMIT) -> list[str]:
    """Split on paragraph boundaries, then lines, then words. Numbering is added later."""
    raw = (text or "").strip()
    if not raw:
        return []
    if len(raw) <= limit:
        return [raw]
    paragraphs = re.split(r"\n{2,}", raw)
    chunks: list[str] = []
    buf = ""

    def _flush() -> None:
        nonlocal buf
        if buf.strip():
            chunks.append(buf.strip())
        buf = ""

    def _append(piece: str) -> None:
        nonlocal buf
        piece = piece.strip("\n")
        if not piece:
            return
        if not buf:
            if len(piece) <= limit:
                buf = piece
                return
            _split_long(piece)
            return
        joined = f"{buf}\n\n{piece}"
        if len(joined) <= limit:
            buf = joined
            return
        _flush()
        if len(piece) <= limit:
            buf = piece
        else:
            _split_long(piece)

    def _split_long(piece: str) -> None:
        nonlocal buf
        lines = piece.splitlines() or [piece]
        line_buf = ""
        for line in lines:
            if not line_buf:
                candidate = line
            else:
                candidate = f"{line_buf}\n{line}"
            if len(candidate) <= limit:
                line_buf = candidate
                continue
            if line_buf:
                if buf and len(buf) + 2 + len(line_buf) <= limit:
                    buf = f"{buf}\n\n{line_buf}"
                else:
                    _flush()
                    if len(line_buf) <= limit:
                        buf = line_buf
                    else:
                        _words(line_buf)
                line_buf = ""
            if len(line) <= limit:
                line_buf = line
            else:
                _words(line)
        if line_buf:
            if buf and len(buf) + 2 + len(line_buf) <= limit:
                buf = f"{buf}\n\n{line_buf}"
            else:
                _flush()
                buf = line_buf

    def _words(piece: str) -> None:
        nonlocal buf
        words = piece.split()
        current = ""
        for word in words:
            trial = f"{current} {word}".strip() if current else word
            if len(trial) <= limit:
                current = trial
                continue
            if current:
                if buf and len(buf) + 2 + len(current) <= limit:
                    buf = f"{buf}\n\n{current}"
                else:
                    _flush()
                    buf = current
                    _flush()
                current = word if len(word) <= limit else word[:limit]
            else:
                _flush()
                chunks.append(word[:limit])
                current = ""
        if current:
            if buf and len(buf) + 2 + len(current) <= limit:
                buf = f"{buf}\n\n{current}"
            else:
                _flush()
                buf = current

    for para in paragraphs:
        _append(para)
    _flush()
    return [c for c in chunks if c]


def number_chunks(chunks: list[str]) -> list[str]:
    if len(chunks) <= 1:
        return list(chunks)
    total = len(chunks)
    return [f"({i}/{total})\n{chunk}" for i, chunk in enumerate(chunks, 1)]


def extract_image_payloads(tool_results: Any) -> list[dict[str, Any]]:
    """Pull generated-image local paths/bytes from tool results. No I/O if missing."""
    from pathlib import Path

    out: list[dict[str, Any]] = []
    for row in tool_results or []:
        if not isinstance(row, dict):
            continue
        tool = str(row.get("tool") or "")
        if tool not in {"minimax_text_to_image", "minimax_image_to_image", "generate_image"}:
            continue
        payload = row.get("result") or {}
        if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
            payload = payload["data"]
        images = []
        if isinstance(payload, dict):
            images = payload.get("images") or []
            if not images and payload.get("local_path"):
                images = [payload]
        for img in images:
            if not isinstance(img, dict):
                continue
            path = str(img.get("local_path") or "")
            data = img.get("data") or b""
            if not data and path:
                p = Path(path)
                if p.is_file():
                    try:
                        data = p.read_bytes()
                    except OSError:
                        data = b""
            if not data:
                continue
            name = str(img.get("filename") or (Path(path).name if path else "image.png"))
            mime = str(img.get("mime") or img.get("mime_type") or "image/png")
            out.append({
                "filename": name,
                "data": data,
                "mime": mime,
                "caption": str(img.get("caption") or ""),
                "kind": "image",
            })
    return out


def images_from_desk_result(result: Any) -> list[dict[str, Any]]:
    """Collect generated image bytes from a desk task result. No live send."""
    from pathlib import Path

    if isinstance(result, dict):
        return extract_image_payloads([
            {"tool": "minimax_text_to_image", "success": True, "result": result},
        ])
    text = str(result or "")
    found: list[dict[str, Any]] = []
    for match in re.findall(r"((?:/|[A-Za-z]:\\)[^\s\"']+\.(?:png|jpe?g|webp))", text, re.I):
        path = Path(match)
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        mime = "image/png" if suffix == ".png" else ("image/webp" if suffix == ".webp" else "image/jpeg")
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if data:
            found.append({"filename": path.name, "data": data, "mime": mime, "kind": "image"})
    return found
