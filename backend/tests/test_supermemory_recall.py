from datetime import datetime, timedelta, timezone

import pytest

from app.services.max import supermemory_recall


def test_supermemory_ranking_prefers_surface_registry_and_recency(monkeypatch):
    monkeypatch.setattr(supermemory_recall, "_git_commit", lambda: "new1234")
    now = datetime.now(timezone.utc)
    memories = [
        {
            "id": "generic-current",
            "content": "generic current",
            "surface": "generic",
            "written_at": (now - timedelta(minutes=1)).isoformat(),
            "metadata": {"registry_version": "operating-registry-v2", "commit_hash": "new1234", "surface": "generic", "valid_until": (now + timedelta(days=1)).isoformat()},
        },
        {
            "id": "web-old-registry",
            "content": "web old registry",
            "surface": "web_chat",
            "written_at": now.isoformat(),
            "metadata": {"registry_version": "old", "commit_hash": "new1234", "surface": "web_chat", "valid_until": (now + timedelta(days=1)).isoformat()},
        },
        {
            "id": "web-current-older",
            "content": "web current older",
            "surface": "web_chat",
            "written_at": (now - timedelta(minutes=2)).isoformat(),
            "metadata": {"registry_version": "operating-registry-v2", "commit_hash": "new1234", "surface": "web_chat", "valid_until": (now + timedelta(days=1)).isoformat()},
        },
        {
            "id": "telegram-current",
            "content": "telegram current",
            "surface": "telegram",
            "written_at": now.isoformat(),
            "metadata": {"registry_version": "operating-registry-v2", "commit_hash": "new1234", "surface": "telegram", "valid_until": (now + timedelta(days=1)).isoformat()},
        },
    ]

    ranked = supermemory_recall.rank_supermemory_results(
        memories,
        current_surface="web",
        current_registry_version="operating-registry-v2",
        current_commit_hash="new1234",
    )

    assert ranked[0]["id"] == "web-current-older"
    assert ranked.index(next(m for m in ranked if m["id"] == "generic-current")) < ranked.index(next(m for m in ranked if m["id"] == "telegram-current"))


def test_supermemory_write_includes_registry_commit_and_decay(monkeypatch, tmp_path):
    monkeypatch.setattr(
        supermemory_recall,
        "get_registry_load_info",
        lambda: {"registry_version": "operating-registry-v2", "last_error": None},
    )
    monkeypatch.setattr(supermemory_recall, "_git_commit", lambda: "abc1234")

    result = supermemory_recall.write_supermemory_memory(
        bucket="session/handoff memory",
        content="Handoff summary",
        surface="mobile_browser",
        tags=["empirebox", "max"],
        product="max",
        trigger="verified_handoff_refresh",
        path=tmp_path / "supermemory.jsonl",
    )
    memories = supermemory_recall._load_memories(tmp_path / "supermemory.jsonl")

    assert result["written"] is True
    meta = memories[0]["metadata"]
    assert meta["registry_version"] == "operating-registry-v2"
    assert meta["commit_hash"] == "abc1234"
    assert meta["surface"] == "web_chat"
    assert meta["valid_until"]
    assert meta["version_ceiling"] == "operating-registry-v2"
    assert meta["authority"] == "secondary_recall_only"


def test_supermemory_write_refuses_when_registry_unavailable(monkeypatch, tmp_path):
    monkeypatch.setattr(
        supermemory_recall,
        "get_registry_load_info",
        lambda: {"registry_version": None, "last_error": "parse failed"},
    )

    with pytest.raises(RuntimeError):
        supermemory_recall.write_supermemory_memory(
            bucket="session/handoff memory",
            content="should not write",
            trigger="verified_handoff_refresh",
            path=tmp_path / "supermemory.jsonl",
        )

    assert not (tmp_path / "supermemory.jsonl").exists()


def test_supermemory_recall_reports_secondary_authority(monkeypatch, tmp_path):
    monkeypatch.setattr(
        supermemory_recall,
        "get_registry_load_info",
        lambda: {"registry_version": "operating-registry-v2", "last_error": None},
    )
    monkeypatch.setattr(supermemory_recall, "_git_commit", lambda: "abc1234")
    path = tmp_path / "supermemory.jsonl"
    supermemory_recall.write_supermemory_memory(
        bucket="product snapshots",
        content="MAX status snapshot",
        surface="web",
        tags=["max"],
        product="max",
        trigger="verified_product_snapshot",
        path=path,
    )

    recall = supermemory_recall.query_supermemory_recall("max", surface="web", path=path)

    assert recall["authority"] == "secondary_recall_only"
    assert recall["runtime_truth_override"] is True
    assert recall["results"][0]["metadata"]["registry_version"] == "operating-registry-v2"
