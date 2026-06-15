import pytest

from app.services.max.phase1 import foundation


def test_approval_phrase_exact_matching():
    for phrase in foundation.APPROVAL_PHRASES:
        assert foundation.approval_matches(phrase) is True


@pytest.mark.parametrize(
    "phrase",
    [
        "approve push",
        "APPROVE PUSH ",
        " APPROVE PUSH",
        "APPROVE CODEX",
        "APPROVE SERVICE RESTART NOW",
        "APPROVE LIVE STRIPE",
    ],
)
def test_invalid_approval_phrase_rejection(phrase):
    assert foundation.approval_matches(phrase) is False


def test_schema_and_template_artifacts_are_valid():
    foundation.validate_all_phase1_artifacts()


def test_gate_1_not_launch_ready_while_approvals_missing():
    data = foundation.load_artifact("gate_register_template.json")
    gate1 = next(item for item in data["gate_examples"] if item["gate"] == "Gate 1")

    assert foundation.is_gate_launch_ready(gate1) is False

    still_missing_restart = {
        **gate1,
        "launch_ready": True,
        "required_approvals_missing": ["APPROVE SERVICE RESTART"],
    }
    assert foundation.is_gate_launch_ready(still_missing_restart) is False


def test_openclaw_execution_blocked_by_default():
    assert foundation.openclaw_execution_allowed_by_default() is False

    approvals = foundation.load_artifact("approval_phrases.json")
    assert approvals["openclaw_empire_git"]["commit_push_capability"] == "dormant"


def test_notification_sending_disabled_by_default():
    assert foundation.notifications_enabled_by_default() is False

    prompts = foundation.load_artifact("prompt_templates.json")
    assert prompts["notification_policy"] == "opt_in_only"
    for template in prompts["templates"].values():
        assert template["runtime_execution_allowed"] is False


def test_report_template_required_fields():
    data = foundation.load_artifact("report_templates.json")
    required = set(data["required_fields"])

    for template in data["templates"].values():
        assert required.issubset(set(template["fields"]))
