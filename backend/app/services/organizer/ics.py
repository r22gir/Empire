"""ICS export for Organizer calendar items (RFC 5545 subset)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, Optional

from app.services.organizer.timeutil import event_window, parse_dt


def _fold(line: str) -> str:
    out = []
    while len(line) > 73:
        out.append(line[:73])
        line = " " + line[73:]
    out.append(line)
    return "\r\n".join(out)


def _esc(value: Optional[str]) -> str:
    raw = (value or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
    return raw.replace("\n", "\\n")


def _ics_dt(value: Optional[str]) -> Optional[str]:
    dt = parse_dt(value)
    if not dt:
        return None
    return dt.strftime("%Y%m%dT%H%M%S")


def event_to_vevent(item: dict) -> str:
    start, end = event_window(item.get("start_time") or item.get("due_at"), item.get("end_time"))
    if not start:
        return ""
    uid = f"{item.get('id') or 'item'}@empire-organizer"
    dtstamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART:{start.strftime('%Y%m%dT%H%M%S')}",
        f"DTEND:{(end or start + timedelta(hours=1)).strftime('%Y%m%dT%H%M%S')}",
        _fold(f"SUMMARY:{_esc(item.get('title') or 'Empire item')}"),
    ]
    loc = item.get("location_address")
    if loc:
        lines.append(_fold(f"LOCATION:{_esc(loc)}"))
    desc_bits = [
        item.get("notes") or "",
        f"Type: {item.get('kind') or item.get('type') or ''}",
        f"Job: {item.get('job_title') or item.get('job_id') or ''}",
        f"Phone: {item.get('phone') or ''}",
        "Draft reminders are never sent to customers without founder approval.",
    ]
    lines.append(_fold("DESCRIPTION:" + _esc(" | ".join(b for b in desc_bits if b and b.split(": ")[-1]))))
    if item.get("status") == "cancelled":
        lines.append("STATUS:CANCELLED")
    lines.append("END:VEVENT")
    return "\r\n".join(lines)


def build_calendar(items: Iterable[dict], *, calendar_name: str = "Empire Organizer") -> str:
    vevents = [event_to_vevent(it) for it in items]
    body = "\r\n".join(v for v in vevents if v)
    return (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//Empire//Organizer//EN\r\n"
        "CALSCALE:GREGORIAN\r\n"
        "METHOD:PUBLISH\r\n"
        f"X-WR-CALNAME:{_esc(calendar_name)}\r\n"
        f"{body}\r\n"
        "END:VCALENDAR\r\n"
    )
