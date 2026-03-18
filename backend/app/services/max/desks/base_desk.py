"""
BaseDesk — abstract base class for all AI desks.
All desks inherit from this to get: task handling, status reporting,
escalation, automatic brain memory logging, AI calls with cost tracking,
and scoped file/git operations (v6.0).
"""
import logging
import os
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger("max.desks")


class TaskPriority(str, Enum):
    URGENT = "urgent"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class TaskState(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ESCALATED = "escalated"


@dataclass
class DeskAction:
    """A single action taken by a desk."""
    action: str
    detail: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    success: bool = True


@dataclass
class DeskTask:
    """A task assigned to a desk."""
    id: str
    title: str
    description: str
    priority: TaskPriority = TaskPriority.NORMAL
    state: TaskState = TaskState.PENDING
    source: str = "max"  # who created it: max, auto, founder, desk
    customer_name: Optional[str] = None
    conversation_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    result: Optional[str] = None
    actions: list[DeskAction] = field(default_factory=list)
    escalation_reason: Optional[str] = None


class BaseDesk(ABC):
    """Abstract base class for all AI desks."""

    desk_id: str = "base"
    desk_name: str = "Base Desk"
    desk_description: str = "Abstract base desk"
    agent_name: str = "MAX"
    capabilities: list[str] = []
    preferred_model: str = "grok"  # default; desks override for cost-optimized routing

    def __init__(self):
        self.active_tasks: list[DeskTask] = []
        self.completed_tasks: list[DeskTask] = []
        self.escalated_tasks: list[DeskTask] = []
        self._memory_store = None
        self._token_tracker = None
        self._telegram = None

    @property
    def memory_store(self):
        if self._memory_store is None:
            try:
                from app.services.max.brain.memory_store import MemoryStore
                self._memory_store = MemoryStore()
            except Exception:
                pass
        return self._memory_store

    @property
    def token_tracker(self):
        if self._token_tracker is None:
            try:
                from app.services.max.token_tracker import token_tracker
                self._token_tracker = token_tracker
            except Exception:
                pass
        return self._token_tracker

    @property
    def telegram(self):
        """Lazy-load the shared TelegramBot instance."""
        if self._telegram is None:
            try:
                from app.services.max.telegram_bot import telegram_bot
                self._telegram = telegram_bot
            except Exception:
                pass
        return self._telegram

    async def notify_telegram(self, message: str) -> bool:
        """Send a notification via Telegram. Available to all desks."""
        if not self.telegram or not self.telegram.is_configured:
            return False
        try:
            return await self.telegram.send_message(
                f"🏢 <b>{self.agent_name} ({self.desk_name})</b>\n\n{message}"
            )
        except Exception as e:
            logger.warning(f"Telegram notification failed: {e}")
            return False

    def _log_to_brain(self, content: str, importance: int = 5, tags: list[str] = None):
        """Log an action to the brain memory store."""
        if not self.memory_store:
            return
        try:
            self.memory_store.add_memory(
                category="desk_action",
                subcategory=self.desk_id,
                content=f"[{self.agent_name}@{self.desk_name}] {content}",
                subject=f"{self.agent_name} ({self.desk_name})",
                importance=importance,
                source="desk",
                tags=tags or ["desk", self.desk_id],
            )
        except Exception as e:
            logger.warning(f"Failed to log desk action to brain: {e}")

    @abstractmethod
    async def handle_task(self, task: DeskTask) -> DeskTask:
        """Process a task. Must be implemented by each desk.

        Should update task.state, task.result, and task.actions.
        Returns the updated task.
        """
        ...

    async def ai_execute_task(self, task: DeskTask) -> str:
        """Use AI (Grok/Claude) to execute a task with the desk's system prompt.

        Returns the AI-generated result text. Desks can call this from handle_task()
        or it can be used by the standalone task worker script.
        """
        from app.services.max.ai_router import ai_router, AIMessage

        # Load desk-specific system prompt
        try:
            from app.services.max.desk_prompt import get_desk_system_prompt
            system_prompt = get_desk_system_prompt(self.desk_id)
        except Exception:
            system_prompt = (
                f"You are {self.agent_name}, the AI agent running the {self.desk_name} desk for Empire, "
                f"a custom drapery and upholstery business in Washington DC. "
                f"Complete the assigned task thoroughly and provide actionable results."
            )

        user_message = (
            f"Complete this research task for the {self.desk_name} desk.\n\n"
            f"**Task:** {task.title}\n\n"
            f"**Details:** {task.description}\n\n"
            f"**Priority:** {task.priority.value if hasattr(task.priority, 'value') else task.priority}\n\n"
            f"Provide thorough, specific, actionable results. "
            f"Include real data, numbers, and recommendations where applicable. "
            f"Format your response with clear headings and bullet points."
        )

        response = await ai_router.chat(
            messages=[AIMessage(role="user", content=user_message)],
            desk=self.desk_id,
            system_prompt=system_prompt,
        )
        return response.content

    # ── v6.0: AI Call with Cost Tracking ───────────────────────────

    async def ai_call(self, prompt: str, model_preference: Optional[str] = None) -> str:
        """Call AI router with automatic cost tracking per desk.

        Use this instead of raw ai_router.chat() — it logs costs to the desk
        and falls back gracefully if all providers are down.

        Uses desk's preferred_model if no explicit model_preference is given.

        Args:
            prompt: The user/task prompt to send to AI.
            model_preference: Optional model ID ("grok", "claude", "ollama-llama").
                             Falls back to self.preferred_model if not specified.

        Returns: AI response text, or empty string on failure.
        """
        from app.services.max.ai_router import ai_router, AIMessage, AIModel

        # Use explicit preference, then desk default, then global default
        pref = model_preference or self.preferred_model
        model = None
        if pref:
            try:
                model = AIModel(pref)
            except ValueError:
                pass

        try:
            from app.services.max.desk_prompt import get_desk_system_prompt
            system_prompt = get_desk_system_prompt(self.desk_id)
        except Exception:
            system_prompt = (
                f"You are {self.agent_name}, the AI agent running the {self.desk_name} desk "
                f"for Empire, a custom drapery and upholstery business in Washington DC."
            )

        try:
            response = await ai_router.chat(
                messages=[AIMessage(role="user", content=prompt)],
                model=model,
                desk=self.desk_id,
                system_prompt=system_prompt,
            )
            return response.content
        except Exception as e:
            logger.warning(f"[{self.desk_name}] ai_call failed: {e}")
            return ""

    # ── v6.0: Scoped File Operations ────────────────────────────

    # All file ops are scoped to ~/empire-repo/ — desks cannot escape this boundary
    _REPO_ROOT = Path.home() / "empire-repo"

    def write_file(self, relative_path: str, content: str) -> dict:
        """Write a file within the empire-repo directory (scoped).

        Args:
            relative_path: Path relative to ~/empire-repo/ (e.g., "backend/data/reports/daily.md")
            content: File content to write.

        Returns: {"success": bool, "path": str, "error": str | None}
        """
        try:
            target = (self._REPO_ROOT / relative_path).resolve()

            # Security: ensure path stays within repo
            if not str(target).startswith(str(self._REPO_ROOT.resolve())):
                return {"success": False, "path": str(target), "error": "Path traversal blocked"}

            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)

            self._log_to_brain(
                f"Wrote file: {relative_path} ({len(content)} chars)",
                importance=5,
                tags=["desk", self.desk_id, "file_write"],
            )

            # Log to task_activity
            try:
                from app.db.database import get_db
                with get_db() as conn:
                    conn.execute(
                        """INSERT INTO task_activity (task_id, actor, action, detail)
                           VALUES (?, ?, 'file_write', ?)""",
                        (f"desk_{self.desk_id}", self.agent_name, f"Wrote {relative_path}"),
                    )
            except Exception:
                pass

            return {"success": True, "path": str(target), "error": None}
        except Exception as e:
            logger.error(f"[{self.desk_name}] write_file failed: {e}")
            return {"success": False, "path": relative_path, "error": str(e)}

    def git_commit(self, message: str, files: list[str] = None) -> dict:
        """Create a git commit within empire-repo (scoped, non-destructive).

        Args:
            message: Commit message. Will be auto-tagged with desk name.
            files: List of relative paths to stage. If None, stages all changes.

        Returns: {"success": bool, "commit_hash": str | None, "error": str | None}
        """
        repo = str(self._REPO_ROOT)
        tagged_msg = f"[{self.desk_id}/{self.agent_name}] {message}"

        try:
            # Stage files
            if files:
                for f in files:
                    target = (self._REPO_ROOT / f).resolve()
                    if not str(target).startswith(str(self._REPO_ROOT.resolve())):
                        continue
                    subprocess.run(
                        ["git", "add", f], cwd=repo,
                        capture_output=True, text=True, timeout=10,
                    )
            else:
                subprocess.run(
                    ["git", "add", "-A"], cwd=repo,
                    capture_output=True, text=True, timeout=10,
                )

            # Commit
            result = subprocess.run(
                ["git", "commit", "-m", tagged_msg],
                cwd=repo, capture_output=True, text=True, timeout=30,
            )

            if result.returncode == 0:
                # Extract commit hash
                log_result = subprocess.run(
                    ["git", "log", "--oneline", "-1"],
                    cwd=repo, capture_output=True, text=True, timeout=5,
                )
                commit_hash = log_result.stdout.strip().split()[0] if log_result.stdout else "unknown"

                self._log_to_brain(
                    f"Git commit: {commit_hash} — {message}",
                    importance=6,
                    tags=["desk", self.desk_id, "git_commit"],
                )

                return {"success": True, "commit_hash": commit_hash, "error": None}
            else:
                error = result.stderr.strip() or result.stdout.strip()
                if "nothing to commit" in error.lower():
                    return {"success": True, "commit_hash": None, "error": "Nothing to commit"}
                return {"success": False, "commit_hash": None, "error": error}

        except subprocess.TimeoutExpired:
            return {"success": False, "commit_hash": None, "error": "Git command timed out"}
        except Exception as e:
            logger.error(f"[{self.desk_name}] git_commit failed: {e}")
            return {"success": False, "commit_hash": None, "error": str(e)}

    # ── v6.0: OpenClaw Dispatch ──────────────────────────────────

    async def dispatch_to_openclaw(self, task: DeskTask) -> DeskTask:
        """Dispatch a task to OpenClaw for execution. Fallback for complex tasks.

        Any desk can call this when its own handler cannot complete a task,
        e.g., when the task requires shell execution or autonomous code work.
        OpenClaw may not be running — all errors are handled gracefully.
        """
        try:
            from app.routers.openclaw_bridge import dispatch_desk_task_to_openclaw

            result = await dispatch_desk_task_to_openclaw(
                desk_id=self.desk_id,
                task_title=task.title,
                task_description=task.description,
            )

            if result.get("status") == "completed":
                self._log_to_brain(
                    f"OpenClaw completed task: {task.title}",
                    importance=6,
                    tags=["desk", self.desk_id, "openclaw", "completed"],
                )
                return await self.complete_task(task, result.get("summary", "Completed via OpenClaw"))
            else:
                error_msg = result.get("error", "OpenClaw execution failed")
                self._log_to_brain(
                    f"OpenClaw failed task: {task.title} — {error_msg}",
                    importance=7,
                    tags=["desk", self.desk_id, "openclaw", "failed"],
                )
                return await self.fail_task(task, f"OpenClaw: {error_msg}")

        except Exception as e:
            logger.warning(f"[{self.desk_name}] OpenClaw dispatch error: {e}")
            return await self.fail_task(task, f"OpenClaw unavailable: {e}")

    # ── v6.0: Cross-Desk Delegation ─────────────────────────────

    async def delegate_to_pipeline(self, title: str, description: str) -> dict:
        """Submit a multi-step task to the pipeline engine for cross-desk execution.

        Use when a task requires work from multiple desks.
        Returns: pipeline submission result dict.
        """
        try:
            from app.services.max.pipeline import pipeline_engine
            result = await pipeline_engine.submit_pipeline(
                title=title,
                description=description,
                source=f"desk:{self.desk_id}",
                channel="desk",
            )
            self._log_to_brain(
                f"Delegated to pipeline: {title} ({result.get('pipeline_id', '?')})",
                importance=6,
                tags=["desk", self.desk_id, "pipeline_delegation"],
            )
            return result
        except Exception as e:
            logger.error(f"[{self.desk_name}] Pipeline delegation failed: {e}")
            return {"error": str(e)}

    def _task_to_dict(self, task: DeskTask) -> dict:
        """Convert a DeskTask to a serializable dict with full details."""
        return {
            "id": task.id,
            "title": task.title,
            "description": task.description[:200] if task.description else "",
            "priority": task.priority.value if hasattr(task.priority, 'value') else str(task.priority),
            "state": task.state.value if hasattr(task.state, 'value') else str(task.state),
            "source": task.source,
            "customer_name": task.customer_name,
            "created_at": task.created_at,
            "completed_at": task.completed_at,
            "result": task.result[:500] if task.result else None,
            "escalation_reason": task.escalation_reason,
            "actions": [
                {"action": a.action, "detail": a.detail[:300], "timestamp": a.timestamp, "success": a.success}
                for a in (task.actions or [])
            ],
        }

    async def report_status(self) -> dict:
        """Return desk status summary with recent task details."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        completed_today = [
            t for t in self.completed_tasks
            if t.completed_at and t.completed_at[:10] == today
        ]
        # Recent tasks: last 10 completed (most recent first)
        recent = sorted(self.completed_tasks, key=lambda t: t.completed_at or "", reverse=True)[:10]

        return {
            "desk_id": self.desk_id,
            "desk_name": self.desk_name,
            "agent_name": self.agent_name,
            "description": self.desk_description,
            "capabilities": self.capabilities,
            "active_tasks": len(self.active_tasks),
            "completed_today": len(completed_today),
            "completed_total": len(self.completed_tasks),
            "escalated": len(self.escalated_tasks),
            "status": "busy" if self.active_tasks else "idle",
            # Detailed task lists
            "active_task_details": [self._task_to_dict(t) for t in self.active_tasks],
            "escalated_task_details": [self._task_to_dict(t) for t in self.escalated_tasks[-5:]],
            "recent_completed": [self._task_to_dict(t) for t in recent],
            "last_activity": (
                recent[0].completed_at if recent else
                self.active_tasks[-1].created_at if self.active_tasks else None
            ),
        }

    async def escalate(self, task: DeskTask, reason: str) -> DeskTask:
        """Escalate a task to the founder's inbox."""
        task.state = TaskState.ESCALATED
        task.escalation_reason = reason
        task.actions.append(DeskAction(
            action="escalated",
            detail=f"Escalated to founder: {reason}",
        ))

        # Move to escalated list
        if task in self.active_tasks:
            self.active_tasks.remove(task)
        self.escalated_tasks.append(task)

        self._log_to_brain(
            f"Escalated task '{task.title}' — {reason}",
            importance=8,
            tags=["desk", self.desk_id, "escalation"],
        )

        logger.info(f"[{self.desk_name}] Escalated: {task.title} — {reason}")
        return task

    async def accept_task(self, task: DeskTask) -> DeskTask:
        """Accept a task into the active queue."""
        task.state = TaskState.IN_PROGRESS
        task.actions.append(DeskAction(
            action="accepted",
            detail=f"Task accepted by {self.desk_name}",
        ))
        self.active_tasks.append(task)

        self._log_to_brain(
            f"Accepted task: {task.title}",
            importance=5,
            tags=["desk", self.desk_id, "task_accepted"],
        )

        logger.info(f"[{self.desk_name}] Accepted: {task.title}")
        return task

    async def complete_task(self, task: DeskTask, result: str) -> DeskTask:
        """Mark a task as completed."""
        task.state = TaskState.COMPLETED
        task.result = result
        task.completed_at = datetime.utcnow().isoformat()
        task.actions.append(DeskAction(
            action="completed",
            detail=result,
        ))

        if task in self.active_tasks:
            self.active_tasks.remove(task)
        self.completed_tasks.append(task)

        self._log_to_brain(
            f"Completed task: {task.title} — {result}",
            importance=6,
            tags=["desk", self.desk_id, "task_completed"],
        )

        logger.info(f"[{self.desk_name}] Completed: {task.title}")
        return task

    async def fail_task(self, task: DeskTask, error: str) -> DeskTask:
        """Mark a task as failed."""
        task.state = TaskState.FAILED
        task.result = f"FAILED: {error}"
        task.completed_at = datetime.utcnow().isoformat()
        task.actions.append(DeskAction(
            action="failed",
            detail=error,
            success=False,
        ))

        if task in self.active_tasks:
            self.active_tasks.remove(task)

        self._log_to_brain(
            f"Failed task: {task.title} — {error}",
            importance=7,
            tags=["desk", self.desk_id, "task_failed"],
        )

        logger.warning(f"[{self.desk_name}] Failed: {task.title} — {error}")
        return task

    def get_briefing_section(self) -> str:
        """Generate this desk's section for the morning briefing."""
        active = len(self.active_tasks)
        today_done = len([
            t for t in self.completed_tasks
            if t.completed_at and t.completed_at[:10] == datetime.utcnow().strftime("%Y-%m-%d")
        ])
        escalated = len(self.escalated_tasks)

        lines = [f"### {self.desk_name}"]
        if active == 0 and today_done == 0 and escalated == 0:
            lines.append("- Idle, no activity")
        else:
            if active > 0:
                lines.append(f"- {active} active task(s)")
                for t in self.active_tasks[:3]:
                    lines.append(f"  - [{t.priority.value}] {t.title}")
            if today_done > 0:
                lines.append(f"- {today_done} completed today")
            if escalated > 0:
                lines.append(f"- {escalated} escalated (needs your attention)")
                for t in self.escalated_tasks[:3]:
                    lines.append(f"  - {t.title}: {t.escalation_reason}")

        return "\n".join(lines)

    async def generate_tasks_from_findings(
        self,
        findings: list[dict],
        default_priority: str = "normal",
    ) -> list[dict]:
        """Create persistent SQLite tasks from desk audit findings.

        Each finding dict should have:
          - title: str (required)
          - description: str (optional)
          - priority: str (optional, defaults to default_priority)
          - due_date: str (optional, YYYY-MM-DD)
          - follow_up_date: str (optional)
          - recurrence: str (optional)

        Returns list of created task dicts.
        """
        from app.db.database import get_db
        import json as _json

        created = []
        with get_db() as conn:
            for f in findings:
                title = f.get("title")
                if not title:
                    continue
                priority = f.get("priority", default_priority)
                conn.execute(
                    """INSERT INTO tasks
                       (id, title, description, status, priority, desk,
                        assigned_to, created_by, due_date, follow_up_date,
                        recurrence, source, tags, metadata)
                       VALUES (lower(hex(randomblob(8))), ?, ?, 'todo', ?, ?, ?, 'max', ?, ?, ?, 'desk_audit', ?, ?)""",
                    (
                        title,
                        f.get("description"),
                        priority,
                        self.desk_id,
                        f.get("assigned_to"),
                        f.get("due_date"),
                        f.get("follow_up_date"),
                        f.get("recurrence"),
                        _json.dumps(f.get("tags", [self.desk_id, "auto"])),
                        _json.dumps(f.get("metadata", {})),
                    ),
                )
                row = conn.execute(
                    "SELECT * FROM tasks ORDER BY created_at DESC LIMIT 1"
                ).fetchone()
                if row:
                    created.append({
                        "id": row[0], "title": row[1], "desk": self.desk_id,
                        "priority": priority, "status": "todo",
                    })

        if created:
            self._log_to_brain(
                f"Auto-generated {len(created)} tasks from audit findings",
                importance=6,
                tags=["desk", self.desk_id, "auto_tasks"],
            )

        return created
