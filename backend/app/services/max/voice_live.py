"""MAX Live Voice — browser <-> xAI Grok realtime (speech-to-speech) bridge.

Added 2026-09-30 (Phase B, live voice). The browser never sees the xAI key:
it streams raw PCM16 mic audio to our authenticated WebSocket
(/api/v1/avatar/live) and we relay it to wss://api.x.ai/v1/realtime.

Browser protocol (our socket)
  client -> server
    binary frame        : PCM16 LE mono @ SAMPLE_RATE (mic audio)
    {"type":"hangup"}   : end the call
    {"type":"ping"}     : keepalive (answered with pong)
    {"type":"text","text":"..."} : optional typed turn
  server -> client
    binary frame        : PCM16 LE mono @ SAMPLE_RATE (Max speaking)
    {"type":"ready", call_id, cap_seconds, sample_rate, model, voice, conversation_id}
    {"type":"transcript", role:"user"|"assistant", text|delta, final}
    {"type":"speech_started"} / {"type":"speech_stopped"}
    {"type":"interrupt", response_id} -> client must flush playback NOW
    {"type":"tool", name, status:"running"|"done", ok}
    {"type":"response_done", response_id}
    {"type":"ping", remaining}   (heartbeat every HEARTBEAT_SECONDS)
    {"type":"warning", remaining} (30 s before the hard cap)
    {"type":"ended", reason, duration_s, transcript_saved, conversation_id}
    {"type":"error", message}

Voice upgrade (2026-09-30, founder-approved)
  * FRESH BRAIN: instructions are built at call start by voice_brain from
    the same sources as text /max/chat (system_prompt incl. CURRENT
    OPERATING FACTS, get_max_brain_context, brain ContextBuilder/MemoryStore)
    plus a live snapshot; cached 60 s. max/memory.md (stale "v5.1 /
    2026-03-18") is no longer read for voice.
  * TRANSCRIPTS: every call is saved to Max's conversation history
    (channel "voice") by voice_transcript, with an end-of-call summary.
  * TOOLS: server-side allowlist (VOICE_TOOL_ALLOWLIST) of read-only tools
    plus queue_for_founder_approval, which only files a pending task
    (status 'waiting', tags voice-request / needs-founder-approval) and never
    executes anything. Everything else is refused server-side.

Safety
  * Tools run server-side; anything not in VOICE_TOOL_ALLOWLIST is refused
    before tool_executor is touched (send_email, shell_execute, file_write,
    approve/reject, deposit links, deletes ... are all refused).
  * Hard cap per call (MAX_VOICE_CALL_CAP_SECONDS, default 600 s) with
    auto-hangup; limited concurrent calls.
  * xAI is used for voice via its own flag (MAX_VOICE_XAI_ENABLED, default
    on) so MAX_DISABLE_XAI=true keeps text routing off xAI unchanged.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("max.voice_live")

XAI_REALTIME_URL = os.getenv("XAI_REALTIME_URL", "wss://api.x.ai/v1/realtime")
SAMPLE_RATE = 24000
HEARTBEAT_SECONDS = 15
MAX_CONCURRENT_CALLS = 2
TOOL_OUTPUT_LIMIT = 6000

# ── Server-side tool allowlist ──────────────────────────────────────
VOICE_READ_ONLY_TOOLS = (
    "search_quotes", "get_quote", "search_contacts",
    "get_tasks", "get_desk_status", "get_services_health", "get_system_stats",
    "check_email", "list_job_images", "search_conversations", "get_weather",
    "list_quotes_awaiting_review", "show_quote_for_review",
    "get_revenue_chart",
)
QUEUE_TOOL = "queue_for_founder_approval"
VOICE_TOOL_ALLOWLIST = frozenset(VOICE_READ_ONLY_TOOLS + (QUEUE_TOOL,))
READ_ONLY_TOOLS = VOICE_READ_ONLY_TOOLS  # backwards-compatible name
# Explicitly named so logs/tests are clear; the allowlist above is what enforces.
VOICE_DENIED_EXAMPLES = frozenset({
    "send_email", "send_telegram", "shell_execute", "env_set", "file_write", "file_edit",
    "file_append", "file_delete", "approve_quote", "reject_quote", "deposit_pay_link",
    "create_task", "service_manager", "git_ops", "delete_quote", "delete_contact",
})

_active_calls: set[str] = set()


def _flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def voice_model() -> str:
    return os.getenv("MAX_VOICE_MODEL", "grok-voice-think-fast-2.0")


def voice_name() -> str:
    return os.getenv("MAX_VOICE_NAME", "rex")


def call_cap_seconds() -> int:
    try:
        return max(30, int(os.getenv("MAX_VOICE_CALL_CAP_SECONDS", "600")))
    except ValueError:
        return 600


def voice_status() -> dict[str, Any]:
    """Non-secret readiness summary for /avatar/status and the UI."""
    key_present = bool(os.getenv("XAI_API_KEY"))
    enabled = _flag("MAX_VOICE_XAI_ENABLED", True)
    return {
        "provider": "xai-realtime",
        "endpoint": "/api/v1/avatar/live",
        "model": voice_model(),
        "voice": voice_name(),
        "key_present": key_present,
        "enabled": enabled and key_present,
        "reason": None if (enabled and key_present) else ("XAI_API_KEY missing" if not key_present else "MAX_VOICE_XAI_ENABLED=false"),
        "cap_seconds": call_cap_seconds(),
        "sample_rate": SAMPLE_RATE,
        "active_calls": len(_active_calls),
        "text_routing_xai_disabled": _flag("MAX_DISABLE_XAI", False),
        "tools": sorted(VOICE_TOOL_ALLOWLIST),
        "transcripts_saved": True,
    }


# ── Instructions ────────────────────────────────────────────────────

def build_instructions() -> str:
    """Static fallback instructions (no live sources).

    Used only if the fresh voice brain (voice_brain.get_voice_instructions)
    cannot be built. Deliberately does NOT read max/memory.md: that file is a
    stale "v5.1 / 2026-03-18" summary that /max/chat does not load.
    """
    from app.services.max.voice_brain import VOICE_CAPABILITIES, VOICE_ROLE, VOICE_STYLE, VOICE_TRUTH
    return "\n\n".join([
        VOICE_ROLE.format(model=voice_model()),
        VOICE_STYLE,
        VOICE_CAPABILITIES.format(read_tools=", ".join(VOICE_READ_ONLY_TOOLS)),
        VOICE_TRUTH,
        "# Live snapshot\nThe live snapshot could not be loaded for this call. Use the tools "
        "(get_tasks, get_desk_status, get_services_health, list_quotes_awaiting_review) before "
        "stating current status.",
    ])


async def fresh_instructions() -> tuple[str, dict]:
    try:
        from app.services.max.voice_brain import get_voice_instructions
        return await asyncio.wait_for(
            get_voice_instructions(model=voice_model(), read_tools=list(VOICE_READ_ONLY_TOOLS)),
            timeout=10,
        )
    except Exception as exc:
        logger.warning("voice_live: fresh instructions unavailable (%s); using static fallback",
                       type(exc).__name__)
        return build_instructions(), {"fallback": True, "error": type(exc).__name__}


# ── Tools ───────────────────────────────────────────────────────────

def _obj(props: dict, required: list | None = None) -> dict:
    out: dict[str, Any] = {"type": "object", "properties": props}
    if required:
        out["required"] = required
    return out


_STR = {"type": "string"}
_INT = {"type": "integer"}

_FALLBACK_TOOL_SCHEMAS = {
    # Parameter names match the tool_executor handlers.
    "search_quotes": {
        "description": "List/search Empire quotes newest by updated_at. Matches customer, project/site, address, notes, and quote number. Use latest=true for the newest match or today=true for today's newest quote. Read-only.",
        "parameters": _obj({
            "query": {"type": "string", "description": "Free-text customer/project/site/notes search, e.g. Willard (optional)"},
            "customer_name": {"type": "string", "description": "Part of the customer's name (optional)"},
            "status": {"type": "string", "description": "Optional status filter: draft, founder_review, sent, accepted, rejected, expired"},
            "latest": {"type": "boolean", "description": "Return only the newest matching quote"},
            "today": {"type": "boolean", "description": "Restrict to quotes created or updated today"},
            "limit": {"type": "integer", "description": "Max results (default 5, max 20)"},
        }),
    },
    "get_quote": {
        "description": "Get one quote's details (status, customer, totals, items) by quote number like EST-2026-285 or internal id. Read-only.",
        "parameters": _obj({"quote_id": {"type": "string", "description": "Quote number (e.g. EST-2026-285) or internal quote id"}}, ["quote_id"]),
    },
    "search_contacts": {
        "description": "Search customers/contacts by name, email, phone or company. Read-only.",
        "parameters": _obj({
            "search": {"type": "string", "description": "Name, email, phone or company"},
            "limit": {"type": "integer", "description": "Max results (default 5)"},
        }, ["search"]),
    },
    "get_tasks": {
        "description": "List Empire tasks from the task system (newest first). Optional status: todo, in_progress, waiting, done. With no status, returns open tasks (todo, in_progress, waiting). Read-only.",
        "parameters": _obj({
            "status": {"type": "string", "description": "todo | in_progress | waiting | done (optional)"},
            "desk": {"type": "string", "description": "Desk name filter (optional)"},
            "limit": {"type": "integer", "description": "Max results (default 10)"},
        }),
    },
    "get_desk_status": {
        "description": "Task counts per desk (todo / in_progress / waiting / done) and total open. Read-only.",
        "parameters": _obj({}),
    },
    "get_services_health": {
        "description": "Which Empire services are online (backend, Command Center, OpenClaw, Ollama, ...). Read-only.",
        "parameters": _obj({}),
    },
    "get_system_stats": {
        "description": "EmpireDell machine stats: CPU, RAM, disk, uptime. Read-only.",
        "parameters": _obj({}),
    },
    "check_email": {
        "description": "Read the Gmail inbox (read-only: sender, subject, date, snippet). Never sends or changes mail.",
        "parameters": _obj({
            "limit": {"type": "integer", "description": "Max emails (default 5, max 10)"},
            "unread_only": {"type": "boolean", "description": "Only unread (default true)"},
        }),
    },
    "list_job_images": {
        "description": "List photos/images stored for a job or quote (or the unassigned bucket). Pass exactly one of job_id, quote_id, unassigned=true. Read-only.",
        "parameters": _obj({
            "job_id": _STR, "quote_id": {"type": "string", "description": "Quote id or number"},
            "unassigned": {"type": "boolean"}, "limit": {"type": "integer", "description": "Max rows (default 10)"},
        }),
    },
    "search_conversations": {
        "description": "Search Max's conversation history across channels (web, Telegram, voice): memories, summaries and messages. Use channel 'voice' and query 'last voice call' to recall the previous voice call. Read-only.",
        "parameters": _obj({
            "query": {"type": "string", "description": "Keyword or phrase"},
            "channel": {"type": "string", "description": "Optional: web, telegram, cc, voice"},
            "limit": {"type": "integer", "description": "Max results (default 8)"},
        }, ["query"]),
    },
    "get_weather": {
        "description": "Current weather (Open-Meteo). Default city Washington DC. Read-only.",
        "parameters": _obj({"city": {"type": "string", "description": "City (default Washington DC)"}}),
    },
    "get_revenue_chart": {
        "description": "Read-only revenue totals by month from recorded payments. Use for 'last month's revenue' or 'this week's numbers'. Returns a chart. Never invents amounts. Does not send anything.",
        "parameters": _obj({}),
    },
    "list_quotes_awaiting_review": {
        "description": "Quotes waiting for Rafael's review/approval (founder_review, plus legacy proposal quotes). Test quotes are hidden. Read-only — you cannot approve or reject from voice.",
        "parameters": _obj({"business_unit": {"type": "string", "description": "Optional business unit filter"}}),
    },
    "show_quote_for_review": {
        "description": "Show one quote as prepared for review: proposed vs final price per line, totals. Read-only.",
        "parameters": _obj({"quote_id": {"type": "string", "description": "Quote id or number like EST-2026-285"}}, ["quote_id"]),
    },
    QUEUE_TOOL: {
        "description": "Queue a request for Rafael's approval. Creates ONE pending task (tagged voice-request, needs-founder-approval) in the Empire task system and executes NOTHING. Use for anything that would send, write, change or run something, e.g. 'send Max this transcript', 'draft an email to X', 'approve quote Y'. Tell Rafael it is queued for approval, not done.",
        "parameters": _obj({
            "action": {"type": "string", "description": "Short imperative description, e.g. 'Send Max the transcript of this voice call'"},
            "details": {"type": "string", "description": "Everything needed to do it later: who, what, which quote/customer, wording"},
        }, ["action"]),
    },
}

_QUOTE_KEEP = ("id", "quote_number", "status", "customer_name", "project_name", "project_description",
               "business_unit", "subtotal", "tax_amount", "discount_amount", "total", "deposit_required",
               "deposit_paid", "balance_due", "created_at", "updated_at", "sent_at", "accepted_at",
               "expires_at", "notes")
_QUOTE_LIST_KEEP = ("quote_number", "customer_name", "project_name", "status", "total", "business_unit",
                    "updated_at", "state_metadata")


def _compact_for_voice(name: str, data: dict[str, Any]) -> dict[str, Any]:
    """Trim large tool payloads (photos, mockups, raw measurements, bodies) for speech."""
    res = data.get("result")
    if not isinstance(res, dict):
        return data
    out = dict(data)
    if name == "get_quote":
        q = res
        slim = {k: q.get(k) for k in _QUOTE_KEEP if q.get(k) not in (None, "", [], {})}
        items = q.get("line_items") or []
        slim["line_items_count"] = len(items)
        slim["line_items"] = [
            {k: it.get(k) for k in ("description", "name", "room", "quantity", "total", "amount") if isinstance(it, dict) and it.get(k) not in (None, "")}
            for it in items[:8]
        ]
        out["result"] = slim
    elif name == "list_quotes_awaiting_review":
        rows = []
        hidden = 0
        for key in ("awaiting_review", "legacy_pending_migration", "quotes"):
            for q in res.get(key) or []:
                if not isinstance(q, dict):
                    continue
                if q.get("is_test"):
                    hidden += 1
                    continue
                rows.append({k: q.get(k) for k in _QUOTE_LIST_KEEP if q.get(k) not in (None, "")})
        out["result"] = {"count": len(rows), "quotes": rows[:15], "test_quotes_hidden": hidden}
    elif name == "show_quote_for_review":
        slim = dict(res)
        slim["line_items"] = (res.get("line_items") or [])[:10]
        slim["line_items_count"] = len(res.get("line_items") or [])
        out["result"] = slim
    elif name == "check_email":
        emails = []
        for e in (res.get("emails") or [])[:10]:
            if isinstance(e, dict):
                emails.append({"from": e.get("from"), "subject": e.get("subject"), "date": e.get("date"),
                               "unread": e.get("unread"), "snippet": str(e.get("snippet") or "")[:200]})
        out["result"] = {"count": res.get("count", len(emails)), "emails": emails}
    elif name == "list_job_images":
        imgs = [{k: i.get(k) for k in ("filename", "job_id", "quote_id", "source_channel", "created_at") if i.get(k)}
                for i in (res.get("images") or [])[:15] if isinstance(i, dict)]
        out["result"] = {"count": res.get("count", len(imgs)), "images": imgs, "filter": res.get("filter")}
    elif name == "search_conversations":
        rows = []
        for r in (res.get("results") or [])[:12]:
            if isinstance(r, dict):
                rows.append({k: (str(v)[:300] if isinstance(v, str) else v) for k, v in r.items()
                             if k in ("type", "role", "content", "summary", "channel", "date", "subject",
                                      "conversation_id", "started_at", "lines")})
        out["result"] = {"query": res.get("query"), "count": res.get("count", len(rows)), "results": rows}
    elif name == "get_tasks":
        tasks = [{k: t.get(k) for k in ("id", "title", "status", "priority", "desk", "due_date", "created_at")}
                 for t in (res.get("tasks") or [])[:15] if isinstance(t, dict)]
        out["result"] = {"count": res.get("count", len(tasks)), "tasks": tasks}
    return out


def realtime_tool_definitions() -> list[dict[str, Any]]:
    """Realtime-format (flat) function definitions for the voice allowlist.

    Prefer the canonical schemas from tool_executor.get_xai_tool_definitions()
    so parameter names match the handlers; fall back to local schemas.
    """
    canonical: dict[str, dict[str, Any]] = {}
    try:
        from app.services.max.tool_executor import get_xai_tool_definitions
        for d in get_xai_tool_definitions() or []:
            fn = d.get("function") if isinstance(d, dict) and "function" in d else d
            if isinstance(fn, dict) and fn.get("name") in VOICE_READ_ONLY_TOOLS:
                canonical[fn["name"]] = fn
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("voice_live: canonical tool schemas unavailable: %s", exc)
    out = []
    for name in VOICE_READ_ONLY_TOOLS + (QUEUE_TOOL,):
        fn = canonical.get(name) or _FALLBACK_TOOL_SCHEMAS[name]
        out.append({
            "type": "function",
            "name": name,
            "description": (fn.get("description") or _FALLBACK_TOOL_SCHEMAS[name]["description"])[:1000],
            "parameters": fn.get("parameters") or _FALLBACK_TOOL_SCHEMAS[name]["parameters"],
        })
    return out


def queue_for_founder_approval(action: str, details: str = "", *, call_id: str = "",
                               conversation_id: str = "") -> dict[str, Any]:
    """File ONE pending task for founder approval. Executes nothing.

    Written straight into the tasks table (same table/shape as create_task)
    instead of calling the create_task tool, because create_task immediately
    auto-executes the task through desk_manager and may queue it to OpenClaw.
    Status 'waiting', created_by 'voice' and no auto_execute metadata key keep
    it out of the TaskWorker (which only picks status='todo' AND
    created_by='max' / metadata "auto_execute") and the startup probe
    (status='todo' urgent/high). tags: voice-request, needs-founder-approval.
    """
    action = " ".join(str(action or "").split())[:200]
    details = str(details or "").strip()[:4000]
    if not action:
        return {"success": False, "error": "action is required"}
    from datetime import datetime as _dt
    from app.db.database import get_db
    from app.services.max.voice_brain import now_et
    task_id = uuid.uuid4().hex[:8]
    now = _dt.utcnow().isoformat()
    title = f"[Voice request - needs founder approval] {action}"[:240]
    description = (
        f"Requested by Rafael on a live voice call with Max ({now_et().strftime('%Y-%m-%d %I:%M %p')} ET).\n"
        f"Voice Max cannot execute actions; this is queued for founder approval only. Nothing was sent, "
        f"changed or run.\n\nAction: {action}\nDetails: {details or '-'}\n\n"
        f"Voice transcript: conversation {conversation_id or '-'} (channel voice), call {call_id or '-'}."
    )
    tags = ["voice-request", "needs-founder-approval"]
    metadata = {
        "source": "voice_live", "channel": "voice", "call_id": call_id, "conversation_id": conversation_id,
        "requested_action": action, "requested_details": details, "requires_founder_approval": True,
        "execution": "none - founder approval required",
    }
    with get_db() as conn:
        conn.execute(
            """INSERT INTO tasks (id, title, description, status, priority, desk, created_by, tags, metadata,
                                  created_at, updated_at)
               VALUES (?, ?, ?, 'waiting', 'normal', 'founder', 'voice', ?, ?, ?, ?)""",
            (task_id, title, description, json.dumps(tags), json.dumps(metadata), now, now),
        )
        conn.execute(
            "INSERT INTO task_activity (task_id, actor, action, detail, created_at) VALUES (?, 'max_voice', 'created', ?, ?)",
            (task_id, "Queued from live voice for founder approval (not executed)", now),
        )
        row = conn.execute("SELECT id, title, status FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not row or row["status"] != "waiting":
        return {"success": False, "error": "task insert could not be verified"}
    logger.info("voice_live[%s]: queued founder-approval task %s: %s", call_id or "-", task_id, action)
    return {"success": True, "tool": QUEUE_TOOL, "result": {
        "task_id": task_id, "status": "waiting", "tags": tags, "title": title,
        "executed": False, "note": "Queued for Rafael's approval. Nothing was sent or run.",
    }}


def run_voice_tool(name: str, arguments: dict[str, Any], *, call_id: str = "",
                   conversation_id: str = "") -> dict[str, Any]:
    """Execute one allowlisted voice tool (sync). Server-side allowlist enforced here."""
    if name not in VOICE_TOOL_ALLOWLIST:
        logger.warning("voice_live[%s]: refused non-allowlisted tool %r", call_id or "-", name)
        return {"success": False, "error": f"Tool '{name}' is not available in voice mode (read-only tools "
                                           f"plus queue_for_founder_approval only). Offer to queue it for "
                                           f"Rafael's approval instead."}
    call = {k: v for k, v in (arguments or {}).items() if not str(k).startswith("_")}
    if name == QUEUE_TOOL:
        return queue_for_founder_approval(call.get("action", ""), call.get("details", ""),
                                          call_id=call_id, conversation_id=conversation_id)
    if name == "get_revenue_chart":
        from app.services.max.presentation_stage import revenue_tool_result
        return revenue_tool_result()
    from app.services.max.tool_executor import TOOL_REGISTRY, execute_tool
    if name not in TOOL_REGISTRY:
        return {"success": False, "error": f"Tool '{name}' is not registered."}
    call["tool"] = name
    if name == "search_quotes":
        if not call.get("customer_name") and call.get("query"):
            call["customer_name"] = call.pop("query")
        call["limit"] = min(int(call.get("limit") or 5), 20)
    elif name == "search_contacts":
        if not call.get("search") and call.get("query"):
            call["search"] = call.pop("query")
        call.setdefault("limit", 5)
    elif name == "get_tasks":
        call["limit"] = min(int(call.get("limit") or 10), 25)
        if not call.get("status"):
            merged: list[dict] = []
            for st in ("in_progress", "todo", "waiting"):
                r = execute_tool(dict(call, status=st), desk=None, access_context=None, founder=False,
                                 channel="voice_live").to_dict()
                merged += (r.get("result") or {}).get("tasks") or []
            return _compact_for_voice(name, {"tool": name, "success": True,
                                             "result": {"tasks": merged, "count": len(merged),
                                                        "statuses": ["in_progress", "todo", "waiting"]}})
    elif name == "check_email":
        call["limit"] = min(int(call.get("limit") or 5), 10)
    elif name == "list_job_images":
        call["limit"] = min(int(call.get("limit") or 10), 50)
    elif name == "search_conversations":
        call["limit"] = min(int(call.get("limit") or 8), 20)
    elif name == "get_weather":
        call["city"] = call.get("city") or "Washington DC"
    result = execute_tool(call, desk=None, access_context=None, founder=False, channel="voice_live")
    return _compact_for_voice(name, result.to_dict())


def run_readonly_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Backwards-compatible wrapper (read-only tools only)."""
    if name not in VOICE_READ_ONLY_TOOLS:
        return {"success": False, "error": f"Tool '{name}' is not available in voice mode (read-only tools only)."}
    return run_voice_tool(name, arguments)


