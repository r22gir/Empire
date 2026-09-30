"""MAX live voice — transcript persistence into Max's normal history.

Added 2026-09-30. Every live voice call is written to the same stores the
text /max/chat path and search_conversations use, marked channel "voice":

  * unified_message_store (unified_messages, channel="voice") — every user
    and Max line, each tool call, call start/end and an end-of-call summary,
    written incrementally (a crash mid-call keeps what was said). This store
    feeds text Max's "Recent Cross-Channel Activity" and "Last Voice Call"
    context (system_prompt.get_max_brain_context).
  * backend/data/chats/founder/<chat_id>.json — the Command Center chat
    history file format /max/chat writes, so the call shows up in the CC
    chat list and can be opened and continued in text.
  * brain MemoryStore — a category="conversation" memory (subject
    "voice_call") and a conversation_summaries row, which
    search_conversations searches.

Nothing here sends, emails or executes anything.
"""
from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("max.voice_transcript")

CHANNEL = "voice"
CHATS_DIR = Path(__file__).resolve().parents[3] / "data" / "chats"
_writer = ThreadPoolExecutor(max_workers=1, thread_name_prefix="voice-transcript")  # keeps order


def _now_et() -> datetime:
    from app.services.max.voice_brain import now_et
    return now_et()


def _unified():
    from app.services.max.unified_message_store import unified_store
    return unified_store


def _fmt_dur(seconds: float) -> str:
    s = int(round(seconds or 0))
    return f"{s // 60}m {s % 60:02d}s" if s >= 60 else f"{s}s"


def _short(text: str, n: int) -> str:
    text = re.sub(r"\s+", " ", (text or "")).strip()
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


