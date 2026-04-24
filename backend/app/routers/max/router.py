"""
MAX API Router - Endpoints for AI Assistant Manager.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Response, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import json
import os
import logging
import re
import uuid
from datetime import datetime
from pathlib import Path

from app.services.max.ai_router import ai_router, AIMessage, AIModel
from app.services.max.telegram_bot import telegram_bot, _auto_save_exchange_to_memory
from app.services.max.guardrails import check_input, sanitize_output, SAFE_REFUSAL, is_founder_message
from app.services.max.security.sanitizer import sanitizer as input_sanitizer
from app.services.max.tool_executor import parse_tool_blocks, strip_tool_blocks, execute_tool, ToolResult, get_xai_tool_definitions
from app.services.max.evaluation_service import evaluation_service
from app.services.max.drawing_intent import build_drawing_handoff
from app.services.max.grounding_verifier import verify_web_response, log_to_audit
from app.services.max.response_quality_engine import quality_engine, Channel
from app.services.max.system_prompt import get_compact_system_prompt, get_system_prompt_with_brain, is_ordinary_text_request
from app.services.max.runtime_truth_check import format_runtime_truth_check, should_run_runtime_truth_check
from app.services.max.ambiguity_gate import build_inventory_clarification, should_clarify_inventory_request
from app.services.max.brain import ContextBuilder, ConversationTracker
from app.services.max.brain.brain_config import (
    REALTIME_LEARNING_ENABLED,
    BATCH_LEARNING_ENABLED,
    BATCH_LEARNING_INTERVAL,
)
from app.services.max.token_tracker import token_tracker
from app.services.max.desks import AIDeskManager, TaskStatus
from pathlib import Path as _Path

# ── Chat history persistence ─────────────────────────────────────────────────
# Must go 4 parents up: router.py → max → routers → app → backend
_ROUTER_CHATS_DIR = _Path(__file__).parent.parent.parent.parent / "data" / "chats"
_ROUTER_CHATS_DIR.mkdir(parents=True, exist_ok=True)

try:
    from app.services.max.access_control import access_controller
except ImportError:
    access_controller = None

logger = logging.getLogger("max.api")
router = APIRouter(prefix="/max", tags=["MAX AI Assistant"])


# ── Conversation windowing ───────────────────────────────────────────
MAX_CONTEXT_MESSAGES = 10   # Keep last N messages verbatim
SUMMARY_THRESHOLD = 8       # Summarize after this many older messages

def _window_conversation(history: list[dict]) -> list[dict]:
    """Apply sliding window to conversation history.

    Keeps the most recent MAX_CONTEXT_MESSAGES verbatim.
    Older messages get compressed into a single summary context note.
    This prevents context overload after 10-15+ back-and-forth messages.
    """
    if len(history) <= MAX_CONTEXT_MESSAGES:
        return history

    older = history[:-MAX_CONTEXT_MESSAGES]
    recent = history[-MAX_CONTEXT_MESSAGES:]

    # Build compact summary of older messages
    summary_parts = []
    for msg in older:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        # Skip system-injected context that's already huge
        if content.startswith("[Context from previous sessions]"):
            continue
        # Truncate each old message to key info
        preview = content[:150].replace("\n", " ")
        if len(content) > 150:
            preview += "..."
        summary_parts.append(f"  {role}: {preview}")

    if not summary_parts:
        return recent

    summary = "[Earlier in this conversation (" + str(len(older)) + " messages)]\n"
    # Limit summary to ~2000 chars to keep it compact
    summary += "\n".join(summary_parts)[:2000]

    context_msg = {"role": "system", "content": summary}
    return [context_msg] + recent


async def _safe_background(coro, label: str):
    """Run a coroutine in background, logging any errors without crashing."""
    try:
        await coro
    except Exception as e:
        logger.warning(f"Background {label} failed: {e}")

def _log_quality_metric(quality_result, model_used: str, channel: str, response_time_ms: float = 0.0):
    """Log quality gate result + response time to database for metrics."""
    try:
        import sqlite3
        db_path = os.path.expanduser("~/empire-repo/backend/data/empire.db")
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS quality_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT (datetime('now')),
                category TEXT,
                quality_level TEXT,
                checks_performed TEXT,
                warnings TEXT,
                validation_time_ms REAL,
                message_preview TEXT,
                model_used TEXT,
                channel TEXT,
                response_time_ms REAL DEFAULT 0
            )
        """)
        conn.execute(
            "INSERT INTO quality_metrics (category, quality_level, checks_performed, warnings, validation_time_ms, model_used, channel, response_time_ms) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("chat", quality_result.level, ",".join(quality_result.checks_performed), ",".join(quality_result.warnings), quality_result.validation_time_ms, model_used, channel, response_time_ms)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.debug(f"Quality metric log failed: {e}")


def _drawing_tool_result_dict(result) -> dict:
    return {
        "tool": result.tool,
        "success": result.success,
        "result": result.result,
        "error": result.error,
    }


def _drawing_missing_response(handoff) -> str:
    payload = {
        "subject": handoff.subject,
        "item_type": handoff.item_type,
        "dimensions_known": handoff.dimensions,
        "dimensions_missing": handoff.missing,
        "views": handoff.views,
        "output_format": handoff.output_format,
    }
    if handoff.source_image:
        payload["source_image"] = handoff.source_image
    return f"{handoff.response}\n\nStructured drawing handoff:\n```json\n{json.dumps(payload, indent=2)}\n```"


def _runtime_truth_tool_payload() -> dict:
    return {"tool": "empire_runtime_truth_check", "public": True}


def _response_metadata(channel: str | None, skill_used: str | None = None) -> dict:
    from app.services.max.surface_identity import build_response_metadata
    return build_response_metadata(channel, skill_used=skill_used)


def _ledger_metadata(channel: str | None, extra: dict | None = None) -> dict:
    from app.services.max.surface_identity import build_ledger_metadata
    return build_ledger_metadata(channel, extra=extra)


def _save_runtime_truth_exchange(request, response_text: str, result: ToolResult, founder: bool) -> str:
    conv_id = request.conversation_id or str(uuid.uuid4())
    try:
        conversation_tracker.add_message(conv_id, "user", request.message)
        conversation_tracker.add_message(conv_id, "assistant", response_text)
    except Exception as exc:
        logger.debug(f"Runtime truth conversation tracking failed: {exc}")

    try:
        from app.services.max.unified_message_store import unified_store
        unified_store.add_message(
            conv_id,
            request.channel or "web",
            "user",
            request.message,
            metadata=_ledger_metadata(request.channel, {"source": "runtime_truth_check_intent"}),
            founder_verified=founder,
        )
        unified_store.add_message(
            conv_id,
            request.channel or "web",
            "assistant",
            response_text,
            model="empire-runtime-truth-check",
            tool_results=[{"tool": result.tool, "success": result.success}],
            metadata=_ledger_metadata(request.channel, {"source": "runtime_truth_check_result"}),
        )
    except Exception as exc:
        logger.warning(f"Runtime truth unified message store write failed: {exc}")
    return conv_id


def _execute_drawing_handoff(handoff):
    logger.info(
        "[MAX] Drawing intent routed to sketch_to_drawing: item_type=%s views=%s dims=%s source_image=%s",
        handoff.item_type,
        ",".join(handoff.views),
        sorted(handoff.dimensions.keys()),
        bool(handoff.source_image),
    )
    result = execute_tool({"tool": "sketch_to_drawing", **(handoff.tool_payload or {})})
    return _quality_gate_drawing_result(handoff, result)


def _quality_gate_drawing_result(handoff, result):
    if not result.success:
        return result

    payload = result.result or {}
    svg = payload.get("svg") or ""
    errors = []
    checks = []

    if "<svg" not in svg:
        errors.append("drawing renderer did not return SVG output")
    else:
        checks.append("svg_present")

    forbidden = ["MEASUREMENT DIAGRAM", "measurement diagram", "placeholder", "generic measurement"]
    if any(token in svg for token in forbidden):
        errors.append("renderer returned a placeholder/generic measurement diagram")
    else:
        checks.append("no_placeholder_measurement_diagram")

    if handoff.item_type == "generic" or payload.get("item_type") == "generic":
        errors.append("drawing output is generic instead of product-specific")
    else:
        checks.append("product_specific_item_type")

    lower_svg = svg.lower()
    view_requirements = {
        "plan": ("plan",),
        "isometric": ("isometric",),
        "elevation": ("elevation", "front"),
        "front_elevation": ("front", "elevation"),
        "side_elevation": ("side", "elevation"),
    }
    for view in handoff.views:
        if view == "side_elevation" and "side" not in lower_svg:
            # Existing bench sheets do not yet include a distinct side view; do not
            # mark them production-complete, but do not block plan/front/isometric output.
            payload.setdefault("quality_warnings", []).append("side_elevation_requested_but_not_distinct")
            continue
        tokens = view_requirements.get(view)
        if tokens and not any(token in lower_svg for token in tokens):
            errors.append(f"requested view not evident in SVG: {view}")
    if not errors:
        checks.append("requested_views_evident")

    for label, value in (handoff.dimensions or {}).items():
        numeric = re.sub(r"[^0-9.]", "", str(value))
        if numeric and numeric not in svg:
            errors.append(f"provided dimension missing from SVG: {label}={value}")
    if not errors:
        checks.append("provided_dimensions_evident")

    if not payload.get("pdf_url"):
        errors.append("drawing PDF artifact URL missing")
    else:
        checks.append("pdf_artifact_present")

    if errors:
        return ToolResult(
            tool=result.tool,
            success=False,
            error="Drawing quality gate blocked artifact: " + "; ".join(dict.fromkeys(errors)),
            result={
                "quality_gate": {
                    "passed": False,
                    "errors": list(dict.fromkeys(errors)),
                    "checks": checks,
                    "handoff": {
                        "item_type": handoff.item_type,
                        "dimensions": handoff.dimensions,
                        "views": handoff.views,
                        "source_image": handoff.source_image,
                    },
                }
            },
        )

    payload["quality_gate"] = {
        "passed": True,
        "checks": checks,
        "warnings": payload.get("quality_warnings", []),
        "handoff": {
            "item_type": handoff.item_type,
            "dimensions": handoff.dimensions,
            "views": handoff.views,
            "source_image": handoff.source_image,
        },
    }
    result.result = payload
    return result


# Brain instances (shared across requests)
conversation_tracker = ConversationTracker()

# Unified desk manager (replaces both legacy DeskManager and AIDeskManager)
from app.services.max.desks.desk_manager import desk_manager
ai_desk_manager = desk_manager


class ChatRequest(BaseModel):
    message: str
    model: Optional[str] = None
    history: List[Dict[str, Any]] = []
    image_filename: Optional[str] = None
    desk: Optional[str] = None
    conversation_id: Optional[str] = None
    channel: Optional[str] = None  # "telegram", "web", etc.
    chat_id: Optional[str] = None  # Telegram chat ID for founder detection


TELEGRAM_DIRECTIVE = (
    "\n\n## CHANNEL: TELEGRAM\n"
    "This message is from Telegram. Respond ultra-short and direct.\n"
    "- No markdown headers, no bullet points unless specifically needed.\n"
    "- No greetings, no filler, no sign-offs.\n"
    "- Keep responses under 3 sentences when possible.\n"
    "- If the answer is a single fact or number, just say it.\n"
    "- IMPORTANT: You MUST still use ```tool blocks when actions are needed (web_search, quotes, etc). "
    "Tool blocks are the ONLY exception to the plain text rule — they are required for execution."
)


class ChatResponse(BaseModel):
    response: str
    model_used: str
    fallback_used: bool = False
    tool_results: Optional[List[Dict[str, Any]]] = None
    quality: Optional[Dict[str, Any]] = None
    response_id: Optional[str] = None  # for feedback linkage
    metadata: Optional[Dict[str, Any]] = None


class TaskCreateRequest(BaseModel):
    title: str
    description: str
    desk_id: Optional[str] = None
    domains: List[str] = []
    priority: int = 5


class TelegramMessageRequest(BaseModel):
    message: str
    urgent: bool = False


class PresentRequest(BaseModel):
    topic: str
    source_content: Optional[str] = None
    image_count: int = 3


ACTION_TOOLS = {
    "create_task",
    "queue_openclaw_task",
    "dispatch_to_openclaw",
    "run_desk_task",
    "delegate_to_atlas",
}


def _is_decision_only_request(message: str | None) -> bool:
    text = (message or "").lower()
    decision_markers = (
        "should this be",
        "should i",
        "whether this should",
        "tell me whether",
        "logged only or delegated",
        "log only or delegate",
        "logged or delegated",
        "recommend whether",
    )
    return any(marker in text for marker in decision_markers)


def _is_action_tool(tool_call: dict[str, Any]) -> bool:
    return str(tool_call.get("tool") or "").strip() in ACTION_TOOLS


def _decision_only_response(request: ChatRequest) -> ChatResponse:
    return ChatResponse(
        response=(
            "Decision-only request detected. I did not create, queue, or delegate anything.\n"
            "Recommendation: log this first unless you explicitly say to delegate it."
        ),
        model_used="decision-boundary",
        fallback_used=False,
        tool_results=[],
        metadata=_response_metadata(request.channel, skill_used="decision_boundary"),
    )


def _is_vendorops_request(message: str | None) -> bool:
    text = (message or "").lower()
    return "vendorops" in text or "vendor ops" in text


def _is_vendorops_write_request(message: str | None) -> bool:
    text = (message or "").lower()
    write_markers = (
        "approve",
        "reject",
        "provision",
        "create vendor",
        "create account",
        "edit vendor",
        "edit account",
        "cancel subscription",
        "activate",
        "upgrade",
        "start checkout",
    )
    return _is_vendorops_request(text) and any(marker in text for marker in write_markers)


def _format_vendorops_summary(summary: dict[str, Any]) -> str:
    activation = ((summary.get("vendorops") or {}).get("activation") or {})
    dashboard = summary.get("dashboard") or {}
    kpis = dashboard.get("kpis") or {}
    alerts = (summary.get("renewal_alerts") or {}).get("alerts") or []
    preferences = summary.get("alert_preferences") or {}
    sent = sum(1 for alert in alerts if alert.get("delivery_status") == "sent")
    failed = sum(1 for alert in alerts if alert.get("delivery_status") == "failed")
    queued = sum(1 for alert in alerts if alert.get("delivery_status") in {"queued", "queued_not_sent"})
    active_subscriptions = summary.get("active_subscriptions") or []
    upcoming = [
        f"{sub.get('vendor_name')} / {sub.get('plan_name')} renews {sub.get('renewal_date')} (${float(sub.get('monthly_cost_usd') or 0):.2f})"
        for sub in active_subscriptions[:5]
    ]
    lines = [
        "VendorOps query result (read-only).",
        f"- Active tier: {activation.get('tier')} ({activation.get('activation_state')})",
        f"- Checkout status: {activation.get('checkout_status')}",
        f"- Checkout completed at: {activation.get('completed_at') or 'not completed'}",
        f"- Monthly external-services cost: ${float(kpis.get('monthly_cost_total_usd') or 0):.2f}",
        f"- Active subscriptions: {kpis.get('active_subscriptions', 0)}",
        f"- Pending approvals: {kpis.get('pending_approvals', 0)}",
        f"- Renewal alerts: {len(alerts)} active ({queued} queued, {sent} sent, {failed} failed).",
        f"- Alert preferences: Telegram {'enabled' if preferences.get('telegram_enabled') else 'disabled'} / Email {'enabled' if preferences.get('email_enabled') else 'disabled'}.",
        "- Write gate: MAX can query VendorOps, but approvals/provisioning/cancellations require explicit founder-confirmed routes.",
    ]
    if upcoming:
        lines.append("- Upcoming renewals: " + "; ".join(upcoming))
    return "\n".join(lines)


def _vendorops_query_response(request: ChatRequest) -> ChatResponse:
    if _is_vendorops_write_request(request.message):
        return ChatResponse(
            response=(
                "VendorOps write request blocked. I can query VendorOps status, renewals, costs, and alerts, "
                "but I cannot approve, provision, activate, edit, or cancel VendorOps records without an explicit founder-confirmed route."
            ),
            model_used="vendorops-query",
            fallback_used=False,
            tool_results=[{"tool": "vendorops_summary", "success": False, "error": "write_gate_blocked"}],
            metadata=_response_metadata(request.channel, skill_used="vendorops_summary"),
        )
    try:
        from app.routers.vendorops import get_vendorops_max_summary
        summary = get_vendorops_max_summary()
        return ChatResponse(
            response=_format_vendorops_summary(summary),
            model_used="vendorops-query",
            fallback_used=False,
            tool_results=[{"tool": "vendorops_summary", "success": True, "result": summary}],
            metadata=_response_metadata(request.channel, skill_used="vendorops_summary"),
        )
    except Exception as exc:
        return ChatResponse(
            response=f"VendorOps query failed: {exc}",
            model_used="vendorops-query",
            fallback_used=False,
            tool_results=[{"tool": "vendorops_summary", "success": False, "error": str(exc)}],
            metadata=_response_metadata(request.channel, skill_used="vendorops_summary"),
        )


def _is_hermes_prefill_request(message: str | None) -> bool:
    try:
        from app.services.max.hermes_phase2 import is_prefill_request

        return is_prefill_request(message)
    except Exception:
        return False


def _hermes_prefill_response(request: ChatRequest) -> ChatResponse:
    try:
        from app.services.max.hermes_phase2 import (
            format_prefill_response,
            mark_draft_presented,
            prepare_prefill_draft_from_message,
        )

        draft = prepare_prefill_draft_from_message(request.message, channel=request.channel or "web")
        mark_draft_presented(draft["id"])
        response_text = format_prefill_response(draft)
        if _mentions_browser_assist(request.message):
            response_text += (
                "\n- No Hermes browser action was created from this request.\n"
                "- Phase 3 browser assist only reports real planned records; none exist for this request yet."
            )
        return ChatResponse(
            response=response_text,
            model_used="hermes-form-prep",
            fallback_used=False,
            tool_results=[{"tool": "hermes_form_prep", "success": True, "result": draft}],
            metadata=_response_metadata(request.channel, skill_used="hermes_form_prep"),
        )
    except Exception as exc:
        return ChatResponse(
            response=f"Hermes form-prep draft failed: {exc}",
            model_used="hermes-form-prep",
            fallback_used=False,
            tool_results=[{"tool": "hermes_form_prep", "success": False, "error": str(exc)}],
            metadata=_response_metadata(request.channel, skill_used="hermes_form_prep"),
        )


def _is_hermes_scheduled_request(message: str | None) -> bool:
    try:
        from app.services.max.hermes_phase2 import is_scheduled_result_request

        return is_scheduled_result_request(message)
    except Exception:
        return False


def _hermes_scheduled_response(request: ChatRequest) -> ChatResponse:
    try:
        from app.services.max.hermes_phase2 import (
            format_scheduled_results_response,
            list_scheduled_results,
            mark_scheduled_result_presented,
        )

        results = list_scheduled_results(limit=5)
        for item in results:
            if item.get("id"):
                mark_scheduled_result_presented(item["id"])
        return ChatResponse(
            response=format_scheduled_results_response(results),
            model_used="hermes-scheduled-intake",
            fallback_used=False,
            tool_results=[{"tool": "hermes_scheduled_intake", "success": True, "result": {"results": results}}],
            metadata=_response_metadata(request.channel, skill_used="hermes_scheduled_intake"),
        )
    except Exception as exc:
        return ChatResponse(
            response=f"Hermes scheduled-result intake failed: {exc}",
            model_used="hermes-scheduled-intake",
            fallback_used=False,
            tool_results=[{"tool": "hermes_scheduled_intake", "success": False, "error": str(exc)}],
            metadata=_response_metadata(request.channel, skill_used="hermes_scheduled_intake"),
        )


def _is_hermes_browser_plan_request(message: str | None) -> bool:
    try:
        from app.services.max.hermes_phase3 import is_browser_plan_request

        return is_browser_plan_request(message)
    except Exception:
        return False


def _hermes_browser_plan_response(request: ChatRequest) -> ChatResponse:
    try:
        from app.services.max.hermes_phase3 import create_browser_action_plan, format_browser_plan_response

        record = create_browser_action_plan(request.message, channel=request.channel or "web")
        return ChatResponse(
            response=format_browser_plan_response(record),
            model_used="hermes-browser-plan",
            fallback_used=False,
            tool_results=[{"tool": "hermes_browser_plan", "success": True, "result": record}],
            metadata=_response_metadata(request.channel, skill_used="hermes_browser_plan"),
        )
    except Exception as exc:
        return ChatResponse(
            response=f"Hermes browser plan failed: {exc}",
            model_used="hermes-browser-plan",
            fallback_used=False,
            tool_results=[{"tool": "hermes_browser_plan", "success": False, "error": str(exc)}],
            metadata=_response_metadata(request.channel, skill_used="hermes_browser_plan"),
        )


def _extract_hermes_browser_approval_id(message: str | None) -> str | None:
    try:
        from app.services.max.hermes_phase3 import parse_approval_request

        return parse_approval_request(message)
    except Exception:
        return None


def _hermes_browser_approval_response(request: ChatRequest, action_id: str) -> ChatResponse:
    try:
        from app.services.max.hermes_phase3 import approve_browser_action, format_browser_approval_response

        record = approve_browser_action(action_id, actor="founder")
        return ChatResponse(
            response=format_browser_approval_response(record),
            model_used="hermes-browser-approval",
            fallback_used=False,
            tool_results=[{"tool": "hermes_browser_approval", "success": True, "result": record}],
            metadata=_response_metadata(request.channel, skill_used="hermes_browser_approval"),
        )
    except Exception as exc:
        return ChatResponse(
            response=f"Hermes browser approval failed: {exc}",
            model_used="hermes-browser-approval",
            fallback_used=False,
            tool_results=[{"tool": "hermes_browser_approval", "success": False, "error": str(exc)}],
            metadata=_response_metadata(request.channel, skill_used="hermes_browser_approval"),
        )


def _extract_hermes_browser_execute_id(message: str | None) -> str | None:
    try:
        from app.services.max.hermes_phase3 import parse_execution_request

        return parse_execution_request(message)
    except Exception:
        return None


def _hermes_browser_execute_response(request: ChatRequest, action_id: str) -> ChatResponse:
    try:
        from app.services.max.hermes_phase3 import execute_browser_action, format_browser_execution_response

        result = execute_browser_action(action_id, actor="founder")
        return ChatResponse(
            response=format_browser_execution_response(result),
            model_used="hermes-browser-execute",
            fallback_used=False,
            tool_results=[{"tool": "hermes_browser_execute", "success": not result.get("error"), "result": result}],
            metadata=_response_metadata(request.channel, skill_used="hermes_browser_execute"),
        )
    except Exception as exc:
        return ChatResponse(
            response=f"Hermes browser execution failed: {exc}",
            model_used="hermes-browser-execute",
            fallback_used=False,
            tool_results=[{"tool": "hermes_browser_execute", "success": False, "error": str(exc)}],
            metadata=_response_metadata(request.channel, skill_used="hermes_browser_execute"),
        )


def _is_hermes_browser_log_request(message: str | None) -> bool:
    try:
        from app.services.max.hermes_phase3 import is_browser_log_request

        return is_browser_log_request(message)
    except Exception:
        return False


def _hermes_browser_log_response(request: ChatRequest) -> ChatResponse:
    try:
        from app.services.max.hermes_phase3 import format_browser_audit_response, read_browser_action_audit

        entries = read_browser_action_audit(limit=25)
        return ChatResponse(
            response=format_browser_audit_response(entries),
            model_used="hermes-browser-logs",
            fallback_used=False,
            tool_results=[{"tool": "hermes_browser_logs", "success": True, "result": {"entries": entries}}],
            metadata=_response_metadata(request.channel, skill_used="hermes_browser_logs"),
        )
    except Exception as exc:
        return ChatResponse(
            response=f"Hermes browser log read failed: {exc}",
            model_used="hermes-browser-logs",
            fallback_used=False,
            tool_results=[{"tool": "hermes_browser_logs", "success": False, "error": str(exc)}],
            metadata=_response_metadata(request.channel, skill_used="hermes_browser_logs"),
        )


def _is_hermes_channel_status_request(message: str | None) -> bool:
    try:
        from app.services.max.hermes_phase3 import is_channel_status_request

        return is_channel_status_request(message)
    except Exception:
        return False


def _hermes_channel_status_response(request: ChatRequest) -> ChatResponse:
    try:
        from app.services.max.hermes_phase3 import format_channel_status_response, get_channel_interfaces

        channels = get_channel_interfaces()
        return ChatResponse(
            response=format_channel_status_response(channels),
            model_used="hermes-channel-status",
            fallback_used=False,
            tool_results=[{"tool": "hermes_channel_status", "success": True, "result": channels}],
            metadata=_response_metadata(request.channel, skill_used="hermes_channel_status"),
        )
    except Exception as exc:
        return ChatResponse(
            response=f"Hermes channel status failed: {exc}",
            model_used="hermes-channel-status",
            fallback_used=False,
            tool_results=[{"tool": "hermes_channel_status", "success": False, "error": str(exc)}],
            metadata=_response_metadata(request.channel, skill_used="hermes_channel_status"),
        )


ARCHIVEFORGE_ROUTE_MARKERS = (
    "life magazine",
    "archiveforge",
    "cover search",
    "cover lookup",
    "issue lookup",
    "intake draft",
    "life intake",
)
EXPLICIT_DRAWING_OVERRIDE_PATTERNS = (
    r"\bdrawing\b",
    r"\bdraw\b",
    r"\brender\b",
    r"\bsketch\b",
    r"\bcad\b",
    r"\bspec drawing\b",
    r"\btechnical drawing\b",
    r"\bpdf drawing\b",
)
BROWSER_ASSIST_MARKERS = (
    "browser assist",
    "browser assistance",
    "browser action",
    "browser lookup",
    "browser plan",
)
EMAIL_SEND_TRUTH_PATTERNS = (
    r"^\s*send to my email\s*$",
    r"^\s*send this to my email\s*$",
    r"^\s*email this to me\s*$",
    r"^\s*send me an email\s*$",
    r"^\s*email me\s*$",
)
EMAIL_REPLY_READ_PATTERNS = (
    r"\bread my reply\b",
    r"\bcan you read my reply\b",
    r"\bwhat did (?:they|he|she) reply\b",
    r"\bshow me (?:the )?reply\b",
    r"\bquote (?:my|the) reply\b",
)
FAKE_BROWSER_ID_PATTERN = re.compile(r"\bhermes_browser(?:_id)?_[A-Za-z0-9_:-]+\b", re.IGNORECASE)


def _mentions_browser_assist(message: str | None) -> bool:
    text = (message or "").lower()
    return any(marker in text for marker in BROWSER_ASSIST_MARKERS)


def _is_archiveforge_request(message: str | None) -> bool:
    text = (message or "").lower()
    return any(marker in text for marker in ARCHIVEFORGE_ROUTE_MARKERS)


def _has_explicit_drawing_override(message: str | None) -> bool:
    text = (message or "").lower()
    if _explicit_no_drawing_router(message):
        return False
    if any(neg in text for neg in ("don't draw", "do not draw", "not asking for a drawing", "not asking you to draw")):
        return False
    return any(re.search(pattern, text) for pattern in EXPLICIT_DRAWING_OVERRIDE_PATTERNS)


def _prefer_archiveforge_over_drawing(message: str | None) -> bool:
    return _is_archiveforge_request(message) and not _has_explicit_drawing_override(message)


def _archiveforge_no_draft_response(request: ChatRequest) -> ChatResponse:
    response_lines = [
        "ArchiveForge/LIFE request routed to Hermes/ArchiveForge first.",
        "- No Hermes intake draft was created from this message.",
        "- This request reads like lookup/search work, not a complete intake draft yet.",
        "- If you want a draft, ask for `prepare LIFE magazine intake draft ...` with whatever fields you know.",
    ]
    if _mentions_browser_assist(request.message):
        response_lines.append("- No Hermes browser action was created from this request.")
        response_lines.append("- Phase 3 browser assist only returns real planned records; none exist yet.")
    return ChatResponse(
        response="\n".join(response_lines),
        model_used="hermes-form-prep",
        fallback_used=False,
        tool_results=[{
            "tool": "hermes_form_prep",
            "success": False,
            "error": "no_draft_created_from_request",
            "result": {
                "workflow_key": "life_magazine_intake",
                "draft_created": False,
                "archiveforge_route": True,
            },
        }],
        metadata=_response_metadata(request.channel, skill_used="hermes_form_prep"),
    )


def _is_unverified_email_send_request(message: str | None) -> bool:
    text = (message or "").strip().lower()
    return any(re.search(pattern, text) for pattern in EMAIL_SEND_TRUTH_PATTERNS)


def _is_email_reply_read_request(message: str | None) -> bool:
    text = (message or "").lower()
    return any(re.search(pattern, text) for pattern in EMAIL_REPLY_READ_PATTERNS)


def _email_send_boundary_response(request: ChatRequest) -> ChatResponse:
    return ChatResponse(
        response=(
            "Email MAX is partial.\n"
            "- I have not sent anything because there is no verified send result for this request.\n"
            "- I cannot claim an email or attachment was delivered without a real `send_email` or `send_quote_email` success result.\n"
            "- Tell me exactly what to send, and I will only confirm delivery after the send tool returns proof."
        ),
        model_used="email-truth-guardrail",
        fallback_used=False,
        tool_results=[{"tool": "email_truth_guardrail", "success": True, "result": {"sent": False, "verified_send_result": False}}],
        metadata=_response_metadata(request.channel),
    )


def _email_reply_boundary_response(request: ChatRequest) -> ChatResponse:
    return ChatResponse(
        response=(
            "Email MAX is partial.\n"
            "- I have not fetched the exact email thread/message for this request.\n"
            "- Reply threading continuity is partial, so I cannot quote or confirm a reply body from memory.\n"
            "- I can only present a reply body after the exact thread/message is actually fetched."
        ),
        model_used="email-truth-guardrail",
        fallback_used=False,
        tool_results=[{"tool": "email_truth_guardrail", "success": True, "result": {"reply_body_verified": False, "thread_continuity": "partial"}}],
        metadata=_response_metadata(request.channel),
    )


def _normalize_tool_result_entry(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return {
            "tool": item.get("tool"),
            "success": bool(item.get("success")),
            "result": item.get("result"),
            "error": item.get("error"),
        }
    return {
        "tool": getattr(item, "tool", None),
        "success": bool(getattr(item, "success", False)),
        "result": getattr(item, "result", None),
        "error": getattr(item, "error", None),
    }


def _has_verified_email_send_result(tool_results: list[Any] | None) -> bool:
    for item in tool_results or []:
        entry = _normalize_tool_result_entry(item)
        if entry.get("success") and entry.get("tool") in {"send_email", "send_quote_email"}:
            return True
    return False


def _real_browser_action_ids(tool_results: list[Any] | None) -> set[str]:
    valid_ids: set[str] = set()
    for item in tool_results or []:
        entry = _normalize_tool_result_entry(item)
        result = entry.get("result") or {}
        tool = entry.get("tool")
        if tool == "hermes_browser_plan" and isinstance(result, dict) and result.get("id"):
            valid_ids.add(str(result["id"]))
        if tool in {"hermes_browser_approval", "hermes_browser_execute"} and isinstance(result, dict):
            record = result.get("record") if tool == "hermes_browser_execute" else result
            if isinstance(record, dict) and record.get("id"):
                valid_ids.add(str(record["id"]))
    return valid_ids


def _apply_truth_guardrails(message: str | None, response_text: str, tool_results: list[Any] | None) -> str:
    if _is_unverified_email_send_request(message) and not _has_verified_email_send_result(tool_results):
        return _email_send_boundary_response(ChatRequest(message=message or "", history=[])).response

    if _is_email_reply_read_request(message):
        return _email_reply_boundary_response(ChatRequest(message=message or "", history=[])).response

    if _mentions_browser_assist(message):
        valid_ids = _real_browser_action_ids(tool_results)
        fake_ids = [match.group(0) for match in FAKE_BROWSER_ID_PATTERN.finditer(response_text) if match.group(0) not in valid_ids]
        if "simulated" in response_text.lower() or fake_ids:
            return (
                "No Hermes browser action was created from this request.\n"
                "- Phase 3 browser assist only reports real planned/approved/executed records from storage.\n"
                "- Valid flow: planned -> approved -> executed."
            )

    return response_text


def _maybe_handle_direct_route_request(request: ChatRequest) -> ChatResponse | None:
    browser_approval_id = _extract_hermes_browser_approval_id(request.message)
    if not request.desk and not request.image_filename and browser_approval_id:
        return _hermes_browser_approval_response(request, browser_approval_id)

    browser_execute_id = _extract_hermes_browser_execute_id(request.message)
    if not request.desk and not request.image_filename and browser_execute_id:
        return _hermes_browser_execute_response(request, browser_execute_id)

    if not request.desk and not request.image_filename and _is_hermes_browser_log_request(request.message):
        return _hermes_browser_log_response(request)

    if not request.desk and not request.image_filename and _is_hermes_channel_status_request(request.message):
        return _hermes_channel_status_response(request)

    if not request.desk and not request.image_filename and _prefer_archiveforge_over_drawing(request.message) and _is_hermes_prefill_request(request.message):
        return _hermes_prefill_response(request)

    if not request.desk and not request.image_filename and _is_hermes_browser_plan_request(request.message):
        return _hermes_browser_plan_response(request)

    if not request.desk and not request.image_filename and _is_hermes_prefill_request(request.message):
        return _hermes_prefill_response(request)

    if not request.desk and not request.image_filename and _prefer_archiveforge_over_drawing(request.message):
        return _archiveforge_no_draft_response(request)

    if not request.desk and not request.image_filename and _is_hermes_scheduled_request(request.message):
        return _hermes_scheduled_response(request)

    if not request.desk and not request.image_filename and _is_vendorops_request(request.message):
        return _vendorops_query_response(request)

    if not request.desk and not request.image_filename and _is_unverified_email_send_request(request.message):
        return _email_send_boundary_response(request)

    if not request.desk and not request.image_filename and _is_email_reply_read_request(request.message):
        return _email_reply_boundary_response(request)

    return None


def _stream_immediate_response(response: ChatResponse, conversation_id: str | None = None) -> StreamingResponse:
    async def gen():
        for tool_result in response.tool_results or []:
            yield f"data: {json.dumps({'type': 'tool_result', **tool_result})}\n\n"
        yield f"data: {json.dumps({'type': 'text', 'content': response.response})}\n\n"
        done = {
            "type": "done",
            "model_used": response.model_used,
            "conversation_id": conversation_id or str(uuid.uuid4()),
            "metadata": response.metadata,
        }
        if response.quality:
            done["quality"] = response.quality
        yield f"data: {json.dumps(done)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})


def _image_upload_path(image_filename: str | None) -> Path | None:
    if not image_filename:
        return None
    safe = Path(image_filename).name
    candidates = [
        Path.home() / "empire-repo" / "backend" / "data" / "uploads" / "images" / safe,
        Path.home() / "empire-repo" / "uploads" / "images" / safe,
        Path.home() / "empire-repo" / "backend" / "data" / "uploads" / safe,
    ]
    return next((path for path in candidates if path.exists()), None)


def _explicit_no_drawing_router(message: str | None) -> bool:
    text = (message or "").lower()
    return "do not use drawing-router" in text or "don't use drawing-router" in text or "no drawing-router" in text


@router.post("/chat", response_model=ChatResponse)
async def chat_with_max(request: ChatRequest, background_tasks: BackgroundTasks, http_response: Response):
    import time as _time_mod
    _chat_start = _time_mod.time()
    _response_id = str(uuid.uuid4())[:12]  # unique per request for feedback linkage

    msg_ctx = {"channel": request.channel or "", "chat_id": request.chat_id or ""}
    founder = is_founder_message(msg_ctx)
    if founder:
        logger.info(f"Founder message detected via chat_id={request.chat_id}")

    is_safe, reason = check_input(request.message, message_context=msg_ctx)
    if not is_safe:
        logger.warning(f"Blocked input ({reason}): {request.message[:100]}")
        return ChatResponse(response=SAFE_REFUSAL, model_used="guardrail", fallback_used=False)

    # v6.0 unified sanitizer — audit logging + SQL/XSS checks
    sec_result = input_sanitizer.check(request.message, channel="chat", session_id=request.conversation_id or "")
    if not sec_result["safe"]:
        logger.warning(f"Sanitizer blocked ({sec_result['threat_type']}): {request.message[:100]}")
        return ChatResponse(response=SAFE_REFUSAL, model_used="guardrail", fallback_used=False)

    for msg in request.history[-3:]:
        content = msg.get("content", "")
        # Skip guardrail check on system-injected context-pack messages
        if content.startswith("[Context from previous sessions]") or content == "Context loaded. Ready.":
            continue
        hist_safe, _ = check_input(content)
        if not hist_safe:
            return ChatResponse(response=SAFE_REFUSAL, model_used="guardrail", fallback_used=False)

    direct_route = _maybe_handle_direct_route_request(request)
    if direct_route is not None:
        return direct_route

    try:
        from app.services.max.continuity_compaction import (
            audit_continuity_state,
            create_founder_handoff,
            should_run_continuity_audit,
            should_handle_continuity_command,
        )
        if not request.desk and not request.image_filename and should_handle_continuity_command(request.message):
            handoff = await asyncio.to_thread(
                create_founder_handoff,
                message=request.message,
                channel=request.channel or "web",
                history=request.history,
            )
            packet = handoff["packet"]
            tier_1 = packet.get("tier_1", {})
            runtime = tier_1.get("last_runtime_truth_result") or {}
            score = handoff.get("latest_score") or {}
            active = handoff.get("active_task_state") or {}
            openclaw_count = len(active.get("openclaw_tasks") or [])
            max_task_count = len(active.get("max_tasks") or [])
            response_text = (
                "Session handoff refreshed.\n"
                f"- Packet: {handoff['path']}\n"
                f"- Registry: {tier_1.get('registry_version')}\n"
                f"- Surface: {(tier_1.get('founder_surface_identity') or {}).get('canonical_channel')}\n"
                f"- Runtime commit: {runtime.get('commit')}\n"
                f"- OpenClaw gate: {((runtime.get('openclaw_gate') or {}).get('state'))}\n"
                f"- Latest evaluation score: {score.get('overall_score')}\n"
                f"- Active task state: {openclaw_count} OpenClaw / {max_task_count} MAX tasks tracked."
            )
            metadata = _response_metadata(request.channel, skill_used="session_handoff")
            return ChatResponse(
                response=response_text,
                model_used="session-handoff",
                fallback_used=False,
                tool_results=[{"tool": "session_handoff", "success": True, "result": {"path": handoff["path"]}}],
                metadata=metadata,
            )
        if not request.desk and not request.image_filename and should_run_continuity_audit(request.message):
            audit = await asyncio.to_thread(audit_continuity_state, channel=request.channel or "web")
            handoff = audit.get("handoff") or {}
            tier_1 = handoff.get("tier_1") or {}
            score = audit.get("latest_score") or {}
            active = audit.get("active_task_state") or {}
            response_text = (
                "Continuity audit completed.\n"
                f"- Surface: {(audit.get('surface') or {}).get('canonical_channel')}\n"
                f"- Registry: {audit.get('registry_version')}\n"
                f"- Handoff loaded: {audit.get('handoff_loaded')}\n"
                f"- Current task: {tier_1.get('current_task')}\n"
                f"- Last runtime commit: {((tier_1.get('last_runtime_truth_result') or {}).get('commit'))}\n"
                f"- Latest evaluation score: {score.get('overall_score')}\n"
                f"- Active OpenClaw tasks tracked: {len(active.get('openclaw_tasks') or [])}\n"
                f"- Supermemory: {audit.get('supermemory_status')}."
            )
            metadata = _response_metadata(request.channel, skill_used="empire_max_continuity_audit")
            return ChatResponse(
                response=response_text,
                model_used="empire-max-continuity-audit",
                fallback_used=False,
                tool_results=[{"tool": "empire_max_continuity_audit", "success": True, "result": audit}],
                metadata=metadata,
            )
    except Exception as exc:
        metadata = _response_metadata(request.channel, skill_used="session_handoff")
        return ChatResponse(
            response=f"Session handoff refresh failed: {exc}",
            model_used="session-handoff",
            fallback_used=False,
            tool_results=[{"tool": "session_handoff", "success": False, "error": str(exc)}],
            metadata=metadata,
        )

    if not request.desk and not request.image_filename and should_run_runtime_truth_check(request.message):
        result = await asyncio.to_thread(execute_tool, _runtime_truth_tool_payload(), founder=founder)
        response_text = (
            format_runtime_truth_check(result.result or {})
            if result.success
            else f"Runtime truth check failed: {result.error}"
        )
        conv_id = _save_runtime_truth_exchange(request, response_text, result, founder)
        metadata = _response_metadata(request.channel, skill_used="empire_runtime_truth_check")
        await asyncio.to_thread(
            evaluation_service.log_response,
            response_id=_response_id,
            channel=request.channel or "web",
            conversation_id=conv_id,
            message=request.message,
            model_used="empire-runtime-truth-check",
            tools_used=["empire_runtime_truth_check"],
            tool_results=[{"tool": result.tool, "success": result.success}],
            latency_ms=int((_time_mod.time() - _chat_start) * 1000),
            response_length=len(response_text),
            fallback_used=False,
            metadata_envelope=metadata,
        )
        return ChatResponse(
            response=response_text,
            model_used="empire-runtime-truth-check",
            fallback_used=False,
            tool_results=[result.to_dict()],
            metadata=metadata,
        )

    if not request.desk and not request.image_filename and should_clarify_inventory_request(request.message):
        return ChatResponse(
            response=build_inventory_clarification(request.message),
            model_used="clarification-gate",
            fallback_used=False,
            tool_results=[],
            metadata=_response_metadata(request.channel, skill_used="inventory_ambiguity_gate"),
        )

    if request.image_filename and _image_upload_path(request.image_filename) is None:
        return ChatResponse(
            response="IMAGE_NOT_AVAILABLE",
            model_used="image-availability-check",
            fallback_used=False,
            tool_results=[],
            metadata=_response_metadata(request.channel, skill_used="image_availability_check"),
        )

    drawing_handoff = (
        build_drawing_handoff(request.message, image_filename=request.image_filename)
        if not _explicit_no_drawing_router(request.message) and not _prefer_archiveforge_over_drawing(request.message)
        else type("NoDrawingHandoff", (), {"is_drawing_intent": False})()
    )
    if drawing_handoff.is_drawing_intent:
        logger.info(
            "[MAX] Drawing intent intercepted before chat model: ready=%s missing=%s message=%r",
            drawing_handoff.ready,
            drawing_handoff.missing,
            request.message[:160],
        )
        if not drawing_handoff.ready:
            return ChatResponse(
                response=_drawing_missing_response(drawing_handoff),
                model_used="drawing-router",
                fallback_used=False,
                tool_results=None,
                metadata=_response_metadata(request.channel, skill_used="sketch_to_drawing"),
            )
        drawing_result = _execute_drawing_handoff(drawing_handoff)
        response_text = (
            "Drawing generated through Drawing Studio."
            if drawing_result.success
            else f"Drawing workflow failed: {drawing_result.error}"
        )
        return ChatResponse(
            response=response_text,
            model_used="drawing-router",
            fallback_used=False,
            tool_results=[_drawing_tool_result_dict(drawing_result)],
            metadata=_response_metadata(request.channel, skill_used="sketch_to_drawing"),
        )

    try:
        # Apply conversation windowing to prevent context overload
        windowed_history = _window_conversation(request.history)
        if len(windowed_history) < len(request.history):
            logger.info(f"Conversation windowed: {len(request.history)} -> {len(windowed_history)} messages")

        messages = [AIMessage(role=h["role"], content=h["content"]) for h in windowed_history]
        messages.append(AIMessage(role="user", content=request.message))
        model = None
        if request.model:
            try:
                model = AIModel(request.model)
            except ValueError:
                pass

        # Build brain-enriched system prompt (non-desk requests only)
        enriched_prompt = None
        if not request.desk:
            # Normalize channel for cross-channel context injection
            _ch = request.channel
            if _ch in {"web", "web_cc", "dashboard"}:
                _ch_normalized = "web_chat"
            else:
                _ch_normalized = _ch or "web"
            if not request.image_filename and is_ordinary_text_request(request.message):
                enriched_prompt = get_compact_system_prompt(channel=_ch_normalized)
            else:
                try:
                    enriched_prompt = await get_system_prompt_with_brain(
                        user_message=request.message,
                        conversation_history=request.history,
                    )
                except Exception as e:
                    logger.warning(f"Brain context failed, using base prompt: {e}")

        # Append channel-specific directives
        if request.channel == "telegram" and enriched_prompt:
            enriched_prompt += TELEGRAM_DIRECTIVE

        # Pass tool definitions to xAI when image is attached — enables native function_call
        # via /v1/responses endpoint (function_calls returned alongside or instead of text)
        _tools = get_xai_tool_definitions() if request.image_filename else None

        response = await asyncio.wait_for(
            ai_router.chat(messages, model=model, image_filename=request.image_filename, desk=request.desk, system_prompt=enriched_prompt, conversation_id=request.conversation_id or "", tools=_tools),
            timeout=45.0,
        )

        # Resolve access control user
        _ac_context = None
        if access_controller:
            try:
                _ac_user = access_controller.resolve_user(request.chat_id or request.conversation_id or "", request.channel or "web")
                if _ac_user:
                    _ac_context = {"user": _ac_user}
            except Exception as _ac_err:
                logger.debug(f"Access control resolve failed: {_ac_err}")

        # Extract PIN from chat message if present (e.g. "pin 7777" or just "7777")
        _extracted_pin = None
        _pin_match = re.search(r'\bpin\s+(\d{4,6})\b', request.message, re.IGNORECASE)
        if not _pin_match:
            # Bare PIN: message is only digits (4-6 chars)
            _bare = request.message.strip()
            if re.fullmatch(r'\d{4,6}', _bare):
                _pin_match_bare = _bare
                _extracted_pin = _bare
        if _pin_match and not _extracted_pin:
            _extracted_pin = _pin_match.group(1)
        if _extracted_pin and _ac_context is not None:
            _ac_context["pin"] = _extracted_pin
            logger.info(f"Extracted PIN from chat message for tool authorization")
        elif _extracted_pin and _ac_context is None:
            _ac_context = {"pin": _extracted_pin}

        # Multi-turn tool loop: execute tools, feed results back, allow follow-up tools (max 3 rounds)
        tool_results_list = []
        final_content = response.content
        loop_messages = list(messages)
        current_response = response

        for _tool_round in range(3):
            # Check for ```tool ... ``` blocks first (existing text-based format)
            tool_calls = parse_tool_blocks(current_response.content)
            # Also check xAI /v1/responses function_calls format
            if not tool_calls and hasattr(current_response, 'function_calls') and current_response.function_calls:
                tool_calls = current_response.function_calls
            if not tool_calls:
                break

            if _is_decision_only_request(request.message) and any(_is_action_tool(tc) for tc in tool_calls):
                return _decision_only_response(request)

            # File/git tool calls from main chat get re-routed to CodeForge desk
            # because Atlas (Opus) handles path expansion, validation, and smart truncation
            _CODEFORGE_TOOLS = {"file_read", "file_write", "file_edit", "file_append", "git_ops"}

            round_results = []
            for tc in tool_calls:
                # Inject image_filename into quote tools so uploaded photos flow through
                if request.image_filename and tc.get("tool") in ("create_quick_quote", "photo_to_quote") and "image_filename" not in tc:
                    tc["image_filename"] = request.image_filename

                # Auto-reroute file/git tools to CodeForge desk
                if tc.get("tool") in _CODEFORGE_TOOLS and not request.desk:
                    tool_name = tc["tool"]
                    path = tc.get("path", "")
                    desc_parts = [f"Tool: {tool_name}"]
                    if path:
                        desc_parts.append(f"Path: {path}")
                    if tc.get("content"):
                        desc_parts.append(f"Content: {tc['content'][:500]}")
                    if tc.get("command"):
                        desc_parts.append(f"Command: {tc['command']}")
                    if tc.get("old_str"):
                        desc_parts.append(f"Replace: {tc['old_str'][:200]} → {tc.get('new_str', '')[:200]}")
                    if tc.get("args"):
                        desc_parts.append(f"Args: {tc['args']}")

                    # Build descriptive title for CodeForge
                    if tool_name == "file_read":
                        title = f"Read {path}" if path else "Read file"
                    elif tool_name == "file_write":
                        title = f"Create {path}" if path else "Write file"
                    elif tool_name == "file_edit":
                        title = f"Edit {path}" if path else "Edit file"
                    elif tool_name == "file_append":
                        title = f"Append to {path}" if path else "Append to file"
                    elif tool_name == "git_ops":
                        title = f"Git {tc.get('command', 'status')}"
                    else:
                        title = tool_name

                    logger.info(f"[chat] Auto-routing {tool_name} to CodeForge: {title}")
                    tc = {"tool": "run_desk_task", "title": title, "description": " | ".join(desc_parts), "priority": "normal"}

                result = execute_tool(tc, desk=request.desk, access_context=_ac_context, founder=founder)
                entry = {"tool": result.tool, "success": result.success, "result": result.result, "error": result.error}
                round_results.append(entry)
                tool_results_list.append(entry)

            # Build tool summary and ask AI for follow-up
            tool_summary_parts = []
            for r in round_results:
                if r["success"] and r["result"]:
                    # Give web_read more room so AI has enough content to cite accurately
                    limit = 5000 if r['tool'] == 'web_read' else 3000
                    tool_summary_parts.append(f"[{r['tool']}] Result:\n{json.dumps(r['result'], indent=2, default=str)[:limit]}")
                else:
                    tool_summary_parts.append(f"[{r['tool']}] Error: {r.get('error', 'Unknown')}")
            tool_summary = "\n\n".join(tool_summary_parts)
            if any(r.get("tool") in ACTION_TOOLS and r.get("success") for r in round_results):
                tool_summary += (
                    "\n\n[SYSTEM: Task identity rule — if you mention a task/delegation id, "
                    "use only task_id/openclaw_task_id from the current tool result above. "
                    "Never use IDs from session handoff, active task state, or prior history.]"
                )

            is_last_round = _tool_round >= 2
            followup_instruction = (
                "[SYSTEM: Tool results below — use this data to give a complete, accurate answer. Do NOT output more tool blocks.]"
                if is_last_round else
                "[SYSTEM: Tool results below. You may call additional tools if needed to complete the task, or give a final answer.]"
            )

            loop_messages.append(AIMessage(role="assistant", content=strip_tool_blocks(current_response.content)))
            loop_messages.append(AIMessage(role="user", content=f"{followup_instruction}\n\n{tool_summary}"))

            current_response = await ai_router.chat(loop_messages, model=model, desk=request.desk, system_prompt=enriched_prompt, conversation_id=request.conversation_id or "", tools=_tools)
            # Only keep the FINAL round's response — previous rounds are context for the AI, not for the user
            final_content = current_response.content

        # Grounding verification: strip hallucinated citations from web-sourced responses
        if tool_results_list:
            has_web_tools = any(tr.get("tool") in ("web_search", "web_read") for tr in tool_results_list)
            if has_web_tools:
                try:
                    verification = verify_web_response(final_content, tool_results_list)
                    if verification.claims_stripped > 0:
                        logger.info(f"Grounding: {verification.claims_verified} verified, {verification.claims_stripped} stripped, {verification.phantom_citations_removed} phantom citations removed")
                    final_content = verification.verified
                    log_to_audit(
                        user_query=request.message,
                        verification=verification,
                        model_used=response.model_used,
                    )
                except Exception as e:
                    logger.warning(f"Grounding verification failed: {e}")

        # Universal quality check on final response
        chat_channel = Channel.TELEGRAM if (hasattr(request, 'channel') and request.channel == 'telegram') else Channel.CHAT
        qr = quality_engine.validate(final_content, channel=chat_channel, founder_override=founder)
        if qr.fixed_count > 0:
            logger.info(f"Quality engine fixed {qr.fixed_count} issues in {chat_channel.value} response")
            final_content = qr.cleaned

        final_content = _apply_truth_guardrails(request.message, final_content, tool_results_list)

        # Log to accuracy monitor (all channels, not just web-sourced)
        if qr.issues or not tool_results_list:
            try:
                from app.services.max.accuracy_monitor import accuracy_monitor
                accuracy_monitor.log_audit(
                    user_query=request.message,
                    response_text=final_content,
                    verification=type('V', (), {
                        'claims_found': len(qr.issues),
                        'claims_verified': len(qr.issues) - len([i for i in qr.issues if i.severity.value == 'critical']),
                        'claims_stripped': qr.fixed_count,
                        'phantom_citations_removed': 0,
                    })(),
                    model_used=response.model_used,
                    channel=chat_channel.value,
                    output_type="chat",
                    quality_severity=qr.severity,
                    fixed_by_engine=qr.fixed_count,
                )
            except Exception as e:
                logger.debug(f"Quality audit log failed: {e}")

        # Track conversation in background
        conv_id = request.conversation_id or str(uuid.uuid4())
        conversation_tracker.add_message(conv_id, "user", request.message)
        conversation_tracker.add_message(conv_id, "assistant", strip_tool_blocks(final_content))
        background_tasks.add_task(conversation_tracker.check_and_summarize, conv_id)

        # Save to unified cross-channel store
        try:
            from app.services.max.unified_message_store import unified_store
            user_metadata = _ledger_metadata(
                request.channel,
                {"image_filename": request.image_filename} if request.image_filename else None,
            )
            attachment_refs = [{"type": "upload", "ref": request.image_filename}] if request.image_filename else None
            unified_store.add_message(
                conv_id, request.channel or "web", "user", request.message,
                metadata=user_metadata,
                attachment_refs=attachment_refs,
                founder_verified=founder,
            )
            unified_store.add_message(
                conv_id, request.channel or "web", "assistant", strip_tool_blocks(final_content),
                model=response.model_used,
                tool_results=[{"tool": r.tool, "success": r.success} for r in tool_results_list] if tool_results_list else None,
                metadata=_ledger_metadata(request.channel, {"source": "max_chat_response"}),
            )
        except Exception as _ums_err:
            logger.warning(f"Unified message store write failed: {_ums_err}")

        # Backend-side chat history save (non-streaming, web/CC only)
        _nc = request.channel or "web"
        if _nc not in ("telegram", "phone"):
            try:
                import datetime as _dt
                _nc_user_dir = _ROUTER_CHATS_DIR / "founder"
                _nc_user_dir.mkdir(exist_ok=True)
                _nc_chat_id = conv_id[:8]
                _nc_chat_file = _nc_user_dir / f"{_nc_chat_id}.json"
                _nc_existing = {}
                if _nc_chat_file.exists():
                    try:
                        _nc_existing = json.loads(_nc_chat_file.read_text())
                    except Exception:
                        _nc_existing = {}
                _nc_msgs = _nc_existing.get("messages", [])
                _nc_new = [
                    {"role": "user", "content": request.message,
                     "timestamp": _dt.datetime.utcnow().isoformat()},
                    {"role": "assistant", "content": final_content,
                     "timestamp": _dt.datetime.utcnow().isoformat(),
                     "model": response.model_used},
                ]
                _nc_already = (
                    _nc_msgs
                    and _nc_msgs[-1].get("role") == "user"
                    and _nc_msgs[-1].get("content") == request.message
                )
                _nc_all = _nc_msgs if _nc_already else (_nc_msgs + _nc_new)
                _nc_chat_data = {
                    "id": _nc_chat_id,
                    "title": _nc_existing.get("title") or (request.message[:57] + "..." if len(request.message) > 60 else request.message),
                    "created_at": _nc_existing.get("created_at") or _dt.datetime.utcnow().isoformat(),
                    "updated_at": _dt.datetime.utcnow().isoformat(),
                    "pinned": _nc_existing.get("pinned", False),
                    "preview": (request.message[:120]).strip(),
                    "messages": _nc_all,
                }
                _nc_chat_file.write_text(json.dumps(_nc_chat_data, indent=2, default=str))
            except Exception as _nc_err:
                logger.debug(f"[chat] history save failed: {_nc_err}")

        # Learning: real-time (every exchange) or batch (every N messages)
        if REALTIME_LEARNING_ENABLED:
            background_tasks.add_task(
                conversation_tracker.learn_from_exchange,
                conv_id, request.message, response.content
            )
        elif BATCH_LEARNING_ENABLED:
            msg_count = conversation_tracker.get_message_count(conv_id)
            if msg_count > 0 and msg_count % BATCH_LEARNING_INTERVAL == 0:
                background_tasks.add_task(
                    conversation_tracker.learn_from_exchange,
                    conv_id, request.message, response.content
                )

        # Log token usage
        input_text = request.message + "".join(h.get("content", "") for h in request.history[-10:])
        token_tracker.log_chat(response.model_used, input_text, final_content, "chat", conv_id)

        # Auto-save valuable exchanges to shared memory store (web/CC conversations)
        _channel_source = request.channel or "web"
        if _channel_source != "telegram":  # Telegram auto-save handled in telegram_bot.py
            background_tasks.add_task(
                _auto_save_exchange_to_memory,
                request.message, final_content, _channel_source, conv_id,
            )

        # Quality gate — confidence level check
        try:
            from app.services.max.quality_gate import validate_response, get_response_suffix, get_quality_badge
            quality_result = validate_response(
                final_content,
                category=request.desk or "general",
                tool_results=tool_results_list,
                model_used=response.model_used,
            )
            quality_suffix = get_response_suffix(quality_result)
            if quality_suffix:
                final_content += quality_suffix
            quality_badge = get_quality_badge(quality_result)

            # Log quality metrics with response time
            _response_time_ms = (_time_mod.time() - _chat_start) * 1000
            _log_quality_metric(quality_result, response.model_used, request.channel or "web", _response_time_ms)
            logger.info(f"Response time: {_response_time_ms:.0f}ms | Quality: {quality_result.level} | Model: {response.model_used}")
        except Exception as qg_err:
            logger.debug(f"Quality gate error (non-fatal): {qg_err}")
            quality_badge = None

        resp = ChatResponse(
            response=sanitize_output(final_content),
            model_used=response.model_used,
            fallback_used=response.fallback_used,
            tool_results=tool_results_list if tool_results_list else None,
            quality=quality_badge,
            response_id=_response_id,
            metadata=_response_metadata(request.channel),
        )

        # Log response for evaluation loop (non-blocking)
        _final_latency_ms = int((_time_mod.time() - _chat_start) * 1000)
        background_tasks.add_task(
            evaluation_service.log_response,
            response_id=_response_id,
            channel=request.channel or "web",
            conversation_id=conv_id,
            message=request.message,
            model_used=response.model_used,
            tools_used=[r.get("tool") for r in tool_results_list] if tool_results_list else [],
            tool_results=tool_results_list if tool_results_list else [],
            latency_ms=_final_latency_ms,
            response_length=len(final_content),
            fallback_used=response.fallback_used,
            metadata_envelope=resp.metadata,
        )
        # Prevent phone/browser caching stale responses
        http_response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        http_response.headers["Pragma"] = "no-cache"
        return resp
    except asyncio.TimeoutError:
        logger.error("Chat request timed out after 45s")
        return ChatResponse(
            response="Request timed out after 45 seconds. The AI provider may be slow or unreachable. Please try again.",
            model_used="timeout",
            fallback_used=True,
            response_id=_response_id,
            metadata=_response_metadata(request.channel),
        )
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """SSE streaming endpoint for MAX chat with brain context."""
    msg_ctx = {"channel": request.channel or "", "chat_id": request.chat_id or ""}
    founder = is_founder_message(msg_ctx)
    if founder:
        logger.info(f"Founder message (stream) detected via chat_id={request.chat_id}")

    is_safe, reason = check_input(request.message, message_context=msg_ctx)
    if not is_safe:
        logger.warning(f"Blocked input ({reason}): {request.message[:100]}")
        async def refusal_gen():
            yield f"data: {json.dumps({'type': 'text', 'content': SAFE_REFUSAL})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'model_used': 'guardrail'})}\n\n"
        return StreamingResponse(refusal_gen(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})

    # v6.0 — unified sanitizer check on streaming endpoint
    sec_result = input_sanitizer.check(request.message, channel="chat", session_id=request.conversation_id or "")
    if not sec_result["safe"]:
        logger.warning(f"Sanitizer blocked stream ({sec_result['threat_type']}): {request.message[:100]}")
        async def refusal_gen():
            yield f"data: {json.dumps({'type': 'text', 'content': SAFE_REFUSAL})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'model_used': 'guardrail'})}\n\n"
        return StreamingResponse(refusal_gen(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})

    for msg in request.history[-3:]:
        content = msg.get("content", "")
        if content.startswith("[Context from previous sessions]") or content == "Context loaded. Ready.":
            continue
        hist_safe, _ = check_input(content)
        if not hist_safe:
            async def refusal_gen():
                yield f"data: {json.dumps({'type': 'text', 'content': SAFE_REFUSAL})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'model_used': 'guardrail'})}\n\n"
            return StreamingResponse(refusal_gen(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})

    direct_route = _maybe_handle_direct_route_request(request)
    if direct_route is not None:
        return _stream_immediate_response(direct_route, request.conversation_id)

    if not request.desk and not request.image_filename and should_run_runtime_truth_check(request.message):
        async def runtime_truth_gen():
            conv_id = request.conversation_id or str(uuid.uuid4())
            result = await asyncio.to_thread(execute_tool, _runtime_truth_tool_payload(), founder=founder)
            yield f"data: {json.dumps({'type': 'tool_result', **result.to_dict()})}\n\n"
            response_text = (
                format_runtime_truth_check(result.result or {})
                if result.success
                else f"Runtime truth check failed: {result.error}"
            )
            _save_runtime_truth_exchange(request, response_text, result, founder)
            yield f"data: {json.dumps({'type': 'text', 'content': response_text})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'model_used': 'empire-runtime-truth-check', 'conversation_id': conv_id, 'metadata': _response_metadata(request.channel, skill_used='empire_runtime_truth_check')})}\n\n"

        return StreamingResponse(runtime_truth_gen(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})

    if not request.desk and not request.image_filename and should_clarify_inventory_request(request.message):
        async def clarification_gen():
            yield f"data: {json.dumps({'type': 'text', 'content': build_inventory_clarification(request.message)})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'model_used': 'clarification-gate', 'metadata': _response_metadata(request.channel, skill_used='inventory_ambiguity_gate')})}\n\n"

        return StreamingResponse(clarification_gen(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})

    if request.image_filename and _image_upload_path(request.image_filename) is None:
        async def image_unavailable_gen():
            yield f"data: {json.dumps({'type': 'text', 'content': 'IMAGE_NOT_AVAILABLE'})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'model_used': 'image-availability-check', 'metadata': _response_metadata(request.channel, skill_used='image_availability_check')})}\n\n"
        return StreamingResponse(image_unavailable_gen(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})

    drawing_handoff = (
        build_drawing_handoff(request.message, image_filename=request.image_filename)
        if not _explicit_no_drawing_router(request.message) and not _prefer_archiveforge_over_drawing(request.message)
        else type("NoDrawingHandoff", (), {"is_drawing_intent": False})()
    )
    if drawing_handoff.is_drawing_intent:
        logger.info(
            "[MAX] Drawing intent intercepted before stream model: ready=%s missing=%s message=%r",
            drawing_handoff.ready,
            drawing_handoff.missing,
            request.message[:160],
        )

        async def drawing_gen():
            conv_id = request.conversation_id or str(uuid.uuid4())
            if not drawing_handoff.ready:
                yield f"data: {json.dumps({'type': 'text', 'content': _drawing_missing_response(drawing_handoff)})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'model_used': 'drawing-router', 'conversation_id': conv_id})}\n\n"
                return

            yield f"data: {json.dumps({'type': 'text', 'content': 'Starting the Drawing Studio workflow. '})}\n\n"
            result = _execute_drawing_handoff(drawing_handoff)
            yield f"data: {json.dumps({'type': 'tool_result', **_drawing_tool_result_dict(result)})}\n\n"
            final_text = (
                "Drawing generated through Drawing Studio."
                if result.success
                else f"Drawing workflow failed: {result.error}"
            )
            yield f"data: {json.dumps({'type': 'text', 'content': final_text})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'model_used': 'drawing-router', 'conversation_id': conv_id})}\n\n"

        return StreamingResponse(drawing_gen(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})

    # Apply conversation windowing
    windowed_history = _window_conversation(request.history)
    if len(windowed_history) < len(request.history):
        logger.info(f"[stream] Conversation windowed: {len(request.history)} -> {len(windowed_history)} messages")

    messages = [AIMessage(role=h["role"], content=h["content"]) for h in windowed_history]
    messages.append(AIMessage(role="user", content=request.message))
    model = None
    if request.model:
        try:
            model = AIModel(request.model)
        except ValueError:
            pass

    # Auto-switch to local if budget threshold reached
    if model != AIModel.OLLAMA and token_tracker.should_switch_to_local():
        logger.info("Budget threshold reached — auto-switching to Ollama")
        model = AIModel.OLLAMA

    # Build brain-enriched system prompt before streaming (non-desk only)
    enriched_prompt = None
    if not request.desk:
        # Normalize channel for cross-channel context injection
        _stream_ch = request.channel
        if _stream_ch in {"web", "web_cc", "dashboard"}:
            _stream_ch_normalized = "web_chat"
        else:
            _stream_ch_normalized = _stream_ch or "web"
        if not request.image_filename and is_ordinary_text_request(request.message):
            enriched_prompt = get_compact_system_prompt(channel=_stream_ch_normalized)
        else:
            try:
                enriched_prompt = await get_system_prompt_with_brain(
                    user_message=request.message,
                    conversation_history=request.history,
                )
            except Exception as e:
                logger.warning(f"Brain context failed, using base prompt: {e}")

    # Append channel-specific directives
    if request.channel == "telegram" and enriched_prompt:
        enriched_prompt += TELEGRAM_DIRECTIVE

    # Conversation tracking ID
    conv_id = request.conversation_id or str(uuid.uuid4())
    conversation_tracker.add_message(conv_id, "user", request.message)

    # Save user message to unified cross-channel store
    try:
        from app.services.max.unified_message_store import unified_store
        user_metadata = _ledger_metadata(
            request.channel,
            {"image_filename": request.image_filename} if request.image_filename else None,
        )
        attachment_refs = [{"type": "upload", "ref": request.image_filename}] if request.image_filename else None
        unified_store.add_message(
            conv_id, request.channel or "web", "user", request.message,
            metadata=user_metadata,
            attachment_refs=attachment_refs,
            founder_verified=founder,
        )
    except Exception as _ums_err:
        logger.warning(f"Unified message store (stream user) failed: {_ums_err}")

    # Resolve access control user for streaming
    _stream_ac_context = None
    if access_controller:
        try:
            _stream_ac_user = access_controller.resolve_user(request.chat_id or request.conversation_id or "", request.channel or "web")
            if _stream_ac_user:
                _stream_ac_context = {"user": _stream_ac_user}
        except Exception as _ac_err:
            logger.debug(f"Access control resolve failed (stream): {_ac_err}")

    async def event_generator():
        model_used = "unknown"
        full_response = ""
        try:
            async for chunk, m_used in ai_router.chat_stream(messages, model=model, image_filename=request.image_filename, desk=request.desk, system_prompt=enriched_prompt, source=request.channel or "", conversation_id=request.conversation_id or ""):
                model_used = m_used
                safe_chunk = sanitize_output(chunk)
                full_response += safe_chunk
                yield f"data: {json.dumps({'type': 'text', 'content': safe_chunk})}\n\n"

            # Multi-turn tool loop: execute tools, allow follow-up tools (max 3 rounds)
            tool_results_list = []
            loop_messages = list(messages)
            current_text = full_response

            for _tool_round in range(3):
                tool_calls = parse_tool_blocks(current_text)
                if not tool_calls:
                    break

                if _is_decision_only_request(request.message) and any(_is_action_tool(tc) for tc in tool_calls):
                    full_response = _decision_only_response(request).response
                    yield f"data: {json.dumps({'type': 'text', 'content': full_response})}\n\n"
                    break

                # File/git tool calls from main chat get re-routed to CodeForge desk
                _CODEFORGE_TOOLS_STREAM = {"file_read", "file_write", "file_edit", "file_append", "git_ops"}

                round_results = []
                for tc in tool_calls:
                    # Inject image_filename into quote tools so uploaded photos flow through
                    if request.image_filename and tc.get("tool") in ("create_quick_quote", "photo_to_quote") and "image_filename" not in tc:
                        tc["image_filename"] = request.image_filename

                    # Auto-reroute file/git tools to CodeForge desk
                    if tc.get("tool") in _CODEFORGE_TOOLS_STREAM and not request.desk:
                        tool_name = tc["tool"]
                        path = tc.get("path", "")
                        desc_parts = [f"Tool: {tool_name}"]
                        if path:
                            desc_parts.append(f"Path: {path}")
                        if tc.get("content"):
                            desc_parts.append(f"Content: {tc['content'][:500]}")
                        if tc.get("command"):
                            desc_parts.append(f"Command: {tc['command']}")
                        if tc.get("old_str"):
                            desc_parts.append(f"Replace: {tc['old_str'][:200]} → {tc.get('new_str', '')[:200]}")
                        if tc.get("args"):
                            desc_parts.append(f"Args: {tc['args']}")

                        if tool_name == "file_read":
                            title = f"Read {path}" if path else "Read file"
                        elif tool_name == "file_write":
                            title = f"Create {path}" if path else "Write file"
                        elif tool_name == "file_edit":
                            title = f"Edit {path}" if path else "Edit file"
                        elif tool_name == "file_append":
                            title = f"Append to {path}" if path else "Append to file"
                        elif tool_name == "git_ops":
                            title = f"Git {tc.get('command', 'status')}"
                        else:
                            title = tool_name

                        logger.info(f"[stream] Auto-routing {tool_name} to CodeForge: {title}")
                        tc = {"tool": "run_desk_task", "title": title, "description": " | ".join(desc_parts), "priority": "normal"}

                    result = execute_tool(tc, desk=request.desk, access_context=_stream_ac_context, founder=founder)
                    round_results.append(result)
                    tool_results_list.append(result)
                    yield f"data: {json.dumps({'type': 'tool_result', 'tool': result.tool, 'success': result.success, 'result': result.result, 'error': result.error})}\n\n"

                tool_summary_parts = []
                for r in round_results:
                    if r.success and r.result:
                        tool_summary_parts.append(f"[{r.tool}] Result:\n{json.dumps(r.result, indent=2, default=str)[:3000]}")
                    else:
                        tool_summary_parts.append(f"[{r.tool}] Error: {r.error}")
                tool_summary = "\n\n".join(tool_summary_parts)
                if any(r.tool in ACTION_TOOLS and r.success for r in round_results):
                    tool_summary += (
                        "\n\n[SYSTEM: Task identity rule — if you mention a task/delegation id, "
                        "use only task_id/openclaw_task_id from the current tool result above. "
                        "Never use IDs from session handoff, active task state, or prior history.]"
                    )

                is_last_round = _tool_round >= 2
                followup_instruction = (
                    "[SYSTEM: Tool results below — use this data to give a complete, accurate answer. Do NOT output more tool blocks.]"
                    if is_last_round else
                    "[SYSTEM: Tool results below. You may call additional tools if needed to complete the task, or give a final answer.]"
                )

                loop_messages.append(AIMessage(role="assistant", content=strip_tool_blocks(current_text)))
                loop_messages.append(AIMessage(role="user", content=f"{followup_instruction}\n\n{tool_summary}"))

                yield f"data: {json.dumps({'type': 'text', 'content': chr(10) + chr(10)})}\n\n"
                followup_text = ""
                async for chunk, m_used in ai_router.chat_stream(loop_messages, model=model, desk=request.desk, system_prompt=enriched_prompt, source=request.channel or "", conversation_id=request.conversation_id or ""):
                    model_used = m_used
                    safe_chunk = sanitize_output(chunk)
                    followup_text += safe_chunk
                    yield f"data: {json.dumps({'type': 'text', 'content': safe_chunk})}\n\n"

                current_text = followup_text
                # Only keep the FINAL round's response — previous rounds are context for the AI, not for the user
                full_response = followup_text

            # Track assistant response — fire-and-forget background tasks
            conversation_tracker.add_message(conv_id, "assistant", strip_tool_blocks(full_response))
            asyncio.create_task(_safe_background(
                conversation_tracker.check_and_summarize(conv_id),
                "summarization"
            ))

            # Save assistant response to unified cross-channel store
            try:
                from app.services.max.unified_message_store import unified_store
                unified_store.add_message(
                    conv_id, request.channel or "web", "assistant", strip_tool_blocks(full_response),
                    model=model_used,
                    tool_results=[{"tool": r.tool, "success": r.success} for r in tool_results_list] if tool_results_list else None,
                    metadata=_ledger_metadata(request.channel, {"source": "max_stream_response"}),
                )
            except Exception as _ums_err:
                logger.warning(f"Unified message store (stream assistant) failed: {_ums_err}")
            # Learning: real-time (every exchange) or batch (every N messages)
            if REALTIME_LEARNING_ENABLED:
                asyncio.create_task(_safe_background(
                    conversation_tracker.learn_from_exchange(conv_id, request.message, full_response),
                    "real-time learning"
                ))
            elif BATCH_LEARNING_ENABLED:
                msg_count = conversation_tracker.get_message_count(conv_id)
                if msg_count > 0 and msg_count % BATCH_LEARNING_INTERVAL == 0:
                    asyncio.create_task(_safe_background(
                        conversation_tracker.learn_from_exchange(conv_id, request.message, full_response),
                        "batch learning"
                    ))

            # Log token usage
            input_text = request.message + "".join(h.get("content", "") for h in request.history[-10:])
            token_tracker.log_chat(model_used, input_text, full_response, "chat/stream", conv_id)

            # Auto-save valuable exchanges to shared memory store (web/CC streaming)
            _stream_channel = request.channel or "web"
            if _stream_channel != "telegram":  # Telegram auto-save handled in telegram_bot.py
                _auto_save_exchange_to_memory(
                    request.message, full_response, _stream_channel, conv_id,
                )

            # ── Streaming quality checks (mirrors non-streaming /chat endpoint) ──
            _q_channel = Channel.TELEGRAM if (request.channel == "telegram") else Channel.CHAT

            # 1. Grounding verification for web-sourced responses
            _grounding_events = []
            if tool_results_list:
                # Convert result objects to dicts for verify_web_response
                _tool_dicts = [{"tool": r.tool, "success": r.success, "result": r.result, "error": r.error} for r in tool_results_list]
                _has_web = any(td["tool"] in ("web_search", "web_read") for td in _tool_dicts)
                if _has_web:
                    try:
                        _verification = verify_web_response(full_response, _tool_dicts)
                        if _verification.claims_stripped > 0:
                            logger.info(f"[stream] Grounding: {_verification.claims_verified} verified, {_verification.claims_stripped} stripped, {_verification.phantom_citations_removed} phantom citations removed")
                            full_response = _verification.verified
                            _grounding_events.append({
                                "type": "quality_fix",
                                "source": "grounding",
                                "claims_verified": _verification.claims_verified,
                                "claims_stripped": _verification.claims_stripped,
                                "phantom_citations_removed": _verification.phantom_citations_removed,
                            })
                        log_to_audit(
                            user_query=request.message,
                            verification=_verification,
                            model_used=model_used,
                        )
                    except Exception as _gv_err:
                        logger.warning(f"[stream] Grounding verification failed: {_gv_err}")

            # 2. Quality engine validation
            try:
                _qr = quality_engine.validate(full_response, channel=_q_channel, founder_override=founder)
                if _qr.fixed_count > 0:
                    logger.info(f"[stream] Quality engine fixed {_qr.fixed_count} issues in {_q_channel.value} response")
                    _original_len = len(full_response)
                    full_response = _qr.cleaned
                    yield f"data: {json.dumps({'type': 'quality_fix', 'source': 'quality_engine', 'original_length': _original_len, 'cleaned_length': len(full_response), 'issues': [str(i) for i in _qr.issues]})}\n\n"
                    # Update conversation tracker with cleaned version
                    conversation_tracker.add_message(conv_id, "assistant", strip_tool_blocks(full_response))
            except Exception as _qe_err:
                logger.warning(f"[stream] Quality engine failed: {_qe_err}")
                _qr = None

            # Emit grounding events (after quality engine so all fixes are sequential)
            for _ge in _grounding_events:
                yield f"data: {json.dumps(_ge)}\n\n"

            # 3. Accuracy monitor audit log
            try:
                from app.services.max.accuracy_monitor import accuracy_monitor
                _issues = _qr.issues if _qr else []
                _fixed = _qr.fixed_count if _qr else 0
                _severity = _qr.severity if _qr else None
                accuracy_monitor.log_audit(
                    user_query=request.message,
                    response_text=full_response,
                    verification=type('V', (), {
                        'claims_found': len(_issues),
                        'claims_verified': len(_issues) - len([i for i in _issues if i.severity.value == 'critical']),
                        'claims_stripped': _fixed,
                        'phantom_citations_removed': 0,
                    })(),
                    model_used=model_used,
                    channel=_q_channel.value,
                    output_type="chat/stream",
                    quality_severity=_severity,
                    fixed_by_engine=_fixed,
                )
            except Exception as _am_err:
                logger.debug(f"[stream] Quality audit log failed: {_am_err}")

            # Quality gate — confidence badge for streaming responses
            _quality_badge = None
            try:
                from app.services.max.quality_gate import validate_response as _qg_validate, get_quality_badge as _qg_badge
                _tool_dicts_for_qg = [{"tool": r.tool, "success": r.success, "result": r.result, "error": r.error} for r in tool_results_list] if tool_results_list else []
                _qg_result = _qg_validate(full_response, category=request.desk or "general", tool_results=_tool_dicts_for_qg, model_used=model_used)
                _quality_badge = _qg_badge(_qg_result)
                _log_quality_metric(_qg_result, model_used, request.channel or "web")
            except Exception as _qg_err:
                logger.debug(f"[stream] Quality gate error: {_qg_err}")

            # ── Backend-side chat history save (web/CC only) ─────────────────────
            # Write complete user+assistant exchange to JSON file so history is
            # available even if frontend auto-save is slow or races incorrectly.
            # Telegram uses its own _append_and_save (separate path).
            _save_channel = request.channel or "web"
            if _save_channel not in ("telegram", "phone"):
                try:
                    import datetime as _dt
                    _chat_user_dir = _ROUTER_CHATS_DIR / "founder"
                    _chat_user_dir.mkdir(exist_ok=True)
                    _chat_id_short = conv_id[:8]
                    _chat_file = _chat_user_dir / f"{_chat_id_short}.json"
                    _existing = {}
                    if _chat_file.exists():
                        try:
                            _existing = json.loads(_chat_file.read_text())
                        except Exception:
                            _existing = {}
                    # Preserve existing messages if this is a multi-turn continuation
                    _existing_msgs = _existing.get("messages", [])
                    # Build new messages from this exchange
                    _new_msgs = [
                        {"role": "user", "content": request.message,
                         "timestamp": _dt.datetime.utcnow().isoformat()},
                        {"role": "assistant", "content": full_response,
                         "timestamp": _dt.datetime.utcnow().isoformat(),
                         "model": model_used},
                    ]
                    # Deduplicate: if last message in file is same user msg, skip duplicate save
                    _already_has = (
                        _existing_msgs
                        and _existing_msgs[-1].get("role") == "user"
                        and _existing_msgs[-1].get("content") == request.message
                    )
                    if not _already_has:
                        _all_msgs = _existing_msgs + _new_msgs
                    else:
                        _all_msgs = _existing_msgs
                    _chat_data = {
                        "id": _chat_id_short,
                        "title": _existing.get("title") or (request.message[:57] + "..." if len(request.message) > 60 else request.message),
                        "created_at": _existing.get("created_at") or _dt.datetime.utcnow().isoformat(),
                        "updated_at": _dt.datetime.utcnow().isoformat(),
                        "pinned": _existing.get("pinned", False),
                        "preview": (request.message[:120]).strip(),
                        "messages": _all_msgs,
                    }
                    _chat_file.write_text(json.dumps(_chat_data, indent=2, default=str))
                except Exception as _save_err:
                    logger.debug(f"[stream] Chat history save failed: {_save_err}")

            _done_data = {
                'type': 'done',
                'model_used': model_used,
                'conversation_id': conv_id,
                'metadata': _response_metadata(request.channel),
            }
            if _quality_badge:
                _done_data['quality'] = _quality_badge
            yield f"data: {json.dumps(_done_data)}\n\n"
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})


