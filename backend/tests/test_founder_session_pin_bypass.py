"""2026-10-05: verified founder session runs restricted tools without the PIN.

Founder session = Cloudflare Access JWT verified (sig/aud/iss/exp) whose
email is in FOUNDER_EMAILS. Never a client flag. Non-founder sessions,
family editions and calls after untrusted content keep the PIN gate.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.max import founder_session as fs
from app.services.max.restricted_tool_resume import (
    needs_founder_pin_card,
    resume_restricted_tool,
    stash_restricted_call,
)
from app.services.max.tool_executor import execute_tool

SECRET = "918273"
FOUNDER = "founder@example.com"


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setattr("app.services.max.tool_audit.AUDIT_DB", str(tmp_path / "tool_audit.db"), raising=False)
    monkeypatch.setattr("app.services.max.tool_executor.FOUNDER_PIN", SECRET)
    monkeypatch.setenv("FOUNDER_PIN", SECRET)
    monkeypatch.setenv("FOUNDER_ACCESS_EMAILS", f"{FOUNDER},other-founder@example.com")
    monkeypatch.setenv("FOUNDER_EMAILS", "shared-mailbox@example.com")
    monkeypatch.delenv("FOUNDER_EMAIL", raising=False)
    monkeypatch.delenv("EMPIRE_EDITION", raising=False)

    def fake_verify(token):
        if token.startswith("good:"):
            return True, "cloudflare_access", token.split(":", 1)[1]
        return False, "invalid access token (JWTError)", ""

    monkeypatch.setattr("app.services.max.voice_live.verify_access_jwt", fake_verify)


def _req(headers=None, cookies=None):
    return SimpleNamespace(headers={k.lower(): v for k, v in (headers or {}).items()}, cookies=cookies or {})


def test_resolve_requires_verified_jwt_with_founder_email():
    ok = fs.resolve_founder_session(_req({"Cf-Access-Jwt-Assertion": f"good:{FOUNDER}"}))
    assert ok["verified"] is True and ok["email"] == FOUNDER
    cookie = fs.resolve_founder_session(_req(cookies={"CF_Authorization": f"good:{FOUNDER}"}))
    assert cookie["verified"] is True
    assert fs.resolve_founder_session(_req({"Cf-Access-Jwt-Assertion": "good:someone@else.com"}))["verified"] is False
    assert fs.resolve_founder_session(_req({"Cf-Access-Jwt-Assertion": "forged"}))["verified"] is False
    # The plain email header alone is never trusted.
    assert fs.resolve_founder_session(_req({"Cf-Access-Authenticated-User-Email": FOUNDER}))["verified"] is False
    assert fs.resolve_founder_session(None)["verified"] is False
    # Shared mailboxes in FOUNDER_EMAILS are not founder logins.
    assert fs.resolve_founder_session(_req({"Cf-Access-Jwt-Assertion": "good:shared-mailbox@example.com"}))["verified"] is False


def test_family_edition_never_gets_a_founder_session(monkeypatch):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    assert fs.resolve_founder_session(_req({"Cf-Access-Jwt-Assertion": f"good:{FOUNDER}"}))["verified"] is False
    ctx = {"founder_session": True}
    assert fs.founder_session_allows(ctx, True) is False


def test_founder_session_runs_restricted_tool_without_pin():
    session = fs.resolve_founder_session(_req({"Cf-Access-Jwt-Assertion": f"good:{FOUNDER}"}))
    ctx = fs.apply_to_access_context(None, session)
    result = execute_tool({"tool": "shell_execute", "command": "pwd"}, access_context=ctx, founder=True)
    assert "founder PIN" not in (result.error or ""), result.error
    assert "Invalid PIN" not in (result.error or "")


def test_non_founder_session_is_still_gated():
    session = fs.resolve_founder_session(_req({"Cf-Access-Jwt-Assertion": "good:guest@example.com"}))
    ctx = fs.apply_to_access_context(None, session)
    result = execute_tool({"tool": "shell_execute", "command": "pwd"}, access_context=ctx, founder=True)
    assert result.success is False
    assert needs_founder_pin_card(result.error)
    assert "Continue the answer WITHOUT this tool" in result.error


def test_client_supplied_flag_is_not_enough_without_founder():
    # A dict flag with founder=False (non-founder channel) stays gated.
    result = execute_tool({"tool": "env_set", "key": "X", "value": "1"},
                          access_context={"founder_session": True}, founder=False)
    assert result.success is False and needs_founder_pin_card(result.error)


def test_untrusted_content_restores_the_gate():
    session = {"verified": True, "email": FOUNDER}
    ctx = fs.apply_to_access_context({}, session)
    fs.mark_untrusted(ctx, "check_email")
    result = execute_tool({"tool": "shell_execute", "command": "pwd"}, access_context=ctx, founder=True)
    assert result.success is False and needs_founder_pin_card(result.error)


def test_resume_with_founder_session_needs_no_pin():
    rid = stash_restricted_call(tool_call={"tool": "shell_execute", "command": "pwd"},
                                desk=None, founder=True, channel="web")
    out = resume_restricted_tool(rid, "", founder_session={"verified": True, "email": FOUNDER})
    assert out.get("status") == "resumed"
    assert "founder PIN" not in str(out.get("error") or "")


def test_resume_without_session_still_needs_pin():
    rid = stash_restricted_call(tool_call={"tool": "shell_execute", "command": "pwd"},
                                desk=None, founder=True, channel="web")
    assert resume_restricted_tool(rid, "wrong")["status"] == "invalid_pin"
