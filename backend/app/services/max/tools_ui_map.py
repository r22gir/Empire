"""find_in_app — look up a Command Center screen from the live screen-path map.

Registered into tool_executor.TOOL_REGISTRY on import. Never greps the repo.
"""
from __future__ import annotations

from typing import Optional

from app.services.max.tool_executor import ToolResult, tool
from app.services.max.ui_map import (
    feature_markdown_link,
    find_in_app_reply,
    format_feature_reply,
    is_family_edition,
    lookup_feature,
)


@tool("find_in_app")
def _find_in_app(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Where a screen/button lives. Answers from the live screen-path map only."""
    q = " ".join(
        str(params.get(k) or "").strip()
        for k in ("query", "q", "name", "feature", "screen")
    ).strip()
    if not q:
        return ToolResult(
            tool="find_in_app",
            success=False,
            error="Say what to find: Presentation mode, Organizer, Quotes, …",
        )
    family = is_family_edition()
    channel = params.get("_channel") or params.get("channel")
    feat = lookup_feature(q, family=family)
    if feat:
        text = format_feature_reply(feat, channel=channel, family=family)
        return ToolResult(
            tool="find_in_app",
            success=True,
            result={
                "id": feat.id,
                "name": feat.name,
                "where": feat.where,
                "href": feat.href,
                "markdown_link": feature_markdown_link(feat, channel=channel, family=family),
                "text": text,
                "workroom_only": feat.workroom_only,
                "note": (
                    "Answer from this result only. Include the markdown_link. "
                    "Do not grep the repo or read .next / .next.prev builds."
                ),
            },
        )
    fallback = find_in_app_reply(q, family=family) or (
        f'No screen-path map entry matched "{q}". Ask with the screen name.'
    )
    return ToolResult(
        tool="find_in_app",
        success=False,
        error=fallback,
        result={"query": q, "text": fallback},
    )


UI_MAP_TOOLS_DOC = """
### App location (live screen-path map — no repo search)
- **find_in_app** — Where a screen or button is in Command Center. Use for
  "where is X", "how do I open X", "dónde está X". Answers from the live
  screen-path map (LeftNav / QuickSwitch / page.tsx). NEVER shell_execute,
  grep, rg, or read .next / .next.prev / node_modules for these questions.
  Always include the markdown_link so the chat can render a tappable link.
  `{"tool": "find_in_app", "query": "presentation mode"}`
"""
