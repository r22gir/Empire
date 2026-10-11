"""Absolute public file links for Max web chat.

ChatMarkdown only turns http(s) (and same-origin /api/v1/files/found) into
buttons. Relative paths look like plain text.

Family editions (Max-e / Maxine) never fall back to studio.empirebox.store.
When public_base() is empty, nothing is rewritten or injected.
Voice and Telegram never get a Sources list or URLs (do not read them aloud).
"""
from __future__ import annotations

import os
import re
from typing import Any, Iterable
from urllib.parse import urlparse

from app.services.max import file_finder as ff

DEFAULT_PUBLIC_BASE = "https://studio.empirebox.store"
FOUND_PATH = "/api/v1/files/found"
SPOKEN_CHANNELS = frozenset({"voice", "telegram", "phone", "sms"})
_FAMILY_EDITIONS = frozenset({"amp", "maxine", "max-e", "maxe", "family"})
_FAMILY_PATHS = ("/data/amp", "/data/maxine", "empire-amp", "empire-maxine")

_RELATIVE_MD = re.compile(
    r"\]\((/api/v1/files/found\?t=[^)\s]+)\)",
    re.IGNORECASE,
)
_BARE_RELATIVE = re.compile(
    r"(?<![(\w/])(/api/v1/files/found\?t=[A-Za-z0-9._=-]+)",
    re.IGNORECASE,
)
_DOC_LOOKUP = re.compile(
    r"\b(?:show|find|get|pull|open|list|where|send|share|"
    r"muestra|muestrame|muéstrame|ensena|enséñame|busca|buscar)\b.{0,60}\b"
    r"(?:docs?|documents?|pdfs?|files?|documentos?|archivos?)\b",
    re.IGNORECASE,
)
_DOC_CONTEXT = re.compile(
    r"\b(?:docs?|documents?|pdfs?|files?|links?|sources?|viewer|"
    r"documentos?|archivos?|enlaces?|"
    r"find_files|share_file|files/found|relative links?|no links?)\b",
    re.IGNORECASE,
)


def is_family_edition() -> bool:
    ed = (os.getenv("EMPIRE_EDITION") or "").strip().lower()
    if ed in _FAMILY_EDITIONS:
        return True
    paths = " ".join(os.getenv(k, "") for k in ("EMPIRE_DATA_DIR", "DATABASE_URL", "MAX_MEMORY_PATH"))
    return any(m in paths for m in _FAMILY_PATHS)


def public_base() -> str:
    """Public origin for file links. Empty on family editions unless a non-studio host is set."""
    raw = (os.getenv("EMPIRE_PUBLIC_BASE_URL") or os.getenv("PUBLIC_BASE_URL") or "").strip().rstrip("/")
    if is_family_edition():
        if not raw or "studio.empirebox.store" in raw.lower():
            return ""
        return raw
    return raw or DEFAULT_PUBLIC_BASE


def is_spoken_channel(channel: str | None) -> bool:
    return (channel or "").strip().lower() in SPOKEN_CHANNELS


def _abs_found_re() -> re.Pattern | None:
    base = public_base()
    if not base:
        return None
    return re.compile(
        re.escape(base) + r"/api/v1/files/found\?t=[A-Za-z0-9._=-]+",
        re.IGNORECASE,
    )


def url_is_public_found_link(url: str | None) -> bool:
    """True only for a found-file link on this edition's public_base()."""
    if not url:
        return False
    base = public_base()
    if not base:
        return False
    u = url.strip()
    if u.startswith("/"):
        return False
    parsed = urlparse(u)
    if parsed.scheme not in ("http", "https"):
        return False
    allowed = urlparse(base)
    if parsed.netloc.lower() != allowed.netloc.lower():
        return False
    return FOUND_PATH in (parsed.path or "")


def studio_found_url(path: str) -> str:
    """Signed 24h viewer URL on the public host, or '' when this edition has no public base."""
    base = public_base()
    if not base:
        return ""
    return f"{base}{FOUND_PATH}?t={ff.share_token(path)}"


def is_document_lookup_request(text: str | None) -> bool:
    return bool(_DOC_LOOKUP.search(text or ""))


def history_text(history: Any, n: int = 6) -> str:
    parts: list[str] = []
    for h in list(history or [])[-n:]:
        if isinstance(h, dict):
            parts.append(str(h.get("content") or ""))
        else:
            parts.append(str(getattr(h, "content", "") or ""))
    return "\n".join(parts)


def recent_context_is_documents(history: Any) -> bool:
    return bool(_DOC_CONTEXT.search(history_text(history)))


