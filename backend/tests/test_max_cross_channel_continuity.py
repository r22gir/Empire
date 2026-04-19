from datetime import datetime, timedelta

from app.services.max import system_prompt
from app.services.max import unified_message_store as ums
from app.services.max.unified_message_store import UnifiedMessageStore


def _set_created_at(store: UnifiedMessageStore, conversation_id: str, created_at: str) -> None:
    conn = store._get_conn()
    try:
        conn.execute(
            "UPDATE unified_messages SET created_at = ? WHERE conversation_id = ?",
            (created_at, conversation_id),
        )
        conn.commit()
    finally:
        conn.close()


def _insert_legacy_channel(store: UnifiedMessageStore, conversation_id: str, channel: str, content: str) -> None:
    conn = store._get_conn()
    try:
        conn.execute(
            """INSERT INTO unified_messages
               (conversation_id, channel, role, content, created_at)
               VALUES (?, ?, 'user', ?, datetime('now'))""",
            (conversation_id, channel, content),
        )
        conn.commit()
    finally:
        conn.close()


def test_telegram_compact_prompt_includes_web_context_and_excludes_telegram(tmp_path, monkeypatch):
    store = UnifiedMessageStore(tmp_path / "unified_messages.db")
    monkeypatch.setattr(ums, "unified_store", store)

    store.add_message("web-proof", "dashboard", "user", "web command center continuity proof")
    store.add_message("tg-proof", "telegram", "user", "telegram private continuity proof")

    prompt = system_prompt.get_compact_system_prompt(channel="telegram")

    assert "Other Surface Activity" in prompt
    assert "Web/CC" in prompt
    assert "web command center continuity proof" in prompt
    assert "telegram private continuity proof" not in prompt


def test_web_compact_prompt_includes_telegram_and_excludes_web_aliases(tmp_path, monkeypatch):
    store = UnifiedMessageStore(tmp_path / "unified_messages.db")
    monkeypatch.setattr(ums, "unified_store", store)

    store.add_message("tg-proof", "telegram", "user", "telegram handoff proof")
    store.add_message("web-chat-proof", "web_chat", "user", "web_chat should be excluded")
    store.add_message("dashboard-proof", "dashboard", "user", "dashboard should be excluded")
    _insert_legacy_channel(store, "legacy-web-proof", "web", "legacy web should be excluded")
    _insert_legacy_channel(store, "legacy-web-cc-proof", "web_cc", "legacy web_cc should be excluded")

    prompt = system_prompt.get_compact_system_prompt(channel="web_chat")

    assert "Telegram" in prompt
    assert "telegram handoff proof" in prompt
    assert "web_chat should be excluded" not in prompt
    assert "dashboard should be excluded" not in prompt
    assert "legacy web should be excluded" not in prompt
    assert "legacy web_cc should be excluded" not in prompt


def test_cross_channel_context_excludes_stale_rows_with_sqlite_timestamps(tmp_path, monkeypatch):
    store = UnifiedMessageStore(tmp_path / "unified_messages.db")
    monkeypatch.setattr(ums, "unified_store", store)

    store.add_message("fresh-web", "web", "user", "fresh web timestamp proof")
    store.add_message("stale-tg", "telegram", "user", "stale telegram timestamp proof")

    stale_time = (datetime.utcnow() - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S")
    _set_created_at(store, "stale-tg", stale_time)

    prompt = system_prompt.get_compact_system_prompt(channel="telegram")
    ctx = store.get_cross_channel_context(exclude_channel="telegram", limit_per_channel=3, hours=4)

    assert "fresh web timestamp proof" in prompt
    assert "stale telegram timestamp proof" not in prompt
    assert "web_chat" in ctx
    assert all("stale telegram timestamp proof" not in m["content"] for msgs in ctx.values() for m in msgs)
