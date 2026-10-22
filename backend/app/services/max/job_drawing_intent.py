"""Route job drawing / layout revision asks to Drawing Studio (forge / Kai).

Live miss (2026-10-21): "give me a drawing of the marleys job" was treated
as a file lookup; the follow-up spec change searched files; "you change it"
became a pipeline dump. These requests own the Drawing Studio desk, never
Sales / pipeline summary.

Follow-ups such as "you change it" inherit the prior job + spec from
conversation history. No live I/O — classification only.
"""
from __future__ import annotations

import re
from typing import Any, Optional

DRAWING_DESK_ID = "forge"
DRAWING_DESK_LABEL = "Kai (ForgeDesk / Drawing Studio)"

# Generate / revise a shop drawing for a named job (not "show me the docs").
_JOB_DRAWING_ASK = re.compile(
    r"\b(?:give|get|make|create|generate|draw|render|produce|need|want|"
    r"can you|could you|please)\b.{0,80}\b(?:drawing|drawings|layout|layouts|"
    r"shop drawing|shop drawings)\b|"
    r"\b(?:drawing|layout|shop drawing)\b.{0,40}\b(?:of|for|on)\b.{0,40}\b"
    r"(?:job|estimate|quote|client|banquette|bench)\b|"
    r"\b(?:drawing|layout)\b.{0,20}\b(?:the\s+)?\w+(?:'s)?\s+job\b|"
    r"\b(?:job|estimate|quote)\b.{0,40}\b(?:drawing|layout)\b",
    re.I,
)

_LAYOUT_REVISION = re.compile(
    r"\b(?:this|that|the)\s+layout\b|"
    r"\b(?:older|old)\s+(?:one|layout|drawing)\b|"
    r"\bwe need the (?:one|layout|drawing)\b|"
    r"\brevis(?:e|ed|ion)\b.{0,40}\b(?:drawing|layout)\b|"
    r"\b(?:drawing|layout)\b.{0,40}\brevis(?:e|ed|ion)\b|"
    r"\bchannel(?:s)?\s+back\b|"
    r"\bchannel(?:s)?\s+(?:at|to|of|width|wide)\b|"
    r"\bchannel\s+width\b|"
    r"\bseat\s+cushions?\s+(?:on|in|to)\b|"
    r"\bseat\s+(?:backs?|cushion)\s+on\b|"
    r"\b(?:back|seat)\s+(?:fabric|vinyl|cushion)\b.{0,20}\b(?:on|in)\b",
    re.I,
)

# Bare "change it" and "change it to <specs>" / "redo the drawing with …"
_CHANGE_FOLLOWUP = re.compile(
    r"^\s*(?:you\s+)?(?:can you\s+|could you\s+|please\s+)?"
    r"(?:change|revise|update|fix|edit|redraw|redo)\s+"
    r"(?:it|this|that|the\s+drawing|the\s+layout)\b",
    re.I,
)

_JOB_HINT = re.compile(
    r"\b(?:the\s+)?([A-Za-z][A-Za-z0-9&.'-]{1,40})(?:'s)?\s+job\b|"
    r"\bjob\s+(?:for|on)\s+([A-Za-z][A-Za-z0-9&.'-]{1,40})\b|"
    r"\b(EST-\d{4}-\d+)\b",
    re.I,
)

