"""Periodic follow-up sweep for waiting / in_progress / stale todo desk tasks.

Also builds a daily founder digest: desk, task, state, next step.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from .desk_registry import desk_label
from .task_lifecycle import due_for_retry

logger = logging.getLogger("max.desks.sweeper")

STALE_IN_PROGRESS_MINUTES = 20
STALE_WAITING_MINUTES = 60
STALE_TODO_MINUTES = 45


def sweep_once(now: datetime | None = None) -> dict[str, Any]:
    """Inspect open tasks, apply retry-cap on hopeless in_progress, return digest rows."""
    from app.db.database import get_db, dict_rows
    from . import founder_inbox

    now = now or datetime.utcnow()
    now_s = now.strftime("%Y-%m-%d %H:%M:%S")
    founder_inbox.ensure_schema()

    with get_db() as conn:
        rows = dict_rows(conn.execute(
            """SELECT id, title, status, desk, priority, retry_count, max_retries,
                      next_retry_at, updated_at, created_at, result_summary
               FROM tasks
               WHERE status IN ('todo','in_progress','waiting','escalated')
               ORDER BY
                   CASE priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1
                                 WHEN 'normal' THEN 2 ELSE 3 END,
                   created_at ASC
               LIMIT 200"""
        ).fetchall())

    stale_in_progress = []
    stale_waiting = []
    stale_todo = []
    ready_retry = []
    inbox = founder_inbox.list_open(20)

    for r in rows:
        age_min = _age_minutes(r.get("updated_at") or r.get("created_at"), now)
        status = r.get("status")
        if status == "in_progress" and age_min >= STALE_IN_PROGRESS_MINUTES:
            stale_in_progress.append(r)
        elif status == "waiting" and age_min >= STALE_WAITING_MINUTES:
            stale_waiting.append(r)
        elif status == "todo" and age_min >= STALE_TODO_MINUTES:
            nxt = r.get("next_retry_at")
            if nxt and nxt > due_for_retry(now):
                continue
            stale_todo.append(r)
            if (r.get("retry_count") or 0) > 0:
                ready_retry.append(r)

    items = []
    for r in rows:
        items.append(_digest_row(r, now))
    for row in inbox:
        items.append({
            "desk": "founder_inbox",
            "task_id": row.get("id"),
            "title": row.get("title"),
            "state": "inbox",
            "next_step": row.get("reason") or "Assign a desk or handle yourself",
        })

    summary = {
        "swept_at": now_s,
        "open": len(rows),
        "stale_in_progress": len(stale_in_progress),
        "stale_waiting": len(stale_waiting),
        "stale_todo": len(stale_todo),
        "ready_retry": len(ready_retry),
        "founder_inbox": len(inbox),
        "items": items[:40],
    }
    logger.info(
        "Desk sweeper: open=%s stale_ip=%s stale_wait=%s stale_todo=%s inbox=%s",
        summary["open"], summary["stale_in_progress"], summary["stale_waiting"],
        summary["stale_todo"], summary["founder_inbox"],
    )
    return summary


def format_digest(summary: dict[str, Any]) -> str:
    lines = [
        "Daily desk digest",
        f"Open: {summary.get('open', 0)} · "
        f"stale in_progress: {summary.get('stale_in_progress', 0)} · "
        f"waiting: {summary.get('stale_waiting', 0)} · "
        f"inbox: {summary.get('founder_inbox', 0)}",
        "",
    ]
    for it in summary.get("items") or []:
        lines.append(
            f"- [{it.get('desk')}] #{it.get('task_id')} {it.get('title')} "
            f"— {it.get('state')} — next: {it.get('next_step')}"
        )
    if len(lines) == 3:
        lines.append("- All clear. No open desk tasks.")
    return "\n".join(lines)


async def send_daily_digest() -> dict[str, Any]:
    summary = sweep_once()
    text = format_digest(summary)
    try:
        from app.services.max.telegram_bot import telegram_bot
        if telegram_bot and telegram_bot.is_configured:
            await telegram_bot.send_message(f"📋 <b>Desk digest</b>\n{text[:3500]}")
            summary["notified"] = "telegram"
        else:
            summary["notified"] = "skipped"
    except Exception as exc:
        summary["notified"] = f"error: {exc}"
    return summary


def _digest_row(r: dict, now: datetime) -> dict[str, Any]:
    status = r.get("status")
    desk = r.get("desk")
    nxt = {
        "todo": "Worker will pick up when backoff allows",
        "in_progress": "Sweeper watching; timeout hits retry cap then failed",
        "waiting": "Waiting on founder tap or a dependency",
        "escalated": "In founder inbox — assign a desk or decide",
        "failed": "Capped or errored — re-open only on founder ask",
        "done": "Done (reviewed)",
    }.get(status, "Check it")
    return {
        "desk": desk_label(desk) if desk and desk != "unassigned" else (desk or "unassigned"),
        "task_id": r.get("id"),
        "title": r.get("title"),
        "state": status,
        "next_step": nxt,
        "retry_count": r.get("retry_count") or 0,
    }


def _age_minutes(ts: str | None, now: datetime) -> float:
    if not ts:
        return 0
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            then = datetime.strptime(ts[:26], fmt)
            return max(0.0, (now - then).total_seconds() / 60.0)
        except ValueError:
            continue
    return 0
