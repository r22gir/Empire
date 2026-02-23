"""
Agent memory/context store for OpenClaw.

Stores conversation history in a JSON file and provides retrieval helpers.
"""

import json
import logging
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


class AgentMemory:
    """Simple file-backed conversation memory store."""

    def __init__(self, session_id: str = "default") -> None:
        self.session_id = session_id
        self._path = os.path.join(DATA_DIR, f"session_{session_id}.json")
        self._history: List[Dict[str, Any]] = self._load()

    def _load(self) -> List[Dict[str, Any]]:
        os.makedirs(DATA_DIR, exist_ok=True)
        if not os.path.exists(self._path):
            return []
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not load memory for session %s: %s", self.session_id, exc)
            return []

    def _save(self) -> None:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._history, f, indent=2)

    def add(self, role: str, content: str) -> None:
        """Append a message to the conversation history."""
        self._history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self._save()

    def get_recent(self, n: int = 10) -> List[Dict[str, Any]]:
        """Return the n most recent messages."""
        return self._history[-n:]

    def clear(self) -> None:
        """Clear the conversation history."""
        self._history = []
        self._save()

    @property
    def history(self) -> List[Dict[str, Any]]:
        return list(self._history)
