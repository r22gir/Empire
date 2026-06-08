"""Tests for the AI Desk scout + final model routing pilot.

The pilot covers 4 desks: Kai (forge), Aria (sales), Sage (finance),
Elena (clients). Each desk has a registered scout policy:
    - scout_model: a free/low-cost model for first-pass work
    - final_model: MiniMax-M3 (the only model allowed to recommend)
    - founder_approval_required: True (always)
    - restricted_actions: full set, always enforced

These tests pin the policy so any change to the policy (e.g.
removing the guard, changing the final model, widening the
restricted-actions set) is caught.

We do not make live API calls. We only inspect the in-process
policy object and the guard logic.
"""
import os
import sys
import importlib
import pytest

LIVE_VENV = "/home/rg/empire-repo/backend/venv/lib/python3.12/site-packages"
if LIVE_VENV not in sys.path:
    sys.path.insert(0, LIVE_VENV)

import pytest

from app.services.max.scout_routing import (
    DESK_SCOUT_POLICIES,
    PILOT_DESK_IDS,
    DeskScoutPolicy,
    OUTPUT_KIND_PRELIMINARY,
    OUTPUT_KIND_SYNTHESIZED,
    RESTRICTED_ACTIONS,
    FINAL_MINIMAX_M3,
    SCOUT_DEEPSEEK_FLASH,
    SCOUT_GEMINI_FLASH,
    RestrictedActionError,
    all_pilot_policies,
    assert_action_allowed,
    get_desk_scout_policy,
    is_pilot_desk,
    new_final_synthesis,
    new_scout_finding,
    pilot_enabled,
)


# ── 1. Pilot desk registry ───────────────────────────────────────────────

def test_four_pilot_desks_registered():
    """The pilot has exactly 4 desks: forge, sales, finance, clients."""
    assert PILOT_DESK_IDS == frozenset({"forge", "sales", "finance", "clients"})
    assert set(DESK_SCOUT_POLICIES.keys()) == {"forge", "sales", "finance", "clients"}


@pytest.mark.parametrize("desk_id,agent,scout,final", [
    ("forge", "Kai", SCOUT_DEEPSEEK_FLASH, FINAL_MINIMAX_M3),
    ("sales", "Aria", SCOUT_GEMINI_FLASH, FINAL_MINIMAX_M3),
    ("finance", "Sage", SCOUT_DEEPSEEK_FLASH, FINAL_MINIMAX_M3),
    ("clients", "Elena", SCOUT_GEMINI_FLASH, FINAL_MINIMAX_M3),
])
def test_each_pilot_desk_has_scout_and_final(desk_id, agent, scout, final):
    p = get_desk_scout_policy(desk_id)
    assert p is not None, f"desk {desk_id} not in pilot"
    assert p.agent_name == agent
    assert p.scout_model == scout
    assert p.final_model == final
    assert p.can_final_recommend() is True, "M3 must be the final model"
    assert p.founder_approval_required is True


# ── 2. Restricted actions guard ──────────────────────────────────────────

RESTRICTED_SAMPLE = [
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
]


@pytest.mark.parametrize("action", RESTRICTED_SAMPLE)
def test_restricted_action_guard_raises(action):
    """Every restricted action must raise when guard is called for any desk."""
    for desk_id in ("forge", "sales", "finance", "clients"):
        with pytest.raises(RestrictedActionError):
            assert_action_allowed(desk_id, action)


@pytest.mark.parametrize("action", ["inspect_file", "summarize_log", "draft_copy", "compare_options", "brainstorm"])
def test_non_restricted_actions_pass_guard(action):
    """Inspecting, summarizing, drafting, comparing, brainstorming must NOT raise."""
    for desk_id in ("forge", "sales", "finance", "clients"):
        assert_action_allowed(desk_id, action)  # must not raise


def test_restricted_set_is_comprehensive():
    """The restricted set must contain every action that touches money, code,
    customer comms, legal text, or production deployment."""
    required = {
        "send_customer_message", "send_invoice", "send_payment_receipt",
        "approve_money", "approve_legal_text", "approve_pricing",
        "create_invoice", "create_payment",
        "commit_code", "push_code", "deploy",
        "contact_customer_without_approval",
    }
    assert required.issubset(RESTRICTED_ACTIONS)


