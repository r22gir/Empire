"""
Base skill class for OpenClaw plugin system.

All skills must inherit from this class and implement the execute method.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class Skill(ABC):
    """Abstract base class for all OpenClaw skills."""

    name: str
    description: str
    triggers: List[str]

    @abstractmethod
    async def execute(self, intent: str, params: Dict[str, Any]) -> str:
        """Execute the skill with the given intent and parameters."""
        pass

    def matches(self, message: str) -> bool:
        """Return True if this skill should handle the given message."""
        return any(t.lower() in message.lower() for t in self.triggers)