@router.post("/present")
async def generate_presentation(request: PresentRequest):
    """Generate a structured presentation for a given topic."""
    from app.services.max.presentation_builder import build_presentation

    try:
        result = await build_presentation(
            topic=request.topic,
            source_content=request.source_content,
            image_count=request.image_count,
        )
        return result
    except Exception as e:
        logger.error(f"Presentation generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/present/pdf")
async def presentation_to_pdf(data: dict):
    """Render presentation data as PDF and return the file."""
    from app.services.max.tool_executor import _render_presentation_pdf
    from fastapi.responses import FileResponse

    try:
        pdf_path = _render_presentation_pdf(data)
        filename = os.path.basename(pdf_path)
        return FileResponse(pdf_path, media_type="application/pdf", filename=filename)
    except Exception as e:
        logger.error(f"Presentation PDF error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/presentations")
async def list_presentations():
    """List all saved presentation PDFs with metadata."""
    pres_dir = Path.home() / "empire-repo" / "backend" / "data" / "presentations"
    pres_dir.mkdir(parents=True, exist_ok=True)
    presentations = []
    for f in sorted(pres_dir.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True):
        stat = f.stat()
        # Parse title from filename: YYMMDD_HHMM_slug.pdf
        stem = f.stem
        parts = stem.split("_", 2)
        title_slug = parts[2] if len(parts) >= 3 else stem
        title = title_slug.replace("-", " ").title()
        presentations.append({
            "filename": f.name,
            "title": title,
            "size": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "url": f"/api/v1/max/presentations/{f.name}",
        })
    return {"presentations": presentations}


