"""Absolute studio file links for Max chat.

ChatMarkdown only turns https:// (and same-origin /api/v1/files/found) into
buttons. Relative paths and /api/... without the studio host look like plain
text — that is the 'relative links aren't rendering as buttons' bug.

Rules:
- find_files / share_file always emit https://studio.empirebox.store/api/v1/files/found?t=...
- the first reply after a successful find must include those markdown links
- clean_reply must not strip a Sources block that is the file list
"""
from __future__ import annotations

import os
import re
from typing import Any, Iterable, Optional

from app.services.max import file_finder as ff

DEFAULT_PUBLIC_BASE = "https://studio.empirebox.store"
FOUND_PATH = "/api/v1/files/found"

_RELATIVE_MD = re.compile(
    r"\]\((/api/v1/files/found\?t=[^)\s]+)\)",
    re.IGNORECASE,
)
_BARE_RELATIVE = re.compile(
    r"(?<![(\w/])(/api/v1/files/found\?t=[A-Za-z0-9._=-]+)",
    re.IGNORECASE,
)
_ABS_FOUND = re.compile(
    r"https?://[^\s)\]>]+/api/v1/files/found\?t=[A-Za-z0-9._=-]+",
    re.IGNORECASE,
)
_DOC_LOOKUP = re.compile(
    r"\b(?:show|find|get|pull|open|list|where|send|share)\b.{0,60}\b"
    r"(?:docs?|documents?|pdfs?|files?)\b",
    re.IGNORECASE,
)
_DOC_CONTEXT = re.compile(
    r"\b(?:docs?|documents?|pdfs?|files?|links?|sources?|viewer|"
    r"find_files|share_file|files/found|relative links?|no links?)\b",
    re.IGNORECASE,
)


def public_base() -> str:
    return (os.getenv("EMPIRE_PUBLIC_BASE_URL") or DEFAULT_PUBLIC_BASE).rstrip("/")


def studio_found_url(path: str) -> str:
    """Signed 24h viewer URL on the public studio host."""
    return f"{public_base()}{FOUND_PATH}?t={ff.share_token(path)}"


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
    if existing.startswith("https://") and FOUND_PATH in existing:
        title = match.get("name") or "Document"
        match.setdefault("markdown_link", f"[{title}]({existing})")
        return match
    ref = str(match.get("file_id") or match.get("path") or match.get("file") or "")
    path = ff.resolve_file(ref) if ref else None
    if not path:
        return match
    url = studio_found_url(path)
    title = str(match.get("name") or os.path.basename(path) or "Document")
    match["viewer_url"] = url
    match["download_url"] = url + "&download=1"
    match["markdown_link"] = f"[{title}]({url})"
    return match


def attach_studio_links_to_matches(matches: Iterable[dict]) -> list[dict]:
    return [attach_studio_links(dict(m)) for m in (matches or [])]


def rewrite_relative_file_links(text: str | None) -> str:
    """Turn /api/v1/files/found?... into https://studio.../api/v1/files/found?..."""
    if not text:
        return text or ""
    base = public_base()

    def md(m: re.Match) -> str:
        return f"]({base}{m.group(1)})"

    def bare(m: re.Match) -> str:
        return f"{base}{m.group(1)}"

    out = _RELATIVE_MD.sub(md, text)
    return _BARE_RELATIVE.sub(bare, out)


def collect_found_links(tool_results: Any) -> list[tuple[str, str]]:
    """(title, absolute_url) from find_files / share_file results, first-seen order."""
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
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
            if FOUND_PATH not in url:
                continue
            if url.startswith("/"):
                url = public_base() + url
            if not url.startswith("http"):
                continue
            if url in seen:
                continue
            seen.add(url)
            title = str(row.get("name") or row.get("title") or "Document")
            out.append((title, url))
    return out


def _has_absolute_found_link(text: str) -> bool:
    return bool(_ABS_FOUND.search(text or ""))


def format_sources_block(links: list[tuple[str, str]]) -> str:
    lines = [f"{i}. [{title}]({url})" for i, (title, url) in enumerate(links, 1)]
    if len(lines) >= 2:
        return "Sources\n" + "\n".join(lines)
    return lines[0] if lines else ""


def ensure_absolute_doc_links(text: str | None, tool_results: Any = None) -> str:
    """Rewrite relative found-links and inject a titled Sources list if missing."""
    out = rewrite_relative_file_links(text or "")
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


def sources_block_has_file_links(text: str | None) -> bool:
    return bool(_ABS_FOUND.search(text or "") or re.search(
        r"/api/v1/files/found\?t=", text or "", re.IGNORECASE,
    ))
