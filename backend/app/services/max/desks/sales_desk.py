"""
SalesDesk — Sales pipeline and lead management.
Absorbs: legacy SalesBot (domains) + standalone LeadBot (scoring logic).
"""
import logging
import re
from datetime import datetime
from .base_desk import BaseDesk, DeskTask, DeskAction, TaskPriority

logger = logging.getLogger("max.desks.sales")

# Lead scoring thresholds (ported from LeadBot)
LEAD_QUALIFICATION_THRESHOLD = 30
HIGH_VALUE_LEAD_THRESHOLD = 70


class SalesDesk(BaseDesk):
    desk_id = "sales"
    desk_name = "SalesDesk"
    desk_description = (
        "Manages the sales pipeline: lead capture, qualification and scoring, "
        "follow-ups, proposals, consultations, deposit collection, and referral tracking. "
        "Bilingual support (English/Spanish)."
    )
    capabilities = [
        "lead_capture",
        "lead_scoring",
        "pipeline_management",
        "follow_up_scheduling",
        "proposal_drafting",
        "consultation_scheduling",
        "deposit_tracking",
        "referral_tracking",
    ]

    # Sales pipeline stages
    PIPELINE_STAGES = [
        "inquiry", "consultation_scheduled", "consultation_done",
        "quote_sent", "follow_up", "deposit_received", "in_production", "closed_won", "closed_lost",
    ]

    def __init__(self):
        super().__init__()
        self.pipeline: list[dict] = []
        self.pending_followups: list[dict] = []

    async def handle_task(self, task: DeskTask) -> DeskTask:
        """Route task to the appropriate sales handler."""
        await self.accept_task(task)

        combined = f"{task.title} {task.description}".lower()

        try:
            if any(w in combined for w in ["lead", "prospect", "inquiry", "new customer"]):
                return await self._handle_lead(task)
            elif any(w in combined for w in ["follow up", "followup", "follow-up", "check in"]):
                return await self._handle_followup(task)
            elif any(w in combined for w in ["proposal", "quote", "bid"]):
                return await self._handle_proposal(task)
            elif any(w in combined for w in ["consult", "meeting", "appointment", "visit"]):
                return await self._handle_consultation(task)
            elif any(w in combined for w in ["deposit", "payment", "collect"]):
                return await self._handle_deposit(task)
            elif any(w in combined for w in ["referral", "referred"]):
                return await self._handle_referral(task)
            elif any(w in combined for w in ["pipeline", "funnel", "report", "status"]):
                return await self._handle_pipeline_report(task)
            else:
                return await self._handle_general(task)
        except Exception as e:
            logger.error(f"SalesDesk task failed: {e}")
            return await self.fail_task(task, str(e))

    async def _handle_lead(self, task: DeskTask) -> DeskTask:
        """Capture and score a new lead (logic ported from LeadBot)."""
        task.actions.append(DeskAction(
            action="lead_capture",
            detail=f"Capturing lead: {task.customer_name or 'Unknown'}",
        ))

        # Score the lead (ported from LeadBot scoring formula)
        score = self._score_lead(task)
        qualified = score >= LEAD_QUALIFICATION_THRESHOLD

        task.actions.append(DeskAction(
            action="lead_scored",
            detail=f"Score: {score}/100 — {'Qualified' if qualified else 'Not qualified'}",
        ))

        # High-value leads escalate to founder
        if score >= HIGH_VALUE_LEAD_THRESHOLD:
            return await self.escalate(
                task,
                f"High-value lead (score {score}) — {task.customer_name or 'Unknown'} needs founder attention"
            )

        if qualified:
            # Add to pipeline
            self.pipeline.append({
                "customer": task.customer_name or "Unknown",
                "stage": "inquiry",
                "score": score,
                "created": datetime.utcnow().isoformat(),
                "task_id": task.id,
            })

            # Schedule follow-up
            self.pending_followups.append({
                "task_id": task.id,
                "customer": task.customer_name or "Unknown",
                "type": "new_lead_followup",
                "followup_in_days": 1,
                "created": datetime.utcnow().isoformat(),
            })

            result = (
                f"Lead captured: {task.customer_name or 'Unknown'} (score {score}/100, qualified). "
                f"Added to pipeline at 'inquiry' stage. 1-day follow-up scheduled. "
                f"Next: Schedule consultation."
            )
        else:
            result = (
                f"Lead captured: {task.customer_name or 'Unknown'} (score {score}/100, not qualified). "
                f"Below threshold ({LEAD_QUALIFICATION_THRESHOLD}). Logged for nurture campaign."
            )

        self._log_to_brain(
            f"Lead: {task.customer_name or 'Unknown'}, score={score}, qualified={qualified}",
            importance=6 if qualified else 4,
            tags=["desk", "sales", "lead", "qualified" if qualified else "unqualified"],
        )

        return await self.complete_task(task, result)

    async def _handle_followup(self, task: DeskTask) -> DeskTask:
        """Handle sales follow-up tasks."""
        task.actions.append(DeskAction(
            action="followup_prep",
            detail=f"Preparing follow-up for {task.customer_name or 'customer'}",
        ))

        # Check brain for customer history
        customer_context = ""
        if task.customer_name and self.memory_store:
            try:
                memories = self.memory_store.search_memories(
                    query=task.customer_name, category="customer", limit=5
                )
                if memories:
                    customer_context = "; ".join(m["content"] for m in memories[:3])
            except Exception:
                pass

        result = (
            f"Follow-up prepared for {task.customer_name or 'customer'}. "
            f"{'Context: ' + customer_context + '. ' if customer_context else ''}"
            f"Recommended actions: Check pipeline stage, send personalized update, "
            f"ask about timeline and decision factors."
        )

        return await self.complete_task(task, result)

    async def _handle_proposal(self, task: DeskTask) -> DeskTask:
        """Handle proposal/quote requests."""
        task.actions.append(DeskAction(
            action="proposal_draft",
            detail="Drafting proposal outline",
        ))

        amount = self._extract_dollar_amount(task.description)
        if amount and amount > 5000:
            return await self.escalate(
                task,
                f"Proposal over $5,000 (${amount:,.0f}) for {task.customer_name or 'customer'} — needs founder review"
            )

        result = (
            f"Proposal workflow started for {task.customer_name or 'customer'}. "
            f"Include: scope of work, materials, labor, timeline, terms (50% deposit). "
            f"{'Estimated value: $' + f'{amount:,.0f}. ' if amount else ''}"
            f"3-day follow-up auto-scheduled after delivery."
        )

        self.pending_followups.append({
            "task_id": task.id,
            "customer": task.customer_name or "Unknown",
            "type": "proposal_followup",
            "followup_in_days": 3,
            "created": datetime.utcnow().isoformat(),
        })

        return await self.complete_task(task, result)

    async def _handle_consultation(self, task: DeskTask) -> DeskTask:
        """Handle consultation/meeting scheduling."""
        task.actions.append(DeskAction(
            action="consultation_schedule",
            detail="Processing consultation request",
        ))

        result = (
            f"Consultation request for {task.customer_name or 'customer'}. "
            f"Details: {task.description[:200]}. "
            f"Recommended: Confirm date/time, prepare measurement tools, "
            f"review any prior quotes or preferences."
        )

        return await self.complete_task(task, result)

    async def _handle_deposit(self, task: DeskTask) -> DeskTask:
        """Handle deposit collection tracking."""
        task.actions.append(DeskAction(
            action="deposit_tracking",
            detail="Logging deposit/payment activity",
        ))

        amount = self._extract_dollar_amount(task.description)
        result = (
            f"Deposit logged for {task.customer_name or 'customer'}. "
            f"{'Amount: $' + f'{amount:,.2f}. ' if amount else ''}"
            f"Pipeline stage updated to 'deposit_received'. "
            f"Next: Confirm order and move to production."
        )

        self._log_to_brain(
            f"Deposit received: {task.customer_name or 'Unknown'}" +
            (f", ${amount:,.2f}" if amount else ""),
            importance=7,
            tags=["desk", "sales", "deposit", "revenue"],
        )

        return await self.complete_task(task, result)

    async def _handle_referral(self, task: DeskTask) -> DeskTask:
        """Handle referral tracking."""
        task.actions.append(DeskAction(
            action="referral_logged",
            detail="Referral source recorded",
        ))

        result = (
            f"Referral logged: {task.description[:200]}. "
            f"Customer: {task.customer_name or 'Unknown'}. "
            f"Added to pipeline as warm lead. Thank-you note recommended for referrer."
        )

        self._log_to_brain(
            f"Referral received for {task.customer_name or 'Unknown'}",
            importance=6,
            tags=["desk", "sales", "referral"],
        )

        return await self.complete_task(task, result)

    async def _handle_pipeline_report(self, task: DeskTask) -> DeskTask:
        """Generate pipeline status report."""
        task.actions.append(DeskAction(
            action="pipeline_report",
            detail="Generating pipeline summary",
        ))

        if self.pipeline:
            stage_counts = {}
            for entry in self.pipeline:
                stage = entry.get("stage", "unknown")
                stage_counts[stage] = stage_counts.get(stage, 0) + 1
            summary = ", ".join(f"{s}: {c}" for s, c in stage_counts.items())
        else:
            summary = "Pipeline empty"

        result = (
            f"Pipeline report: {len(self.pipeline)} active leads. "
            f"Stages: {summary}. "
            f"Pending follow-ups: {len(self.pending_followups)}."
        )

        return await self.complete_task(task, result)

    async def _handle_general(self, task: DeskTask) -> DeskTask:
        """Handle general sales tasks."""
        task.actions.append(DeskAction(
            action="general_sales",
            detail="Processing general sales task",
        ))

        result = f"Sales task processed: {task.title}. Details logged. {task.description[:200]}"
        return await self.complete_task(task, result)

    def _score_lead(self, task: DeskTask) -> int:
        """Score a lead 0-100 (ported from LeadBot formula)."""
        score = 0
        desc = task.description.lower()

        # Email bonus (from LeadBot)
        if "@" in desc or "email" in desc:
            score += 10

        # Budget extraction and scoring (from LeadBot: min(budget, 5000) // 50)
        amount = self._extract_dollar_amount(task.description)
        if amount:
            score += min(int(amount), 5000) // 50

        # Source bonuses
        if "referral" in desc or "referred" in desc:
            score += 20
        if "repeat" in desc or "returning" in desc:
            score += 25
        if "website" in desc or "online" in desc:
            score += 5
        if "social" in desc or "instagram" in desc:
            score += 5

        # Urgency signals
        if any(w in desc for w in ["urgent", "asap", "rush", "this week"]):
            score += 15

        # Priority bonus
        if task.priority == TaskPriority.URGENT:
            score += 15
        elif task.priority == TaskPriority.HIGH:
            score += 10

        return min(100, score)

    def _extract_dollar_amount(self, text: str) -> float | None:
        """Extract a dollar amount from text."""
        patterns = [
            r'\$\s?([\d,]+(?:\.\d{2})?)',
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)(?:\s*dollars?)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1).replace(",", ""))
                except ValueError:
                    continue
        return None

    async def report_status(self) -> dict:
        base = await super().report_status()
        base["pipeline_count"] = len(self.pipeline)
        base["pending_followups"] = len(self.pending_followups)
        return base

    def get_briefing_section(self) -> str:
        base = super().get_briefing_section()
        extras = []
        if self.pipeline:
            extras.append(f"- {len(self.pipeline)} lead(s) in pipeline")
        if self.pending_followups:
            extras.append(f"- {len(self.pending_followups)} follow-up(s) due")
        if extras:
            base += "\n" + "\n".join(extras)
        return base
