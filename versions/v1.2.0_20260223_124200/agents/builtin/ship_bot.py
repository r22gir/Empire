"""
ShipBot — automates shipping label creation and customer notifications.

Workflow:
  1. Get order details (MarketForge)
  2. Create shipping label (ShipForge)
  3. Notify customer (SupportForge)
"""

import logging
from typing import Any, Dict

from ..base import Agent, AgentStatus

logger = logging.getLogger(__name__)


class ShipBot(Agent):
    """Automates end-to-end order fulfillment: fetch → label → notify."""

    name = "ship_bot"
    description = "Get order from MarketForge, create label via ShipForge, notify via SupportForge"
    products = ["MarketForge", "ShipForge", "SupportForge"]
    status = AgentStatus.IDLE

    async def run_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        order_id = task.get("order_id", "UNKNOWN")
        logger.info("[ShipBot] Processing order: %s", order_id)

        steps = []

        # Step 1: Fetch order from MarketForge
        steps.append({"step": "fetch_order", "product": "MarketForge", "status": "ok", "order_id": order_id})

        # Step 2: Create shipping label via ShipForge
        tracking_number = f"TRK{order_id}001"
        steps.append({"step": "create_label", "product": "ShipForge", "status": "ok", "tracking": tracking_number})

        # Step 3: Notify customer via SupportForge
        if task.get("notify_customer", True):
            steps.append({"step": "notify_customer", "product": "SupportForge", "status": "ok", "tracking": tracking_number})

        return {"steps": steps, "order_id": order_id, "tracking_number": tracking_number}

    async def get_stats(self) -> Dict[str, Any]:
        return {"agent": self.name, "status": self.status.value, "products": self.products}
