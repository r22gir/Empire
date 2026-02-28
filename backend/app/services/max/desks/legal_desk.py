"""
LegalDesk — Contracts, compliance, insurance, and legal document management.
Source: DB desk config (legal) — no legacy bot equivalent.
"""
import logging
from datetime import datetime
from .base_desk import BaseDesk, DeskTask, DeskAction

logger = logging.getLogger("max.desks.legal")


class LegalDesk(BaseDesk):
    desk_id = "legal"
    desk_name = "LegalDesk"
    desk_description = (
        "Manages legal documents: client contracts, vendor agreements, installer "
        "subcontractor agreements, terms and conditions, warranty policies, and "
        "compliance tracking. Standard terms: 50% deposit, cancellation policies, "
        "liability clauses. Always recommends professional legal review."
    )
    capabilities = [
        "contract_drafting",
        "terms_review",
        "compliance_tracking",
        "expiration_alerts",
        "vendor_agreements",
        "warranty_policies",
        "insurance_tracking",
    ]

    def __init__(self):
        super().__init__()
        self.active_contracts: list[dict] = []
        self.expiring_soon: list[dict] = []

    async def handle_task(self, task: DeskTask) -> DeskTask:
        await self.accept_task(task)
        combined = f"{task.title} {task.description}".lower()

        try:
            if any(w in combined for w in ["contract", "agreement", "draft"]):
                return await self._handle_contract(task)
            elif any(w in combined for w in ["terms", "conditions", "policy", "policies"]):
                return await self._handle_terms(task)
            elif any(w in combined for w in ["compliance", "regulation", "license", "permit"]):
                return await self._handle_compliance(task)
            elif any(w in combined for w in ["insurance", "liability", "bond"]):
                return await self._handle_insurance(task)
            elif any(w in combined for w in ["expir", "renew", "renewal"]):
                return await self._handle_expiration(task)
            elif any(w in combined for w in ["llc", "business entity", "incorporation"]):
                return await self._handle_entity(task)
            else:
                return await self._handle_general(task)
        except Exception as e:
            logger.error(f"LegalDesk task failed: {e}")
            return await self.fail_task(task, str(e))

    async def _handle_contract(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="contract_draft", detail="Drafting contract"))

        self.active_contracts.append({
            "task_id": task.id,
            "customer": task.customer_name or "Unknown",
            "type": "client_contract",
            "status": "draft",
            "date": datetime.utcnow().isoformat(),
        })

        result = (
            f"Contract drafted for {task.customer_name or 'client'}. "
            f"Standard terms: 50% deposit at approval, balance at installation. "
            f"Cancellation: Full refund if cancelled before fabric order, 50% after. "
            f"Warranty: 1 year workmanship, fabric per manufacturer. "
            f"NOTE: Recommend professional legal review before use."
        )

        self._log_to_brain(
            f"Contract: {task.customer_name or 'Unknown'} — {task.title}",
            importance=7,
            tags=["desk", "legal", "contract"],
        )
        return await self.complete_task(task, result)

    async def _handle_terms(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="terms_review", detail="Reviewing terms and conditions"))

        result = (
            f"Terms review: {task.title}. "
            f"Key clauses to include: payment schedule, cancellation policy, "
            f"warranty scope, liability limitations, change order process, "
            f"timeline estimates (not guarantees). "
            f"Details: {task.description[:200]}."
        )
        return await self.complete_task(task, result)

    async def _handle_compliance(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="compliance_check", detail="Checking compliance requirements"))

        result = (
            f"Compliance task: {task.title}. "
            f"Track: business licenses, contractor licenses, tax registrations, "
            f"insurance certificates, building permits (if applicable). "
            f"Details: {task.description[:200]}."
        )
        return await self.complete_task(task, result)

    async def _handle_insurance(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="insurance_review", detail="Processing insurance task"))

        result = (
            f"Insurance task: {task.title}. "
            f"Required coverage: general liability, workers' comp (if employees), "
            f"commercial auto (delivery/install vehicles), professional liability. "
            f"Verify all contractors carry their own insurance. "
            f"Details: {task.description[:200]}."
        )
        return await self.complete_task(task, result)

    async def _handle_expiration(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="expiration_alert", detail="Checking expirations"))

        await self.notify_telegram(
            f"Expiration alert: {task.title}\n{task.description[:200]}"
        )

        result = (
            f"Expiration check: {task.title}. "
            f"Review: contract end dates, insurance renewals, license expirations, "
            f"certification renewals. Set 30-day advance reminders."
        )
        return await self.complete_task(task, result)

    async def _handle_entity(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="entity_management", detail="Processing business entity task"))

        result = (
            f"Business entity task: {task.title}. "
            f"Track: LLC annual reports, registered agent, operating agreement updates, "
            f"EIN documentation, state registrations. "
            f"Details: {task.description[:200]}."
        )
        return await self.complete_task(task, result)

    async def _handle_general(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="general_legal", detail="Processing legal task"))
        result = f"Legal task processed: {task.title}. {task.description[:200]}. NOTE: Recommend professional legal review."
        return await self.complete_task(task, result)

    async def report_status(self) -> dict:
        base = await super().report_status()
        base["active_contracts"] = len(self.active_contracts)
        base["expiring_soon"] = len(self.expiring_soon)
        return base