@router.get("/presentations/{filename}")
async def serve_presentation(filename: str):
    """Serve a saved presentation PDF."""
    from fastapi.responses import FileResponse
    pres_dir = Path.home() / "empire-repo" / "backend" / "data" / "presentations"
    file_path = pres_dir / filename
    if not file_path.exists() or not file_path.name.endswith(".pdf"):
        raise HTTPException(404, "Presentation not found")
    return FileResponse(file_path, media_type="application/pdf", filename=filename)


@router.delete("/presentations/{filename}")
async def delete_presentation(filename: str):
    """Delete a saved presentation PDF."""
    pres_dir = Path.home() / "empire-repo" / "backend" / "data" / "presentations"
    file_path = pres_dir / filename
    if not file_path.exists():
        raise HTTPException(404, "Presentation not found")
    file_path.unlink()
    return {"status": "deleted", "filename": filename}


@router.post("/present/telegram")
async def presentation_to_telegram(data: dict):
    """Render presentation as PDF and send via Telegram."""
    from app.services.max.tool_executor import _render_presentation_pdf

    try:
        pdf_path = _render_presentation_pdf(data)
        # Send via Telegram
        from app.services.max.telegram_bot import TelegramBot
        bot = TelegramBot()
        telegram_sent = False
        if bot.is_configured:
            title = data.get("title", "Presentation")
            section_count = len(data.get("sections", []))
            caption = f"\U0001f4ca <b>{title}</b>\n{section_count} sections \u00b7 {data.get('model_used', 'AI')}"
            await bot.send_document(pdf_path, caption=caption)
            telegram_sent = True
        return {"success": True, "pdf_path": pdf_path, "telegram_sent": telegram_sent}
    except Exception as e:
        logger.error(f"Presentation Telegram error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def get_available_models():
    return {"models": ai_router.get_available_models()}


@router.get("/desks")
async def get_all_desks():
    return {"desks": desk_manager.get_all_desks()}


@router.get("/desks/status")
async def get_desk_statuses():
    """Get status of all AI desks (ForgeDesk, MarketDesk, SocialDesk, SupportDesk).
    Alias for /ai-desks/status — kept for convenience.
    """
    statuses = await ai_desk_manager.get_all_statuses()
    return {"desks": statuses}


@router.get("/desks/{desk_id}")
async def get_desk(desk_id: str):
    desk = desk_manager.get_desk_legacy(desk_id)
    if not desk:
        raise HTTPException(status_code=404, detail=f"Desk {desk_id} not found")
    return desk


@router.post("/tasks")
async def create_task(request: TaskCreateRequest, background_tasks: BackgroundTasks):
    task = desk_manager.create_task(title=request.title, description=request.description, desk_id=request.desk_id, domains=request.domains, priority=request.priority)
    if telegram_bot.is_configured:
        background_tasks.add_task(telegram_bot.send_task_update, task.title, "started", task.description[:100], task.desk_id)
    return {"task": task.dict()}


@router.get("/tasks")
async def get_all_tasks(status: Optional[str] = None, desk_id: Optional[str] = None):
    task_status = TaskStatus(status) if status else None
    tasks = desk_manager.get_all_tasks(status=task_status, desk_id=desk_id)
    return {"tasks": tasks}


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    task = desk_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task": task}


@router.post("/tasks/{task_id}/complete")
async def complete_task(task_id: str, background_tasks: BackgroundTasks):
    task = desk_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    success = desk_manager.complete_task(task_id)
    if telegram_bot.is_configured:
        background_tasks.add_task(telegram_bot.send_task_update, task["title"], "completed", "", task["desk_id"])
    return {"status": "completed", "task_id": task_id}


@router.post("/tasks/{task_id}/fail")
async def fail_task(task_id: str, error: str = "Unknown error", background_tasks: BackgroundTasks = None):
    task = desk_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    success = desk_manager.fail_task(task_id, error)
    if telegram_bot.is_configured and background_tasks:
        background_tasks.add_task(telegram_bot.send_task_update, task["title"], "failed", error, task["desk_id"])
    return {"status": "failed", "task_id": task_id, "error": error}


@router.get("/stats")
async def get_stats():
    return {"stats": desk_manager.get_stats(), "telegram_connected": telegram_bot.is_configured}


# ── v6.0 Pipeline Endpoints ─────────────────────────────────────────

class PipelineCreateRequest(BaseModel):
    title: str
    description: str = ""
    source: str = "api"
    channel: str = "web"


class PipelineApprovalRequest(BaseModel):
    reason: str = ""


@router.post("/pipeline")
async def create_pipeline(request: PipelineCreateRequest, background_tasks: BackgroundTasks):
    """Create a new pipeline — AI decomposes task into ordered subtasks."""
    from app.services.max.pipeline import pipeline_engine
    result = await pipeline_engine.submit_pipeline(
        title=request.title,
        description=request.description or request.title,
        source=request.source,
        channel=request.channel,
    )
    if telegram_bot.is_configured:
        count = len(result.get("subtasks", []))
        background_tasks.add_task(
            telegram_bot.send_message,
            f"🚀 <b>New Pipeline</b>\n\n<b>{request.title}</b>\n{count} subtask(s) created\nSource: {request.source}",
        )
    return result


@router.get("/pipeline")
async def list_pipelines(active_only: bool = False, limit: int = 20):
    """List pipelines with progress summaries."""
    from app.services.max.pipeline import pipeline_engine
    if active_only:
        return {"pipelines": pipeline_engine.get_active_pipelines()}
    return {"pipelines": pipeline_engine.get_all_pipelines(limit=limit)}


@router.get("/pipeline/review")
async def get_review_tasks():
    """Get all subtasks awaiting founder approval."""
    from app.services.max.pipeline import pipeline_engine
    return {"tasks": pipeline_engine.get_review_tasks()}


@router.get("/pipeline/precheck")
async def pipeline_precheck():
    """Check API key dependencies and notify of blockers."""
    from app.services.max.pipeline import pipeline_engine
    return await pipeline_engine.pre_check_dependencies()


@router.get("/pipeline/audit")
async def pipeline_audit():
    """Audit ecosystem for unwired endpoints, missing frontends, and backlog items."""
    from app.services.max.pipeline import pipeline_engine
    return await pipeline_engine.audit_ecosystem()


@router.get("/pipeline/{pipeline_id}")
async def get_pipeline(pipeline_id: str):
    """Get a pipeline with all subtasks and progress."""
    from app.services.max.pipeline import pipeline_engine
    result = pipeline_engine.get_pipeline(pipeline_id)
    if not result:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return result


@router.post("/pipeline/{pipeline_id}/cancel")
async def cancel_pipeline(pipeline_id: str):
    """Cancel an active pipeline and all pending subtasks."""
    from app.services.max.pipeline import pipeline_engine
    result = await pipeline_engine.cancel_pipeline(pipeline_id)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/pipeline/task/{task_id}/approve")
async def approve_pipeline_task(task_id: str):
    """Founder approves a subtask in review state."""
    from app.services.max.pipeline import pipeline_engine
    result = await pipeline_engine.approve_subtask(task_id)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/pipeline/task/{task_id}/reject")
async def reject_pipeline_task(task_id: str, request: PipelineApprovalRequest = PipelineApprovalRequest()):
    """Founder rejects a subtask — sends back for re-execution."""
    from app.services.max.pipeline import pipeline_engine
    result = await pipeline_engine.reject_subtask(task_id, request.reason)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/security/stats")
async def security_stats():
    """Get security layer stats — blocked inputs, rate limits, audit counts."""
    stats = input_sanitizer.get_stats()
    # Count audit log entries
    audit_path = Path.home() / "empire-repo" / "backend" / "data" / "security" / "audit_log.jsonl"
    audit_count = 0
    if audit_path.exists():
        with open(audit_path) as f:
            audit_count = sum(1 for _ in f)
    stats["audit_log_entries"] = audit_count
    return stats


@router.get("/security/audit")
async def security_audit(limit: int = 50):
    """Get recent security audit log entries."""
    audit_path = Path.home() / "empire-repo" / "backend" / "data" / "security" / "audit_log.jsonl"
    if not audit_path.exists():
        return {"entries": [], "total": 0}
    entries = []
    with open(audit_path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(__import__("json").loads(line))
                except Exception:
                    pass
    # Return most recent first
    entries.reverse()
    return {"entries": entries[:limit], "total": len(entries)}


@router.get("/intelligence/brief")
async def get_morning_brief():
    """Get the latest morning brief (or generate on-demand)."""
    import json as _json
    brief_path = Path.home() / "empire-repo" / "backend" / "data" / "reports" / "morning_brief.json"
    if brief_path.exists():
        with open(brief_path) as f:
            return _json.load(f)
    # Generate on-demand if none exists
    from app.services.max.desks.desk_scheduler import desk_scheduler
    await desk_scheduler._generate_morning_brief()
    if brief_path.exists():
        with open(brief_path) as f:
            return _json.load(f)
    return {"date": None, "html": "No brief available yet.", "generated_at": None}


@router.get("/intelligence/weekly")
async def get_weekly_report():
    """Get the latest weekly report."""
    import json as _json
    report_path = Path.home() / "empire-repo" / "backend" / "data" / "reports" / "weekly_report.json"
    if report_path.exists():
        with open(report_path) as f:
            return _json.load(f)
    return {"week_of": None, "html": "No weekly report available yet.", "generated_at": None}


@router.post("/intelligence/brief/generate")
async def generate_morning_brief():
    """Force-generate a fresh morning brief now."""
    from app.services.max.desks.desk_scheduler import desk_scheduler
    await desk_scheduler._generate_morning_brief()
    import json as _json
    brief_path = Path.home() / "empire-repo" / "backend" / "data" / "reports" / "morning_brief.json"
    if brief_path.exists():
        with open(brief_path) as f:
            return _json.load(f)
    return {"status": "generated"}


@router.post("/intelligence/weekly/generate")
async def generate_weekly_report():
    """Force-generate a fresh weekly report now."""
    from app.services.max.desks.desk_scheduler import desk_scheduler
    await desk_scheduler._generate_weekly_report()
    import json as _json
    report_path = Path.home() / "empire-repo" / "backend" / "data" / "reports" / "weekly_report.json"
    if report_path.exists():
        with open(report_path) as f:
            return _json.load(f)
    return {"status": "generated"}


@router.get("/intelligence/cost-per-desk")
async def cost_per_desk():
    """Get AI cost breakdown per desk from token tracker logs."""
    try:
        from app.services.max.token_tracker import token_tracker
        from app.db.database import get_db
        import json as _json

        # Query token usage grouped by desk/caller
        costs_by_desk = {}
        with get_db() as conn:
            rows = conn.execute(
                """SELECT metadata, cost_usd FROM token_usage
                   WHERE date(timestamp) >= date('now', '-30 days')"""
            ).fetchall()
            for row in rows:
                cost = row[1] if len(row) > 1 else 0
                meta = {}
                try:
                    meta = _json.loads(row[0]) if row[0] else {}
                except Exception:
                    pass
                desk = meta.get("desk_id") or meta.get("caller") or "general"
                costs_by_desk[desk] = costs_by_desk.get(desk, 0) + (cost or 0)

        # Sort by cost descending
        sorted_desks = sorted(costs_by_desk.items(), key=lambda x: x[1], reverse=True)
        return {
            "period": "30d",
            "desks": [{"desk_id": d, "cost_usd": round(c, 4)} for d, c in sorted_desks],
            "total_usd": round(sum(c for _, c in sorted_desks), 4),
        }
    except Exception as e:
        # Fallback: return empty if token_usage table doesn't have the right columns
        return {"period": "30d", "desks": [], "total_usd": 0, "note": str(e)}


@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "MAX AI Assistant Manager", "desks_online": len(desk_manager.get_all_desks()), "telegram_configured": telegram_bot.is_configured}


@router.get("/status")
async def max_status():
    """Aggregated MAX operating status for runtime/evaluation freshness."""
    from app.services.max.operating_registry import get_registry_load_info, load_operating_registry
    from app.services.max.startup_health import read_startup_health_record
    from app.services.max.runtime_truth_check import _git_commit
    from app.services.max.openclaw_gate import check_openclaw_gate
    from app.services.max.hermes_memory import get_hermes_memory_status

    registry = load_operating_registry()
    skills = registry.get("skills", [])
    callable_hooks = [
        item.get("key")
        for item in skills
        if item.get("status") == "implemented_callable"
    ]
    return {
        "status": "ok",
        "current_commit": _git_commit(),
        "registry": get_registry_load_info(),
        "surfaces": [
            {
                "key": item.get("key"),
                "name": item.get("name"),
                "status": item.get("status"),
                "canonical_channel": item.get("canonical_channel"),
            }
            for item in registry.get("surfaces", [])
        ],
        "active_skill_hooks": callable_hooks,
        "startup_health": read_startup_health_record(),
        "hermes_memory_bridge": get_hermes_memory_status(),
        "openclaw_gate": check_openclaw_gate().to_dict(),
        "registry_reload_requires_restart": False,
    }


@router.get("/evaluation/scores")
async def max_evaluation_scores(limit: int = 10):
    """Recent Evaluation Loop v1 scores for MAX self-reporting."""
    from app.services.max.evaluation_loop_v1 import get_recent_scores
    return {"scores": get_recent_scores(limit=limit), "limit": limit}


@router.get("/self-assessment")
async def max_self_assessment(channel: str = "web", limit: int = 5):
    """Session-start quality check. Low recent scores trigger continuity audit."""
    from app.services.max.continuity_compaction import audit_continuity_state
    from app.services.max.evaluation_loop_v1 import get_recent_scores

    scores = get_recent_scores(limit=max(1, min(limit, 5)))
    average = round(sum(float(item.get("overall_score") or 0) for item in scores) / len(scores), 3) if scores else None
    should_audit = average is not None and average < 0.6
    audit = audit_continuity_state(channel=channel) if should_audit else None
    message = None
    if should_audit:
        message = (
            f"My recent responses averaged {average} truthfulness - "
            "I may be working from stale context. Running a continuity check."
        )
    return {
        "threshold": 0.6,
        "limit": min(limit, 5),
        "average_score": average,
        "should_run_continuity_audit": should_audit,
        "message": message,
        "skill_used": "empire_max_continuity_audit" if should_audit else None,
        "audit": audit,
        "scores": scores,
    }


@router.get("/supermemory/recall")
async def max_supermemory_recall(q: str = "max", channel: str = "web", limit: int = 5):
    """Ranked secondary recall. Never authoritative over runtime or registry truth."""
    from app.services.max.supermemory_recall import query_supermemory_recall
    return query_supermemory_recall(q, surface=channel, limit=limit)


@router.post("/supermemory/product-snapshots")
async def max_supermemory_product_snapshots():
    """Write compact registry-derived product snapshots to the Supermemory scaffold."""
    from app.services.max.supermemory_recall import write_product_snapshots
    return write_product_snapshots()


@router.get("/orchestration/status")
async def orchestration_status():
    """Canonical Command Center status for MAX as the orchestration brain."""
    import httpx

    async def _probe_json(url: str, timeout: float = 3.0) -> tuple[bool, Any]:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url)
            if resp.status_code >= 400:
                return False, {"status_code": resp.status_code}
            try:
                return True, resp.json()
            except Exception:
                return True, {}
        except Exception as e:
            return False, {"error": str(e)}

    from app.services.max.stt_service import stt_service
    from app.services.max.tts_service import tts_service
    from app.services.ollama_vision_router import (
        OLLAMA_URL,
        PRIMARY_VISION_MODEL,
        FALLBACK_VISION_MODEL,
        vision_model_order,
    )

    ollama_ok, ollama_data = await _probe_json(f"{OLLAMA_URL}/api/tags")
    openclaw_url = os.getenv("OPENCLAW_URL", "http://localhost:7878")
    openclaw_ok, openclaw_data = await _probe_json(f"{openclaw_url}/health")
    ollama_models = [m.get("name", "") for m in ollama_data.get("models", [])] if isinstance(ollama_data, dict) else []
    normalized_ollama_models = {m.split(":")[0] for m in ollama_models}
    openclaw_stats: Dict[str, Any] = {}
    recent_openclaw_tasks: List[Dict[str, Any]] = []
    try:
        from app.db.database import get_db, dict_rows
        with get_db() as db:
            rows = db.execute("SELECT status, COUNT(*) as count FROM openclaw_tasks GROUP BY status").fetchall()
            openclaw_stats = {row[0]: row[1] for row in rows}
            openclaw_stats["total"] = sum(openclaw_stats.values())
            recent_openclaw_tasks = dict_rows(db.execute(
                """SELECT id, title, desk, status, source, created_at, completed_at, result, error
                   FROM openclaw_tasks
                   ORDER BY id DESC LIMIT 5"""
            ).fetchall())
    except Exception as e:
        openclaw_stats = {"error": str(e)}

    code_mode_status: Dict[str, Any]
    try:
        from app.services.max.code_task_runner import code_task_runner
        tasks = list(code_task_runner._tasks.values())
        active_tasks = [t for t in tasks if t.state.value in ("queued", "running")]
        code_mode_status = {
            "available": True,
            "mode": "subordinate_to_max",
            "executor": "CodeForge / Atlas",
            "endpoint": "/api/v1/max/code-task",
            "active_tasks": len(active_tasks),
            "recent_tasks": [
                {
                    "id": t.id,
                    "state": t.state.value,
                    "prompt": t.prompt[:120],
                    "files_changed": t.files_changed[:5],
                    "error": t.error,
                }
                for t in tasks[-5:]
            ],
            "allowed_tools": [
                "file_read", "file_write", "file_edit", "file_append", "git_ops",
                "test_runner", "shell_execute", "package_manager", "service_manager",
                "project_scaffold",
            ],
        }
    except Exception as e:
        code_mode_status = {"available": False, "error": str(e)}

    self_heal_status: Dict[str, Any]
    try:
        from app.services.max.self_heal import get_heal_status
        self_heal_status = {
            "mode": "guided_self_heal",
            "full_autonomous_repair_verified": False,
            "path": "MAX diagnosis -> Code Mode/CodeForge -> tests -> targeted service restart -> verification -> founder report",
            "status": get_heal_status(),
        }
    except Exception as e:
        self_heal_status = {"mode": "guided_self_heal", "error": str(e)}

    desks = desk_manager.get_all_desks()
    try:
        desk_statuses = await ai_desk_manager.get_all_statuses()
    except Exception:
        desk_statuses = []

    configured_models = ai_router.get_available_models()
    cloud_providers = [
        {
            "id": model["id"],
            "name": model["name"],
            "configured": bool(model["available"]),
            "primary": bool(model.get("primary")),
            "status_source": "env_configured",
            **({"model": model["model"]} if model.get("model") else {}),
            **({"base_url": model["base_url"]} if model.get("base_url") else {}),
        }
        for model in configured_models
        if model.get("type") == "cloud"
    ]

    local_vision_order = vision_model_order()
    local_vision_ready = ollama_ok and all(
        candidate in normalized_ollama_models
        or any(model == candidate or model.startswith(f"{candidate}:") for model in ollama_models)
        for candidate in [PRIMARY_VISION_MODEL, FALLBACK_VISION_MODEL]
    )

    return {
        "role": {
            "founder": "top",
            "max": "primary_command_center_brain",
            "ai_desks": "subordinate_specialists",
            "openclaw": "execution_delegation_layer",
        },
        "entrypoints": {
            "web_chat": "/api/v1/max/chat/stream",
            "telegram_chat": "/api/v1/max/chat",
            "voice_stt": "/api/v1/voice/transcribe",
            "voice_tts": "/api/v1/max/tts",
            "upload": "/api/v1/files/upload",
            "desk_tasks": "/api/v1/max/ai-desks/tasks",
            "openclaw": "/api/v1/openclaw/tasks",
        },
        "routing": {
            "normal_web_chat": "simple: Gemini -> Grok -> Groq -> Claude Sonnet; moderate: Grok -> Groq -> Claude Sonnet -> Gemini; complex: Claude Sonnet -> Grok -> OpenAI GPT-4o -> Groq; critical/code: Claude Opus -> Claude Sonnet",
            "telegram_chat": "MAX chat with Telegram brevity directive and founder channel persistence",
            "voice_input": "Groq Whisper STT through /api/v1/voice/transcribe; transcribed text enters MAX chat",
            "voice_output": "xAI Grok TTS through /api/v1/max/tts",
            "image_analysis": f"local Ollama triage {PRIMARY_VISION_MODEL} -> {FALLBACK_VISION_MODEL}, then MAX cloud routing as needed",
            "document_analysis": "uploaded PDF/text/code content is extracted and prepended to MAX chat context",
            "desk_delegation": "MAX run_desk_task / ai-desks tasks; CodeForge uses Claude Opus; finance/support/sales/etc. use desk routing",
            "openclaw_execution": "MAX tools can dispatch or queue OpenClaw tasks below desk/MAX control",
        },
        "providers": {
            "cloud": cloud_providers,
            "local": [
                {
                    "id": "ollama",
                    "name": "Ollama",
                    "online": ollama_ok,
                    "status_source": "live_http",
                    "models": ollama_models,
                },
                {
                    "id": "openclaw",
                    "name": "OpenClaw",
                    "online": openclaw_ok,
                    "status_source": "live_http",
                    "detail": openclaw_data,
                    "queue_stats": openclaw_stats,
                    "recent_tasks": recent_openclaw_tasks,
                },
            ],
        },
        "capabilities": {
            "text_chat": True,
            "image_upload_analysis": local_vision_ready or ollama_ok,
            "document_upload_analysis": True,
            "voice_input": stt_service.is_configured,
            "voice_output": tts_service.is_configured and tts_service.get_status().get("last_status") != "failed",
            "desk_delegation": len(desks) > 0,
            "openclaw_delegation": openclaw_ok,
        },
        "local_vision": {
            "online": ollama_ok,
            "ready": local_vision_ready,
            "primary": PRIMARY_VISION_MODEL,
            "fallback": FALLBACK_VISION_MODEL,
            "route": local_vision_order,
            "installed_models": ollama_models,
        },
        "desks": {
            "count": len(desks),
            "statuses": desk_statuses,
        },
        "voice": {
            "stt_service": "groq-whisper" if stt_service.is_configured else "unconfigured",
            "tts_service": "grok-tts" if tts_service.is_configured else "unconfigured",
            "stt": stt_service.get_status(),
            "tts": tts_service.get_status(),
        },
        "code_mode": code_mode_status,
        "self_heal": self_heal_status,
        "uploads": {
            "accepted_categories": ["images", "documents", "audio", "code"],
            "command_center_max_accept": ["image/*", ".pdf", ".txt", ".md", ".csv", ".json"],
        },
        "checked_at": datetime.utcnow().isoformat(),
    }


