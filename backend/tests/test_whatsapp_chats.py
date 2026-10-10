"""WhatsApp chat-log and founder read API. Mocks only — no live Meta, no live data."""
from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import whatsapp as whatsapp_router
from app.services.max import whatsapp_channel as wa
from app.services.max.whatsapp_log import (
    get_conversation_messages,
    get_display_label,
    list_conversations,
    log_message,
    search_all_messages,
    update_delivery_status,
)
from tests._live_data_guard import assert_isolated_env, assert_no_live_graph

pytest_plugins = ["tests._live_data_guard"]

FAKE_TOKEN = "test-access-token-secret"
FAKE_SECRET = "test-app-secret"
FAKE_VERIFY = "test-verify-token"
FOUNDER_PIN = "test-founder-pin"
RAFAEL = "12022996975"
NELMA = "17036239203"


class _GraphResponse:
    def __init__(self, body=None, content=b"", status_code=200):
        self.status_code = status_code
        self.content = content
        self._body = body or {}

    def json(self):
        return self._body


@pytest.fixture(autouse=True)
def _isolate_channel(monkeypatch, tmp_path, isolated_whatsapp_edition):
    monkeypatch.setattr(wa, "_state_path", lambda: tmp_path / "wa-state.json")
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", FAKE_TOKEN)
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123456")
    monkeypatch.setenv("WHATSAPP_APP_SECRET", FAKE_SECRET)
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", FAKE_VERIFY)
    monkeypatch.setenv("WHATSAPP_REPLY_MODE", "text")
    assert_isolated_env()


