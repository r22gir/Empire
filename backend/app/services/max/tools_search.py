"""search / find_in_app — universal in-app search with deep links.

find_in_app still answers "where is Presentation" from the live UI map
(PR #116). When the query is a record ("find Marley's quote") it falls
through to universal search so Max returns grouped hits with hrefs.
"""
from __future__ import annotations

from typing import Optional

from app.services.max.tool_executor import ToolResult, tool
from app.services.max.ui_map import (
    feature_markdown_link,
    format_feature_reply,
    is_family_edition,
    lookup_feature,
)
from app.services.search.edition import process_edition
from app.services.search.universal import run_universal_search


def _channel(params: dict) -> Optional[str]:
    return params.get("_channel") or params.get("channel")


def _query(params: dict) -> str:
    return " ".join(
        str(params.get(k) or "").strip()
        for k in ("query", "q", "name", "feature", "screen", "search")
    ).strip()


def _looks_like_record(q: str) -> bool:
    import re
    return bool(re.search(
        r"\b(?:quote|quotes|estimate|invoice|job|email|mail|pdf|file|"
        r"appointment|todo|to-do|follow-?up|customer|contact|person|"
        r"est-\d+)\b",
        q or "",
        re.I,
    ))


def _format_search_reply(payload: dict, *, channel: Optional[str] = None) -> str:
    results = payload.get("results") or []
    if payload.get("blocked"):
        return "Search is not available on this edition."
    if not results:
        q = payload.get("query") or "that"
        return f'No matches for "{q}" in this edition.'
    lines = []
    for item in results[:8]:
        href = item.get("href") or ""
        title = item.get("title") or item.get("id")
        kind = item.get("type") or "result"
        if href:
            lines.append(f"- [{title}]({href}) ({kind})")
        else:
            lines.append(f"- {title} ({kind})")
    top = payload.get("top") or results[0]
    top_href = top.get("href") or ""
    head = f"Top result: **{top.get('title')}**"
    if top_href:
        head += f" — [Open]({top_href})"
    return head + "\n\n" + "\n".join(lines)


def run_search_tool(params: dict, desk: Optional[str] = None) -> ToolResult:
    q = _query(params)
    if not q:
        return ToolResult(
            tool="search",
            success=False,
            error="Say what to find: Marley's quote, Improvements, a job number…",
        )
    edition = process_edition()
    if edition == "unknown":
        return ToolResult(
            tool="search",
            success=False,
            error="Unknown EMPIRE_EDITION — search is fail-closed.",
            result={"blocked": True, "edition": edition, "sent": False},
        )
    payload = run_universal_search(q, edition=edition)
    text = _format_search_reply(payload, channel=_channel(params))
    return ToolResult(
        tool="search",
        success=bool(payload.get("results")),
        error="" if payload.get("results") else text,
        result={
            **payload,
            "text": text,
            "markdown_links": [
                item.get("href") for item in (payload.get("results") or []) if item.get("href")
            ],
            "note": "Include the markdown links. Do not send email. Draft reply needs the owner's tap.",
        },
    )


@tool("search")
def _search(params: dict, desk: Optional[str] = None) -> ToolResult:
    """Find screens and owner records (quotes, jobs, people, files, mail)."""
    return run_search_tool(params, desk)


def find_in_app_or_search(params: dict, desk: Optional[str] = None) -> ToolResult:
    q = _query(params)
    if not q:
        return ToolResult(
            tool="find_in_app",
            success=False,
            error="Say what to find: Presentation mode, Marley's quote, Improvements…",
        )
    family = is_family_edition()
    channel = _channel(params)
    feat = None if _looks_like_record(q) else lookup_feature(q, family=family)
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
                "note": "Answer from this result only. Include the markdown_link.",
            },
        )
    search = run_search_tool(params, desk)
    search.tool = "find_in_app"
    return search


SEARCH_TOOLS_DOC = """
### Universal search (screens + owner records)
- **search** / **find_in_app** — Find a screen or a record. Use for
  "find Marley's quote", "where is Improvements", "open the invoice".
  Returns grouped hits with deep links (`href` / markdown). Edition-isolated.
  NEVER send mail from this tool. Draft reply goes to the approval queue.
  `{"tool": "search", "query": "Marley's quote"}`
  `{"tool": "find_in_app", "query": "presentation mode"}`
"""
