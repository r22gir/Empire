"""MAX live voice — fresh session instructions ("voice brain").

Added 2026-09-30. Before this, voice Max was primed with the first ~1200
characters of max/memory.md — a stale "COMPLETE BRAIN v5.1 / Last Updated
2026-03-18" document that /max/chat does not load at all. On a phone test
voice Max said "I'm running on the latest brain, v5.1 from March 18th",
didn't know the current Empire status and didn't know transcripts are saved.

Voice instructions are now built at call start from the SAME sources the
text /max/chat path uses (system_prompt.get_system_prompt incl. the
"CURRENT OPERATING FACTS" block, system_prompt.get_max_brain_context and
brain.ContextBuilder over the MemoryStore), plus a compact live snapshot
(branch/HEAD, open + awaiting-review quotes excluding is_test, open tasks,
services health, today's date). max/memory.md is NOT read for voice.
The result is capped (~7k tokens) and cached for CACHE_TTL seconds.
"""
from __future__ import annotations

import asyncio
import logging
import re
import subprocess
import time
from datetime import datetime
from typing import Any, Callable, Optional

logger = logging.getLogger("max.voice_brain")

CACHE_TTL = 60                # seconds
MAX_INSTRUCTION_CHARS = 28000  # ~7k tokens hard cap
SOURCE_TIMEOUT = 6.0           # seconds per source before we give up on it

_cache: dict[str, Any] = {"text": None, "at": 0.0, "meta": None}

# Lines that reintroduce the stale v5.1 / March-18 memory summary.
_STALE_RE = re.compile(
    r"(\bv5\.1\b|COMPLETE BRAIN|Last Updated:\s*2026-03-18|\bMarch 18(th)?\b|\bMar 18\b|2026-03-18)",
    re.IGNORECASE,
)


def _tz():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo("America/New_York")
    except Exception:  # pragma: no cover
        return None


def now_et() -> datetime:
    tz = _tz()
    return datetime.now(tz) if tz else datetime.now()


def strip_stale(text: str) -> str:
    """Drop lines carrying the stale v5.1 / March 18 brain summary."""
    return "\n".join(ln for ln in (text or "").splitlines() if not _STALE_RE.search(ln))


def _clip(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 20].rstrip() + "\n...[trimmed]"


# ── Sources shared with /max/chat ───────────────────────────────────

def operating_core() -> str:
    """Identity + CURRENT OPERATING FACTS + prime directive from system_prompt.py.

    Same get_system_prompt() text /max/chat uses (60 s cached there too);
    we keep only the head (up to "=== CORE RULES") plus the live channel
    status line — the full tool roster is for text, not voice.
    """
    from app.services.max.system_prompt import get_system_prompt
    full = get_system_prompt() or ""
    end = full.find("=== CORE RULES")
    head = full[:end] if end > 0 else full[:5000]
    out = [head.strip()]
    m = re.search(r"## Live Channel Status\n([^\n]+)", full)
    if m:
        out.append("Live channel status: " + m.group(1).strip())
    return strip_stale("\n\n".join(out))


def live_brain_context() -> str:
    """system_prompt.get_max_brain_context() — the always-on text context."""
    from app.services.max.system_prompt import get_max_brain_context
    return strip_stale(get_max_brain_context() or "")


async def memory_context() -> str:
    """brain.ContextBuilder over the MemoryStore (what /max/chat injects)."""
    from app.services.max.brain.context_builder import ContextBuilder
    ctx = await ContextBuilder().build_context(
        user_message="Empire status, priorities today, open quotes and tasks, founder preferences",
        conversation_history=[],
    )
    return strip_stale(ctx or "")


# ── Live snapshot ───────────────────────────────────────────────────

OPEN_QUOTE_STATUSES = ("founder_review", "proposal", "draft", "sent")


def _git_state() -> str:
    try:
        from app.services.drawing.canonical_path import resolve_canonical_root
        repo = str(resolve_canonical_root())
    except Exception:
        return "Git: canonical repo root unresolved."
    def git(*args: str) -> str:
        r = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, timeout=5)
        return r.stdout.strip() if r.returncode == 0 else ""
    branch = git("rev-parse", "--abbrev-ref", "HEAD") or "?"
    head = git("log", "-1", "--format=%h %s (%cr)") or "?"
    return f"Git: branch {branch}, HEAD {head}."