# ── 3. Scout vs final output kinds ───────────────────────────────────────

def test_scout_finding_is_preliminary():
    f = new_scout_finding("forge", "inspect quote flow", "5 gaps found",
                          SCOUT_DEEPSEEK_FLASH, FINAL_MINIMAX_M3)
    assert f["output_kind"] == OUTPUT_KIND_PRELIMINARY
    assert f["is_final_recommendation"] is False
    assert f["requires_final_synthesis"] is True
    assert f["scout_model"] == SCOUT_DEEPSEEK_FLASH
    assert f["final_model"] == FINAL_MINIMAX_M3


def test_final_synthesis_m3_is_final_recommendation():
    """Only M3 final synthesis can be a final recommendation."""
    f = new_scout_finding("forge", "inspect", "...", SCOUT_DEEPSEEK_FLASH, FINAL_MINIMAX_M3)
    s = new_final_synthesis("forge", [f], "selected: smaller quote card", FINAL_MINIMAX_M3)
    assert s["output_kind"] == OUTPUT_KIND_SYNTHESIZED
    assert s["is_final_recommendation"] is True
    assert s["is_m3_reviewed"] is True


def test_non_m3_synthesis_is_NOT_a_final_recommendation():
    """A non-M3 model synthesizing cannot be a final recommendation.

    This is the central policy: only MiniMax-M3 has final-review authority.
    A scout (DeepSeek/Gemini) synthesizing without M3 review must NOT
    be marked as a final recommendation, even if it has the same shape.
    """
    f = new_scout_finding("forge", "inspect", "...", SCOUT_DEEPSEEK_FLASH, FINAL_MINIMAX_M3)
    s = new_final_synthesis("forge", [f], "this is a scout pretending to be final", "deepseek")
    assert s["output_kind"] == OUTPUT_KIND_SYNTHESIZED  # wrapper label is synthesized
    assert s["is_final_recommendation"] is False  # but it's not actually final
    assert s["is_m3_reviewed"] is False


def test_final_synthesis_requires_at_least_one_scout_output():
    """A final synthesis with no scout outputs is a policy violation.

    The whole point of the pilot is scout → final. Empty scout list
    means the final is recommending without a scout's preliminary work.
    """
    with pytest.raises(ValueError):
        new_final_synthesis("forge", [], "i have no scout context", FINAL_MINIMAX_M3)


# ── 4. Code-writing is only allowed for Harry ────────────────────────────

def test_harry_is_the_only_code_writing_desk():
    """The four pilot desks are Kai/Aria/Sage/Elena — none of them write code.

    Code-writing is restricted to Harry (the opencode remote lane).
    The restricted-actions set catches commit_code and push_code, so
    any attempt by a pilot desk to commit/push will raise.
    """
    for did in ("forge", "sales", "finance", "clients"):
        with pytest.raises(RestrictedActionError):
            assert_action_allowed(did, "commit_code")
        with pytest.raises(RestrictedActionError):
            assert_action_allowed(did, "push_code")


# ── 5. Founder approval is required for every pilot desk ─────────────────

@pytest.mark.parametrize("desk_id", ["forge", "sales", "finance", "clients"])
def test_founder_approval_required_for_pilot_desks(desk_id):
    p = get_desk_scout_policy(desk_id)
    assert p.founder_approval_required is True


# ── 6. Fallback behavior if a scout model is unavailable ─────────────────

