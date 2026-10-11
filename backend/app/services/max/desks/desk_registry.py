"""Live 17-desk roster — single source of truth for Max the orchestrator.

The registered AI desks (see AIDeskManager.initialize) are the live count.
CostTracker is a tool/budget surface, not a desk. Do not invent an 18th desk.
"""
from __future__ import annotations

from typing import Any

# Agent + scope for each registered desk. Order matches AIDeskManager.initialize().
DESK_ROSTER: list[dict[str, str]] = [
    {"id": "forge", "name": "ForgeDesk", "agent": "Kai",
     "scope": "Workroom operations: quotes, scheduling, fabric, production, measurements"},
    {"id": "market", "name": "MarketDesk", "agent": "Sofia",
     "scope": "Marketplace ops: eBay/Facebook listings, inventory, shipping, relist"},
    {"id": "marketing", "name": "MarketingDesk", "agent": "Nova",
     "scope": "Social media, content drafts, campaigns, SEO copy"},
    {"id": "support", "name": "SupportDesk", "agent": "Luna",
     "scope": "Customer support, ticket triage, refunds, warranty"},
    {"id": "sales", "name": "SalesDesk", "agent": "Aria",
     "scope": "Sales pipeline, leads, follow-ups, proposals, deposits"},
    {"id": "finance", "name": "FinanceDesk", "agent": "Sage",
     "scope": "Invoices, payments, expenses, P&L — drafts only until founder approval"},
    {"id": "clients", "name": "ClientsDesk", "agent": "Elena",
     "scope": "Client records, preferences, meeting prep, history"},
    {"id": "contractors", "name": "ContractorsDesk", "agent": "Marcus",
     "scope": "Installer/seamstress scheduling, crew, dispatch, pay rates"},
    {"id": "it", "name": "ITDesk", "agent": "Orion",
     "scope": "Systems admin, health checks, monitoring, restarts (PIN/founder session)"},
    {"id": "website", "name": "WebsiteDesk", "agent": "Zara",
     "scope": "Website copy, SEO, portfolio, Google Business, review responses"},
    {"id": "legal", "name": "LegalDesk", "agent": "Raven",
     "scope": "Contracts, terms, compliance, insurance — never send without founder approval"},
    {"id": "lab", "name": "LabDesk", "agent": "Phoenix",
     "scope": "R&D sandbox, prototypes, experiments (no production writes)"},
    {"id": "innovation", "name": "InnovationDesk", "agent": "Spark",
     "scope": "Market scan, competitor watch, product ideas, roadmap"},
    {"id": "intake", "name": "IntakeDesk", "agent": "Zara",
     "scope": "LuxeForge submissions, project classification, routing to Workroom/Craft"},
    {"id": "analytics", "name": "AnalyticsDesk", "agent": "Raven",
     "scope": "Business intelligence, metrics, forecasts, daily/weekly summaries"},
    {"id": "quality", "name": "QualityDesk", "agent": "Phoenix",
     "scope": "AI accuracy monitoring, quality digests, escalation of bad outputs"},
    {"id": "codeforge", "name": "CodeForge", "agent": "Atlas",
     "scope": "Code edits, git, tests via code_task_runner (MiniMax). Not OpenClaw."},
]

DESK_IDS = tuple(d["id"] for d in DESK_ROSTER)

OPERATING_PROCEDURE = (
    "1. Pick the owning desk from the roster (deterministic rules first).\n"
    "2. Delegate: create a tracked desk task (never answer the work yourself).\n"
    "3. Track: persist status (todo / in_progress / waiting / done / failed / escalated).\n"
    "4. Verify: review desk output against the original request before reporting done.\n"
    "5. Report: tell the founder the desk, task id, state, and next step.\n"
    "6. Escalate: unmatched, blocked, or approval-gated work goes to the founder inbox."
)

APPROVAL_GATED_ACTIONS = (
    "outbound send", "invoice send", "payment", "pricing change", "legal send", "deploy",
)


def live_desk_count() -> int:
    """Live count from the registered desk manager when available, else the roster."""
    try:
        from app.services.max.desks.desk_manager import desk_manager
        desk_manager.initialize()
        n = len(desk_manager.router.desk_ids)
        if n:
            return n
    except Exception:
        pass
    return len(DESK_ROSTER)


def roster_by_id() -> dict[str, dict[str, str]]:
    return {d["id"]: d for d in DESK_ROSTER}


def desk_label(desk_id: str | None) -> str:
    if not desk_id:
        return "unassigned"
    row = roster_by_id().get(desk_id)
    if not row:
        return desk_id
    return f"{row['agent']} ({row['name']})"


def roster_prompt_block() -> str:
    """System-prompt section: real roster + operating procedure. No OpenClaw target."""
    n = live_desk_count()
    lines = [
        f"=== DESK SYSTEM ({n} DESKS) ===",
        "",
        "You are the orchestrator / chief of staff of the desks below. You do not do their work.",
        "Procedure: pick desk → delegate → track → verify → report → escalate.",
        "Never delegate to OpenClaw (quarantined). Never invent a desk that is not on this roster.",
        "",
        "Roster (name — agent — scope):",
    ]
    for i, d in enumerate(DESK_ROSTER, 1):
        lines.append(f"{i}. **{d['agent']}** → {d['name']} (`{d['id']}`) — {d['scope']}")
    lines += [
        "",
        "Operating procedure:",
        OPERATING_PROCEDURE,
        "",
        "Approval gate (founder tap required, Max never executes): outbound sends, invoices,",
        "payments, pricing changes, legal documents, deploys/merges.",
        "Improvements (IMP-NNNN): file the request and send the Studio deep link;",
        "approval is Rafael's tap only.",
        "",
        "Atlas (CodeForge) handles code on MiniMax M3 via code_task_runner. For small read-only",
        "code questions use file_read + git_ops yourself; delegate real edits to Atlas.",
    ]
    return "\n".join(lines)


def registry_payload() -> dict[str, Any]:
    return {
        "desk_count": live_desk_count(),
        "desks": list(DESK_ROSTER),
        "procedure": OPERATING_PROCEDURE,
        "openclaw_is_delegation_target": False,
    }
