"""
EmpireBox Agent Framework

Provides autonomous agents for cross-product workflows across Forge products.

Usage:
    from agents import Orchestrator
    from agents.builtin import ListingBot, ShipBot

    orchestrator = Orchestrator()
    orchestrator.register(ListingBot())
    orchestrator.register(ShipBot())

    import asyncio
    result = asyncio.run(orchestrator.assign_task("listing_bot", {
        "title": "Nike Shoes Size 10",
        "price": 120,
        "post_social": True,
    }))
"""

from .base import Agent, AgentStatus
from .memory import AgentMemory
from .orchestrator import Orchestrator

__all__ = ["Agent", "AgentStatus", "AgentMemory", "Orchestrator"]
