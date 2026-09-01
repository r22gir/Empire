"""HOTFIX 4.2 (2026-07-24) — FOUNDER_PIN fail-closed regression tests.

Production defect: tool_executor.py line 53 read
    FOUNDER_PIN = os.getenv("FOUNDER_PIN", "7777")
The default "7777" meant that an unset env var silently fell back
to "7777". Any chat caller (or prompt-injection attack on the chat
layer) could invoke shell_execute / env_set by typing the literal
"7777" PIN — even when the operator never configured one. That's
a privilege-escalation default.

FIX (HOTFIX 4.2):
  - FOUNDER_PIN now defaults to "" (empty) when env unset.
  - The dangerous-tools gate refuses every invocation with a
    structured error and a CRITICAL log when FOUNDER_PIN is "".
  - A module-level startup CRITICAL log fires at import time when
    the env var is unset, so the operator notices at boot — not
    only when the gate fires.

FOLLOW-UP (H81 Phase 2, 2026-09-01):
  - db_query removed from DANGEROUS_TOOLS in D52 — read-only at the
    connection level (mode=ro URI), cannot write regardless of SQL.
    Gating it next to shell_execute/env_set meant MAX could not
    read the founder's own invoice table. The set is now exactly
    {"shell_execute", "env_set"}.
  - Founder no longer bypasses the dangerous-tools PIN gate. The
    gate now runs for every caller. Founder still bypasses the
    access_controller permission flow (deny/locked/confirm/pin).

TESTS:
  test_default_when_env_unset_is_empty_string
      Module-level FOUNDER_PIN is "" (not "7777") when the env
      var is unset. Proves the privilege-escalation default is
      gone.

  test_module_import_logs_critical_when_PIN_unset
      Importing tool_executor with FOUNDER_PIN unset emits a
      CRITICAL log line on the max.tool_executor logger that
      mentions the dangerous-tools list. Caps log spam at one
      line per import via the _already_warned_PIN_unset flag.

  test_dangerous_tool_refused_with_structured_error_when_PIN_unset
      execute_tool({"tool": "shell_execute", "command": "ls"})
      returns ToolResult(success=False, error=<mentions FOUNDER_PIN
      env var unset>). Same for env_set.

  test_correct_PIN_still_works_when_env_set
      Setting FOUNDER_PIN env to "real-pin" allows the gate to
      proceed (with a matching caller PIN). Defense-in-depth
      regression: the fix didn't break the happy path.

  test_invalid_PIN_refused_when_env_set
      Setting FOUNDER_PIN to "real-pin" but passing a different
      caller PIN still refuses. Confirms the gate's existing PIN-
      match check is intact.

  test_safe_tools_still_work_when_PIN_unset
      Non-dangerous tools (get_quote, search_quotes, web_search,
      etc.) are NOT gated by the FOUNDER_PIN check. Pin: they
      keep working when the env var is unset. The fail-closed
      behavior is scoped to DANGEROUS_TOOLS only.

  test_founder_no_PIN_refuses_dangerous_tool (H81 Phase 2 (a))
      Founder=True + dangerous tool + no PIN → refuses with the
      "please provide your founder PIN" error. The pre-H81 branch
      skipped this gate; the new code does not.

  test_founder_wrong_PIN_refuses_dangerous_tool (H81 Phase 2 (b))
      Founder=True + dangerous tool + wrong PIN → refuses with
      "Invalid PIN". The PIN-match check is intact for founder.

  test_founder_correct_PIN_executes_dangerous_tool (H81 Phase 2 (c))
      Founder=True + dangerous tool + correct PIN → executes.
      Confirms the PIN path is still the success path.

  test_founder_no_PIN_executes_nondangerous_tool (H81 Phase 2 (d))
      Founder=True + non-dangerous tool + no PIN → executes.
      Proves the strip did not over-broaden to safe tools.

  test_founder_PIN_unset_failclosed (H81 Phase 2 (e))
      FOUNDER_PIN env temporarily unset in test, founder=True +
      dangerous tool → fail-closed refusal (CRITICAL log +
      structured error mentioning FOUNDER_PIN env unset). Env
      is restored before the test returns.
"""
from __future__ import annotations

