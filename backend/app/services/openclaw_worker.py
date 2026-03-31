"""OpenClaw Worker Loop — polls task queue, dispatches to OpenClaw, stores results.

Runs as an asyncio background task inside the FastAPI app.
One task at a time (protect EmpireDell resources).
"""

import asyncio
import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta

import httpx

log = logging.getLogger("openclaw_worker")

DB_PATH = os.path.expanduser("~/empire-repo/backend/data/empire.db")
OPENCLAW_URL = "http://localhost:7878"
OPENCLAW_TIMEOUT = 300  # 5 min per task
POLL_INTERVAL = 30  # seconds between queue checks
ZOMBIE_TIMEOUT_MINUTES = 10  # mark running tasks as failed after this


# ── Desk context for prompting ──────────────────────────────────────

DESK_CONTEXTS = {
    "CodeForge": "You are Atlas, the code desk. You write, test, and commit code in ~/empire-repo/. Use empire-backend and empire-frontend skills.",
    "MarketingDesk": "You are Nova, the marketing desk. You create social media content, blog posts, and marketing copy. Use empire-social skill.",
    "SupportDesk": "You are Luna, the support desk. You handle customer inquiries and update the knowledge base.",
    "ForgeDesk": "You are Kai, the workroom desk. You manage quotes, inventory, and scheduling.",
    "FinanceDesk": "You are Sage, the finance desk. You handle invoicing, payments, and financial reporting.",
    "ITDesk": "You are Orion, the IT desk. You monitor system health, manage services, and handle infrastructure.",
    "WebsiteDesk": "You are Zara, the website desk. You manage the website, SEO, and portfolio content.",
    "AnalyticsDesk": "You are Raven, the analytics desk. You produce business intelligence and revenue forecasting.",
    "QualityDesk": "You are Phoenix, the quality desk. You audit AI responses and maintain accuracy standards.",
    "SalesDesk": "You are Aria, the sales desk. You handle lead qualification and sales pipeline.",
    "ClientsDesk": "You are Elena, the clients desk. You manage customer relationships and preferences.",
    "ContractorsDesk": "You are Marcus, the contractors desk. You schedule and manage installer assignments.",
    "LegalDesk": "You are Raven, the legal desk. You handle contracts, compliance, and insurance.",
    "InnovationDesk": "You are Spark, the innovation desk. You scan markets, track competitors, and identify opportunities.",
    "LabDesk": "You are Phoenix, the lab desk. You prototype and test new features in a sandbox.",
    "IntakeDesk": "You are Zara, the intake desk. You process LuxeForge submissions and route projects.",
    "CostTracker": "You are CostTracker. You monitor AI token budgets and spending alerts.",
}


def _get_db():
    """Get a fresh database connection (thread-safe)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _get_next_task() -> dict | None:
    """Get the next queued task (highest priority, oldest first)."""
    conn = _get_db()
    try:
        row = conn.execute(
            "SELECT * FROM openclaw_tasks WHERE status = 'queued' ORDER BY priority ASC, created_at ASC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _update_task(task_id: int, **kwargs):
    """Update task fields in the database."""
    conn = _get_db()
    try:
        sets = []
        params = []
        for k, v in kwargs.items():
            sets.append(f"{k} = ?")
            params.append(v)
        params.append(task_id)
        conn.execute(f"UPDATE openclaw_tasks SET {', '.join(sets)} WHERE id = ?", params)
        conn.commit()
    finally:
        conn.close()


def _cleanup_zombies():
    """Mark tasks that have been 'running' for too long as failed."""
    conn = _get_db()
    try:
        cutoff = (datetime.now() - timedelta(minutes=ZOMBIE_TIMEOUT_MINUTES)).isoformat()
        result = conn.execute(
            """UPDATE openclaw_tasks SET status = 'failed',
               error = 'Zombie protection: task exceeded 10 minute timeout',
               completed_at = datetime('now')
               WHERE status = 'running' AND started_at < ?""",
            (cutoff,),
        )
        if result.rowcount > 0:
            log.warning(f"Cleaned up {result.rowcount} zombie tasks")
        conn.commit()
    finally:
        conn.close()


def _build_task_prompt(task: dict) -> str:
    """Build a context-rich prompt for OpenClaw based on task + desk."""
    desk = task.get("desk", "general")
    desk_context = DESK_CONTEXTS.get(desk, "You are a general Empire AI agent.")

    return f"""{desk_context}

TASK: {task['title']}
DESCRIPTION: {task['description']}
PRIORITY: {task['priority']}

RULES:
- Execute the task. Do not just describe what you would do.
- If you need to modify files, use the filesystem MCP.
- Report exactly what you did, what files you changed, and what needs review.
- If you're unsure about something, say "NEEDS_APPROVAL: [question]" and stop.
"""


async def _dispatch_to_openclaw(prompt: str) -> dict:
    """Send a prompt to OpenClaw and get the response."""
    async with httpx.AsyncClient(timeout=OPENCLAW_TIMEOUT) as client:
        resp = await client.post(
            f"{OPENCLAW_URL}/chat",
            json={
                "message": prompt,
                "history": [],
                "system_prompt": "You are MAX's execution agent. Execute the task precisely. Report what you did, what changed, and what needs review.",
            },
        )

    if resp.status_code == 200:
        data = resp.json()
        return {
            "success": True,
            "response": data.get("response", ""),
            "skill_used": data.get("skill_used"),
            "source": data.get("source", "openclaw"),
        }
    else:
        return {
            "success": False,
            "error": f"OpenClaw returned {resp.status_code}: {resp.text[:300]}",
        }


async def _notify_telegram(message: str):
    """Send a notification via the MAX chat/Telegram pipeline."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(
                "http://localhost:8000/api/v1/max/chat",
                json={"message": message, "channel": "telegram"},
            )
    except Exception as e:
        log.warning(f"Telegram notification failed: {e}")


