"""
Zara — Intake Desk: Handles LuxeForge intake submissions.
Auto-classifies project type, routes to correct business, sends auto-response.
"""
import logging
from typing import Optional
from .base_desk import BaseDesk, DeskTask, DeskAction, TaskState

logger = logging.getLogger("max.desks.intake")


class IntakeDesk(BaseDesk):
    desk_id = "intake"
    desk_name = "Intake Desk"
    desk_description = "Handles incoming client submissions — classifies, routes, and responds"
    agent_name = "Zara"
    capabilities = [
        "classify_project",
        "route_to_business",
        "send_auto_response",
        "create_customer_record",
    ]

    PROJECT_TYPES = {
        "drapery": "workroom",
        "drapes": "workroom",
        "curtains": "workroom",
        "upholstery": "workroom",
        "pillows": "workroom",
        "blinds": "workroom",
        "shades": "workroom",
        "valance": "workroom",
        "cnc": "craftforge",
        "woodwork": "craftforge",
        "3d print": "craftforge",
        "furniture": "craftforge",
        "cabinet": "craftforge",
    }

    def classify_project(self, description: str) -> tuple[str, str]:
        """Classify project type and route to correct business."""
        desc_lower = description.lower()
        for keyword, business in self.PROJECT_TYPES.items():
            if keyword in desc_lower:
                return keyword, business
        return "general", "workroom"  # Default to workroom

    async def _handle_task(self, task: DeskTask) -> DeskTask:
        """Process an intake submission."""
        task.state = TaskState.IN_PROGRESS
        task.actions.append(DeskAction(action="started", detail="Processing intake submission"))

        # Classify the project
        project_type, business = self.classify_project(task.description)
        task.actions.append(DeskAction(
            action="classified",
            detail=f"Project type: {project_type}, routed to: {business}",
        ))

        # Log to brain
        self._log_to_brain(
            f"New intake: {task.customer_name or 'Unknown'} — {project_type} → {business}",
            importance=7,
            tags=["intake", "new_lead", business],
        )

        # Notify via Telegram
        await self.notify_telegram(
            f"New intake submission!\n"
            f"Customer: {task.customer_name or 'Unknown'}\n"
            f"Type: {project_type}\n"
            f"Routed to: {business}\n"
            f"Description: {task.description[:200]}"
        )

        task.state = TaskState.COMPLETED
        task.result = f"Classified as {project_type}, routed to {business}"
        task.actions.append(DeskAction(action="completed", detail=task.result))
        return task

    def get_status(self) -> dict:
        return {
            "desk_id": self.desk_id,
            "agent": self.agent_name,
            "active_tasks": len(self.active_tasks),
            "completed_today": len(self.completed_tasks),
            "capabilities": self.capabilities,
        }