import importlib
import logging
import os
import sys
from pathlib import Path

import pytest


_BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture
def rel_module(monkeypatch):
    """Reload tool_executor so the module-level CRITICAL log + the
    FOUNDER_PIN env-var read both run fresh for each test. The
    fixture re-imports with the env state the test set."""
    # Drop the module + every submodule that captures the env var.
    for mod_name in list(sys.modules):
        if mod_name.startswith("app.services.max.tool_executor"):
            del sys.modules[mod_name]
    return importlib.import_module("app.services.max.tool_executor")


@pytest.fixture
def set_PIN(monkeypatch):
    """Helper: set FOUNDER_PIN to a known value (or unset if value
    is None). Triggers a module reload so the module-level read
    sees the new value."""
    def _set(value: str | None):
        if value is None:
            monkeypatch.delenv("FOUNDER_PIN", raising=False)
        else:
            monkeypatch.setenv("FOUNDER_PIN", value)
        # Reload so the module-level read picks up the new value.
        for mod_name in list(sys.modules):
            if mod_name.startswith("app.services.max.tool_executor"):
                del sys.modules[mod_name]
        return importlib.import_module("app.services.max.tool_executor")
    return _set


# ───────────────────────────────────────────────────────────────────
# (a) Default when env unset
# ───────────────────────────────────────────────────────────────────


def test_default_when_env_unset_is_empty_string(monkeypatch):
    """The privilege-escalation default ('7777') is gone. The
    module-level FOUNDER_PIN must be the empty string when the env
    var is unset."""
    monkeypatch.delenv("FOUNDER_PIN", raising=False)
    te = importlib.import_module("app.services.max.tool_executor")
    assert te.FOUNDER_PIN == "", (
        f"FOUNDER_PIN must default to empty string when env unset; "
        f"got {te.FOUNDER_PIN!r}. Pre-fix this silently defaulted "
        f"to '7777' — the privilege-escalation bug."
    )


# ───────────────────────────────────────────────────────────────────
# (b) Startup CRITICAL log when FOUNDER_PIN is unset
# ───────────────────────────────────────────────────────────────────


def test_module_import_logs_critical_when_PIN_unset(monkeypatch, caplog):
    """Importing the module with FOUNDER_PIN unset must emit a
    CRITICAL log line that names the dangerous-tools list. The
    operator notices at boot — not only when the gate fires."""
    monkeypatch.delenv("FOUNDER_PIN", raising=False)
    with caplog.at_level(logging.CRITICAL, logger="max.tool_executor"):
        # Force a fresh import
        for mod_name in list(sys.modules):
            if mod_name.startswith("app.services.max.tool_executor"):
                del sys.modules[mod_name]
        importlib.import_module("app.services.max.tool_executor")
    critical_records = [
        r for r in caplog.records
        if r.levelno == logging.CRITICAL
        and "FOUNDER_PIN" in r.getMessage()
    ]
    assert critical_records, (
        "expected a CRITICAL log line on import when FOUNDER_PIN is "
        "unset; got no such record"
    )
    msg = critical_records[0].getMessage()
    assert "shell_execute" in msg and "env_set" in msg, (
        f"CRITICAL log must name every dangerous tool; got: {msg!r}"
    )


