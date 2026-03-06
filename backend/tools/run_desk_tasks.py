"""
AI Desk Task Worker — picks up 'todo' tasks from the DB, executes them via AI (Grok/Claude),
writes results back, and sends summaries to Telegram.

Usage:
  cd ~/empire-repo/backend && ./venv/bin/python tools/run_desk_tasks.py
  ./venv/bin/python tools/run_desk_tasks.py --desk forge --limit 2
  ./venv/bin/python tools/run_desk_tasks.py --dry-run
"""
import argparse
import asyncio
import json
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import get_db, dict_rows
from app.db.init_db import init_database

DESK_EMOJIS = {
    "forge": "\u2702\ufe0f", "market": "\U0001f4e6", "marketing": "\U0001f4f1",
    "support": "\U0001f6e0\ufe0f", "sales": "\U0001f4bc", "finance": "\U0001f4b0",
    "clients": "\U0001f465", "contractors": "\U0001f527", "it": "\U0001f5a5\ufe0f",
    "website": "\U0001f310", "legal": "\u2696\ufe0f", "lab": "\U0001f9ea",
}


def get_pending_tasks(desk: str | None = None, limit: int | None = None) -> list[dict]:
    """Fetch todo tasks from the DB, ordered by priority then creation date."""
    with get_db() as conn:
        sql = """
            SELECT id, title, description, priority, desk, tags, metadata
            FROM tasks
            WHERE status = 'todo'
        """
        params = []
        if desk:
            sql += " AND desk = ?"
            params.append(desk)
        sql += " ORDER BY CASE priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 WHEN 'low' THEN 3 END, created_at ASC"
        if limit:
            sql += f" LIMIT {int(limit)}"
        rows = conn.execute(sql, params).fetchall()
        return dict_rows(rows)


async def execute_task(task: dict) -> tuple[bool, str]:
    """Send a task to AI for execution and return (success, result_text)."""
    from app.services.max.ai_router import ai_router, AIMessage

    # Load desk-specific system prompt
    try:
        from app.services.max.desk_prompt import get_desk_system_prompt
        system_prompt = get_desk_system_prompt(task["desk"])
    except Exception:
        system_prompt = (
            f"You are MAX running the {task['desk']} desk for Empire, "
            f"a custom drapery and upholstery business in Washington DC. "
            f"Complete the assigned task thoroughly and provide actionable results."
        )

    user_message = (
        f"Complete this research task for the {task['desk']} desk.\n\n"
        f"**Task:** {task['title']}\n\n"
        f"**Details:** {task['description']}\n\n"
        f"**Priority:** {task['priority']}\n\n"
        f"Provide thorough, specific, actionable results. "
        f"Include real data, numbers, and recommendations where applicable. "
        f"Format your response with clear headings and bullet points."
    )

    try:
        response = await ai_router.chat(
            messages=[AIMessage(role="user", content=user_message)],
            desk=task["desk"],
            system_prompt=system_prompt,
        )
        return True, response.content
    except Exception as e:
        return False, str(e)


def update_task_done(task_id: str, result: str):
    """Mark task as done and log the AI result as activity."""
    with get_db() as conn:
        conn.execute(
            "UPDATE tasks SET status = 'done', updated_at = datetime('now'), completed_at = datetime('now') WHERE id = ?",
            (task_id,),
        )
        conn.execute(
            "INSERT INTO task_activity (task_id, actor, action, detail) VALUES (?, 'MAX', 'completed', ?)",
            (task_id, result[:5000]),
        )
        conn.commit()


def update_task_failed(task_id: str, error: str):
    """Reset task back to todo with error logged."""
    with get_db() as conn:
        conn.execute(
            "UPDATE tasks SET status = 'todo', updated_at = datetime('now') WHERE id = ?",
            (task_id,),
        )
        conn.execute(
            "INSERT INTO task_activity (task_id, actor, action, detail) VALUES (?, 'MAX', 'failed', ?)",
            (task_id, f"AI execution failed: {error}"),
        )
        conn.commit()


def mark_in_progress(task_id: str):
    """Set task to in_progress while AI is working."""
    with get_db() as conn:
        conn.execute(
            "UPDATE tasks SET status = 'in_progress', updated_at = datetime('now') WHERE id = ?",
            (task_id,),
        )
        conn.commit()


async def send_telegram(message: str):
    """Send a summary message via Telegram."""
    try:
        from app.services.max.telegram_bot import TelegramBot
        bot = TelegramBot()
        if bot.is_configured:
            await bot.send_message(message)
    except Exception as e:
        print(f"  Telegram send failed: {e}")


async def run(desk: str | None, limit: int | None, dry_run: bool):
    init_database()
    tasks = get_pending_tasks(desk, limit)

    if not tasks:
        print("No pending tasks found.")
        return

    print(f"Found {len(tasks)} pending task(s).\n")

    if dry_run:
        for t in tasks:
            emoji = DESK_EMOJIS.get(t["desk"], "\U0001f4cb")
            print(f"  {emoji} [{t['desk']}] [{t['priority']}] {t['title']}")
        print(f"\nDry run — {len(tasks)} tasks would be processed.")
        return

    completed = 0
    failed = 0
    results_summary = []

    for i, task in enumerate(tasks, 1):
        emoji = DESK_EMOJIS.get(task["desk"], "\U0001f4cb")
        print(f"[{i}/{len(tasks)}] {emoji} {task['desk']}: {task['title']}")

        # Mark in progress
        mark_in_progress(task["id"])

        # Execute via AI
        start = time.time()
        success, result = await execute_task(task)
        elapsed = time.time() - start

        if success:
            update_task_done(task["id"], result)
            completed += 1
            preview = result[:200].replace("\n", " ")
            print(f"  Done ({elapsed:.1f}s) — {preview}...")
            results_summary.append(f"{emoji} <b>{task['title']}</b>\n{result[:500]}")

            # Send individual Telegram update
            tg_msg = (
                f"{emoji} <b>Task Completed: {task['desk'].title()} Desk</b>\n\n"
                f"<b>{task['title']}</b>\n\n"
                f"{result[:800]}"
            )
            await send_telegram(tg_msg)
        else:
            update_task_failed(task["id"], result)
            failed += 1
            print(f"  FAILED ({elapsed:.1f}s) — {result[:100]}")

        # Brief pause between tasks to avoid rate limits
        if i < len(tasks):
            await asyncio.sleep(2)

    # Final summary
    print(f"\n{'=' * 60}")
    print(f"Completed: {completed} | Failed: {failed} | Total: {len(tasks)}")

    if completed > 0:
        desks_done = set(t["desk"] for t in tasks[:completed])
        summary_msg = (
            f"\U0001f4cb <b>Desk Task Report</b>\n\n"
            f"\u2705 {completed}/{len(tasks)} tasks completed across {len(desks_done)} desk(s)\n"
            f"{('\u274c ' + str(failed) + ' failed') if failed else ''}"
        )
        await send_telegram(summary_msg)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run AI desk tasks")
    parser.add_argument("--desk", help="Only run tasks for this desk (e.g., forge)")
    parser.add_argument("--limit", type=int, help="Max tasks to process")
    parser.add_argument("--dry-run", action="store_true", help="Show tasks without executing")
    args = parser.parse_args()

    asyncio.run(run(args.desk, args.limit, args.dry_run))
