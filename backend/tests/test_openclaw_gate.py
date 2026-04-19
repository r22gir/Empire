import httpx

from app.services.max import openclaw_gate
from app.services.max.openclaw_gate import check_openclaw_gate, clear_openclaw_gate_cache
from app.services.max.tool_executor import execute_tool


class _Resp:
    def __init__(self, status_code=200, text="ok"):
        self.status_code = status_code
        self.text = text


def setup_function():
    clear_openclaw_gate_cache()


def test_openclaw_gate_healthy_and_cached(monkeypatch):
    calls = {"count": 0}

    def fake_get(*args, **kwargs):
        calls["count"] += 1
        return _Resp(200)

    monkeypatch.setattr(openclaw_gate.httpx, "get", fake_get)
    monkeypatch.setattr(openclaw_gate, "_queue_snapshot", lambda: (True, {"queued": 1, "total": 1}, {"total": 1}))

    first = check_openclaw_gate(force=True)
    second = check_openclaw_gate()

    assert first.state == "healthy"
    assert first.allowed is True
    assert "OpenClaw healthy" in first.founder_message
    assert second.state == "healthy"
    assert calls["count"] == 1


def test_openclaw_gate_degraded_on_503(monkeypatch):
    monkeypatch.setattr(openclaw_gate.httpx, "get", lambda *args, **kwargs: _Resp(503, "down"))
    monkeypatch.setattr(openclaw_gate, "_queue_snapshot", lambda: (True, {"total": 0}, {"total": 0}))

    result = check_openclaw_gate(force=True)

    assert result.state == "degraded"
    assert result.allowed is False
    assert "delegation blocked" in result.founder_message


def test_openclaw_gate_unknown_on_timeout(monkeypatch):
    def timeout(*args, **kwargs):
        raise httpx.TimeoutException("boom")

    monkeypatch.setattr(openclaw_gate.httpx, "get", timeout)
    monkeypatch.setattr(openclaw_gate, "_queue_snapshot", lambda: (True, {"total": 0}, {"total": 0}))

    result = check_openclaw_gate(force=True)

    assert result.state == "unknown"
    assert result.allowed is False
    assert "inspect-only mode" in result.founder_message


def test_openclaw_gate_unavailable_on_connect_error(monkeypatch):
    def connect_error(*args, **kwargs):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(openclaw_gate.httpx, "get", connect_error)
    monkeypatch.setattr(openclaw_gate, "_queue_snapshot", lambda: (True, {"total": 0}, {"total": 0}))

    result = check_openclaw_gate(force=True)

    assert result.state == "unavailable"
    assert result.allowed is False
    assert "task queued locally" in result.founder_message


def test_dispatch_tool_does_not_silently_delegate_when_gate_fails(monkeypatch):
    def fake_gate():
        return openclaw_gate.OpenClawGateResult(
            state="degraded",
            allowed=False,
            reason="health endpoint returned 503",
            checked_at="2026-04-19T00:00:00+00:00",
            cache_ttl_seconds=20,
            cache_age_seconds=0,
            health_endpoint="http://localhost:7878/health",
            founder_message="OpenClaw degraded (health endpoint returned 503) - delegation blocked. Will retry when healthy.",
        )

    monkeypatch.setattr("app.services.max.openclaw_gate.check_openclaw_gate", fake_gate)

    result = execute_tool({
        "tool": "dispatch_to_openclaw",
        "title": "Proof task",
        "description": "Should not post when gate is degraded",
    }, founder=True)

    assert result.success is False
    assert "delegation blocked" in result.error
    assert result.result["openclaw_gate"]["state"] == "degraded"
