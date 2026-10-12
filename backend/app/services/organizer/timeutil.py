"""ISO datetime helpers for the Organizer (naive local / America/New_York context)."""

from datetime import datetime, timedelta
from typing import Optional


def parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    raw = raw.replace("Z", "")
    if " " in raw and "T" not in raw:
        raw = raw.replace(" ", "T", 1)
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(raw[:26], fmt) if fmt.endswith("%f") else datetime.strptime(raw[:19] if "T" in raw and fmt != "%Y-%m-%d" else raw[:10], fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def to_iso(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    if dt.second or dt.microsecond:
        return dt.strftime("%Y-%m-%dT%H:%M:%S")
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def event_window(start_time: Optional[str], end_time: Optional[str], default_minutes: int = 60):
    start = parse_dt(start_time)
    if not start:
        return None, None
    end = parse_dt(end_time)
    if not end or end <= start:
        end = start + timedelta(minutes=default_minutes)
    return start, end


def ranges_overlap(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end


def gap_minutes(first_end: datetime, second_start: datetime) -> float:
    return (second_start - first_end).total_seconds() / 60.0
