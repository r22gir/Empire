from app.services.max.continuity_compaction import (
    CONTEXT_TOKEN_THRESHOLD,
    PACKET_SCHEMA_VERSION,
    build_session_handoff_packet,
    read_session_handoff_packet,
    restore_session_handoff,
    write_session_handoff_packet,
    should_handle_continuity_command,
    create_founder_handoff,
    audit_continuity_state,
)


def test_session_handoff_round_trip_preserves_tier_1(tmp_path):
    path = tmp_path / "session_handoff.json"
    packet = build_session_handoff_packet(
        current_task="Implement OpenClaw gate",
        channel="mobile_browser",
        last_runtime_truth_result={"commit": "abc1234", "restart_required": False},
        product_statuses={"openclaw": "gated"},
        known_limitations=["Supermemory deferred"],
        delegated_task_state={"task_id": 42, "state": "queued"},
        last_founder_intent="Make MAX safer across sessions",
        recent_session_history=["verified registry", "implemented gate"],
        last_evaluation_score={"overall_score": 0.8},
    )

    write_session_handoff_packet(packet, path)
    loaded = read_session_handoff_packet(path)
    restored = restore_session_handoff(path)

    assert CONTEXT_TOKEN_THRESHOLD == 120_000
    assert loaded["schema"] == "max-session-handoff-v1"
    assert loaded["packet_schema_version"] == PACKET_SCHEMA_VERSION
    assert restored["restored"] is True
    assert restored["tier_1"]["current_task"] == "Implement OpenClaw gate"
    assert restored["tier_1"]["founder_surface_identity"]["canonical_channel"] == "web_chat"
    assert restored["tier_1"]["registry_version"]
    assert restored["tier_1"]["last_runtime_truth_result"]["commit"] == "abc1234"
    assert restored["last_evaluation_score"]["overall_score"] == 0.8


def test_session_handoff_rejects_schema_mismatch(tmp_path):
    path = tmp_path / "session_handoff.json"
    packet = build_session_handoff_packet(
        current_task="Protect handoff schema",
        channel="web",
        last_runtime_truth_result={"commit": "abc1234"},
    )
    packet["packet_schema_version"] = PACKET_SCHEMA_VERSION + 1
    write_session_handoff_packet(packet, path)

    assert read_session_handoff_packet(path) is None
    assert restore_session_handoff(path) == {"restored": False, "reason": "no valid handoff packet"}


def test_founder_compaction_command_refreshes_packet(monkeypatch, tmp_path):
    path = tmp_path / "session_handoff.json"
    monkeypatch.setattr(
        "app.services.max.continuity_compaction._runtime_truth",
        lambda public=True: {
            "current_commit": {"hash": "fresh123"},
            "restart_required": False,
            "openclaw_gate": {"state": "healthy"},
        },
    )
    monkeypatch.setattr(
        "app.services.max.continuity_compaction._active_task_state",
        lambda: {"openclaw_tasks": [{"id": 1}], "max_tasks": []},
    )
    monkeypatch.setattr(
        "app.services.max.continuity_compaction._latest_score",
        lambda: {"overall_score": 0.98},
    )
    monkeypatch.setattr(
        "app.services.max.supermemory_recall.write_handoff_memory_from_packet",
        lambda packet: {"written": True, "memory_id": "test"},
    )

    assert should_handle_continuity_command("compact now")
    result = create_founder_handoff(
        message="compact now",
        channel="mobile_browser",
        history=["prior step"],
        path=path,
    )
    restored = audit_continuity_state(channel="mobile_browser")

    assert result["packet"]["tier_1"]["last_runtime_truth_result"]["commit"] == "fresh123"
    assert result["packet"]["tier_1"]["founder_surface_identity"]["canonical_channel"] == "web_chat"
    assert result["packet"]["last_evaluation_score"]["overall_score"] == 0.98
    assert path.exists()
    assert restored["surface"]["canonical_channel"] == "web_chat"
