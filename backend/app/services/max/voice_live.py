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
    {"type":"ready", call_id, cap_seconds, sample_rate, model, voice}
    {"type":"transcript", role:"user"|"assistant", text|delta, final}
    {"type":"speech_started"} / {"type":"speech_stopped"}
    {"type":"interrupt", response_id} -> client must flush playback NOW
    {"type":"tool", name, status:"running"|"done", ok}
    {"type":"response_done", response_id}
    {"type":"ping", remaining}   (heartbeat every HEARTBEAT_SECONDS)
    {"type":"warning", remaining} (30 s before the hard cap)
    {"type":"ended", reason, duration_s}
    {"type":"error", message}

Safety
  * Only READ-ONLY tools (search_quotes, get_quote, search_contacts) are
    exposed and they run server-side through tool_executor.execute_tool.
    Anything else the model asks for is refused.
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
READ_ONLY_TOOLS = ("search_quotes", "get_quote", "search_contacts")
TOOL_OUTPUT_LIMIT = 6000

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
    }


# ── Instructions (Max persona + short memory summary) ────────────────

def _memory_summary(max_chars: int = 1200) -> str:
    """Short, read-only summary pulled from max/memory.md (never written)."""
    path = Path(os.getenv("MAX_MEMORY_PATH", str(Path.home() / "empire-repo-main" / "max" / "memory.md")))
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    keep: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("<!--") or s.startswith("```"):
            continue
        if len(s) > 220:
            s = s[:217] + "..."
        keep.append(s)
        if sum(len(x) + 1 for x in keep) > max_chars:
            break
    return "\n".join(keep)[:max_chars]


def build_instructions() -> str:
    memory = _memory_summary()
    parts = [
        "# Role\n"
        "You are Max, the AI chief of staff for Empire (Empire Workroom — custom "
        "drapery, upholstery and window treatments in the Washington DC area — and "
        "the wider EmpireBox platform). You are talking live, by voice, with the "
        "founder, Rafael.",
        "# Style\n"
        "Speak naturally and briefly: one to three short sentences per turn unless "
        "asked for detail. No markdown, lists, emojis or URLs; say numbers and money "
        "the way a person would. If you were interrupted, stop and listen. Match "
        "Rafael's language (English or Spanish).",
        "# Tools\n"
        "You can look things up with read-only tools: search_quotes, get_quote "
        "(quote ids look like EST-2026-285; say 'E S T twenty twenty-six two eighty-"
        "five' naturally), and search_contacts. Use them whenever Rafael asks about a "
        "quote, customer or contact instead of guessing. Say a quick 'one sec' before "
        "a lookup. You cannot create, edit, send, approve, delete, restart or run "
        "anything in this voice mode; if asked, say it needs the text chat in the "
        "Command Center.",
        "# Truth\n"
        "Only state facts you got from a tool result or the context below. If a "
        "lookup fails or finds nothing, say so plainly. Never invent quote amounts, "
        "statuses or names.",
    ]
    if memory:
        parts.append("# Context (memory summary)\n" + memory)
    return "\n\n".join(parts)


# ── Tools ───────────────────────────────────────────────────────────

_FALLBACK_TOOL_SCHEMAS = {
    # Parameter names match the tool_executor handlers.
    "search_quotes": {
        "description": "List/search Empire quotes (newest first). Filter by customer name and/or status. Read-only.",
        "parameters": {"type": "object", "properties": {
            "customer_name": {"type": "string", "description": "Part of the customer's name (optional)"},
            "status": {"type": "string", "description": "Optional status filter: draft, sent, accepted, rejected, expired"},
            "limit": {"type": "integer", "description": "Max results (default 5, max 20)"},
        }},
    },
    "get_quote": {
        "description": "Get one quote's details (status, customer, totals, items) by quote number like EST-2026-285 or internal id. Read-only.",
        "parameters": {"type": "object", "properties": {
            "quote_id": {"type": "string", "description": "Quote number (e.g. EST-2026-285) or internal quote id"},
        }, "required": ["quote_id"]},
    },
    "search_contacts": {
        "description": "Search customers/contacts by name, email, phone or company. Read-only.",
        "parameters": {"type": "object", "properties": {
            "search": {"type": "string", "description": "Name, email, phone or company"},
            "limit": {"type": "integer", "description": "Max results (default 5)"},
        }, "required": ["search"]},
    },
}

_QUOTE_KEEP = ("id", "quote_number", "status", "customer_name", "project_name", "project_description",
               "business_unit", "subtotal", "tax_amount", "discount_amount", "total", "deposit_required",
               "deposit_paid", "balance_due", "created_at", "updated_at", "sent_at", "accepted_at",
               "expires_at", "notes")


def _compact_for_voice(name: str, data: dict[str, Any]) -> dict[str, Any]:
    """Trim large tool payloads (photos, mockups, raw measurements) for speech."""
    if name != "get_quote" or not isinstance(data.get("result"), dict):
        return data
    q = data["result"]
    slim = {k: q.get(k) for k in _QUOTE_KEEP if q.get(k) not in (None, "", [], {})}
    items = q.get("line_items") or []
    slim["line_items_count"] = len(items)
    slim["line_items"] = [
        {k: it.get(k) for k in ("description", "name", "room", "quantity", "total", "amount") if isinstance(it, dict) and it.get(k) not in (None, "")}
        for it in items[:8]
    ]
    out = dict(data)
    out["result"] = slim
    return out


