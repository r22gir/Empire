"""
ForgeDesk — WorkroomForge AI desk for custom window treatments.
PRIORITY 1: Handles quoting, customer follow-up, scheduling, measurements.
Integrates with WorkroomForge AI vision APIs for measurement, design, and analysis.
"""
import logging
import httpx
from datetime import datetime
from .base_desk import BaseDesk, DeskTask, DeskAction, TaskPriority, TaskState
from app.config.business_config import biz

logger = logging.getLogger("max.desks.forge")

# Thresholds for auto-escalation (from business config)
QUOTE_ESCALATION_THRESHOLD = biz.quote_escalation_threshold
FOLLOWUP_DAYS_OVERDUE = biz.followup_days_overdue


class ForgeDesk(BaseDesk):
    desk_id = "forge"
    desk_name = "ForgeDesk (WorkroomForge)"
    agent_name = "Kai"
    desk_description = (
        "Handles WorkroomForge operations: quote generation, customer follow-up, "
        "appointment scheduling, measurement tracking, and production coordination. "
        "Custom window treatments — drapes, shades, cornices, valances, bedding, upholstery."
    )
    capabilities = [
        "quote_generation",
        "customer_followup",
        "appointment_scheduling",
        "measurement_tracking",
        "fabric_lookup",
        "pricing_calculation",
        "production_status",
        "installation_scheduling",
        "ai_vision_measure",
        "ai_vision_mockup",
        "ai_vision_outline",
        "ai_vision_upholstery",
    ]

    # WorkroomForge API base (port 3001)
    WORKROOM_API = "http://localhost:3001/api"

    # WorkroomForge pricing constants (from business config)
    FABRIC_MARKUP = biz.fabric_markup
    LABOR_RATE = biz.labor_rate
    DC_TAX_RATE = biz.tax_rate

    def __init__(self):
        super().__init__()
        self.pending_followups: list[dict] = []
        self.pending_reminders: list[dict] = []

    async def _handle_task(self, task: DeskTask) -> DeskTask:
        """Route task to the appropriate handler based on content."""
        await self.accept_task(task)

        title_lower = task.title.lower()
        desc_lower = task.description.lower()
        combined = f"{title_lower} {desc_lower}"

        try:
            # Route to specific handler
            if any(w in combined for w in ["quote", "estimate", "price", "pricing", "cost"]):
                return await self._handle_quote(task)
            elif any(w in combined for w in ["follow up", "followup", "follow-up", "check in"]):
                return await self._handle_followup(task)
            elif any(w in combined for w in ["schedule", "appointment", "visit", "install"]):
                return await self._handle_scheduling(task)
            elif any(w in combined for w in ["measure", "measurement", "dimensions", "window size"]):
                return await self._handle_measurement(task)
            elif any(w in combined for w in ["fabric", "material", "supplier"]):
                return await self._handle_fabric_lookup(task)
            elif any(w in combined for w in ["mockup", "design mockup", "design proposal"]):
                return await self._handle_ai_vision(task, "mockup")
            elif any(w in combined for w in ["outline", "dimensional", "window outline"]):
                return await self._handle_ai_vision(task, "outline")
            elif any(w in combined for w in ["upholster", "sofa", "couch", "chair reupholster"]):
                return await self._handle_ai_vision(task, "upholstery")
            elif any(w in combined for w in ["ai measure", "photo measure", "vision measure"]):
                return await self._handle_ai_vision(task, "measure")
            elif any(w in combined for w in ["complaint", "issue", "problem", "unhappy", "angry"]):
                if task.source != "founder":
                    return await self.escalate(task, "Customer complaint — needs founder attention")
            else:
                return await self._handle_general(task)
        except Exception as e:
            logger.error(f"ForgeDesk task failed: {e}")
            return await self.fail_task(task, str(e))

    async def _handle_quote(self, task: DeskTask) -> DeskTask:
        """Generate or process a quote."""
        task.actions.append(DeskAction(
            action="quote_analysis",
            detail="Analyzing quote request for treatment type, fabric, and dimensions",
        ))

        # Extract customer and amount if mentioned
        amount_mentioned = self._extract_dollar_amount(task.description)

        # Escalate large quotes (skip if founder-originated — don't escalate back to the founder)
        if amount_mentioned and amount_mentioned > QUOTE_ESCALATION_THRESHOLD and task.source != "founder":
            return await self.escalate(
                task,
                f"Quote over ${QUOTE_ESCALATION_THRESHOLD:,} (estimated ${amount_mentioned:,.0f}) — needs founder approval"
            )

        # Check if this is a new customer (escalate for approval, skip for founder)
        if task.customer_name and self._is_new_customer(task.customer_name) and task.source != "founder":
            return await self.escalate(
                task,
                f"New customer '{task.customer_name}' — needs founder approval before quoting"
            )

        # Process quote
        result = self._build_quote_response(task)
        task.actions.append(DeskAction(
            action="quote_generated",
            detail=result,
        ))

        # Schedule follow-up reminder
        self.pending_followups.append({
            "task_id": task.id,
            "customer": task.customer_name or "Unknown",
            "type": "quote_followup",
            "created": datetime.utcnow().isoformat(),
            "followup_in_days": 3,
        })

        return await self.complete_task(task, result)

    async def _handle_followup(self, task: DeskTask) -> DeskTask:
        """Handle customer follow-up tasks."""
        task.actions.append(DeskAction(
            action="followup_check",
            detail=f"Checking follow-up status for {task.customer_name or 'customer'}",
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
            f"{'History: ' + customer_context if customer_context else 'No prior history found.'} "
            f"Recommended: Send status update and check satisfaction."
        )

        return await self.complete_task(task, result)

    async def _handle_scheduling(self, task: DeskTask) -> DeskTask:
        """Handle appointment/scheduling requests."""
        task.actions.append(DeskAction(
            action="scheduling",
            detail="Processing scheduling request",
        ))

        # Installation scheduling needs founder confirmation (skip if founder is the one asking)
        if "install" in task.description.lower() and task.source != "founder":
            return await self.escalate(
                task,
                "Installation scheduling requires founder confirmation of date and crew availability"
            )

        result = (
            f"Scheduling request logged for {task.customer_name or 'customer'}. "
            f"Details: {task.description[:200]}. "
            f"Recommended: Confirm availability and send calendar invite."
        )

        self.pending_reminders.append({
            "task_id": task.id,
            "type": "appointment_reminder",
            "customer": task.customer_name or "Unknown",
            "created": datetime.utcnow().isoformat(),
        })

        return await self.complete_task(task, result)

    async def _handle_measurement(self, task: DeskTask) -> DeskTask:
        """Handle measurement tracking."""
        task.actions.append(DeskAction(
            action="measurement_log",
            detail="Recording measurement data",
        ))

        # Log measurements to brain
        self._log_to_brain(
            f"Measurement recorded: {task.description[:200]}",
            importance=6,
            tags=["desk", "forge", "measurement", task.customer_name or "unknown"],
        )

        result = (
            f"Measurements logged. {task.description[:200]}. "
            f"Standard workflow: Verify → Select fabric → Calculate yardage → Price labor → Add 6% DC tax."
        )

        return await self.complete_task(task, result)

    async def _handle_fabric_lookup(self, task: DeskTask) -> DeskTask:
        """Handle fabric/material inquiries."""
        task.actions.append(DeskAction(
            action="fabric_lookup",
            detail="Looking up fabric/material information",
        ))

        # Check brain knowledge base for supplier info
        supplier_info = ""
        if self.memory_store:
            try:
                kb = self.memory_store.get_knowledge("workroomforge", "supplier", "primary_suppliers")
                if kb:
                    supplier_info = f"Primary suppliers: {kb}"
            except Exception:
                supplier_info = "Primary suppliers: Kravet, Robert Allen, Fabricut, Schumacher, Duralee"

        result = (
            f"Fabric lookup processed. {supplier_info or 'Primary suppliers: Kravet, Robert Allen, Fabricut, Schumacher, Duralee'}. "
            f"Standard markup: {self.FABRIC_MARKUP}x wholesale. Query: {task.description[:150]}"
        )

        return await self.complete_task(task, result)

    async def _handle_ai_vision(self, task: DeskTask, vision_type: str) -> DeskTask:
        """Call WorkroomForge AI vision API (measure, mockup, outline, upholstery)."""
        task.actions.append(DeskAction(
            action=f"ai_vision_{vision_type}",
            detail=f"Calling WorkroomForge AI vision: {vision_type}",
        ))

        # Extract image URL from task description
        image_url = self._extract_image_url(task.description)
        if not image_url:
            return await self.complete_task(
                task,
                f"AI vision ({vision_type}) requires an image. "
                "Please upload or reference a window/room photo in the task description."
            )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {"imageUrl": image_url}
                if vision_type == "mockup":
                    payload["notes"] = task.description[:500]
                resp = await client.post(
                    f"{self.WORKROOM_API}/{vision_type}",
                    json=payload,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    result = f"AI Vision ({vision_type}) complete: {str(data)[:500]}"

                    # Log to brain for future reference
                    self._log_to_brain(
                        f"AI vision {vision_type} for {task.customer_name or 'customer'}: {result[:300]}",
                        importance=7,
                        tags=["desk", "forge", "ai_vision", vision_type],
                    )

                    task.actions.append(DeskAction(
                        action=f"ai_vision_{vision_type}_complete",
                        detail=result[:200],
                        success=True,
                    ))
                    return await self.complete_task(task, result)
                else:
                    error = f"WorkroomForge API error: {resp.status_code}"
                    return await self.fail_task(task, error)
        except httpx.ConnectError:
            return await self.fail_task(
                task,
                "WorkroomForge (port 3001) is not running. Start it with: cd ~/empire-repo/workroomforge && npm run dev"
            )
        except Exception as e:
            return await self.fail_task(task, f"AI vision failed: {e}")

    def _extract_image_url(self, text: str) -> str | None:
        """Extract image URL or uploaded file reference from text."""
        import re
        # Direct URL
        url_match = re.search(r'https?://[^\s]+\.(?:jpg|jpeg|png|webp|gif)', text, re.IGNORECASE)
        if url_match:
            return url_match.group(0)
        # Uploaded file reference
        file_match = re.search(r'(?:uploads?/images?/|file:?\s*)(\S+\.(?:jpg|jpeg|png|webp|gif))', text, re.IGNORECASE)
        if file_match:
            return f"http://localhost:8000/api/v1/files/view/images/{file_match.group(1)}"
        return None

    async def _handle_general(self, task: DeskTask) -> DeskTask:
        """Handle general WorkroomForge tasks."""
        task.actions.append(DeskAction(
            action="general_processing",
            detail="Processing general WorkroomForge task",
        ))

        result = f"Task processed: {task.title}. Details logged. {task.description[:200]}"
        return await self.complete_task(task, result)

    def _extract_dollar_amount(self, text: str) -> float | None:
        """Try to extract a dollar amount from text."""
        import re
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

    def _is_new_customer(self, name: str) -> bool:
        """Check if customer exists in brain memory."""
        if not self.memory_store:
            return False  # Can't check, don't block
        try:
            results = self.memory_store.search_memories(query=name, category="customer", limit=1)
            return len(results) == 0
        except Exception:
            return False

    def _build_quote_response(self, task: DeskTask) -> str:
        """Build a structured quote response."""
        return (
            f"Quote workflow initiated for {task.customer_name or 'customer'}. "
            f"Process: Measure → Select fabric → Calculate yardage → "
            f"Price labor (${self.LABOR_RATE}/hr) → Apply {self.FABRIC_MARKUP}x fabric markup → "
            f"Add {self.DC_TAX_RATE*100:.0f}% DC tax → Present quote. "
            f"Terms: 50% deposit at approval, balance at installation. "
            f"3-day follow-up scheduled."
        )

    async def report_status(self) -> dict:
        """Extended status with WorkroomForge-specific info."""
        base = await super().report_status()
        base["pending_followups"] = len(self.pending_followups)
        base["pending_reminders"] = len(self.pending_reminders)
        return base

    def get_briefing_section(self) -> str:
        """Extended briefing with follow-ups and reminders."""
        base = super().get_briefing_section()
        extras = []
        if self.pending_followups:
            extras.append(f"- {len(self.pending_followups)} pending follow-up(s)")
        if self.pending_reminders:
            extras.append(f"- {len(self.pending_reminders)} pending reminder(s)")
        if extras:
            base += "\n" + "\n".join(extras)
        return base
