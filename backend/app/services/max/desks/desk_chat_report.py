"""Founder-facing desk reports — never dump raw desk output into chat.

When review fails, Max tells Rafael briefly what failed. Pipeline dumps
and 200-quote lists stay off the chat surface.
"""
from __future__ import annotations

import re
from typing import Any

_FAILED_PREFIX = re.compile(
    r"^\s*(?:FAILED(?:\s*\(review\))?\s*:)\s*",
    re.I,
)
_PIPELINE_DUMP = re.compile(
    r"today'?s pipeline summary|open quotes:|\d+\s+open quotes",
    re.I,
)


def brief_review_failure(reason: str | None, *, desk_id: str | None = None) -> str:
    why = (reason or "desk output did not match the request").strip()
    why = _FAILED_PREFIX.sub("", why)
    why = re.sub(r"\s+", " ", why).strip()
    if len(why) > 180:
        why = why[:177].rstrip() + "…"
    who = f"{desk_id} desk" if desk_id else "desk"
    return f"{who} review failed: {why}. I did not dump the raw desk output."


def is_raw_desk_dump(text: str | None) -> bool:
    raw = (text or "").strip()
    if not raw:
        return False
    if _PIPELINE_DUMP.search(raw) and raw.count("\n") >= 8:
        return True
    if raw.lower().startswith("failed") and len(raw) > 400:
        return True
    return False


def founder_facing_desk_result(
    result_text: str | None,
    *,
    verdict: str | None = None,
    reason: str | None = None,
    desk_id: str | None = None,
    state: str | None = None,
) -> str:
    """Replace failed / dumped desk output with a short line for chat."""
    raw = (result_text or "").strip()
    failed = (
        (verdict or "").lower() == "failed"
        or (state or "").lower() in {"failed", "fail"}
        or raw.lower().startswith("failed")
    )
    if failed or is_raw_desk_dump(raw):
        why = reason
        if not why:
            first = raw.splitlines()[0] if raw else ""
            why = _FAILED_PREFIX.sub("", first) or "review rejected the desk result"
        return brief_review_failure(why, desk_id=desk_id)
    return raw


def sanitize_desk_tool_payload(data: dict[str, Any] | None, *, desk_id: str | None = None) -> dict[str, Any]:
    """Strip raw result text from a run_desk_task payload when review failed."""
    payload = dict(data or {})
    state = str(payload.get("state") or payload.get("status") or "")
    raw = payload.get("result")
    text = raw if isinstance(raw, str) else ""
    if (state.lower() in {"failed", "fail"} or text.lower().startswith("failed")
            or is_raw_desk_dump(text)):
        brief = founder_facing_desk_result(
            text, state=state, desk_id=desk_id or payload.get("desk"),
        )
        payload["result"] = brief
        payload["founder_brief"] = brief
        payload.pop("output", None)
    return payload
