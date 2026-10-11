"""Sanitize MiniMax image/video prompts.

Client photos and Workroom records must not enter family-edition prompts.
Family editions never receive Workroom quotes, jobs, CRM, or host paths.
"""
from __future__ import annotations

import re
from typing import Optional

_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\s().-]?){8,15}\d(?!\w)")
_PATH_RE = re.compile(
    r"(?:"
    r"/home/rg\S*"
    r"|~/empire\S*"
    r"|/data/(?:amp|maxine|empire|images|backups|workroom|photos)\S*"
    r"|empire-repo\S*"
    r"|empire-data/photos\S*"
    r"|/api/v1/photos/\S*"
    r"|workroom-showroom/photos\S*"
    r")"
)
_DATA_URI_RE = re.compile(r"data:image/[^;]+;base64,[A-Za-z0-9+/=\s]+", re.I)
_SECRET_RE = re.compile(
    r"(?i)\b(api[_-]?key|secret|token|password|passwd|jwt|minimax_api_key)\s*[:=]\s*\S+"
)

WORKROOM_MARKERS = (
    "frolich",
    "hyattsville",
    "workroom@",
    "woodcraft@",
    "nelma",
    "nehal",
    "dahlia",
    "the willard",
    "mclean whittington",
    "empire workroom",
    "9408 old courthouse",
    "rg's drapery",
)

# Host paths to Workroom client photos. Family image prompts must reject
# these outright — redacting is not enough (the model still saw the leak).
WORKROOM_PHOTO_MARKERS = (
    "/home/rg/empire-repo/backend/data/photos",
    "~/empire-repo/backend/data/photos",
    "empire-repo/backend/data/photos",
    "/data/photos/",
    "empire-data/photos",
    "/api/v1/photos/",
    "/photos/quote/",
    "/photos/fabric/",
    "/photos/serve/",
    "/photos/intake/",
    "photos/quote/",
    "photos/fabric/",
    "photos/intake/",
    "workroom-showroom/photos",
    "backend/data/photos",
)


class PromptRejected(ValueError):
    """Prompt still contains client / Workroom data after sanitizing."""


def sanitize_prompt(text: str, *, edition: Optional[str] = None, max_len: int = 2000) -> str:
    """Return a prompt safe to send to MiniMax image-01 / H3."""
    out = (text or "").strip()
    if not out:
        raise PromptRejected("empty prompt")
    lowered = out.lower()
    if edition in {"amp", "maxine"} or _family_process():
        for marker in WORKROOM_MARKERS:
            if marker in lowered:
                raise PromptRejected("workroom data is not allowed in family prompts")
        for marker in WORKROOM_PHOTO_MARKERS:
            if marker.lower() in lowered:
                raise PromptRejected("workroom photo path is not allowed in family prompts")
    out = _DATA_URI_RE.sub("[image omitted]", out)
    out = _SECRET_RE.sub("[redacted]", out)
    out = _EMAIL_RE.sub("[redacted]", out)
    out = _PHONE_RE.sub("[redacted]", out)
    out = _PATH_RE.sub("[path omitted]", out)
    try:
        from app.edition import is_family_edition
        from app.services.family_help import redact_text

        if is_family_edition() or (edition in {"amp", "maxine"}):
            out = redact_text(out, edition=edition)
    except Exception:
        pass
    cleaned = re.sub(r"\s+", " ", out).strip()
    if not cleaned:
        raise PromptRejected("prompt empty after redaction")
    return cleaned[:max_len]


def _family_process() -> bool:
    try:
        from app.edition import is_family_edition

        return is_family_edition()
    except Exception:
        return False


def family_blocks_reference_image() -> bool:
    """Family editions cannot send client photos into image-to-image."""
    return _family_process()
