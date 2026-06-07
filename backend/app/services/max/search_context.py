"""Search-context carry-forward for MAX web searches.

When MAX runs a web_search, the raw user message is often short or topic-implicit
(e.g. "current elections" after a prior turn about Colombia). This module
extracts topic keywords from the prior conversation and injects them into the
search query so the search targets the right region/topic.

Functions:
    build_search_query(message, history) -> dict
        Returns {"query": str, "context_injected": bool, "context_terms": list[str]}

    Looks at the most recent assistant + user turns to identify a topic anchor
    (proper noun, country, named person, named event). If the current message
    is short (< 6 words) OR contains a topic-implicit phrase like
    "current", "latest", "today", "now", "this year", it prepends the anchor
    to the query.

    The carry-forward is conservative: only injects when there is a clear
    single-topic anchor, and never removes the user's original words.
"""
from __future__ import annotations

import re
from typing import Any


# Phrases that signal the user is asking for "the latest" but expects the prior
# topic context to apply.
TOPIC_IMPLICIT_MARKERS = (
    "current",
    "latest",
    "now",
    "today",
    "this week",
    "this month",
    "this year",
    "recent",
    "ongoing",
    "right now",
    "at the moment",
    "happening now",
    "more",
    "what about",
    "how about",
    "and ",
    "what about that",
)


# Country / region names that are common carry-forward anchors. If a country
# appears in the prior turn and the current message is short or topic-implicit,
# inject the country into the search query.
KNOWN_COUNTRIES = {
    "colombia": ("Colombia", "Colombian"),
    "mexico": ("Mexico", "Mexican"),
    "brazil": ("Brazil", "Brazilian"),
    "argentina": ("Argentina", "Argentine"),
    "venezuela": ("Venezuela", "Venezuelan"),
    "united states": ("United States", "U.S."),
    "usa": ("USA", "U.S."),
    "us": ("U.S.", "American"),
    "spain": ("Spain", "Spanish"),
    "france": ("France", "French"),
    "germany": ("Germany", "German"),
    "italy": ("Italy", "Italian"),
    "japan": ("Japan", "Japanese"),
    "china": ("China", "Chinese"),
    "india": ("India", "Indian"),
    "uk": ("UK", "British"),
    "united kingdom": ("UK", "British"),
    "canada": ("Canada", "Canadian"),
    "australia": ("Australia", "Australian"),
}


def _extract_topic_anchor(history: list[dict[str, Any]] | None) -> str | None:
    """Return a single topic anchor from the most recent prior turns.

    Looks at the last 4 turns (user + assistant) and returns the most prominent
    proper noun / country / named event. Returns None if no clear anchor.
    """
    if not history:
        return None
    # Concatenate the last 4 messages, preferring the most recent user turn.
    recent: list[str] = []
    for h in history[-4:]:
        content = (h.get("content") or "").strip()
        if content:
            recent.append(content)
    text = " ".join(recent)
    if not text:
        return None

    lowered = text.lower()

    # 1. Check known country names first (most reliable anchor)
    for key, (canonical, _alt) in KNOWN_COUNTRIES.items():
        if re.search(rf"\b{re.escape(key)}\b", lowered):
            return canonical

    # 2. Look for capitalized multi-word proper nouns ("New York", "Los Angeles")
    proper_nouns = re.findall(
        r"\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,2})\b", text
    )
    if proper_nouns:
        # Filter out common sentence-start words
        blacklist = {"The", "This", "That", "There", "These", "Those", "Then",
                     "When", "Where", "While", "What", "How", "Why", "Who",
                     "And", "But", "Or", "So", "If", "Yes", "No", "I", "We",
                     "You", "It", "He", "She", "They", "My", "Our", "Your",
                     "His", "Her", "Its", "Their", "A", "An"}
        for noun in proper_nouns:
            if noun not in blacklist and len(noun) > 3:
                return noun

    return None


def _is_topic_implicit_or_short(message: str) -> bool:
    """True if the message is short or carries a topic-implicit marker.

    These are the messages that benefit most from carry-forward context.
    """
    text = (message or "").strip()
    if not text:
        return True
    word_count = len(text.split())
    if word_count <= 6:
        return True
    lowered = text.lower()
    return any(marker in lowered for marker in TOPIC_IMPLICIT_MARKERS)


def build_search_query(message: str, history: list[dict[str, Any]] | None = None) -> dict:
    """Build a search query with topic context carry-forward.

    Args:
        message: the current user message.
        history: list of prior turns, each a dict with role+content.

    Returns:
        A dict with keys:
            query: the search query string to send to web_search.
            context_injected: True if carry-forward was applied.
            context_terms: list of terms injected (for auditability).
    """
    raw = (message or "").strip()
    if not raw:
        return {"query": "", "context_injected": False, "context_terms": []}

    # Only inject context if the message is short or topic-implicit AND
    # we have a clear topic anchor from prior turns.
    if not _is_topic_implicit_or_short(raw):
        return {"query": raw, "context_injected": False, "context_terms": []}

    anchor = _extract_topic_anchor(history or [])
    if not anchor:
        return {"query": raw, "context_injected": False, "context_terms": []}

    # Don't re-add the anchor if it's already in the message
    if anchor.lower() in raw.lower():
        return {"query": raw, "context_injected": False, "context_terms": []}

    # Prepend the anchor to the query.
    injected = f"{anchor} {raw}"
    return {
        "query": injected,
        "context_injected": True,
        "context_terms": [anchor],
    }
