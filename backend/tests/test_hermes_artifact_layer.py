import asyncio
import importlib
from pathlib import Path

from fastapi import BackgroundTasks, Response

from app.services.max.ai_router import AIResponse
from app.services.max.hermes_artifact_layer import (
    TRUTH_HIERARCHY,
    ensure_hermes_artifact_scaffold,
    get_hermes_artifact_layer_status,
    hermes_artifact_export,
    hermes_artifact_get,
    hermes_artifact_search,
    hermes_artifact_supersede,
    hermes_artifact_update_status,
    hermes_artifact_write,
)


def test_artifact_scaffold_and_status(monkeypatch, tmp_path):
    root = tmp_path / "empire-box-memory"
    monkeypatch.setenv("EMPIRE_BOX_MEMORY_DIR", str(root))
    monkeypatch.setenv("EMPIRE_LANE", "v10-test")

    scaffold = ensure_hermes_artifact_scaffold()
    status = get_hermes_artifact_layer_status()

    artifacts_root = root / "ARTIFACTS"
    assert artifacts_root.exists()
    assert (artifacts_root / "index.jsonl").exists()
    assert (artifacts_root / "max").exists()
    assert (artifacts_root / "hermes").exists()
    assert (artifacts_root / "openclaw").exists()
    assert (artifacts_root / "modules" / "archiveforge").exists()
    assert status["enabled"] is True
    assert status["lane"] == "v10-test"
    assert status["truth_hierarchy"][0] == "runtime"
    assert scaffold["root"] == str(artifacts_root)


def test_write_sanitizes_html_and_generates_extracted_text(monkeypatch, tmp_path):
    root = tmp_path / "empire-box-memory"
    monkeypatch.setenv("EMPIRE_BOX_MEMORY_DIR", str(root))
    monkeypatch.setenv("EMPIRE_LANE", "v10-test")

    payload = hermes_artifact_write(
        title="Risky HTML Artifact",
        artifact_type="html_artifact",
        content=(
            "<html><head><link rel='stylesheet' href='https://evil.css'>"
            "<script>alert('x')</script></head>"
            "<body><h1 onclick=\"doBad()\">Hello</h1>"
            "<a href=\"https://evil.example\">bad link</a>"
            "<img src=\"https://evil.example/1.png\" />"
            "<form action=\"https://evil.example/post\"><input name='x'></form>"
            "<iframe src=\"https://evil.example/frame\"></iframe>"
            "<p>Safe body text.</p></body></html>"
        ),
        content_format="html",
        module="ArchiveForge",
        source_agent="max",
        tags=["review", "html"],
    )

    artifact_id = payload["artifact_id"]
    result = hermes_artifact_get(artifact_id)
    assert result is not None
    metadata = result["metadata"]
    html_path = Path(metadata["paths"]["artifact_html"])
    text_path = Path(metadata["paths"]["extracted_text"])
    summary_path = Path(metadata["paths"]["summary_text"])

    cleaned = html_path.read_text(encoding="utf-8").lower()
    extracted = text_path.read_text(encoding="utf-8")
    summary = summary_path.read_text(encoding="utf-8")

    assert "<script" not in cleaned
    assert "<iframe" not in cleaned
    assert "<form" not in cleaned
    assert "<link" not in cleaned
    assert "https://evil.example" not in cleaned
    assert "onclick=" not in cleaned
    assert "Hello" in extracted
    assert "Safe body text" in extracted
    assert summary
    assert metadata["module"] == "archiveforge"
    assert metadata["approval_status"] == "draft"
    assert metadata["lane"] == "v10-test"
    assert metadata["safety_status"] == "sanitized_no_scripts_no_external_network"


def test_search_update_export_and_supersede(monkeypatch, tmp_path):
    root = tmp_path / "empire-box-memory"
    monkeypatch.setenv("EMPIRE_BOX_MEMORY_DIR", str(root))
    monkeypatch.setenv("EMPIRE_LANE", "v10-test")

    old_artifact = hermes_artifact_write(
        title="ArchiveForge packet v1",
        artifact_type="markdown_report",
        content="# v1\nSummary",
        content_format="markdown",
        module="archiveforge",
        source_agent="hermes",
        tags=["archiveforge", "packet"],
        retrieval_keywords=["life magazine", "review packet"],
    )
    new_artifact = hermes_artifact_write(
        title="ArchiveForge packet v2",
        artifact_type="markdown_report",
        content="# v2\nSummary",
        content_format="markdown",
        module="archiveforge",
        source_agent="hermes",
        tags=["archiveforge", "packet"],
        retrieval_keywords=["life magazine", "review packet"],
    )

    old_id = old_artifact["artifact_id"]
    new_id = new_artifact["artifact_id"]

    updated = hermes_artifact_update_status(old_id, approval_status="approved", notes="Founder accepted v1")
    assert updated["approval_status"] == "approved"
    assert updated["status_notes"] == "Founder accepted v1"

    search_before = hermes_artifact_search(query="packet", module="archiveforge", current_only=True)
    assert any(item["id"] == old_id for item in search_before["results"])
    assert any(item["id"] == new_id for item in search_before["results"])

    supersede = hermes_artifact_supersede(
        superseded_id=old_id,
        replacement_id=new_id,
        notes="v2 replaces v1",
    )
    assert supersede["old_status"] == "superseded"
    assert old_id in supersede["new_supersedes"]

    search_current = hermes_artifact_search(query="packet", module="archiveforge", current_only=True)
    ids_current = {item["id"] for item in search_current["results"]}
    assert old_id not in ids_current
    assert new_id in ids_current

    search_all = hermes_artifact_search(
        query="packet",
        module="archiveforge",
        current_only=False,
        include_superseded=True,
    )
    ids_all = {item["id"] for item in search_all["results"]}
    assert old_id in ids_all
    assert new_id in ids_all

    export = hermes_artifact_export(new_id, export_format="json")
    export_path = Path(export["path"])
    assert export_path.exists()
    exported = export_path.read_text(encoding="utf-8")
    assert "\"truth_hierarchy\"" in exported


def test_truth_hierarchy_runtime_precedence():
    assert TRUTH_HIERARCHY == (
        "runtime",
        "repo_truth",
        "database_truth",
        "module_docs",
        "approved_artifacts",
        "session_context",
        "model_opinion",
    )


def test_max_chat_still_works_and_artifacts_are_optional(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")

    async def fake_ai_router(*args, **kwargs):
        return AIResponse(
            content="Hello from MAX without artifact blocks.",
            model_used="test-model",
            fallback_used=False,
        )

    monkeypatch.setattr(max_router.ai_router, "chat", fake_ai_router)

    request = max_router.ChatRequest(
        message="hello",
        history=[],
        channel="web",
    )
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert response.response.startswith("Hello from MAX")
    assert response.model_used == "test-model"
    assert response.artifacts is None
