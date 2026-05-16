from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_artifact_api_write_search_get_status_export(monkeypatch, tmp_path):
    root = tmp_path / "empire-box-memory"
    monkeypatch.setenv("EMPIRE_BOX_MEMORY_DIR", str(root))
    monkeypatch.setenv("EMPIRE_LANE", "v10-test")

    status_res = client.get("/api/v1/hermes/artifacts/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["enabled"] is True
    assert status_data["lane"] == "v10-test"

    write_res = client.post(
        "/api/v1/hermes/artifacts/write",
        json={
            "title": "Workroom Plan Packet",
            "artifact_type": "html_artifact",
            "content_format": "html",
            "content": "<h1>Workroom</h1><script>alert(1)</script><p>Plan packet.</p>",
                "module": "workroom",
                "source_agent": "max",
                "approval_status": "approved",
                "tags": ["workroom", "plan"],
                "retrieval_keywords": ["plan packet", "workroom"],
            },
        )
    assert write_res.status_code == 200
    write_data = write_res.json()
    artifact_id = write_data["artifact_id"]

    get_res = client.get(f"/api/v1/hermes/artifacts/{artifact_id}")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["metadata"]["id"] == artifact_id
    assert get_data["metadata"]["module"] == "workroom"
    assert "Plan packet" in get_data["extracted_text"]

    search_res = client.post(
        "/api/v1/hermes/artifacts/search",
        json={"query": "workroom", "module": "workroom", "current_only": True},
    )
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["count"] >= 1
    assert search_data["ranking_version"] == "hermes_artifact_rank_v3"
    assert "score" in search_data["results"][0]
    assert "matched_fields" in search_data["results"][0]
    assert "latest_attestation_level" in search_data["results"][0]
    assert "latest_attestation_hash_short" in search_data["results"][0]
    assert "requires_reattestation" in search_data["results"][0]
    assert any(item["id"] == artifact_id for item in search_data["results"])

    update_res = client.post(
        f"/api/v1/hermes/artifacts/{artifact_id}/status",
        json={
            "approval_status": "approved",
            "notes": "Founder approved",
            "actor_id": "founder-session-api",
            "actor_type": "founder",
            "actor_label": "Founder QA",
            "actor_source": "verified_session",
            "actor_session_id": "founder-session-api",
            "approval_method": "api",
            "approval_confidence": "verified_session",
            "attestation_level": "founder_attested",
            "actor_note": "api status approval test",
        },
    )
    assert update_res.status_code == 200
    payload = update_res.json()
    assert payload["approval_status"] == "approved"
    assert payload["approval_actor_id"] == "founder-session-api"
    assert payload["approval_actor_source"] == "verified_session"
    assert payload["approval_method"] == "api"
    assert payload["approval_confidence"] == "verified_session"
    assert payload["latest_attestation_level"] == "founder_attested"
    assert payload["latest_attestation_hash"]
    assert payload["latest_attestation_hash_short"]
    assert payload["is_current"] is True
    assert payload["requires_reattestation"] is False
    history = payload.get("approval_history") or []
    assert history[-1]["approval_actor_type"] == "founder"
    assert history[-1]["approval_actor_label"] == "Founder QA"
    assert history[-1]["approval_confidence"] == "verified_session"
    assert history[-1]["attestation_hash"]

    export_res = client.get(f"/api/v1/hermes/artifacts/{artifact_id}/export?export_format=json")
    assert export_res.status_code == 200
    assert export_res.json()["format"] == "json"


def test_artifact_api_supersede(monkeypatch, tmp_path):
    root = tmp_path / "empire-box-memory"
    monkeypatch.setenv("EMPIRE_BOX_MEMORY_DIR", str(root))
    monkeypatch.setenv("EMPIRE_LANE", "v10-test")

    old_res = client.post(
        "/api/v1/hermes/artifacts/write",
        json={
            "title": "Archive report v1",
            "artifact_type": "markdown_report",
            "content_format": "markdown",
            "content": "# v1",
            "module": "archiveforge",
            "source_agent": "hermes",
            "approval_status": "approved",
        },
    )
    new_res = client.post(
        "/api/v1/hermes/artifacts/write",
        json={
            "title": "Archive report v2",
            "artifact_type": "markdown_report",
            "content_format": "markdown",
            "content": "# v2",
            "module": "archiveforge",
            "source_agent": "hermes",
            "approval_status": "approved",
        },
    )
    old_id = old_res.json()["artifact_id"]
    new_id = new_res.json()["artifact_id"]

    sup_res = client.post(
        "/api/v1/hermes/artifacts/supersede",
        json={
            "superseded_id": old_id,
            "replacement_id": new_id,
            "notes": "v2 replaces v1",
        },
    )
    assert sup_res.status_code == 200
    sup_data = sup_res.json()
    assert sup_data["superseded_id"] == old_id
    assert sup_data["replacement_id"] == new_id

    current = client.post(
        "/api/v1/hermes/artifacts/search",
        json={"query": "archive report", "module": "archiveforge", "current_only": True},
    ).json()
    ids_current = {row["id"] for row in current["results"]}
    assert new_id in ids_current
    assert old_id not in ids_current

    current_approved_only = client.post(
        "/api/v1/hermes/artifacts/search",
        json={"query": "archive report", "module": "archiveforge", "current_only": True, "approval_status": "approved"},
    )
    assert current_approved_only.status_code == 200
    approved_rows = current_approved_only.json()["results"]
    assert all(row["approval_status"] == "approved" for row in approved_rows)