def realtime_tool_definitions() -> list[dict[str, Any]]:
    """Realtime-format (flat) function definitions for the read-only tools.

    Prefer the canonical schemas from tool_executor.get_xai_tool_definitions()
    so parameter names match the handlers; fall back to local schemas.
    """
    canonical: dict[str, dict[str, Any]] = {}
    try:
        from app.services.max.tool_executor import get_xai_tool_definitions
        for d in get_xai_tool_definitions() or []:
            fn = d.get("function") if isinstance(d, dict) and "function" in d else d
            if isinstance(fn, dict) and fn.get("name") in READ_ONLY_TOOLS:
                canonical[fn["name"]] = fn
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("voice_live: canonical tool schemas unavailable: %s", exc)
    out = []
    for name in READ_ONLY_TOOLS:
        fn = canonical.get(name) or _FALLBACK_TOOL_SCHEMAS[name]
        out.append({
            "type": "function",
            "name": name,
            "description": (fn.get("description") or _FALLBACK_TOOL_SCHEMAS[name]["description"])[:1000],
            "parameters": fn.get("parameters") or _FALLBACK_TOOL_SCHEMAS[name]["parameters"],
        })
    return out


def run_readonly_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute one read-only tool via the canonical executor (sync)."""
    if name not in READ_ONLY_TOOLS:
        return {"success": False, "error": f"Tool '{name}' is not available in voice mode (read-only tools only)."}
    from app.services.max.tool_executor import execute_tool
    call = {k: v for k, v in (arguments or {}).items() if not str(k).startswith("_")}
    call["tool"] = name
    if name == "search_quotes" and not call.get("limit"):
        call["limit"] = 5
    if name == "search_contacts":
        if not call.get("search") and call.get("query"):
            call["search"] = call.pop("query")
        call.setdefault("limit", 5)
    if name == "search_quotes" and not call.get("customer_name") and call.get("query"):
        call["customer_name"] = call.pop("query")
    result = execute_tool(call, desk=None, access_context=None, founder=False, channel="voice_live")
    return _compact_for_voice(name, result.to_dict())


def _tool_output_text(data: dict[str, Any]) -> str:
    text = json.dumps(data, default=str)
    if len(text) > TOOL_OUTPUT_LIMIT:
        text = text[:TOOL_OUTPUT_LIMIT] + '..."(truncated)"'
    return text


# ── Session config ──────────────────────────────────────────────────

def session_update_event() -> dict[str, Any]:
    session: dict[str, Any] = {
        "voice": voice_name(),
        "instructions": build_instructions(),
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
            if rid and rid in self.cancelled:
                return
            await self.send_client_json({"type": "transcript", "role": "assistant",
                                         "delta": event.get("delta", ""), "final": False,
                                         "response_id": rid})
            return
        if etype in ("response.output_audio_transcript.done", "response.audio_transcript.done"):
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
            data = await asyncio.to_thread(run_readonly_tool, name, args)
        except Exception as exc:
            data = {"success": False, "error": f"{type(exc).__name__}: {exc}"}
        ok = bool(data.get("success"))
        logger.info("voice_live[%s]: tool %s ok=%s in %dms", self.call_id, name, ok,
                    int((time.monotonic() - started) * 1000))
        await self.send_client_json({"type": "tool", "name": name, "status": "done", "ok": ok})
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
            return
        await self.send_upstream(session_update_event())
        await self.send_client_json({
            "type": "ready", "call_id": self.call_id, "cap_seconds": self.cap,
            "sample_rate": SAMPLE_RATE, "model": voice_model(), "voice": voice_name(),
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
        await call.send_client_json({"type": "ended", "reason": call.end_reason, "duration_s": duration})
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
            "audio_out_bytes": call.audio_out_bytes,
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


def authorize_websocket(ws) -> tuple[bool, str, str]:
    """Same trust model as the Command Center: Cloudflare Access at the edge.

    * Via the tunnel (proxy headers present): require a valid Access JWT
      (Cf-Access-Jwt-Assertion header or CF_Authorization cookie).
    * Direct local connection (loopback peer, no proxy headers): allowed —
      that is the Command Center on this box and the local test harness.
    """
    headers = ws.headers
    host = (headers.get("host") or "").split(":")[0].lower()
    if host in _PUBLIC_UNGATED_HOSTS:
        return False, "public host not allowed", ""
    token = headers.get("cf-access-jwt-assertion") or ws.cookies.get("CF_Authorization")
    if token:
        return verify_access_jwt(token)
    proxied = any(headers.get(h) for h in _PROXY_HEADERS)
    peer = getattr(ws.client, "host", "") if ws.client else ""
    if not proxied and peer in ("127.0.0.1", "::1", "localhost"):
        return True, "loopback", ""
    return False, "Cloudflare Access token required", ""