def _quotes_state() -> str:
    from app.db.database import get_db
    marks = ",".join("?" for _ in OPEN_QUOTE_STATUSES)
    with get_db() as conn:
        counts = {r[0]: r[1] for r in conn.execute(
            f"SELECT status, COUNT(*) FROM quotes_v2 WHERE (is_test IS NULL OR is_test = 0) "
            f"AND status IN ({marks}) GROUP BY status", OPEN_QUOTE_STATUSES).fetchall()}
        review = conn.execute(
            "SELECT quote_number, customer_name, total, status, updated_at FROM quotes_v2 "
            "WHERE (is_test IS NULL OR is_test = 0) AND status IN ('founder_review','proposal') "
            "ORDER BY updated_at DESC LIMIT 5").fetchall()
        recent = conn.execute(
            f"SELECT quote_number, customer_name, total, status, updated_at FROM quotes_v2 "
            f"WHERE (is_test IS NULL OR is_test = 0) AND status IN ('sent','draft') "
            f"ORDER BY updated_at DESC LIMIT 5").fetchall()
    def fmt(r) -> str:
        total = r["total"]
        money = f"${total:,.2f}" if isinstance(total, (int, float)) else "no total"
        return f"  - {r['quote_number']} {r['customer_name'] or '?'} ({r['status']}, {money}, updated {str(r['updated_at'] or '')[:10]})"
    lines = ["Quotes (real only, is_test excluded): " + ", ".join(
        f"{counts.get(s, 0)} {s}" for s in OPEN_QUOTE_STATUSES)]
    if review:
        lines.append(" Awaiting founder review:")
        lines += [fmt(r) for r in review]
    else:
        lines.append(" Awaiting founder review: none.")
    if recent:
        lines.append(" Most recent open (sent/draft):")
        lines += [fmt(r) for r in recent]
    return "\n".join(lines)


def _tasks_state() -> str:
    from app.services.max.tool_executor import execute_tool
    desk = execute_tool({"tool": "get_desk_status"}, founder=False, channel="voice_live").to_dict()
    total_open = (desk.get("result") or {}).get("total_open")
    rows: list[dict] = []
    for status in ("in_progress", "todo", "waiting"):
        res = execute_tool({"tool": "get_tasks", "status": status, "limit": 8},
                           founder=False, channel="voice_live").to_dict()
        rows += (res.get("result") or {}).get("tasks") or []
    lines = [f"Tasks: {total_open if total_open is not None else '?'} open (todo+in_progress), "
             f"{sum(1 for r in rows if r.get('status') == 'waiting')} waiting."]
    for r in rows[:8]:
        lines.append(f"  - [{r.get('status')}/{r.get('priority')}] {str(r.get('title') or '')[:110]} "
                     f"(desk {r.get('desk') or '-'}, id {r.get('id')})")
    if not rows:
        lines.append("  (no open tasks)")
    return "\n".join(lines)


def _services_state() -> str:
    from app.services.max.tool_executor import execute_tool
    res = execute_tool({"tool": "get_services_health"}, founder=False, channel="voice_live").to_dict()
    data = res.get("result") or {}
    svcs = data.get("services") or {}
    up = sorted(k for k, v in svcs.items() if (v or {}).get("status") == "online")
    down = sorted(k for k, v in svcs.items() if (v or {}).get("status") != "online")
    return (f"Services: {data.get('online', len(up))}/{data.get('total', len(svcs))} online "
            f"(online: {', '.join(up) or 'none'}; offline: {', '.join(down) or 'none'}).")


def live_snapshot() -> str:
    parts = [f"Today: {now_et().strftime('%A, %B %d, %Y, %I:%M %p')} ET (America/New_York)."]
    for fn in (_git_state, _quotes_state, _tasks_state, _services_state):
        try:
            parts.append(fn())
        except Exception as exc:
            parts.append(f"{fn.__name__.strip('_').replace('_', ' ')}: unavailable ({type(exc).__name__}).")
    return "\n".join(parts)


