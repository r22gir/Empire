import importlib

from fastapi.testclient import TestClient

from app.main import app
from app.services.max.hermes_artifact_layer import (
    hermes_artifact_get,
    hermes_artifact_supersede,
    hermes_artifact_write,
)
from app.services.max.tool_executor import ToolResult, execute_tool


client = TestClient(app)


def _fake_runtime_truth_payload() -> dict:
    return {
        "skill": "empire-runtime-truth-check",
        "callable": "empire_runtime_truth_check",
        "mode": "inspect_only",
        "current_commit": {"hash": "rt12345", "message": "rt12345"},
        "backend_status": {"service": {"active": True}, "port_8000_open": True, "local_root": {"status_code": 200}},
        "frontend_status": {"service": {"active": True}, "port_3005_open": True, "local_root": {"status_code": 200}},
        "local_freshness": {"api_git": {"data": {"last_commit_hash": "rt12345"}}, "api_matches_current_commit": True},
        "public_freshness": {"api_git": {"data": {"last_commit_hash": "rt12345"}}, "api_matches_current_commit": True, "api_root": {"status_code": 200}, "studio_root": {"status_code": 200}},
        "restart_required": False,
        "stale_or_broken": [],
        "repair_capability": "inspect_only_no_restart",
    }


def test_hermes_tool_search_and_get_default_to_approved_current(monkeypatch, tmp_path):
    root = tmp_path / "empire-box-memory"
    monkeypatch.setenv("EMPIRE_BOX_MEMORY_DIR", str(root))
    monkeypatch.setenv("EMPIRE_LANE", "v10-test")

    old = hermes_artifact_write(
        title="ArchiveForge packet old",
        artifact_type="markdown_report",
        content="# old packet",
        content_format="markdown",
        module="archiveforge",
        source_agent="hermes",
        approval_status="approved",
    )["artifact_id"]
    replacement = hermes_artifact_write(
        title="ArchiveForge packet latest",
        artifact_type="markdown_report",
        content="# latest packet",
        content_format="markdown",
        module="archiveforge",
        source_agent="hermes",
        approval_status="approved",
    )["artifact_id"]
    draft = hermes_artifact_write(
        title="ArchiveForge packet draft",
        artifact_type="markdown_report",
        content="# draft packet",
        content_format="markdown",
        module="archiveforge",
        source_agent="hermes",
        approval_status="draft",
    )["artifact_id"]
    hermes_artifact_supersede(
        superseded_id=old,
        replacement_id=replacement,
        notes="latest supersedes old",
        actor_type="founder",
        actor_label="founder-qa",
    )

    search_default = execute_tool(
        {"tool": "hermes_artifact_search", "query": "archiveforge packet", "module": "archiveforge"},
        founder=True,
    )
    assert search_default.success is True
    rows = search_default.result["results"]
    ids = {row["id"] for row in rows}
    assert replacement in ids
    assert old not in ids
    assert draft not in ids
    assert all(row["approval_status"] == "approved" for row in rows)

    search_all = execute_tool(
        {
            "tool": "hermes_artifact_search",
            "query": "archiveforge packet",
            "module": "archiveforge",
            "include_non_approved": True,
            "include_superseded": True,
            "current_only": False,
            "limit": 10,
        },
        founder=True,
    )
    assert search_all.success is True
    ids_all = {row["id"] for row in search_all.result["results"]}
    assert replacement in ids_all
    assert old in ids_all
    assert draft in ids_all

    get_latest = execute_tool({"tool": "hermes_artifact_get", "artifact_id": replacement}, founder=True)
    assert get_latest.success is True
    assert get_latest.result["metadata"]["id"] == replacement
    assert get_latest.result["approval_status"] == "approved"


def test_hermes_write_tool_is_gated(monkeypatch, tmp_path):
    root = tmp_path / "empire-box-memory"
    monkeypatch.setenv("EMPIRE_BOX_MEMORY_DIR", str(root))

    blocked_non_founder = execute_tool(
        {
            "tool": "hermes_artifact_write",
            "title": "Packet",
            "artifact_type": "markdown_report",
            "content": "# packet",
            "content_format": "markdown",
        },
        founder=False,
    )
    assert blocked_non_founder.success is False
    assert "founder_required" in (blocked_non_founder.error or "")

    blocked_missing_intent = execute_tool(
        {
            "tool": "hermes_artifact_write",
            "title": "Packet",
            "artifact_type": "markdown_report",
            "content": "# packet",
            "content_format": "markdown",
        },
        founder=True,
    )
    assert blocked_missing_intent.success is False
    assert "explicit founder save intent" in (blocked_missing_intent.error or "")

    allowed = execute_tool(
        {
            "tool": "hermes_artifact_write",
            "title": "Packet approved save",
            "artifact_type": "markdown_report",
            "content": "# packet",
            "content_format": "markdown",
            "explicit_save": True,
            "module": "system",
        },
        founder=True,
    )
    assert allowed.success is True
    assert allowed.result["artifact_id"].startswith("ha_")