_INCH_NUM = r"(\d+(?:\s+\d+/\d+)?(?:\.\d+)?)"
_CHANNEL_WIDTH = re.compile(
    r"\bchannel(?:s)?(?:\s+backs?)?(?:\s+width)?(?:\s+(?:at|to|of))?\s+"
    + _INCH_NUM
    + r"\s*(?:\"|in(?:ch(?:es)?)?|wide)?",
    re.I,
)
_CHANNEL_WIDTH_PREFIX = re.compile(
    r"\b" + _INCH_NUM + r"\s*(?:\"|in(?:ch(?:es)?)?)?\s+(?:wide\s+)?channels?\b",
    re.I,
)
_CHANNEL_WIDTH_WIDE = re.compile(
    r"\b(\d+(?:\s+\d+/\d+)?(?:\.\d+)?)\s*(?:\"|in)?\s*wide\b",
    re.I,
)
_BACK_FABRIC = re.compile(
    r"\b(?:seat\s+backs?|channel\s+backs?|backs?)\s+(?:on|in|to)\s+([A-Za-z0-9#/-]+)",
    re.I,
)
_SEAT_FABRIC = re.compile(
    r"\b(?:seat\s+cushions?|seat\s+fabric|seats?)\s+(?:on|in|to)\s+([A-Za-z0-9#/-]+)",
    re.I,
)
_SEAT_FOR = re.compile(
    r"\b(?:use|put)\s+([A-Za-z0-9#/-]+)\s+for\s+(?:the\s+)?(?:seat\s+cushions?|seats?)\b",
    re.I,
)
_BACK_FOR = re.compile(
    r"\b(?:use|put)\s+([A-Za-z0-9#/-]+)\s+for\s+(?:the\s+)?(?:seat\s+backs?|channel\s+backs?|backs?)\b",
    re.I,
)
_SEAT_CODE = re.compile(r"\bseats?\s+(V\d{3}-[A-Za-z0-9]+)\b", re.I)
_BACK_CODE = re.compile(r"\b(?:channel\s+)?backs?\s+(V\d{3}-[A-Za-z0-9]+)\b", re.I)
_SEATS_COLOR = re.compile(
    r"\b(?:with\s+)?(black|cognac|bittersweet|raven|cherrywood)\s+seats?\b",
    re.I,
)
_FABRIC_CODE = re.compile(r"\b(V\d{3}-[A-Za-z0-9]+)\b", re.I)
_DOC_ONLY = re.compile(
    r"\b(?:docs?|documents?|files?|addendum|invoice)\b",
    re.I,
)
_DRAWING_CONTEXT = re.compile(
    r"\b(?:drawing|drawings|layout|layouts|shop drawing|channel back|"
    r"seat back|seat cushion|banquette|bench)\b",
    re.I,
)

# Words that mean "just find the existing PDF", not generate a new one.
_LOOKUP_ONLY = re.compile(
    r"\b(?:show|find|open|pull|where is|share)\b.{0,40}\b"
    r"(?:docs?|documents?|files?|pdfs?|addendum)\b",
    re.I,
)


def _history_blob(history: Any, n: int = 8) -> str:
    parts: list[str] = []
    for item in list(history or [])[-n:]:
        if isinstance(item, dict):
            parts.append(str(item.get("content") or item.get("message") or ""))
        else:
            parts.append(str(getattr(item, "content", "") or ""))
    return "\n".join(parts)


def is_job_drawing_request(text: str | None) -> bool:
    """True for 'give me a drawing of the X job' — generate, do not file-search."""
    raw = (text or "").strip()
    if not raw:
        return False
    if _LOOKUP_ONLY.search(raw) and not _JOB_DRAWING_ASK.search(raw):
        return False
    if _DOC_ONLY.search(raw) and not re.search(r"\b(?:drawing|layout)\b", raw, re.I):
        return False
    if not _JOB_DRAWING_ASK.search(raw):
        return False
    if extract_job_hint(raw) or re.search(r"\b(?:job|estimate|quote|client)\b", raw, re.I):
        return True
    return False


def is_layout_revision_request(text: str | None) -> bool:
    raw = (text or "").strip()
    if not raw:
        return False
    return bool(_LAYOUT_REVISION.search(raw))


def is_drawing_change_followup(text: str | None) -> bool:
    return bool(_CHANGE_FOLLOWUP.search((text or "").strip()))


def history_has_drawing_job_context(history: Any) -> bool:
    blob = _history_blob(history)
    if not blob:
        return False
    if _DRAWING_CONTEXT.search(blob) and (
        is_job_drawing_request(blob) or is_layout_revision_request(blob) or _JOB_HINT.search(blob)
    ):
        return True
    return bool(_DRAWING_CONTEXT.search(blob) and re.search(r"\bjob\b", blob, re.I))


def extract_job_hint(text: str | None) -> Optional[str]:
    raw = (text or "").strip()
    if not raw:
        return None
    match = _JOB_HINT.search(raw)
    if not match:
        return None
    for group in match.groups():
        if group:
            return group.strip().rstrip(".,")
    return None