@router.post("/telegram/send")
async def send_telegram_message(request: TelegramMessageRequest):
    if not telegram_bot.is_configured:
        raise HTTPException(status_code=400, detail="Telegram not configured")
    if request.urgent:
        success = await telegram_bot.send_urgent_alert("Manual Alert", request.message)
    else:
        success = await telegram_bot.send_message(request.message)
    return {"success": success}


@router.get("/telegram/status")
async def telegram_status():
    return {"configured": telegram_bot.is_configured, "bot_token_set": bool(telegram_bot.bot_token), "chat_id_set": bool(telegram_bot.founder_chat_id)}


@router.get("/telegram/image/{filename}")
async def serve_telegram_image(filename: str):
    """Serve a Telegram-uploaded image."""
    from fastapi.responses import FileResponse
    img_path = Path.home() / "empire-repo" / "backend" / "data" / "uploads" / "images" / filename
    if not img_path.exists() or not img_path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    # Prevent path traversal
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    ext = img_path.suffix.lower()
    media_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    return FileResponse(str(img_path), media_type=media_types.get(ext, "image/jpeg"))


@router.get("/telegram/history")
async def get_telegram_history(chat_id: Optional[str] = None, limit: int = 50):
    """Get Telegram conversation history (persisted to disk).

    When chat_id is explicitly provided: returns messages for that chat.
    When chat_id is omitted (None): returns list of all Telegram chat files.
    """
    from app.services.max.telegram_bot import _TELEGRAM_CHAT_DIR, _get_history
    from fastapi import Query

    # Explicitly None means "list all chats" — explicit value means "get this chat"
    # Use default=None for Query param so we can detect explicit vs omitted
    target = chat_id
    if target is None:
        # No chat_id provided — return list of all chat files
        chats = []
        for f in sorted(_TELEGRAM_CHAT_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                import json as _j
                data = _j.loads(f.read_text())
                msgs = data.get("messages", [])
                chats.append({
                    "chat_id": f.stem,
                    "message_count": len(msgs),
                    "updated_at": data.get("updated_at"),
                    "last_message": msgs[-1]["content"][:100] if msgs else "",
                })
            except Exception:
                pass
        return {
            "scope": "telegram_only",
            "canonical_channel": "telegram",
            "unified_history_route": "/api/v1/chats/memory-bank?channel=all",
            "note": "This endpoint lists Telegram disk history only. Use the unified history route for All Channels.",
            "chats": chats,
        }
    messages = _get_history(str(target))
    return {
        "scope": "telegram_only",
        "canonical_channel": "telegram",
        "unified_history_route": "/api/v1/chats/memory-bank?channel=all",
        "chat_id": str(target),
        "messages": messages[-limit:],
        "total": len(messages),
    }


class AccessConfirmRequest(BaseModel):
    session_id: str


class AccessPinRequest(BaseModel):
    session_id: str
    pin: str


@router.post("/access/confirm")
async def access_confirm(request: AccessConfirmRequest):
    if not access_controller:
        raise HTTPException(status_code=501, detail="Access control not available")
    result = access_controller.confirm_session(request.session_id)
    if not result:
        raise HTTPException(status_code=400, detail="Session expired or not found")
    tr = execute_tool({"tool": result["tool_name"], **result["tool_params"]}, desk=result.get("desk"))
    access_controller.audit_log(result.get("user_id", ""), result["tool_name"], 2, "confirmed", channel="web")
    return {"tool": tr.tool, "success": tr.success, "result": tr.result, "error": tr.error}


@router.post("/access/pin")
async def access_pin(request: AccessPinRequest):
    if not access_controller:
        raise HTTPException(status_code=501, detail="Access control not available")
    result = access_controller.authorize_pin_session(request.session_id, request.pin)
    if not result:
        raise HTTPException(status_code=403, detail="Invalid PIN or session expired")
    tr = execute_tool({"tool": result["tool_name"], **result["tool_params"]}, desk=result.get("desk"))
    access_controller.audit_log(result.get("user_id", ""), result["tool_name"], 3, "pin_authorized", channel="web")
    return {"tool": tr.tool, "success": tr.success, "result": tr.result, "error": tr.error}


@router.get("/brain/status")
async def brain_status():
    """Get MAX Brain status — memory counts, drive status, Ollama health."""
    from app.services.max.brain.brain_config import get_brain_path, get_db_path, OLLAMA_BASE_URL
    from app.services.max.brain.memory_store import MemoryStore
    import httpx

    brain_path = get_brain_path()
    db_path = get_db_path()
    is_external = False  # brain is local-only now (NVMe primary)

    # Memory stats
    try:
        store = MemoryStore(db_path)
        memory_count = store.count()
    except Exception as e:
        memory_count = -1
        logger.warning(f"Brain DB error: {e}")

    # Ollama health
    ollama_ok = False
    ollama_models = []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if resp.status_code == 200:
                ollama_ok = True
                ollama_models = [m["name"] for m in resp.json().get("models", [])]
    except Exception:
        pass

    return {
        "brain_online": memory_count >= 0 and ollama_ok,
        "storage": {
            "path": str(brain_path),
            "external_drive": is_external,
            "db_path": db_path,
        },
        "memories": {
            "total": memory_count,
        },
        "ollama": {
            "online": ollama_ok,
            "url": OLLAMA_BASE_URL,
            "models": ollama_models,
        },
        "conversations": {
            "active": conversation_tracker.get_active_count(),
        },
    }


@router.get("/tokens/stats")
async def get_token_stats(days: int = 30):
    """Get token usage statistics and cost tracking."""
    return token_tracker.get_stats(days=days)


class BudgetUpdateRequest(BaseModel):
    monthly_budget: Optional[float] = None
    alert_threshold: Optional[float] = None
    auto_switch_to_local: Optional[bool] = None
    auto_switch_threshold: Optional[float] = None


@router.patch("/tokens/budget")
async def update_budget(request: BudgetUpdateRequest):
    """Update monthly budget configuration."""
    token_tracker.update_budget(
        monthly_budget=request.monthly_budget,
        alert_threshold=request.alert_threshold,
        auto_switch=request.auto_switch_to_local,
        auto_switch_threshold=request.auto_switch_threshold,
    )
    return {"status": "updated"}


# ── AI Desk Delegation System ────────────────────────────────────────────


class DeskTaskRequest(BaseModel):
    title: str
    description: str
    priority: str = "normal"
    customer_name: Optional[str] = None
    source: str = "founder"
    conversation_id: Optional[str] = None


@router.post("/ai-desks/tasks")
async def submit_desk_task(request: DeskTaskRequest):
    """Submit a task to the AI desk delegation system.
    Task is routed to the appropriate desk automatically.
    """
    task = await ai_desk_manager.submit_task(
        title=request.title,
        description=request.description,
        priority=request.priority,
        customer_name=request.customer_name,
        source=request.source,
        conversation_id=request.conversation_id,
    )
    return {
        "task_id": task.id,
        "title": task.title,
        "state": task.state.value,
        "escalation_reason": task.escalation_reason,
        "result": task.result,
        "actions": [{"action": a.action, "detail": a.detail, "timestamp": a.timestamp} for a in task.actions],
    }


@router.get("/ai-desks/status")
async def get_ai_desk_statuses():
    """Get status of all AI desks."""
    statuses = await ai_desk_manager.get_all_statuses()
    return {"desks": statuses}


@router.get("/ai-desks/{desk_id}/detail")
async def get_ai_desk_detail(desk_id: str):
    """Get detailed status and task history for a single AI desk."""
    desk = ai_desk_manager.get_desk(desk_id)
    if not desk:
        raise HTTPException(404, f"Desk '{desk_id}' not found")
    status = await desk.report_status()
    # Also include brain memory logs for this desk
    try:
        from app.services.max.brain.memory_store import MemoryStore
        store = MemoryStore()
        memories = store.search(query=desk.desk_name, category="desk_action", limit=20)
        status["brain_logs"] = [
            {"content": m.get("content", ""), "created_at": m.get("created_at", ""), "importance": m.get("importance", 5)}
            for m in memories
        ]
    except Exception:
        status["brain_logs"] = []
    return status


@router.get("/ai-desks/briefing")
async def get_desk_briefing():
    """Get morning briefing from all AI desks."""
    briefing = await ai_desk_manager.generate_briefing()
    return {"briefing": briefing}


@router.post("/ai-desks/trigger")
async def trigger_desk_task(request: DeskTaskRequest):
    """Manually trigger a desk task immediately (bypasses schedule).
    Executes with AI, stores result, sends Telegram notification."""
    from app.services.max.desks.desk_scheduler import desk_scheduler
    import asyncio

    # Determine desk from title/description keywords, or use source as desk hint
    desk_id = request.source if request.source in [
        "forge", "sales", "marketing", "support", "finance", "it",
        "market", "clients", "contractors", "website", "legal", "lab",
    ] else None

    if not desk_id:
        # Route automatically
        task = await ai_desk_manager.submit_task(
            title=request.title,
            description=request.description,
            priority=request.priority,
            source="manual_trigger",
        )
        return {
            "task_id": task.id,
            "title": task.title,
            "desk": "auto-routed",
            "state": task.state.value,
            "result": task.result,
        }

    # Direct desk execution with AI + Telegram
    asyncio.create_task(
        desk_scheduler.trigger_now(desk_id, request.title, request.description)
    )
    return {
        "status": "triggered",
        "desk": desk_id,
        "title": request.title,
        "message": f"Task sent to {desk_id} desk. Result will be sent to Telegram.",
    }


@router.get("/ai-desks/report")
async def get_desk_daily_report():
    """Get end-of-day desk report."""
    report = await ai_desk_manager.generate_daily_report()
    return {"report": report}


# ── Quality Gate Metrics ─────────────────────────────────────────────


@router.get("/quality/metrics")
async def get_quality_metrics():
    """Get quality gate metrics for today."""
    import sqlite3
    db_path = os.path.expanduser("~/empire-repo/backend/data/empire.db")
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT quality_level, COUNT(*) as count
            FROM quality_metrics
            WHERE date(timestamp) = date('now')
            GROUP BY quality_level
        """).fetchall()
        total = conn.execute("""
            SELECT COUNT(*) FROM quality_metrics WHERE date(timestamp) = date('now')
        """).fetchone()[0]
        conn.close()

        breakdown = {r["quality_level"]: r["count"] for r in rows}
        return {
            "today_total": total,
            "verified": breakdown.get("verified", 0),
            "high": breakdown.get("high", 0),
            "moderate": breakdown.get("moderate", 0),
            "low": breakdown.get("low", 0),
            "failed": breakdown.get("failed", 0),
        }
    except Exception as e:
        return {"today_total": 0, "error": str(e)}


# ── Code Mode — Async Code Tasks ─────────────────────────────────────


class CodeTaskRequest(BaseModel):
    prompt: str
    pin: str = ""
    channel: str = "web_cc"


@router.post("/code-task")
async def submit_code_task(request: CodeTaskRequest):
    """Submit an async code task to CodeForge/Atlas.
    Founder channels (web_cc, telegram founder) skip PIN.
    Non-founder channels require PIN.
    Poll status via GET /code-task/{id}/status.
    """
    import os
    msg_ctx = {"channel": request.channel or "web_cc"}
    founder = is_founder_message(msg_ctx)
    if not founder:
        founder_pin = os.getenv("FOUNDER_PIN", "7777")
        if not request.pin or str(request.pin) != founder_pin:
            raise HTTPException(status_code=403, detail="Invalid PIN. Code Mode requires founder authorization.")

    from app.services.max.code_task_runner import code_task_runner

    task = code_task_runner.submit(request.prompt)
    return {
        "task_id": task.id,
        "state": task.state.value,
        "message": "Task submitted to Atlas (CodeForge). Poll /code-task/{id}/status for progress.",
    }


@router.get("/code-task/{task_id}/status")
async def get_code_task_status(task_id: str):
    """Get status and live progress log of an async code task."""
    from app.services.max.code_task_runner import code_task_runner

    task = code_task_runner.get_task(task_id)
    if not task:
        raise HTTPException(404, f"Code task '{task_id}' not found")
    return task.to_dict()


class VerifyPinRequest(BaseModel):
    pin: str


@router.post("/verify-pin")
async def verify_pin(request: VerifyPinRequest):
    """Verify founder PIN without performing any action. Used by Code Mode toggle."""
    import os
    founder_pin = os.getenv("FOUNDER_PIN", "7777")
    if str(request.pin) == founder_pin:
        return {"valid": True}
    raise HTTPException(status_code=403, detail="Invalid PIN")


# ── TTS (Text-to-Speech) ─────────────────────────────────────────────


class TTSRequest(BaseModel):
    text: str
    voice: str = "rex"  # Available: ara, rex, sal, eve, leo


@router.post("/tts")
async def text_to_speech(request: TTSRequest):
    """Convert text to speech audio (MP3) via xAI Grok TTS. Voice: Rex (default)."""
    from app.services.max.tts_service import tts_service

    if not tts_service.is_configured:
        raise HTTPException(status_code=503, detail="TTS not configured — XAI_API_KEY missing")

    audio_bytes = await tts_service.synthesize_for_web(request.text)
    if not audio_bytes:
        raise HTTPException(status_code=500, detail="TTS synthesis failed")

    from fastapi.responses import Response
    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=max_speech.mp3"},
    )


# ── Agent Code of Conduct ─────────────────────────────────────────────


@router.get("/conduct")
async def get_all_agent_conducts():
    """Get all agent codes of conduct."""
    from app.services.max.conduct import get_all_conducts
    return get_all_conducts()


@router.get("/conduct/{agent_id}")
async def get_agent_conduct(agent_id: str):
    """Get code of conduct for a specific agent."""
    from app.services.max.conduct import get_conduct
    conduct = get_conduct(agent_id)
    if not conduct:
        raise HTTPException(status_code=404, detail=f"No conduct defined for agent '{agent_id}'")
    return conduct


# ── Security Scanner ──────────────────────────────────────────────────


@router.get("/security/scan")
async def run_security_scan():
    """Run the security scanner on the Empire codebase."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "tools"))
    from pathlib import Path as P
    from security_scan import SecurityScanner

    empire_root = P(__file__).parent.parent.parent.parent.parent
    scanner = SecurityScanner(empire_root)
    # Quick scan (no npm audit — that's slow)
    for scan_dir in scanner.__class__.__dict__.get("SCAN_DIRS", []) or ["backend", "founder_dashboard/src"]:
        dir_path = empire_root / scan_dir
        if dir_path.exists():
            scanner.scan_directory(dir_path)

    return {
        "scan_time": datetime.utcnow().isoformat(),
        "stats": scanner.stats,
        "findings_count": len(scanner.findings),
        "critical": [f for f in scanner.findings if f["severity"] == "CRITICAL"][:10],
        "high": [f for f in scanner.findings if f["severity"] == "HIGH"][:20],
        "medium": [f for f in scanner.findings if f["severity"] == "MEDIUM"][:10],
    }


# ── Speech-to-Text (STT) ─────────────────────────────────────────────────────

from fastapi import UploadFile, File

@router.post("/stt")
async def speech_to_text(file: UploadFile = File(...), language: str = "es"):
    """
    Transcribe uploaded audio to text using Groq Whisper.
    Accepts: mp3, mp4, m4a, wav, ogg, flac, webm (max 25MB).
    Default language: Spanish.
    """
    from app.services.max.stt_service import stt_service

    if not stt_service.is_configured:
        raise HTTPException(status_code=503, detail="STT not configured — GROQ_API_KEY missing")

    # Save temp file
    import tempfile
    suffix = Path(file.filename or "audio.webm").suffix or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        transcript = await stt_service.transcribe(tmp_path, language=language)
        return {"text": transcript, "language": language, "filename": file.filename}
    finally:
        tmp_path.unlink(missing_ok=True)



# ── System Report & Change Log ──────────────────────────────────────────────

@router.get("/system-report")
async def get_system_report():
    """
    Comprehensive system report for MAX: modules, connectivity, recent changes,
    desk statuses, and actionable insights. Serves as a tutorial guide and
    continuous update feed.
    """
    import psutil
    import subprocess

    report: Dict[str, Any] = {
        "generated_at": datetime.utcnow().isoformat(),
        "system": {},
        "modules": [],
        "recent_changes": [],
        "desk_reports": [],
        "connectivity": [],
        "suggestions": [],
        "bugs": [],
    }

    # ── System Stats ──
    try:
        from app.routers.system_monitor import _get_disk_summary
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = _get_disk_summary()
        report["system"] = {
            "cpu_percent": cpu,
            "memory_used_gb": round(mem.used / (1024**3), 1),
            "memory_total_gb": round(mem.total / (1024**3), 1),
            "memory_percent": mem.percent,
            "disk_used_gb": disk["used_gb"],
            "disk_total_gb": disk["total_gb"],
            "disk_percent": disk["percent"],
            "disk_drives": disk["drives"],
            "uptime": _get_uptime(),
        }
    except Exception as e:
        report["system"]["error"] = str(e)

    # ── Module Inventory ──
    modules = [
        {"name": "MAX Chat (SSE)", "endpoint": "/max/chat/stream", "frontend": True, "status": "active"},
        {"name": "MAX Desks", "endpoint": "/max/desks", "frontend": True, "status": "active"},
        {"name": "Chat History", "endpoint": "/chats/*", "frontend": True, "status": "active"},
        {"name": "Quotes", "endpoint": "/quotes/*", "frontend": True, "status": "active"},
        {"name": "Files", "endpoint": "/files/*", "frontend": True, "status": "active"},
        {"name": "System Monitor", "endpoint": "/system/stats", "frontend": True, "status": "active"},
        {"name": "Memory/Brain", "endpoint": "/memory/*", "frontend": True, "status": "active"},
        {"name": "TTS (Voice)", "endpoint": "/max/tts", "frontend": True, "status": "active"},
        {"name": "STT (Speech)", "endpoint": "/api/transcribe", "frontend": True, "status": "active"},
        {"name": "Notifications", "endpoint": "/notifications/*", "frontend": "partial", "status": "active"},
        {"name": "CraftForge", "endpoint": "/craftforge/*", "frontend": False, "status": "backend_only"},
        {"name": "SupportForge", "endpoint": "/tickets/*", "frontend": False, "status": "backend_only"},
        {"name": "Finance/Economic", "endpoint": "/economic/*", "frontend": False, "status": "backend_only"},
        {"name": "Tasks", "endpoint": "/tasks/*", "frontend": False, "status": "backend_only"},
        {"name": "Contacts/CRM", "endpoint": "/contacts/*", "frontend": False, "status": "backend_only"},
        {"name": "Vision/Mockups", "endpoint": "/vision/*", "frontend": False, "status": "backend_only"},
        {"name": "Shipping", "endpoint": "/shipping/*", "frontend": False, "status": "backend_only"},
        {"name": "Docker Manager", "endpoint": "/docker/*", "frontend": False, "status": "backend_only"},
        {"name": "Ollama Manager", "endpoint": "/ollama/*", "frontend": False, "status": "backend_only"},
        {"name": "Intake Portal", "endpoint": "/intake/*", "frontend": True, "status": "active"},
    ]
    report["modules"] = modules

    # ── Recent Git Changes ──
    try:
        repo_root = Path(__file__).parent.parent.parent.parent.parent
        result = subprocess.run(
            ["git", "log", "--oneline", "--no-decorate", "-20"],
            cwd=str(repo_root), capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    parts = line.strip().split(" ", 1)
                    report["recent_changes"].append({
                        "hash": parts[0],
                        "message": parts[1] if len(parts) > 1 else "",
                    })

        # Recent file changes (last 48h)
        diff_result = subprocess.run(
            ["git", "diff", "--stat", "HEAD~5", "HEAD"],
            cwd=str(repo_root), capture_output=True, text=True, timeout=5
        )
        if diff_result.returncode == 0:
            report["recent_diff_summary"] = diff_result.stdout.strip().split("\n")[-1] if diff_result.stdout.strip() else ""
    except Exception as e:
        report["recent_changes"].append({"error": str(e)})

    # ── AI Desk Reports ──
    try:
        desks = ai_desk_manager.list_desks()
        for d in desks:
            desk_info = {
                "id": d.get("id", ""),
                "name": d.get("name", ""),
                "status": d.get("status", "idle"),
                "persona": d.get("persona", ""),
                "domains": d.get("domains", []),
                "can_report": [
                    "Generate daily summary",
                    "List pending tasks",
                    "Report on recent activity",
                    "Analyze performance metrics",
                ],
            }
            report["desk_reports"].append(desk_info)
    except Exception as e:
        report["desk_reports"].append({"error": str(e)})

    # ── Connectivity Check ──
    import aiohttp
    services_to_check = [
        ("Backend API", "http://localhost:8000/health"),
        ("Command Center", "http://localhost:3009"),
        ("AMP Portal", "http://localhost:3003"),
        ("Ollama", "http://localhost:11434/api/version"),
    ]
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3)) as session:
        for name, url in services_to_check:
            try:
                async with session.get(url) as resp:
                    report["connectivity"].append({
                        "service": name, "url": url,
                        "status": "online" if resp.status < 500 else "error",
                        "code": resp.status,
                    })
            except Exception:
                report["connectivity"].append({
                    "service": name, "url": url,
                    "status": "offline", "code": 0,
                })

    # ── Known Bugs ──
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    if env_path.exists():
        env_content = env_path.read_text()
        if "GROQ_API_KEY=\n" in env_content or "GROQ_API_KEY=" == env_content.strip().split("\n")[-1]:
            report["bugs"].append({"severity": "medium", "desc": "GROQ_API_KEY is empty — STT/transcription won't work"})
    report["bugs"].append({"severity": "low", "desc": "Ollama running but no models downloaded"})
    report["bugs"].append({"severity": "medium", "desc": "CraftForge frontend shows hardcoded data despite 15 real backend endpoints"})
    report["bugs"].append({"severity": "low", "desc": "Video Call screen is a UI mockup only"})

    # ── Suggestions ──
    connected = sum(1 for m in modules if m["frontend"] is True)
    backend_only = sum(1 for m in modules if m["frontend"] is False)
    report["suggestions"] = [
        f"{backend_only} modules have backend endpoints but no frontend wiring — biggest gaps: CraftForge, Tasks, Finance",
        "Add a live Activity Feed to Command Center showing desk completions, quote updates, file uploads",
        "Wire CraftForge dashboard to real /craftforge/* endpoints (designs, jobs, inventory)",
        "Add Tasks panel to DesksScreen — show active tasks per desk from /tasks/* endpoints",
        "Enable daily auto-reports from each AI desk via scheduler",
    ]

    return report