class VoiceTranscript:
    def __init__(self, call_id: str, *, user: str = "", auth_via: str = "", model: str = "") -> None:
        self.call_id = call_id
        self.conversation_id = f"voice-{call_id}"
        self.chat_id = ("v" + call_id)[:8]
        self.user = user
        self.auth_via = auth_via
        self.model = model
        self.founder_verified = auth_via in ("cloudflare_access", "loopback")
        self.started_at = _now_et()
        self.ended_at: Optional[datetime] = None
        self.entries: list[dict[str, Any]] = []
        self.summary: str = ""
        self.saved = False
        self.started = False
        self.errors: list[str] = []

    # ── incremental writes (ordered, off the event loop) ───────────
    def _meta(self, kind: str, **extra: Any) -> dict[str, Any]:
        return {"channel": CHANNEL, "source": "voice_live", "surface": "live_voice", "call_id": self.call_id,
                "kind": kind, "model": self.model, **extra}

    def _write(self, role: str, content: str, kind: str, *, tool_results: list | None = None,
               summary: str | None = None, **extra: Any) -> None:
        def job() -> None:
            try:
                _unified().add_message(
                    self.conversation_id, CHANNEL, role, content,
                    model=self.model or None, tool_results=tool_results,
                    metadata=self._meta(kind, **extra), subject=f"Voice call {self.call_id}",
                    summary=summary, founder_verified=(self.founder_verified and role == "user"),
                    sender=("Founder" if role == "user" else "MAX") if role in ("user", "assistant") else "MAX voice",
                )
            except Exception as exc:  # never break the call over persistence
                self.errors.append(f"unified:{type(exc).__name__}")
                logger.warning("voice_transcript[%s]: unified write failed: %s", self.call_id, exc)
        _writer.submit(job)

    def start(self) -> None:
        self.started = True
        self._write("system", f"[Voice call started {self.started_at.strftime('%Y-%m-%d %I:%M:%S %p')} ET] "
                              f"call {self.call_id}, model {self.model}", "call_start",
                    started_at=self.started_at.isoformat())

    def add_user(self, text: str, item_id: str | None = None) -> None:
        text = (text or "").strip()
        if not text:
            return
        ts = _now_et()
        self.entries.append({"role": "user", "text": text, "t": ts.isoformat(), "item_id": item_id})
        self._write("user", text, "transcript", item_id=item_id, at=ts.isoformat())

    def add_assistant(self, text: str, response_id: str | None = None, interrupted: bool = False) -> None:
        text = (text or "").strip()
        if not text:
            return
        ts = _now_et()
        self.entries.append({"role": "assistant", "text": text, "t": ts.isoformat(),
                             "response_id": response_id, "interrupted": interrupted})
        self._write("assistant", text + (" [interrupted]" if interrupted else ""), "transcript",
                    response_id=response_id, interrupted=interrupted, at=ts.isoformat())

    def add_tool(self, name: str, args: dict, ok: bool, note: str = "") -> None:
        ts = _now_et()
        safe_args = {k: v for k, v in (args or {}).items() if not str(k).startswith("_")}
        self.entries.append({"role": "tool", "name": name, "args": safe_args, "ok": ok, "note": note,
                             "t": ts.isoformat()})
        line = f"[tool] {name}({_short(json.dumps(safe_args, default=str), 300)}) -> {'ok' if ok else 'failed'}"
        if note:
            line += f": {_short(note, 300)}"
        self._write("tool", line, "tool_call", tool_results=[{"tool": name, "success": ok}],
                    tool=name, args=safe_args, ok=ok, at=ts.isoformat())

    # ── end of call ────────────────────────────────────────────────
    def build_summary(self, duration_s: float, end_reason: str) -> str:
        users = [e["text"] for e in self.entries if e["role"] == "user"]
        maxes = [e["text"] for e in self.entries if e["role"] == "assistant" and not e.get("interrupted")]
        tools = [e for e in self.entries if e["role"] == "tool"]
        end = self.ended_at or _now_et()
        parts = [
            f"Voice call with Rafael on {self.started_at.strftime('%a %b %d, %Y')}, "
            f"{self.started_at.strftime('%I:%M %p').lstrip('0')}–{end.strftime('%I:%M %p').lstrip('0')} ET "
            f"({_fmt_dur(duration_s)}, ended: {end_reason}); {len(users)} user turn(s)."
        ]
        if users:
            parts.append("Rafael asked: " + "; ".join(f"“{_short(u, 110)}”" for u in users[:6]) + ".")
        if tools:
            tl = []
            for t in tools[:8]:
                s = f"{t['name']} ({'ok' if t['ok'] else 'failed'})"
                if t.get("note") and t["name"] == "queue_for_founder_approval":
                    s += f" — {_short(t['note'], 120)}"
                tl.append(s)
            parts.append("Tools used: " + ", ".join(tl) + ".")
        else:
            parts.append("No tools used.")
        if maxes:
            parts.append(f"Max's last reply: “{_short(maxes[-1], 200)}”.")
        parts.append(f"Full transcript: conversation {self.conversation_id} (channel voice), "
                     f"Command Center chat {self.chat_id}.")
        return _short(" ".join(parts), 1400)

    def finish(self, duration_s: float, end_reason: str) -> dict[str, Any]:
        """Write call_end + summary to every store. Blocking; call via to_thread."""
        self.ended_at = _now_et()
        if not self.started:
            return {"saved": False, "reason": "not_started", "conversation_id": self.conversation_id}
        if not self.entries:
            # Nothing was said (e.g. connect failure): record the end, skip the rest.
            self._write("system", f"[Voice call ended {self.ended_at.strftime('%I:%M:%S %p')} ET] "
                                  f"{_fmt_dur(duration_s)}, reason {end_reason}, no speech", "call_end",
                        ended_at=self.ended_at.isoformat(), duration_s=duration_s, reason=end_reason)
            _writer.submit(lambda: None).result(timeout=10)
            return {"saved": False, "reason": "empty", "conversation_id": self.conversation_id}
        self.summary = self.build_summary(duration_s, end_reason)
        self._write("system", f"[Voice call ended {self.ended_at.strftime('%I:%M:%S %p')} ET] "
                              f"{_fmt_dur(duration_s)}, reason {end_reason}", "call_end",
                    ended_at=self.ended_at.isoformat(), duration_s=duration_s, reason=end_reason)
        self._write("system", "[Voice call summary] " + self.summary, "summary", summary=self.summary,
                    started_at=self.started_at.isoformat(), ended_at=self.ended_at.isoformat(),
                    duration_s=duration_s, reason=end_reason, chat_id=self.chat_id)
        try:
            _writer.submit(lambda: None).result(timeout=15)  # flush ordered unified writes
        except Exception:
            self.errors.append("unified:flush_timeout")
        self._write_chat_file(duration_s, end_reason)
        self._write_memory()
        self.saved = not any(e.startswith("unified") for e in self.errors)
        logger.info("voice_transcript[%s]: saved=%s entries=%d errors=%s", self.call_id, self.saved,
                    len(self.entries), self.errors or "-")
        return {"saved": self.saved, "conversation_id": self.conversation_id, "chat_id": self.chat_id,
                "entries": len(self.entries), "errors": list(self.errors)}

    def _write_chat_file(self, duration_s: float, end_reason: str) -> None:
        try:
            d = CHATS_DIR / "founder"
            d.mkdir(parents=True, exist_ok=True)
            msgs: list[dict[str, Any]] = []
            pending_tools: list[dict[str, Any]] = []
            for e in self.entries:
                if e["role"] == "tool":
                    pending_tools.append({"tool": e["name"], "success": e["ok"], "args": e.get("args"),
                                          "note": e.get("note") or None})
                    continue
                m = {"role": e["role"], "content": e["text"] + (" [interrupted]" if e.get("interrupted") else ""),
                     "timestamp": e["t"], "channel": CHANNEL}
                if e["role"] == "assistant":
                    m["model"] = self.model
                    if pending_tools:
                        m["voice_tools"] = pending_tools
                        pending_tools = []
                msgs.append(m)
            msgs.append({"role": "assistant", "content": "Voice call summary: " + self.summary,
                         "timestamp": (self.ended_at or _now_et()).isoformat(), "channel": CHANNEL,
                         "model": "voice-summary", **({"voice_tools": pending_tools} if pending_tools else {})})
            first_user = next((e["text"] for e in self.entries if e["role"] == "user"), "")
            data = {
                "id": self.chat_id,
                "title": f"Voice call — {self.started_at.strftime('%b %d, %I:%M %p')} ET",
                "created_at": self.started_at.isoformat(),
                "updated_at": (self.ended_at or _now_et()).isoformat(),
                "pinned": False,
                "preview": _short(first_user, 120),
                "channel": CHANNEL,
                "conversation_id": self.conversation_id,
                "voice": {"call_id": self.call_id, "duration_s": duration_s, "end_reason": end_reason,
                          "started_at": self.started_at.isoformat(),
                          "ended_at": (self.ended_at or _now_et()).isoformat()},
                "messages": msgs,
            }
            path = d / f"{self.chat_id}.json"
            tmp = path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
            tmp.replace(path)
        except Exception as exc:
            self.errors.append(f"chat_file:{type(exc).__name__}")
            logger.warning("voice_transcript[%s]: chat file write failed: %s", self.call_id, exc)

    def _write_memory(self) -> None:
        try:
            from app.services.max.brain.memory_store import MemoryStore
            store = MemoryStore()
            store.add_memory(
                category="conversation", subject="voice_call",
                content="Last voice call — " + self.summary,
                importance=7, source="voice_live", tags=["voice", "voice_call", "transcript"],
                conversation_id=self.conversation_id,
            )
            tools = sorted({e["name"] for e in self.entries if e["role"] == "tool"})
            queued = [e.get("note") for e in self.entries
                      if e["role"] == "tool" and e["name"] == "queue_for_founder_approval" and e["ok"]]
            store.save_conversation_summary(
                conversation_id=self.conversation_id, summary=self.summary,
                tasks_created=[q for q in queued if q], topics=["voice call", "voice"] + tools,
                message_count=sum(1 for e in self.entries if e["role"] in ("user", "assistant")),
            )
        except Exception as exc:
            self.errors.append(f"memory:{type(exc).__name__}")
            logger.warning("voice_transcript[%s]: memory write failed: %s", self.call_id, exc)


