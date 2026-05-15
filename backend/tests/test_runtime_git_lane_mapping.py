import importlib

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_api_git_returns_lane_aware_metadata(monkeypatch):
    monkeypatch.setenv("EMPIRE_LANE", "v10-test")
    monkeypatch.setenv("EMPIRE_BACKEND_PORT", "8010")
    monkeypatch.setenv("EMPIRE_FRONTEND_EXPECTED_PORT", "3010")

    res = client.get("/api/v1/git")
    assert res.status_code == 200
    payload = res.json()

    assert payload["status"] == "ok"
    assert payload["lane"] == "v10-test"
    assert payload["expected_backend_port"] == 8010
    assert payload["expected_frontend_port"] == 3010
    assert payload["current_commit"]["hash"]
    assert payload["current_commit"]["branch"] == "feature/v10.0-test-lane"
    assert payload["worktree_path"].endswith("/empire-repo-v10")


def test_dev_git_compat_matches_new_git_endpoint(monkeypatch):
    monkeypatch.setenv("EMPIRE_LANE", "v10-test")
    monkeypatch.setenv("EMPIRE_BACKEND_PORT", "8010")
    monkeypatch.setenv("EMPIRE_FRONTEND_EXPECTED_PORT", "3010")

    new_res = client.get("/api/v1/git")
    compat_res = client.get("/api/v1/dev/git")
    assert new_res.status_code == 200
    assert compat_res.status_code == 200

    new_data = new_res.json()
    compat = compat_res.json()
    assert compat["branch"] == new_data["current_commit"]["branch"]
    assert compat["last_commit_hash"] == new_data["current_commit"]["hash"]
    assert compat["lane"] == new_data["lane"]
    assert compat["worktree_path"] == new_data["worktree_path"]


def test_runtime_truth_uses_active_lane_git_endpoint(monkeypatch):
    module = importlib.import_module("app.services.max.runtime_truth_check")
    called_urls: list[str] = []

    monkeypatch.setattr(
        module,
        "get_lane_git_metadata",
        lambda: {
            "lane": "v10-test",
            "expected_backend_port": 8010,
            "expected_frontend_port": 3010,
            "public_base_url": "https://test-studio.empirebox.store",
            "worktree_path": "/home/rg/empire-repo-v10",
            "source_path_used": "git_rev_parse_show_toplevel",
            "expected_worktree_path": "/home/rg/empire-repo-v10",
            "branch": "feature/v10.0-test-lane",
            "commit": "abc1234",
            "message": "abc1234 test commit",
            "mismatch_reason": None,
        },
    )
    monkeypatch.setattr(module, "_git_commit", lambda: {"hash": "abc1234", "branch": "feature/v10.0-test-lane", "message": "abc1234 test commit"})
    monkeypatch.setattr(module, "_service_status", lambda unit: {"active": True, "unit": unit})
    monkeypatch.setattr(module, "_port_open", lambda host, port, timeout=1.0: True)
    monkeypatch.setattr(module, "_http_status", lambda url, timeout=4.0: {"ok": True, "status_code": 200, "bytes": 1})

    def fake_http_json(url: str, timeout: float = 4.0):
        called_urls.append(url)
        if url.endswith("/api/v1/git"):
            return {
                "ok": True,
                "status_code": 200,
                "data": {"current_commit": {"hash": "abc1234", "branch": "feature/v10.0-test-lane"}},
            }
        return {"ok": True, "status_code": 200, "data": {}}

    monkeypatch.setattr(module, "_http_json", fake_http_json)

    result = module.run_runtime_truth_check(public=True)
    assert result["git_freshness"]["freshness_status"] == "ok"
    assert "local_api_commit_mismatch" not in (result.get("stale_or_broken") or [])
    assert "public_api_commit_mismatch" not in (result.get("stale_or_broken") or [])
    assert "http://127.0.0.1:8010/api/v1/git" in called_urls
    assert "https://test-studio.empirebox.store/api/v1/git" in called_urls
    assert "http://127.0.0.1:8000/api/v1/dev/git" not in called_urls
    assert "https://api.empirebox.store/api/v1/dev/git" not in called_urls


def test_runtime_truth_public_unavailable_not_marked_stale(monkeypatch):
    module = importlib.import_module("app.services.max.runtime_truth_check")

    monkeypatch.setattr(
        module,
        "get_lane_git_metadata",
        lambda: {
            "lane": "v10-test",
            "expected_backend_port": 8010,
            "expected_frontend_port": 3010,
            "public_base_url": "https://test-studio.empirebox.store",
            "worktree_path": "/home/rg/empire-repo-v10",
            "source_path_used": "git_rev_parse_show_toplevel",
            "expected_worktree_path": "/home/rg/empire-repo-v10",
            "branch": "feature/v10.0-test-lane",
            "commit": "abc1234",
            "message": "abc1234 test commit",
            "mismatch_reason": None,
        },
    )
    monkeypatch.setattr(module, "_git_commit", lambda: {"hash": "abc1234", "branch": "feature/v10.0-test-lane", "message": "abc1234 test commit"})
    monkeypatch.setattr(module, "_service_status", lambda unit: {"active": True, "unit": unit})
    monkeypatch.setattr(module, "_port_open", lambda host, port, timeout=1.0: True)
    monkeypatch.setattr(module, "_http_status", lambda url, timeout=4.0: {"ok": True, "status_code": 200, "bytes": 1})

    def fake_http_json(url: str, timeout: float = 4.0):
        if url == "http://127.0.0.1:8010/api/v1/git":
            return {
                "ok": True,
                "status_code": 200,
                "data": {"current_commit": {"hash": "abc1234", "branch": "feature/v10.0-test-lane"}},
            }
        if url == "https://test-studio.empirebox.store/api/v1/git":
            return {"ok": False, "error": "timeout"}
        return {"ok": True, "status_code": 200, "data": {}}

    monkeypatch.setattr(module, "_http_json", fake_http_json)

    result = module.run_runtime_truth_check(public=True)
    assert result["git_freshness"]["freshness_status"] == "public_unavailable"
    assert "public_api_commit_mismatch" not in (result.get("stale_or_broken") or [])


def test_max_status_and_api_git_agree_lane_commit_worktree():
    status_res = client.get("/api/v1/max/status")
    git_res = client.get("/api/v1/git")
    assert status_res.status_code == 200
    assert git_res.status_code == 200

    status_data = status_res.json()
    git_data = git_res.json()

    assert status_data["runtime_lane"]["lane"] == git_data["lane"]
    assert status_data["current_commit"]["branch"] == git_data["current_commit"]["branch"]
    assert status_data["current_commit"]["hash"] == git_data["current_commit"]["hash"]
    assert status_data["runtime_lane"]["worktree"] == git_data["worktree_path"]

