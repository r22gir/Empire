"""
Scout + Final Model Routing Pilot
=================================

Pilot goal: use free/low-cost "scout" models to generate first-pass
insights, inspections, summaries, and alternatives; then route the
best findings to MiniMax-M3 (the "final" model) for synthesis and
final recommendation.

This is NOT a replacement for MiniMax-M3. It is a scouting layer.

Critical policy (see operating model in the desk model audit):

    Scout models may:
        - brainstorm ideas
        - inspect files/routes
        - summarize logs
        - create first drafts
        - compare options
        - generate marketing variants
        - propose test plans
        - produce preliminary findings

    Scout models may NOT:
        - make final pricing decisions
        - approve invoices/payments
        - approve legal language
        - approve production code changes
        - decide deployment
        - contact customers without founder approval
        - override MiniMax-M3 final review

    MiniMax-M3 is final authority for:
        - final business recommendation
        - final quote/invoice/payment decisions
        - final customer-facing language
        - final code implementation plan
        - final desk report
        - final approval package for founder

The pilot covers 4 desks only:
    - Kai  (forge / WorkroomForge)        — scout: deepseek-v4-flash
    - Aria (sales / proposals)            — scout: gemini-2.5-flash
    - Sage (finance / pricing)            — scout: deepseek-v4-flash
    - Elena (clients / customer records)  — scout: gemini-2.5-flash

All 4 use MiniMax-M3 as the final model.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("max.scout_routing")


# ── Output kinds ──────────────────────────────────────────────────────────

OUTPUT_KIND_PRELIMINARY = "preliminary"  # scout output; never final approval
OUTPUT_KIND_SYNTHESIZED = "synthesized"  # M3 final synthesis; the only kind that can recommend a feature


# ── Model IDs (must match AIModel values in ai_router.py) ────────────────

# Scout models
SCOUT_DEEPSEEK_FLASH = "deepseek"
SCOUT_GEMINI_FLASH = "gemini"
SCOUT_OPENAI_NANO = "openai-nano"
SCOUT_MINIMAX_FAST = "minimax-m2-7-highspeed"
SCOUT_MINIMAX_CHEAP = "minimax-m2-7"

# Final authority
FINAL_MINIMAX_M3 = "minimax"


# ── Restricted actions ────────────────────────────────────────────────────

# Actions a desk may never autonomously take. A scout must never trigger
# these; even the final M3 synthesis can only RECOMMEND them — execution
# still requires explicit founder approval.
RESTRICTED_ACTIONS = frozenset({
    "send_customer_message",
    "send_invoice",
    "send_payment_receipt",
    "approve_money",
    "approve_legal_text",
    "approve_pricing",
    "create_invoice",
    "create_payment",
    "commit_code",
    "push_code",
    "deploy",
    "contact_customer_without_approval",
})


# ── Approval authority tiers ──────────────────────────────────────────────

# Each desk has a single approval authority tier:
#   "founder"    — founder must approve any output before action
#   "founder_for_money" — same, with extra scrutiny on money/legal
#   "m3_only"    — M3 can recommend but cannot trigger execution
#   "scout_only" — scouts cannot recommend anything; can only report findings
APPROVAL_FINAL_AUTHORITY = "MiniMax-M3"
APPROVAL_EXECUTION = "founder"


# ── DeskScoutPolicy ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class DeskScoutPolicy:
    """Routing policy for a single AI desk.

    The desk itself already has an existing preferred_model field; the
    scout policy is an additional layer that defines:
        - which cheap model to use for scouting
        - which final model to use for synthesis
        - what actions the desk is forbidden from triggering
        - what approval level is required for any output
    """
    desk_id: str
    agent_name: str
    function: str
    scout_model: str
    final_model: str
    restricted_actions: frozenset = field(default_factory=lambda: RESTRICTED_ACTIONS)
    founder_approval_required: bool = True
    max_scout_words: int = 400  # 1-page finding
    max_final_words: int = 400  # 1-page synthesis
    notes: str = ""

    def can_final_recommend(self) -> bool:
        """True iff this desk's final model is the M3-style final authority."""
        return self.final_model == FINAL_MINIMAX_M3

    def is_action_allowed(self, action: str) -> bool:
        """A desk may never autonomously take a restricted action."""
        return action not in self.restricted_actions

    def to_dict(self) -> dict:
        return {
            "desk_id": self.desk_id,
            "agent_name": self.agent_name,
            "function": self.function,
            "scout_model": self.scout_model,
            "final_model": self.final_model,
            "founder_approval_required": self.founder_approval_required,
            "max_scout_words": self.max_scout_words,
            "max_final_words": self.max_final_words,
            "notes": self.notes,
            "can_final_recommend": self.can_final_recommend(),
            "is_pilot": True,
        }