async def _process_task(task: dict):
    """Process a single task: dispatch to OpenClaw, store result, notify."""
    task_id = task["id"]
    log.info(f"Processing task #{task_id}: {task['title']} [desk={task['desk']}, priority={task['priority']}]")

    # Mark as running
    _update_task(task_id, status="running", started_at=datetime.now().isoformat())

    try:
        prompt = _build_task_prompt(task)
        result = await _dispatch_to_openclaw(prompt)

        if result["success"]:
            response_text = result["response"]

            # Check for NEEDS_APPROVAL
            if "NEEDS_APPROVAL" in response_text:
                question = response_text.split("NEEDS_APPROVAL:")[-1].strip()[:500]
                _update_task(task_id, status="paused", result=response_text[:5000], error=f"NEEDS_APPROVAL: {question}")
                log.info(f"Task #{task_id} paused — needs approval: {question[:100]}")
                await _notify_telegram(
                    f"🤔 OpenClaw needs your input on Task #{task_id}: {task['title']}\n\n"
                    f"Question: {question}\n\n"
                    f"Approve at studio.empirebox.store/openclaw"
                )
                return

            # Success
            _update_task(
                task_id,
                status="done",
                result=response_text[:5000],
                completed_at=datetime.now().isoformat(),
            )
            log.info(f"Task #{task_id} completed: {task['title']}")

            # Notify for high-priority or tasks with changes
            if task["priority"] <= 3:
                await _notify_telegram(
                    f"✅ OpenClaw Task #{task_id}: {task['title']}\n"
                    f"Desk: {task['desk']}\n"
                    f"Result: {response_text[:300]}"
                )

        else:
            # Dispatch failed
            retry_count = task.get("retry_count", 0)
            max_retries = task.get("max_retries", 2)

            if retry_count < max_retries:
                _update_task(task_id, status="queued", retry_count=retry_count + 1,
                             error=result["error"][:2000])
                log.warning(f"Task #{task_id} failed, requeueing (attempt {retry_count + 1}/{max_retries})")
            else:
                _update_task(task_id, status="failed", error=result["error"][:2000],
                             completed_at=datetime.now().isoformat())
                log.error(f"Task #{task_id} failed after {max_retries} retries: {result['error'][:200]}")
                await _notify_telegram(
                    f"❌ OpenClaw Task #{task_id} FAILED: {task['title']}\n"
                    f"Desk: {task['desk']}\n"
                    f"Error: {result['error'][:300]}"
                )

    except httpx.ConnectError:
        _update_task(task_id, status="failed", error="OpenClaw not reachable on port 7878",
                     completed_at=datetime.now().isoformat())
        log.error(f"Task #{task_id} failed: OpenClaw unreachable")
    except httpx.ReadTimeout:
        _update_task(task_id, status="failed", error=f"OpenClaw timed out after {OPENCLAW_TIMEOUT}s",
                     completed_at=datetime.now().isoformat())
        log.error(f"Task #{task_id} timed out")
    except Exception as e:
        _update_task(task_id, status="failed", error=str(e)[:2000],
                     completed_at=datetime.now().isoformat())
        log.error(f"Task #{task_id} unexpected error: {e}")


_tasks_completed_since_summary = 0
_last_summary_time = None


async def _send_batch_summary():
    """Send a batch summary of recent completions. Called every 30 min if tasks were done."""
    global _tasks_completed_since_summary, _last_summary_time

    if _tasks_completed_since_summary < 1:
        return

    conn = _get_db()
    try:
        since = _last_summary_time or (datetime.now() - timedelta(minutes=30)).isoformat()
        done = conn.execute(
            "SELECT id, title, desk, status FROM openclaw_tasks WHERE completed_at > ? AND status = 'done' ORDER BY completed_at DESC LIMIT 10",
            (since,),
        ).fetchall()
        failed = conn.execute(
            "SELECT id, title, desk, error FROM openclaw_tasks WHERE completed_at > ? AND status = 'failed' ORDER BY completed_at DESC LIMIT 5",
            (since,),
        ).fetchall()
    finally:
        conn.close()

    if not done and not failed:
        _tasks_completed_since_summary = 0
        return

    msg = f"📊 OpenClaw Progress — {len(done)} done, {len(failed)} failed\n\n"
    for r in done:
        msg += f"✅ #{r[0]} {r[1]} ({r[2]})\n"
    for r in failed:
        msg += f"❌ #{r[0]} {r[1]}: {(r[3] or '')[:80]}\n"

    await _notify_telegram(msg)
    _tasks_completed_since_summary = 0
    _last_summary_time = datetime.now().isoformat()


async def openclaw_worker_loop():
    """Main worker loop — polls queue every 30 seconds, processes one task at a time."""
    global _tasks_completed_since_summary
    log.info("OpenClaw worker loop started — polling every %ds", POLL_INTERVAL)

    # Brief startup delay
    await asyncio.sleep(10)

    summary_interval = 0  # counter for batch summary timing

    while True:
        try:
            # Clean up zombies
            _cleanup_zombies()

            # Check for next task
            task = _get_next_task()
            if task:
                await _process_task(task)
                _tasks_completed_since_summary += 1
                # Brief pause between tasks
                await asyncio.sleep(5)
            else:
                await asyncio.sleep(POLL_INTERVAL)

            # Batch summary every ~30 minutes (60 poll cycles * 30s)
            summary_interval += 1
            if summary_interval >= 60:
                await _send_batch_summary()
                summary_interval = 0

        except Exception as e:
            log.error(f"Worker loop error: {e}")
            await asyncio.sleep(POLL_INTERVAL)
