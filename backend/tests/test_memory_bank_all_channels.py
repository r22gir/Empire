from app.services.max.unified_message_store import UnifiedMessageStore


def test_memory_bank_all_channels_returns_registry_channel_labels(tmp_path):
    store = UnifiedMessageStore(tmp_path / "unified_messages.db")
    store.add_message("web-1", "web", "user", "web hello", direction="inbound")
    store.add_message("tg-1", "telegram", "user", "telegram hello", direction="inbound")
    store.add_outbound_email(
        recipient="client@example.com",
        subject="Email proof",
        body_html="<p>email hello</p>",
        sender="max@empirebox.store",
    )

    rows = store.list_memory_bank(channel="all", limit=10)
    channels = {row["channel"] for row in rows}

    assert {"web_chat", "telegram", "email"}.issubset(channels)
    email = next(row for row in rows if row["channel"] == "email")
    assert email["direction"] == "outbound"
    assert email["subject"] == "Email proof"


def test_web_aliases_share_web_chat_history(tmp_path):
    store = UnifiedMessageStore(tmp_path / "unified_messages.db")
    store.add_message("desktop-1", "web", "user", "desktop web", direction="inbound")
    store.add_message("mobile-1", "mobile_browser", "user", "mobile web", direction="inbound")
    store.add_message("cc-1", "command_center", "user", "command center", direction="inbound")

    rows = store.list_memory_bank(channel="web_chat", limit=10)

    assert {row["message_text"] for row in rows} == {"desktop web", "mobile web", "command center"}
    assert {row["channel"] for row in rows} == {"web_chat"}
