"""Max self-improvement loop: approve enqueues Atlas; MiniMax plans; GitHub issue; never merge/deploy.

Isolated temp DB. MiniMax / GitHub / Cursor are mocked. Nothing is sent outbound.
"""
from __future__ import annotations

import importlib
import json
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class _FakeResp:
    def __init__(self, code, data, text=None):
        self.status_code = code
        self._d = data
        self.text = text if text is not None else str(data)
        self.headers = {"content-type": "application/json"}

    def json(self):
        return self._d


class _FakeClient:
    def __init__(self, handler):
        self.handler = handler

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def post(self, url, json=None, headers=None, **k):
        return self.handler("POST", url, json)

    def get(self, url, headers=None, **k):
        return self.handler("GET", url, None)


@pytest.fixture()
def loop(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))
    monkeypatch.setenv("MAX_IMPROVE_SPEC_DIR", str(tmp_path / "specs"))
    monkeypatch.setenv("MINIMAX_METER_DIR", str(tmp_path / "meter"))
    monkeypatch.setenv("EMPIRE_EDITION", "studio")
    monkeypatch.delenv("CURSOR_API_KEY", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("MAX_IMPROVE_GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    from app.db import database, init_db
    importlib.reload(database)
    importlib.reload(init_db)
    init_db.init_database()
    from app.services.leadforge import growth
    from app.services.max import improvements
    from app.services.max import improvement_queue
    from app.services.max import improvement_planner
    from app.services.max import improvement_github
    from app.services.max import improvement_worker
    from app.routers import growth as growth_router
    for m in (growth, improvements, improvement_queue, improvement_planner, improvement_github, improvement_worker, growth_router):
        importlib.reload(m)
    app = FastAPI()
    app.include_router(growth_router.router, prefix="/api/v1")
    return dict(
        client=TestClient(app),
        imp=improvements,
        queue=improvement_queue,
        planner=improvement_planner,
        worker=improvement_worker,
        github=improvement_github,
        tmp=tmp_path,
    )


def _req(loop, **kw):
    return loop["imp"].create_request(
        kw.get("title", "Bulk approve"),
        kw.get("problem", "Too many taps"),
        kw.get("proposed_change", "Add select-all"),
        kw.get("affected_modules", ["LeadForge"]),
        kw.get("risk", "low"),
        kind=kw.get("kind", "growth"),
    )


def test_approve_only_enqueues(loop):
    c = loop["client"]
    r = _req(loop)
    assert c.post(f"/api/v1/growth/improvements/{r['id']}/approve", json={}).status_code == 403
    a = c.post(f"/api/v1/growth/improvements/{r['id']}/approve", json={"confirm": True}).json()
    assert a["status"] == "approved"
    job = loop["queue"].latest_for(r["id"])
    assert job["status"] == "queued" and job["improvement_id"] == r["id"]
    usage = c.get("/api/v1/growth/improvements/usage").json()
    assert usage["call_cap"] == 40
    assert usage["auto_credits"] is False
    assert usage["pipeline"] == ["proposed", "approved", "planning", "pr_open", "deployed"]
    listed = c.get("/api/v1/growth/improvements").json()
    assert listed["minimax"]["call_cap"] == 40
    assert listed["queue"]["queued"] == 1


def test_atlas_template_plan_without_keys(loop):
    r = _req(loop)
    loop["imp"].approve_build(r["id"], confirm=True)
    out = loop["worker"].process_one()
    assert out["used_llm"] is False
    assert out["merged"] is False and out["deployed"] is False
    got = loop["imp"].get(r["id"])
    assert got["status"] == "awaiting_build"
    spec = Path(got["spec_path"]).read_text()
    assert "Do not merge. Do not deploy." in spec
    assert "max/memory.md" in spec
    assert "client_aliases.json" not in spec or "Never" in spec


def test_atlas_minimax_and_github_issue(loop, monkeypatch):
    monkeypatch.setenv("MINIMAX_API_KEY", "test-minimax-key")
    monkeypatch.setenv("MAX_IMPROVE_ALLOW_TEST_KEY", "1")
    monkeypatch.setenv("MAX_IMPROVE_GITHUB_TOKEN", "gh-test")
    calls = []

    def handler(method, url, body):
        calls.append((method, url, body))
        if url.endswith("/chat/completions"):
            assert body["model"] == "MiniMax-M2"
            assert "Do not merge" in body["messages"][1]["content"]
            return _FakeResp(200, {
                "choices": [{"message": {"content": "## Plan\nShip a draft PR.\n## Proposed patch / spec\nTouch backend/app\n## Files to touch\nimprovements.py\n## Tests\nnightly\n## Rollback\nrevert"}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 30},
            })
        if url.endswith("/issues"):
            assert "max-improvement" in (body or {}).get("labels", [])
            assert "Do not merge" in (body or {}).get("body", "")
            return _FakeResp(201, {"html_url": "https://github.com/r22gir/Empire/issues/42", "number": 42})
        if "/labels" in url:
            return _FakeResp(200, {"name": "max-improvement"})
        return _FakeResp(200, {})

    monkeypatch.setattr(httpx, "Client", lambda **k: _FakeClient(handler))
    r = _req(loop)
    loop["imp"].approve_build(r["id"], confirm=True)
    out = loop["worker"].process_one()
    assert out["issue_url"].endswith("/issues/42")
    got = loop["imp"].get(r["id"])
    assert got["status"] == "pr_open"
    assert got["issue_url"].endswith("/issues/42")
    snap = loop["planner"].usage_snapshot()
    assert snap["calls"] == 1
    assert snap["tokens"] >= 42
    assert snap["auto_credits"] is False
    assert not any("merge" in (u or "") and "PUT" in m for m, u, _ in calls)


def test_daily_cap_stops_and_does_not_call_minimax(loop, monkeypatch):
    monkeypatch.setenv("MINIMAX_API_KEY", "test-minimax-key")
    monkeypatch.setenv("MAX_IMPROVE_ALLOW_TEST_KEY", "1")
    monkeypatch.setenv("MAX_IMPROVE_MINIMAX_DAILY_CALLS", "1")
    loop["planner"]._record_usage(calls=1, tokens=10)
    r = _req(loop)
    loop["imp"].approve_build(r["id"], confirm=True)
    called = []

    def boom(*a, **k):
        called.append(1)
        raise AssertionError("MiniMax must not be called at cap")

    monkeypatch.setattr(loop["planner"], "call_minimax", boom)
    out = loop["worker"].process_one()
    assert out.get("status") == "failed" or out.get("error")
    assert called == []
    got = loop["imp"].get(r["id"])
    assert got["status"] == "build_failed"
    assert "cap" in (got.get("build_note") or "").lower()
    retry = loop["client"].post(f"/api/v1/growth/improvements/{r['id']}/retry", json={"confirm": True})
    assert retry.status_code == 200
    assert retry.json()["status"] == "approved"


def test_family_edition_does_not_run_planner(loop, monkeypatch):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("MINIMAX_API_KEY", "test-minimax-key")
    monkeypatch.setenv("MAX_IMPROVE_ALLOW_TEST_KEY", "1")
    from app import edition
    importlib.reload(edition)
    importlib.reload(loop["planner"])
    with pytest.raises(loop["planner"].BudgetExceeded):
        loop["planner"].call_minimax("s", "u")


def test_nightly_files_fix_improvements_without_outbound(loop, monkeypatch, tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "nightly_improvement_tests",
        Path(__file__).resolve().parents[1] / "scripts" / "nightly_improvement_tests.py",
    )
    nightly = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(nightly)
    monkeypatch.setattr(nightly, "LOG_DIR", tmp_path)
    monkeypatch.setattr(
        nightly,
        "_run",
        lambda cmd, cwd, env, timeout: {
            "cmd": cmd,
            "returncode": 1,
            "ok": False,
            "output": "FAILED tests/test_growth.py::test_roi_report_by_channel_with_manual_spend\n",
        } if "pytest" in cmd else {
            "cmd": cmd,
            "returncode": 0,
            "ok": True,
            "output": "ok 1 pipeline",
        },
    )
    res = nightly.run_nightly(dry_run=False)
    assert res["outbound"] is False
    assert res["filed"]
    assert res["filed"][0]["title"].startswith("Nightly fix:")
    items = loop["imp"].list_requests()["items"]
    assert any(i["kind"] == "fix" and i["status"] == "proposed" for i in items)
    # dry-run does not file more
    n = len(items)
    nightly.run_nightly(dry_run=True)
    assert len(loop["imp"].list_requests()["items"]) == n
