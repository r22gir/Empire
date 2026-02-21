"""
Agent orchestrator for the EmpireBox Agent Framework.

Manages a priority task queue, coordinates multiple agents, handles retries,
and tracks performance metrics.
"""

import asyncio
import logging
from collections import deque
from typing import Any, Deque, Dict, List, Optional

from .base import Agent, AgentStatus
from .memory import AgentMemory

logger = logging.getLogger(__name__)


class Orchestrator:
    """Coordinates multiple EmpireBox agents with a priority task queue."""

    def __init__(self, memory: Optional[AgentMemory] = None) -> None:
        self._agents: Dict[str, Agent] = {}
        self._queue: Deque[Dict[str, Any]] = deque()
        self._memory = memory or AgentMemory()
        self._metrics: Dict[str, int] = {"total_tasks": 0, "successful": 0, "failed": 0}

    def register(self, agent: Agent) -> None:
        """Register an agent with the orchestrator."""
        self._agents[agent.name] = agent
        logger.info("Registered agent: %s", agent.name)

    def list_agents(self) -> List[Dict[str, Any]]:
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
        self,
        agent_name: str,
        task: Dict[str, Any],
        priority: int = 5,
    ) -> Dict[str, Any]:
        """
        Assign a task to the named agent.

        Priority is 1 (highest) through 10 (lowest). Retries up to 3 times.
        """
        agent = self._agents.get(agent_name)
        if agent is None:
            return {"success": False, "error": f"Agent '{agent_name}' not found"}
        if agent.status == AgentStatus.PAUSED:
            return {"success": False, "error": f"Agent '{agent_name}' is paused"}

        self._queue.append({"agent": agent_name, "task": task, "priority": priority})
        return await self._execute(agent, task)

    async def _execute(
        self,
        agent: Agent,
        task: Dict[str, Any],
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        agent.status = AgentStatus.RUNNING
        self._metrics["total_tasks"] += 1
        last_error: Optional[str] = None
        for attempt in range(1, max_retries + 1):
            try:
                result = await agent.run_task(task)
                agent.status = AgentStatus.IDLE
                self._metrics["successful"] += 1
                self._memory.append_log(agent.name, f"Task completed: {task}")
                return {"success": True, "result": result}
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                logger.warning("Agent %s attempt %d/%d failed: %s", agent.name, attempt, max_retries, exc)
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
        agent.status = AgentStatus.ERROR
        self._metrics["failed"] += 1
        self._memory.append_log(agent.name, f"Task failed: {task} — {last_error}")
        return {"success": False, "error": last_error}

    def get_queue(self) -> List[Dict[str, Any]]:
        return list(self._queue)

    def get_metrics(self) -> Dict[str, int]:
        return dict(self._metrics)

    def get_agent(self, name: str):
        """Return the named agent, or None if not registered."""
        return self._agents.get(name)

    def pause_agent(self, name: str) -> bool:
        agent = self._agents.get(name)
        if agent is None:
            return False
        agent.status = AgentStatus.PAUSED
        return True

    def resume_agent(self, name: str) -> bool:
        agent = self._agents.get(name)
        if agent is None:
            return False
        agent.status = AgentStatus.IDLE
        return True