def _parse_inches(raw: str | None) -> Optional[float]:
    if not raw:
        return None
    text = str(raw).strip()
    mixed = re.match(r"^(\d+)\s+(\d+)\s*/\s*(\d+)$", text)
    if mixed:
        try:
            return float(mixed.group(1)) + float(mixed.group(2)) / float(mixed.group(3))
        except (TypeError, ValueError, ZeroDivisionError):
            return None
    frac = re.match(r"^(\d+)\s*/\s*(\d+)$", text)
    if frac:
        try:
            return float(frac.group(1)) / float(frac.group(2))
        except (TypeError, ValueError, ZeroDivisionError):
            return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def extract_spec_changes(text: str | None) -> dict[str, Any]:
    """Pull channel width and fabric color/code from a revision sentence."""
    raw = (text or "").strip()
    changes: dict[str, Any] = {}
    if not raw:
        return changes
    codes = [m.group(1) for m in _FABRIC_CODE.finditer(raw)]
    if codes:
        changes["fabric_codes"] = codes
    inches = None
    ch = _CHANNEL_WIDTH.search(raw)
    if ch:
        inches = _parse_inches(ch.group(1))
    if inches is None:
        prefixed = _CHANNEL_WIDTH_PREFIX.search(raw)
        if prefixed:
            inches = _parse_inches(prefixed.group(1))
    if inches is None and "wide" in raw.lower() and "channel" in raw.lower():
        wide = _CHANNEL_WIDTH_WIDE.search(raw)
        if wide:
            inches = _parse_inches(wide.group(1))
    if inches is not None:
        changes["channel_width_in"] = inches
    back = _BACK_FABRIC.search(raw) or _BACK_FOR.search(raw) or _BACK_CODE.search(raw)
    if back:
        changes["back_fabric"] = back.group(1).strip().rstrip(".,;")
    seat = (
        _SEAT_FABRIC.search(raw)
        or _SEAT_FOR.search(raw)
        or _SEAT_CODE.search(raw)
        or _SEATS_COLOR.search(raw)
    )
    if seat:
        token = seat.group(1).strip().rstrip(".,;")
        if token.lower() not in {"backs", "back", "channels", "channel"}:
            changes["seat_fabric"] = token
    return changes


def merge_drawing_job_context(message: str | None, history: Any = None) -> dict[str, Any]:
    """Carry prior job + spec into a short follow-up like 'you change it'."""
    current = (message or "").strip()
    prior = _history_blob(history)
    combined = f"{prior}\n{current}".strip()
    spec = extract_spec_changes(prior)
    spec.update(extract_spec_changes(current))
    job = extract_job_hint(current) or extract_job_hint(prior)
    return {
        "job_hint": job,
        "spec_changes": spec,
        "combined_text": combined,
        "message": current,
    }


def is_spec_revision_request(text: str | None) -> bool:
    """True when the sentence carries drawing specs (width / fabric / redo)."""
    raw = (text or "").strip()
    if not raw:
        return False
    if extract_spec_changes(raw):
        return True
    if is_layout_revision_request(raw):
        return True
    if _FABRIC_CODE.search(raw) and re.search(
        r"\b(?:seat|seats|back|backs|cushion|cushions|channel|drawing|layout)\b",
        raw,
        re.I,
    ):
        return True
    return False


def should_route_to_drawing_desk(
    text: str | None,
    history: Any = None,
) -> bool:
    """True when Drawing Studio (forge / Kai) owns the turn."""
    raw = (text or "").strip()
    if not raw:
        return False
    if _LOOKUP_ONLY.search(raw) and not is_job_drawing_request(raw):
        return False
    if is_job_drawing_request(raw):
        return True
    if is_layout_revision_request(raw):
        return True
    has_ctx = history_has_drawing_job_context(history) or (
        is_job_drawing_request(_history_blob(history))
        or is_layout_revision_request(_history_blob(history))
    )
    if is_drawing_change_followup(raw) and has_ctx:
        return True
    if has_ctx and is_spec_revision_request(raw):
        return True
    if has_ctx and re.search(
        r"\b(?:change|revise|update|redo|redraw)\b.{0,40}\b(?:drawing|layout)\b",
        raw,
        re.I,
    ):
        return True
    return False


def drawing_desk_id() -> str:
    return DRAWING_DESK_ID


def force_drawing_desk(title: str | None, description: str | None, chosen: str | None = None) -> Optional[str]:
    """If this is a drawing/layout revision, pin the desk to forge / Kai."""
    blob = f"{title or ''}\n{description or ''}"
    if should_route_to_drawing_desk(blob):
        return DRAWING_DESK_ID
    return (chosen or "").strip() or None
