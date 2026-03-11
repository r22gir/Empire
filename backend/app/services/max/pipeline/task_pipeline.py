"""
MAX Task Pipeline Engine — v6.0

Single entry point for multi-step autonomous work:
1. submit_pipeline(title, description, source, channel) → pipeline_id
2. AI breaks task into ordered subtasks with acceptance criteria
3. Routes subtasks to correct desks via existing desk_router
4. Background executor picks up queued subtasks (one at a time per desk)
5. Status: queued → assigned → in_progress → review → complete/failed
6. Founder approval for tasks in review state
7. Notifications via existing Telegram integration
"""
import json
import os
import uuid
import logging
from datetime import datetime
from typing import Optional

from app.db.database import get_db, dict_row, dict_rows
from app.services.max.ai_router import ai_router, AIMessage
from app.services.max.token_tracker import token_tracker

# Required API keys and their env vars — used by pre-check
REQUIRED_KEYS = {
    "XAI_API_KEY": "Grok chat/vision/TTS",
    "ANTHROPIC_API_KEY": "Claude fallback",
    "TELEGRAM_BOT_TOKEN": "Telegram notifications",
}
OPTIONAL_KEYS = {
    "GROQ_API_KEY": "Groq Whisper STT",
    "BRAVE_API_KEY": "Brave web search",
    "STABILITY_API_KEY": "Stability inpainting",
}

logger = logging.getLogger("max.pipeline")

# Pipeline-level statuses (on the pipeline row itself)
PIPELINE_STATUSES = ("active", "paused", "complete", "failed", "cancelled")

# Subtask statuses (on each task row with a pipeline_id)
SUBTASK_STATUSES = ("queued", "assigned", "in_progress", "review", "complete", "failed")

# Decomposition prompt — instructs AI to break a high-level task into subtasks
DECOMPOSE_PROMPT = """\
You are MAX, the autonomous AI manager for Empire — a drapery, upholstery, and CNC business platform.

Break the following task into 2-7 ordered subtasks. Each subtask should be assignable to ONE of these desks:
forge, sales, market, marketing, support, finance, clients, contractors, it, website, legal, lab

For each subtask, provide:
- title: short action title
- description: what needs to be done (specific, measurable)
- desk: which desk handles this
- acceptance_criteria: how we know it's done (1-2 sentences)
- depends_on: list of subtask indices (0-based) this depends on, or empty list

Respond with ONLY a JSON array, no other text:
[
  {"title": "...", "description": "...", "desk": "...", "acceptance_criteria": "...", "depends_on": []},
  ...
]

TASK TO DECOMPOSE:
Title: {title}
Description: {description}
Source: {source}
"""


