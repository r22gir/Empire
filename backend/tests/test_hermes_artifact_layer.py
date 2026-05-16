import asyncio
import importlib
from pathlib import Path

from fastapi import BackgroundTasks, Response

from app.services.max.ai_router import AIResponse
from app.services.max.hermes_artifact_layer import (
    TRUTH_HIERARCHY,
    _compute_attestation_hash,
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
    assert metadata["approval_method"] == "max_internal"
    assert metadata["approval_confidence"] == "system_generated"
    assert metadata["approval_actor_source"] == "system_generated"
    assert metadata["lane"] == "v10-test"
    assert metadata["safety_status"] == "sanitized_no_scripts_no_external_network"
    assert metadata["latest_attestation_level"] == "system_generated"
    assert metadata["latest_attestation_hash"]
    assert metadata["latest_content_hash"]
    assert isinstance(metadata.get("attestation_history"), list)


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

    updated = hermes_artifact_update_status(
        old_id,
        approval_status="approved",
        notes="Founder accepted v1",
        actor_id="founder-session-1",
        actor_type="founder",
        actor_label="Founder QA",
        actor_source="verified_session",
        approval_method="api",
        approval_confidence="verified_session",
        actor_note="review accepted",
    )
    assert updated["approval_status"] == "approved"
    assert updated["status_notes"] == "Founder accepted v1"
    assert updated["approval_actor_id"] == "founder-session-1"
    assert updated["approval_actor_source"] == "verified_session"
    assert updated["approval_confidence"] == "verified_session"
    assert updated["approval_note"] == "review accepted"
    assert updated["latest_attestation_level"] == "founder_attested"
    assert updated["latest_attestation_hash"]

    search_before = hermes_artifact_search(query="packet", module="archiveforge", current_only=True)
    assert any(item["id"] == old_id for item in search_before["results"])
    assert all(item["approval_status"] == "approved" for item in search_before["results"])
    assert not any(item["id"] == new_id for item in search_before["results"])
    assert all("score" in item for item in search_before["results"])
    assert all("matched_fields" in item for item in search_before["results"])

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
    assert new_id not in ids_current

    hermes_artifact_update_status(
        new_id,
        approval_status="approved",
        actor_id="founder-session-1",
        actor_type="founder",
        actor_label="Founder QA",
        actor_source="verified_session",
        actor_session_id="founder-session-1",
        approval_method="api",
        approval_confidence="verified_session",
        actor_note="approved replacement",
    )
    search_current_after_approval = hermes_artifact_search(query="packet", module="archiveforge", current_only=True)
    ids_current_after = {item["id"] for item in search_current_after_approval["results"]}
    assert new_id in ids_current_after

    search_all = hermes_artifact_search(
        query="packet",
        module="archiveforge",
        current_only=False,
        include_superseded=True,
    )
    ids_all = {item["id"] for item in search_all["results"]}
    assert old_id in ids_all
    assert new_id in ids_all
    old_row = next(item for item in search_all["results"] if item["id"] == old_id)
    assert old_row["stale_warning"] == "artifact_superseded_or_not_current"
    assert old_row["is_current"] is False
    assert old_row["latest_attestation_level"] in {"local_ui", "session_verified", "founder_attested", "system_generated", "imported", "none"}

    export = hermes_artifact_export(new_id, export_format="json")
    export_path = Path(export["path"])
    assert export_path.exists()
    exported = export_path.read_text(encoding="utf-8")
    assert "\"truth_hierarchy\"" in exported


def test_ranking_prefers_approved_current_module_match(monkeypatch, tmp_path):
    root = tmp_path / "empire-box-memory"
    monkeypatch.setenv("EMPIRE_BOX_MEMORY_DIR", str(root))
    monkeypatch.setenv("EMPIRE_LANE", "v10-test")

    approved_current = hermes_artifact_write(
        title="ArchiveForge Publish Safety Review",
        artifact_type="markdown_report",
        content="ArchiveForge publish gate approved current notes",
        content_format="markdown",
        module="archiveforge",
        source_agent="max",
        approval_status="approved",
        tags=["archiveforge", "publish"],
        retrieval_keywords=["publish safety", "archiveforge"],
        provenance={
            "source_agent": "max",
            "source_files": ["docs/v10/HERMES_KNOWLEDGE_ARTIFACT_LAYER.md"],
            "source_endpoints": ["/api/v1/hermes/artifacts/search"],
        },
    )["artifact_id"]

    rejected = hermes_artifact_write(
        title="ArchiveForge Publish Safety Draft",
        artifact_type="markdown_report",
        content="Older rejected draft",
        content_format="markdown",
        module="archiveforge",
        source_agent="max",
        approval_status="rejected",
        tags=["archiveforge"],
        retrieval_keywords=["publish safety"],
    )["artifact_id"]

    rows = hermes_artifact_search(
        query="archiveforge publish safety review",
        module="archiveforge",
        current_only=False,
        include_superseded=True,
        limit=10,
    )["results"]
    assert rows
    top = rows[0]
    assert top["id"] == approved_current
    assert top["approval_status"] == "approved"
    assert top["is_current"] is True
    assert top["score"] >= rows[-1]["score"]
    assert "module" in top["matched_fields"]
    assert "approval_status:approved" in top["matched_fields"]
    assert top["freshness_score"] >= 0
    assert top["approval_weight"] > 0
    assert top["module_weight"] > 0
    assert top["provenance_weight"] > 0

    rejected_row = next(item for item in rows if item["id"] == rejected)
    assert rejected_row["approval_status"] == "rejected"
    assert rejected_row["is_current"] is False
    assert rejected_row["stale_warning"] == "artifact_status_rejected_not_current_truth"


def test_ranking_prefers_founder_attested_over_local_ui(monkeypatch, tmp_path):
    root = tmp_path / "empire-box-memory"
    monkeypatch.setenv("EMPIRE_BOX_MEMORY_DIR", str(root))
    monkeypatch.setenv("EMPIRE_LANE", "v10-test")

    local_ui_id = hermes_artifact_write(
        title="ArchiveForge Decision Local UI",
        artifact_type="markdown_report",
        content="Decision packet for archiveforge flow",
        content_format="markdown",
        module="archiveforge",
        source_agent="max",
        approval_status="approved",
    )["artifact_id"]
    founder_id = hermes_artifact_write(
        title="ArchiveForge Decision Founder Attested",
        artifact_type="markdown_report",
        content="Decision packet for archiveforge flow",
        content_format="markdown",
        module="archiveforge",
        source_agent="max",
        approval_status="approved",
    )["artifact_id"]

    hermes_artifact_update_status(
        local_ui_id,
        approval_status="approved",
        actor_type="founder",
        actor_label="Founder UI",
        actor_source="local_ui",
        approval_method="ui",
        approval_confidence="local_ui",
        attestation_level="local_ui",
    )
    hermes_artifact_update_status(
        founder_id,
        approval_status="approved",
        actor_id="founder-attested-session",
        actor_type="founder",
        actor_label="Founder QA",
        actor_source="verified_session",
        actor_session_id="founder-attested-session",
        approval_method="api",
        approval_confidence="verified_session",
        attestation_level="founder_attested",
    )

    rows = hermes_artifact_search(
        query="archiveforge decision packet",
        module="archiveforge",
        current_only=True,
        approval_status="approved",
        limit=10,
    )["results"]
    founder_row = next(item for item in rows if item["id"] == founder_id)
    local_row = next(item for item in rows if item["id"] == local_ui_id)
    assert founder_row["latest_attestation_level"] == "founder_attested"
    assert local_row["latest_attestation_level"] == "local_ui"
    assert founder_row["score"] >= local_row["score"]


def test_verified_session_confidence_requires_actor_id(monkeypatch, tmp_path):
    root = tmp_path / "empire-box-memory"
    monkeypatch.setenv("EMPIRE_BOX_MEMORY_DIR", str(root))
    monkeypatch.setenv("EMPIRE_LANE", "v10-test")

    artifact_id = hermes_artifact_write(
        title="Session confidence packet",
        artifact_type="markdown_report",
        content="# session confidence",
        content_format="markdown",
        module="system",
        source_agent="max",
        approval_status="draft",
    )["artifact_id"]

    updated = hermes_artifact_update_status(
        artifact_id,
        approval_status="approved",
        actor_type="founder",
        actor_source="verified_session",
        approval_method="api",
        approval_confidence="verified_session",
        actor_note="attempt verified without actor id",
    )
    assert updated["approval_actor_source"] == "unknown"
    assert updated["approval_confidence"] != "verified_session"
    assert updated["latest_attestation_level"] in {"none", "system_generated"}


def test_attestation_hash_chain_and_deterministic(monkeypatch, tmp_path):
    root = tmp_path / "empire-box-memory"
    monkeypatch.setenv("EMPIRE_BOX_MEMORY_DIR", str(root))
    monkeypatch.setenv("EMPIRE_LANE", "v10-test")

    artifact_id = hermes_artifact_write(
        title="Attestation chain packet",
        artifact_type="markdown_report",
        content="# chain",
        content_format="markdown",
        module="archiveforge",
        source_agent="max",
        approval_status="draft",
    )["artifact_id"]

    approved = hermes_artifact_update_status(
        artifact_id,
        approval_status="approved",
        actor_id="founder-session-2",
        actor_type="founder",
        actor_label="Founder QA",
        actor_source="verified_session",
        actor_session_id="founder-session-2",
        approval_method="api",
        approval_confidence="verified_session",
        actor_note="approve for release packet",
    )
    changed = hermes_artifact_update_status(
        artifact_id,
        approval_status="changes_requested",
        actor_id="founder-session-2",
        actor_type="founder",
        actor_label="Founder QA",
        actor_source="verified_session",
        actor_session_id="founder-session-2",
        approval_method="api",
        approval_confidence="verified_session",
        actor_note="follow-up changes",
    )

    approved_attestation = (approved.get("attestation_history") or [])[-1]
    changed_attestation = (changed.get("attestation_history") or [])[-1]

    assert approved_attestation["attestation_hash"] == _compute_attestation_hash(approved_attestation)
    assert changed_attestation["attestation_hash"] == _compute_attestation_hash(changed_attestation)
    assert changed_attestation["previous_attestation_hash"] == approved_attestation["attestation_hash"]
    assert approved["latest_attestation_level"] == "founder_attested"


def test_content_change_requires_reattestation(monkeypatch, tmp_path):
    root = tmp_path / "empire-box-memory"
    monkeypatch.setenv("EMPIRE_BOX_MEMORY_DIR", str(root))
    monkeypatch.setenv("EMPIRE_LANE", "v10-test")

    artifact_id = hermes_artifact_write(
        title="Reattestation packet",
        artifact_type="html_artifact",
        content="<h1>Alpha</h1><p>initial</p>",
        content_format="html",
        module="archiveforge",
        source_agent="max",
        approval_status="approved",
    )["artifact_id"]

    before = hermes_artifact_get(artifact_id)
    assert before is not None
    assert before["is_current"] is True
    assert before["requires_reattestation"] is False
    html_path = Path(before["metadata"]["paths"]["artifact_html"])
    html_path.write_text("<h1>Alpha</h1><p>changed content</p>", encoding="utf-8")

    changed_bundle = hermes_artifact_get(artifact_id)
    assert changed_bundle is not None
    assert changed_bundle["requires_reattestation"] is True
    assert changed_bundle["is_current"] is False
    assert changed_bundle["stale_warning"] == "artifact_requires_reattestation"


def test_truth_hierarchy_runtime_precedence():
    assert TRUTH_HIERARCHY == (
        "runtime",
        "repo_truth",
        "database_truth",
        "module_docs",
        "approved_attested_artifacts",
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