def _get_uptime():
    """Get system uptime as human-readable string."""
    try:
        import psutil
        boot = datetime.fromtimestamp(psutil.boot_time())
        delta = datetime.now() - boot
        days = delta.days
        hours, rem = divmod(delta.seconds, 3600)
        mins = rem // 60
        if days > 0:
            return f"{days}d {hours}h {mins}m"
        return f"{hours}h {mins}m"
    except Exception:
        return "--"


@router.get("/changelog")
async def get_changelog():
    """Get recent system changes — git commits, file modifications, new features."""
    import subprocess
    repo_root = Path(__file__).parent.parent.parent.parent.parent

    result = {
        "generated_at": datetime.utcnow().isoformat(),
        "commits": [],
        "new_features": [],
        "modified_files": [],
    }

    try:
        # Last 30 commits with dates
        log = subprocess.run(
            ["git", "log", "--format=%H|%ai|%s", "-30"],
            cwd=str(repo_root), capture_output=True, text=True, timeout=5
        )
        if log.returncode == 0:
            for line in log.stdout.strip().split("\n"):
                if "|" in line:
                    parts = line.split("|", 2)
                    result["commits"].append({
                        "hash": parts[0][:8],
                        "date": parts[1].strip(),
                        "message": parts[2] if len(parts) > 2 else "",
                    })

        # Files changed in last 5 commits
        diff = subprocess.run(
            ["git", "diff", "--name-status", "HEAD~5", "HEAD"],
            cwd=str(repo_root), capture_output=True, text=True, timeout=5
        )
        if diff.returncode == 0:
            for line in diff.stdout.strip().split("\n"):
                if line.strip():
                    parts = line.strip().split("\t", 1)
                    if len(parts) == 2:
                        status_map = {"A": "added", "M": "modified", "D": "deleted"}
                        result["modified_files"].append({
                            "status": status_map.get(parts[0], parts[0]),
                            "file": parts[1],
                        })

        # Detect new features from commit messages
        for c in result["commits"][:10]:
            msg = c["message"].lower()
            if any(kw in msg for kw in ["add", "new", "feature", "build", "create", "implement"]):
                result["new_features"].append({
                    "date": c["date"],
                    "description": c["message"],
                })

    except Exception as e:
        result["error"] = str(e)

    return result


