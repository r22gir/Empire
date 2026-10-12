"""Execute ```tool blocks without importing the full tool_executor at module load.

Import of tool_executor pulls inpaint/generated-dir setup; keep that lazy so
tests and desks can run against a temp DB without touching live paths.
"""
from __future__ import annotations

from typing import Any, Callable, Optional


def execute_embedded_tool_blocks(
    content: str,
    *,
    desk_id: str,
    task: Any = None,
    execute_fn: Optional[Callable] = None,
    parse_fn: Optional[Callable] = None,
    strip_fn: Optional[Callable] = None,
) -> str:
    if not content:
        return content
    if execute_fn is None or parse_fn is None or strip_fn is None:
        try:
            from app.services.max.tool_executor import (
                execute_tool, parse_tool_blocks, strip_tool_blocks,
            )
        except Exception:
            return content
        execute_fn = execute_fn or execute_tool
        parse_fn = parse_fn or parse_tool_blocks
        strip_fn = strip_fn or strip_tool_blocks
    actions = parse_fn(content)
    if not actions:
        return content
    result_lines = []
    for action in actions:
        try:
            result = execute_fn(action, desk=desk_id)
            ok = bool(getattr(result, "success", False))
            payload = getattr(result, "result", None)
            if payload is None:
                payload = getattr(result, "error", "")
            if task is not None:
                from app.services.max.desks.base_desk import DeskAction

                task.actions.append(DeskAction(
                    action=str(action.get("tool") or "tool"),
                    detail=str(payload)[:300],
                    success=ok,
                ))
            result_lines.append(
                f"Tool {action.get('tool')}: {'ok' if ok else 'error'} — {str(payload)[:400]}"
            )
        except Exception as e:
            result_lines.append(f"Tool {action.get('tool')}: error — {e}")
    cleaned = strip_fn(content).strip()
    executed = "\n".join(result_lines)
    if cleaned:
        return f"{cleaned}\n\n{executed}"
    return executed