# ── Assembly ────────────────────────────────────────────────────────

VOICE_ROLE = (
    "# Voice session\n"
    "You are Max (the same Max as the Command Center text chat), talking live by voice with the "
    "founder, Rafael. The operating facts, memory and live snapshot below were loaded fresh at the "
    "start of this call. They are your current state. Never describe yourself with an old brain "
    "version number or an old 'last updated' date from past memory files; those documents are retired. "
    "If asked what version you are, say you run on the Empire platform version 7.0 with the live voice "
    "model {model}, and give the branch and HEAD from the snapshot, then today's priorities from the "
    "snapshot (quotes awaiting review, open tasks, services)."
)

VOICE_STYLE = (
    "# Style\n"
    "Speak naturally and briefly: one to three short sentences per turn unless asked for detail. No "
    "markdown, lists, emojis or URLs; say numbers and money the way a person would; say quote ids like "
    "EST-2026-285 as 'E S T twenty twenty-six two eighty-five'. If interrupted, stop and listen. Match "
    "Rafael's language (English or Spanish): his latest words decide. Before a lookup say a quick "
    "'un segundo' in Spanish or 'one sec' in English."
)

VOICE_CAPABILITIES = (
    "# What you can do in voice (server-enforced)\n"
    "Read-only tools: {read_tools}. Use them instead of guessing whenever Rafael asks about quotes, "
    "customers, tasks, desks, services, the machine, email, job photos, past conversations or weather. "
    "For news, local events or any current public fact (e.g. 'últimas noticias en Cartago, Valle'), call "
    "web_search and summarize the top headlines in a few sentences; never say you have no news access.\n"
    "One request tool: queue_for_founder_approval(action, details). It only files a pending task tagged "
    "voice-request / needs-founder-approval in the Empire task system. It never sends, runs or changes "
    "anything; Rafael (or text Max after his approval) acts on it later. Use it for requests like "
    "'send Max this transcript', 'draft an email to X', 'remind me to...', or anything that needs a "
    "write. Tell Rafael it is queued for his approval, not done.\n"
    "Email to Rafael himself: when he says 'email me' / 'send that to my email' or names "
    "empirebox2026@gmail.com, rafa22giraldo@gmail.com or max@empirebox.store, call send_email right "
    "away. No PIN, no second yes. Outbound send uses SMTP and works; never say you can't send email or "
    "that email settings block it (a Gmail inbox-read token problem does not affect sending). If a send "
    "fails, say the real error in one sentence.\n"
    "Files: find_files searches ALL of Rafael's files (jobs, Downloads, Desktop, Documents, Pictures, quote "
    "PDFs, backup drive) by name, client or nickname (Dahlia = Nehal Elrefai) or quote number. Say how many "
    "matched and name the top ones (e.g. both Nehal phases). share_file sends one to Rafael by email, WhatsApp "
    "or a studio link. Never say you found or sent a file without a tool result; if nothing matched, say so "
    "and name the closest files.\n"
    "Email to anyone else (clients, vendors) needs Rafael's explicit yes in text chat: offer "
    "queue_for_founder_approval. You CANNOT send texts or messages, run shell commands, write or delete "
    "files, approve or reject quotes, create deposit or payment links, or delete anything from voice. If "
    "asked, offer to queue it for approval or to do it in the Command Center text chat.\n"
    "Change requests: when Rafael asks you to change, fix or investigate-and-fix something in Empire "
    "(a module, a chart, permissions, how you behave), call request_improvement in the same turn with his "
    "words and say it is filed and will be built on a test copy for his approval. Never say you can't "
    "edit your own code.\n"
    "Unclear requests: speech-to-text mishears (for example 'yo quiero' heard as 'no quiero'). If a request "
    "is unclear, contradicts itself or does not fit what was just said, ask ONE short clarifying question "
    "(e.g. '¿Qué permisos: los del teléfono, del portal o de los archivos?'). Never drop a request or "
    "answer it with 'ok, nothing'. If it is clearly a request to fix something, file request_improvement.\n"
    "Transcripts: this call IS being saved. Every line you and Rafael say, each tool call, and the start "
    "and end time go into your normal conversation history (channel 'voice'), plus a short end-of-call "
    "summary, so text Max can see and continue it. If asked, say yes, it is saved."
)

