"""Morning proposed day: due items, who is free, best order of field stops."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Iterable

from app.services.organizer.constants import DEFAULT_EVENT_MINUTES
from app.services.organizer.timeutil import event_window, parse_dt, ranges_overlap


FIELD_KINDS = {"install", "pickup", "drop_off", "delivery", "measure", "fitting", "fabric_pickup"}
PLAN_KINDS = FIELD_KINDS | {"material_order", "followup", "todo", "deadline", "call", "reminder"}
SHOP_START = "08:30"
TRAVEL_PAD = 25


def _today() -> date:
    return date.today()


def resource_free_windows(resources: list[dict], events: list[dict], day: str) -> list[dict]:
    start = datetime.fromisoformat(f"{day}T07:00:00")
    end = datetime.fromisoformat(f"{day}T19:00:00")
    out = []
    for res in resources:
        rid = res.get("id")
        booked = []
        for ev in events:
            ids = ev.get("assigned_resource_ids") or []
            if rid not in ids:
                continue
            a, b = event_window(ev.get("start_time"), ev.get("end_time"))
            if a and b:
                booked.append((a, b, ev.get("title")))
        booked.sort()
        gaps = []
        cursor = start
        for a, b, title in booked:
            if a > cursor:
                gaps.append({"from": cursor.isoformat(timespec="seconds"), "to": a.isoformat(timespec="seconds")})
            if b > cursor:
                cursor = b
        if cursor < end:
            gaps.append({"from": cursor.isoformat(timespec="seconds"), "to": end.isoformat(timespec="seconds")})
        out.append({
            "resource": res,
            "free": bool(gaps),
            "free_windows": gaps,
            "booked_count": len(booked),
        })
    return out


def order_field_stops(items: Iterable[dict]) -> list[dict]:
    """Order installs/pickups: timed first, then by address to keep travel short."""
    field = [i for i in items if (i.get("kind") or i.get("type")) in FIELD_KINDS]
    timed = sorted(
        [i for i in field if i.get("start_time")],
        key=lambda i: i.get("start_time") or "",
    )
    untimed = [i for i in field if not i.get("start_time")]
    # Cluster untimed by address so the same street stays together.
    untimed.sort(key=lambda i: (i.get("location_address") or "", i.get("title") or ""))
    return timed + untimed


def propose_day(board: list[dict], resources: list[dict], *, day: str | None = None) -> dict:
    day = day or _today().isoformat()
    due = []
    today_items = []
    for row in board:
        if str(row.get("status") or "") in ("done", "cancelled"):
            continue
        when = (row.get("due_at") or row.get("start_time") or "")[:10]
        kind = row.get("kind") or row.get("type")
        if when and when < day:
            due.append({**row, "bucket": "overdue"})
        elif when == day or (not when and kind in PLAN_KINDS):
            today_items.append({**row, "bucket": "today"})
    field = order_field_stops(today_items + [d for d in due if (d.get("kind") in FIELD_KINDS)])
    extras = [
        i for i in (today_items + due)
        if (i.get("kind") or i.get("type")) in PLAN_KINDS and i.get("id") not in {s.get("id") for s in field}
    ]
    extras.sort(key=lambda i: (0 if (i.get("kind") in {"material_order", "followup"}) else 1, i.get("title") or ""))
    stops = field + extras
    cursor = datetime.fromisoformat(f"{day}T{SHOP_START}:00")
    suggested = []
    for stop in stops:
        start, end = event_window(stop.get("start_time"), stop.get("end_time"), DEFAULT_EVENT_MINUTES)
        if start and start.date().isoformat() == day:
            suggested.append({
                **stop,
                "suggested_start": start.isoformat(timespec="seconds"),
                "suggested_end": end.isoformat(timespec="seconds") if end else None,
                "kept_existing_time": True,
            })
            cursor = (end or start) + timedelta(minutes=TRAVEL_PAD)
            continue
        dur = DEFAULT_EVENT_MINUTES
        suggested.append({
            **stop,
            "suggested_start": cursor.isoformat(timespec="seconds"),
            "suggested_end": (cursor + timedelta(minutes=dur)).isoformat(timespec="seconds"),
            "kept_existing_time": False,
        })
        cursor = cursor + timedelta(minutes=dur + TRAVEL_PAD)
    who = resource_free_windows(resources, [i for i in board if (i.get("start_time") or "")[:10] == day], day)
    return {
        "date": day,
        "headline": f"{len(due)} overdue · {len(today_items)} on today · {len(stops)} field stops",
        "overdue": due,
        "today": today_items,
        "proposed_order": suggested,
        "who_is_free": who,
        "requires_approval": True,
        "approved": False,
        "outbound_blocked": True,
        "note": "Draft plan only. One tap approves the order. Nothing is sent to a customer.",
    }