def test_fallback_marker_in_synthesis():
    """The synthesis metadata should be able to carry fallback info if a
    scout was unavailable. The pilot does NOT require that field, but
    the wrapper must accept a fallback_used=True flag and surface it
    honestly.
    """
    f = new_scout_finding("forge", "inspect", "5 gaps",
                          SCOUT_DEEPSEEK_FLASH, FINAL_MINIMAX_M3)
    s = new_final_synthesis(
        "forge", [f], "selected: gap 3",
        FINAL_MINIMAX_M3,
        metadata={"scout_fallback": True, "scout_fallback_reason": "deepseek_503"},
    )
    assert s["metadata"]["scout_fallback"] is True
    assert s["metadata"]["scout_fallback_reason"] == "deepseek_503"
    # Fallback is just metadata; the synthesis is still M3-reviewed.
    assert s["is_m3_reviewed"] is True
    assert s["is_final_recommendation"] is True


def test_pilot_disabled_by_default():
    """The pilot is opt-in via DESK_SCOUT_PILOT_ENABLED env var.

    By default the policy registry is loaded (so the endpoint can
    surface it) but the live desk code paths do not switch over to
    the scout-then-final routing. This test pins the default.
    """
    # Ensure the env var is unset when this test runs
    os.environ.pop("DESK_SCOUT_PILOT_ENABLED", None)
    # pilot_enabled() reads the env at call time, so no module reload needed.
    assert pilot_enabled() is False


def test_pilot_enabled_when_env_set():
    os.environ["DESK_SCOUT_PILOT_ENABLED"] = "1"
    try:
        assert pilot_enabled() is True
    finally:
        # Always reset, even if the assertion fails
        os.environ.pop("DESK_SCOUT_PILOT_ENABLED", None)
        assert pilot_enabled() is False  # back to default
# ── 7. Pipeline 1 dry-run/report-only mode ───────────────────────────────

def test_pipeline1_dry_run_invariants():
    """The Pipeline 1 dry-run is purely informational. The scout outputs
    and the M3 synthesis are returned as data only — no code writes,
    no commits, no customer messages, no invoices.
    """
    # Defensive: ensure no env var from prior tests is leaking
    os.environ.pop("DESK_SCOUT_PILOT_ENABLED", None)

    scouts = [
        new_scout_finding(desk_id, "inspect", f"{desk_id} findings",
                          SCOUT_DEEPSEEK_FLASH if desk_id in ("forge", "finance") else SCOUT_GEMINI_FLASH,
                          FINAL_MINIMAX_M3)
        for desk_id in ("forge", "sales", "finance", "clients")
    ]
    # All scout outputs are preliminary, none are final recommendations.
    for s in scouts:
        assert s["is_final_recommendation"] is False
        assert s["requires_final_synthesis"] is True

    # The M3 synthesis is the only thing that can recommend a feature.
    synthesis = new_final_synthesis(
        "pilot", scouts,
        "selected: smaller quote card (1 PR, 4 files)",
        FINAL_MINIMAX_M3,
    )
    assert synthesis["is_final_recommendation"] is True
    assert synthesis["is_m3_reviewed"] is True
    assert synthesis["scout_output_count"] == 4

    # The dry-run did NOT trigger any restricted action.
    for action in RESTRICTED_SAMPLE:
        with pytest.raises(RestrictedActionError):
            assert_action_allowed("pilot", action)


# ── 8. Desk classes carry the policy at __init__ time ────────────────────

@pytest.mark.parametrize("module_name,class_name,desk_id", [
    ("app.services.max.desks.forge_desk", "ForgeDesk", "forge"),
    ("app.services.max.desks.sales_desk", "SalesDesk", "sales"),
    ("app.services.max.desks.finance_desk", "FinanceDesk", "finance"),
    ("app.services.max.desks.clients_desk", "ClientsDesk", "clients"),
])
def test_desk_class_resolves_to_pilot_policy(module_name, class_name, desk_id):
    """The 4 pilot desk classes are mapped to the right policy keys.

    We don't instantiate (BaseDesk is abstract and requires _handle_task
    in subclasses — instantiation is fine, but we don't need to here).
    The point is the desk_id matches the policy registry.
    """
    m = importlib.import_module(module_name)
    cls = getattr(m, class_name)
    assert cls.desk_id == desk_id
    p = get_desk_scout_policy(cls.desk_id)
    assert p is not None, f"desk {desk_id} is not in the pilot policy registry"
    assert p.final_model == FINAL_MINIMAX_M3
