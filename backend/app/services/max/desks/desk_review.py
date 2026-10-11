"""Review desk output against the original request before reporting done.

Second pass uses the *active* chat provider (never disabled Ollama).
Template-only desk replies are marked draft-only and are not reported as done.
"""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("max.desks.review")

# Phrases that mean the desk returned a canned shell, not real work.
_TEMPLATE_MARKERS = (
    "suggested hashtags",
    "ready for review and scheduling",
    "status: draft — ready",
    "post drafted for",
    "i have completed the task",
    "task completed successfully",
    "here is a template",
    "placeholder",
    "lorem ipsum",
    "todo: fill",
    "[insert",
    "coming soon",
)

_DRAFT_ONLY_PREFIX = "draft only"


def looks_like_template(text: str | None) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return True
    if len(t) < 40:
        return True
    return any(m in t for m in _TEMPLATE_MARKERS)


def mark_draft_only(text: str | None) -> str:
    body = (text or "").strip()
    if body.lower().startswith(_DRAFT_ONLY_PREFIX):
        return body
    return f"draft only — {body}" if body else "draft only — desk returned template text"


async def review_desk_output(
    *,
    original_request: str,
    desk_id: str,
    result_text: str | None,
    title: str = "",
) -> dict[str, Any]:
    """Return {verdict, reason, report}.

    verdict: 'done' | 'draft_only' | 'failed'
    """
    result = (result_text or "").strip()
    if looks_like_template(result):
        report = mark_draft_only(result)
        return {
            "verdict": "draft_only",
            "reason": "desk returned template or empty text",
            "report": report,
            "reviewed_by": "template-gate",
        }

    llm = await _second_pass(original_request or title, desk_id, result)
    if llm is None:
        # No active provider — keep the work, do not invent a pass.
        return {
            "verdict": "done",
            "reason": "review skipped (no active provider); output is non-template",
            "report": result,
            "reviewed_by": "skipped",
        }
    verdict = llm.get("verdict") or "done"
    if verdict == "draft_only":
        return {
            "verdict": "draft_only",
            "reason": llm.get("reason") or "reviewer marked draft only",
            "report": mark_draft_only(result),
            "reviewed_by": llm.get("provider") or "active-model",
        }
    if verdict == "failed":
        return {
            "verdict": "failed",
            "reason": llm.get("reason") or "output does not match the request",
            "report": result,
            "reviewed_by": llm.get("provider") or "active-model",
        }
    return {
        "verdict": "done",
        "reason": llm.get("reason") or "output matches the request",
        "report": result,
        "reviewed_by": llm.get("provider") or "active-model",
    }


async def _second_pass(request: str, desk_id: str, result: str) -> dict[str, Any] | None:
    """Ask the active (non-Ollama) provider whether the output satisfies the request."""
    try:
        from app.services.max.ai_router import ai_router, AIMessage
        from app.services.max.routing_state import canonical_provider
    except Exception as exc:
        logger.debug("desk review: router import failed: %s", exc)
        return None

    state = ai_router.get_routing_state_payload()
    provider = canonical_provider(str(state.get("selected_provider") or ""))
    if not provider or provider == "ollama":
        logger.info("desk review: refusing Ollama / empty provider")
        return None
    if state.get("ai_calls_disabled"):
        return None

    prompt = (
        "You review desk output for Max (chief of staff). "
        "Reply with JSON only: "
        '{"verdict":"done"|"draft_only"|"failed","reason":"one sentence"}\n'
        "done = output addresses the original request with specific content.\n"
        "draft_only = generic template, missing facts, or not ready to present as finished.\n"
        "failed = wrong desk work or does not address the request.\n\n"
        f"Desk: {desk_id}\nRequest: {request[:800]}\nOutput: {result[:2000]}"
    )
    try:
        response = await ai_router.chat(
            messages=[AIMessage(role="user", content=prompt)],
            system_prompt="Return valid JSON only. No markdown.",
            desk="quality",
        )
        if getattr(response, "provider_unavailable", False):
            return None
        return _parse_verdict(response.content, provider)
    except Exception as exc:
        logger.warning("desk review second pass failed: %s", exc)
        return None


def _parse_verdict(raw: str, provider: str) -> dict[str, Any]:
    import json
    text = (raw or "").strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return {"verdict": "done", "reason": "unparseable review; keeping output", "provider": provider}
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {"verdict": "done", "reason": "unparseable review; keeping output", "provider": provider}
    verdict = str(data.get("verdict") or "done").lower()
    if verdict not in ("done", "draft_only", "failed"):
        verdict = "done"
    return {"verdict": verdict, "reason": str(data.get("reason") or ""), "provider": provider}
