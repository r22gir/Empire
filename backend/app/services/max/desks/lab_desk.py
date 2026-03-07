"""
LabDesk — R&D sandbox for experimental AI features and prototyping.
Source: DB desk config (lab) — no legacy bot equivalent.
"""
import logging
from datetime import datetime
from .base_desk import BaseDesk, DeskTask, DeskAction

logger = logging.getLogger("max.desks.lab")


class LabDesk(BaseDesk):
    desk_id = "lab"
    desk_name = "LabDesk"
    agent_name = "Phoenix"
    desk_description = (
        "R&D Lab for testing new AI capabilities, prototyping features, and "
        "experimenting with integrations. More creative and exploratory — "
        "suggests automations, tests vision/voice features, brainstorms improvements. "
        "Nothing here affects production data."
    )
    capabilities = [
        "experiment_tracking",
        "prototype_management",
        "feature_testing",
        "vision_api_testing",
        "voice_testing",
        "automation_brainstorm",
        "sandbox_execution",
    ]

    def __init__(self):
        super().__init__()
        self.experiments: list[dict] = []

    async def handle_task(self, task: DeskTask) -> DeskTask:
        await self.accept_task(task)
        combined = f"{task.title} {task.description}".lower()

        try:
            if any(w in combined for w in ["experiment", "test", "try", "prototype"]):
                return await self._handle_experiment(task)
            elif any(w in combined for w in ["vision", "photo", "image", "camera"]):
                return await self._handle_vision_test(task)
            elif any(w in combined for w in ["voice", "tts", "speech", "audio"]):
                return await self._handle_voice_test(task)
            elif any(w in combined for w in ["automat", "workflow", "integration"]):
                return await self._handle_automation(task)
            elif any(w in combined for w in ["idea", "brainstorm", "suggest", "improve"]):
                return await self._handle_brainstorm(task)
            else:
                return await self._handle_general(task)
        except Exception as e:
            logger.error(f"LabDesk task failed: {e}")
            return await self.fail_task(task, str(e))

    async def _handle_experiment(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="experiment_start", detail=f"Starting experiment: {task.title}"))

        experiment = {
            "id": task.id,
            "name": task.title,
            "description": task.description[:300],
            "status": "running",
            "started": datetime.utcnow().isoformat(),
        }
        self.experiments.append(experiment)

        self._log_to_brain(
            f"Lab experiment started: {task.title}",
            importance=5,
            tags=["desk", "lab", "experiment"],
        )

        result = (
            f"Experiment started: {task.title}. "
            f"Sandbox mode — no production impact. "
            f"Details: {task.description[:200]}. "
            f"Total experiments: {len(self.experiments)}."
        )
        return await self.complete_task(task, result)

    async def _handle_vision_test(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="vision_test", detail="Testing vision/photo analysis"))

        result = (
            f"Vision test: {task.title}. "
            f"Available: xAI Vision API (via Grok), Ollama LLaVA (local, heavy on RAM). "
            f"NOTE: Ollama currently disabled to prevent crashes. "
            f"Use xAI Vision for photo analysis. "
            f"Details: {task.description[:200]}."
        )
        return await self.complete_task(task, result)

    async def _handle_voice_test(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="voice_test", detail="Testing voice/TTS features"))

        result = (
            f"Voice test: {task.title}. "
            f"TTS: edge-tts (free, no API key). "
            f"Endpoint: POST /api/v1/max/tts. "
            f"Details: {task.description[:200]}."
        )
        return await self.complete_task(task, result)

    async def _handle_automation(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="automation_design", detail="Designing automation workflow"))

        result = (
            f"Automation design: {task.title}. "
            f"Current automations: desk routing (keyword+LLM), Telegram notifications, "
            f"auto-responses (SupportDesk), lead scoring (SalesDesk). "
            f"Potential: scheduled desk briefings, auto-follow-ups, inventory alerts. "
            f"Details: {task.description[:200]}."
        )
        return await self.complete_task(task, result)

    async def _handle_brainstorm(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="brainstorm", detail="Brainstorming ideas"))

        result = (
            f"Brainstorm: {task.title}. "
            f"Ideas logged for review. The Lab desk is the place for wild ideas — "
            f"nothing here affects production. "
            f"Details: {task.description[:200]}."
        )

        self._log_to_brain(
            f"Lab idea: {task.title} — {task.description[:150]}",
            importance=4,
            tags=["desk", "lab", "idea", "brainstorm"],
        )
        return await self.complete_task(task, result)

    async def _handle_general(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="general_lab", detail="Processing lab task"))
        result = f"Lab task processed: {task.title}. Sandbox mode — no production impact. {task.description[:200]}"
        return await self.complete_task(task, result)

    async def report_status(self) -> dict:
        base = await super().report_status()
        base["experiments"] = len(self.experiments)
        active = len([e for e in self.experiments if e.get("status") == "running"])
        base["active_experiments"] = active
        return base
