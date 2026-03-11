"""
ContractorsDesk — Installer/contractor scheduling, pay rates, and assignments.
Source: DB desk config (contractors) — no legacy bot equivalent.
"""
import logging
from datetime import datetime
from .base_desk import BaseDesk, DeskTask, DeskAction, TaskPriority

logger = logging.getLogger("max.desks.contractors")


class ContractorsDesk(BaseDesk):
    desk_id = "contractors"
    desk_name = "ContractorsDesk"
    agent_name = "Marcus"
    desk_description = (
        "Manages contractor relationships: installers, seamstresses, and vendors. "
        "Tracks availability, pay rates, specialties (motorization, heavy drapery), "
        "and reliability scores. Schedules installations by matching the right "
        "installer to the right job."
    )
    capabilities = [
        "availability_check",
        "installer_assignment",
        "pay_rate_tracking",
        "schedule_management",
        "specialty_matching",
        "reliability_scoring",
        "payment_logging",
    ]

    def __init__(self):
        super().__init__()
        self.assignments: list[dict] = []
        self.pending_payments: list[dict] = []

    async def handle_task(self, task: DeskTask) -> DeskTask:
        await self.accept_task(task)
        combined = f"{task.title} {task.description}".lower()

        try:
            if any(w in combined for w in ["available", "availability", "free", "open"]):
                return await self._handle_availability(task)
            elif any(w in combined for w in ["assign", "send", "dispatch", "schedule install"]):
                return await self._handle_assignment(task)
            elif any(w in combined for w in ["pay", "rate", "invoice", "payment"]):
                return await self._handle_payment(task)
            elif any(w in combined for w in ["specialty", "best for", "who can", "motoriz", "heavy"]):
                return await self._handle_specialty_match(task)
            elif any(w in combined for w in ["reliability", "score", "rating", "review"]):
                return await self._handle_reliability(task)
            else:
                return await self._handle_general(task)
        except Exception as e:
            logger.error(f"ContractorsDesk task failed: {e}")
            return await self.fail_task(task, str(e))

    async def _handle_availability(self, task: DeskTask) -> DeskTask:
        """AI-enhanced availability check."""
        task.actions.append(DeskAction(action="availability_check", detail="Checking contractor availability"))

        ai_result = await self.ai_call(
            f"Check contractor/installer availability for a drapery business.\n\n"
            f"Request: {task.description[:500]}\n"
            f"Current active assignments: {len(self.assignments)}\n"
            f"Pending payments: {len(self.pending_payments)}\n\n"
            f"Consider: travel distance, job complexity, installer specialties "
            f"(motorization, heavy drapery, blinds/shades). Suggest optimal scheduling."
        )

        result = ai_result if ai_result and len(ai_result) > 50 else (
            f"Availability check: {task.description[:200]}. "
            f"Check calendar for open slots. Consider: travel distance, job complexity, "
            f"installer specialties. Current assignments: {len(self.assignments)}."
        )
        return await self.complete_task(task, result)

    async def _handle_assignment(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="installer_assignment", detail="Processing installer assignment"))

        # Urgent assignments escalate
        if task.priority in (TaskPriority.URGENT, TaskPriority.HIGH):
            return await self.escalate(
                task,
                f"Urgent installer assignment: {task.title} — needs founder to confirm crew and date"
            )

        self.assignments.append({
            "task_id": task.id,
            "job": task.title,
            "customer": task.customer_name or "Unknown",
            "status": "assigned",
            "date": datetime.utcnow().isoformat(),
        })

        await self.notify_telegram(
            f"Installer assigned\nJob: {task.title}\nCustomer: {task.customer_name or 'Unknown'}"
        )

        result = (
            f"Installer assignment logged: {task.title}. "
            f"Customer: {task.customer_name or 'Unknown'}. "
            f"Next: Confirm date with installer and customer, verify tools/materials needed."
        )

        self._log_to_brain(
            f"Assignment: {task.title} for {task.customer_name or 'Unknown'}",
            importance=6,
            tags=["desk", "contractors", "assignment"],
        )

        return await self.complete_task(task, result)

    async def _handle_payment(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="contractor_payment", detail="Processing contractor payment"))

        self.pending_payments.append({
            "task_id": task.id,
            "description": task.title,
            "date": datetime.utcnow().isoformat(),
        })

        result = (
            f"Contractor payment logged: {task.title}. "
            f"Details: {task.description[:200]}. "
            f"Pending payments: {len(self.pending_payments)}."
        )
        return await self.complete_task(task, result)

    async def _handle_specialty_match(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="specialty_match", detail="Matching job to installer specialty"))

        combined = f"{task.title} {task.description}".lower()
        if "motoriz" in combined:
            specialty = "motorization specialist (Somfy/Lutron certified)"
        elif "heavy" in combined:
            specialty = "heavy drapery installer (can handle 50+ lb treatments)"
        elif "blind" in combined or "shade" in combined:
            specialty = "blinds/shades technician"
        else:
            specialty = "general installer"

        result = (
            f"Specialty match: {task.title}. "
            f"Recommended: {specialty}. "
            f"Check availability and proximity to job site."
        )
        return await self.complete_task(task, result)

    async def _handle_reliability(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="reliability_check", detail="Reviewing contractor reliability"))

        result = (
            f"Reliability review: {task.description[:200]}. "
            f"Track: on-time rate, quality scores, customer feedback, callbacks needed."
        )
        return await self.complete_task(task, result)

    async def _handle_general(self, task: DeskTask) -> DeskTask:
        """AI-enhanced general contractor task."""
        task.actions.append(DeskAction(action="general_contractors", detail="Processing contractor task"))

        ai_result = await self.ai_call(
            f"Contractor management task for Empire Workroom:\n\n"
            f"Title: {task.title}\n"
            f"Details: {task.description[:500]}\n\n"
            f"Provide actionable response."
        )

        result = ai_result if ai_result and len(ai_result) > 30 else (
            f"Contractor task processed: {task.title}. {task.description[:200]}"
        )
        return await self.complete_task(task, result)

    async def report_status(self) -> dict:
        base = await super().report_status()
        base["active_assignments"] = len(self.assignments)
        base["pending_payments"] = len(self.pending_payments)
        return base
