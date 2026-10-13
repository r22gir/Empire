"""Weekly review and evening shutdown ritual.

Both surfaces cover every life and business area on this edition.
Workroom is one space, not the product. Nothing is sent.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Iterable, Optional

from app.services.organizer.constants import OUTBOUND_POLICY
from app.services.organizer.edition import default_spaces, process_edition
from app.services.organizer.store import load_item, now_iso, new_id


CLOSED = {"done", "cancelled"}
OPENISH = {"open", "planned", "in_progress", "waiting_on", "confirmed", "snoozed"}
MOVE_DESTINATIONS = {"tomorrow", "later", "keep", "drop"}


def _status(it: dict) -> str:
    return str(it.get("status") or "")


def _active(it: dict) -> bool:
    return _status(it) not in CLOSED


def _day_of(it: dict) -> str:
    return (it.get("due_at") or it.get("start_time") or "")[:10]


def _moved_of(it: dict) -> str:
    return (it.get("last_moved_at") or it.get("updated_at") or it.get("created_at") or "")[:10]


def _space_of(it: dict) -> str:
    return str(it.get("space_id") or "personal")


def _by_space(items: Iterable[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for it in items:
        out.setdefault(_space_of(it), []).append(it)
    return out


def _space_counts(items: Iterable[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for it in items:
        slug = _space_of(it)
        counts[slug] = counts.get(slug, 0) + 1
    return counts


def _area_catalog() -> list[dict]:
    return [
        {"slug": s["slug"], "label": s["label"], "kind": s.get("kind"), "icon": s.get("icon")}
        for s in default_spaces()
    ]


def weekly_review(items: list[dict], *, today: str | None = None) -> dict:
    today = today or date.today().isoformat()
    start = date.fromisoformat(today)
    week_end = (start + timedelta(days=7)).isoformat()
    week_start = (start - timedelta(days=start.weekday())).isoformat()
    stuck_before = (start - timedelta(days=7)).isoformat()
    slipped, stuck, next_week, wins = [], [], [], []
    for it in items:
        status = _status(it)
        due = _day_of(it)
        moved = _moved_of(it)
        if status == "done":
            if moved and week_start <= moved <= today:
                wins.append(it)
            continue
        if status == "cancelled":
            continue
        if due and due < today:
            slipped.append(it)
        elif due and today < due <= week_end:
            next_week.append(it)
        if moved and moved <= stuck_before:
            stuck.append(it)
    areas = sorted({_space_of(it) for it in items if _space_of(it)})
    return {
        "date": today,
        "horizon": week_end,
        "week_start": week_start,
        "slipped": slipped,
        "stuck": stuck,
        "next_week": next_week,
        "wins": wins,
        "completed": wins,
        "by_space": {
            "slipped": _by_space(slipped),
            "stuck": _by_space(stuck),
            "next_week": _by_space(next_week),
            "wins": _by_space(wins),
        },
        "space_counts": {
            "slipped": _space_counts(slipped),
            "stuck": _space_counts(stuck),
            "next_week": _space_counts(next_week),
            "wins": _space_counts(wins),
        },
        "areas": areas,
        "area_catalog": _area_catalog(),
        "counts": {
            "slipped": len(slipped),
            "stuck": len(stuck),
            "next_week": len(next_week),
            "wins": len(wins),
            "areas": len(areas),
        },
        "cross_area": True,
        "workroom_only": False,
        "sent": False,
        "outbound_policy": OUTBOUND_POLICY,
    }


def evening_shutdown(items: list[dict], *, today: str | None = None) -> dict:
    """Review today, list unfinished across every area, preview tomorrow."""
    today = today or date.today().isoformat()
    tomorrow = (date.fromisoformat(today) + timedelta(days=1)).isoformat()
    completed, unfinished, tomorrow_items, undated = [], [], [], []
    for it in items:
        status = _status(it)
        due = _day_of(it)
        moved = _moved_of(it)
        if status == "done" and (moved == today or due == today):
            completed.append(it)
            continue
        if status == "cancelled":
            continue
        if due == tomorrow:
            tomorrow_items.append(it)
            continue
        if due == today or (due and due < today):
            unfinished.append(it)
        elif not due and status in OPENISH:
            undated.append(it)
    areas = sorted({
        _space_of(it)
        for it in (*completed, *unfinished, *tomorrow_items, *undated)
        if _space_of(it)
    })
    return {
        "date": today,
        "tomorrow": tomorrow,
        "steps": ("review", "move", "plan"),
        "completed": completed,
        "unfinished": unfinished,
        "undated": undated,
        "tomorrow_preview": tomorrow_items,
        "by_space": {
            "completed": _by_space(completed),
            "unfinished": _by_space(unfinished),
            "tomorrow": _by_space(tomorrow_items),
            "undated": _by_space(undated),
        },
        "space_counts": {
            "completed": _space_counts(completed),
            "unfinished": _space_counts(unfinished),
            "tomorrow": _space_counts(tomorrow_items),
        },
        "areas": areas,
        "area_catalog": _area_catalog(),
        "counts": {
            "completed": len(completed),
            "unfinished": len(unfinished),
            "tomorrow": len(tomorrow_items),
            "undated": len(undated),
            "areas": len(areas),
        },
        "cross_area": True,
        "workroom_only": False,
        "sent": False,
        "wrote_live": False,
        "outbound_policy": OUTBOUND_POLICY,
    }


def resolve_shutdown_due(destination: str, *, today: str, later: str | None = None) -> Optional[str]:
    dest = (destination or "").strip().lower()
    if dest == "tomorrow":
        return (date.fromisoformat(today) + timedelta(days=1)).isoformat() + "T09:00:00"
    if dest == "later":
        day = (later or "")[:10]
        if not day:
            day = (date.fromisoformat(today) + timedelta(days=2)).isoformat()
        return f"{day}T09:00:00"
    return None


def apply_shutdown_moves(
    items: list[dict],
    moves: list[dict],
    *,
    today: str | None = None,
) -> list[dict]:
    """Pure apply for tests. Does not touch a database."""
    today = today or date.today().isoformat()
    by_id = {str(it.get("id")): dict(it) for it in items}
    for move in moves or []:
        item_id = str(move.get("id") or "")
        dest = str(move.get("destination") or "keep").lower()
        if dest not in MOVE_DESTINATIONS or item_id not in by_id:
            continue
        row = by_id[item_id]
        if dest == "keep":
            continue
        if dest == "drop":
            row["status"] = "cancelled"
            continue
        due = resolve_shutdown_due(dest, today=today, later=move.get("due_at") or move.get("later"))
        if due:
            row["due_at"] = due
            if row.get("start_time"):
                row["start_time"] = due
            row["last_moved_at"] = today
    return list(by_id.values())


def persist_shutdown(conn, pack: dict, moves: list[dict], *, notes: str = "") -> dict:
    """Write item moves for this edition only. Never sends. Never touches quotes."""
    today = pack.get("date") or date.today().isoformat()
    applied = []
    skipped = []
    for move in moves or []:
        item_id = str(move.get("id") or "")
        dest = str(move.get("destination") or "keep").lower()
        if dest not in MOVE_DESTINATIONS:
            skipped.append({"id": item_id, "reason": "bad_destination"})
            continue
        item = load_item(conn, item_id) if item_id else None
        if not item:
            skipped.append({"id": item_id, "reason": "not_found"})
            continue
        if dest == "keep":
            applied.append({"id": item_id, "destination": dest, "item": item})
            continue
        fields = ["updated_at = ?", "last_moved_at = ?"]
        params: list = [now_iso(), now_iso()]
        if dest == "drop":
            fields.append("status = ?")
            params.append("cancelled")
        else:
            due = resolve_shutdown_due(dest, today=today, later=move.get("due_at") or move.get("later"))
            if due:
                fields.append("due_at = ?")
                params.append(due)
                if item.get("start_time"):
                    fields.append("start_time = ?")
                    params.append(due)
        params.append(item_id)
        conn.execute(
            f"UPDATE organizer_items SET {', '.join(fields)} WHERE id = ?",
            params,
        )
        applied.append({"id": item_id, "destination": dest, "item": load_item(conn, item_id)})

    ritual_id = new_id()
    conn.execute(
        """
        INSERT INTO organizer_rituals
            (id, edition, kind, ritual_date, notes, payload_json, sent, created_at)
        VALUES (?, ?, 'shutdown', ?, ?, ?, 0, ?)
        """,
        (
            ritual_id,
            process_edition(),
            today,
            notes or "",
            json.dumps({
                "moves": [{"id": m.get("id"), "destination": m.get("destination")} for m in moves or []],
                "counts": pack.get("counts"),
                "areas": pack.get("areas"),
            }),
            now_iso(),
        ),
    )
    return {
        "ritual_id": ritual_id,
        "applied": applied,
        "skipped": skipped,
        "sent": False,
        "wrote_live": False,
        "wrote_quotes": False,
        "outbound_policy": OUTBOUND_POLICY,
    }
