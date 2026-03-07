"""
SupportDesk — Customer support and ticket management.
Absorbs: legacy SupportBot (domains) + standalone SupportBot (auto-responses, escalation).
"""
import logging
from datetime import datetime
from .base_desk import BaseDesk, DeskTask, DeskAction, TaskPriority

logger = logging.getLogger("max.desks.support")

# Escalation thresholds
MAX_OPEN_TICKETS_BEFORE_ALERT = 10
REPEAT_COMPLAINT_THRESHOLD = 3


class SupportDesk(BaseDesk):
    desk_id = "support"
    desk_name = "SupportDesk"
    agent_name = "Luna"
    desk_description = (
        "Handles customer support: ticket triage, auto-responses for common issues, "
        "warranty claims, complaint resolution, service scheduling, and satisfaction tracking. "
        "Professional tone — always acknowledge, explain resolution, set timelines."
    )
    capabilities = [
        "ticket_management",
        "auto_response",
        "warranty_claims",
        "complaint_resolution",
        "service_scheduling",
        "satisfaction_tracking",
        "knowledge_base_lookup",
        "order_cross_reference",
    ]

    # Auto-responses ported from standalone SupportBot
    AUTO_RESPONSES = {
        "shipping": "Your order has been shipped. Please check your tracking number in your order confirmation email.",
        "refund": "We have initiated your refund. It typically takes 3-5 business days to process.",
        "cancel": "Your cancellation request has been received and is being processed. You will receive confirmation shortly.",
        "invoice": "Your invoice has been emailed to the address on file. Please check your spam folder if not received.",
        "tracking": "Your tracking information has been sent to your email. Please allow 24 hours for tracking updates to appear.",
        "warranty": "Your warranty claim has been logged. Our team will review and respond within 2 business days.",
    }

    # Common drapery issues for smart routing
    DRAPERY_ISSUES = {
        "uneven hem": "Schedule a service visit — seamstress can adjust on-site (typically 30 min).",
        "cord malfunction": "Check if cord is tangled or jammed. If mechanism is broken, schedule replacement visit.",
        "motor": "Check remote batteries first. If motor is unresponsive, schedule technician visit.",
        "fading": "Document with photos. Check warranty coverage — most fabrics warranted 3 years against fading.",
        "hardware loose": "Tighten mounting brackets. If wall anchors have failed, schedule reinstallation.",
    }

    def __init__(self):
        super().__init__()
        self.open_tickets: list[dict] = []
        self.resolved_tickets: list[dict] = []

    async def handle_task(self, task: DeskTask) -> DeskTask:
        """Route support task to appropriate handler."""
        await self.accept_task(task)

        combined = f"{task.title} {task.description}".lower()

        try:
            if any(w in combined for w in ["complaint", "unhappy", "angry", "terrible", "worst"]):
                return await self._handle_complaint(task)
            elif any(w in combined for w in ["warranty", "warranty claim", "defective"]):
                return await self._handle_warranty(task)
            elif any(w in combined for w in ["schedule service", "repair", "fix", "broken"]):
                return await self._handle_service_request(task)
            elif any(w in combined for w in ["ticket", "support request", "help"]):
                return await self._handle_ticket(task)
            else:
                # Try auto-response first, then general handling
                auto = self._try_auto_response(combined)
                if auto:
                    return await self._handle_auto_response(task, auto)
                return await self._handle_ticket(task)
        except Exception as e:
            logger.error(f"SupportDesk task failed: {e}")
            return await self.fail_task(task, str(e))

    async def _handle_ticket(self, task: DeskTask) -> DeskTask:
        """Triage and process a support ticket."""
        task.actions.append(DeskAction(
            action="ticket_triage",
            detail=f"Triaging ticket from {task.customer_name or 'customer'}",
        ))

        # Check for auto-response match
        combined = f"{task.title} {task.description}".lower()
        auto = self._try_auto_response(combined)

        if auto:
            return await self._handle_auto_response(task, auto)

        # Check for drapery-specific issues
        drapery_advice = self._check_drapery_issues(combined)

        # Log ticket
        ticket = {
            "task_id": task.id,
            "customer": task.customer_name or "Unknown",
            "subject": task.title,
            "status": "open",
            "created": datetime.utcnow().isoformat(),
            "priority": task.priority.value,
        }
        self.open_tickets.append(ticket)

        # Alert if too many open tickets
        if len(self.open_tickets) >= MAX_OPEN_TICKETS_BEFORE_ALERT:
            await self.notify_telegram(
                f"Support queue at {len(self.open_tickets)} open tickets — may need attention"
            )

        result = (
            f"Ticket created for {task.customer_name or 'customer'}: {task.title}. "
            f"{'Suggestion: ' + drapery_advice + ' ' if drapery_advice else ''}"
            f"Priority: {task.priority.value}. Status: open. "
            f"Open tickets: {len(self.open_tickets)}."
        )

        self._log_to_brain(
            f"Support ticket: {task.title} from {task.customer_name or 'Unknown'}",
            importance=5,
            tags=["desk", "support", "ticket"],
        )

        return await self.complete_task(task, result)

    async def _handle_auto_response(self, task: DeskTask, response: str) -> DeskTask:
        """Handle with auto-response (ported from SupportBot)."""
        task.actions.append(DeskAction(
            action="auto_response",
            detail=f"Auto-responded: {response[:100]}",
        ))

        result = (
            f"Auto-response sent to {task.customer_name or 'customer'}: {response} "
            f"Ticket auto-resolved."
        )

        self._log_to_brain(
            f"Auto-responded to {task.customer_name or 'Unknown'}: {task.title}",
            importance=3,
            tags=["desk", "support", "auto_response"],
        )

        return await self.complete_task(task, result)

    async def _handle_complaint(self, task: DeskTask) -> DeskTask:
        """Handle customer complaints — always escalate to founder."""
        task.actions.append(DeskAction(
            action="complaint_received",
            detail=f"Complaint from {task.customer_name or 'customer'} flagged for escalation",
        ))

        # Check for repeat complaints
        repeat_count = 0
        if task.customer_name and self.memory_store:
            try:
                memories = self.memory_store.search_memories(
                    query=f"complaint {task.customer_name}",
                    category="desk_action",
                    limit=10,
                )
                repeat_count = len(memories)
            except Exception:
                pass

        severity = "REPEAT" if repeat_count >= REPEAT_COMPLAINT_THRESHOLD else "NEW"

        # Notify via Telegram
        await self.notify_telegram(
            f"Customer complaint ({severity})\n"
            f"Customer: {task.customer_name or 'Unknown'}\n"
            f"Issue: {task.title}\n"
            f"Details: {task.description[:200]}"
        )

        self._log_to_brain(
            f"Complaint ({severity}) from {task.customer_name or 'Unknown'}: {task.title}",
            importance=9,
            tags=["desk", "support", "complaint", severity.lower()],
        )

        return await self.escalate(
            task,
            f"Customer complaint ({severity}) from {task.customer_name or 'Unknown'} — "
            f"needs founder response. {f'Repeat offender ({repeat_count} prior).' if repeat_count else ''}"
        )

    async def _handle_warranty(self, task: DeskTask) -> DeskTask:
        """Handle warranty claims."""
        task.actions.append(DeskAction(
            action="warranty_claim",
            detail="Processing warranty claim",
        ))

        result = (
            f"Warranty claim logged for {task.customer_name or 'customer'}. "
            f"Issue: {task.description[:200]}. "
            f"Next steps: Verify purchase date, check warranty coverage (standard 1 year parts, "
            f"3 years fabric fading), schedule inspection if needed."
        )

        self._log_to_brain(
            f"Warranty claim: {task.customer_name or 'Unknown'} — {task.title}",
            importance=6,
            tags=["desk", "support", "warranty"],
        )

        return await self.complete_task(task, result)

    async def _handle_service_request(self, task: DeskTask) -> DeskTask:
        """Handle service/repair requests."""
        task.actions.append(DeskAction(
            action="service_request",
            detail="Processing service request",
        ))

        combined = f"{task.title} {task.description}".lower()
        drapery_advice = self._check_drapery_issues(combined)

        # Urgent service requests escalate
        if task.priority in (TaskPriority.URGENT, TaskPriority.HIGH):
            return await self.escalate(
                task,
                f"Urgent service request from {task.customer_name or 'customer'}: {task.title}"
            )

        result = (
            f"Service request logged for {task.customer_name or 'customer'}. "
            f"{'Diagnosis: ' + drapery_advice + ' ' if drapery_advice else ''}"
            f"Details: {task.description[:200]}. "
            f"Next: Schedule service visit and confirm with customer."
        )

        return await self.complete_task(task, result)

    def _try_auto_response(self, text: str) -> str | None:
        """Check if text matches auto-response keywords."""
        for keyword, response in self.AUTO_RESPONSES.items():
            if keyword in text:
                return response
        return None

    def _check_drapery_issues(self, text: str) -> str | None:
        """Check for known drapery issues and return advice."""
        for issue, advice in self.DRAPERY_ISSUES.items():
            if issue in text:
                return advice
        return None

    async def report_status(self) -> dict:
        base = await super().report_status()
        base["open_tickets"] = len(self.open_tickets)
        base["resolved_today"] = len([
            t for t in self.resolved_tickets
            if t.get("resolved", "")[:10] == datetime.utcnow().strftime("%Y-%m-%d")
        ])
        return base

    def get_briefing_section(self) -> str:
        base = super().get_briefing_section()
        extras = []
        if self.open_tickets:
            extras.append(f"- {len(self.open_tickets)} open ticket(s)")
        if extras:
            base += "\n" + "\n".join(extras)
        return base
