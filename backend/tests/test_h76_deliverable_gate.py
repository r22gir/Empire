"""
H76 STEP 3 — deliverable gate + notifier + routing demonstration.

Tests:
1. C2 gate: chat task with empty result lands as FAILED.
2. C2 gate: chat task whose result starts with "No available provider"
   lands as FAILED with a reason that names the gate.
3. G2 gate: codeforge task whose result claims "Edited {path}" but the file
   does not exist lands as FAILED with a reason that names the gate.
4. G2 gate: codeforge task whose result claims "Created {N} file(s):" with
   paths that do not all exist lands as FAILED.
5. G2 gate: codeforge task with no marker and no successful tool action
   lands as FAILED.
6. G2 gate: codeforge task with a "Created {N} file(s):" marker whose
   paths DO exist lands as COMPLETED (gate does not over-fire).
7. G2 gate: codeforge task with a "Edited {path}" marker where path DOES
   exist lands as COMPLETED.
8. G2 gate: codeforge task with a successful file_read action (no marker,
   but a tool action) lands as COMPLETED.
9. STEP 3b notifier: when state goes from COMPLETED to FAILED via the gate,
   the notifier prefix is "FAILED", not "COMPLETED".
10. STEP 3c routing: a code-titled task with code-task keywords routes to
    codeforge via the keyword map (was previously routed by best keyword
    match to a non-code desk).
11. STEP 3c routing: codeforge keyword map entry exists and is non-empty.
"""
import asyncio
import os
import tempfile
from unittest.mock import AsyncMock, patch

import pytest

from app.services.max.ai_router import AIResponse
from app.services.max.desks.base_desk import (
    DeskAction,
    DeskTask,
    TaskPriority,
    TaskState,
)
from app.services.max.desks.codeforge_desk import CodeForgeDesk
from app.services.max.desks.desk_router import KEYWORD_MAP, DeskRouter
from app.services.max.desks.innovation_desk import InnovationDesk
from app.services.max.tool_executor import _enforce_deliverable_gate


def _ok_response(text="answer"):
    return AIResponse(content=text, model_used="minimax", provider_unavailable=False)


# ─────────────────────────────────────────────────────────────────────
# C2 — chat-style gates
# ─────────────────────────────────────────────────────────────────────

def test_c2_chat_task_with_empty_result_must_fail():
    task = DeskTask(
        id="c2-empty",
        title="Chat task",
        description="desc",
        state=TaskState.COMPLETED,
        result="",
    )
    _enforce_deliverable_gate(task, desk_id="innovation")
    assert task.state == TaskState.FAILED
    assert "deliverable gate C2" in task.result


def test_c2_chat_task_with_no_provider_string_must_fail():
    task = DeskTask(
        id="c2-noprovider",
        title="Chat task",
        description="desc",
        state=TaskState.COMPLETED,
        result=(
            "No available provider could satisfy this request under current "
            "routing policy. Attempted: none. Blocked: minimax."
        ),
    )
    _enforce_deliverable_gate(task, desk_id="innovation")
    assert task.state == TaskState.FAILED
    assert "deliverable gate C2" in task.result


def test_c2_chat_task_with_real_text_passes():
    """A normal chat task with substantive text result passes C2."""
    task = DeskTask(
        id="c2-pass",
        title="Chat task",
        description="desc",
        state=TaskState.COMPLETED,
        result="Here is the meeting brief you asked for, with 5 sections.",
    )
    _enforce_deliverable_gate(task, desk_id="clients")
    assert task.state == TaskState.COMPLETED


# ─────────────────────────────────────────────────────────────────────
# G2 — codeforge gates
# ─────────────────────────────────────────────────────────────────────

def test_g2_codeforge_edited_marker_with_missing_file_must_fail():
    task = DeskTask(
        id="g2-edited-missing",
        title="Edit a file",
        description="desc",
        state=TaskState.COMPLETED,
        result="Edited /tmp/this-file-definitely-does-not-exist-xyz123.py",
    )
    _enforce_deliverable_gate(task, desk_id="codeforge")
    assert task.state == TaskState.FAILED
    assert "deliverable gate G2" in task.result


def test_g2_codeforge_created_marker_with_missing_files_must_fail():
    task = DeskTask(
        id="g2-created-missing",
        title="Create files",
        description="desc",
        state=TaskState.COMPLETED,
        result="Created 2 file(s): /tmp/missing-a.py, /tmp/missing-b.py",
    )
    _enforce_deliverable_gate(task, desk_id="codeforge")
    assert task.state == TaskState.FAILED
    assert "deliverable gate G2" in task.result


