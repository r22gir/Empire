from app.services.max.continuity_compaction import (
    CONTEXT_TOKEN_THRESHOLD,
    build_session_handoff_packet,
    read_session_handoff_packet,
    restore_session_handoff,
    write_session_handoff_packet,
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
    assert restored["restored"] is True
    assert restored["tier_1"]["current_task"] == "Implement OpenClaw gate"
    assert restored["tier_1"]["founder_surface_identity"]["canonical_channel"] == "web_chat"
    assert restored["tier_1"]["registry_version"]
    assert restored["tier_1"]["last_runtime_truth_result"]["commit"] == "abc1234"
    assert restored["last_evaluation_score"]["overall_score"] == 0.8