class TaskPipeline:
    """Core pipeline engine for multi-step autonomous task execution."""

    def __init__(self):
        self._ensure_pipeline_columns()

    def _ensure_pipeline_columns(self):
        """Add pipeline columns to tasks table if they don't exist (safe migration)."""
        try:
            with get_db() as conn:
                # Check which columns exist
                cursor = conn.execute("PRAGMA table_info(tasks)")
                existing_cols = {row[1] for row in cursor.fetchall()}

                migrations = [
                    ("pipeline_id", "TEXT"),
                    ("subtask_order", "INTEGER DEFAULT 0"),
                    ("acceptance_criteria", "TEXT"),
                    ("channel", "TEXT DEFAULT 'system'"),
                    ("result_summary", "TEXT"),
                    ("resume_state", "TEXT"),  # JSON blob for partial progress resumption
                ]
                for col_name, col_type in migrations:
                    if col_name not in existing_cols:
                        conn.execute(f"ALTER TABLE tasks ADD COLUMN {col_name} {col_type}")
                        logger.info(f"Added column {col_name} to tasks table")

                # Index for pipeline lookups
                conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_pipeline ON tasks(pipeline_id)")
        except Exception as e:
            logger.error(f"Pipeline column migration failed: {e}")

    # ── Pipeline Submission ──────────────────────────────────────

    async def submit_pipeline(
        self,
        title: str,
        description: str,
        source: str = "founder",
        channel: str = "system",
    ) -> dict:
        """Create a new pipeline: decompose task into subtasks and queue them.

        Returns: {"pipeline_id": str, "title": str, "subtasks": list[dict], "status": str}
        """
        pipeline_id = f"pl-{uuid.uuid4().hex[:12]}"
        logger.info(f"[Pipeline] Creating {pipeline_id}: {title}")

        # Step 1: AI decomposition
        subtask_defs = await self._decompose_task(title, description, source)

        if not subtask_defs:
            # Fallback: single subtask assigned to forge
            subtask_defs = [{
                "title": title,
                "description": description,
                "desk": "forge",
                "acceptance_criteria": "Task completed as described",
                "depends_on": [],
            }]

        # Step 2: Persist pipeline header as a parent task
        with get_db() as conn:
            conn.execute(
                """INSERT INTO tasks (id, title, description, status, priority, desk,
                   created_by, pipeline_id, channel, metadata)
                   VALUES (?, ?, ?, 'in_progress', 'normal', 'pipeline',
                   ?, ?, ?, ?)""",
                (
                    pipeline_id, title, description, source,
                    pipeline_id, channel,
                    json.dumps({
                        "type": "pipeline_header",
                        "subtask_count": len(subtask_defs),
                        "source": source,
                        "created_at": datetime.utcnow().isoformat(),
                    }),
                ),
            )

            # Step 3: Create subtask rows
            subtasks_out = []
            for i, sd in enumerate(subtask_defs):
                task_id = f"pl-{uuid.uuid4().hex[:8]}"
                desk = sd.get("desk", "forge")
                conn.execute(
                    """INSERT INTO tasks (id, title, description, status, priority, desk,
                       created_by, pipeline_id, subtask_order, acceptance_criteria,
                       channel, metadata)
                       VALUES (?, ?, ?, 'todo', 'normal', ?,
                       'pipeline', ?, ?, ?,
                       ?, ?)""",
                    (
                        task_id,
                        sd.get("title", f"Subtask {i+1}"),
                        sd.get("description", ""),
                        desk,
                        pipeline_id,
                        i,
                        sd.get("acceptance_criteria", ""),
                        channel,
                        json.dumps({
                            "depends_on": sd.get("depends_on", []),
                            "source": source,
                        }),
                    ),
                )
                # Log activity
                conn.execute(
                    """INSERT INTO task_activity (task_id, actor, action, detail)
                       VALUES (?, 'pipeline', 'created', ?)""",
                    (task_id, f"Subtask {i+1} of pipeline {pipeline_id}"),
                )
                subtasks_out.append({
                    "id": task_id,
                    "order": i,
                    "title": sd.get("title"),
                    "desk": desk,
                    "status": "todo",
                    "acceptance_criteria": sd.get("acceptance_criteria"),
                    "depends_on": sd.get("depends_on", []),
                })

        logger.info(f"[Pipeline] {pipeline_id} created with {len(subtasks_out)} subtasks")
        return {
            "pipeline_id": pipeline_id,
            "title": title,
            "subtasks": subtasks_out,
            "status": "active",
        }

    # ── Task Decomposition via AI ────────────────────────────────

    async def _decompose_task(self, title: str, description: str, source: str) -> list[dict]:
        """Use AI to break a high-level task into ordered subtasks."""
        prompt = DECOMPOSE_PROMPT.format(title=title, description=description, source=source)

        try:
            response = await ai_router.chat(
                [AIMessage(role="user", content=prompt)],
                system_prompt="You are a task decomposition engine. Respond with ONLY valid JSON.",
            )
            raw = response.content.strip()

            # Extract JSON array from response
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start >= 0 and end > start:
                subtasks = json.loads(raw[start:end])
                if isinstance(subtasks, list) and len(subtasks) > 0:
                    # Validate desk assignments
                    valid_desks = {
                        "forge", "sales", "market", "marketing", "support",
                        "finance", "clients", "contractors", "it", "website",
                        "legal", "lab",
                    }
                    for st in subtasks:
                        if st.get("desk") not in valid_desks:
                            st["desk"] = "forge"  # safe default
                        if "depends_on" not in st:
                            st["depends_on"] = []
                    return subtasks[:7]  # cap at 7
        except Exception as e:
            logger.error(f"Task decomposition failed: {e}")

        return []

    # ── Pipeline Execution (called by scheduler) ─────────────────

    async def execute_next_subtasks(self) -> list[dict]:
        """Find and execute the next ready subtasks across all active pipelines.

        A subtask is ready when:
        1. Its pipeline is active (header status = 'in_progress')
        2. Its status is 'todo'
        3. All dependencies (by subtask_order) are 'done'

        Returns list of executed subtask results.
        """
        from app.services.max.desks.desk_manager import desk_manager

        results = []
        pipelines = self._get_active_pipelines()

        for pl in pipelines:
            pid = pl["id"]
            subtasks = self._get_subtasks(pid)

            # Build completion map: order → status
            status_map = {st["subtask_order"]: st["status"] for st in subtasks}

            for st in subtasks:
                if st["status"] != "todo":
                    continue

                # Check dependencies
                meta = {}
                try:
                    meta = json.loads(st.get("metadata") or "{}")
                except Exception:
                    pass
                deps = meta.get("depends_on", [])
                deps_met = all(status_map.get(d) == "done" for d in deps)

                if not deps_met:
                    continue

                # Execute this subtask via desk manager
                result = await self._execute_subtask(st, desk_manager)
                results.append(result)

        return results

    async def _execute_subtask(self, subtask: dict, desk_manager) -> dict:
        """Execute a single subtask by routing to the appropriate desk."""
        task_id = subtask["id"]
        desk_id = subtask["desk"]
        title = subtask["title"]
        desc = subtask.get("description", "")

        logger.info(f"[Pipeline] Executing subtask {task_id} on desk {desk_id}: {title}")

        # Mark as in_progress
        with get_db() as conn:
            conn.execute(
                "UPDATE tasks SET status = 'in_progress', updated_at = datetime('now') WHERE id = ?",
                (task_id,),
            )
            conn.execute(
                """INSERT INTO task_activity (task_id, actor, action, detail)
                   VALUES (?, 'pipeline', 'started', ?)""",
                (task_id, f"Executing on {desk_id} desk"),
            )

        try:
            # Route to desk via desk_manager.submit_task
            result = await desk_manager.submit_task(
                title=title,
                description=desc,
                priority="normal",
                customer_name=None,
                source="pipeline",
            )

            result_text = ""
            if hasattr(result, "result") and result.result:
                result_text = result.result
            elif hasattr(result, "description"):
                result_text = result.description or ""

            # Check if result needs founder review
            needs_review = False
            if hasattr(result, "state"):
                from app.services.max.desks.base_desk import TaskState
                needs_review = result.state == TaskState.ESCALATED

            new_status = "waiting" if needs_review else "done"

            with get_db() as conn:
                conn.execute(
                    """UPDATE tasks SET status = ?, result_summary = ?,
                       updated_at = datetime('now'), completed_at = CASE WHEN ? = 'done' THEN datetime('now') ELSE NULL END
                       WHERE id = ?""",
                    (new_status, result_text[:2000], new_status, task_id),
                )
                conn.execute(
                    """INSERT INTO task_activity (task_id, actor, action, detail)
                       VALUES (?, 'pipeline', ?, ?)""",
                    (task_id, "review" if needs_review else "completed", result_text[:500]),
                )

            # Check if pipeline is complete
            self._check_pipeline_completion(subtask.get("pipeline_id"))

            # Notify via Telegram
            await self._notify_subtask_result(subtask, new_status, result_text)

            return {
                "task_id": task_id,
                "desk": desk_id,
                "status": new_status,
                "result": result_text[:500],
            }

        except Exception as e:
            logger.error(f"[Pipeline] Subtask {task_id} failed: {e}")
            with get_db() as conn:
                conn.execute(
                    "UPDATE tasks SET status = 'cancelled', result_summary = ?, updated_at = datetime('now') WHERE id = ?",
                    (f"Failed: {e}", task_id),
                )
                conn.execute(
                    """INSERT INTO task_activity (task_id, actor, action, detail)
                       VALUES (?, 'pipeline', 'failed', ?)""",
                    (task_id, str(e)[:500]),
                )
            return {"task_id": task_id, "desk": desk_id, "status": "failed", "error": str(e)}

    # ── Founder Approval ─────────────────────────────────────────

    async def approve_subtask(self, task_id: str) -> dict:
        """Founder approves a subtask in review state → marks as done."""
        with get_db() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            if not row:
                return {"error": "Task not found"}
            task = dict(row)
            if task["status"] != "waiting":
                return {"error": f"Task is {task['status']}, not in review"}

            conn.execute(
                """UPDATE tasks SET status = 'done', completed_at = datetime('now'),
                   updated_at = datetime('now') WHERE id = ?""",
                (task_id,),
            )
            conn.execute(
                """INSERT INTO task_activity (task_id, actor, action, detail)
                   VALUES (?, 'founder', 'approved', 'Founder approved this subtask')""",
                (task_id,),
            )

        # Check if pipeline is now complete
        if task.get("pipeline_id"):
            self._check_pipeline_completion(task["pipeline_id"])

        return {"status": "approved", "task_id": task_id}

    async def reject_subtask(self, task_id: str, reason: str = "") -> dict:
        """Founder rejects a subtask → marks as todo for re-execution."""
        with get_db() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            if not row:
                return {"error": "Task not found"}
            task = dict(row)
            if task["status"] != "waiting":
                return {"error": f"Task is {task['status']}, not in review"}

            conn.execute(
                """UPDATE tasks SET status = 'todo', result_summary = NULL,
                   updated_at = datetime('now') WHERE id = ?""",
                (task_id,),
            )
            conn.execute(
                """INSERT INTO task_activity (task_id, actor, action, detail)
                   VALUES (?, 'founder', 'rejected', ?)""",
                (task_id, reason or "Founder rejected — will retry"),
            )

        return {"status": "rejected", "task_id": task_id}

    # ── Pipeline Queries ─────────────────────────────────────────

    def get_pipeline(self, pipeline_id: str) -> Optional[dict]:
        """Get a pipeline with all its subtasks."""
        with get_db() as conn:
            header = conn.execute(
                "SELECT * FROM tasks WHERE id = ? AND pipeline_id = ?",
                (pipeline_id, pipeline_id),
            ).fetchone()
            if not header:
                return None

            subtasks = conn.execute(
                """SELECT * FROM tasks WHERE pipeline_id = ? AND id != ?
                   ORDER BY subtask_order""",
                (pipeline_id, pipeline_id),
            ).fetchall()

            header_dict = dict(header)
            subtask_list = [dict(s) for s in subtasks]

            # Calculate progress
            total = len(subtask_list)
            done = sum(1 for s in subtask_list if s["status"] == "done")
            in_review = sum(1 for s in subtask_list if s["status"] == "waiting")
            failed = sum(1 for s in subtask_list if s["status"] == "cancelled")

            return {
                "pipeline_id": pipeline_id,
                "title": header_dict["title"],
                "description": header_dict.get("description"),
                "status": header_dict["status"],
                "channel": header_dict.get("channel", "system"),
                "created_at": header_dict.get("created_at"),
                "subtasks": subtask_list,
                "progress": {
                    "total": total,
                    "done": done,
                    "in_review": in_review,
                    "failed": failed,
                    "pending": total - done - in_review - failed,
                    "percent": round((done / total) * 100) if total > 0 else 0,
                },
            }

    def get_active_pipelines(self) -> list[dict]:
        """Get all active pipelines with progress summaries."""
        pipelines = self._get_active_pipelines()
        result = []
        for pl in pipelines:
            full = self.get_pipeline(pl["id"])
            if full:
                result.append(full)
        return result

    def get_all_pipelines(self, limit: int = 20) -> list[dict]:
        """Get all pipelines (active + completed), most recent first."""
        with get_db() as conn:
            rows = conn.execute(
                """SELECT * FROM tasks WHERE pipeline_id = id
                   ORDER BY created_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()

        result = []
        for row in rows:
            full = self.get_pipeline(dict(row)["id"])
            if full:
                result.append(full)
        return result

    def get_review_tasks(self) -> list[dict]:
        """Get all subtasks awaiting founder approval."""
        with get_db() as conn:
            rows = conn.execute(
                """SELECT t.*, p.title as pipeline_title FROM tasks t
                   LEFT JOIN tasks p ON t.pipeline_id = p.id AND p.pipeline_id = p.id
                   WHERE t.status = 'waiting' AND t.pipeline_id IS NOT NULL AND t.pipeline_id != t.id
                   ORDER BY t.updated_at DESC""",
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Internal Helpers ─────────────────────────────────────────

    def _get_active_pipelines(self) -> list[dict]:
        """Get pipeline header rows that are still active."""
        with get_db() as conn:
            rows = conn.execute(
                """SELECT * FROM tasks WHERE pipeline_id = id AND status = 'in_progress'
                   ORDER BY created_at DESC""",
            ).fetchall()
        return [dict(r) for r in rows]

    def _get_subtasks(self, pipeline_id: str) -> list[dict]:
        """Get all subtasks for a pipeline, ordered."""
        with get_db() as conn:
            rows = conn.execute(
                """SELECT * FROM tasks WHERE pipeline_id = ? AND id != ?
                   ORDER BY subtask_order""",
                (pipeline_id, pipeline_id),
            ).fetchall()
        return [dict(r) for r in rows]

    def _check_pipeline_completion(self, pipeline_id: str):
        """Check if all subtasks are done → mark pipeline complete."""
        if not pipeline_id:
            return
        subtasks = self._get_subtasks(pipeline_id)
        if not subtasks:
            return

        all_done = all(s["status"] == "done" for s in subtasks)
        any_failed = any(s["status"] == "cancelled" for s in subtasks)

        if all_done:
            with get_db() as conn:
                conn.execute(
                    "UPDATE tasks SET status = 'done', completed_at = datetime('now'), updated_at = datetime('now') WHERE id = ?",
                    (pipeline_id,),
                )
                conn.execute(
                    """INSERT INTO task_activity (task_id, actor, action, detail)
                       VALUES (?, 'pipeline', 'pipeline_complete', 'All subtasks completed')""",
                    (pipeline_id,),
                )
            logger.info(f"[Pipeline] {pipeline_id} COMPLETE — all subtasks done")
        elif any_failed and all(s["status"] in ("done", "cancelled") for s in subtasks):
            # All resolved but some failed
            with get_db() as conn:
                conn.execute(
                    "UPDATE tasks SET status = 'cancelled', updated_at = datetime('now') WHERE id = ?",
                    (pipeline_id,),
                )
            logger.info(f"[Pipeline] {pipeline_id} FAILED — some subtasks failed")

    async def _notify_subtask_result(self, subtask: dict, status: str, result_text: str):
        """Send Telegram notification for subtask completion/review."""
        try:
            from app.services.max.telegram_bot import telegram_bot
            if not telegram_bot.is_configured:
                return

            emoji = {"done": "✅", "waiting": "🔍", "cancelled": "❌"}.get(status, "📋")
            pipeline_id = subtask.get("pipeline_id", "?")
            desk = subtask.get("desk", "?")
            title = subtask.get("title", "?")

            msg = (
                f"{emoji} <b>Pipeline Update</b>\n\n"
                f"<b>Pipeline:</b> {pipeline_id}\n"
                f"<b>Subtask:</b> {title}\n"
                f"<b>Desk:</b> {desk}\n"
                f"<b>Status:</b> {status}\n"
            )
            if result_text:
                msg += f"\n<i>{result_text[:300]}</i>"

            if status == "waiting":
                # Add approval buttons
                markup = {
                    "inline_keyboard": [[
                        {"text": "✅ Approve", "callback_data": f"pl_approve_{subtask['id']}"},
                        {"text": "❌ Reject", "callback_data": f"pl_reject_{subtask['id']}"},
                    ]]
                }
                await telegram_bot.send_message(msg, reply_markup=markup)
            else:
                await telegram_bot.send_message(msg)
        except Exception as e:
            logger.warning(f"Pipeline notification failed: {e}")

    # ── Dependency Pre-Check ────────────────────────────────────

    async def pre_check_dependencies(self) -> dict:
        """Check for missing API keys and notify founder of blockers."""
        missing_required = []
        missing_optional = []

        for key, desc in REQUIRED_KEYS.items():
            if not os.getenv(key):
                missing_required.append(f"{key} ({desc})")
        for key, desc in OPTIONAL_KEYS.items():
            if not os.getenv(key):
                missing_optional.append(f"{key} ({desc})")

        result = {
            "status": "ok" if not missing_required else "degraded",
            "missing_required": missing_required,
            "missing_optional": missing_optional,
        }

        if missing_required or missing_optional:
            try:
                from app.services.max.telegram_bot import telegram_bot
                if telegram_bot.is_configured:
                    msg = "⚠️ <b>Pipeline Dependency Check</b>\n\n"
                    if missing_required:
                        msg += "<b>BLOCKERS:</b>\n" + "\n".join(f"• {k}" for k in missing_required) + "\n\n"
                    if missing_optional:
                        msg += "<b>Optional (degraded):</b>\n" + "\n".join(f"• {k}" for k in missing_optional)
                    await telegram_bot.send_message(msg)
            except Exception as e:
                logger.warning(f"Pre-check notification failed: {e}")

        return result

    # ── Ecosystem Audit ──────────────────────────────────────────

    async def audit_ecosystem(self) -> dict:
        """Scan for unwired endpoints, missing frontends, and generate backlog pipelines."""
        from pathlib import Path
        import re

        findings = []

        # 1. Check for backend routers with no frontend wiring
        router_dir = Path.home() / "empire-repo" / "backend" / "app" / "routers"
        if router_dir.exists():
            for rfile in router_dir.glob("**/*.py"):
                if rfile.name.startswith("_"):
                    continue
                content = rfile.read_text(errors="replace")
                endpoints = re.findall(r'@router\.(get|post|put|delete)\("([^"]+)"', content)
                if len(endpoints) > 3:
                    router_name = rfile.stem
                    findings.append({
                        "type": "router_audit",
                        "name": router_name,
                        "endpoint_count": len(endpoints),
                        "path": str(rfile),
                    })

        # 2. Check CraftForge frontend gap (known high-priority)
        craft_dir = Path.home() / "empire-repo" / "empire-command-center" / "app" / "components" / "screens"
        has_craftforge = any(
            "craft" in f.name.lower() for f in craft_dir.glob("*.tsx")
        ) if craft_dir.exists() else False

        if not has_craftforge:
            findings.append({
                "type": "missing_frontend",
                "name": "CraftForge",
                "description": "15 backend endpoints exist, zero frontend — biggest gap",
                "priority": "high",
            })

        # 3. Check sidebar/navigation items vs actual screens
        # 4. Check for placeholder vs live data in AMP
        amp_dir = Path.home() / "empire-repo" / "amp"
        if amp_dir.exists():
            findings.append({
                "type": "audit_needed",
                "name": "AMP",
                "description": "Port 3003 — needs audit for placeholders vs live data",
            })

        # 5. Check RelistApp completion
        relist_dir = Path.home() / "empire-repo" / "relistapp"
        if relist_dir.exists():
            findings.append({
                "type": "audit_needed",
                "name": "RelistApp",
                "description": "Smart Lister and Quote Verification — check completion status",
            })

        return {
            "findings": findings,
            "total": len(findings),
            "timestamp": datetime.utcnow().isoformat(),
        }

    # ── Resume Support ───────────────────────────────────────────

    def save_resume_state(self, task_id: str, state_data: dict):
        """Save partial progress for a subtask so it can resume after restart."""
        with get_db() as conn:
            conn.execute(
                "UPDATE tasks SET resume_state = ?, updated_at = datetime('now') WHERE id = ?",
                (json.dumps(state_data, default=str), task_id),
            )

    def get_resume_state(self, task_id: str) -> Optional[dict]:
        """Get saved resume state for a subtask."""
        with get_db() as conn:
            row = conn.execute("SELECT resume_state FROM tasks WHERE id = ?", (task_id,)).fetchone()
            if row and row[0]:
                try:
                    return json.loads(row[0])
                except Exception:
                    pass
        return None

    # ── Cancel Pipeline ──────────────────────────────────────────

    async def cancel_pipeline(self, pipeline_id: str) -> dict:
        """Cancel an active pipeline and all its pending subtasks."""
        with get_db() as conn:
            header = conn.execute(
                "SELECT * FROM tasks WHERE id = ? AND pipeline_id = ?",
                (pipeline_id, pipeline_id),
            ).fetchone()
            if not header:
                return {"error": "Pipeline not found"}

            # Cancel all pending subtasks
            conn.execute(
                """UPDATE tasks SET status = 'cancelled', updated_at = datetime('now')
                   WHERE pipeline_id = ? AND id != ? AND status IN ('todo', 'in_progress', 'waiting')""",
                (pipeline_id, pipeline_id),
            )
            # Cancel pipeline header
            conn.execute(
                "UPDATE tasks SET status = 'cancelled', updated_at = datetime('now') WHERE id = ?",
                (pipeline_id,),
            )
            conn.execute(
                """INSERT INTO task_activity (task_id, actor, action, detail)
                   VALUES (?, 'founder', 'cancelled', 'Pipeline cancelled by founder')""",
                (pipeline_id,),
            )

        return {"status": "cancelled", "pipeline_id": pipeline_id}


# Global singleton
pipeline_engine = TaskPipeline()
