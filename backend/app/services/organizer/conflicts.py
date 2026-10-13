"""Conflict detection for Organizer calendar items. Never silent-overwrite."""

from __future__ import annotations

from typing import Any, Iterable, Optional

from app.services.organizer.constants import DEFAULT_TRAVEL_GAP_MINUTES
from app.services.organizer.timeutil import event_window, gap_minutes, ranges_overlap


def _norm_addr(value: Optional[str]) -> str:
    return " ".join((value or "").lower().split())


def detect_conflicts(
    candidate: dict,
    existing: Iterable[dict],
    *,
    travel_gap_minutes: int = DEFAULT_TRAVEL_GAP_MINUTES,
) -> list[dict]:
    """Return a list of conflict objects. Empty means the write is clean.

    candidate / existing items use:
      id, start_time, end_time, title, location_address,
      assigned_resource_ids (list[str]), assigned_names (optional list),
      status
    """
    cand_start, cand_end = event_window(candidate.get("start_time"), candidate.get("end_time"))
    if not cand_start:
        return []

    cand_id = str(candidate.get("id") or "")
    cand_people = {str(p) for p in (candidate.get("assigned_resource_ids") or []) if p}
    cand_addr = _norm_addr(candidate.get("location_address"))
    travel_needed = int(candidate.get("travel_minutes") or travel_gap_minutes)

    conflicts: list[dict] = []
    for other in existing:
        if str(other.get("status") or "") == "cancelled":
            continue
        other_id = str(other.get("id") or "")
        if other_id and cand_id and other_id == cand_id:
            continue
        o_start, o_end = event_window(other.get("start_time"), other.get("end_time"))
        if not o_start:
            continue

        other_people = {str(p) for p in (other.get("assigned_resource_ids") or []) if p}
        shared = sorted(cand_people & other_people)
        overlapping = ranges_overlap(cand_start, cand_end, o_start, o_end)
        names = other.get("assigned_names") or []

        if overlapping:
            if shared:
                conflicts.append(
                    {
                        "code": "double_booked_person",
                        "severity": "error",
                        "message": (
                            f"{_who(shared, names)} is already booked for "
                            f"'{other.get('title') or 'another event'}' "
                            f"from {_fmt(o_start)} to {_fmt(o_end)}."
                        ),
                        "other_id": other_id,
                        "resource_ids": shared,
                    }
                )
            else:
                conflicts.append(
                    {
                        "code": "overlapping_event",
                        "severity": "warning",
                        "message": (
                            f"Overlaps '{other.get('title') or 'another event'}' "
                            f"({_fmt(o_start)}–{_fmt(o_end)})."
                        ),
                        "other_id": other_id,
                    }
                )
            continue

        if not shared:
            continue

        # Travel gap: adjacent events for the same person at different places.
        other_addr = _norm_addr(other.get("location_address"))
        if not cand_addr or not other_addr or cand_addr == other_addr:
            continue

        if cand_end <= o_start:
            gap = gap_minutes(cand_end, o_start)
        elif o_end <= cand_start:
            gap = gap_minutes(o_end, cand_start)
        else:
            continue
        other_travel = int(other.get("travel_minutes") or travel_gap_minutes)
        needed = max(travel_needed, other_travel)
        if 0 <= gap < needed:
            conflicts.append(
                {
                    "code": "travel_gap",
                    "severity": "warning",
                    "message": (
                        f"{_who(shared, names)} has only {int(gap)} min between "
                        f"'{other.get('title') or 'another event'}' and this item "
                        f"(need {needed} min for travel)."
                    ),
                    "other_id": other_id,
                    "resource_ids": shared,
                    "gap_minutes": int(gap),
                    "needed_minutes": needed,
                }
            )
    return conflicts


def summarize_conflicts(conflicts: list[dict]) -> str:
    if not conflicts:
        return ""
    return " ".join(c.get("message") or c.get("code") or "conflict" for c in conflicts)


def has_blocking_conflict(conflicts: list[dict]) -> bool:
    return any(c.get("severity") == "error" or c.get("code") == "double_booked_person" for c in conflicts)


def _who(ids: list[str], names: Any) -> str:
    if isinstance(names, list) and names:
        return ", ".join(str(n) for n in names if n)
    if len(ids) == 1:
        return "This person"
    return "Assigned people"


def _fmt(dt) -> str:
    return dt.strftime("%Y-%m-%d %H:%M")
