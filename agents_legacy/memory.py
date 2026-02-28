"""
Shared memory store for the EmpireBox Agent Framework.

Agents can read and write shared state so cross-product workflows can
pass data between steps.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "data", "agent_memory.json")


class AgentMemory:
    """File-backed key-value and conversation memory store shared across agents."""

    def __init__(self, path: Optional[str] = None) -> None:
        self._path = path or _DEFAULT_PATH
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        self._store: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if not os.path.exists(self._path):
            return {}
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not load agent memory: %s", exc)
            return {}

    def _save(self) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._store, f, indent=2)

    # Key-value interface
    def set(self, key: str, value: Any) -> None:
        self._store[key] = value
        self._save()

    def get(self, key: str, default: Any = None) -> Any:
        return self._store.get(key, default)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)
        self._save()

    # Conversation log interface
    def append_log(self, agent: str, message: str) -> None:
        logs: List[Dict[str, Any]] = self._store.setdefault("_logs", [])
        logs.append({"agent": agent, "message": message, "timestamp": datetime.now(timezone.utc).isoformat()})
        self._save()

    def get_logs(self, agent: Optional[str] = None) -> List[Dict[str, Any]]:
        logs = self._store.get("_logs", [])
        if agent:
            return [l for l in logs if l["agent"] == agent]
        return list(logs)
