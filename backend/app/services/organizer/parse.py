"""Natural-language quick-add / Max draft parser for the Organizer."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Optional

from app.services.organizer.constants import DEFAULT_EVENT_MINUTES, FOLLOWUP_KINDS, ITEM_KINDS

_WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

_KIND_KEYWORDS = [
    ("job_milestone", ("milestone", "job milestone")),
    ("material_order", ("material order", "fabric order", "order fabric", "eta", "ordered")),
    ("followup", ("follow up", "follow-up", "followup")),
    ("reminder", ("remind", "reminder")),
    ("deadline", ("deadline", "due", "must be done")),
    ("fitting", ("fitting",)),
    ("measure", ("measure", "measurement", "site visit")),
    ("install", ("install", "installation")),
    ("pickup", ("pick up", "pickup", "pick-up")),
    ("drop_off", ("drop off", "drop-off", "dropoff")),
    ("delivery", ("deliver", "delivery")),
    ("meeting", ("meeting", "meet with")),
    ("call", ("call", "phone", "ring")),
    ("appointment", ("appointment", "appt")),
    ("todo", ("todo", "to-do", "to do", "task")),
]

_FOLLOWUP_KEYWORDS = [
    ("deposit", ("deposit",)),
    ("payment", ("payment", "invoice", "balance", "paid")),
    ("quote", ("quote", "estimate")),
]


def next_weekday(from_day: date, weekday: int, *, next_week_word: bool = False) -> date:
    delta = (weekday - from_day.weekday()) % 7
    if delta == 0:
        delta = 7 if next_week_word or True else 0
        # "Friday" from a Friday means this Friday only if we keep 0;
        # Rafael's phrasing is usually the upcoming one. Same-day stays today.
        if next_week_word:
            delta = 7
        else:
            delta = 0
    return from_day + timedelta(days=delta if delta or not next_week_word else 0)


def resolve_date_phrase(text: str, today: Optional[date] = None) -> Optional[date]:
    today = today or date.today()
    raw = text.lower()
    if re.search(r"\btoday\b", raw):
        return today
    if re.search(r"\btomorrow\b", raw):
        return today + timedelta(days=1)
    iso = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", raw)
    if iso:
        return date.fromisoformat(iso.group(1))
    us = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", raw)
    if us:
        month, day = int(us.group(1)), int(us.group(2))
        year = int(us.group(3)) if us.group(3) else today.year
        if year < 100:
            year += 2000
        try:
            return date(year, month, day)
        except ValueError:
            return None
    months = {
        "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
        "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
        "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
        "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
    }
    named = re.search(
        r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
        r"jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|"
        r"dec(?:ember)?)\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s*(\d{4}))?\b",
        raw,
    )
    if named:
        month = months[named.group(1)[:3] if named.group(1)[:3] != "sep" else "sep"]
        if named.group(1).startswith("sept"):
            month = 9
        day = int(named.group(2))
        year = int(named.group(3)) if named.group(3) else today.year
        try:
            return date(year, month, day)
        except ValueError:
            return None
    wd = re.search(
        r"\b(next\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        raw,
    )
    if wd:
        return _upcoming_weekday(today, _WEEKDAYS[wd.group(2)], bool(wd.group(1)))
    return None


def _upcoming_weekday(today: date, weekday: int, force_next: bool) -> date:
    delta = (weekday - today.weekday()) % 7
    if force_next and delta == 0:
        delta = 7
    # If it's already past that weekday this week, jump forward.
    if delta == 0 and not force_next:
        return today
    if delta == 0:
        delta = 7
    return today + timedelta(days=delta)


def resolve_time_phrase(text: str) -> Optional[str]:
    raw = text.lower()
    if re.search(r"\bnoon\b", raw):
        return "12:00"
    if re.search(r"\bmidnight\b", raw):
        return "00:00"
    if re.search(r"\bmorning\b", raw) and not re.search(r"\d", raw):
        return "09:00"
    if re.search(r"\bafternoon\b", raw) and not re.search(r"\d", raw):
        return "14:00"
    m = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", raw)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2) or 0)
        ap = m.group(3)
        if ap == "pm" and hour < 12:
            hour += 12
        if ap == "am" and hour == 12:
            hour = 0
        return f"{hour:02d}:{minute:02d}"
    m24 = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", raw)
    if m24:
        return f"{int(m24.group(1)):02d}:{m24.group(2)}"
    return None


def infer_kind(text: str) -> str:
    raw = text.lower()
    for kind, keys in _KIND_KEYWORDS:
        if any(k in raw for k in keys):
            return kind
    return "appointment"


def infer_followup_kind(text: str) -> Optional[str]:
    raw = text.lower()
    for kind, keys in _FOLLOWUP_KEYWORDS:
        if any(k in raw for k in keys):
            return kind
    return None


def extract_subject_name(text: str) -> Optional[str]:
    """Pull a likely person/job name: 'the Marley job', 'call Marley', 'with Whittington'."""
    patterns = [
        r"\b(?:the\s+)?([A-Z][\w'&.-]+(?:\s+[A-Z][\w'&.-]+){0,3})\s+job\b",
        r"\b([A-Z][\w'&.-]+)'s\s+(?:install|appointment|measure|pickup|fitting|delivery|call|visit|todo)\b",
        r"\b(?:move|reschedule)\s+([A-Z][\w'&.-]+)",
        r"\b(?:for|with|at)\s+(?:the\s+)?([A-Z][\w'&.-]+(?:\s+[A-Z][\w'&.-]+){0,3})\b",
        r"\b(?:call|phone|meet|text)\s+([A-Z][\w'&.-]+(?:\s+[A-Z][\w'&.-]+){0,2})\b",
    ]
    skip = {"friday", "monday", "tuesday", "wednesday", "thursday", "saturday", "sunday",
            "today", "tomorrow", "install", "pickup", "the"}
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            name = re.sub(r"'s$", "", m.group(1).strip(" .,"), flags=re.I)
            if name.lower() not in skip:
                return name
    # lowercase fallback: 'the marley job'
    m = re.search(r"\bthe\s+([a-z0-9'&.-]+(?:\s+[a-z0-9'&.-]+){0,3})\s+job\b", text, re.I)
    if m:
        return m.group(1).strip()
    m = re.search(r"\bcall\s+([a-z0-9'&.-]+)\b", text, re.I)
    if m and m.group(1).lower() not in _WEEKDAYS:
        return m.group(1)
    return None


def parse_quick_add(text: str, *, today: Optional[date] = None) -> dict:
    """Parse a typed/voice line into a draft organizer item. Does not write."""
    today = today or date.today()
    cleaned = (text or "").strip()
    kind = infer_kind(cleaned)
    followup = infer_followup_kind(cleaned) if kind in {"followup", "reminder", "call"} else None
    if followup and kind == "appointment":
        kind = "followup"
    if followup and kind == "call":
        # keep call, but tag the follow-up reason
        pass
    day = resolve_date_phrase(cleaned, today)
    clock = resolve_time_phrase(cleaned)
    start_time = None
    end_time = None
    due_at = None
    if day and clock:
        start_time = f"{day.isoformat()}T{clock}:00"
        end_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S") + timedelta(minutes=DEFAULT_EVENT_MINUTES)
        end_time = end_dt.strftime("%Y-%m-%dT%H:%M:%S")
    elif day and kind in {"todo", "reminder", "deadline", "followup", "material_order"}:
        due_at = f"{day.isoformat()}T17:00:00"
    elif day:
        start_time = f"{day.isoformat()}T09:00:00"
        end_time = f"{day.isoformat()}T10:00:00"
    elif clock:
        start_time = f"{today.isoformat()}T{clock}:00"
        end_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S") + timedelta(minutes=DEFAULT_EVENT_MINUTES)
        end_time = end_dt.strftime("%Y-%m-%dT%H:%M:%S")

    subject = extract_subject_name(cleaned)
    title = cleaned
    if len(title) > 80:
        title = title[:77] + "..."

    timed = bool(start_time)
    return {
        "kind": kind if kind in ITEM_KINDS else "appointment",
        "title": title,
        "start_time": start_time,
        "end_time": end_time,
        "due_at": due_at,
        "subject_name": subject,
        "followup_kind": followup if followup in FOLLOWUP_KINDS else None,
        "requires_confirmation": True,
        "is_draft_only": True,
        "timed": timed,
        "original_text": cleaned,
        "notes": f"Draft from quick-add: {cleaned}",
        "outbound_blocked": True,
        "reminder_only": kind == "reminder",
    }


def parse_quick_add_lines(text: str, *, today: Optional[date] = None) -> list[dict]:
    today = today or date.today()
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    if not lines:
        return []
    drafts = [parse_quick_add(ln, today=today) for ln in lines]
    return [d for d in drafts if d.get("original_text")]
