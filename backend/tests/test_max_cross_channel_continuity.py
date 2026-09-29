"""Cross-channel continuity tests for the MAX system prompt (H52 retired).

H52 Phase 2 retired the compact prompt variant. These tests were scoped
to the compact prompt's cross-channel section, which no longer exists.
The cross-channel logic itself moved into get_max_brain_context()
(system_prompt.py:635-650) and is invoked by get_system_prompt_with_brain
for every turn. The live behavior — web/CC and telegram carry forward
to each other — is now verified at the store API level, since that is
where the cross-channel filtering actually runs.
"""
from datetime import datetime, timedelta

from app.services.max import unified_message_store as ums
from app.services.max.unified_message_store import UnifiedMessageStore


def _set_created_at(store: UnifiedMessageStore, conversation_id: str, created_at: str) -> None:
    conn = store._get_conn()
    try:
        conn.execute(
            "UPDATE unified_messages SET created_at = ? WHERE conversation_id = ?",
            (conversation_id, created_at),
        )
        conn.commit()
    finally:
        conn.close()


def test_cross_channel_context_excludes_stale_rows_with_sqlite_timestamps(tmp_path, monkeypatch):
    store = UnifiedMessageStore(tmp_path / "unified_messages.db")
    monkeypatch.setattr(ums, "unified_store", store)

    store.add_message("fresh-web", "web", "user", "fresh web timestamp proof")
    store.add_message("stale-tg", "telegram", "user", "stale telegram timestamp proof")

    stale_time = (datetime.utcnow() - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S")
    _set_created_at(store, "stale-tg", stale_time)

    ctx = store.get_cross_channel_context(exclude_channel="telegram", limit_per_channel=3, hours=4)

    # Fresh row survives, stale row excluded by the hours window.
    assert any(
        "fresh web timestamp proof" in m["content"]
        for msgs in ctx.values() for m in msgs
    )
    assert not any(
        "stale telegram timestamp proof" in m["content"]
        for msgs in ctx.values() for m in msgs
    )