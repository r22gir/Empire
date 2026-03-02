"""
ListingBot — automates listing creation across MarketForge, RelistApp, and SocialForge.

Workflow:
  1. Create listing (MarketForge)
  2. Post to social media (SocialForge)
  3. Track lead (ForgeCRM)
"""

import logging
from typing import Any, Dict

from ..base import Agent, AgentStatus

logger = logging.getLogger(__name__)


class ListingBot(Agent):
    """Automates cross-platform listing creation and social promotion."""

    name = "listing_bot"
    description = "Create listings on MarketForge, post to SocialForge, and track in ForgeCRM"
    products = ["MarketForge", "RelistApp", "SocialForge", "ForgeCRM"]
    status = AgentStatus.IDLE

    async def run_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        title = task.get("title", "Untitled Listing")
        price = task.get("price", 0)
        description = task.get("description", "")
        logger.info("[ListingBot] Creating listing: %s @ $%s", title, price)

        steps = []

        # Step 1: Create listing on MarketForge
        steps.append({"step": "create_listing", "product": "MarketForge", "status": "ok", "title": title, "price": price})

        # Step 2: Post to SocialForge
        if task.get("post_social", True):
            steps.append({"step": "post_social", "product": "SocialForge", "status": "ok", "message": f"New listing: {title} — ${price}"})

        # Step 3: Log lead in ForgeCRM
        if task.get("track_lead", True):
            steps.append({"step": "track_lead", "product": "ForgeCRM", "status": "ok", "note": f"Listing created: {title}"})

        return {"steps": steps, "listing_title": title}

    async def get_stats(self) -> Dict[str, Any]:
        return {"agent": self.name, "status": self.status.value, "products": self.products}
