"""'What are you building / what's next' answered from Max's real internal state.

2026-10-06: Rafael asked "What are you building now?" and "what is empirebox next
step with you" and got web articles, Verified/Sources sections and an invented
roadmap. Questions about Max or EmpireBox's own work never go to the web; they
are answered here, in a few plain lines, from:
  - the improvements queue (building / PR open / waiting on Rafael's tap),
  - commits on this checkout's branch from the last 1-3 days,
  - recent open tasks (waiting / in progress) and pending approval drafts.
Empty categories are skipped. Nothing is invented.
"""
from __future__ import annotations

import logging
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("max.self_status")

REPO_ROOT = Path(__file__).resolve().parents[4]
MAX_WORDS = 14

_RESEARCH_SIGNALS = re.compile(
    r"\b(research|look\s*up|look\s+it\s+up|search|google|web|online|internet|sources?|cite|citations?|"
    r"articles?|news|blogs?|industry|competitors?|market)\b")
# Questions about a specific job/quote/client are not "self status".
_BUSINESS_OBJECT = re.compile(r"\b(quote|estimate|invoice|order|job|client|customer|lead|deposit|payment|drawing)s?\b")

_SELF_PATTERNS = [
    r"\bwhat\s+(?:are|r)\s+(?:you|u)\s+(?:building|working\s+on|doing|up\s+to|coding|shipping|making)\b",
    r"\bwhat\s+(?:have|did)\s+(?:you|u)\s+(?:built|build|shipped|ship|done|do|finished|finish)\b"
    r"(?:\s+(?:today|lately|recently|yesterday|this\s+week))?",
    r"\bwhat(?:'s|s|\s+is)\s+(?:your|ur)\s+(?:status|plan|queue|next\s+step|next\s+move|progress|work)\b",
    r"\bwhat(?:'s|s|\s+is|\s+are)\s+(?:the\s+)?next(?:\s+steps?)?\s*(?:for|with)?\s*(?:you|u|max|empire\s*box|empirebox|empire|us)?\s*$",
    r"\b(?:empire\s*box|empirebox|empire|max)(?:'s)?\s+(?:next\s+steps?|status|progress)\b",
    r"\bnext\s+steps?\s+(?:with|for)\s+(?:you|u|max|empire\s*box|empirebox|empire|us)\b",
    r"\bwhat(?:'s|s|\s+is|\s+are)\s+(?:in\s+progress|in\s+the\s+queue|pending|on\s+deck|being\s+built)\b",
    r"\bwhat(?:'s|s|\s+is)\s+(?:the\s+)?(?:status|progress)\s+(?:of|on)\s+(?:empire\s*box|empirebox|empire|max|you|your\s+work|the\s+build|the\s+builds)\b",
    r"^(?:status|status\s+update|your\s+status|max\s+status|empire\s*box\s+status|empirebox\s+status|"
    r"what's\s+new\s+with\s+you|any\s+updates?|progress\s+update)$",
]
_SELF_RE = [re.compile(p) for p in _SELF_PATTERNS]


def _norm(message: Optional[str]) -> str:
    t = (message or "").lower().replace("\u2019", "'").replace("`", "'")
    t = re.sub(r"[^\w\s']", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"^(?:and|so|ok|okay|hey|hi|max|then|also|well)\b\s*", "", t)
    t = re.sub(r"^(?:and|so|ok|okay|hey|hi|max|then|also|well)\b\s*", "", t)
    return t


def is_self_status_question(message: Optional[str]) -> bool:
    """Short questions about Max's / EmpireBox's own work. Never long or multi-part asks."""
    raw = message or ""
    if raw.count("?") > 1:
        return False
    t = _norm(raw)
    if not t or len(t.split()) > MAX_WORDS:
        return False
    if _RESEARCH_SIGNALS.search(t) or _BUSINESS_OBJECT.search(t):
        return False
    return any(r.search(t) for r in _SELF_RE)


def wants_next_step(message: Optional[str]) -> bool:
    t = _norm(message)
    return bool(re.search(r"\b(next|pending|on deck|in the queue|plan)\b", t))


# ── gather ──────────────────────────────────────────────────────────
def _plain_commit(subject: str) -> str:
    s = re.sub(r"^\s*(?:feat|fix|chore|docs|refactor|test|perf|style)(?:\([^)]*\))?!?:\s*", "", subject)
    s = re.sub(r"^(?:Max(?:\s*\([^)]*\))?|MAX)\s*:\s*", "", s)
    s = re.split(r"\s+[—–]\s+|;\s+|\s+\(", s)[0].strip()
    s = re.sub(r"\bRafael's\b", "your", s)
    s = re.sub(r"\bto Rafael\b", "to you", s)
    s = s[:1].upper() + s[1:]
    return (s[:90].rsplit(" ", 1)[0] + "…") if len(s) > 90 else s


