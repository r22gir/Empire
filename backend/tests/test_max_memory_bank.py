from app.services.max.unified_message_store import UnifiedMessageStore


def test_memory_bank_canonical_fields_and_filters(tmp_path):
    store = UnifiedMessageStore(tmp_path / "unified_messages.db")

    store.add_message(
        conversation_id="web-proof",
        channel="web",
        role="user",
        content="Founder asked MAX to remember the blue supplier note.",
        founder_verified=True,
        attachment_refs=[{"type": "upload", "ref": "window-photo.jpg"}],
        linked_refs=[{"type": "task", "id": "task-1"}],
    )
    store.add_message(
        conversation_id="email-proof",
        channel="email",
        role="user",
        content="Please review the attached invoice.",
        sender="empirebox2026@gmail.com",
        recipient="max@empirebox.store",
        subject="Invoice review",
        attachment_refs=[{"type": "email_file", "ref": "invoice.pdf"}],
        founder_verified=True,
    )

    web_messages = store.list_memory_bank(channel="web_chat", query="blue supplier", founder_only=True)
    assert len(web_messages) == 1
    assert web_messages[0]["channel"] == "web_chat"
    assert web_messages[0]["direction"] == "inbound"
    assert web_messages[0]["sender"] == "Founder"
    assert web_messages[0]["recipient"] == "MAX"
    assert web_messages[0]["attachment_refs"][0]["ref"] == "window-photo.jpg"
    assert web_messages[0]["linked_refs"][0]["id"] == "task-1"

    attachment_messages = store.list_memory_bank(channel="attachments")
    assert {m["channel"] for m in attachment_messages} == {"web_chat", "email"}
    assert all(m["attachment_refs"] for m in attachment_messages)

    threads = store.get_memory_threads()
    thread_ids = {thread["thread_id"] for thread in threads}
    assert {"web-proof", "email-proof"}.issubset(thread_ids)


def test_memory_bank_keeps_unverified_email_truthful(tmp_path):
    store = UnifiedMessageStore(tmp_path / "unified_messages.db")

    store.add_message(
        conversation_id="email-unverified",
        channel="email",
        role="user",
        content="External message",
        sender="someone@example.com",
        recipient="max@empirebox.store",
        subject="Outside sender",
        founder_verified=False,
    )

    all_email = store.list_memory_bank(channel="email", query="External")
    founder_email = store.list_memory_bank(channel="email", query="External", founder_only=True)

    assert len(all_email) == 1
    assert all_email[0]["founder_verified"] is False
    assert all_email[0]["sender"] == "someone@example.com"
    assert founder_email == []
