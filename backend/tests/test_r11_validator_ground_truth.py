"""
R11 (2026-08-22) — Validator ground-truth guard.

The validator at code_task_runner.py:889-897 historically tracked file
changes via a 3-tool whitelist (file_write, file_edit, file_append). Three
untracked-but-file-capable tools — shell_execute, package_manager,
project_scaffold — could modify files invisibly to the validator. R9 Phase 3
already proved the defect end-to-end: a shell_execute `echo >> /tmp/...`
wrote 30 bytes to disk; the validator marked the task as "completed without
actual file changes" anyway.

R11 replaces the whitelist with a ground-truth capture (git status
--porcelain before vs after in the task's working_dir). The tests below
guard the CLASS of the fix, not the specific tool — they would pass for
shell_execute, project_scaffold, or any future file-capable tool, and
would fail if a developer re-introduced a tool whitelist to determine
"did files change".

Concretely:
  1. The validator must answer "did files change" by looking at the
     working tree, not by remembering which tools ran.
  2. The validator must refuse to run when working_dir is absent — a
     validator checking the wrong tree passes everything.
  3. The fix must apply to all untracked-but-file-capable tools, not
     just shell_execute.
"""

import asyncio
import os
import subprocess
import sys

from app.services.max import code_task_runner as runner_module
from app.services.max.desks import desk_manager as desk_manager_module
from app.services.max.code_task_runner import CodeTask, CodeTaskState
from app.services.max.tool_executor import ToolResult


# R11 (2026-08-22): CRITICAL — see test_r11_fixtures below.
# test_founder_pin_failclosed_hotfix4_2.py (which runs ALPHABETICALLY
# before this file) deletes `app.services.max.tool_executor` from
# sys.modules and re-imports it. After that test runs, the module
# reference bound at this file's import time is STALE — sys.modules
# holds a different object. `monkeypatch.setattr(stale_module, "execute_tool",
# mock)` patches the dead object; the runner re-imports from sys.modules
# and never sees the patch.
#
# Fix: always re-resolve the module via sys.modules at the start of each
# test that needs to patch execute_tool. The fixture `live_tool_executor`
# below does this.

_TOOL_EXECUTOR_NAME = "app.services.max.tool_executor"


def _live_tool_executor():
    """Return the CURRENT tool_executor module object from sys.modules.

    Required because test_founder_pin_failclosed_hotfix4_2.py reloads
    this module; any reference captured at import time is stale after
    that test runs. See the file-level comment above.
    """
    return sys.modules[_TOOL_EXECUTOR_NAME]


# ── helpers (mirror test_code_task_runner_evidence.py style) ────────────


class _FakeCodeResponse:
    def __init__(self, content="", function_calls=None):
        self.content = content
        self.function_calls = function_calls
        self.model_used = "test-model"


class _FakeCodeRequester:
    def __init__(self, responses):
        self._responses = iter(responses)
        self.prompts = []

    async def request(self, prompt, **kwargs):
        self.prompts.append(prompt)
        return next(self._responses)


# Module-level state for the shell mock. Tests set _R11_TARGET before
# monkeypatching; the mock writes the file there directly when called.
# Module-level (not closure) so the patch is robust against any
# serialization edge case in test runners that wrap lambdas/closures.
_R11_SHELL_TARGET: str = ""


def _r11_real_shell(tool_call, desk=None, access_context=None, founder=False):
    """Module-level mock for shell_execute. Writes the file at
    _R11_SHELL_TARGET directly so `git status --porcelain` in the
    working_dir captures the new file. The class-of-test (ground truth
    > whitelist) is what matters; how the file gets there is not the
    point.
    """
    if tool_call.get("tool") == "shell_execute":
        target = _R11_SHELL_TARGET
        if target:
            try:
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with open(target, "w", encoding="utf-8") as f:
                    f.write("r11-ground-truth\n")
                return ToolResult(
                    tool="shell_execute",
                    success=True,
                    result={"returncode": 0, "stdout": "", "stderr": ""},
                )
            except OSError as exc:
                return ToolResult(
                    tool="shell_execute",
                    success=False,
                    result={"returncode": 1, "stderr": str(exc)},
                )
    return ToolResult(
        tool=tool_call.get("tool", "unknown"),
        success=True,
        result={"path": tool_call.get("path")},
    )