def recent_commits(days: int = 3, limit: int = 6) -> list[dict]:
    try:
        out = subprocess.run(["git", "log", f"--since={days} days ago", "--pretty=%h\t%ad\t%s",
                              "--date=format:%Y-%m-%d", "-n", str(limit * 3)],
                             cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=8)
        rows = []
        for line in (out.stdout or "").splitlines():
            parts = line.split("\t", 2)
            if len(parts) == 3:
                rows.append({"hash": parts[0], "date": parts[1], "text": _plain_commit(parts[2])})
        return rows
    except Exception as exc:
        logger.debug("self_status: git log failed: %s", exc)
        return []


def _improvements() -> list[dict]:
    try:
        from app.services.max import improvements
        return improvements.list_requests().get("items") or []
    except Exception as exc:
        logger.debug("self_status: improvements failed: %s", exc)
        return []


def _approvals_pending() -> int:
    try:
        from app.services.leadforge import growth
        with growth._db() as conn:
            row = conn.execute("SELECT COUNT(*) FROM approval_queue WHERE status='pending'").fetchone()
        return int(row[0] or 0)
    except Exception as exc:
        logger.debug("self_status: approvals failed: %s", exc)
        return 0


def _recent_tasks(days: int = 14) -> list[dict]:
    try:
        from app.services.max.tool_executor import execute_tool
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        out = []
        for st in ("in_progress", "waiting", "todo"):
            r = execute_tool({"tool": "get_tasks", "status": st, "limit": 25}).to_dict()
            for t in (r.get("result") or {}).get("tasks") or []:
                if str(t.get("created_at") or "")[:10] >= cutoff:
                    out.append({"id": t.get("id"), "title": t.get("title") or "", "status": st,
                                "created_at": t.get("created_at")})
        return out
    except Exception as exc:
        logger.debug("self_status: tasks failed: %s", exc)
        return []


def gather() -> dict[str, Any]:
    return {"improvements": _improvements(), "commits": recent_commits(), "approvals_pending": _approvals_pending(),
            "tasks": _recent_tasks()}


# ── format ──────────────────────────────────────────────────────────
def _task_title(t: str) -> str:
    t = re.sub(r"^\[Voice request - needs founder approval\]\s*", "", t or "").strip()
    return (t[:70].rsplit(" ", 1)[0] + "…") if len(t) > 70 else t


def _short(t: str, n: int = 60) -> str:
    t = (t or "").strip()
    return (t[:n].rsplit(" ", 1)[0] + "…") if len(t) > n else t


def _join(items: list[str], n: int) -> str:
    items = [i for i in items if i][:n]
    return "; ".join(items)


def format_status(data: dict, message: Optional[str] = None) -> str:
    imps = data.get("improvements") or []
    building = [i for i in imps if i.get("status") in ("building", "pr_open")]
    waiting_tap = [i for i in imps if i.get("status") in ("proposed", "awaiting_build", "build_failed")]
    commits = data.get("commits") or []
    approvals = int(data.get("approvals_pending") or 0)
    tasks = data.get("tasks") or []
    active_tasks = [t for t in tasks if t["status"] == "in_progress"]
    founder_tasks = [t for t in tasks if t["status"] == "waiting"]
    lines: list[str] = []

    if wants_next_step(message):
        if building:
            lines.append("In progress: " + _join([f"#{i['id']} {_short(i['title'])}" for i in building], 3) + ".")
        if waiting_tap:
            lines.append(f"Waiting on your tap ({len(waiting_tap)} improvement request{'s' if len(waiting_tap) != 1 else ''}): "
                         + _join([f"#{i['id']} {_short(i['title'])}" for i in waiting_tap], 3) + ".")
        if founder_tasks:
            lines.append(f"Waiting on your approval: " + _join([_task_title(t["title"]) for t in founder_tasks], 3) + ".")
        if approvals:
            lines.append(f"{approvals} outreach draft{'s' if approvals != 1 else ''} in Approvals.")
        if not lines:
            lines.append("Nothing is queued right now. Tell me what you want next and I'll file it.")
        return "\n".join(lines)

    if building:
        lines.append("Building now: " + _join([f"#{i['id']} {_short(i['title'])}" for i in building], 3) + ".")
    elif active_tasks:
        lines.append("Working on: " + _join([_task_title(t["title"]) for t in active_tasks], 2) + ".")
    else:
        lines.append("Nothing is building right this minute.")
    if commits:
        today = datetime.now().strftime("%Y-%m-%d")
        shipped_today = [c["text"] for c in commits if c["date"] == today]
        earlier = [c["text"] for c in commits if c["date"] != today]
        if shipped_today:
            lines.append("Shipped today: " + _join(shipped_today, 3) + ".")
        if earlier:
            lines.append(("Before that: " if shipped_today else "Recently shipped: ") + _join(earlier, 2 if shipped_today else 3) + ".")
    if waiting_tap:
        lines.append(f"Waiting on your tap: " + _join([f"#{i['id']} {_short(i['title'])}" for i in waiting_tap], 3) + ".")
    if founder_tasks:
        lines.append(f"{len(founder_tasks)} request{'s' if len(founder_tasks) != 1 else ''} waiting on your approval.")
    return "\n".join(lines)


def answer(message: Optional[str]) -> dict:
    data = gather()
    return {"text": format_status(data, message), "data": data}