def attach_studio_links(match: dict) -> dict:
    """Add absolute viewer_url + markdown_link onto a find_files match."""
    if not isinstance(match, dict):
        return match
    existing = str(match.get("viewer_url") or "")
    if url_is_public_found_link(existing):
        title = match.get("name") or "Document"
        match.setdefault("markdown_link", f"[{title}]({existing})")
        return match
    if not public_base():
        match.pop("viewer_url", None)
        match.pop("markdown_link", None)
        return match
    ref = str(match.get("file_id") or match.get("path") or match.get("file") or "")
    path = ff.resolve_file(ref) if ref else None
    if not path:
        return match
    url = studio_found_url(path)
    if not url:
        return match
    title = str(match.get("name") or os.path.basename(path) or "Document")
    match["viewer_url"] = url
    match["download_url"] = url + "&download=1"
    match["markdown_link"] = f"[{title}]({url})"
    return match


def attach_studio_links_to_matches(matches: Iterable[dict]) -> list[dict]:
    return [attach_studio_links(dict(m)) for m in (matches or [])]


def rewrite_relative_file_links(text: str | None) -> str:
    """Turn /api/v1/files/found?... into {public_base}/api/v1/files/found?..."""
    if not text:
        return text or ""
    base = public_base()
    if not base:
        return text

    def md(m: re.Match) -> str:
        return f"]({base}{m.group(1)})"

    def bare(m: re.Match) -> str:
        return f"{base}{m.group(1)}"

    out = _RELATIVE_MD.sub(md, text)
    return _BARE_RELATIVE.sub(bare, out)


def collect_found_links(tool_results: Any) -> list[tuple[str, str]]:
    """(title, absolute_url) from find_files / share_file on this edition's host."""
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    base = public_base()
    if not base:
        return out
    for entry in tool_results or []:
        if not isinstance(entry, dict) or not entry.get("success"):
            continue
        tool = str(entry.get("tool") or "")
        result = entry.get("result") or {}
        if not isinstance(result, dict):
            continue
        rows: list[dict] = []
        if tool == "find_files":
            rows = [m for m in (result.get("matches") or []) if isinstance(m, dict)]
        elif tool == "share_file":
            rows = [result]
        for row in rows:
            url = str(row.get("viewer_url") or "")
            if url.startswith("/"):
                url = base + url
            if not url_is_public_found_link(url):
                continue
            if url in seen:
                continue
            seen.add(url)
            title = str(row.get("name") or row.get("title") or "Document")
            out.append((title, url))
    return out


def _has_absolute_found_link(text: str) -> bool:
    pat = _abs_found_re()
    return bool(pat and pat.search(text or ""))


def format_sources_block(links: list[tuple[str, str]]) -> str:
    lines = [f"{i}. [{title}]({url})" for i, (title, url) in enumerate(links, 1)]
    if len(lines) >= 2:
        return "Sources\n" + "\n".join(lines)
    return lines[0] if lines else ""


def sources_chunk_is_public_file_list(chunk: str | None) -> bool:
    """Keep a Sources block only when it cites this edition's public found-file host."""
    if not chunk or not public_base():
        return False
    return _has_absolute_found_link(chunk)


def first_reply_link_instruction() -> str:
    """Prompt line that uses the live public_base(), or a no-URL rule when empty."""
    base = public_base()
    if not base:
        return ("Name each found file in the first reply. Do not emit public studio "
                "URLs or a Sources list of links.")
    return (f"Paste each markdown_link in the FIRST reply as [Title]({base}{FOUND_PATH}?t=...). "
            "Never use relative paths. Never read or paste those URLs on voice or Telegram.")


def ensure_absolute_doc_links(
    text: str | None,
    tool_results: Any = None,
    channel: str | None = None,
) -> str:
    """Rewrite relative found-links and inject a titled Sources list if missing.

    Voice / Telegram / phone: return the reply unchanged (no URLs, no Sources).
    Family / empty public_base: no rewriting or injection.
    """
    out = text or ""
    if is_spoken_channel(channel):
        return out
    if not public_base():
        return out
    out = rewrite_relative_file_links(out)
    links = collect_found_links(tool_results)
    if not links:
        return out
    present = sum(1 for _title, url in links if url in out)
    if present >= min(len(links), 2) and _has_absolute_found_link(out):
        return out
    if present == len(links) and _has_absolute_found_link(out):
        return out
    block = format_sources_block(links)
    if not block or block in out:
        return out
    body = out.strip()
    if not body:
        return f"Here are the documents:\n\n{block}"
    return f"{body}\n\n{block}"