# ── Gmail Inbox (read-only) ────────────────────────────────────────

@router.get("/gmail/inbox")
async def gmail_inbox(limit: int = 10, unread_only: bool = True):
    """Read-only Gmail inbox check via OAuth2."""
    import asyncio
    try:
        from app.services.max.gmail_reader import check_inbox
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: check_inbox(limit=min(limit, 20), unread_only=unread_only)
        )
    except Exception as e:
        return {"success": False, "error": str(e), "emails": [], "count": 0}


# ── MAX Health + Self-Heal Status ────────────────────────────────────

@router.get("/self-heal-status")
async def max_self_heal_status():
    """MAX self-heal dashboard — capabilities, incidents, mode."""
    result = {"status": "ok"}
    try:
        from app.services.max.capability_loader import load_registry
        result["capabilities"] = load_registry()
    except Exception as e:
        result["capabilities"] = {"error": str(e)}
    try:
        from app.services.max.operating_registry import load_operating_registry
        result["operating_registry"] = load_operating_registry()
    except Exception as e:
        result["operating_registry"] = {"error": str(e)}
    try:
        from app.services.max.self_heal import get_heal_status
        result["self_heal"] = get_heal_status()
    except Exception as e:
        result["self_heal"] = {"error": str(e)}
    result["auto_heal_enabled"] = True
    return result


