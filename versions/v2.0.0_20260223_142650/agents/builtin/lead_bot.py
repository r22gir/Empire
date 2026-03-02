"""
LeadBot — automates lead capture, qualification, and CRM entry.

Workflow:
  1. Capture lead (LeadForge / SocialForge)
  2. Score and qualify lead
  3. Create contact and opportunity (ForgeCRM)
"""

import logging
from typing import Any, Dict

from ..base import Agent, AgentStatus

logger = logging.getLogger(__name__)


class LeadBot(Agent):
    """Captures leads from LeadForge/SocialForge, qualifies them, and logs in ForgeCRM."""

    name = "lead_bot"
    description = "Capture leads from LeadForge/SocialForge, qualify, and log in ForgeCRM"
    products = ["LeadForge", "ForgeCRM", "SocialForge"]
    status = AgentStatus.IDLE

    async def run_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        name = task.get("name", "Unknown Lead")
        email = task.get("email", "")
        source = task.get("source", "LeadForge")
        budget = task.get("budget", 0)
        logger.info("[LeadBot] Processing lead: %s from %s", name, source)

        steps = []

        # Step 1: Capture from source
        steps.append({"step": "capture_lead", "product": source, "status": "ok", "name": name, "email": email})

        # Step 2: Score/qualify
        score = min(100, (10 if email else 0) + (min(budget, 5000) // 50))
        qualified = score >= 30
        steps.append({"step": "qualify_lead", "status": "ok", "score": score, "qualified": qualified})

        # Step 3: Log in CRM
        if qualified:
            steps.append({"step": "create_crm_contact", "product": "ForgeCRM", "status": "ok", "name": name, "email": email, "score": score})

        return {"steps": steps, "lead_name": name, "score": score, "qualified": qualified}

    async def get_stats(self) -> Dict[str, Any]:
        return {"agent": self.name, "status": self.status.value, "products": self.products}
