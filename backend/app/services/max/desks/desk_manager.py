"""
AIDeskManager — manages all AI desks, routes tasks, generates reports.
Central coordinator for the desk delegation system.

Also provides backward-compatible methods (get_all_desks, create_task,
complete_task, fail_task, get_task, get_all_tasks, get_stats) that were
previously on the legacy DeskManager class, so router endpoints keep working.
"""
import logging
import uuid
from datetime import datetime
from enum import Enum
from .base_desk import BaseDesk, DeskTask, TaskPriority, TaskState
try:
    from app.db.database import get_db, dict_rows
except ImportError:
    get_db = None
from .desk_router import DeskRouter
from .forge_desk import ForgeDesk
from .market_desk import MarketDesk
from .marketing_desk import MarketingDesk
from .support_desk import SupportDesk
from .sales_desk import SalesDesk
from .finance_desk import FinanceDesk
from .clients_desk import ClientsDesk
from .contractors_desk import ContractorsDesk
from .it_desk import ITDesk
from .website_desk import WebsiteDesk
from .legal_desk import LegalDesk
from .lab_desk import LabDesk
from .innovation_desk import InnovationDesk
from .intake_desk import IntakeDesk
from .analytics_desk import AnalyticsDesk
from .quality_desk import QualityDesk
from .codeforge_desk import CodeForgeDesk

logger = logging.getLogger("max.desks.manager")