# ── MAX Evaluation Loop — Feedback + Stats ─────────────────────────────

class FeedbackRequest(BaseModel):
    response_id: str
    thumbs_up: Optional[int] = None   # 1 = up, 0 = down, null = skip
    rating: Optional[int] = None        # 1–5, null = skip
    tag_helpful: Optional[bool] = False
    tag_wrong: Optional[bool] = False
    tag_incomplete: Optional[bool] = False
    tag_too_slow: Optional[bool] = False
    tag_wrong_tool: Optional[bool] = False
    tag_stale: Optional[bool] = False
    tag_should_have_searched: Optional[bool] = False
    tag_should_have_used_image: Optional[bool] = False
    comment: Optional[str] = None


@router.post("/evaluation/feedback")
async def submit_feedback(request: FeedbackRequest):
    """Submit explicit feedback for a MAX response.

    Use the response_id from the original chat response.
    At least one of thumbs_up or rating should be provided.
    """
    if request.thumbs_up is None and request.rating is None and not any([
        request.tag_helpful, request.tag_wrong, request.tag_incomplete,
        request.tag_too_slow, request.tag_wrong_tool, request.tag_stale,
        request.tag_should_have_searched, request.tag_should_have_used_image
    ]):
        return {"ok": False, "error": "Provide at least thumbs_up, rating, or a tag"}

    ok = evaluation_service.submit_feedback(
        response_id=request.response_id,
        thumbs_up=request.thumbs_up,
        rating=request.rating,
        tag_helpful=request.tag_helpful,
        tag_wrong=request.tag_wrong,
        tag_incomplete=request.tag_incomplete,
        tag_too_slow=request.tag_too_slow,
        tag_wrong_tool=request.tag_wrong_tool,
        tag_stale=request.tag_stale,
        tag_should_have_searched=request.tag_should_have_searched,
        tag_should_have_used_image=request.tag_should_have_used_image,
        comment=request.comment,
    )
    return {"ok": ok}


@router.get("/evaluation/stats")
async def get_evaluation_stats(days: int = Query(default=30, ge=1, le=365)):
    """Get MAX evaluation stats for routing decisions and founder visibility.

    Returns:
    - routing_preferences: provider performance by capability (weighted score for routing)
    - tool_performance: tool success rates by capability
    - frustration_hotspots: common failure patterns
    - recent_evaluations: last N evaluations for inspection
    """
    return {
        "routing_preferences": evaluation_service.get_routing_preferences(days=days),
        "tool_performance": evaluation_service.get_tool_performance(days=days),
        "frustration_hotspots": evaluation_service.get_frustration_hotspots(days=days),
        "recent_evaluations": evaluation_service.get_recent_evaluations(limit=20),
    }
