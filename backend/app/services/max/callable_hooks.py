"""Small shared pattern for bounded MAX callable hooks."""
from __future__ import annotations

from typing import Any, Callable


def invoke_bounded_hook(name: str, func: Callable[[], Any]) -> dict[str, Any]:
    """Invoke one internal hook and return a consistent result envelope."""
    try:
        result = func()
        if hasattr(result, "to_dict"):
            result = result.to_dict()
        return {"hook": name, "success": True, "result": result}
    except Exception as exc:
        return {"hook": name, "success": False, "error": str(exc)}
