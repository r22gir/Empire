"""find_in_app — look up a Command Center screen from the live UI map,
then fall through to universal search for records (quotes, jobs, people).

Registered into tool_executor.TOOL_REGISTRY on import (same pattern as
tools_files). Never greps the repo.
"""
from __future__ import annotations

from typing import Optional

from app.services.max.tool_executor import ToolResult, tool


@tool("find_in_app")
def _find_in_app(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Where a screen/button lives, or a record (quote, job, person)."""
    from app.services.max.tools_search import find_in_app_or_search
    return find_in_app_or_search(params, desk)


UI_MAP_TOOLS_DOC = """
### App location + universal search
- **find_in_app** — Where a screen or button is, or find a record.
  "where is X" uses the live UI map (LeftNav / MaxHome / CommandCenter ids).
  "find Marley's quote" falls through to universal search and returns deep links.
  NEVER shell_execute, grep, rg, or read .next / .next.prev / node_modules.
  `{"tool": "find_in_app", "query": "presentation mode"}`
- **search** — Same index as the header search (screens, jobs, quotes,
  invoices, people, files, organizer, pending mail, memory). Edition-isolated.
  `{"tool": "search", "query": "Marley's quote"}`
"""
