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


def _fold_accents(text: str) -> str:
    """Fold Spanish accents so 'qué pasó' and 'Que paso' match the same patterns."""
    return (
        (text or "")
        .replace("á", "a").replace("é", "e").replace("í", "i")
        .replace("ó", "o").replace("ú", "u").replace("ü", "u").replace("ñ", "n")
        .replace("Á", "A").replace("É", "E").replace("Í", "I")
        .replace("Ó", "O").replace("Ú", "U").replace("Ü", "U").replace("Ñ", "N")
    )


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
    # Spanish evergreen (accent-folded). Skip deictics and help-offers.
    r'\bque\s+(?:es|son|significa)\s+(?!eso\b|esto\b|aquello\b|asi\b)',
    r'\bcomo\s+(?:es|son|funciona|se\b|hacer|va)\b',
    r'\bpor\s+que\s+(?!no\s+funciona)',
    r'\bdiferencia\s+entre\b',
]

# News-intent cues only. Bare "hoy" / "ayer" must not search on their own.
_SPANISH_NEWS_CUES = (
    r'\bque\s+paso\b',
    r'\bque\s+esta\s+pasando\b',
    r'\bnoticias\b',
    r'\bultima\s+hora\b',
    r'\bquien\s+gano\b',
    r'\bcuanto\s+(?:cuesta|esta|es|vale)\b',
    r'\bclima\b',
    r'\b(?:dolar|trm)\b',
    r'\bresultados?\b',
    r'\belecciones?\b',
)

# Casual Spanish that mentions time or question words without asking for news.
_CASUAL_SPANISH = (
    r'\bhoy\s+no\s+(?:puedo|puedes|podemos|voy|vamos)\b',
    r'\bvoy\s+a\s+(?:casa|la\s+casa)\b',
    r'\bcomo\s+puedo\s+ayudarte\b',
    r'\bque\s+es\s+(?:eso|esto|aquello|asi)\b',
    r'\bpor\s+que\s+no\s+funciona\b',
    r'\bque\s+tal\b',
)

# Pure chit-chat should not incur a public web lookup.
# These are whole-message greetings so "hola, qué pasó en Panamá" still searches.
CHITCHAT_PATTERNS = (
    r'^(?:how are you|how do you feel|what\'s up)(?:\s+today)?\s*[?.!]*$',
    r'^(?:hello|hi|hey|thanks|thank you|good morning|good night)\s*[?.!]*$',
    r'^(?:who are you|can you help me)\s*[?.!]*$',
    r'^(?:hola|gracias|buenos\s+dias|buenas\s+tardes|buenas\s+noches)\s*[?.!]*$',
    r'^(?:como\s+estas?|como\s+te\s+va)\s*[?.!]*$',
    r'^(?:como\s+puedo\s+ayudarte)\s*[?.!]*$',
)

# Internal Empire data and founder pricing doctrine are already governed by
# local verified tools/rules; web search would be both noisy and unsafe.
# Match these as whole tokens so 'max' does not fire inside Max-e, máximo,
# alexandra, or empirebox.
INTERNAL_PATTERNS = (
    'client:', 'project:', 'quote #', 'invoice #', 'order #', 'estimate #',
    'maria', 'david', 'alex', 'kayzark', 'empire', 'workroom', 'craftforge',
    'hermes', 'openclaw', 'max', 'crm', 'job status', 'work order',
    'founder pricing', 'our pricing rule', 'our rate card', 'internal rate',
)

# Phrase indicators keep a literal match. Single tokens use a hyphen-aware
# word boundary so "max-e" and "máximo" are not treated as "max".
_INTERNAL_PHRASE_MARKERS = tuple(
    p for p in INTERNAL_PATTERNS if any(ch in p for ch in (':', '#', ' '))
)
_INTERNAL_TOKEN_RE = re.compile(
    r'(?<![\w-])('
    + '|'.join(re.escape(p) for p in INTERNAL_PATTERNS if p not in _INTERNAL_PHRASE_MARKERS)
    + r')(?![\w-])',
    re.I,
)

SEARCH_FAILURE_ES = (
    "No pude consultar fuentes ahora. Inténtalo de nuevo en un momento."
)


def _is_internal_or_pricing(msg: str) -> bool:
    folded = _fold_accents(msg)
    if any(ind in folded for ind in _INTERNAL_PHRASE_MARKERS):
        return True
    return _INTERNAL_TOKEN_RE.search(folded) is not None


def _is_chitchat(msg: str) -> bool:
    folded = _fold_accents(msg)
    return any(re.search(pattern, folded, re.I) for pattern in CHITCHAT_PATTERNS)


def _has_spanish_news_cue(msg: str) -> bool:
    return any(re.search(pattern, msg, re.I) for pattern in _SPANISH_NEWS_CUES)


def _is_casual_spanish(msg: str) -> bool:
    return any(re.search(pattern, msg, re.I) for pattern in _CASUAL_SPANISH)


def _is_spanish_greeting_lead(msg: str) -> bool:
    return bool(re.match(
        r'^(?:hola|buenos\s+dias|buenas\s+tardes|buenas\s+noches|gracias)\b',
        msg,
        re.I,
    ))


def is_factual_question(message: str) -> bool:
    """Return whether a public factual answer needs web grounding."""
    raw = (message or '').strip()
    if not raw:
        return False
    msg = _fold_accents(raw).lower()
    if _is_internal_or_pricing(msg):
        return False
    news = _has_spanish_news_cue(msg)
    if (_is_chitchat(msg) or _is_casual_spanish(msg) or _is_spanish_greeting_lead(msg)) and not news:
        return False
    if news:
        return True
    if any(re.search(p, msg, re.I) for p in FACTUAL_PATTERNS):
        return True
    # Evergreen questions should be lookup-backed even without a date word.
    return any(re.search(p, msg, re.I) for p in EVERGREEN_FACTUAL_PATTERNS)


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


def search_unavailable_reply() -> str:
    """Short Spanish reply when web search fails. Never 'no tengo información'."""
    return SEARCH_FAILURE_ES


def enforce_web_search(message: str, tools_used: list) -> tuple[bool, str]:
    if not is_factual_question(message):
        return True, ""
    if "web_search" in tools_used:
        return True, ""
    return False, (
        "I need to verify this information from reliable sources before answering. "
        "Let me search the web for current or authoritative data on this topic."
    )
