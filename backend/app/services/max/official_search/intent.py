"""Detect official-source intent in English and Spanish."""
from __future__ import annotations

import re

_OFFICIAL_EN = (
    r"official(?:\s+source)?s?",
    r"primary\s+source",
    r"from\s+the\s+(?:agency|government|regulator|court)",
    r"\bgov(?:ernment)?\b",
    r"\.gov\b",
    r"federal\s+register",
    r"statute",
    r"regulation(?:s)?\.gov",
    r"congress\.gov",
    r"court\s+opinion",
    r"standards?\s+bod(?:y|ies)",
)

_OFFICIAL_ES = (
    r"oficial(?:es)?",
    r"fuente(?:s)?\s+oficial(?:es)?",
    r"gobierno",
    r"gubernamental",
    r"\.gov\b",
    r"sitio\s+oficial",
    r"p[aá]gina\s+oficial",
    r"normativa\s+oficial",
    r"diario\s+oficial",
    r"fuente\s+primaria",
)

_OFFICIAL_RE = re.compile(
    r"(?:" + "|".join(_OFFICIAL_EN + _OFFICIAL_ES) + r")",
    re.I,
)

_ES_HINTS = re.compile(
    r"\b(?:qu[eé]|cu[aá]l|cu[aá]les|d[oó]nde|c[oó]mo|por\s+qu[eé]|"
    r"oficial|gobierno|fuente|fuentes|ley|decreto|normativa|"
    r"buscar|busca|encuentra|encuentre)\b",
    re.I,
)


def is_official_intent(text: str | None, *, force: bool = False) -> bool:
    """True when the user asked for official / government / .gov sources."""
    if force:
        return True
    blob = (text or "").strip()
    if not blob:
        return False
    return bool(_OFFICIAL_RE.search(blob))


def detect_language(text: str | None) -> str:
    """Return 'es' or 'en' from the question. Conservative: default English."""
    blob = (text or "").strip()
    if not blob:
        return "en"
    if _ES_HINTS.search(blob):
        return "es"
    return "en"