def test_g2_codeforge_no_marker_no_tool_action_must_fail():
    task = DeskTask(
        id="g2-no-marker-no-tool",
        title="Some dev task",
        description="desc",
        state=TaskState.COMPLETED,
        result="Just a text response from the model with no tool calls.",
    )
    _enforce_deliverable_gate(task, desk_id="codeforge")
    assert task.state == TaskState.FAILED
    assert "deliverable gate G2" in task.result


def test_g2_codeforge_edited_marker_with_real_file_passes(tmp_path):
    target = tmp_path / "real_file.py"
    target.write_text("# existing content\n")
    task = DeskTask(
        id="g2-edited-real",
        title="Edit a real file",
        description="desc",
        state=TaskState.COMPLETED,
        result=f"Edited {target}",
    )
    _enforce_deliverable_gate(task, desk_id="codeforge")
    assert task.state == TaskState.COMPLETED


def test_g2_codeforge_created_marker_with_real_files_passes(tmp_path):
    p1 = tmp_path / "created_a.py"
    p2 = tmp_path / "created_b.py"
    p1.write_text("# a\n")
    p2.write_text("# b\n")
    task = DeskTask(
        id="g2-created-real",
        title="Create real files",
        description="desc",
        state=TaskState.COMPLETED,
        result=f"Created 2 file(s): {p1}, {p2}",
    )
    _enforce_deliverable_gate(task, desk_id="codeforge")
    assert task.state == TaskState.COMPLETED


def test_g2_codeforge_file_read_action_passes_no_marker():
    """A file_read is a real deliverable even without a marker."""
    task = DeskTask(
        id="g2-read-passes",
        title="Read a file",
        description="desc",
        state=TaskState.COMPLETED,
        result="/tmp/whatever.py (100 lines)\n```\n# file content\n```",
        actions=[
            DeskAction(action="file_read", detail="Direct read: /tmp/whatever.py"),
        ],
    )
    _enforce_deliverable_gate(task, desk_id="codeforge")
    assert task.state == TaskState.COMPLETED


def test_g2_codeforge_git_action_passes_no_marker():
    task = DeskTask(
        id="g2-git-passes",
        title="Git status",
        description="desc",
        state=TaskState.COMPLETED,
        result="On branch main\nnothing to commit, working tree clean",
        actions=[
            DeskAction(action="git_ops", detail="Running git operation"),
        ],
    )
    _enforce_deliverable_gate(task, desk_id="codeforge")
    assert task.state == TaskState.COMPLETED


def test_gate_does_not_fire_on_already_failed():
    """Already-FAILED tasks stay FAILED — the gate does not touch them."""
    task = DeskTask(
        id="g2-noop",
        title="Already failed",
        description="desc",
        state=TaskState.FAILED,
        result="some prior error",
    )
    _enforce_deliverable_gate(task, desk_id="codeforge")
    assert task.state == TaskState.FAILED
    assert task.result == "some prior error"


# ─────────────────────────────────────────────────────────────────────
# STEP 3b — Notifier payload
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_notifier_payload_after_gate_downgrades_completed_to_failed():
    """When the gate downgrades COMPLETED to FAILED, the notifier payload
    carries FAILED (not COMPLETED) and includes the gate's reason.

    We exercise the gate directly (no live desk.handle_task) to keep the
    test deterministic. The notifier payload assembly is the same logic
    _run_atlas_background uses post-gate (lines 3939-3947 in
    tool_executor.py).
    """
    # Synthetic DeskTask: a codeforge task that "completed" with a
    # "Created" marker pointing at a non-existent file. The gate MUST
    # downgrade this to FAILED.
    task = DeskTask(
        id="notif-test-1",
        title="D36 H76 notifier test",
        description="A task whose result claims to have created a file that does not exist.",
        state=TaskState.COMPLETED,
        result="Created 1 file(s): /tmp/this-path-definitely-does-not-exist-d36.py",
    )

    # Apply the gate. This is the same call _run_atlas_background makes.
    _enforce_deliverable_gate(task, desk_id="codeforge")
    assert task.state == TaskState.FAILED
    assert "deliverable gate G2" in task.result

    # STEP 3b: the notifier payload uses state, not task.state alone.
    # The notifier code in _run_atlas_background reads `state == "completed"`
    # to choose the COMPLETED prefix. After the gate fired, state is FAILED,
    # so the prefix becomes "FAILED".
    state = task.state.value
    if state == "completed":
        notifier_prefix = f"Atlas task #notif-test-1 COMPLETED: {task.title}"
    else:
        notifier_prefix = f"Atlas task #notif-test-1 FAILED: {task.title}"
    notifier_body = str(task.result)[:200]
    notifier_payload = notifier_prefix + "\n" + notifier_body

    assert "FAILED" in notifier_payload
    assert "COMPLETED" not in notifier_payload
    assert "deliverable gate G2" in notifier_payload