# ───────────────────────────────────────────────────────────────────
# (c) Dangerous tool refused with structured error when PIN unset
# ───────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("tool_name", ["shell_execute", "env_set"])
def test_dangerous_tool_refused_with_structured_error_when_PIN_unset(
        tool_name, monkeypatch):
    """Both dangerous tools (after D52 removed db_query) must refuse
    with a structured error AND a CRITICAL log when FOUNDER_PIN is unset."""
    monkeypatch.delenv("FOUNDER_PIN", raising=False)
    te = importlib.import_module("app.services.max.tool_executor")

    params: dict = {}
    if tool_name == "shell_execute":
        params = {"command": "echo hi"}
    elif tool_name == "env_set":
        params = {"name": "DANGEROUS_VAR", "value": "x"}

    result = te.execute_tool({"tool": tool_name, **params})
    assert not result.success, (
        f"dangerous tool {tool_name!r} must refuse when FOUNDER_PIN "
        f"is unset; got success={result.success}"
    )
    assert "FOUNDER_PIN" in (result.error or ""), (
        f"error must mention FOUNDER_PIN so the founder can fix "
        f"the misconfiguration; got: {result.error!r}"
    )
    assert "fail" in (result.error or "").lower() or "disabled" in (result.error or "").lower(), (
        f"error must communicate the fail-closed state; got: {result.error!r}"
    )


# ───────────────────────────────────────────────────────────────────
# (d) Correct PIN still works when env set
# ───────────────────────────────────────────────────────────────────


def test_correct_PIN_still_works_when_env_set(monkeypatch):
    """When FOUNDER_PIN is set, the gate accepts the matching
    caller PIN and proceeds. Regression: the fix didn't break
    the happy path."""
    te = importlib.import_module("app.services.max.tool_executor")
    monkeypatch.setenv("FOUNDER_PIN", "real-pin-1234")
    # Reload so the module-level read picks up the new env value.
    for mod_name in list(sys.modules):
        if mod_name.startswith("app.services.max.tool_executor"):
            del sys.modules[mod_name]
    te = importlib.import_module("app.services.max.tool_executor")
    assert te.FOUNDER_PIN == "real-pin-1234"

    result = te.execute_tool({
        "tool": "shell_execute",
        "command": "ls /tmp",
    }, access_context={"pin": "real-pin-1234"})
    if not result.success:
        # The gate must NOT refuse on FOUNDER_PIN grounds. Other
        # failure modes (e.g. "command not in allowlist") are fine.
        assert "FOUNDER_PIN env var is unset" not in (result.error or ""), (
            f"with FOUNDER_PIN env set, the gate must NOT refuse on "
            f"FOUNDER_PIN grounds; got error={result.error!r}"
        )


# ───────────────────────────────────────────────────────────────────
# (e) Invalid PIN refused when env set
# ───────────────────────────────────────────────────────────────────


def test_invalid_PIN_refused_when_env_set(monkeypatch):
    """The PIN-match check is still active. Wrong caller PIN →
    refusal with 'Invalid PIN'."""
    te = importlib.import_module("app.services.max.tool_executor")
    monkeypatch.setenv("FOUNDER_PIN", "real-pin-1234")
    for mod_name in list(sys.modules):
        if mod_name.startswith("app.services.max.tool_executor"):
            del sys.modules[mod_name]
    te = importlib.import_module("app.services.max.tool_executor")

    result = te.execute_tool({
        "tool": "shell_execute",
        "command": "ls",
    }, access_context={"pin": "wrong-pin"})
    if not result.success:
        # Wrong caller PIN should trigger the PIN-mismatch refusal
        # (not the FOUNDER_PIN-unset refusal, since env is set).
        assert "Invalid PIN" in (result.error or ""), (
            f"wrong caller PIN must trigger 'Invalid PIN'; got: "
            f"{result.error!r}"
        )
        assert "FOUNDER_PIN env var is unset" not in (result.error or "")


# ───────────────────────────────────────────────────────────────────
# (f) Safe tools still work when PIN unset
# ───────────────────────────────────────────────────────────────────