def _tool_note(name: str, data: dict[str, Any]) -> str:
    """One-line human note for the transcript."""
    if not data.get("success"):
        return str(data.get("error") or "failed")[:200]
    res = data.get("result") or {}
    if name == QUEUE_TOOL:
        return f"task {res.get('task_id')} pending founder approval (not executed): {res.get('title', '')}"
    if isinstance(res, dict) and "count" in res:
        return f"{res.get('count')} result(s)"
    return ""


def _tool_output_text(data: dict[str, Any]) -> str:
    text = json.dumps(data, default=str)
    if len(text) > TOOL_OUTPUT_LIMIT:
        text = text[:TOOL_OUTPUT_LIMIT] + '..."(truncated)"'
    return text


# ── Session config ──────────────────────────────────────────────────

def session_update_event(instructions: Optional[str] = None) -> dict[str, Any]:
    session: dict[str, Any] = {
        "voice": voice_name(),
        "instructions": instructions or build_instructions(),
        "turn_detection": {
            "type": "server_vad",
            "threshold": float(os.getenv("MAX_VOICE_VAD_THRESHOLD", "0.5")),
            "silence_duration_ms": int(os.getenv("MAX_VOICE_VAD_SILENCE_MS", "550")),
            "prefix_padding_ms": 300,
        },
        "audio": {
            "input": {"format": {"type": "audio/pcm", "rate": SAMPLE_RATE}},
            "output": {"format": {"type": "audio/pcm", "rate": SAMPLE_RATE}},
        },
        "tools": realtime_tool_definitions(),
        "tool_choice": "auto",
    }
    effort = os.getenv("MAX_VOICE_REASONING_EFFORT", "").strip().lower()
    if effort in ("none", "high"):
        session["reasoning"] = {"effort": effort}
    return {"type": "session.update", "session": session}


