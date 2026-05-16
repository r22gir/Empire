"""v10 MAX operations capability registry and lightweight NL parser.

This registry is intentionally capability-oriented: it maps founder language to
approved MAX/Hermes/OpenClaw control-plane operations without turning MAX into a
rigid command menu.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any


TASK_ID_PATTERNS = (
    re.compile(r"\btask[_\s-]*id\s*[:=#]?\s*(\d+)\b", re.IGNORECASE),
    re.compile(r"\btask\s*#\s*(\d+)\b", re.IGNORECASE),
    re.compile(r"\bopen\s*claw\s+task\s*[:=#]?\s*(\d+)\b", re.IGNORECASE),
    re.compile(r"\btask\s+(\d+)\b", re.IGNORECASE),
)
TASK_REF_PATTERN = re.compile(r"\btask_ref\s*=\s*([A-Za-z0-9_-]{3,120})\b", re.IGNORECASE)


@dataclass(frozen=True)
class OperationCapability:
    capability_id: str
    route_name: str
    model_used: str
    description: str
    natural_language_examples: tuple[str, ...]
    intent_actions: tuple[str, ...]
    intent_objects: tuple[str, ...]
    required_entities: tuple[str, ...]
    optional_entities: tuple[str, ...]
    read_only: bool
    mutates_state: bool
    requires_founder_approval: bool
    requires_task_ref: bool
    allowed_lanes: tuple[str, ...]
    forbidden_lanes: tuple[str, ...]
    safety_gates: tuple[str, ...]
    handler_name: str
    fallback_message: str
    report_fields: tuple[str, ...]
    enabled: bool = True

    def to_public_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["examples"] = data.pop("natural_language_examples")
        return data


@dataclass(frozen=True)
class ParsedOperationIntent:
    capability_id: str | None
    route_name: str | None
    action: str | None
    object: str | None
    entities: dict[str, Any]
    modifiers: dict[str, Any]
    confidence: float
    unsupported_intent: str | None = None
    reason: str | None = None


CAPABILITIES: tuple[OperationCapability, ...] = (
    OperationCapability(
        capability_id="runtime_lane_verify",
        route_name="supervised-v10-repair-preflight",
        model_used="supervised-v10-repair-preflight",
        description="Verify v10 lane, git freshness, Hermes artifact status, and bounded-task safety.",
        natural_language_examples=(
            "check v10 status",
            "run preflight",
            "verify the lane",
            "are we safe to create a task?",
        ),
        intent_actions=("verify", "preflight", "status"),
        intent_objects=("runtime_lane", "git", "hermes_artifact_layer"),
        required_entities=(),
        optional_entities=("lane",),
        read_only=True,
        mutates_state=False,
        requires_founder_approval=False,
        requires_task_ref=False,
        allowed_lanes=("v10-test",),
        forbidden_lanes=("main", "feature/v10.0"),
        safety_gates=("lane", "branch", "git_freshness", "hermes_artifact_layer"),
        handler_name="supervised_v10_repair_preflight",
        fallback_message="I can run the v10 preflight as a read-only runtime verification.",
        report_fields=("lane", "branch", "commit", "git_freshness_status", "hermes_artifact_layer_enabled"),
    ),
    OperationCapability(
        capability_id="level1_delegation_sprint",
        route_name="supervised-v10-level1-delegation-sprint",
        model_used="supervised-v10-level1-delegation-sprint",
        description="Read-only Level 1 supervised v10 delegation planning sprint.",
        natural_language_examples=(
            "start Level 1 delegation",
            "put MAX into supervised delegation mode",
            "recommend 3 safe tasks",
            "start a v10 repair sprint",
            "put OpenClaw to work, but do not create tasks yet",
        ),
        intent_actions=("start_sprint", "recommend"),
        intent_objects=("delegation_sprint", "openclaw_tasks"),
        required_entities=(),
        optional_entities=("task_id", "count"),
        read_only=True,
        mutates_state=False,
        requires_founder_approval=False,
        requires_task_ref=False,
        allowed_lanes=("v10-test",),
        forbidden_lanes=("main", "feature/v10.0"),
        safety_gates=("lane", "branch", "git_freshness", "hermes_artifact_layer", "no_task_creation"),
        handler_name="supervised_v10_level1_delegation_sprint",
        fallback_message="I can run a read-only Level 1 delegation sprint and recommend exactly 3 bounded v10 tasks.",
        report_fields=("lane", "git_freshness_status", "task_id_8_status", "recommended_tasks"),
    ),
    OperationCapability(
        capability_id="supervised_repair_recommend_task",
        route_name="supervised-v10-repair-recommend-task",
        model_used="supervised-v10-repair-recommend-task",
        description="Recommend exactly one bounded v10 OpenClaw repair task from runtime and Hermes context.",
        natural_language_examples=(
            "find something small OpenClaw can fix",
            "recommend one bounded v10 repair",
            "what should OpenClaw work on next?",
            "use Hermes context and recommend one task",
        ),
        intent_actions=("recommend", "search"),
        intent_objects=("openclaw_task", "repair"),
        required_entities=(),
        optional_entities=("module",),
        read_only=True,
        mutates_state=False,
        requires_founder_approval=False,
        requires_task_ref=False,
        allowed_lanes=("v10-test",),
        forbidden_lanes=("main", "feature/v10.0"),
        safety_gates=("lane", "branch", "git_freshness", "hermes_artifact_layer", "no_task_creation"),
        handler_name="supervised_v10_repair_recommend_task",
        fallback_message="I can recommend one bounded v10 repair task without creating it.",
        report_fields=("task_ref", "task_title", "scope", "tests_required", "approval_instruction"),
    ),
    OperationCapability(
        capability_id="supervised_openclaw_task_create",
        route_name="supervised-v10-openclaw-task-create",
        model_used="supervised-v10-openclaw-task-create",
        description="Create exactly one OpenClaw task from an approved one-time task_ref.",
        natural_language_examples=(
            "Approved task_ref=<TOKEN>. Create exactly one bounded OpenClaw task.",
            "create the approved task_ref",
            "proceed with this approved token",
        ),
        intent_actions=("create", "approve"),
        intent_objects=("openclaw_task",),
        required_entities=("task_ref",),
        optional_entities=(),
        read_only=False,
        mutates_state=True,
        requires_founder_approval=True,
        requires_task_ref=True,
        allowed_lanes=("v10-test",),
        forbidden_lanes=("main", "feature/v10.0"),
        safety_gates=("founder_approval", "task_ref", "lane", "branch", "git_freshness", "openclaw_gate"),
        handler_name="supervised_v10_openclaw_task_create",
        fallback_message="Creating an OpenClaw task requires exact task_ref approval.",
        report_fields=("queued", "task_id", "failed_gate", "consumed_task_ref"),
    ),
    OperationCapability(
        capability_id="openclaw_task_inspect",
        route_name="supervised-v10-openclaw-task-inspect",
        model_used="supervised-v10-openclaw-task-inspect",
        description="Read-only inspection of one OpenClaw task.",
        natural_language_examples=(
            "inspect task 8",
            "check OpenClaw task_id=8",
            "what is task 8 doing?",
            "is task 8 a duplicate?",
        ),
        intent_actions=("inspect", "check", "status"),
        intent_objects=("openclaw_task",),
        required_entities=("task_id",),
        optional_entities=(),
        read_only=True,
        mutates_state=False,
        requires_founder_approval=False,
        requires_task_ref=False,
        allowed_lanes=("v10-test",),
        forbidden_lanes=("main", "feature/v10.0"),
        safety_gates=("read_only", "no_task_creation", "no_mutation"),
        handler_name="supervised_v10_openclaw_task_inspect",
        fallback_message="I can inspect one OpenClaw task by task_id without changing it.",
        report_fields=("task_id", "task_title", "status", "duplicate_assessment", "recommendation"),
    ),
    OperationCapability(
        capability_id="openclaw_task_disposition",
        route_name="supervised-v10-openclaw-task-disposition",
        model_used="supervised-v10-openclaw-task-disposition",
        description="Approved disposition for one safe v10 OpenClaw task, such as cancelling a duplicate.",
        natural_language_examples=(
            "Approved. Cancel OpenClaw task_id=8 as duplicate.",
            "Founder approves cancelling task 8.",
            "mark task 8 duplicate/cancelled.",
        ),
        intent_actions=("cancel", "dispose", "mark_duplicate"),
        intent_objects=("openclaw_task",),
        required_entities=("task_id",),
        optional_entities=("duplicate",),
        read_only=False,
        mutates_state=True,
        requires_founder_approval=True,
        requires_task_ref=False,
        allowed_lanes=("v10-test",),
        forbidden_lanes=("main", "feature/v10.0"),
        safety_gates=("founder_approval", "task_id", "lane", "branch", "safe_status", "duplicate_gate"),
        handler_name="supervised_v10_openclaw_task_disposition",
        fallback_message="Task disposition requires explicit founder approval and a single task_id.",
        report_fields=("task_id", "previous_status", "new_status", "failed_gate", "mutated"),
    ),
    OperationCapability(
        capability_id="openclaw_task_list",
        route_name="supervised-v10-openclaw-task-list",
        model_used="supervised-v10-openclaw-task-list",
        description="Read-only OpenClaw queue/recent task listing.",
        natural_language_examples=(
            "show OpenClaw queue",
            "what is OpenClaw working on?",
            "list queued tasks",
            "show recent tasks",
            "show cancelled tasks",
        ),
        intent_actions=("list", "show", "status"),
        intent_objects=("openclaw_queue", "openclaw_tasks"),
        required_entities=(),
        optional_entities=("status_filter",),
        read_only=True,
        mutates_state=False,
        requires_founder_approval=False,
        requires_task_ref=False,
        allowed_lanes=("v10-test",),
        forbidden_lanes=("main", "feature/v10.0"),
        safety_gates=("read_only", "no_task_creation", "no_mutation"),
        handler_name="supervised_v10_openclaw_task_list",
        fallback_message="I can list OpenClaw tasks read-only.",
        report_fields=("status_filter", "tasks", "total"),
    ),
    OperationCapability(
        capability_id="hermes_artifact_search",
        route_name="hermes-artifact-memory",
        model_used="hermes-artifact-memory",
        description="Search approved/current Hermes artifact memory.",
        natural_language_examples=(
            "search Hermes",
            "what approved context applies?",
            "what did we decide?",
            "use approved memory",
            "show current artifacts for this module",
        ),
        intent_actions=("search", "recall"),
        intent_objects=("hermes_artifact", "approved_memory"),
        required_entities=(),
        optional_entities=("module", "approval_status"),
        read_only=True,
        mutates_state=False,
        requires_founder_approval=False,
        requires_task_ref=False,
        allowed_lanes=("v10-test",),
        forbidden_lanes=("main", "feature/v10.0"),
        safety_gates=("approved_current_default", "supporting_memory_only"),
        handler_name="hermes_artifact_memory",
        fallback_message="I can search approved/current Hermes artifact memory as supporting context.",
        report_fields=("artifacts", "grounding", "truth_boundary"),
    ),
    OperationCapability(
        capability_id="module_knowledge_lookup",
        route_name="empire-module-knowledge",
        model_used="empire-module-knowledge",
        description="Explain Empire modules and products without performing operations.",
        natural_language_examples=(
            "what is OpenClaw?",
            "explain Hermes",
            "what does ArchiveForge do?",
        ),
        intent_actions=("explain",),
        intent_objects=("module",),
        required_entities=(),
        optional_entities=("module",),
        read_only=True,
        mutates_state=False,
        requires_founder_approval=False,
        requires_task_ref=False,
        allowed_lanes=("v10-test", "main", "feature/v10.0"),
        forbidden_lanes=(),
        safety_gates=("documentation_only",),
        handler_name="empire_module_knowledge",
        fallback_message="I can answer module explanation questions from module knowledge.",
        report_fields=("module", "sources"),
    ),
)


CAPABILITY_BY_ID = {cap.capability_id: cap for cap in CAPABILITIES}


def _normalized_text(message: str | None) -> str:
    return re.sub(r"\s+", " ", (message or "").lower()).strip()


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def extract_task_id(message: str | None) -> int | None:
    text = message or ""
    for pattern in TASK_ID_PATTERNS:
        match = pattern.search(text)
        if match:
            try:
                return int(match.group(1))
            except Exception:
                return None
    return None


def extract_task_ref(message: str | None) -> str | None:
    match = TASK_REF_PATTERN.search(message or "")
    if not match:
        return None
    return str(match.group(1) or "").strip()


def _extract_status_filter(text: str) -> str | None:
    for status in ("queued", "running", "cancelled", "canceled", "failed", "done", "paused", "recent"):
        if status in text:
            return "cancelled" if status == "canceled" else status
    return None


def _extract_module(text: str) -> str | None:
    aliases = {
        "openclaw": ("openclaw", "open claw"),
        "hermes": ("hermes",),
        "archiveforge": ("archiveforge", "archive forge"),
        "marketforge": ("marketforge", "market forge"),
        "workroom": ("workroom",),
    }
    for module, values in aliases.items():
        if any(value in text for value in values):
            return module
    return None


def _approval_granted(text: str) -> bool:
    return "approved" in text or "i approve" in text or "founder approves" in text or "proceed with" in text


def _is_explanation_only(text: str) -> bool:
    explanation_signal = (
        text.startswith("what is ")
        or text.startswith("what's ")
        or text.startswith("explain ")
        or text.startswith("tell me about ")
        or "what does " in text
    )
    operational_words = (
        "task",
        "queue",
        "queued",
        "running",
        "cancel",
        "inspect",
        "create",
        "recommend",
        "sprint",
        "preflight",
        "status",
        "duplicate",
        "working on",
    )
    return bool(explanation_signal and not any(word in text for word in operational_words))


def parse_operations_intent(message: str | None) -> ParsedOperationIntent:
    text = _normalized_text(message)
    task_id = extract_task_id(message)
    task_ref = extract_task_ref(message)
    status_filter = _extract_status_filter(text)
    module = _extract_module(text)
    approval = _approval_granted(text)
    modifiers = {
        "approval_granted": approval,
        "do_not_create": _contains_any(text, ("do not create", "don't create", "no task creation")),
        "read_only": _contains_any(text, ("read-only", "read only", "inspect", "check", "show", "list")),
        "duplicate": "duplicate" in text,
        "v10_only": "v10" in text,
        "approved_current": "approved/current" in text or "approved current" in text,
        "preflight_only": "preflight" in text or "verify lane" in text,
        "exactly_one": bool(re.search(r"\bexactly\s+(1|one)\b", text)),
        "exactly_three": bool(re.search(r"\bexactly\s+(3|three)\b", text)),
        "cancelled": "cancelled" in text or "canceled" in text,
    }
    entities: dict[str, Any] = {
        "task_id": task_id,
        "task_ref": task_ref,
        "module": module,
        "lane": "v10-test" if "v10" in text else None,
        "branch": "feature/v10.0-test-lane" if "v10" in text else None,
        "approval_phrase": approval,
        "status_filter": status_filter,
    }

    if not text:
        return ParsedOperationIntent(None, None, None, None, entities, modifiers, 0.0)

    if _is_explanation_only(text):
        return ParsedOperationIntent(
            "module_knowledge_lookup",
            CAPABILITY_BY_ID["module_knowledge_lookup"].route_name,
            "explain",
            "module",
            entities,
            modifiers,
            0.92,
        )

    create_intent = (
        ("create" in text or "proceed" in text)
        and not modifiers["do_not_create"]
        and not _contains_any(text, ("do not queue", "don't queue", "no queue"))
    )

    if task_ref and (create_intent or approval):
        return ParsedOperationIntent(
            "supervised_openclaw_task_create",
            CAPABILITY_BY_ID["supervised_openclaw_task_create"].route_name,
            "create",
            "openclaw_task",
            entities,
            modifiers,
            0.98,
        )

    if create_intent and "task" in text and not task_ref:
        return ParsedOperationIntent(
            "supervised_openclaw_task_create",
            CAPABILITY_BY_ID["supervised_openclaw_task_create"].route_name,
            "create",
            "openclaw_task",
            entities,
            modifiers,
            0.8,
            reason="missing_task_ref",
        )

    if (
        "level 1" in text
        or "delegation sprint" in text
        or ("sprint" in text and "v10" in text)
        or (modifiers["exactly_three"] and ("recommend" in text or "task" in text))
    ):
        return ParsedOperationIntent(
            "level1_delegation_sprint",
            CAPABILITY_BY_ID["level1_delegation_sprint"].route_name,
            "start_sprint",
            "delegation_sprint",
            entities,
            modifiers,
            0.93,
        )

    if (
        ("openclaw" in text or "open claw" in text)
        and (
            "queue" in text
            or "working on" in text
            or "list" in text
            or "show" in text
            or "recent" in text
            or status_filter in {"queued", "running", "cancelled", "failed", "done", "paused"}
        )
        and task_id is None
    ):
        return ParsedOperationIntent(
            "openclaw_task_list",
            CAPABILITY_BY_ID["openclaw_task_list"].route_name,
            "list",
            "openclaw_queue",
            entities,
            modifiers,
            0.9,
        )

    if task_id is not None and (
        "cancel" in text
        or "dispose" in text
        or "mark" in text and "duplicate" in text
    ):
        return ParsedOperationIntent(
            "openclaw_task_disposition",
            CAPABILITY_BY_ID["openclaw_task_disposition"].route_name,
            "cancel",
            "openclaw_task",
            entities,
            modifiers,
            0.92,
        )

    if task_id is not None and (
        "inspect" in text
        or "check" in text
        or "status" in text
        or "what is" in text
        or "what's" in text
        or "duplicate" in text
        or "doing" in text
    ):
        return ParsedOperationIntent(
            "openclaw_task_inspect",
            CAPABILITY_BY_ID["openclaw_task_inspect"].route_name,
            "inspect",
            "openclaw_task",
            entities,
            modifiers,
            0.9,
        )

    if task_id is None and (
        ("openclaw" in text or "open claw" in text)
        and "task" in text
        and ("inspect" in text or "check" in text)
    ):
        return ParsedOperationIntent(
            "openclaw_task_inspect",
            CAPABILITY_BY_ID["openclaw_task_inspect"].route_name,
            "inspect",
            "openclaw_task",
            entities,
            modifiers,
            0.76,
            reason="missing_task_id",
        )

    if (
        "recommend" in text
        or "find something small" in text
        or "what should openclaw work on next" in text
        or "what should open claw work on next" in text
        or ("hermes" in text and "task" in text and ("safe" in text or "repair" in text))
    ) and ("task" in text or "repair" in text or "openclaw" in text or "open claw" in text):
        return ParsedOperationIntent(
            "supervised_repair_recommend_task",
            CAPABILITY_BY_ID["supervised_repair_recommend_task"].route_name,
            "recommend",
            "openclaw_task",
            entities,
            modifiers,
            0.88,
        )

    if (
        "preflight" in text
        or "verify the lane" in text
        or "verify lane" in text
        or "check v10 status" in text
        or "safe to create" in text
    ):
        return ParsedOperationIntent(
            "runtime_lane_verify",
            CAPABILITY_BY_ID["runtime_lane_verify"].route_name,
            "verify",
            "runtime_lane",
            entities,
            modifiers,
            0.87,
        )

    if (
        "search hermes" in text
        or "approved context" in text
        or "approved memory" in text
        or "what did we decide" in text
        or "use approved memory" in text
    ):
        return ParsedOperationIntent(
            "hermes_artifact_search",
            CAPABILITY_BY_ID["hermes_artifact_search"].route_name,
            "search",
            "hermes_artifact",
            entities,
            modifiers,
            0.86,
        )

    if ("openclaw" in text or "open claw" in text) and "pause" in text and ("all" in text or "jobs" in text or "tasks" in text):
        return ParsedOperationIntent(
            None,
            None,
            "pause",
            "openclaw_tasks",
            entities,
            modifiers,
            0.82,
            unsupported_intent="openclaw_task_pause_all",
        )

    if ("openclaw" in text or "open claw" in text) and any(word in text for word in ("task", "queue", "job", "status")):
        return ParsedOperationIntent(
            None,
            None,
            "status",
            "openclaw",
            entities,
            modifiers,
            0.55,
            unsupported_intent="openclaw_operation_unknown",
        )

    return ParsedOperationIntent(None, None, None, None, entities, modifiers, 0.0)


def list_operations_capabilities() -> list[dict[str, Any]]:
    return [cap.to_public_dict() for cap in CAPABILITIES]


def get_operations_capability(capability_id: str | None) -> OperationCapability | None:
    if not capability_id:
        return None
    return CAPABILITY_BY_ID.get(capability_id)


def get_operations_capability_registry_status() -> dict[str, Any]:
    enabled_caps = [cap for cap in CAPABILITIES if cap.enabled]
    return {
        "enabled": True,
        "capability_count": len(enabled_caps),
        "read_only_count": sum(1 for cap in enabled_caps if cap.read_only),
        "mutating_count": sum(1 for cap in enabled_caps if cap.mutates_state),
        "task_ref_required_count": sum(1 for cap in enabled_caps if cap.requires_task_ref),
    }


def available_safe_action_labels() -> list[str]:
    return [
        "runtime_lane_verify",
        "level1_delegation_sprint",
        "supervised_repair_recommend_task",
        "openclaw_task_inspect",
        "openclaw_task_list",
        "hermes_artifact_search",
        "module_knowledge_lookup",
    ]