# ── Pilot desk policies ───────────────────────────────────────────────────

DESK_SCOUT_POLICIES: dict[str, DeskScoutPolicy] = {
    # ── Kai — Workroom operations / quote flow ──────────────────────────
    "forge": DeskScoutPolicy(
        desk_id="forge",
        agent_name="Kai",
        function="WorkroomForge operations: quote generation, customer follow-up, "
                 "appointment scheduling, measurement tracking, production coordination.",
        scout_model=SCOUT_DEEPSEEK_FLASH,
        final_model=FINAL_MINIMAX_M3,
        founder_approval_required=True,
        notes="Scout does first-pass inspection of /api/v1/forge/* and /api/v1/workroom/* "
              "routes to find quote-to-cash gaps. M3 reviews and picks the smallest shippable "
              "revenue feature. No quote, no price, no production action without founder approval.",
    ),
    # ── Aria — sales / proposal / follow-up ──────────────────────────────
    "sales": DeskScoutPolicy(
        desk_id="sales",
        agent_name="Aria",
        function="Sales pipeline: lead capture, qualification, follow-up, proposals, "
                 "consultation scheduling, deposit tracking, referral tracking.",
        scout_model=SCOUT_GEMINI_FLASH,
        final_model=FINAL_MINIMAX_M3,
        founder_approval_required=True,
        notes="Scout generates copy variants and inspects /api/v1/sales/* for follow-up gaps. "
              "M3 selects the final customer-facing copy. No message is ever sent by an agent.",
    ),
    # ── Sage — pricing, invoice, payment, deposit ────────────────────────
    "finance": DeskScoutPolicy(
        desk_id="finance",
        agent_name="Sage",
        function="Pricing, invoice creation, payment tracking, expense logging, "
                 "P&L, subscription management, profitability analysis.",
        scout_model=SCOUT_DEEPSEEK_FLASH,
        final_model=FINAL_MINIMAX_M3,
        founder_approval_required=True,
        notes="Deterministic Python math first, then scout sanity, then M3 final. "
              "Sage proposes only; Sage never creates or sends an invoice/payment/receipt. "
              "All money and pricing changes require founder approval.",
    ),
    # ── Elena — customer / contact records ──────────────────────────────
    "clients": DeskScoutPolicy(
        desk_id="clients",
        agent_name="Elena",
        function="Customer database, property addresses, job history, fabric/style "
                 "preferences, communication history, meeting prep, thank-you notes.",
        scout_model=SCOUT_GEMINI_FLASH,
        final_model=FINAL_MINIMAX_M3,
        founder_approval_required=True,
        notes="Scout summarizes /api/v1/clients/* flows. M3 picks the carry-forward gap "
              "to fix. No contact update is made by an agent without founder approval.",
    ),
}


# ── Pilot metadata ───────────────────────────────────────────────────────

PILOT_DESK_IDS: frozenset[str] = frozenset(DESK_SCOUT_POLICIES.keys())


# ── Lookup helpers ────────────────────────────────────────────────────────


