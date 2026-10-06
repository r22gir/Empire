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


# 2026-10-06: explicit research intent. Questions addressed to Max about himself or
# "us" (what are you building, what's next with you, what did we ship) never go to
# the web unless Rafael explicitly asks for research.
EXPLICIT_RESEARCH_RE = re.compile(
    r"\b(research|look\s+(?:it\s+)?up|search(?:\s+the\s+web|\s+online|\s+for)?|google|web|online|internet|"
    r"sources?|cite|citations?|articles?|news|find\s+out)\b", re.I)
SELF_ADDRESSED_RE = re.compile(
    r"\b(?:are|were|r)\s+(?:you|u)\b|\b(?:you|u)\s+(?:are|were|building|working|doing|shipping|planning|up\s+to)\b|"
    r"\b(?:have|did)\s+(?:you|we)\s+(?:built|build|ship|shipped|done|do|finish|finished)\b|"
    r"\b(?:your|our)\s+(?:plan|plans|queue|status|next|roadmap|work|progress|build|builds|priorities)\b|"
    r"\b(?:with|for)\s+(?:you|us)\s*\??$|\bnext\s+steps?\b|\bin\s+progress\b", re.I)


def has_explicit_research_intent(message: str) -> bool:
    return bool(EXPLICIT_RESEARCH_RE.search(message or ''))


def is_self_addressed(message: str) -> bool:
    """About Max / EmpireBox's own work rather than a public topic."""
    try:
        from app.services.max.self_status import is_self_status_question
        if is_self_status_question(message):
            return True
    except Exception:
        pass
    return bool(SELF_ADDRESSED_RE.search(message or ''))


def is_factual_question(message: str) -> bool:
    """Return whether a public factual answer needs web grounding."""
    msg = (message or '').lower().strip()
    if not msg or _is_internal_or_pricing(msg) or _is_chitchat(msg):
        return False
    if is_self_addressed(message) and not has_explicit_research_intent(message):
        return False
    if any(re.search(p, message, re.I) for p in FACTUAL_PATTERNS):
        return True
    # Evergreen questions should be lookup-backed even without a date word.
    return any(re.search(p, message, re.I) for p in EVERGREEN_FACTUAL_PATTERNS)


def undated_source_label(message: str | None) -> str:
    """Label used only when a fetched page has no publication or updated date."""
    text = message or ""
    if re.search(
        r"[¿¡]|\b(?:tela|telas|cuál|cual|recomienda|fuentes|comparación|comparacion|compara|precio)\b",
        text,
        re.I,
    ):
        return "fecha no indicada"
    return "date not shown"


def grounding_directive(message: str | None = None) -> str:
    """Prompt contract for numbered citations, Sources, and fact/inference split."""
    undated = undated_source_label(message)
    recommend = ""
    if message and re.search(
        r"\b(compare|comparison|vs\.?|versus|which|recommend|better|best)\b",
        message,
        re.I,
    ):
        recommend = (
            " The question asks for a comparison or a choice: state a clear recommendation "
            "and name the option you would use."
        )
    return (
        "Public factual-answer grounding requirement: the full text of the top relevant "
        "pages has already been fetched. Answer from that page text, not from search "
        "snippets alone. Cite every factual claim with a numbered inline markdown citation "
        "immediately after it, such as [1](https://example.com). End with a numbered Sources "
        "list whose links match those citations and include each source's publication or "
        f"updated date. If a page truly has no date, write exactly '{undated}'. "
        "Include two clearly labeled sections: `Verified` for claims supported by the fetched "
        "pages, and `Max's inference` for conclusions or recommendations drawn from them. "
        "Mark inference explicitly and never present it as source fact. For evergreen "
        "questions, use the best authoritative sources of any age; do not impose a date limit. "
        "Do not invent dates, sources, or citations. Quote concrete figures that appear in "
        "the page text (ratings, prices, cleaning methods, dimensions) when the question "
        "asks for them. Do not leave an empty heading or a colon introduction with no items "
        "under it. Do not offer to open, read, or fetch the articles — that lookup is already done. "
        "Keep it short: lead with the direct answer in 1-2 sentences, keep `Verified` and "
        "`Max's inference` to a few bullets each, stay under about 200 words before the Sources "
        "list unless the user asked for a detailed report, and write each source as one line: "
        "`N. Title — site (date)`."
        + recommend
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
