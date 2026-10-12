"""find_in_app — look up a Command Center screen from the live UI map.

Registered into tool_executor.TOOL_REGISTRY on import (same pattern as
tools_files). Never greps the repo.
"""
from __future__ import annotations

from typing import Optional

from app.services.max.tool_executor import ToolResult, tool
from app.services.max.ui_map import (
    find_in_app_reply,
    format_feature_reply,
    is_family_edition,
    lookup_feature,
)


@tool("find_in_app")
def _find_in_app(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Where a screen/button lives. Answers from the live UI map only."""
    q = " ".join(
        str(params.get(k) or "").strip()
        for k in ("query", "q", "name", "feature", "screen")
    ).strip()
    if not q:
        return ToolResult(
            tool="find_in_app",
            success=False,
            error="Say what to find: Presentation mode, AI face, Talk, Improvements, …",
        )
    family = is_family_edition()
    feat = lookup_feature(q, family=family)
    if feat:
        text = format_feature_reply(feat)
        return ToolResult(
            tool="find_in_app",
            success=True,
            result={
                "id": feat.id,
                "name": feat.name,
                "where": feat.where,
                "href": feat.href,
                "text": text,
                "workroom_only": feat.workroom_only,
                "note": "Answer from this result only. Do not grep the repo or read .next builds.",
            },
        )
    fallback = find_in_app_reply(q, family=family) or (
        f'No UI map entry matched "{q}". Ask with the screen name from the live UI map.'
    )
    return ToolResult(
        tool="find_in_app",
        success=False,
        error=fallback,
        result={"query": q, "text": fallback},
    )


UI_MAP_TOOLS_DOC = """
### App location (live UI map — no repo search)
- **find_in_app** — Where a screen or button is in Command Center. Use for
  "where is X", "how do I open X", "dónde está X". Answers from the live UI
  map (LeftNav / MaxHome / CommandCenter screen ids). NEVER shell_execute,
  grep, rg, or read .next / .next.prev / node_modules for these questions.
  `{"tool": "find_in_app", "query": "presentation mode"}`
"""
