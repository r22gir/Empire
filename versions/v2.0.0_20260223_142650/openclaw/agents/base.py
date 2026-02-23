"""
Base agent class for OpenClaw agents sub-package.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, List


class AgentStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class Agent(ABC):
    """Abstract base class for OpenClaw agents."""

    name: str
    description: str
    products: List[str]  # Forge products this agent can access
    status: AgentStatus = AgentStatus.IDLE

    @abstractmethod
    async def run_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Run a task and return the result."""
        pass

    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Return current agent statistics."""
        pass
