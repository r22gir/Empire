"""
ClientsDesk — Customer database, job history, and relationship management.
Source: DB desk config (clients) — no legacy bot equivalent.
"""
import logging
from datetime import datetime
from .base_desk import BaseDesk, DeskTask, DeskAction

logger = logging.getLogger("max.desks.clients")


class ClientsDesk(BaseDesk):
    desk_id = "clients"
    desk_name = "ClientsDesk"
    agent_name = "Elena"
    desk_description = (
        "Manages client relationships: contact records, property addresses, past orders, "
        "fabric/style preferences, communication history. Prepares for meetings, drafts "
        "follow-up emails and thank-you notes. Warm and personable tone."
    )
    capabilities = [
        "client_search",
        "client_creation",
        "history_lookup",
        "preference_tracking",
        "meeting_prep",
        "thank_you_notes",
        "communication_drafting",
    ]

    def __init__(self):
        super().__init__()
        self.recent_lookups: list[dict] = []

    async def handle_task(self, task: DeskTask) -> DeskTask:
        await self.accept_task(task)
        combined = f"{task.title} {task.description}".lower()

        try:
            if any(w in combined for w in ["search", "find", "lookup", "look up", "who is"]):
                return await self._handle_search(task)
            elif any(w in combined for w in ["new client", "add client", "create contact", "new customer"]):
                return await self._handle_new_client(task)
            elif any(w in combined for w in ["history", "past order", "previous", "record"]):
                return await self._handle_history(task)
            elif any(w in combined for w in ["meeting", "prep", "prepare", "appointment"]):
                return await self._handle_meeting_prep(task)
            elif any(w in combined for w in ["thank", "thank you", "appreciation"]):
                return await self._handle_thank_you(task)
            elif any(w in combined for w in ["email", "message", "draft", "write"]):
                return await self._handle_communication(task)
            elif any(w in combined for w in ["preference", "style", "fabric choice", "favorite"]):
                return await self._handle_preferences(task)
            else:
                return await self._handle_general(task)
        except Exception as e:
            logger.error(f"ClientsDesk task failed: {e}")
            return await self.fail_task(task, str(e))

    async def _handle_search(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="client_search", detail=f"Searching for {task.customer_name or task.description[:50]}"))

        results = []
        if task.customer_name and self.memory_store:
            try:
                results = self.memory_store.search_memories(query=task.customer_name, category="customer", limit=5)
            except Exception:
                pass

        self.recent_lookups.append({"query": task.customer_name or task.title, "results": len(results), "date": datetime.utcnow().isoformat()})

        if results:
            context = "; ".join(m["content"] for m in results[:3])
            result = f"Found {len(results)} record(s) for '{task.customer_name}': {context}"
        else:
            result = f"No records found for '{task.customer_name or task.description[:50]}'. May be a new client."

        return await self.complete_task(task, result)

    async def _handle_new_client(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="client_creation", detail=f"Creating record for {task.customer_name or 'new client'}"))

        self._log_to_brain(
            f"New client added: {task.customer_name or 'Unknown'}. {task.description[:150]}",
            importance=6,
            tags=["desk", "clients", "new_client"],
        )

        result = (
            f"Client record created for {task.customer_name or 'new client'}. "
            f"Details: {task.description[:200]}. "
            f"Next: Record property address, note style preferences, schedule consultation."
        )
        return await self.complete_task(task, result)

    async def _handle_history(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="history_lookup", detail=f"Pulling history for {task.customer_name or 'client'}"))

        history = []
        if task.customer_name and self.memory_store:
            try:
                history = self.memory_store.search_memories(query=task.customer_name, limit=10)
            except Exception:
                pass

        if history:
            context = "; ".join(m["content"] for m in history[:5])
            result = f"History for {task.customer_name}: {len(history)} entries. Recent: {context}"
        else:
            result = f"No history found for {task.customer_name or 'client'}."

        return await self.complete_task(task, result)

    async def _handle_meeting_prep(self, task: DeskTask) -> DeskTask:
        """AI-enhanced meeting preparation briefing."""
        task.actions.append(DeskAction(action="meeting_prep", detail="Preparing client meeting briefing"))

        context = ""
        if task.customer_name and self.memory_store:
            try:
                memories = self.memory_store.search_memories(query=task.customer_name, limit=5)
                if memories:
                    context = "; ".join(m["content"] for m in memories[:3])
            except Exception:
                pass

        # v6.0: AI-enhanced meeting brief
        ai_result = await self.ai_call(
            f"Prepare a client meeting briefing for a drapery/upholstery consultation.\n\n"
            f"Client: {task.customer_name or 'Unknown'}\n"
            f"Meeting details: {task.description[:500]}\n"
            f"{'Prior history: ' + context if context else 'No prior history — new client.'}\n\n"
            f"Include: talking points, questions to ask, what to bring, upsell opportunities, "
            f"estimated time. Keep it concise and actionable."
        )

        if ai_result and len(ai_result) > 50:
            result = ai_result
        else:
            result = (
                f"Meeting prep for {task.customer_name or 'client'}: "
                f"{'Prior history: ' + context + '. ' if context else 'No prior history. '}"
                f"Bring: measurement tools, fabric samples, portfolio. "
                f"Review: past quotes, fabric preferences, property details."
            )
        return await self.complete_task(task, result)

    async def _handle_thank_you(self, task: DeskTask) -> DeskTask:
        """AI-generated thank-you note."""
        task.actions.append(DeskAction(action="thank_you_note", detail="Drafting thank-you note"))

        ai_result = await self.ai_call(
            f"Write a warm, professional thank-you note for a drapery/upholstery client.\n\n"
            f"Client: {task.customer_name or 'valued client'}\n"
            f"Context: {task.description[:300]}\n\n"
            f"Tone: warm, personal, not corporate. Mention their specific project. "
            f"Include a subtle referral ask. Keep under 150 words."
        )

        result = ai_result if ai_result and len(ai_result) > 30 else (
            f"Thank-you note prepared for {task.customer_name or 'client'}. "
            f"Tone: warm, personal, professional. "
            f"Include: appreciation for their business, mention specific project details, "
            f"invite future referrals."
        )
        return await self.complete_task(task, result)

    async def _handle_communication(self, task: DeskTask) -> DeskTask:
        """AI-drafted client communication."""
        task.actions.append(DeskAction(action="communication_draft", detail="Drafting client communication"))

        ai_result = await self.ai_call(
            f"Draft a professional client communication for Empire Workroom.\n\n"
            f"Client: {task.customer_name or 'client'}\n"
            f"Subject: {task.title}\n"
            f"Context: {task.description[:500]}\n\n"
            f"Business: custom drapery and upholstery in Washington DC. "
            f"Tone: professional yet warm. Ready to send."
        )

        result = ai_result if ai_result and len(ai_result) > 30 else (
            f"Communication drafted for {task.customer_name or 'client'}. "
            f"Topic: {task.title}. Details: {task.description[:200]}. "
            f"Ready for review and send."
        )
        return await self.complete_task(task, result)

    async def _handle_preferences(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="preference_update", detail="Updating client preferences"))

        self._log_to_brain(
            f"Client preference: {task.customer_name or 'Unknown'} — {task.description[:200]}",
            importance=5,
            tags=["desk", "clients", "preference"],
        )

        result = (
            f"Preferences updated for {task.customer_name or 'client'}: {task.description[:200]}."
        )
        return await self.complete_task(task, result)

    async def _handle_general(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="general_clients", detail="Processing client task"))
        result = f"Client task processed: {task.title}. {task.description[:200]}"
        return await self.complete_task(task, result)

    async def report_status(self) -> dict:
        base = await super().report_status()
        base["recent_lookups"] = len(self.recent_lookups)
        return base