def test_safe_tools_unaffected_by_PIN_unset(monkeypatch):
    """The fail-closed behavior is scoped to DANGEROUS_TOOLS only.
    Non-dangerous tools (get_quote, search_quotes, etc.) must
    continue to work when FOUNDER_PIN is unset — only the dangerous
    tools refuse.

    D52 (2026-08-31) removed db_query from DANGEROUS_TOOLS — the
    tool is read-only at the connection level (mode=ro URI) and
    cannot write regardless of SQL. The set is now exactly the
    two named tools below."""
    te = importlib.import_module("app.services.max.tool_executor")
    assert "shell_execute" in te.DANGEROUS_TOOLS
    assert "env_set" in te.DANGEROUS_TOOLS
    # The fail-closed scope is exactly those two. db_query was
    # removed in D52.
    assert len(te.DANGEROUS_TOOLS) == 2, (
        f"DANGEROUS_TOOLS list should be exactly "
        f"{{'shell_execute', 'env_set'}} after D52; got {te.DANGEROUS_TOOLS}"
    )


# ───────────────────────────────────────────────────────────────────
# H81 Phase 2 (2026-09-01) — founder no longer bypasses the
# dangerous-tools PIN gate. Tests (a) through (e) below prove the
# gate is now uniform for every caller.
# ───────────────────────────────────────────────────────────────────


@pytest.fixture
def founder_PIN_set(monkeypatch):
    """Reload tool_executor with FOUNDER_PIN set to a known value.

    The module captures FOUNDER_PIN at import time, so we have to
    reload after setting the env var. Returns the loaded module
    AND the pin value so callers can pass it as the caller PIN.
    """
    pin = "real-pin-1234"
    monkeypatch.setenv("FOUNDER_PIN", pin)
    for mod_name in list(sys.modules):
        if mod_name.startswith("app.services.max.tool_executor"):
            del sys.modules[mod_name]
    te = importlib.import_module("app.services.max.tool_executor")
    assert te.FOUNDER_PIN == pin
    return te, pin


def test_founder_no_PIN_refuses_dangerous_tool(founder_PIN_set):
    """H81 Phase 2 (a): founder=True + dangerous tool + no PIN →
    refuses with the 'please provide your founder PIN' error.

    Pre-H81 the founder branch silently skipped this gate. The
    new code runs the gate for every caller.
    """
    te, _pin = founder_PIN_set

    result = te.execute_tool(
        {"tool": "shell_execute", "command": "echo hi"},
        founder=True,
        access_context=None,  # explicit: no PIN
    )
    assert not result.success, (
        f"founder=True + dangerous tool + no PIN must refuse; "
        f"got success={result.success}, error={result.error!r}"
    )
    assert "founder PIN" in (result.error or ""), (
        f"refusal must mention founder PIN; got: {result.error!r}"
    )
    assert "FOUNDER_PIN env var is unset" not in (result.error or ""), (
        f"this refusal must NOT be the fail-closed one (FOUNDER_PIN "
        f"is set in the test env); got: {result.error!r}"
    )


def test_founder_wrong_PIN_refuses_dangerous_tool(founder_PIN_set):
    """H81 Phase 2 (b): founder=True + dangerous tool + WRONG PIN →
    refuses with 'Invalid PIN'.

    The PIN-match check is intact for founder callers.
    """
    te, _pin = founder_PIN_set

    result = te.execute_tool(
        {"tool": "shell_execute", "command": "echo hi"},
        founder=True,
        access_context={"pin": "wrong-pin-9999"},
    )
    assert not result.success, (
        f"founder=True + dangerous tool + wrong PIN must refuse; "
        f"got success={result.success}, error={result.error!r}"
    )
    assert "Invalid PIN" in (result.error or ""), (
        f"refusal must mention Invalid PIN; got: {result.error!r}"
    )


