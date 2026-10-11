"""Delegate-first routing for /max/chat.

Max is chief of staff: classify the request to the owning desk *before* the
model answers. Answer directly only for orchestration / status / trivial
lookups. Everything else becomes a tracked desk task.

LLM classification uses the active chat provider only — never disabled Ollama.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from .desk_registry import DESK_IDS, desk_label, live_desk_count

logger = logging.getLogger("max.desks.delegate_first")

# ── Approval gates (founder tap required; Max never executes) ─────────
_APPROVAL = re.compile(
    r"\b(?:send\s+(?:this|it|the|an?|email|invoice|quote)|"
    r"email\s+(?:the\s+)?client|invoice\s+(?:them|the\s+client)|"
    r"charge|take\s+payment|collect\s+payment|process\s+payment|"
    r"change\s+(?:the\s+)?pric(?:e|ing)|cut\s+the\s+price|raise\s+the\s+price|"
    r"sign\s+(?:the\s+)?(?:contract|agreement)|send\s+(?:the\s+)?(?:contract|legal)|"
    r"deploy|merge\s+(?:to|into)\s+(?:main|prod)|push\s+to\s+prod|"
    r"go\s+live|publish\s+to\s+prod)\b",
    re.I,
)

# Orchestration / status — Max answers himself
_ORCH = re.compile(
    r"\b(?:what(?:'s| is| are)?\s+(?:your|the)\s+(?:status|desks?|roster)|"
    r"how\s+many\s+desks|"
    r"who\s+(?:is|are)\s+(?:on|running)\s+(?:the\s+)?desks?|"
    r"desk\s+(?:status|roster|list)|"
    r"what\s+are\s+you\s+(?:working\s+on|building)|"
    r"what'?s\s+next|"
    r"orchestrat|"
    r"chief\s+of\s+staff|"
    r"what\s+can\s+you\s+do|"
    r"who\s+are\s+you|"
    r"what\s+(?:ai|model)\s+are\s+you)\b",
    re.I,
)

# Trivial lookups Max should answer (existing shortcuts / prelookup)
_LOOKUP = re.compile(
    r"\b(?:quote|estimate|cotizaci|"
    r"weather|forecast|"
    r"brief(?:\s+me)?|rundown|agenda|"
    r"check\s+(?:my\s+)?(?:email|inbox|gmail)|"
    r"what(?:'s| is)\s+(?:the\s+)?(?:latest|status|total)|"
    r"show\s+me\s+(?:the\s+)?(?:quote|estimate|invoice|file|doc|pdf)|"
    r"find\s+(?:the\s+)?(?:file|doc|pdf|quote|invoice)|"
    r"open\s+(?:the\s+)?(?:quote|invoice|file|doc))\b",
    re.I,
)

_GREET = re.compile(r"^\s*(?:hi|hey|hello|hola|good\s+(?:morning|afternoon|evening)|thanks|thank you|ok|okay|yes|no)\s*[.!?]*\s*$", re.I)
_FOLLOWUP = re.compile(
    r"\b(?:give\s+me\s+a\s+link|link\s+here|there\s+are\s+no\s+links|"
    r"what do you mean|regenerate where)\b",
    re.I,
)

# Deterministic desk keywords (includes analytics / quality / intake)
DESK_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("analytics", (
        "analytics", "metrics", "kpi", "forecast", "revenue report",
        "daily metrics", "weekly summary", "business intelligence",
        "pipeline analysis", "dashboard numbers",
    )),
    ("quality", (
        "quality audit", "quality digest", "accuracy report", "ai accuracy",
        "quality check", "flagged responses", "quality desk",
    )),
    ("intake", (
        "intake", "luxeforge", "new submission", "incoming project",
        "client submission", "intake form", "new lead form",
    )),
    ("codeforge", (
        "fix the bug", "write code", "edit the file", "refactor",
        "pull request", "run the tests", "typecheck", "implement the",
        "patch the", "commit this",
    )),
    ("forge", (
        "window treatment", "drape", "shade", "cornice", "valance",
        "yardage", "workroom job", "fabric lookup", "measure the window",
    )),
    ("sales", (
        "new lead", "prospect", "pipeline", "follow up with",
        "consultation", "close the deal",
    )),
    ("support", (
        "support ticket", "complaint", "refund", "warranty",
        "unhappy client", "service request",
    )),
    ("marketing", (
        "instagram", "social media", "draft a post", "hashtag",
        "campaign", "pinterest", "facebook post",
    )),
    ("market", (
        "ebay", "relist", "marketplace listing", "facebook marketplace",
        "shipping label", "fulfillment",
    )),
    ("finance", (
        "invoice", "p&l", "expense", "overdue bill", "accounts receivable",
        "billing",
    )),
    ("clients", (
        "client record", "customer record", "client preferences",
        "thank you note", "meeting prep",
    )),
    ("contractors", (
        "installer", "seamstress", "dispatch", "schedule install",
        "crew availability",
    )),
    ("it", (
        "restart the", "disk space", "server down", "uptime",
        "service health", "deploy the service",
    )),
    ("website", (
        "homepage copy", "meta description", "google business",
        "portfolio page", "review response",
    )),
    ("legal", (
        "contract", "terms of service", "liability", "llc filing",
        "warranty policy", "compliance",
    )),
    ("lab", (
        "prototype", "experiment", "r&d", "sandbox test",
    )),
    ("innovation", (
        "competitor", "market scan", "roadmap", "monetize",
        "product idea", "vetforge", "petforge",
    )),
]


@dataclass
class RouteDecision:
    action: str  # answer | delegate | approval
    desk_id: Optional[str] = None
    reason: str = ""
    method: str = "rule"  # rule | llm | specified
    approval_required: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def answers_directly(self) -> bool:
        return self.action == "answer"


def classify_request(
    message: str,
    *,
    specified_desk: Optional[str] = None,
    has_image: bool = False,
) -> RouteDecision:
    """Deterministic classification. LLM is a separate optional step."""
    text = (message or "").strip()
    if specified_desk and specified_desk in DESK_IDS:
        return RouteDecision(
            action="delegate", desk_id=specified_desk,
            reason=f"caller specified desk {specified_desk}", method="specified",
        )
    if not text:
        return RouteDecision(action="answer", reason="empty message")
    if _GREET.match(text):
        return RouteDecision(action="answer", reason="greeting")
    if _FOLLOWUP.search(text):
        return RouteDecision(action="answer", reason="follow-up / not a new desk task")
    if _ORCH.search(text):
        return RouteDecision(action="answer", reason="orchestration/status")
    if _APPROVAL.search(text):
        desk = _keyword_desk(text) or "forge"
        return RouteDecision(
            action="approval", desk_id=desk,
            reason="founder approval required (send/invoice/payment/pricing/legal/deploy)",
            approval_required=True,
        )
    if _LOOKUP.search(text):
        return RouteDecision(action="answer", reason="trivial lookup")
    desk = _keyword_desk(text)
    if desk:
        return RouteDecision(
            action="delegate", desk_id=desk,
            reason=f"keyword rule → {desk}", method="rule",
        )
    # Work-shaped request with no keyword hit: still delegate (inbox if unmatched)
    if _looks_like_work(text) and not has_image:
        return RouteDecision(
            action="delegate", desk_id=None,
            reason="work request, no keyword desk — needs desk or founder inbox",
            method="rule",
        )
    return RouteDecision(action="answer", reason="not a desk task")


def _keyword_desk(text: str) -> Optional[str]:
    low = text.lower()
    best, score = None, 0
    for desk_id, kws in DESK_RULES:
        hits = sum(1 for kw in kws if kw in low)
        if hits > score:
            best, score = desk_id, hits
    return best if score else None


def _looks_like_work(text: str) -> bool:
    return bool(re.search(
        r"\b(?:please|need you to|can you|could you|draft|prepare|build|"
        r"generate|create|write|handle|process|audit|scan|review|research|"
        r"summarize|follow\s+up|schedule|assign)\b",
        text, re.I,
    )) and len(text.split()) >= 4


async def classify_with_active_llm(message: str, fallback: RouteDecision) -> RouteDecision:
    """LLM classify via the *active* provider only. Never Ollama."""
    if fallback.desk_id or fallback.action == "answer":
        return fallback
    try:
        from app.services.max.ai_router import ai_router, AIMessage
        from app.services.max.routing_state import canonical_provider
        from .desk_registry import DESK_ROSTER
    except Exception as exc:
        logger.debug("delegate-first LLM import failed: %s", exc)
        return fallback

    state = ai_router.get_routing_state_payload()
    provider = canonical_provider(str(state.get("selected_provider") or ""))
    if not provider or provider == "ollama" or state.get("ai_calls_disabled"):
        logger.info("delegate-first: skip LLM (provider=%s)", provider)
        return fallback

    roster = "\n".join(f"- {d['id']}: {d['name']} ({d['agent']}) — {d['scope']}" for d in DESK_ROSTER)
    prompt = (
        "Pick the owning desk_id for this founder request. JSON only: "
        '{"desk_id":"id-or-null","confidence":0.0,"reasoning":"..."}\n\n'
        f"Desks:\n{roster}\n\nRequest: {message[:800]}"
    )
    try:
        response = await ai_router.chat(
            messages=[AIMessage(role="user", content=prompt)],
            system_prompt="Task router. Valid JSON only. desk_id must be a listed id or null.",
        )
        if getattr(response, "provider_unavailable", False):
            return fallback
        import json
        m = re.search(r"\{.*\}", response.content or "", re.S)
        if not m:
            return fallback
        data = json.loads(m.group(0))
        desk_id = data.get("desk_id")
        conf = float(data.get("confidence") or 0)
        if desk_id in DESK_IDS and conf >= 0.6:
            return RouteDecision(
                action="delegate", desk_id=desk_id,
                reason=str(data.get("reasoning") or "active-provider classification"),
                method="llm",
            )
    except Exception as exc:
        logger.warning("delegate-first LLM classify failed: %s", exc)
    return fallback


def create_tracked_task(
    *,
    title: str,
    description: str,
    desk_id: Optional[str],
    priority: str = "normal",
    source: str = "delegate_first",
    conversation_id: Optional[str] = None,
    approval_required: bool = False,
) -> dict[str, Any]:
    """Insert a tasks-table row so the worker / desk can pick it up."""
    import json
    import uuid
    from app.db.database import get_db
    from .task_lifecycle import allowed_status

    from .task_lifecycle import migrate_task_status_constraint

    tid = uuid.uuid4().hex[:8]
    status = "waiting" if approval_required else "todo"
    status = allowed_status(status)
    desk = desk_id or "unassigned"
    meta = json.dumps({
        "auto_execute": not approval_required,
        "approval_required": approval_required,
        "source": source,
    })
    with get_db() as conn:
        migrate_task_status_constraint(conn)
        have = {r[1] for r in conn.execute("PRAGMA table_info(tasks)")}
        cols = ["id", "title", "description", "status", "priority", "desk", "created_by", "metadata"]
        vals: list[Any] = [tid, title[:200], description, status, priority, desk, "max", meta]
        if "source" in have:
            cols.append("source")
            vals.append(source)
        if "conversation_id" in have:
            cols.append("conversation_id")
            vals.append(conversation_id)
        if "retry_count" in have:
            cols.append("retry_count")
            vals.append(0)
        if "max_retries" in have:
            cols.append("max_retries")
            vals.append(3)
        placeholders = ", ".join("?" * len(cols))
        conn.execute(
            f"INSERT INTO tasks ({', '.join(cols)}) VALUES ({placeholders})",
            vals,
        )
    if not desk_id:
        from . import founder_inbox
        founder_inbox.add(
            task_id=tid, title=title, description=description,
            priority=priority, reason="no desk matched",
            source=source, conversation_id=conversation_id,
        )
        with get_db() as conn:
            conn.execute(
                "UPDATE tasks SET status='escalated' WHERE id=?", (tid,),
            )
        status = "escalated"
    return {
        "id": tid,
        "title": title,
        "desk": desk_id,
        "desk_label": desk_label(desk_id),
        "status": status,
        "approval_required": approval_required,
    }


def format_delegation_report(decision: RouteDecision, task: dict[str, Any]) -> str:
    n = live_desk_count()
    label = task.get("desk_label") or "founder inbox"
    tid = task["id"]
    status = task["status"]
    if decision.approval_required:
        return (
            f"Held for your tap — {label} drafted the work as task #{tid} ({status}). "
            f"I will not send, invoice, charge, change price, issue legal text, or deploy "
            f"until you approve. ({n} desks; I orchestrate, they execute.)"
        )
    if status == "escalated":
        return (
            f"No desk matched that request. Filed in the founder inbox as task #{tid}. "
            f"Tell me which desk should own it and I'll assign it."
        )
    return (
        f"Delegated to {label} as task #{tid} ({status}). "
        f"I'll track it, verify the output, and report back. "
        f"I don't do the desk's work myself."
    )


async def maybe_delegate(
    message: str,
    *,
    specified_desk: Optional[str] = None,
    conversation_id: Optional[str] = None,
    has_image: bool = False,
) -> Optional[dict[str, Any]]:
    """If the message should be a desk task, create it and return a report dict.

    Returns None when Max should answer directly (shortcuts already handled).
    """
    decision = classify_request(
        message, specified_desk=specified_desk, has_image=has_image,
    )
    if decision.answers_directly:
        return None
    if decision.action == "delegate" and not decision.desk_id:
        decision = await classify_with_active_llm(message, decision)
        if decision.answers_directly:
            return None
    title = (message or "").strip().split("\n")[0][:160] or "Desk task"
    task = create_tracked_task(
        title=title,
        description=message,
        desk_id=decision.desk_id,
        conversation_id=conversation_id,
        approval_required=decision.approval_required,
    )
    report = format_delegation_report(decision, task)
    return {
        "decision": decision,
        "task": task,
        "report": report,
        "model_used": "delegate-first",
    }