def _sign(body: bytes) -> str:
    digest = hmac.new(FAKE_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _payload(message: dict, sender: str = RAFAEL) -> bytes:
    body = {
        "object": "whatsapp_business_account",
        "entry": [{
            "changes": [{
                "field": "messages",
                "value": {
                    "messages": [{
                        "from": sender,
                        "id": message.get("id") or "wamid.1",
                        "timestamp": message.get("timestamp") or str(int(time.time())),
                        "type": message["type"],
                        **{k: v for k, v in message.items() if k not in {"id", "timestamp", "type"}},
                    }]
                },
            }]
        }],
    }
    return json.dumps(body).encode()


def _status_payload(message_id: str, status: str, error_code: str = "", error_title: str = "") -> bytes:
    st = {
        "id": message_id,
        "status": status,
        "timestamp": str(int(time.time())),
        "recipient_id": RAFAEL,
    }
    if error_code:
        st["errors"] = [{"code": error_code, "title": error_title or "failed"}]
    body = {
        "object": "whatsapp_business_account",
        "entry": [{"changes": [{"field": "messages", "value": {"statuses": [st]}}]}],
    }
    return json.dumps(body).encode()


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(whatsapp_router.router, prefix="/api/v1")
    return TestClient(app)


def test_display_labels_use_founder_phones():
    assert get_display_label(RAFAEL) == "Rafael"
    assert get_display_label("+1 703-623-9203") == "Nelma"
    assert get_display_label("15555550100").endswith("5555550100")


def test_secrets_never_enter_the_log(isolated_whatsapp_edition):
    log_message(
        RAFAEL,
        "inbound",
        "text",
        body=f"token Bearer {FAKE_TOKEN} and {FAKE_SECRET}",
        wa_message_id="wamid.secret",
    )
    messages, _ = get_conversation_messages(RAFAEL)
    blob = json.dumps(messages)
    assert FAKE_TOKEN not in blob
    assert FAKE_SECRET not in blob
    assert "Bearer [REDACTED]" in blob
    assert "[REDACTED]" in messages[0]["body"]


def test_inbound_and_outbound_logged_via_webhook(isolated_whatsapp_edition, monkeypatch):
    import asyncio

    posts = []

    def _post(url, body, headers):
        assert_no_live_graph(url)
        assert FAKE_TOKEN not in json.dumps(body)
        posts.append(body)
        return _GraphResponse({"messages": [{"id": "wamid.out-1"}]})

    async def _chat(text, wa_id):
        return "Max reply. Not sent."

    monkeypatch.setattr(wa, "max_chat", _chat)
    raw = _payload({"type": "text", "text": {"body": "What time is install?"}, "id": "wamid.in-1"})
    result = asyncio.run(wa.process_webhook(
        raw, _sign(raw), text_handler=wa.default_text_handler, http_post=_post,
    ))
    assert result["accepted"] is True
    convos = list_conversations()
    assert any(c["wa_id"] == RAFAEL and c["display_label"] == "Rafael" for c in convos)
    messages, total = get_conversation_messages(RAFAEL)
    assert total >= 2
    directions = {m["direction"] for m in messages}
    assert "inbound" in directions
    assert "outbound" in directions
    assert any("install" in (m["body"] or "") for m in messages)
    assert FAKE_TOKEN not in json.dumps(messages)


def test_voice_document_and_call_markers(isolated_whatsapp_edition, monkeypatch):
    import asyncio

    def _post(url, body, headers):
        return _GraphResponse({"messages": [{"id": "wamid.out-voice"}]})

    async def _voice(audio, mime, wa_id):
        return "Draft updated. Not sent."

    def _get(url, headers):
        if url.endswith("/media-voice"):
            return _GraphResponse({"url": "https://example.test/voice", "mime_type": "audio/ogg"})
        return _GraphResponse(content=b"OggS-voice")

    voice_raw = _payload({
        "type": "audio",
        "id": "wamid.voice",
        "audio": {"id": "media-voice", "mime_type": "audio/ogg", "voice": True},
    })
    asyncio.run(wa.process_webhook(
        voice_raw, _sign(voice_raw), voice_handler=_voice, http_get=_get, http_post=_post,
    ))

    doc_raw = _payload({
        "type": "document",
        "id": "wamid.doc-in",
        "document": {"id": "media-doc", "filename": "measure.pdf", "caption": "for Willard"},
    })
    asyncio.run(wa.process_webhook(doc_raw, _sign(doc_raw), http_post=_post))

    call_body = {
        "object": "whatsapp_business_account",
        "entry": [{
            "changes": [{
                "field": "messages",
                "value": {
                    "calls": [{
                        "id": "wamid.call-1",
                        "from": NELMA,
                        "event": "terminate",
                        "timestamp": str(int(time.time())),
                    }]
                },
            }]
        }],
    }
    call_raw = json.dumps(call_body).encode()
    asyncio.run(wa.process_webhook(call_raw, _sign(call_raw), http_post=_post))

    rafael_msgs, _ = get_conversation_messages(RAFAEL)
    types = {m["message_type"] for m in rafael_msgs}
    assert "voice" in types
    assert "document" in types
    assert any("measure.pdf" in (m["body"] or "") for m in rafael_msgs)

    nelma_msgs, _ = get_conversation_messages(NELMA)
    assert nelma_msgs
    assert nelma_msgs[0]["message_type"] == "call"
    assert nelma_msgs[0]["display_label"] == "Nelma"
    assert "terminate" in (nelma_msgs[0]["body"] or "")


def test_outbound_document_marker_has_filename_and_doc_id(isolated_whatsapp_edition, monkeypatch):
    import asyncio

    def _post(url, body, headers):
        assert_no_live_graph(url)
        return _GraphResponse({"messages": [{"id": "wamid.out-doc"}]})

    def _upload(url, data, mime, filename, headers):
        assert_no_live_graph(url)
        return {"id": "media-pdf"}

    wa.note_customer_window(RAFAEL)
    asyncio.run(wa.reply_in_window(
        RAFAEL,
        "Draft EST-9. Not sent.",
        http_post=_post,
        http_upload=_upload,
        documents=[{"filename": "EST-9.pdf", "data": b"%PDF-1.4 draft", "quote_number": "EST-9"}],
    ))
    messages, _ = get_conversation_messages(RAFAEL)
    outbound = [m for m in messages if m["direction"] == "outbound"]
    assert outbound
    blob = json.dumps(outbound)
    assert "EST-9.pdf" in blob
    assert "EST-9" in blob
    assert "[document:" in outbound[-1]["body"]
    assert outbound[-1]["metadata"]["documents"][0]["doc_id"] == "EST-9"


def test_status_webhook_sets_delivered_and_failed(isolated_whatsapp_edition):
    import asyncio

    log_message(
        RAFAEL,
        "outbound",
        "text",
        body="Draft ready. Not sent.",
        wa_message_id="wamid.track",
        delivery_status="sent",
    )
    delivered = _status_payload("wamid.track", "delivered")
    result = asyncio.run(wa.process_webhook(delivered, _sign(delivered)))
    assert result["statuses_updated"] == 1
    messages, _ = get_conversation_messages(RAFAEL)
    assert messages[0]["delivery_status"] == "delivered"

    failed = _status_payload("wamid.track", "failed", error_code="131047", error_title="Message undeliverable")
    asyncio.run(wa.process_webhook(failed, _sign(failed)))
    messages, _ = get_conversation_messages(RAFAEL)
    assert messages[0]["delivery_status"] == "failed"
    assert messages[0]["error_code"] == "131047"
    assert "undeliverable" in (messages[0]["error_message"] or "").lower()


def test_editions_do_not_share_logs(tmp_path, monkeypatch):
    monkeypatch.setenv("FOUNDER_PIN", FOUNDER_PIN)
    a = tmp_path / "edition-a"
    b = tmp_path / "edition-b"
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(a))
    log_message(RAFAEL, "inbound", "text", body="Rafael only", wa_message_id="wamid.a")
    assert list_conversations()
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(b))
    assert list_conversations() == []
    messages, total = get_conversation_messages(RAFAEL)
    assert total == 0
    assert messages == []


