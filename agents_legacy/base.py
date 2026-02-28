"""
Base agent class for the EmpireBox Agent Framework.

All built-in agents inherit from this class.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List


class AgentStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class Agent(ABC):
    """Abstract base class for all EmpireBox autonomous agents."""

    name: str
    description: str
    products: List[str]  # Forge products this agent can access
    status: AgentStatus = AgentStatus.IDLE

    @abstractmethod
    async def run_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the given task and return a result dict."""
        pass

    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Return current performance statistics."""
        pass
