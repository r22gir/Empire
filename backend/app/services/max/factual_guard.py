"""Factual-answer grounding policy for MAX.

Public factual answers use the web regardless of whether the question is current
or evergreen. Internal Empire data and founder pricing rules stay on their
verified local-tool paths.
"""
import re


def _safe_tool_attr(result, attr: str, default=None):
    """Safely get an attribute from a ToolResult object or dict."""
    if isinstance(result, dict):
        return result.get(attr, default)
    return getattr(result, attr, default)


FACTUAL_PATTERNS = [
    r'\b(election|president|prime\s*minister|won|defeated|voted|poll|ballot)\b',
    r'\b(recent|latest|current|today|yesterday|this\s+week|this\s+month)\b',
    r'\b\d{1,2}%\b', r'\b\d{4}\b', r'\$\s*\d+[\.,]\d{2}',
    r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b',
    r'\b(price|cost|value|worth|estimate|quote)\b.*\b(per|each|unit|sqft|board\s*foot)\b',
    r'\b(statistic|data|survey|poll|study|research|report)\b',
    r'\b(average|median|majority|most|many|few)\b.*\b(client|customer|project|order)\b',
    r'\b(weather|temperature|forecast|stock|market\s*index|exchange\s*rate)\b',
]

# Evergreen explanatory/comparison questions. This intentionally catches
# "How does a French pleat compare..." while excluding conversational small talk.
EVERGREEN_FACTUAL_PATTERNS = [
    r'\bwhat\s+(?:is|are|does|do|causes?|makes?)\b',
    r'\bhow\s+(?:does|do|is|are|can|would)\b',
    r'\bwhy\s+(?:does|do|is|are|isn\'t|aren\'t)\b',
    r'\b(?:compare|comparison|difference|distinguish|versus|vs\.?|define|meaning|explain)\b',
    r'\bwhich\s+(?:is|are|has|have|should|would|works?)\b',
    r'\b(best|recommended|advantages?|disadvantages?|pros?\s+and\s+cons?)\b',
]

# Pure chit-chat should not incur a public web lookup.
CHITCHAT_PATTERNS = (
    r'\bhow are you\b', r'\bhow do you feel\b', r'\bwhat\'s up\b',
    r'\b(?:hello|hi|hey|thanks|thank you|good morning|good night)\b',
    r'\bwho are you\b', r'\bcan you help me\b',
)

# Internal Empire data and founder pricing doctrine are already governed by
# local verified tools/rules; web search would be both noisy and unsafe.
INTERNAL_PATTERNS = (
    'client:', 'project:', 'quote #', 'invoice #', 'order #', 'estimate #',
    'maria', 'david', 'alex', 'kayzark', 'empire', 'workroom', 'craftforge',
    'hermes', 'openclaw', 'max', 'crm', 'job status', 'work order',
    'founder pricing', 'our pricing rule', 'our rate card', 'internal rate',
)


def _is_internal_or_pricing(msg: str) -> bool:
    return any(ind in msg for ind in INTERNAL_PATTERNS)


def _is_chitchat(msg: str) -> bool:
    return any(re.search(pattern, msg, re.I) for pattern in CHITCHAT_PATTERNS)


def is_factual_question(message: str) -> bool:
    """Return whether a public factual answer needs web grounding."""
    msg = (message or '').lower().strip()
    if not msg or _is_internal_or_pricing(msg) or _is_chitchat(msg):
        return False
    if any(re.search(p, message, re.I) for p in FACTUAL_PATTERNS):
        return True
    # Evergreen questions should be lookup-backed even without a date word.
    return any(re.search(p, message, re.I) for p in EVERGREEN_FACTUAL_PATTERNS)


def grounding_directive(message: str | None = None) -> str:
    """Prompt contract for numbered citations, Sources, and fact/inference split."""
    return (
        "Public factual-answer grounding requirement: use the web results and cite every "
        "factual claim with a numbered inline markdown citation immediately after it, "
        "such as [1](https://example.com). End with a numbered Sources list whose links "
        "match those citations. Include two clearly labeled sections: `Verified` for "
        "claims supported by the fetched sources, and `Max's inference` for conclusions "
        "or recommendations drawn from them. Mark inference explicitly and never present "
        "it as source fact. For evergreen questions, use the best authoritative sources "
        "of any age; do not impose a date limit. Do not invent dates, sources, or citations."
    )


def enforce_web_search(message: str, tools_used: list) -> tuple[bool, str]:
    if not is_factual_question(message):
        return True, ""
    if "web_search" in tools_used:
        return True, ""
    return False, (
        "I need to verify this information from reliable sources before answering. "
        "Let me search the web for current or authoritative data on this topic."
    )
