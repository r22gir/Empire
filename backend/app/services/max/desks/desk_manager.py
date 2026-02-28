"""
AIDeskManager — manages all AI desks, routes tasks, generates reports.
Central coordinator for the desk delegation system.
"""
import logging
import uuid
from datetime import datetime
from .base_desk import BaseDesk, DeskTask, TaskPriority, TaskState
from .desk_router import DeskRouter
from .forge_desk import ForgeDesk
from .market_desk import MarketDesk
from .social_desk import SocialDesk
from .support_desk import SupportDesk

logger = logging.getLogger("max.desks.manager")


class AIDeskManager:
    """Manages all AI desks: registration, routing, status, and reporting."""

    def __init__(self):
        self.router = DeskRouter()
        self.founder_inbox: list[DeskTask] = []
        self._initialized = False

    def initialize(self):
        """Register all desks. Called once at startup."""
        if self._initialized:
            return

        desks = [ForgeDesk(), MarketDesk(), SocialDesk(), SupportDesk()]
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


# Singleton instance
desk_manager = AIDeskManager()