# ── Read side (text Max) ────────────────────────────────────────────

def _voice_rows(sql_tail: str, params: tuple) -> list[dict]:
    import sqlite3
    store = _unified()
    conn = sqlite3.connect(str(store.db_path))
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(
            f"SELECT * FROM unified_messages WHERE channel = ? {sql_tail}", (CHANNEL, *params)).fetchall()]
    finally:
        conn.close()


def last_voice_call(max_lines: int = 40) -> Optional[dict[str, Any]]:
    """Most recent voice call: summary, times and transcript lines (chronological)."""
    latest = _voice_rows("ORDER BY id DESC LIMIT 1", ())
    if not latest:
        return None
    conv = latest[0]["conversation_id"]
    rows = _voice_rows("AND conversation_id = ? ORDER BY id ASC", (conv,))
    summary = ""
    started = ended = None
    lines = []
    for r in rows:
        try:
            meta = json.loads(r.get("metadata") or "{}")
        except Exception:
            meta = {}
        kind = meta.get("kind")
        if kind == "summary":
            summary = r.get("summary") or r.get("content") or ""
        elif kind == "call_start":
            started = meta.get("started_at") or r.get("created_at")
        elif kind == "call_end":
            ended = meta.get("ended_at") or r.get("created_at")
        elif r.get("role") in ("user", "assistant", "tool"):
            lines.append({"role": r["role"], "content": r["content"], "at": meta.get("at") or r.get("created_at")})
    return {"conversation_id": conv, "call_id": conv.replace("voice-", "", 1), "summary": summary,
            "started_at": started, "ended_at": ended, "in_progress": ended is None,
            "lines": lines[-max_lines:], "line_count": len(lines)}