class TaskStatus(str, Enum):
    """Backward-compatible task status enum (matches legacy DeskManager)."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_INPUT = "needs_input"


class AIDeskManager:
    """Manages all AI desks: registration, routing, status, and reporting."""

    def __init__(self):
        self.router = DeskRouter()
        self.founder_inbox: list[DeskTask] = []
        self._legacy_tasks: dict[str, DeskTask] = {}
        self._initialized = False

    def initialize(self):
        """Register all desks. Called once at startup."""
        if self._initialized:
            return

        desks = [
            ForgeDesk(), MarketDesk(), MarketingDesk(),
            SupportDesk(), SalesDesk(), FinanceDesk(),
            ClientsDesk(), ContractorsDesk(), ITDesk(),
            WebsiteDesk(), LegalDesk(), LabDesk(),
            InnovationDesk(),
            IntakeDesk(), AnalyticsDesk(), QualityDesk(),
            CodeForgeDesk(),
        ]
        for desk in desks:
            self.router.register_desk(desk)

        self._initialized = True
        logger.info(f"AIDeskManager initialized with {len(desks)} desks: {self.router.desk_ids}")

    def get_desk(self, desk_id: str) -> BaseDesk | None:
        return self.router.get_desk(desk_id)

    @property
    def all_desks(self) -> list[BaseDesk]:
        return [self.router.get_desk(did) for did in self.router.desk_ids]

    async def submit_task(
        self,
        title: str,
        description: str,
        priority: str = "normal",
        customer_name: str | None = None,
        source: str = "max",
        conversation_id: str | None = None,
    ) -> DeskTask:
        """Create and route a task to the appropriate desk."""
        self.initialize()

        task = DeskTask(
            id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            priority=TaskPriority(priority) if priority in TaskPriority.__members__.values() else TaskPriority.NORMAL,
            source=source,
            customer_name=customer_name,
            conversation_id=conversation_id,
        )

        # Route to a desk
        desk_id, reason = await self.router.route_task(task)

        if desk_id:
            desk = self.router.get_desk(desk_id)
            logger.info(f"Task '{title}' → {desk.desk_name}: {reason}")
            return await desk.handle_task(task)
        else:
            # No desk matched — send to founder inbox
            task.state = TaskState.ESCALATED
            task.escalation_reason = reason
            self.founder_inbox.append(task)
            logger.info(f"Task '{title}' → founder inbox: {reason}")
            return task

    async def get_all_statuses(self) -> list[dict]:
        """Get status from all registered desks."""
        self.initialize()
        statuses = []
        for desk in self.all_desks:
            try:
                status = await desk.report_status()
                statuses.append(status)
            except Exception as e:
                statuses.append({
                    "desk_id": desk.desk_id,
                    "desk_name": desk.desk_name,
                    "status": "error",
                    "error": str(e),
                })
        return statuses

    async def generate_briefing(self) -> str:
        """Generate morning briefing with all desk statuses."""
        self.initialize()

        lines = [
            "## AI Desk Status Report",
            f"*Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*",
            "",
        ]

        for desk in self.all_desks:
            try:
                lines.append(desk.get_briefing_section())
                lines.append("")
            except Exception as e:
                lines.append(f"### {desk.desk_name}")
                lines.append(f"- Error generating status: {e}")
                lines.append("")

        # Founder inbox section
        if self.founder_inbox:
            lines.append("### Founder Inbox")
            lines.append(f"- {len(self.founder_inbox)} unrouted task(s) need your attention")
            for t in self.founder_inbox[:5]:
                lines.append(f"  - [{t.priority.value}] {t.title}: {t.escalation_reason}")
        else:
            lines.append("### Founder Inbox")
            lines.append("- Empty — all tasks routed successfully")

        return "\n".join(lines)

    async def generate_daily_report(self) -> dict:
        """Generate end-of-day desk report."""
        self.initialize()
        today = datetime.utcnow().strftime("%Y-%m-%d")

        report = {
            "date": today,
            "desks": {},
            "founder_inbox": len(self.founder_inbox),
            "summary": "",
        }

        total_completed = 0
        total_escalated = 0

        for desk in self.all_desks:
            status = await desk.report_status()
            completed_today = status.get("completed_today", 0)
            total_completed += completed_today
            total_escalated += status.get("escalated", 0)
            report["desks"][desk.desk_id] = status

        report["summary"] = (
            f"{total_completed} tasks completed, {total_escalated} escalated, "
            f"{len(self.founder_inbox)} in founder inbox"
        )

        return report

    # ── Backward-compatible API (replaces legacy DeskManager) ────────────

    def _get_db_task_counts(self) -> dict:
        """Fetch task counts per desk from DB."""
        counts = {}
        try:
            if not get_db:
                return counts
            with get_db() as conn:
                rows = dict_rows(conn.execute(
                    "SELECT desk, status, COUNT(*) as cnt FROM tasks WHERE status != 'cancelled' GROUP BY desk, status"
                ).fetchall())
                for r in rows:
                    desk_id = r["desk"]
                    if desk_id not in counts:
                        counts[desk_id] = {"completed": 0, "failed": 0, "todo": 0, "in_progress": 0}
                    if r["status"] == "done":
                        counts[desk_id]["completed"] = r["cnt"]
                    elif r["status"] == "failed":
                        counts[desk_id]["failed"] = r["cnt"]
                    elif r["status"] == "todo":
                        counts[desk_id]["todo"] = r["cnt"]
                    elif r["status"] == "in_progress":
                        counts[desk_id]["in_progress"] = r["cnt"]
        except Exception as e:
            logger.debug(f"Could not load DB task counts: {e}")
        return counts

    def get_all_desks(self) -> list[dict]:
        """Return desk list in the legacy format (used by /max/desks endpoint)."""
        self.initialize()
        db_counts = self._get_db_task_counts()
        return [
            {
                "id": desk.desk_id,
                "name": desk.desk_name,
                "agent_name": desk.agent_name,
                "description": desk.desk_description,
                "status": "busy" if desk.active_tasks else "idle",
                "domains": desk.capabilities,
                "current_task": desk.active_tasks[0].id if desk.active_tasks else None,
                "stats": {
                    "completed": db_counts.get(desk.desk_id, {}).get("completed", 0) + len(desk.completed_tasks),
                    "failed": db_counts.get(desk.desk_id, {}).get("failed", 0) + len([
                        t for t in desk.completed_tasks
                        if t.state == TaskState.FAILED
                    ]),
                    "todo": db_counts.get(desk.desk_id, {}).get("todo", 0),
                    "in_progress": db_counts.get(desk.desk_id, {}).get("in_progress", 0),
                },
            }
            for desk in self.all_desks
        ]

    def get_desk_legacy(self, desk_id: str) -> dict | None:
        """Get a single desk in legacy format (used by /max/desks/{desk_id})."""
        self.initialize()
        desk = self.get_desk(desk_id)
        if not desk:
            return None
        return {
            "id": desk.desk_id,
            "name": desk.desk_name,
            "agent_name": desk.agent_name,
            "description": desk.desk_description,
            "status": "busy" if desk.active_tasks else "idle",
            "domains": desk.capabilities,
            "current_task": desk.active_tasks[0].id if desk.active_tasks else None,
            "stats": {
                "completed": len(desk.completed_tasks),
                "failed": len([
                    t for t in desk.completed_tasks
                    if t.state == TaskState.FAILED
                ]),
            },
        }

    def create_task(
        self,
        title: str,
        description: str,
        desk_id: str | None = None,
        domains: list[str] | None = None,
        priority: int = 5,
    ) -> DeskTask:
        """Synchronous task creation for legacy endpoints.

        Creates a DeskTask and puts it in the founder inbox
        (actual routing happens via submit_task which is async).
        """
        self.initialize()
        pri_map = {1: "urgent", 2: "urgent", 3: "high", 4: "high",
                   5: "normal", 6: "normal", 7: "low", 8: "low", 9: "low", 10: "low"}
        priority_str = pri_map.get(priority, "normal")

        task = DeskTask(
            id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            priority=TaskPriority(priority_str),
            source="founder",
        )
        # Store in _legacy_tasks for retrieval
        self._legacy_tasks[task.id] = task

        # If desk_id given, try to assign directly
        if desk_id:
            desk = self.get_desk(desk_id)
            if desk:
                task.state = TaskState.IN_PROGRESS
                desk.active_tasks.append(task)

        logger.info(f"Created task {task.id}: {title} -> {desk_id or 'unassigned'}")
        return task

    def complete_task(self, task_id: str, result: dict | None = None) -> bool:
        """Mark a legacy task as completed."""
        task = self._legacy_tasks.get(task_id)
        if not task:
            return False
        task.state = TaskState.COMPLETED
        task.completed_at = datetime.utcnow().isoformat()
        task.result = str(result) if result else "Completed"
        # Remove from any desk's active list
        for desk in self.all_desks:
            if task in desk.active_tasks:
                desk.active_tasks.remove(task)
                desk.completed_tasks.append(task)
                break
        return True

    def fail_task(self, task_id: str, error: str = "Unknown error") -> bool:
        """Mark a legacy task as failed."""
        task = self._legacy_tasks.get(task_id)
        if not task:
            return False
        task.state = TaskState.FAILED
        task.completed_at = datetime.utcnow().isoformat()
        task.result = f"FAILED: {error}"
        for desk in self.all_desks:
            if task in desk.active_tasks:
                desk.active_tasks.remove(task)
                break
        return True

    def get_task(self, task_id: str) -> dict | None:
        """Get a task by ID in dict format."""
        task = self._legacy_tasks.get(task_id)
        if not task:
            return None
        return {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "desk_id": "unassigned",
            "status": task.state.value,
            "priority": task.priority.value,
            "created_at": task.created_at,
            "updated_at": task.completed_at or task.created_at,
            "result": task.result,
            "error": task.result if task.state == TaskState.FAILED else None,
        }

    def get_all_tasks(
        self, status: TaskStatus | None = None, desk_id: str | None = None
    ) -> list[dict]:
        """Get all tasks, optionally filtered."""
        tasks = list(self._legacy_tasks.values())
        if status:
            tasks = [t for t in tasks if t.state.value == status.value]
        results = []
        for t in tasks:
            results.append({
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "status": t.state.value,
                "priority": t.priority.value,
                "created_at": t.created_at,
            })
        return results

    def get_stats(self) -> dict:
        """Get overall system stats in legacy format."""
        self.initialize()
        all_tasks = list(self._legacy_tasks.values())
        return {
            "total_completed": len([t for t in all_tasks if t.state == TaskState.COMPLETED]),
            "total_failed": len([t for t in all_tasks if t.state == TaskState.FAILED]),
            "active_tasks": len([t for t in all_tasks if t.state == TaskState.IN_PROGRESS]),
            "pending_tasks": len([t for t in all_tasks if t.state == TaskState.PENDING]),
            "desks_busy": len([d for d in self.all_desks if d.active_tasks]),
            "desks_idle": len([d for d in self.all_desks if not d.active_tasks]),
        }


# Singleton instance
desk_manager = AIDeskManager()
