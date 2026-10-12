"""Weekly review: slipped, stuck (no movement 7+ days), next week."""

from __future__ import annotations

from datetime import date, timedelta


def weekly_review(items: list[dict], *, today: str | None = None) -> dict:
    today = today or date.today().isoformat()
    start = date.fromisoformat(today)
    week_end = (start + timedelta(days=7)).isoformat()
    stuck_before = (start - timedelta(days=7)).isoformat()
    slipped, stuck, next_week = [], [], []
    for it in items:
        status = str(it.get("status") or "")
        if status in {"done", "cancelled"}:
            continue
        due = (it.get("due_at") or it.get("start_time") or "")[:10]
        moved = (it.get("last_moved_at") or it.get("updated_at") or it.get("created_at") or "")[:10]
        if due and due < today:
            slipped.append(it)
        elif due and today < due <= week_end:
            next_week.append(it)
        if moved and moved <= stuck_before:
            stuck.append(it)
    return {
        "date": today,
        "horizon": week_end,
        "slipped": slipped,
        "stuck": stuck,
        "next_week": next_week,
        "counts": {"slipped": len(slipped), "stuck": len(stuck), "next_week": len(next_week)},
    }