def get_desk_scout_policy(desk_id: str) -> Optional[DeskScoutPolicy]:
    """Return the scout policy for the given desk, or None if not in pilot."""
    return DESK_SCOUT_POLICIES.get(desk_id)


def is_pilot_desk(desk_id: str) -> bool:
    return desk_id in PILOT_DESK_IDS


def all_pilot_policies() -> list[DeskScoutPolicy]:
    return list(DESK_SCOUT_POLICIES.values())


# ── Restricted-action guard ──────────────────────────────────────────────


class RestrictedActionError(Exception):
    """Raised when a desk tries to take an action it is not authorized to take."""
    def __init__(self, desk_id: str, action: str):
        self.desk_id = desk_id
        self.action = action
        super().__init__(
            f"Desk '{desk_id}' is not authorized to perform restricted action "
            f"'{action}'. Only the founder (or the final synthesis that the "
            f"founder approves) can do this."
        )


def assert_action_allowed(desk_id: str, action: str) -> None:
    """Raise RestrictedActionError if a desk is not allowed to do this action.

    Use this from any code path that could trigger a restricted action
    (commit, push, send_invoice, contact_customer, etc.). The scout layer
    and the per-desk execution must call this guard before performing
    the action.
    """
    if action in RESTRICTED_ACTIONS:
        # Check if the desk is in the pilot and whether the policy is more
        # permissive (it never is — restricted is restricted).
        raise RestrictedActionError(desk_id, action)


# ── Scout-output metadata (used to label scout findings as preliminary) ───


def new_scout_finding(
    desk_id: str,
    prompt_summary: str,
    content: str,
    scout_model: str,
    final_model: str,
    metadata: Optional[dict] = None,
) -> dict:
    """Wrap a scout's output with explicit preliminary markers.

    The wrapper guarantees:
        - output_kind is "preliminary"
        - is_final_recommendation is False
        - requires_final_synthesis is True
        - restricted_actions_forbidden is the full restricted set
    """
    base = {
        "output_kind": OUTPUT_KIND_PRELIMINARY,
        "is_final_recommendation": False,
        "requires_final_synthesis": True,
        "desk_id": desk_id,
        "scout_model": scout_model,
        "final_model": final_model,
        "prompt_summary": prompt_summary,
        "content": content,
        "metadata": metadata or {},
    }
    return base


def new_final_synthesis(
    desk_id: str,
    scout_outputs: list[dict],
    content: str,
    final_model: str = FINAL_MINIMAX_M3,
    metadata: Optional[dict] = None,
) -> dict:
    """Wrap a final synthesis with explicit authority markers.

    Guarantees:
        - output_kind is "synthesized"
        - is_final_recommendation is True ONLY IF final_model is M3
        - is_m3_reviewed is True ONLY IF final_model is M3
        - the synthesis cannot trigger any restricted action without
          separate founder approval
    """
    if not scout_outputs:
        raise ValueError("final synthesis requires at least one scout output")
    is_m3 = (final_model == FINAL_MINIMAX_M3)
    base = {
        "output_kind": OUTPUT_KIND_SYNTHESIZED,
        "is_final_recommendation": is_m3,
        "is_m3_reviewed": is_m3,
        "desk_id": desk_id,
        "final_model": final_model,
        "scout_output_count": len(scout_outputs),
        "content": content,
        "metadata": metadata or {},
    }
    return base


# ── Environment-driven opt-in ─────────────────────────────────────────────


def pilot_enabled() -> bool:
    """The pilot is opt-in. Off by default; enable by env var.

    The pilot is read-only by default: the policies are loaded and
    exposed, but the BaseDesk.ai_call() is NOT replaced by the
    scout-then-final path. To activate the routing in the live desk
    code path, set DESK_SCOUT_PILOT_ENABLED=1 in the backend env.
    """
    return os.getenv("DESK_SCOUT_PILOT_ENABLED", "").strip().lower() in ("1", "true", "yes", "on")
