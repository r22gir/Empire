"""Chat PIN card resume, and live Workroom checkout path alias."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from app.services.drawing.canonical_path import (
    CanonicalRootError,
    resolve_canonical_root,
    resolve_path_under_canonical_root,
)
from app.services.max.restricted_tool_resume import (
    needs_founder_pin_card,
    resume_restricted_tool,
    stash_restricted_call,
)
from app.services.max.tool_executor import execute_tool


SECRET = "918273"


def test_historical_empire_repo_main_path_lands_in_live_checkout():
    live = resolve_canonical_root()
    rewritten = resolve_path_under_canonical_root(
        "/home/rg/empire-repo-main/backend/app/routers/voice.py"
    )
    assert rewritten == (live / "backend/app/routers/voice.py").resolve()
    assert rewritten.is_relative_to(live.resolve())


def test_file_read_opens_live_tree_for_historical_absolute_path():
    live = resolve_canonical_root()
    result = execute_tool({
        "tool": "file_read",
        "path": "/home/rg/empire-repo-main/backend/app/routers/voice_documents.py",
        "line_start": 1,
        "line_end": 2,
    })
    assert result.success, result.error
    opened = result.result["path"]
    assert opened.startswith(str(live.resolve()))
    assert "voice_documents.py" in opened


def test_stale_fork_is_still_refused():
    with pytest.raises(CanonicalRootError):
        resolve_path_under_canonical_root("/home/rg/empire-repo/backend/app/routers/voice.py")


def test_missing_pin_asks_for_the_card_not_a_chat_typed_pin(monkeypatch):
    monkeypatch.setattr("app.services.max.tool_executor.FOUNDER_PIN", SECRET)
    result = execute_tool({"tool": "shell_execute", "command": "pwd"})
    assert result.success is False
    assert needs_founder_pin_card(result.error)
    assert "Chat PIN card" in (result.error or "")
    assert "type the PIN into the chat" in (result.error or "")


def test_resume_runs_the_blocked_tool_without_logging_the_pin(monkeypatch, caplog):
    monkeypatch.setenv("FOUNDER_PIN", SECRET)
    monkeypatch.setattr("app.services.max.tool_executor.FOUNDER_PIN", SECRET)
    blocked = execute_tool({"tool": "shell_execute", "command": "echo portal-ok"})
    assert needs_founder_pin_card(blocked.error)
    resume_id = stash_restricted_call(
        tool_call={"tool": "shell_execute", "command": "echo portal-ok", "pin": SECRET},
        desk=None,
        founder=True,
        channel="web",
    )
    with caplog.at_level(logging.DEBUG):
        outcome = resume_restricted_tool(resume_id, SECRET)
    assert outcome.get("status") == "resumed"
    assert outcome.get("success") is True
    blob = json.dumps(outcome) + "\n" + "\n".join(r.getMessage() for r in caplog.records)
    assert SECRET not in blob
    assert "portal-ok" in blob


def test_wrong_pin_does_not_consume_the_pending_call(monkeypatch, caplog):
    monkeypatch.setenv("FOUNDER_PIN", SECRET)
    monkeypatch.setattr("app.services.max.tool_executor.FOUNDER_PIN", SECRET)
    resume_id = stash_restricted_call(
        tool_call={"tool": "shell_execute", "command": "echo portal-ok"},
        desk=None,
        founder=True,
        channel="web",
    )
    with caplog.at_level(logging.DEBUG):
        denied = resume_restricted_tool(resume_id, "000000")
    assert denied["status"] == "invalid_pin"
    assert SECRET not in "\n".join(r.getMessage() for r in caplog.records)
    outcome = resume_restricted_tool(resume_id, SECRET)
    assert outcome.get("success") is True
    assert SECRET not in json.dumps(outcome)


def test_runtime_truth_reports_the_live_checkout_not_empire_repo_main():
    from app.services.drawing.canonical_path import running_code_root
    from app.services.max.runtime_truth_check import _git_commit, live_checkout_sentence
    commit = _git_commit()
    live = str(running_code_root())
    assert live == str(resolve_canonical_root())
    assert commit["repo_root"] == live
    assert commit["branch"] == "feature/drawing-standard"
    sentence = live_checkout_sentence(commit["repo_root"], commit["branch"])
    assert live in sentence
    assert "/home/rg/empire-repo-main" not in sentence
    assert Path(__file__).resolve().is_relative_to(Path(live))