def test_read_api_requires_founder_pin_and_pages(isolated_whatsapp_edition):
    log_message(RAFAEL, "inbound", "text", body="first", wa_message_id="wamid.p1", timestamp="2026-01-01T00:00:00+00:00")
    log_message(RAFAEL, "inbound", "text", body="second install", wa_message_id="wamid.p2", timestamp="2026-01-01T00:01:00+00:00")
    log_message(NELMA, "inbound", "text", body="Nelma hello", wa_message_id="wamid.p3")

    client = _client()
    denied = client.get("/api/v1/whatsapp/chats")
    assert denied.status_code in (403, 503)

    headers = {"X-Founder-Pin": FOUNDER_PIN}
    listed = client.get("/api/v1/whatsapp/chats", headers=headers)
    assert listed.status_code == 200
    labels = {c["display_label"] for c in listed.json()["conversations"]}
    assert "Rafael" in labels
    assert "Nelma" in labels

    page = client.get(
        f"/api/v1/whatsapp/chats/{RAFAEL}/messages",
        params={"limit": 1, "offset": 1},
        headers=headers,
    )
    assert page.status_code == 200
    body = page.json()
    assert body["total"] == 2
    assert len(body["messages"]) == 1
    assert body["messages"][0]["body"] == "second install"

    found = client.get("/api/v1/whatsapp/chats/search", params={"q": "install"}, headers=headers)
    assert found.status_code == 200
    assert any("install" in (m["body"] or "") for m in found.json()["messages"])
    assert FAKE_TOKEN not in found.text


def test_update_delivery_status_ignores_unknown_and_empty():
    assert update_delivery_status("", "delivered") is False
    assert update_delivery_status("missing", "banana") is False


def test_search_and_paging_helpers(isolated_whatsapp_edition):
    for i in range(3):
        log_message(RAFAEL, "inbound", "text", body=f"row {i} drapery", wa_message_id=f"wamid.r{i}")
    page, total = get_conversation_messages(RAFAEL, limit=2, offset=0)
    assert total == 3
    assert len(page) == 2
    hits = search_all_messages("drapery")
    assert len(hits) == 3
    assert search_all_messages("") == []
