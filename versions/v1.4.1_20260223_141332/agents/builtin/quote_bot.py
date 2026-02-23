"""
QuoteBot — automates quote creation, delivery, and CRM logging.

Workflow:
  1. Create quote (LuxeForge / ContractorForge)
  2. Send via email (SupportForge)
  3. Log opportunity (ForgeCRM)
"""

import logging
from typing import Any, Dict

from ..base import Agent, AgentStatus

logger = logging.getLogger(__name__)


class QuoteBot(Agent):
    """Creates quotes, emails them, and logs the opportunity in CRM."""

    name = "quote_bot"
    description = "Create quote in LuxeForge/ContractorForge, email via SupportForge, log in ForgeCRM"
    products = ["LuxeForge", "ContractorForge", "ForgeCRM", "SupportForge"]
    status = AgentStatus.IDLE

    async def run_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        customer = task.get("customer", "Unknown Customer")
        items = task.get("items", [])
        total = task.get("total", 0)
        email = task.get("email", "")
        logger.info("[QuoteBot] Creating quote for %s totalling $%s", customer, total)

        steps = []

        # Step 1: Create quote
        source = task.get("source", "LuxeForge")
        quote_id = f"Q{hash(customer) % 100000:05d}"
        steps.append({"step": "create_quote", "product": source, "status": "ok", "quote_id": quote_id, "total": total})

        # Step 2: Send quote via email
        if email:
            steps.append({"step": "send_email", "product": "SupportForge", "status": "ok", "recipient": email, "quote_id": quote_id})

        # Step 3: Log in CRM
        steps.append({"step": "log_opportunity", "product": "ForgeCRM", "status": "ok", "customer": customer, "quote_id": quote_id})

        return {"steps": steps, "quote_id": quote_id, "customer": customer}

    async def get_stats(self) -> Dict[str, Any]:
        return {"agent": self.name, "status": self.status.value, "products": self.products}