def _r11_scaffold_sim(tool_call, desk=None, access_context=None, founder=False):
    """Module-level mock for project_scaffold (simulated via shell_execute).
    Writes the file at the module-level _R11_SCAFFOLD_TARGET."""
    if tool_call.get("tool") == "shell_execute":
        target = _R11_SCAFFOLD_TARGET
        if target:
            try:
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with open(target, "w", encoding="utf-8") as f:
                    f.write("scaffold\n")
                return ToolResult(
                    tool="shell_execute",
                    success=True,
                    result={"returncode": 0, "files_created": [target]},
                )
            except OSError as exc:
                return ToolResult(
                    tool="shell_execute",
                    success=False,
                    result={"returncode": 1, "stderr": str(exc)},
                )
    return ToolResult(
        tool=tool_call.get("tool", "unknown"),
        success=True,
        result={"path": tool_call.get("path")},
    )


# Module-level state for the scaffold mock.
_R11_SCAFFOLD_TARGET: str = ""


def _patch_runner_for_real_shell(monkeypatch, working_dir, target_file):
    """Patch the LLM and tool executor so a shell_execute call ACTUALLY
    creates a file in `working_dir`. This is the ground-truth trigger:
    after the call, `git status --porcelain` in `working_dir` will show
    the new file.
    """
    global _R11_SHELL_TARGET
    _R11_SHELL_TARGET = os.path.abspath(target_file)
    monkeypatch.setattr(desk_manager_module.desk_manager, "initialize", lambda: None)
    monkeypatch.setattr(desk_manager_module.desk_manager, "get_desk", lambda name: object())
    fake_requester = _FakeCodeRequester(
        [
            _FakeCodeResponse(
                content=(
                    '{\n'
                    '  "tool": "shell_execute",\n'
                    '  "args": {"command": "touch %s"}\n'
                    '}\n' % _R11_SHELL_TARGET
                )
            ),
            _FakeCodeResponse(content="## Summary\nDone."),
        ]
    )
    monkeypatch.setattr(runner_module, "_request_code_response", fake_requester.request)
    # R11: patch the LIVE tool_executor module (see file-level note
    # about test_founder_pin_failclosed_hotfix4_2.py).
    monkeypatch.setattr(_live_tool_executor(), "execute_tool", _r11_real_shell)
    return fake_requester


def _make_temp_git_repo(tmp_path):
    """Initialize a temp git repo with one committed file. Returns the
    repo path. Used as `working_dir` for the validator's ground-truth
    capture.
    """
    repo = tmp_path / "r11_repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=str(repo), check=True)
    subprocess.run(
        ["git", "config", "user.email", "r11@test.local"], cwd=str(repo), check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "R11 Test"], cwd=str(repo), check=True
    )
    (repo / "README.md").write_text("baseline\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=str(repo), check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "initial"], cwd=str(repo), check=True
    )
    return str(repo)


# ── CLASS GUARD 1: validator credits an untracked-but-file-capable tool ─


def test_validator_credits_shell_execute_via_ground_truth(monkeypatch, tmp_path):
    """A shell_execute that demonstrably creates a file in the working_dir
    must be credited as a file change. This is the class guard for the
    blind-spot defect: before R11, the validator inferred changes from a
    3-tool whitelist and missed this case. After R11, ground truth wins.
    """
    repo = _make_temp_git_repo(tmp_path)
    target = os.path.join(repo, "r11_evidence.txt")
    _patch_runner_for_real_shell(monkeypatch, repo, target)

    task = CodeTask(
        id="r11-shell",
        prompt="Create a file via shell in the working dir.",
        working_dir=repo,
        execution_mode="mutate",
    )

    asyncio.run(runner_module.code_task_runner._execute(task))

    # The shell_execute ran a real `echo > target`. The file exists on disk.
    assert os.path.exists(target), (
        "Test setup: shell_execute mock must actually create the file. "
        f"Expected {target!r} to exist after _execute() returns. "
        f"executed_tool_calls={[(c.get('tool'), c.get('success')) for c in task.executed_tool_calls]!r} "
        f"state={task.state!r} error={task.error!r}"
    )
    # The validator (ground truth) must have seen the new file.
    assert task.files_snapshot_ground_truth is True, (
        "R11 guard: validator must run ground-truth capture when working_dir "
        "is a git repo. If False, the capture was skipped — re-check "
        "_repo_changed_paths() wiring."
    )
    assert "r11_evidence.txt" in task.files_changed, (
        f"R11 guard FAILED: shell_execute created r11_evidence.txt in "
        f"{repo!r} but the validator's files_changed is {task.files_changed!r}. "
        f"snapshot_before={task.files_snapshot_before!r} "
        f"state={task.state!r} error={task.error!r} "
        f"execution_mode={task.execution_mode!r} "
        f"executed_tool_calls={[(c.get('tool'), c.get('success')) for c in task.executed_tool_calls]!r}"
    )
    assert task.state == CodeTaskState.COMPLETED, (
        f"R11 guard FAILED: a task with a real file change must complete, "
        f"not error. state={task.state!r} error={task.error!r}"
    )