VOICE_TRUTH = (
    "# Truth\n"
    "Only state facts from a tool result or the context below. Numbers in the snapshot are from call "
    "start; re-check with a tool if it matters. If a lookup fails or finds nothing, say so plainly. "
    "Never invent quote amounts, statuses, task ids or names."
)


async def _run_sync(fn: Callable[[], str], label: str, meta: dict) -> str:
    started = time.monotonic()
    try:
        out = await asyncio.wait_for(asyncio.to_thread(fn), timeout=SOURCE_TIMEOUT)
        meta[label] = {"ok": True, "chars": len(out or ""), "ms": int((time.monotonic() - started) * 1000)}
        return out or ""
    except Exception as exc:
        meta[label] = {"ok": False, "error": type(exc).__name__}
        logger.warning("voice_brain: %s unavailable: %s", label, type(exc).__name__)
        return ""


async def _run_async(coro_fn, label: str, meta: dict) -> str:
    started = time.monotonic()
    try:
        out = await asyncio.wait_for(coro_fn(), timeout=SOURCE_TIMEOUT)
        meta[label] = {"ok": True, "chars": len(out or ""), "ms": int((time.monotonic() - started) * 1000)}
        return out or ""
    except Exception as exc:
        meta[label] = {"ok": False, "error": type(exc).__name__}
        logger.warning("voice_brain: %s unavailable: %s", label, type(exc).__name__)
        return ""


def assemble(*, model: str, read_tools: list[str], core: str, snapshot: str,
             brain: str, memory: str) -> str:
    parts = [
        VOICE_ROLE.format(model=model),
        VOICE_STYLE,
        VOICE_CAPABILITIES.format(read_tools=", ".join(read_tools)),
        VOICE_TRUTH,
    ]
    if snapshot:
        parts.append("# Live snapshot (loaded at call start)\n" + _clip(snapshot, 4500))
    if core:
        parts.append("# Operating facts (same as text Max; system_prompt.py)\n" + _clip(core, 6500))
    if brain:
        parts.append("# Live brain context (same as text Max)\n" + _clip(brain, 6000))
    if memory:
        parts.append("# Max memory (MemoryStore, same as text Max)\n" + _clip(memory, 5000))
    text = "\n\n".join(parts)  # sources are strip_stale()d individually
    if len(text) > MAX_INSTRUCTION_CHARS:
        text = text[: MAX_INSTRUCTION_CHARS - 20] + "\n...[trimmed]"
    return text


async def build_voice_instructions(*, model: str, read_tools: list[str]) -> tuple[str, dict]:
    meta: dict[str, Any] = {}
    core, snapshot, brain, memory = await asyncio.gather(
        _run_sync(operating_core, "operating_core", meta),
        _run_sync(live_snapshot, "live_snapshot", meta),
        _run_sync(live_brain_context, "live_brain_context", meta),
        _run_async(memory_context, "memory_context", meta),
    )
    text = assemble(model=model, read_tools=read_tools, core=core, snapshot=snapshot,
                    brain=brain, memory=memory)
    meta["chars"] = len(text)
    meta["approx_tokens"] = len(text) // 4
    return text, meta


async def get_voice_instructions(*, model: str, read_tools: list[str],
                                 force: bool = False) -> tuple[str, dict]:
    """Cached (CACHE_TTL) fresh voice instructions.

    No lock: two calls starting in the same second may both build; that is
    harmless and avoids binding an asyncio.Lock to one event loop.
    """
    now = time.monotonic()
    if not force and _cache["text"] and now - _cache["at"] < CACHE_TTL:
        return _cache["text"], dict(_cache["meta"] or {}, cached=True)
    text, meta = await build_voice_instructions(model=model, read_tools=read_tools)
    _cache.update(text=text, at=time.monotonic(), meta=meta)
    return text, dict(meta, cached=False)


def clear_cache() -> None:
    _cache.update(text=None, at=0.0, meta=None)
