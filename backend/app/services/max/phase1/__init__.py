"""Phase 1 MAX/OpenClaw orchestration foundation artifacts."""

from .foundation import (
    APPROVAL_PHRASES,
    GATE_1_REQUIRED_APPROVALS,
    approval_matches,
    is_gate_launch_ready,
    load_artifact,
    notifications_enabled_by_default,
    openclaw_execution_allowed_by_default,
    validate_all_phase1_artifacts,
)

__all__ = [
    "APPROVAL_PHRASES",
    "GATE_1_REQUIRED_APPROVALS",
    "approval_matches",
    "is_gate_launch_ready",
    "load_artifact",
    "notifications_enabled_by_default",
    "openclaw_execution_allowed_by_default",
    "validate_all_phase1_artifacts",
]
