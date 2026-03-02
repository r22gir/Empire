"""
Agent orchestrator for OpenClaw.

Manages a task queue, routes tasks to appropriate agents, handles retries,
and logs activity.
"""

import asyncio
import logging
from collections import deque
from typing import Dict, Any, List, Optional

from .base import Agent, AgentStatus

logger = logging.getLogger(__name__)


class Orchestrator:
    """Coordinates multiple agents with a priority task queue."""

    def __init__(self) -> None:
        self._agents: Dict[str, Agent] = {}
        self._queue: deque = deque()
        self._activity_log: List[Dict[str, Any]] = []
        self._metrics: Dict[str, Any] = {"total_tasks": 0, "successful": 0, "failed": 0}

    def register(self, agent: Agent) -> None:
        """Register an agent with the orchestrator."""
        self._agents[agent.name] = agent
        logger.info("Agent registered: %s", agent.name)

    def list_agents(self) -> List[Dict[str, Any]]:
        """Return info about all registered agents."""
        return [
            {
                "name": name,
                "description": a.description,
                "status": a.status.value,
                "products": a.products,
            }
            for name, a in self._agents.items()
        ]

    async def assign_task(
        self, agent_name: str, task: Dict[str, Any], priority: int = 5
    ) -> Dict[str, Any]:
        """
        Assign a task to a named agent with optional priority (1=highest, 10=lowest).
        Retries up to 3 times on failure.
        """
        agent = self._agents.get(agent_name)
        if agent is None:
            return {"success": False, "error": f"Agent '{agent_name}' not found"}

        entry = {"agent": agent_name, "task": task, "priority": priority}
        self._queue.append(entry)
        return await self._execute(agent, task)

    async def _execute(self, agent: Agent, task: Dict[str, Any], max_retries: int = 3) -> Dict[str, Any]:
        agent.status = AgentStatus.RUNNING
        self._metrics["total_tasks"] += 1
        last_error: Optional[str] = None
        for attempt in range(1, max_retries + 1):
            try:
                result = await agent.run_task(task)
                agent.status = AgentStatus.IDLE
                self._metrics["successful"] += 1
                self._activity_log.append({"agent": agent.name, "task": task, "result": result, "attempt": attempt})
                return {"success": True, "result": result}
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                logger.warning("Agent %s attempt %d failed: %s", agent.name, attempt, exc)
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
        agent.status = AgentStatus.ERROR
        self._metrics["failed"] += 1
        return {"success": False, "error": last_error}

    def get_queue(self) -> List[Dict[str, Any]]:
        return list(self._queue)

    def get_metrics(self) -> Dict[str, Any]:
        return dict(self._metrics)

    def get_agent(self, name: str):
        """Return the named agent, or None if not registered."""
        return self._agents.get(name)