def search_voice_messages(query: str, limit: int = 20) -> list[dict]:
    q = (query or "").strip()
    return _voice_rows("AND content LIKE ? ORDER BY id DESC LIMIT ?", (f"%{q}%", int(limit)))


_GENERIC_VOICE_Q = re.compile(
    r"^(the\s+)?(last|latest|recent|previous|most recent)?\s*(voice|phone)?\s*(call|calls|conversation|chat|transcript)s?"
    r"(\s+transcript)?$|^voice$|^voice call.*$|^.*last voice call.*$", re.IGNORECASE)


def is_generic_voice_query(query: str) -> bool:
    return bool(_GENERIC_VOICE_Q.match((query or "").strip()))


def render_last_voice_call_for_prompt(max_chars: int = 1800) -> str:
    """Compact 'Last Voice Call' block for text Max's live brain context."""
    call = last_voice_call(max_lines=12)
    if not call:
        return ""
    head = f"conversation {call['conversation_id']}"
    if call.get("started_at"):
        head += f", started {str(call['started_at'])[:19]}"
    if call.get("in_progress"):
        head += " (in progress or not closed)"
    out = [f"- {head}. Saved in your conversation history (channel voice).",
           "- When Rafael asks about the last/previous voice call, FIRST call "
           '{"tool": "search_conversations", "query": "last voice call", "channel": "voice"} '
           "(returns this call's summary and transcript lines), then answer from that result. "
           "Do not say you checked anything unless that tool ran."]
    if call.get("summary"):
        out.append(f"- Summary: {call['summary']}")
    for ln in call["lines"]:
        out.append(f"  - {ln['role']}: {_short(ln['content'], 160)}")
    text = "\n".join(out)
    return text if len(text) <= max_chars else text[: max_chars - 15] + "\n  ...[trimmed]"