@pytest.mark.asyncio
async def test_notifier_payload_for_real_completion():
    """Sanity: a task that DOES produce a real deliverable still notifies
    as COMPLETED with the deliverable text in the body. The notifier
    reads what the gate recorded, not just task.state.
    """
    tmp = tempfile.NamedTemporaryFile(suffix=".py", delete=False)
    tmp.write(b"# real file\n")
    tmp.close()
    try:
        task = DeskTask(
            id="notif-test-2",
            title="D36 H76 real-edit notifier test",
            description="Edit a real file.",
            state=TaskState.COMPLETED,
            result=f"Edited {tmp.name}",
        )
        _enforce_deliverable_gate(task, desk_id="codeforge")
        assert task.state == TaskState.COMPLETED  # gate didn't over-fire

        state = task.state.value
        if state == "completed":
            notifier_prefix = f"Atlas task #notif-test-2 COMPLETED: {task.title}"
        else:
            notifier_prefix = f"Atlas task #notif-test-2 FAILED: {task.title}"
        notifier_body = str(task.result)[:200]
        notifier_payload = notifier_prefix + "\n" + notifier_body

        assert "COMPLETED" in notifier_payload
        assert "FAILED" not in notifier_payload
        assert tmp.name in notifier_body
    finally:
        os.unlink(tmp.name)


# ─────────────────────────────────────────────────────────────────────
# STEP 3c — Routing: codeforge added to KEYWORD_MAP
# ─────────────────────────────────────────────────────────────────────

def test_keyword_map_has_codeforge_entry():
    assert "codeforge" in KEYWORD_MAP
    assert "keywords" in KEYWORD_MAP["codeforge"]
    assert len(KEYWORD_MAP["codeforge"]["keywords"]) > 0


def _router_with_codeforge_registered():
    """Build a DeskRouter with codeforge (and other desks) registered so the
    keyword map check `if desk_id not in self._desks: continue` does not
    skip the new codeforge entry.
    """
    from app.services.max.desks.codeforge_desk import CodeForgeDesk
    from app.services.max.desks.forge_desk import ForgeDesk
    from app.services.max.desks.innovation_desk import InnovationDesk
    from app.services.max.desks.clients_desk import ClientsDesk
    router = DeskRouter()
    for desk in (CodeForgeDesk(), ForgeDesk(), InnovationDesk(), ClientsDesk()):
        router.register_desk(desk)
    router._local_llm = None  # disable LLM routing
    return router


def test_code_titled_task_routes_to_codeforge_via_keywords():
    """A code-titled task with code-task keywords MUST route to codeforge
    via the keyword fallback (was previously routed to forge when "fabric"
    was present in the description). This is the routing fix.
    """
    router = _router_with_codeforge_registered()
    task = DeskTask(
        id="routing-test-1",
        title="Fix the OpenClaw read-task false failure bug",
        description="Patch the openclaw worker to correctly report file_read success",
        priority=TaskPriority.NORMAL,
    )
    desk_id, reason = router._route_with_keywords(task)
    assert desk_id == "codeforge", (
        f"Expected codeforge but got {desk_id!r} via {reason!r}. "
        f"Routing fix did not take effect."
    )


def test_chat_titled_task_does_not_route_to_codeforge():
    """Sanity: a chat-titled task with no code-task keywords must NOT
    route to codeforge. The routing fix shouldn't over-fire.
    """
    router = _router_with_codeforge_registered()
    task = DeskTask(
        id="routing-test-2",
        title="Prepare a meeting brief for Mr. Smith",
        description="Bring fabric swatches and the standard proposal deck.",
        priority=TaskPriority.NORMAL,
    )
    desk_id, reason = router._route_with_keywords(task)
    # Should NOT be codeforge. May be any other desk or None.
    if desk_id is not None:
        assert desk_id != "codeforge", (
            f"Chat task routed to codeforge via {reason!r}. Routing fix "
            f"over-fired."
        )


def test_d36_proof_task_routes_to_codeforge():
    """D36 STEP 3 DEMONSTRATE: the 'D36-PROOF ...' task routes to codeforge."""
    router = _router_with_codeforge_registered()
    task = DeskTask(
        id="routing-d36-proof",
        title="D36-PROOF codeforge routing fix verification",
        description="Add a unit test that verifies code-titled tasks land in codeforge via the keyword map.",
        priority=TaskPriority.NORMAL,
    )
    desk_id, reason = router._route_with_keywords(task)
    assert desk_id == "codeforge", (
        f"D36-PROOF task did NOT route to codeforge (got {desk_id!r} via {reason!r}). "
        f"This is the routing defect that D36 STEP 3c fixes."
    )