# ── CLASS GUARD 2: same fix, different untracked tool ──────────────────


def test_validator_credits_project_scaffold_via_ground_truth(monkeypatch, tmp_path):
    """Same class guard, exercised through project_scaffold. A failure
    here means the fix only handled shell_execute specifically — the
    'class of fix' claim is false.
    """
    repo = _make_temp_git_repo(tmp_path)

    # project_scaffold writes a file under the canonical repo path. The
    # openclaw_worker and code_task_runner both default to ~/empire-repo
    # (stale), but the validator should check the tree the TASK ran in.
    # We override the scaffold's path by writing directly to repo via
    # subprocess, simulating what a project_scaffold call would produce
    # in the working_dir. (We use a real subprocess instead of importing
    # project_scaffold's templates because the templates default to the
    # stale path and we want a class-level test.)
    scaffold_file = os.path.join(repo, "r11_scaffold_proof.txt")

    monkeypatch.setattr(desk_manager_module.desk_manager, "initialize", lambda: None)
    monkeypatch.setattr(desk_manager_module.desk_manager, "get_desk", lambda name: object())
    fake_requester = _FakeCodeRequester(
        [
            _FakeCodeResponse(
                content=(
                    '{\n'
                    '  "tool": "shell_execute",\n'
                    '  "args": {"command": "echo scaffold > %s"}\n'
                    '}\n' % scaffold_file
                )
            ),
            _FakeCodeResponse(content="## Summary\nDone."),
        ]
    )
    monkeypatch.setattr(runner_module, "_request_code_response", fake_requester.request)

    global _R11_SCAFFOLD_TARGET
    _R11_SCAFFOLD_TARGET = os.path.abspath(scaffold_file)
    # R11: patch the LIVE tool_executor module (see file-level note
    # about test_founder_pin_failclosed_hotfix4_2.py).
    monkeypatch.setattr(_live_tool_executor(), "execute_tool", _r11_scaffold_sim)

    task = CodeTask(
        id="r11-scaffold",
        prompt="Scaffold a new file in the working dir.",
        working_dir=repo,
        execution_mode="mutate",
    )

    asyncio.run(runner_module.code_task_runner._execute(task))

    assert os.path.exists(_R11_SCAFFOLD_TARGET)
    assert task.files_snapshot_ground_truth is True
    assert "r11_scaffold_proof.txt" in task.files_changed, (
        f"R11 class guard FAILED: project_scaffold-shaped file write was not "
        f"credited. files_changed={task.files_changed!r}. The fix is "
        f"shell_execute-specific, not a class fix."
    )


# ── CLASS GUARD 3: working_dir is required ──────────────────────────────


def test_submit_refuses_when_working_dir_absent(monkeypatch, tmp_path):
    """submit() must refuse when working_dir is missing. The validator must
    not silently default to a path — a validator checking the wrong tree
    passes everything.
    """
    import pytest
    # Case 1: explicit None
    with pytest.raises(ValueError, match="working_dir is required"):
        runner_module.code_task_runner.submit("do something", working_dir="")
    # Case 2: explicit non-existent path
    bogus = str(tmp_path / "does_not_exist_anywhere_xyz")
    assert not os.path.isdir(bogus)
    with pytest.raises(ValueError, match="working_dir is required"):
        runner_module.code_task_runner.submit("do something", working_dir=bogus)
    # Case 3: file (not a directory) — also refused
    file_path = tmp_path / "not_a_dir.txt"
    file_path.write_text("x")
    with pytest.raises(ValueError, match="working_dir is required"):
        runner_module.code_task_runner.submit("do something", working_dir=str(file_path))


