"""Small, deterministic answer-quality guards used at the response boundary.

This module deliberately does not impose a universal age/date cutoff. Freshness is
an intent of the question; historical questions remain historical.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any

FLAGS = ("truncated", "stale_source", "empty_section", "user_repeat", "pushback")

_CURRENT_RE = re.compile(r"\b(latest|current|today|now|recent|this\s+(?:week|month|year)|breaking|news)\b", re.I)
_HISTORICAL_RE = re.compile(r"\b(history|historical|in\s+\d{4}|during|before\s+\d{4}|originally|at\s+the\s+time)\b", re.I)
_HEADING_ONLY_RE = re.compile(r"(?m)^\s{0,3}#{1,6}\s+[^\n]+\s*$")
_EMPTY_SECTION_RE = re.compile(r"(?ms)^\s{0,3}#{1,6}\s+[^\n]+\s*\n\s*(?=\n|#{1,6}\s|$)")
_DANGLING_INTRO_RE = re.compile(r"(?im)(?:^|\n)\s*(?:here(?:'|’)s|key points?|the (?:main|best) options?|sources?|summary)\s*:\s*$")


def freshness_intent(message: str | None) -> str:
    text = message or ""
    if _HISTORICAL_RE.search(text):
        return "historical"
    if _CURRENT_RE.search(text):
        return "fresh"
    return "general"


def freshness_directive(message: str | None) -> str:
    """Prompt guidance for current queries; no rigid 14-day filter."""
    if freshness_intent(message) != "fresh":
        return ""
    today = date.today().isoformat()
    return (
        "Freshness/grounding requirement: this is a current/recent query. Use web results "
        "appropriate to the requested time window (no universal 14-day cutoff). "
        f"Today is {today}. For every item, show its publication date; if a source is undated, "
        "fetch the page to find the date or label it explicitly as undated. Ground factual "
        "claims with markdown links to the source URLs. Do not invent dates or citations."
    )


def strip_empty_sections(text: str) -> str:
    """Remove headings/intro lines that have no body, preserving useful text."""
    if not text:
        return text or ""
    cleaned = _EMPTY_SECTION_RE.sub("", text)
    cleaned = _DANGLING_INTRO_RE.sub("", cleaned)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def detect_quality_flags(
    text: str | None,
    *,
    user_message: str | None = None,
    tool_results: list[dict[str, Any]] | None = None,
    finish_reason: str | None = None,
) -> dict[str, bool]:
    """Return the requested per-turn self-score flags."""
    body = (text or "").strip()
    tools = tool_results or []
    flags = {name: False for name in FLAGS}
    flags["empty_section"] = bool(_EMPTY_SECTION_RE.search(body) or _DANGLING_INTRO_RE.search(body) or _HEADING_ONLY_RE.fullmatch(body))
    flags["truncated"] = bool(
        finish_reason == "length"
        or (body and _HEADING_ONLY_RE.fullmatch(body) is not None)
        or (tools and len(body) < 40)
    )
    msg = (user_message or "").lower()
    flags["user_repeat"] = bool(re.search(r"\b(again|repeat|same thing|once more|you forgot|incomplete)\b", msg))
    flags["pushback"] = bool(re.search(r"\b(that'?s wrong|incorrect|not right|you misunderstood|not what i asked)\b", msg))
    # A web answer that has no date or source marker is a stale-source risk.
    has_web = any(str(item.get("tool", "")) in {"web_search", "web_read"} for item in tools if isinstance(item, dict))
    flags["stale_source"] = bool(has_web and not re.search(r"(?:https?://|\b(?:published|posted|updated|date)\b|\b20\d{2}\b)", body, re.I))
    return flags


def needs_continuation(text: str | None, *, user_message: str | None = None, tool_results: list[dict[str, Any]] | None = None) -> bool:
    """Detect the 9/30 heading-only/truncated-final-response failure class."""
    body = (text or "").strip()
    if not body:
        return True
    if _EMPTY_SECTION_RE.search(body) or _DANGLING_INTRO_RE.search(body) or _HEADING_ONLY_RE.fullmatch(body):
        return True
    if _HEADING_ONLY_RE.fullmatch(body):
        return True
    if tool_results and len(body) < 40:
        return True
    if user_message and len(user_message.split()) >= 8 and len(body) < 24:
        return True
    return False
