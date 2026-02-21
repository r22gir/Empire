"""
Built-in general skills: search, code assistance, and file operations.
"""

import os
import logging
from typing import Dict, Any

from .base import Skill

logger = logging.getLogger(__name__)


class SearchSkill(Skill):
    """Web/local search skill."""

    name = "search"
    description = "Search the web or local knowledge base"
    triggers = ["search", "find", "look up", "what is", "who is", "how to"]

    async def execute(self, intent: str, params: Dict[str, Any]) -> str:
        query = params.get("query", intent)
        logger.info("SearchSkill executing for query: %s", query)
        return f"Search results for '{query}': (configure a search provider in config.yaml)"


class CodeSkill(Skill):
    """Code generation and explanation skill."""

    name = "code"
    description = "Write, explain, or debug code"
    triggers = ["write code", "code", "script", "function", "debug", "explain code", "program"]

    async def execute(self, intent: str, params: Dict[str, Any]) -> str:
        language = params.get("language", "python")
        task = params.get("task", intent)
        logger.info("CodeSkill executing for task: %s language: %s", task, language)
        return f"Code assistance for '{task}' in {language}: (connect an AI model in config.yaml)"


class FileSkill(Skill):
    """File read/write operations skill."""

    name = "files"
    description = "Read and write files"
    triggers = ["read file", "write file", "open file", "save file", "list files"]

    async def execute(self, intent: str, params: Dict[str, Any]) -> str:
        action = params.get("action", "list")
        path = params.get("path", ".")
        logger.info("FileSkill executing action: %s path: %s", action, path)
        if action == "list":
            try:
                entries = os.listdir(path)
                return f"Files in '{path}': {', '.join(entries)}"
            except OSError as exc:
                return f"Error listing files: {exc}"
        return f"File operation '{action}' on '{path}': unsupported action"