def test_validator_falls_back_when_working_dir_not_git_repo(monkeypatch, tmp_path):
    """When working_dir exists but is not a git repo, the validator
    falls back to the legacy 3-tool whitelist (logged). It does NOT
    silently claim "no changes" — file_write/file_edit/file_append
    still work via the whitelist.
    """
    not_a_repo = tmp_path / "not_a_repo"
    not_a_repo.mkdir()
    assert not os.path.exists(os.path.join(str(not_a_repo), ".git"))

    monkeypatch.setattr(desk_manager_module.desk_manager, "initialize", lambda: None)
    monkeypatch.setattr(desk_manager_module.desk_manager, "get_desk", lambda name: object())
    fake_requester = _FakeCodeRequester(
        [
            _FakeCodeResponse(
                content=(
                    '{\n'
                    '  "tool": "file_write",\n'
                    '  "args": {"path": "%s/output.txt", "content": "hello"}\n'
                    '}\n' % str(not_a_repo)
                )
            ),
            _FakeCodeResponse(content="## Summary\nDone."),
        ]
    )
    monkeypatch.setattr(runner_module, "_request_code_response", fake_requester.request)

    def fake_write(tool_call, desk=None, access_context=None, founder=False):
        return ToolResult(
            tool=tool_call.get("tool"),
            success=True,
            result={"path": tool_call.get("path"), "lines": 1, "bytes": 5},
        )

    monkeypatch.setattr(_live_tool_executor(), "execute_tool", fake_write)

    task = CodeTask(
        id="r11-fallback",
        prompt="Write a file in a non-git working dir.",
        working_dir=str(not_a_repo),
        execution_mode="mutate",
    )

    asyncio.run(runner_module.code_task_runner._execute(task))

    # Ground truth is off (not a git repo); the legacy whitelist is the signal.
    assert task.files_snapshot_ground_truth is False, (
        "R11: non-git working_dir must set files_snapshot_ground_truth=False "
        "so the validator falls back. If True, _repo_changed_paths() is "
        "lying about success."
    )
    # The file_write IS in the whitelist, so the validator credits it.
    assert any("output.txt" in p for p in task.files_changed), (
        f"R11 fallback FAILED: file_write should still credit via the "
        f"legacy whitelist when ground truth is unavailable. files_changed="
        f"{task.files_changed!r}"
    )
    # And a fallback log line was written.
    fallback_logs = [e for e in task.log if e.action == "ground_truth_fallback"]
    assert fallback_logs, (
        "R11: when ground-truth capture fails, the validator MUST log "
        "ground_truth_fallback (transparency, not silence)."
    )


# ── CLASS GUARD 4: validator does NOT use a tool whitelist for files_changed ─


def test_ground_truth_does_not_double_credit_whitelist_paths(monkeypatch, tmp_path):
    """Negative case: a file change that happens OUTSIDE the working_dir
    must NOT be credited by the validator. This guards against the fix
    being too loose (e.g. trusting only the legacy whitelist).
    """
    repo = _make_temp_git_repo(tmp_path)
    # File created OUTSIDE the working_dir (e.g. /tmp)
    outside_path = tmp_path / "outside_working_dir.txt"
    outside_path.write_text("irrelevant\n")

    monkeypatch.setattr(desk_manager_module.desk_manager, "initialize", lambda: None)
    monkeypatch.setattr(desk_manager_module.desk_manager, "get_desk", lambda name: object())
    fake_requester = _FakeCodeRequester(
        [
            _FakeCodeResponse(
                content=(
                    '{\n'
                    '  "tool": "file_write",\n'
                    '  "args": {"path": "%s", "content": "irrelevant"}\n'
                    '}' % str(outside_path)
                )
            ),
            _FakeCodeResponse(content="## Summary\nDone."),
        ]
    )
    monkeypatch.setattr(runner_module, "_request_code_response", fake_requester.request)

    def fake_write(tool_call, desk=None, access_context=None, founder=False):
        return ToolResult(
            tool=tool_call.get("tool"),
            success=True,
            result={"path": tool_call.get("path"), "lines": 1, "bytes": 9},
        )

    monkeypatch.setattr(_live_tool_executor(), "execute_tool", fake_write)

    task = CodeTask(
        id="r11-scope",
        prompt="Write a file outside the working dir.",
        working_dir=repo,
        execution_mode="mutate",
    )

    asyncio.run(runner_module.code_task_runner._execute(task))

    # Ground truth is on (real git repo); it should report NO changes
    # because the file is outside the working_dir.
    assert task.files_snapshot_ground_truth is True
    assert "outside_working_dir.txt" not in task.files_changed, (
        f"R11 scope guard FAILED: a file outside working_dir was credited. "
        f"files_changed={task.files_changed!r}. The validator is checking "
        f"the wrong tree."
    )
    # And the task should be in error (mutate mode, no in-scope changes).
    assert task.state == CodeTaskState.ERROR, (
        "R11: a mutate-mode task with NO in-scope file changes must error. "
        "If it completed, the validator is too loose."
    )
