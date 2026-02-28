"""
BaseDesk — abstract base class for all AI desks.
All desks inherit from this to get: task handling, status reporting,
escalation, and automatic brain memory logging.
"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
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
    capabilities: list[str] = []

    def __init__(self):
        self.active_tasks: list[DeskTask] = []
        self.completed_tasks: list[DeskTask] = []
        self.escalated_tasks: list[DeskTask] = []
        self._memory_store = None
        self._token_tracker = None

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

    def _log_to_brain(self, content: str, importance: int = 5, tags: list[str] = None):
        """Log an action to the brain memory store."""
        if not self.memory_store:
            return
        try:
            self.memory_store.add_memory(
                category="desk_action",
                subcategory=self.desk_id,
                content=f"[{self.desk_name}] {content}",
                subject=self.desk_name,
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

    async def report_status(self) -> dict:
        """Return desk status summary."""
        return {
            "desk_id": self.desk_id,
            "desk_name": self.desk_name,
            "description": self.desk_description,
            "capabilities": self.capabilities,
            "active_tasks": len(self.active_tasks),
            "completed_today": len([
                t for t in self.completed_tasks
                if t.completed_at and t.completed_at[:10] == datetime.utcnow().strftime("%Y-%m-%d")
            ]),
            "escalated": len(self.escalated_tasks),
            "status": "busy" if self.active_tasks else "idle",
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
