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
_TOOL_FAILURE_PLACEHOLDER_RE = re.compile(r"(?i)\b(?:i have not run that yet|web_(?:read|search):\s*(?:http|web read failed))\b")
_PHASE_HEADING_RE = re.compile(r"(?im)^\s{0,3}#{1,6}\s+phase\b")
_GOAL_LINE_RE = re.compile(r"(?im)^\s*(?:\*\*)?goal:\s*")
_STEP_LINE_RE = re.compile(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+\S")
# Offers to do a lookup the research path should already have done.
_LOOKUP_OFFER_RE = re.compile(
    r"(?i)\b(?:"
    r"want me to(?: go ahead and)?|"
    r"would you like me to|"
    r"do you want me to|"
    r"should i(?: go ahead and)?|"
    r"shall i|"
    r"i can(?: go ahead and)?|"
    r"let me"
    r")\s+"
    r"(?:open|read|fetch|pull up|look up|check out|grab)\b"
    r"[^.?\n]{0,120}"
    r"\b(?:articles?|pages?|links?|full (?:articles?|pages?|text)|"
    r"those (?:articles?|pages?|links?)|them)\b"
)

COMPLETENESS_RECOVERY_INSTRUCTION = (
    "The previous draft was incomplete, had an empty section, or offered to look "
    "something up instead of answering. Do NOT call tools. Using only the successful "
    "verified context below, return the complete final answer now, short and plain. Only "
    "when the founder asked for research or web sources: include numbered inline citations "
    "and a Sources list with publication or updated dates (write 'date not shown' or "
    "'fecha no indicada' only when that page truly has no date). If a comparison or "
    "recommendation was requested, state one. Do not leave an empty heading or a "
    "colon introduction with no items. Do not offer to open, read, or fetch the "
    "articles. Never mention tool errors. Every Phase heading must include concrete "
    "steps or deliverables, not only a Goal line."
)


def _next_content_index(lines: list[str], index: int) -> int:
    next_index = index + 1
    while next_index < len(lines) and not lines[next_index].strip():
        next_index += 1
    return next_index


def _colon_intro_has_no_body(lines: list[str], index: int) -> bool:
    """A ':' line is empty when nothing follows, or only a heading or lookup offer follows."""
    next_index = _next_content_index(lines, index)
    if next_index >= len(lines):
        return True
    if lines[next_index].lstrip().startswith(("#", "**Sources")):
        return True
    rest = [line for line in lines[next_index:] if line.strip()]
    if rest and all(_LOOKUP_OFFER_RE.search(line) for line in rest):
        return True
    return False


def _has_dangling_colon_intro(text: str) -> bool:
    """Detect a prose/list introduction ending in ':' with no body after it."""
    lines = (text or "").splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if len(stripped) < 4 or not stripped.endswith(":"):
            continue
        if _colon_intro_has_no_body(lines, index):
            return True
    return False


def _phase_sections_with_goal_only(text: str) -> bool:
    """Detect phased plan headings whose body is only a Goal line (9/30 finance report)."""
    if not _PHASE_HEADING_RE.search(text or ""):
        return False
    parts = re.split(r"(?m)^\s{0,3}#{1,6}\s+", text or "")
    for part in parts[1:]:
        body_lines = [ln.rstrip() for ln in part.splitlines()[1:] if ln.strip()]
        if not body_lines:
            return True
        non_goal = [ln for ln in body_lines if not _GOAL_LINE_RE.match(ln.strip())]
        if not non_goal:
            return True
        if not _STEP_LINE_RE.search("\n".join(non_goal)) and len(non_goal) < 2:
            return True
    return False


def _strip_dangling_colon_intros(text: str) -> str:
    lines = (text or "").splitlines()
    kept = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        if len(stripped) >= 4 and stripped.endswith(":") and _colon_intro_has_no_body(lines, index):
            continue
        kept.append(line)
    return "\n".join(kept)


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
    cleaned = _strip_dangling_colon_intros(cleaned)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def _strip_lookup_offers(text: str) -> str:
    """Drop sentences that offer to open or read sources instead of answering."""
    kept = []
    for line in (text or "").splitlines():
        if _LOOKUP_OFFER_RE.search(line):
            cleaned = _LOOKUP_OFFER_RE.sub("", line).strip(" ,;-")
            if cleaned and not cleaned.endswith(":"):
                kept.append(cleaned)
            continue
        kept.append(line)
    return "\n".join(kept)


def validate_reply_structure(text: str | None) -> list[str]:
    """Post-generation structure check.

    Returns issue codes. Empty means the reply can ship.
    ``empty_section`` — heading or phase with no body.
    ``dangling_colon`` — a list/section intro ending in ':' with nothing under it.
    ``lookup_offer`` — an offer to open or read pages that should already be done.
    """
    body = text or ""
    issues: list[str] = []
    if (
        _EMPTY_SECTION_RE.search(body)
        or _HEADING_ONLY_RE.fullmatch(body.strip())
        or _phase_sections_with_goal_only(body)
    ):
        issues.append("empty_section")
    if _DANGLING_INTRO_RE.search(body) or _has_dangling_colon_intro(body):
        issues.append("dangling_colon")
    if _LOOKUP_OFFER_RE.search(body):
        issues.append("lookup_offer")
    return issues


def repair_reply_structure(text: str | None) -> str:
    """Fill a structurally broken reply by removing empty sections and lookup offers."""
    cleaned = strip_empty_sections(text or "")
    cleaned = _strip_lookup_offers(cleaned)
    cleaned = strip_empty_sections(cleaned)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def enforce_reply_structure(text: str | None, regenerate=None) -> str:
    """Regenerate once when structure is invalid, then fill whatever remains."""
    body = text or ""
    issues = validate_reply_structure(body)
    if not issues:
        return body
    regenerated = None
    if regenerate is not None:
        try:
            regenerated = regenerate(list(issues))
        except Exception:
            regenerated = None
        if isinstance(regenerated, str) and regenerated.strip() and not validate_reply_structure(regenerated):
            return regenerated.strip()
    filled_new = repair_reply_structure(regenerated) if isinstance(regenerated, str) else ""
    filled_old = repair_reply_structure(body)
    if len(filled_new.strip()) >= 40 and len(filled_new) >= len(filled_old):
        return filled_new
    return filled_old


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
    flags["empty_section"] = bool(validate_reply_structure(body))
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
    if validate_reply_structure(body):
        return True
    if tool_results and any(isinstance(item, dict) and not item.get("success") for item in tool_results):
        if _TOOL_FAILURE_PLACEHOLDER_RE.search(body) or len(body) < 200:
            return True
    if _HEADING_ONLY_RE.fullmatch(body):
        return True
    if tool_results and len(body) < 40:
        return True
    if user_message and len(user_message.split()) >= 8 and len(body) < 24:
        return True
    return False
