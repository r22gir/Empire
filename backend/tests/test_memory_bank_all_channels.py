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