def test_hermes_status_update_writes_actor_metadata(monkeypatch, tmp_path):
    root = tmp_path / "empire-box-memory"
    monkeypatch.setenv("EMPIRE_BOX_MEMORY_DIR", str(root))

    artifact_id = hermes_artifact_write(
        title="Actor metadata packet",
        artifact_type="markdown_report",
        content="# review me",
        content_format="markdown",
        module="system",
        source_agent="max",
        approval_status="draft",
    )["artifact_id"]

    updated = execute_tool(
        {
            "tool": "hermes_artifact_update_status",
            "artifact_id": artifact_id,
            "intent": "approve",
            "actor_type": "founder",
            "actor_label": "Founder QA",
            "actor_note": "approved after review",
        },
        founder=True,
    )
    assert updated.success is True
    history = updated.result.get("approval_history") or []
    assert history
    assert history[-1]["actor_type"] == "founder"
    assert history[-1]["actor_label"] == "Founder QA"
    assert history[-1]["note"] == "approved after review"

    bundle = hermes_artifact_get(artifact_id)
    assert bundle is not None
    persisted_history = bundle["metadata"].get("approval_history") or []
    assert persisted_history[-1]["actor_type"] == "founder"


def test_router_artifact_memory_response_uses_hermes_tools(monkeypatch, tmp_path):
    root = tmp_path / "empire-box-memory"
    monkeypatch.setenv("EMPIRE_BOX_MEMORY_DIR", str(root))
    monkeypatch.setenv("EMPIRE_LANE", "v10-test")

    max_router = importlib.import_module("app.routers.max.router")

    artifact_id = hermes_artifact_write(
        title="ArchiveForge decision packet",
        artifact_type="markdown_report",
        content="ArchiveForge publish remains staged and approval-gated.",
        content_format="markdown",
        module="archiveforge",
        source_agent="hermes",
        approval_status="approved",
        provenance={
            "source_agent": "hermes",
            "source_files": ["docs/v10/HERMES_KNOWLEDGE_ARTIFACT_LAYER.md"],
            "source_endpoints": ["/api/v1/hermes/artifacts/search"],
        },
    )["artifact_id"]
    assert artifact_id

    async def fail_ai_router(*args, **kwargs):
        raise AssertionError("Artifact memory query should be handled before generic AI routing")

    monkeypatch.setattr(max_router.ai_router, "chat", fail_ai_router)

    response = client.post(
        "/api/v1/max/chat",
        json={
            "message": "what did we decide about archiveforge design packets?",
            "channel": "web",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["model_used"] == "hermes-artifact-memory"
    assert "Using Hermes artifact memory as supporting context" in data["response"]
    assert "approval_status: approved" in data["response"]
    assert "provenance:" in data["response"]
    assert "Truth basis for live state remains runtime/repo/database checks." in data["response"]
    tools = [row.get("tool") for row in (data.get("tool_results") or [])]
    assert "hermes_artifact_search" in tools
    assert "hermes_artifact_get" in tools


def test_runtime_truth_still_outranks_artifact_memory(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    tool_calls: list[str] = []

    def fake_execute_tool(tool_call, desk=None, access_context=None, founder=False):
        tool_calls.append(tool_call.get("tool"))
        if tool_call == {"tool": "empire_runtime_truth_check", "public": True}:
            return ToolResult(tool="empire_runtime_truth_check", success=True, result=_fake_runtime_truth_payload())
        raise AssertionError(f"Unexpected tool call: {tool_call}")

    monkeypatch.setattr(max_router, "execute_tool", fake_execute_tool)
    monkeypatch.setattr(max_router, "_save_runtime_truth_exchange", lambda *args, **kwargs: "runtime-test")

    response = client.post(
        "/api/v1/max/chat",
        json={
            "message": "what did we decide and is this live?",
            "channel": "web",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["model_used"] == "empire-runtime-truth-check"
    assert "Runtime truth check completed" in data["response"]
    assert "hermes_artifact_search" not in tool_calls
    assert "empire_runtime_truth_check" in tool_calls