# ── Bridge ──────────────────────────────────────────────────────────

class LiveCall:
    def __init__(self, client_ws, *, auth_via: str = "", user: str = ""):
        self.client = client_ws
        self.call_id = uuid.uuid4().hex[:10]
        self.auth_via = auth_via
        self.user = user
        self.started = time.monotonic()
        self.cap = call_cap_seconds()
        self.upstream = None
        self.end_reason = "unknown"
        self.active_response: Optional[str] = None
        self.cancelled: set[str] = set()
        self.pending_tools: dict[str, list[asyncio.Task]] = {}
        self.tool_calls = 0
        self.audio_in_bytes = 0
        self.audio_out_bytes = 0
        self.interrupts = 0
        self.first_audio_ms: Optional[int] = None
        self._turn_started: Optional[float] = None
        self._send_lock = asyncio.Lock()
        self._closed = asyncio.Event()      # call is over (any reason)
        self._client_gone = False           # browser socket unusable
        self.instructions_meta: dict[str, Any] = {}
        self._assistant_partial: dict[str, list[str]] = {}
        self._assistant_final: set[str] = set()
        self.last_user_text = ""
        self.transcript = None
        try:
            from app.services.max.voice_transcript import VoiceTranscript
            self.transcript = VoiceTranscript(self.call_id, user=user, auth_via=auth_via, model=voice_model())
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("voice_live[%s]: transcript disabled: %s", self.call_id, exc)

    @property
    def conversation_id(self) -> str:
        return self.transcript.conversation_id if self.transcript else f"voice-{self.call_id}"

    def _record(self, method: str, *args: Any, **kwargs: Any) -> None:
        if self.transcript is None:
            return
        try:
            getattr(self.transcript, method)(*args, **kwargs)
        except Exception as exc:  # never break the call over persistence
            logger.warning("voice_live[%s]: transcript %s failed: %s", self.call_id, method, exc)

    # client helpers
    async def send_client_json(self, payload: dict[str, Any]) -> None:
        # Control messages still go out after the call ends (e.g. "ended").
        if self._client_gone:
            return
        try:
            async with self._send_lock:
                await self.client.send_text(json.dumps(payload, default=str))
        except Exception:
            self._client_gone = True
            self._closed.set()

    async def send_client_audio(self, pcm: bytes) -> None:
        if self._closed.is_set() or self._client_gone:
            return
        try:
            async with self._send_lock:
                await self.client.send_bytes(pcm)
        except Exception:
            self._client_gone = True
            self._closed.set()

    async def send_upstream(self, payload: dict[str, Any]) -> None:
        if self.upstream is None:
            return
        try:
            await self.upstream.send(json.dumps(payload))
        except Exception as exc:
            logger.warning("voice_live[%s]: upstream send failed: %s", self.call_id, exc)
            self._closed.set()

    def remaining(self) -> int:
        return max(0, int(self.cap - (time.monotonic() - self.started)))

    # tasks
    async def pump_client(self) -> None:
        """Browser -> xAI."""
        while not self._closed.is_set():
            msg = await self.client.receive()
            mtype = msg.get("type")
            if mtype == "websocket.disconnect":
                self._client_gone = True
                self.end_reason = self.end_reason if self.end_reason != "unknown" else "client_disconnect"
                break
            data = msg.get("bytes")
            if data:
                self.audio_in_bytes += len(data)
                await self.send_upstream({
                    "type": "input_audio_buffer.append",
                    "audio": base64.b64encode(data).decode("ascii"),
                })
                continue
            text = msg.get("text")
            if not text:
                continue
            try:
                event = json.loads(text)
            except Exception:
                continue
            etype = event.get("type")
            if etype == "hangup":
                self.end_reason = "hangup"
                break
            if etype == "ping":
                await self.send_client_json({"type": "pong", "remaining": self.remaining()})
            elif etype == "text" and str(event.get("text") or "").strip():
                self._turn_started = time.monotonic()
                self._record("add_user", str(event["text"])[:2000], "typed")
                await self.send_upstream({
                    "type": "conversation.item.create",
                    "item": {"type": "message", "role": "user",
                             "content": [{"type": "input_text", "text": str(event["text"])[:2000]}]},
                })
                await self.send_upstream({"type": "response.create"})
            elif etype == "audio" and event.get("audio"):
                # JSON/base64 fallback for clients that cannot send binary.
                try:
                    raw = base64.b64decode(event["audio"])
                except Exception:
                    continue
                self.audio_in_bytes += len(raw)
                await self.send_upstream({"type": "input_audio_buffer.append", "audio": event["audio"]})
        self._closed.set()

    async def pump_upstream(self) -> None:
        """xAI -> browser."""
        async for raw in self.upstream:
            if self._closed.is_set():
                break
            if isinstance(raw, (bytes, bytearray)):
                # binary transport (not requested, but tolerate it)
                if self.active_response not in self.cancelled:
                    self.audio_out_bytes += len(raw)
                    await self.send_client_audio(bytes(raw))
                continue
            try:
                event = json.loads(raw)
            except Exception:
                continue
            await self.handle_upstream_event(event)
        if self.end_reason == "unknown":
            self.end_reason = "upstream_closed"
        self._closed.set()

    async def handle_upstream_event(self, event: dict[str, Any]) -> None:
        etype = event.get("type", "")
        if etype in ("response.output_audio.delta", "response.audio.delta"):
            rid = event.get("response_id")
            if rid and rid in self.cancelled:
                return
            try:
                pcm = base64.b64decode(event.get("delta") or "")
            except Exception:
                return
            if pcm:
                if self.first_audio_ms is None and self._turn_started is not None:
                    self.first_audio_ms = int((time.monotonic() - self._turn_started) * 1000)
                    await self.send_client_json({"type": "latency", "first_audio_ms": self.first_audio_ms})
                self.audio_out_bytes += len(pcm)
                await self.send_client_audio(pcm)
            return
        if etype == "input_audio_buffer.speech_started":
            await self.send_client_json({"type": "speech_started"})
            # Barge-in: cancel the in-flight response and flush client playback.
            if self.active_response and self.active_response not in self.cancelled:
                rid = self.active_response
                self.cancelled.add(rid)
                self.interrupts += 1
                await self.send_upstream({"type": "response.cancel"})
                logger.info("voice_live[%s]: barge-in, cancelled response %s", self.call_id, rid)
            await self.send_client_json({"type": "interrupt", "response_id": self.active_response})
            return
        if etype == "input_audio_buffer.speech_stopped":
            self._turn_started = time.monotonic()
            self.first_audio_ms = None
            await self.send_client_json({"type": "speech_stopped"})
            return
        if etype == "conversation.item.input_audio_transcription.completed":
            self.last_user_text = str(event.get("transcript") or "")
            self._record("add_user", event.get("transcript", ""), event.get("item_id"))
            await self.send_client_json({"type": "transcript", "role": "user",
                                         "text": event.get("transcript", ""), "final": True,
                                         "item_id": event.get("item_id")})
            return
        if etype in ("conversation.item.input_audio_transcription.updated",
                     "conversation.item.input_audio_transcription.delta"):
            await self.send_client_json({"type": "transcript", "role": "user",
                                         "text": event.get("transcript") or event.get("delta", ""),
                                         "final": False, "item_id": event.get("item_id")})
            return
        if etype in ("response.output_audio_transcript.delta", "response.audio_transcript.delta"):
            rid = event.get("response_id")
            self._assistant_partial.setdefault(rid or "_", []).append(event.get("delta", "") or "")
            if rid and rid in self.cancelled:
                return
            await self.send_client_json({"type": "transcript", "role": "assistant",
                                         "delta": event.get("delta", ""), "final": False,
                                         "response_id": rid})
            return
        if etype in ("response.output_audio_transcript.done", "response.audio_transcript.done"):
            rid = event.get("response_id") or "_"
            if rid not in self._assistant_final:
                self._assistant_final.add(rid)
                self._assistant_partial.pop(rid, None)
                self._record("add_assistant", event.get("transcript", ""), rid, rid in self.cancelled)
            await self.send_client_json({"type": "transcript", "role": "assistant",
                                         "text": event.get("transcript", ""), "final": True,
                                         "response_id": event.get("response_id")})
            return
        if etype == "response.created":
            rid = (event.get("response") or {}).get("id") or event.get("response_id")
            self.active_response = rid
            return
        if etype == "response.function_call_arguments.done":
            rid = event.get("response_id") or self.active_response or "_"
            name = event.get("name") or ""
            call_id = event.get("call_id") or ""
            try:
                args = json.loads(event.get("arguments") or "{}")
            except Exception:
                args = {}
            self.tool_calls += 1
            await self.send_client_json({"type": "tool", "name": name, "status": "running"})
            task = asyncio.create_task(self._run_tool(name, call_id, args))
            self.pending_tools.setdefault(rid, []).append(task)
            return
        if etype == "response.done":
            resp = event.get("response") or {}
            rid = resp.get("id") or event.get("response_id") or self.active_response
            if rid == self.active_response:
                self.active_response = None
            if rid and rid not in self._assistant_final and self._assistant_partial.get(rid):
                self._assistant_final.add(rid)
                partial = "".join(self._assistant_partial.pop(rid, []))
                self._record("add_assistant", partial, rid, rid in self.cancelled)
            tasks = self.pending_tools.pop(rid, None) or self.pending_tools.pop("_", None)
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for r in results:
                    if isinstance(r, tuple):
                        call_id, output = r
                        await self.send_upstream({
                            "type": "conversation.item.create",
                            "item": {"type": "function_call_output", "call_id": call_id, "output": output},
                        })
                # A barged-in response keeps its tool outputs in the conversation,
                # but the user's new turn (server VAD) drives the next response.
                if rid not in self.cancelled:
                    self._turn_started = time.monotonic()
                    self.first_audio_ms = None
                    await self.send_upstream({"type": "response.create"})
            await self.send_client_json({"type": "response_done", "response_id": rid,
                                         "status": resp.get("status")})
            return
        if etype == "error":
            err = event.get("error") or {}
            msg = err.get("message") if isinstance(err, dict) else str(err)
            code = err.get("code") if isinstance(err, dict) else None
            # Cancelling an already-finished response is harmless.
            if code in ("response_cancel_not_active",) or "no active response" in str(msg).lower():
                return
            logger.warning("voice_live[%s]: upstream error: %s", self.call_id, str(msg)[:300])
            await self.send_client_json({"type": "error", "message": str(msg)[:300]})
            return
        if etype in ("session.updated", "session.created", "conversation.created"):
            if etype == "session.updated":
                await self.send_client_json({"type": "session_ready"})
            return

    async def _run_tool(self, name: str, call_id: str, args: dict[str, Any]) -> tuple[str, str]:
        started = time.monotonic()
        try:
            data = await asyncio.to_thread(run_voice_tool, name, args, call_id=self.call_id,
                                           conversation_id=self.conversation_id)
        except Exception as exc:
            data = {"success": False, "error": f"{type(exc).__name__}: {exc}"}
        ok = bool(data.get("success"))
        logger.info("voice_live[%s]: tool %s ok=%s in %dms", self.call_id, name, ok,
                    int((time.monotonic() - started) * 1000))
        self._record("add_tool", name, args, ok, _tool_note(name, data))
        from app.services.max.presentation_stage import stage_event
        stage = stage_event(name, data if isinstance(data, dict) else {}, self.last_user_text)
        await self.send_client_json({
            "type": "tool", "name": name, "status": "done", "ok": ok,
            "artifacts": stage["artifacts"], "slides": stage["slides"],
        })
        return call_id, _tool_output_text(data)

    async def heartbeat(self) -> None:
        warned = False
        while not self._closed.is_set():
            try:
                await asyncio.wait_for(self._closed.wait(), timeout=HEARTBEAT_SECONDS)
                break
            except asyncio.TimeoutError:
                pass
            rem = self.remaining()
            if rem <= 0:
                self.end_reason = "cap_reached"
                self._closed.set()
                break
            if rem <= 30 and not warned:
                warned = True
                await self.send_client_json({"type": "warning", "remaining": rem})
            await self.send_client_json({"type": "ping", "remaining": rem})

    async def cap_timer(self) -> None:
        try:
            await asyncio.wait_for(self._closed.wait(), timeout=self.cap)
        except asyncio.TimeoutError:
            self.end_reason = "cap_reached"
            self._closed.set()

    async def run(self) -> None:
        import websockets  # local import: optional dependency at import time

        key = os.getenv("XAI_API_KEY", "")
        url = f"{XAI_REALTIME_URL}?model={voice_model()}"
        # Build the fresh voice brain while the upstream socket connects.
        instr_task = asyncio.create_task(fresh_instructions(), name="voice-instructions")
        try:
            self.upstream = await websockets.connect(
                url,
                additional_headers={"Authorization": f"Bearer {key}"},
                ping_interval=20,
                ping_timeout=20,
                max_size=8 * 1024 * 1024,
                open_timeout=15,
            )
        except Exception as exc:
            detail = type(exc).__name__
            resp = getattr(exc, "response", None)
            status_code = getattr(resp, "status_code", None)
            if status_code:
                body = (getattr(resp, "body", b"") or b"")[:400].decode("utf-8", "replace").lower()
                detail = f"HTTP {status_code}"
                if status_code in (401, 403):
                    detail += (" - xAI API key is disabled or the team is blocked (billing); re-enable it in console.x.ai"
                               if "disabled" in body or "blocked" in body else " - xAI rejected the API key")
            logger.error("voice_live[%s]: xAI connect failed: %s", self.call_id, detail)
            await self.send_client_json({"type": "error", "message": f"Voice provider connect failed ({detail})"})
            self.end_reason = "upstream_connect_failed"
            instr_task.cancel()
            return
        instructions, self.instructions_meta = await instr_task
        logger.info("voice_live[%s]: instructions %s chars (~%s tokens, cached=%s, fallback=%s)",
                    self.call_id, len(instructions), len(instructions) // 4,
                    self.instructions_meta.get("cached"), self.instructions_meta.get("fallback", False))
        await self.send_upstream(session_update_event(instructions))
        self._record("start")
        await self.send_client_json({
            "type": "ready", "call_id": self.call_id, "cap_seconds": self.cap,
            "sample_rate": SAMPLE_RATE, "model": voice_model(), "voice": voice_name(),
            "conversation_id": self.conversation_id, "transcript_saved": self.transcript is not None,
        })
        tasks = [
            asyncio.create_task(self.pump_client(), name="voice-client"),
            asyncio.create_task(self.pump_upstream(), name="voice-upstream"),
            asyncio.create_task(self.heartbeat(), name="voice-heartbeat"),
            asyncio.create_task(self.cap_timer(), name="voice-cap"),
        ]
        try:
            await self._closed.wait()
        finally:
            for t in tasks:
                t.cancel()
            for group in self.pending_tools.values():
                for t in group:
                    t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            try:
                await self.upstream.close()
            except Exception:
                pass


