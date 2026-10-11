"""Family answer policy: refuse company legal-detail questions on Maxine.

Maxine (Camilo's edition) does not hold or share company legal details.
This guard is fail-closed and language-aware (Spanish default, English
when the user writes in English). It uses only generic category words —
never stored values.
"""
from __future__ import annotations

import re
from typing import Optional

# Categories only. No stored values belong in this module.
_STRONG_LEGAL_RE = re.compile(
    r"(?i)\b("
    r"razon\s+social|nombre\s+legal|denominacion\s+social|legal\s+name|"
    r"nit\b|tax\s*id|tax\s+identification|identificacion\s+tributaria|"
    r"id\s+tributari[oa]|registro\s+mercantil|matricula\s+mercantil|"
    r"camara\s+de\s+comercio|company\s+registration|commercial\s+registration|"
    r"representante\s+legal|junta\s+directiva|oficiales\s+de\s+la\s+(?:empresa|compania|sociedad)|"
    r"company\s+officers?|corporate\s+officers?|"
    r"accionistas?|shareholders?|composicion\s+accionaria|"
    r"ownership\s+splits?|porcentaje(?:s)?\s+de\s+participacion|"
    r"escritura(?:s)?\s+(?:de\s+)?(?:constitucion|la\s+sociedad|publica)|"
    r"title\s+deeds?|property\s+deeds?|company\s+deeds?|"
    r"capital\s+social|share\s+capital|authorized\s+capital|"
    r"datos\s+legales|legal\s+details?|company\s+details?|"
    r"datos\s+de\s+la\s+(?:sociedad|compania|empresa)|"
    r"informacion\s+legal|legal\s+info(?:rmation)?"
    r")\b"
)

_WEAK_LEGAL_RE = re.compile(
    r"(?i)\b("
    r"socios?|partners?|officers?|abogados?|lawyers?|counsel|"
    r"apoderados?|gerentes?|escrituras?|deeds?"
    r")\b"
)

_COMPANY_CONTEXT_RE = re.compile(
    r"(?i)\b("
    r"empresa|compania|sociedad|company|corporation|entity|"
    r"marca|brand|grupo|group"
    r")\b"
)

_EN_CUE_RE = re.compile(
    r"(?i)\b("
    r"what|whats|what'?s|which|who|tell\s+me|do\s+you|"
    r"legal\s+name|tax\s+id|shareholders?|officers?|"
    r"registration|lawyers?|company\s+details?|legal\s+details?"
    r")\b"
)

_ES_CUE_RE = re.compile(
    r"(?i)\b("
    r"cual|quien|que|razon|datos|nit|socios|escritura|"
    r"abogado|compania|empresa|sociedad"
    r")\b"
)

# Vague "send it and I will store it" replies must never pass as a refusal.
SAVE_OFFER_RE = re.compile(
    r"(?i)("
    r"comparte(?:me|los|las)?|pasame|env[ií]ame|mandame|"
    r"te\s+lo\s+guardo|los\s+guardo|las\s+guardo|"
    r"guardo\s+(?:el|los|las|ese|esa|esos)\s+dato|"
    r"share\s+the\s+data|send\s+(?:me\s+)?(?:the\s+)?data|"
    r"i(?:'|’)ll\s+save|i\s+will\s+save|i\s+can\s+save"
    r")"
)

REFUSAL_ES = (
    "No tengo ni comparto los datos legales de la compañía. "
    "No guardo razón social, identificación tributaria, registro, "
    "oficiales, socios, escrituras, capital ni abogados. "
    "Puedo hablar solo de la información pública del proyecto."
)

REFUSAL_EN = (
    "I don't hold or share company legal details. "
    "I do not keep legal name, tax ID, registration, officers, "
    "shareholders, deeds, capital, or lawyers. "
    "I can only point to public project information."
)

MAXINE_LEGAL_PROMPT_RULE = (
    "You do not hold or share company legal details "
    "(legal name, tax ID, registration, officers, shareholders, "
    "ownership splits, partners, deeds, capital, lawyers). "
    "If asked, refuse clearly and politely in the user's language "
    "(Spanish by default). Do not ask anyone to send those details "
    "so you can save them. Point only to public project information."
)


def _fold(text: str) -> str:
    return (
        (text or "")
        .replace("á", "a").replace("é", "e").replace("í", "i")
        .replace("ó", "o").replace("ú", "u").replace("ü", "u").replace("ñ", "n")
        .replace("Á", "A").replace("É", "E").replace("Í", "I")
        .replace("Ó", "O").replace("Ú", "U").replace("Ü", "U").replace("Ñ", "N")
    )


def reply_locale(message: str) -> str:
    """Spanish unless the user clearly wrote in English."""
    folded = _fold(message or "")
    en = len(_EN_CUE_RE.findall(folded))
    es = len(_ES_CUE_RE.findall(folded))
    return "en" if en > es else "es"


def looks_like_company_legal_query(message: str) -> bool:
    """True when the turn asks for company legal-detail categories."""
    folded = _fold(message or "").strip()
    if not folded:
        return False
    if _STRONG_LEGAL_RE.search(folded):
        return True
    if _WEAK_LEGAL_RE.search(folded) and _COMPANY_CONTEXT_RE.search(folded):
        return True
    return False


def is_save_offer_reply(text: str) -> bool:
    return bool(SAVE_OFFER_RE.search(text or ""))


def legal_details_refusal(locale: Optional[str] = None) -> str:
    lang = (locale or "es").strip().lower()
    if lang.startswith("en"):
        return REFUSAL_EN
    return REFUSAL_ES


def maxine_legal_prompt_rule() -> str:
    return MAXINE_LEGAL_PROMPT_RULE


def _edition_is_maxine() -> bool:
    """Fail closed: if the edition cannot be read, treat as Maxine."""
    try:
        from app.edition import is_maxine

        return bool(is_maxine())
    except Exception:
        return True


def family_answer_policy_reply(message: str) -> Optional[str]:
    """Return a canned refusal for Maxine legal-detail asks, else None.

    Fail closed: an edition-lookup error still refuses a matching ask.
    """
    try:
        match = looks_like_company_legal_query(message)
    except Exception:
        match = True
    if not match:
        return None
    try:
        if not _edition_is_maxine():
            return None
    except Exception:
        pass
    try:
        locale = reply_locale(message)
    except Exception:
        locale = "es"
    return legal_details_refusal(locale)


def should_skip_public_lookup(message: str) -> bool:
    """Do not web-search company legal-detail asks on Maxine."""
    return family_answer_policy_reply(message) is not None
