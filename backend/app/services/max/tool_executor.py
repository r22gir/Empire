"""MAX Tool Executor — parses tool blocks from AI responses and executes actions."""
import re
import json
import uuid
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional
from app.db.database import get_db

logger = logging.getLogger("max.tool_executor")

TOOL_BLOCK_RE = re.compile(r"```tool\s*\n(.*?)\n```", re.DOTALL)


@dataclass
class ToolResult:
    tool: str
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}


def parse_tool_blocks(text: str) -> list[dict]:
    """Extract tool call JSON objects from ```tool ... ``` blocks."""
    results = []
    for match in TOOL_BLOCK_RE.finditer(text):
        try:
            obj = json.loads(match.group(1).strip())
            if isinstance(obj, dict) and "tool" in obj:
                results.append(obj)
        except json.JSONDecodeError as e:
            logger.warning(f"Malformed tool JSON: {e}")
    return results


def strip_tool_blocks(text: str) -> str:
    """Remove tool blocks from visible text."""
    return TOOL_BLOCK_RE.sub("", text).strip()


def execute_tool(tool_call: dict, desk: Optional[str] = None) -> ToolResult:
    """Dispatch and execute a tool call."""
    tool_name = tool_call.get("tool", "")
    try:
        if tool_name == "create_task":
            return _create_task(tool_call, desk)
        else:
            return ToolResult(tool=tool_name, success=False, error=f"Unknown tool: {tool_name}")
    except Exception as e:
        logger.error(f"Tool execution error ({tool_name}): {e}")
        return ToolResult(tool=tool_name, success=False, error=str(e))


def _create_task(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Create a task in the tasks table."""
    title = params.get("title", "").strip()
    if not title:
        return ToolResult(tool="create_task", success=False, error="Task title is required")

    task_id = str(uuid.uuid4())[:8]
    description = params.get("description", "")
    priority = params.get("priority", "normal")
    due_date = params.get("due_date")
    task_desk = desk or params.get("desk", "operations")

    if priority not in ("urgent", "high", "normal", "low"):
        priority = "normal"

    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        conn.execute(
            """INSERT INTO tasks (id, title, description, status, priority, desk, created_by, due_date, tags, metadata, created_at, updated_at)
               VALUES (?, ?, ?, 'todo', ?, ?, 'max', ?, '[]', '{}', ?, ?)""",
            (task_id, title, description, priority, task_desk, due_date, now, now),
        )
        # Log activity
        conn.execute(
            """INSERT INTO task_activity (task_id, actor, action, detail, created_at)
               VALUES (?, 'max', 'created', ?, ?)""",
            (task_id, f"Created by MAX via {task_desk} desk chat", now),
        )

    logger.info(f"Task created: {task_id} - {title} (desk={task_desk})")

    return ToolResult(
        tool="create_task",
        success=True,
        result={
            "task_id": task_id,
            "title": title,
            "description": description,
            "priority": priority,
            "desk": task_desk,
            "due_date": due_date,
            "status": "todo",
        },
    )
