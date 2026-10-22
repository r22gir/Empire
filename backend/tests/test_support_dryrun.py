"""Isolated Empire support dry-run: Luna, TEST tickets, Pedir ayuda, Rafael notice."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


FORBIDDEN = (
    "/data/amp",
    "/data/maxine",
    "/data/family-help",
    "/home/rg/empire-data",
)


def _app():
    from app.routers.support_health import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


def _local_client():
    return TestClient(_app(), client=("127.0.0.1", 9))


def _remote_client():
    return TestClient(_app(), client=("203.0.113.9", 9))


def _load_support_cli():
    script = Path(__file__).resolve().parents[2] / "scripts" / "support_dryrun.py"
    spec = importlib.util.spec_from_file_location("support_dryrun_cli", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.main


def test_dryrun_all_steps_pass(monkeypatch, tmp_path):
    from app.services.support_dryrun import format_steps_text, run_support_dryrun

    report = run_support_dryrun()
    names = [s.name for s in report.steps]
    assert names == [
        "desk_ready",
        "ticket_create",
        "family_create",
        "pedir_ayuda",
        "desk_route",
        "notify_render",
        "cleanup",
    ]
    assert all(s.ok for s in report.steps), format_steps_text(report)
    assert report.support_working is True
    assert report.yes_no == "yes"
    assert report.sent is False
    assert report.cleaned is True
    assert report.ticket_id and report.ticket_id.startswith("fh-dryrun-")
    text = format_steps_text(report)
    assert "[PASS] desk_ready" in text
    assert "SUPPORT WORKING: YES" in text
    assert "portable_to: workroom, amp, maxine" in text


def test_dryrun_never_sends(monkeypatch):
    sent = []

    async def _boom(*args, **kwargs):
        sent.append(("email", args, kwargs))
        raise AssertionError("send_email must not run during dry-run")

    def _tg_boom(*args, **kwargs):
        sent.append(("telegram", args, kwargs))
        raise AssertionError("telegram must not run during dry-run")

    def _wa_boom(*args, **kwargs):
        sent.append(("whatsapp", args, kwargs))
        raise AssertionError("whatsapp must not run during dry-run")

    monkeypatch.setattr("app.services.email.sender.send_email", _boom, raising=False)
    monkeypatch.setenv("FAMILY_HELP_OWNER_PHONE", "+15555550199")
    monkeypatch.setenv("RAFAEL_PHONE", "+15555550199")
    monkeypatch.setenv("FAMILY_HELP_OWNER_ALERTS", "true")
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "must-not-be-used")

    try:
        import app.services.max.telegram_bot as tg

        monkeypatch.setattr(tg, "telegram_bot", type("T", (), {"is_configured": True, "send_message": _tg_boom})())
    except Exception:
        pass
    try:
        import app.services.max.whatsapp_channel as wa

        monkeypatch.setattr(wa, "notify_founder_whatsapp", _wa_boom, raising=False)
    except Exception:
        pass

    from app.services.support_dryrun import run_support_dryrun

    report = run_support_dryrun()
    assert report.sent is False
    assert sent == []
    assert report.support_working is True
    note = report.notification or {}
    blob = json.dumps(note)
    assert "+15555550199" not in blob
    assert "must-not-be-used" not in blob
    assert "empirebox2026@gmail.com" not in blob
    assert note.get("real_contacts_used") is False
    assert note.get("channels", {}).get("email", {}).get("to") == "founder-inbox (not disclosed)"


def test_dryrun_cleans_isolated_store():
    from app.services.support_dryrun import run_support_dryrun

    report = run_support_dryrun()
    root = report.isolated_root
    assert root
    assert not Path(root).exists()
    assert report.cleaned is True
    for prefix in FORBIDDEN:
        assert not str(report.ticket_id or "").startswith(prefix)


def test_test_ticket_is_marked_and_filtered():
    from app.services.max.brief_filters import is_test_family_ticket
    from app.services.support_dryrun import TEST_MARK, TEST_TICKET_PREFIX, run_support_dryrun

    report = run_support_dryrun()
    assert report.ticket_id.startswith(TEST_TICKET_PREFIX)
    item = {
        "id": report.ticket_id,
        "sender": "TEST requester (not a real contact)",
        "message": next(
            s.extra.get("ticket_id") and (report.notification or {}).get("channels", {}).get("in_app", {}).get("body")
            for s in report.steps
            if s.name == "notify_render"
        ),
        "name": TEST_MARK,
    }
    assert is_test_family_ticket(
        {
            "sender": "TEST requester (not a real contact)",
            "message": TEST_MARK + " Pedir ayuda a Max",
            "name": TEST_MARK,
        }
    )
    assert TEST_MARK in str(item)


def test_family_create_covers_amp_and_maxine():
    from app.services.support_dryrun import run_support_dryrun

    report = run_support_dryrun()
    family = next(s for s in report.steps if s.name == "family_create")
    created = family.extra.get("created") or []
    editions = {row.split(":")[0] for row in created}
    assert editions == {"amp", "maxine"}
    pedir = next(s for s in report.steps if s.name == "pedir_ayuda")
    assert pedir.extra.get("requester_agent") == "Max-e"
    assert pedir.ok


def test_desk_route_failure_is_fail(monkeypatch):
    from app.services.max.desks.base_desk import DeskTask, TaskState
    from app.services.max.desks.support_desk import SupportDesk
    from app.services.support_dryrun import run_support_dryrun

    async def _fail(self, task: DeskTask):
        return await self.fail_task(task, "injected failure")

    monkeypatch.setattr(SupportDesk, "_handle_task", _fail)
    report = run_support_dryrun()
    desk_step = next(s for s in report.steps if s.name == "desk_route")
    assert desk_step.ok is False
    assert report.support_working is False
    assert report.yes_no == "no"
    cleanup = next(s for s in report.steps if s.name == "cleanup")
    assert cleanup.ok is True
    assert TaskState.FAILED.value in desk_step.detail or "did not complete" in desk_step.detail


def test_http_localhost_health_is_yes():
    client = _local_client()
    res = client.get("/api/v1/support/health")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["yes_no"] == "yes"
    assert body["support_working"] is True
    assert body["sent"] is False
    assert body["dry_run"] is True
    statuses = {s["name"]: s["status"] for s in body["steps"]}
    assert statuses["cleanup"] == "PASS"
    assert statuses["desk_ready"] == "PASS"


def test_http_remote_is_403_without_token():
    res = _remote_client().get("/api/v1/support/health")
    assert res.status_code == 403
    assert "localhost" in res.json()["detail"]


def test_http_remote_allowed_with_internal_token(monkeypatch):
    monkeypatch.setenv("SUPPORT_DRYRUN_TOKEN", "dry-run-secret")
    res = _remote_client().get(
        "/api/v1/support/health",
        headers={"X-Empire-Internal-Token": "dry-run-secret"},
    )
    assert res.status_code == 200
    assert res.json()["yes_no"] == "yes"
    denied = _remote_client().get(
        "/api/v1/support/health",
        headers={"X-Empire-Internal-Token": "wrong"},
    )
    assert denied.status_code == 403


def test_http_x_forwarded_for_cannot_spoof_loopback():
    res = _remote_client().get(
        "/api/v1/support/health",
        headers={"X-Forwarded-For": "127.0.0.1"},
    )
    assert res.status_code == 403


def test_http_dry_run_includes_rendered_notice():
    res = _local_client().post("/api/v1/support/dry-run")
    assert res.status_code == 200
    body = res.json()
    note = body["notification"]
    assert note["sent"] is False
    assert note["recipient_name"] == "Rafael"
    assert note["recipient_role"] == "owner"
    assert "[TEST] EMPIRE SUPPORT DRY-RUN" in note["channels"]["in_app"]["title"]


def test_cli_prints_pass_fail(capsys):
    main = _load_support_cli()
    code = main([])
    out = capsys.readouterr().out
    assert code == 0
    assert "[PASS] desk_ready" in out
    assert "[PASS] cleanup" in out
    assert "SUPPORT WORKING: YES" in out


def test_cli_json_and_fail_exit(monkeypatch, capsys):
    from app.services.max.desks.support_desk import SupportDesk

    monkeypatch.setattr(SupportDesk, "agent_name", "not-luna", raising=False)
    main = _load_support_cli()
    code = main(["--json"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 1
    assert payload["yes_no"] == "no"
    assert payload["sent"] is False


def test_access_exempt_lists_support_health():
    from app.edition import access_exempt

    assert access_exempt("GET", "/api/v1/support/health")
    assert access_exempt("POST", "/api/v1/support/dry-run")
    assert not access_exempt("GET", "/api/v1/family-help/inbox")
    assert not access_exempt("POST", "/api/v1/tickets/")


def test_router_is_loaded_from_main():
    src = (Path(__file__).resolve().parents[1] / "app" / "main.py").read_text(encoding="utf-8")
    assert 'load_router("app.routers.support_health", "/api/v1", ["support-health"])' in src


def test_does_not_touch_live_family_help(monkeypatch, tmp_path):
    from app.services.support_dryrun import isolated_support_env, run_support_dryrun

    monkeypatch.setenv("FAMILY_HELP_INBOX_DIR", "/data/family-help")
    monkeypatch.setenv("FAMILY_HELP_DB", "/data/amp/family-help/amp/help.db")
    report = run_support_dryrun()
    assert report.support_working is True
    # After return, original env is restored; dry-run must not have used those paths.
    assert report.isolated_root
    assert not str(report.isolated_root).startswith("/data/")
    with isolated_support_env(tmp_path / "iso") as paths:
        assert str(paths["inbox"]).startswith(str(tmp_path))
        for prefix in FORBIDDEN:
            assert not str(paths["inbox"]).startswith(prefix)
            assert not str(paths["help_db"]).startswith(prefix)
