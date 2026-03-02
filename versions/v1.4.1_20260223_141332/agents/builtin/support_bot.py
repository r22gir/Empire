"""
SupportBot — handles incoming support tickets across all Forge products.

Workflow:
  1. Receive ticket (SupportForge)
  2. Cross-reference order (MarketForge) if applicable
  3. Auto-respond or escalate to human agent
"""

import logging
from typing import Any, Dict

from ..base import Agent, AgentStatus

logger = logging.getLogger(__name__)


class SupportBot(Agent):
    """Triages support tickets, checks orders, and auto-responds or escalates."""

    name = "support_bot"
    description = "Receive tickets via SupportForge, check MarketForge orders, auto-respond or escalate"
    products = ["SupportForge", "MarketForge", "ForgeCRM"]
    status = AgentStatus.IDLE

    # Simple keyword-based auto-response rules
    _AUTO_RESPONSES = {
        "shipping": "Your order has been shipped. Please check your tracking number.",
        "refund": "We have initiated your refund. It typically takes 3-5 business days.",
        "cancel": "Your cancellation request has been received and is being processed.",
        "invoice": "Your invoice has been emailed to the address on file.",
    }

    async def run_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        ticket_id = task.get("ticket_id", "UNKNOWN")
        subject = task.get("subject", "")
        body = task.get("body", "")
        order_id = task.get("order_id")
        logger.info("[SupportBot] Processing ticket %s: %s", ticket_id, subject)

        steps = []

        # Step 1: Receive/acknowledge ticket
        steps.append({"step": "receive_ticket", "product": "SupportForge", "status": "ok", "ticket_id": ticket_id})

        # Step 2: Look up related order
        if order_id:
            steps.append({"step": "check_order", "product": "MarketForge", "status": "ok", "order_id": order_id})

        # Step 3: Auto-respond or escalate
        combined = f"{subject} {body}".lower()
        response = None
        for keyword, reply in self._AUTO_RESPONSES.items():
            if keyword in combined:
                response = reply
                break

        if response:
            steps.append({"step": "auto_respond", "product": "SupportForge", "status": "ok", "response": response})
            action = "auto_responded"
        else:
            steps.append({"step": "escalate", "product": "SupportForge", "status": "ok", "note": "Escalated to human agent"})
            action = "escalated"

        return {"steps": steps, "ticket_id": ticket_id, "action": action}

    async def get_stats(self) -> Dict[str, Any]:
        return {"agent": self.name, "status": self.status.value, "products": self.products}