async def handle_live_call(client_ws, *, auth_via: str = "", user: str = "") -> None:
    """Entry point used by the /avatar/live WebSocket route (already accepted)."""
    status = voice_status()
    call = LiveCall(client_ws, auth_via=auth_via, user=user)
    if not status["enabled"]:
        await call.send_client_json({"type": "error", "message": f"Live voice unavailable: {status['reason']}"})
        await call.send_client_json({"type": "ended", "reason": "unavailable", "duration_s": 0})
        return
    if len(_active_calls) >= MAX_CONCURRENT_CALLS:
        await call.send_client_json({"type": "error", "message": "Too many live calls in progress."})
        await call.send_client_json({"type": "ended", "reason": "busy", "duration_s": 0})
        return
    _active_calls.add(call.call_id)
    logger.info("voice_live[%s]: call started (auth=%s user=%s model=%s cap=%ss)",
                call.call_id, auth_via, user or "-", voice_model(), call.cap)
    try:
        await call.run()
    except Exception as exc:  # pragma: no cover - defensive
        call.end_reason = f"error:{type(exc).__name__}"
        logger.exception("voice_live[%s]: call crashed", call.call_id)
    finally:
        _active_calls.discard(call.call_id)
        duration = round(time.monotonic() - call.started, 1)
        saved: dict[str, Any] = {"saved": False}
        if call.transcript is not None:
            try:
                saved = await asyncio.wait_for(
                    asyncio.to_thread(call.transcript.finish, duration, call.end_reason), timeout=20)
            except Exception as exc:
                logger.warning("voice_live[%s]: transcript finish failed: %s", call.call_id, exc)
        await call.send_client_json({"type": "ended", "reason": call.end_reason, "duration_s": duration,
                                     "transcript_saved": bool(saved.get("saved")),
                                     "conversation_id": call.conversation_id})
        logger.info(
            "voice_live[%s]: call ended reason=%s duration_s=%.1f tool_calls=%d interrupts=%d "
            "audio_in_kb=%d audio_out_kb=%d",
            call.call_id, call.end_reason, duration, call.tool_calls, call.interrupts,
            call.audio_in_bytes // 1024, call.audio_out_bytes // 1024,
        )
        _log_call_record(call, duration)


