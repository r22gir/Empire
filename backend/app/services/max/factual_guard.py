"""Factual Question Guardrail: Enforces web_search for verifiable claims."""
import re

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


def is_factual_question(message: str) -> bool:
    msg = message.lower()
    # Exclude known internal/business topics that should use memory_search
    if any(ind in msg for ind in ['client:', 'project:', 'quote #', 'invoice #', 'order #', 'maria', 'david', 'alex', 'kayzark', 'empire', 'workroom', 'craftforge', 'hermes', 'max']):
        return False
    return any(re.search(p, message, re.I) for p in FACTUAL_PATTERNS)


def enforce_web_search(message: str, tools_used: list) -> tuple[bool, str]:
    if not is_factual_question(message):
        return True, ""
    if "web_search" in tools_used:
        return True, ""
    return False, (
        "I need to verify this information from reliable sources before answering. "
        "Let me search the web for current data on this topic."
    )