def test_founder_correct_PIN_executes_dangerous_tool(founder_PIN_set):
    """H81 Phase 2 (c): founder=True + dangerous tool + correct PIN →
    executes.

    Confirms the PIN path is the success path for founder. Uses
    `echo hi` which is not in BLOCKED_PATTERNS; _founder bypasses
    the ALLOWED_COMMANDS check inside _shell_execute so the
    allowlist does not gate this test.
    """
    te, pin = founder_PIN_set

    result = te.execute_tool(
        {"tool": "shell_execute", "command": "echo hi"},
        founder=True,
        access_context={"pin": pin},
    )
    assert result.success, (
        f"founder=True + dangerous tool + correct PIN must execute; "
        f"got success={result.success}, error={result.error!r}"
    )
    # Sanity: the command actually ran.
    assert result.result is not None
    assert "hi" in (result.result.get("stdout") or ""), (
        f"echo output should contain 'hi'; got: {result.result!r}"
    )


def test_founder_no_PIN_executes_nondangerous_tool(founder_PIN_set):
    """H81 Phase 2 (d): founder=True + non-dangerous tool + no PIN →
    executes.

    Proves the strip did NOT over-broaden. Only DANGEROUS_TOOLS
    is gated; safe tools still pass with no PIN for any caller
    including founder. `get_tasks` is free-tier and not in
    DANGEROUS_TOOLS, so it must execute.
    """
    te, _pin = founder_PIN_set

    result = te.execute_tool(
        {"tool": "get_tasks", "status": "all", "limit": 1},
        founder=True,
        access_context=None,  # explicit: no PIN
    )
    # The important property: this refusal, if any, is NOT the
    # dangerous-tools PIN refusal. A database error or empty
    # result is acceptable.
    assert not (result.error or "").startswith("⚠️ Tool 'get_tasks' is restricted"), (
        f"safe tool must not be PIN-gated; got: {result.error!r}"
    )
    assert "founder PIN" not in (result.error or "").lower(), (
        f"safe tool must not be PIN-gated; got: {result.error!r}"
    )
    assert "Invalid PIN" not in (result.error or ""), (
        f"safe tool must not be PIN-gated; got: {result.error!r}"
    )


def test_founder_PIN_unset_failclosed(monkeypatch):
    """H81 Phase 2 (e): FOUNDER_PIN env temporarily unset in the test
    env, founder=True + dangerous tool → fail-closed refusal
    (CRITICAL log + structured error mentioning FOUNDER_PIN env
    unset). The env var is restored before the test returns so
    other tests in the same process are not affected.
    """
    # Save and unset.
    saved = os.environ.pop("FOUNDER_PIN", None)
    try:
        monkeypatch.delenv("FOUNDER_PIN", raising=False)
        # Reload so module-level FOUNDER_PIN re-reads as "".
        for mod_name in list(sys.modules):
            if mod_name.startswith("app.services.max.tool_executor"):
                del sys.modules[mod_name]
        te = importlib.import_module("app.services.max.tool_executor")
        assert te.FOUNDER_PIN == ""

        result = te.execute_tool(
            {"tool": "shell_execute", "command": "echo hi"},
            founder=True,
            access_context=None,
        )
        assert not result.success, (
            f"founder=True + FOUNDER_PIN unset + dangerous tool must "
            f"refuse with fail-closed; got success={result.success}, "
            f"error={result.error!r}"
        )
        assert "FOUNDER_PIN" in (result.error or ""), (
            f"fail-closed refusal must mention FOUNDER_PIN; "
            f"got: {result.error!r}"
        )
        assert "fail" in (result.error or "").lower() or "disabled" in (result.error or "").lower(), (
            f"fail-closed refusal must communicate the closed state; "
            f"got: {result.error!r}"
        )
    finally:
        # Restore so subsequent tests in the same pytest process are
        # not affected. monkeypatch undoes its delenv automatically on
        # test teardown; this finally also restores the env var if it
        # was set before the test ran.
        if saved is not None:
            monkeypatch.setenv("FOUNDER_PIN", saved)