def _log_call_record(call: LiveCall, duration: float) -> None:
    try:
        base = Path(os.getenv("EMPIRE_DATA_DIR", str(Path.home() / "empire-data"))) / "voice"
        base.mkdir(parents=True, exist_ok=True)
        rec = {
            "call_id": call.call_id, "ended_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "duration_s": duration, "reason": call.end_reason, "auth": call.auth_via,
            "user": call.user, "model": voice_model(), "tool_calls": call.tool_calls,
            "interrupts": call.interrupts, "audio_in_bytes": call.audio_in_bytes,
            "audio_out_bytes": call.audio_out_bytes, "conversation_id": call.conversation_id,
            "instructions_chars": call.instructions_meta.get("chars"),
        }
        with open(base / "live_calls.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
    except Exception:
        pass


# ── Auth (Cloudflare Access) ────────────────────────────────────────

CF_ACCESS_TEAM_DOMAIN = os.getenv("CF_ACCESS_TEAM_DOMAIN", "empirebox.cloudflareaccess.com")
# Access application AUD tag for studio/api.empirebox.store (not a secret).
CF_ACCESS_AUD = os.getenv(
    "CF_ACCESS_AUD", "515a21e3d659b688fceaf889397b2ad9064e760ebaca5ce57436f40ba2ab374b"
)
_PROXY_HEADERS = ("cf-ray", "cf-connecting-ip", "x-forwarded-for", "x-real-ip", "forwarded")
_PUBLIC_UNGATED_HOSTS = {"luxe.empirebox.store", "test-luxe.empirebox.store",
                         "empirebox.store", "www.empirebox.store"}
_jwks_cache: dict[str, Any] = {"keys": None, "at": 0.0}


def _fetch_jwks() -> dict[str, Any]:
    now = time.time()
    if _jwks_cache["keys"] and now - _jwks_cache["at"] < 3600:
        return _jwks_cache["keys"]
    import httpx
    resp = httpx.get(f"https://{CF_ACCESS_TEAM_DOMAIN}/cdn-cgi/access/certs", timeout=5)
    resp.raise_for_status()
    data = resp.json()
    _jwks_cache.update(keys={"keys": data.get("keys", [])}, at=now)
    return _jwks_cache["keys"]


def verify_access_jwt(token: str) -> tuple[bool, str, str]:
    """Verify a Cloudflare Access JWT (RS256, aud, iss, exp). Returns (ok, why, email)."""
    try:
        from jose import jwt as jose_jwt
    except Exception:
        return False, "jwt library unavailable", ""
    try:
        jwks = _fetch_jwks()
        claims = jose_jwt.decode(
            token, jwks, algorithms=["RS256"], audience=CF_ACCESS_AUD,
            issuer=f"https://{CF_ACCESS_TEAM_DOMAIN}",
            options={"verify_at_hash": False},
        )
        return True, "cloudflare_access", str(claims.get("email") or claims.get("common_name") or "")
    except Exception as exc:
        return False, f"invalid access token ({type(exc).__name__})", ""


def tailscale_allowed_logins() -> set[str]:
    """Comma-separated TAILSCALE_ALLOWED_LOGINS. Empty means nobody."""
    raw = os.getenv("TAILSCALE_ALLOWED_LOGINS") or ""
    return {part.strip().lower() for part in raw.split(",") if part.strip()}


def _peer_host(ws) -> str:
    client = getattr(ws, "client", None)
    return str(getattr(client, "host", "") or "")


def authorize_websocket(ws) -> tuple[bool, str, str]:
    """Who may open Live Voice and the other Presentation Mode avatar routes.

    * Cloudflare Access JWT (header or CF_Authorization cookie) is checked
      first, including on loopback. That path is unchanged.
    * Direct local connection (loopback peer, no proxy headers, no Tailscale
      identity header): allowed. That is the Command Center on this box.
    * `tailscale serve` on this machine: the TCP peer is 127.0.0.1 or ::1 and
      the proxy sets Tailscale-User-Login. Accept only when that login is in
      TAILSCALE_ALLOWED_LOGINS. An empty allowlist denies. The same header
      from any other peer is ignored and the request is denied, because a
      remote client can spoof it.
    """
    headers = ws.headers
    host = (headers.get("host") or "").split(":")[0].lower()
    if host in _PUBLIC_UNGATED_HOSTS:
        return False, "public host not allowed", ""
    token = headers.get("cf-access-jwt-assertion") or ws.cookies.get("CF_Authorization")
    if token:
        return verify_access_jwt(token)
    peer = _peer_host(ws)
    login = (headers.get("tailscale-user-login") or "").strip()
    if login:
        # Identity header present: decide here. Do not fall through to the
        # open loopback allowance, and do not trust the header off-box.
        if peer not in ("127.0.0.1", "::1"):
            return False, "tailscale header from non-loopback", ""
        allowed = tailscale_allowed_logins()
        if login.lower() not in allowed:
            return False, "tailscale login not allowed", ""
        return True, "tailscale", login
    proxied = any(headers.get(h) for h in _PROXY_HEADERS)
    if not proxied and peer in ("127.0.0.1", "::1", "localhost"):
        return True, "loopback", ""
    return False, "Cloudflare Access token required", ""
