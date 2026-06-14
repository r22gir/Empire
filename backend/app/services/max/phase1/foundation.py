"""Static Phase 1 validation helpers for MAX/OpenClaw orchestration.

This module intentionally performs no runtime checks, no task execution, no
notifications, and no service mutations. It only loads bundled Phase 1 artifacts
and validates their shape.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"

APPROVAL_PHRASES = {
    "APPROVE LIVE STRIPE ACTION",
    "APPROVE CLOUDFLARE/DNS CHANGE",
    "APPROVE SERVICE RESTART",
    "APPROVE PUSH",
    "APPROVE MERGE TO MAIN",
    "APPROVE CODEX IMPLEMENTATION",
    "APPROVE GATE 1 EXECUTION",
    "APPROVE GATE 3 PRODUCTION PR",
}

GATE_1_REQUIRED_APPROVALS = {
    "APPROVE CLOUDFLARE/DNS CHANGE",
    "APPROVE SERVICE RESTART",
    "APPROVE GATE 1 EXECUTION",
}

HEALTH_STATES = {"healthy", "degraded", "blocked", "stale", "unknown"}
RISK_LEVELS = {"low", "medium", "high", "critical"}
IMPACT_LEVELS = {"none", "possible", "active"}


def load_artifact(name: str) -> dict[str, Any]:
    """Load a bundled Phase 1 JSON artifact by file name."""
    if "/" in name or "\\" in name or name.startswith("."):
        raise ValueError("artifact name must be a file name")
    path = ARTIFACT_DIR / name
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def approval_matches(value: str) -> bool:
    """Return True only for exact Founder approval phrases."""
    return value in APPROVAL_PHRASES


def openclaw_execution_allowed_by_default() -> bool:
    """Phase 1 never enables OpenClaw task execution."""
    return False


def notifications_enabled_by_default() -> bool:
    """Phase 1 notification templates are opt-in only."""
    return False


def is_gate_launch_ready(gate: dict[str, Any]) -> bool:
    """Gate 1 cannot be launch-ready while required approvals are missing."""
    if gate.get("gate") != "Gate 1":
        return bool(gate.get("launch_ready"))

    missing = set(gate.get("required_approvals_missing", []))
    if missing & GATE_1_REQUIRED_APPROVALS:
        return False
    return bool(gate.get("launch_ready"))


def validate_approval_table(data: dict[str, Any]) -> None:
    phrases = data.get("approval_phrases")
    if set(phrases or []) != APPROVAL_PHRASES:
        raise ValueError("approval phrase table must contain exact required phrases")
    for action in data.get("gated_actions", []):
        phrase = action.get("required_phrase")
        if phrase not in APPROVAL_PHRASES:
            raise ValueError(f"unknown approval phrase for action {action.get('action')}")
    dormant = data.get("openclaw_empire_git", {})
    if dormant.get("commit_push_capability") != "dormant":
        raise ValueError("OpenClaw empire-git commit/push capability must be dormant")


def validate_health_register_template(data: dict[str, Any]) -> None:
    required = {
        "component_name",
        "role",
        "state",
        "last_check_time",
        "last_known_good_state",
        "evidence",
        "owner",
        "backup_diagnostician",
        "pending_approval",
        "pending_audit",
        "recent_changes",
        "next_action",
        "risk_level",
        "public_impact",
        "operator_impact",
        "payment_security_impact",
    }
    component = data.get("component_template", {})
    missing = required - set(component)
    if missing:
        raise ValueError(f"health component template missing fields: {sorted(missing)}")
    if set(data.get("allowed_states", [])) != HEALTH_STATES:
        raise ValueError("health register states mismatch")
    if set(data.get("risk_levels", [])) != RISK_LEVELS:
        raise ValueError("health register risk levels mismatch")
    if set(data.get("impact_levels", [])) != IMPACT_LEVELS:
        raise ValueError("health register impact levels mismatch")


def validate_gate_register_template(data: dict[str, Any]) -> None:
    required = {
        "gate",
        "name",
        "state",
        "launch_ready",
        "required_approvals_missing",
        "blockers",
        "evidence",
        "last_report",
        "next_operator",
        "independent_audit_required",
    }
    gate = data.get("gate_template", {})
    missing = required - set(gate)
    if missing:
        raise ValueError(f"gate template missing fields: {sorted(missing)}")
    gate1 = next((item for item in data.get("gate_examples", []) if item.get("gate") == "Gate 1"), None)
    if not gate1:
        raise ValueError("Gate 1 example is required")
    if is_gate_launch_ready(gate1):
        raise ValueError("Gate 1 example must not be launch-ready with missing approvals")


def validate_triage_matrix(data: dict[str, Any]) -> None:
    required_components = {
        "MAX",
        "OpenClaw",
        "Hermes",
        "Harry / OpenCode",
        "Codex",
        "M3",
        "Portal frontend",
        "Backend API",
        "Cloudflare main tunnel",
        "Cloudflare ApostApp tunnel",
        "DNS/public edge",
        "Cloudflare Access",
        "Stripe/payment system",
        "Git/repo branches",
        "Notifications",
        "Public surfaces",
        "Operator surfaces",
        "Workroom",
        "Woodcraft",
        "ApostApp",
        "PlatformForge",
        "Pricing Studio",
        "ArchiveForge",
        "RecoveryForge",
    }
    rows = data.get("components", [])
    present = {row.get("component") for row in rows}
    missing_components = required_components - present
    if missing_components:
        raise ValueError(f"triage matrix missing components: {sorted(missing_components)}")
    row_fields = {
        "component",
        "owner",
        "backup_diagnostician",
        "safe_read_only_health_check",
        "failure_symptoms",
        "repair_path",
        "required_approval_phrase",
        "audit_requirement",
    }
    for row in rows:
        missing = row_fields - set(row)
        if missing:
            raise ValueError(f"triage matrix row missing fields: {sorted(missing)}")


def validate_report_templates(data: dict[str, Any]) -> None:
    required_fields = {
        "operator_session_used",
        "access_mode",
        "branch_head_if_applicable",
        "runtime_service_state_if_applicable",
        "commands_checks_run",
        "files_touched",
        "mutations_made",
        "forbidden_actions_avoided",
        "evidence",
        "risks",
        "verdict",
        "required_founder_approvals",
        "next_recommended_operator",
        "independent_audit_needed",
    }
    required_templates = {
        "max_report",
        "harry_report",
        "hermes_audit",
        "codex_plan_report",
        "openclaw_report",
    }
    templates = data.get("templates", {})
    if set(templates) != required_templates:
        raise ValueError("report templates mismatch")
    for name, template in templates.items():
        missing = required_fields - set(template.get("fields", []))
        if missing:
            raise ValueError(f"{name} missing report fields: {sorted(missing)}")


def validate_prompt_templates(data: dict[str, Any]) -> None:
    required = {
        "read_only_diagnosis",
        "codex_implementation_plan",
        "harry_execution",
        "hermes_audit",
        "openclaw_bounded_task_proposal",
        "service_restart_request",
        "cloudflare_dns_request",
        "stripe_hard_stop_request",
        "gate_closeout",
    }
    templates = data.get("templates", {})
    missing = required - set(templates)
    if missing:
        raise ValueError(f"prompt templates missing: {sorted(missing)}")
    for name, template in templates.items():
        if not template.get("title") or not template.get("body"):
            raise ValueError(f"{name} prompt template must include title and body")
        if template.get("runtime_execution_allowed") is True:
            raise ValueError(f"{name} prompt template cannot allow runtime execution by default")


def validate_all_phase1_artifacts() -> None:
    """Validate all bundled Phase 1 artifacts."""
    validate_approval_table(load_artifact("approval_phrases.json"))
    validate_health_register_template(load_artifact("health_register_template.json"))
    validate_gate_register_template(load_artifact("gate_register_template.json"))
    validate_triage_matrix(load_artifact("triage_self_heal_matrix.json"))
    validate_report_templates(load_artifact("report_templates.json"))
    validate_prompt_templates(load_artifact("prompt_templates.json"))
