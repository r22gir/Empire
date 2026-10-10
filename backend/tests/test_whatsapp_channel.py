"""Mocked WhatsApp Cloud API payloads. No live Graph calls and no secrets."""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import whatsapp as whatsapp_router
from app.services.max import whatsapp_channel as wa
from app.services.max.hermes_phase3 import get_phase3_status
from app.services.max.whatsapp_channel import (
    REQUIRED_ENV,
    WhatsAppSendBlocked,
    channel_status,
    founder_allowlist,
    is_allowlisted,
    note_customer_window,
    process_webhook,
    reply_in_window,
    send_template,
    subscription_challenge,
    verify_signature,
)

FAKE_TOKEN = "test-access-token"
FAKE_SECRET = "test-app-secret"
FAKE_VERIFY = "test-verify-token"


class _GraphResponse:
    def __init__(self, body=None, content=b"", status_code=200):
        self.status_code = status_code
        self.content = content
        self._body = body or {}

    def json(self):
        return self._body


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    for name in REQUIRED_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("WHATSAPP_REPLY_MODE", raising=False)
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.setattr(wa, "_state_path", lambda: tmp_path / "wa-state.json")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path / "edition-data"))
    monkeypatch.setenv("VOICE_DOC_SESSIONS_PATH", str(tmp_path / "voice-sessions.json"))
    monkeypatch.setenv("EMPIRE_BOX_MEMORY_DIR", str(tmp_path / "memory"))
    monkeypatch.setenv("MAX_DRAWINGS_OUTPUT_DIR", str(tmp_path / "drawings"))


def _enable(monkeypatch):
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", FAKE_TOKEN)
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123456")
    monkeypatch.setenv("WHATSAPP_APP_SECRET", FAKE_SECRET)
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", FAKE_VERIFY)


def _sign(body: bytes) -> str:
    digest = hmac.new(FAKE_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _founder() -> str:
    numbers = founder_allowlist()
    assert numbers, "founder allowlist is empty"
    return sorted(numbers)[0]


def _payload(message: dict, sender: str | None = None) -> bytes:
    body = {
        "object": "whatsapp_business_account",
        "entry": [{
            "changes": [{
                "field": "messages",
                "value": {
                    "messages": [{
                        "from": sender or _founder(),
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


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(whatsapp_router.router, prefix="/api/v1")
    return TestClient(app)


def test_status_is_disabled_and_honest_when_unset():
    status = channel_status()
    assert status["enabled"] is False
    assert status["status"] == "disabled"
    assert status["missing"] == list(REQUIRED_ENV)
    assert status["drafts_require_explicit_confirm"] is True
    assert status["reply_mode"] == "voice_text"
    assert status["autonomous_messaging_allowed"] is False
    blob = json.dumps(status)
    assert FAKE_TOKEN not in blob
    assert FAKE_SECRET not in blob
    phase3 = get_phase3_status()
    whatsapp = phase3["extra_channels"]["whatsapp"]
    assert whatsapp["enabled"] is False
    assert whatsapp["status"] == "disabled"
    assert whatsapp["interface_point"] == "/api/v1/whatsapp/webhook"
    assert whatsapp["autonomous_messaging_allowed"] is False


def test_status_enabled_does_not_echo_credentials(monkeypatch):
    _enable(monkeypatch)
    status = channel_status()
    assert status["enabled"] is True
    assert status["status"] == "enabled"
    assert status["missing"] == []
    blob = json.dumps(status)
    assert FAKE_TOKEN not in blob
    assert FAKE_SECRET not in blob
    assert FAKE_VERIFY not in blob


def test_signature_and_verify_token(monkeypatch):
    body = b'{"object":"whatsapp_business_account"}'
    assert verify_signature(body, _sign(body)) is False
    client = _client()
    denied = client.get("/api/v1/whatsapp/webhook", params={
        "hub.mode": "subscribe",
        "hub.verify_token": "anything",
        "hub.challenge": "challenge-1",
    })
    assert denied.status_code == 503
    assert denied.json()["status"] == "disabled"
    assert FAKE_VERIFY not in denied.text

    _enable(monkeypatch)
    assert verify_signature(body, _sign(body)) is True
    assert verify_signature(body, "sha256=deadbeef") is False
    assert verify_signature(body, None) is False
    assert subscription_challenge("subscribe", FAKE_VERIFY, "challenge-1") == "challenge-1"
    assert subscription_challenge("subscribe", "nope", "challenge-1") is None
    bad = client.get("/api/v1/whatsapp/webhook", params={
        "hub.mode": "subscribe",
        "hub.verify_token": "wrong",
        "hub.challenge": "challenge-1",
    })
    assert bad.status_code == 403
    ok = client.get("/api/v1/whatsapp/webhook", params={
        "hub.mode": "subscribe",
        "hub.verify_token": FAKE_VERIFY,
        "hub.challenge": "challenge-1",
    })
    assert ok.status_code == 200
    assert ok.text == "challenge-1"


def test_bad_signature_and_strangers_are_dropped(monkeypatch):
    _enable(monkeypatch)
    client = _client()
    raw = _payload({"type": "text", "text": {"body": "hello"}})
    bad = client.post(
        "/api/v1/whatsapp/webhook",
        content=raw,
        headers={"X-Hub-Signature-256": "sha256=nope", "content-type": "application/json"},
    )
    assert bad.status_code == 403
    assert bad.json()["accepted"] is False

    stranger = _payload({"type": "text", "text": {"body": "hello"}, "id": "wamid.stranger"}, sender="15555550100")
    ignored = client.post(
        "/api/v1/whatsapp/webhook",
        content=stranger,
        headers={"X-Hub-Signature-256": _sign(stranger), "content-type": "application/json"},
    )
    assert ignored.status_code == 200
    row = ignored.json()["results"][0]
    assert row["allowlisted"] is False
    assert row["sent"] is False
    assert is_allowlisted("15555550100") is False
    assert is_allowlisted(_founder()) is True


def test_text_goes_to_max_chat_and_does_not_send(monkeypatch):
    _enable(monkeypatch)
    calls = []

    async def _chat(text, wa_id):
        calls.append((text, wa_id))
        return "Max reply"

    posts = []

    def _post(url, body, headers):
        posts.append(body)
        assert headers.get("Authorization", "").startswith("Bearer ")
        assert FAKE_TOKEN not in json.dumps(body)
        return _GraphResponse({"messages": [{"id": "wamid.out"}]})

    monkeypatch.setattr(wa, "max_chat", _chat)
    raw = _payload({"type": "text", "text": {"body": "What time is the delivery?"}, "id": "wamid.text"})
    import asyncio
    result = asyncio.run(process_webhook(
        raw, _sign(raw), text_handler=wa.default_text_handler, http_post=_post,
    ))
    assert result["sent"] is False
    assert result["results"][0]["route"] == "chat"
    assert result["results"][0]["reply_sent"] is True
    assert calls and calls[0][0] == "What time is the delivery?"
    assert posts[0]["type"] == "text"
    assert posts[0]["to"] == _founder()

    again = asyncio.run(process_webhook(
        raw, _sign(raw), text_handler=wa.default_text_handler, http_post=_post,
    ))
    assert again["results"][0]["duplicate"] is True
    assert len(calls) == 1


def test_voice_note_uses_document_pipeline_and_never_sends(monkeypatch):
    _enable(monkeypatch)
    seen = {}

    async def _voice(audio, mime, wa_id):
        seen["audio"] = audio
        seen["mime"] = mime
        seen["wa_id"] = wa_id
        return "Draft updated. Not sent."

    def _get(url, headers):
        if url.endswith("/media-voice"):
            return _GraphResponse({"url": "https://lookaside.example/voice", "mime_type": "audio/ogg"})
        return _GraphResponse(content=b"OggS-voice")

    posts = []

    def _post(url, body, headers):
        posts.append(body["type"])
        return _GraphResponse({"messages": [{"id": "wamid.out"}]})

    mail = []
    monkeypatch.setattr(
        "app.services.email.sender.send_email",
        lambda *a, **k: mail.append("sent") or True,
    )
    raw = _payload({
        "type": "audio",
        "id": "wamid.voice",
        "audio": {"id": "media-voice", "mime_type": "audio/ogg", "voice": True},
    })
    import asyncio
    result = asyncio.run(process_webhook(
        raw, _sign(raw), voice_handler=_voice, http_get=_get, http_post=_post,
    ))
    assert seen["audio"] == b"OggS-voice"

    async def _ingest(path, **kwargs):
        assert kwargs["channel"] == "whatsapp"
        assert kwargs["session_key"].startswith("whatsapp:")
        return {"handled": True, "sent": False, "reply_text": "Draft updated. Not sent."}

    monkeypatch.setattr("app.services.voice_documents.pipeline.ingest_audio", _ingest)
    direct = asyncio.run(wa.default_voice_handler(b"OggS-voice", "audio/ogg", _founder()))
    assert direct == "Draft updated. Not sent."
    assert result["results"][0]["route"] == "voice_document"
    assert result["results"][0]["sent"] is False
    assert posts == ["text"]
    assert mail == []


def test_photo_builds_a_draft_quote_and_does_not_send(monkeypatch):
    _enable(monkeypatch)
    mail = []
    monkeypatch.setattr(
        "app.services.email.sender.send_email",
        lambda *a, **k: mail.append("sent") or True,
    )

    async def _analyze(image_data, customer_notes=""):
        assert image_data.startswith("data:image/jpeg;base64,")
        return {
            "items": [{
                "type": "window",
                "description": "Living room window",
                "width": 36,
                "height": 60,
            }]
        }

    monkeypatch.setattr(
        "app.services.quote_engine.item_analyzer.analyze_photo_items",
        _analyze,
    )
    import asyncio
    monkeypatch.setattr(wa, "founder_documents", lambda pipeline: ([], ""))
    reply = asyncio.run(wa.default_photo_handler(b"\xff\xd8\xff", "image/jpeg", "living room", _founder()))
    reply_text = reply["text"] if isinstance(reply, dict) else reply
    assert "Not sent" in reply_text
    assert mail == []
    from app.db.database import get_db
    with get_db() as conn:
        row = conn.execute(
            "SELECT quote_number, status, notes, customer_name FROM quotes_v2 ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    assert row[1] == "draft"
    assert "not sent" in (row[2] or "")
    assert "Rafael" not in (row[3] or "")
    assert row[0] in reply_text


def test_quote_text_stays_on_the_draft_and_send_it_does_not_send(monkeypatch):
    _enable(monkeypatch)
    mail = []
    monkeypatch.setattr(
        "app.services.email.sender.send_email",
        lambda *a, **k: mail.append("sent") or True,
    )
    monkeypatch.setattr(
        "app.services.voice_documents.pipeline._remember",
        lambda *a, **k: None,
    )

    async def _chat(text, wa_id):
        raise AssertionError("quote text must stay on the draft")

    monkeypatch.setattr(wa, "max_chat", _chat)
    monkeypatch.setattr(wa, "founder_documents", lambda pipeline: ([], ""))
    import asyncio

    def _shown(reply):
        return reply["text"] if isinstance(reply, dict) else reply

    first = asyncio.run(wa.default_text_handler(
        "Quote for Maggie. Straight bench 48 inches long.",
        _founder(),
    ))
    shown = _shown(first)
    assert "Not sent" in shown or "not emailed" in shown.lower()
    second = _shown(asyncio.run(wa.default_text_handler("send it", _founder())))
    assert mail == []
    assert "blocked" in second.lower() or "not emailed" in second.lower() or "not sent" in second.lower()


def test_outbound_window_and_explicit_confirm(monkeypatch):
    _enable(monkeypatch)
    founder = _founder()
    posts = []

    def _post(url, body, headers):
        posts.append(body["type"])
        return _GraphResponse({"messages": [{"id": "wamid.out"}]})

    import asyncio
    with pytest.raises(WhatsAppSendBlocked):
        asyncio.run(reply_in_window(founder, "hello", http_post=_post))
    with pytest.raises(WhatsAppSendBlocked):
        asyncio.run(send_template(founder, "quote_ready", confirmed=False, http_post=_post))
    assert posts == []

    sent = asyncio.run(send_template(
        founder, "quote_ready", confirmed=True, http_post=_post,
    ))
    assert sent["kind"] == "template"
    assert sent["confirmed"] is True
    assert posts == ["template"]

    note_customer_window(founder)
    session = asyncio.run(reply_in_window(founder, "draft ready", http_post=_post))
    assert session["kind"] == "session"
    assert session["draft_sent"] is False
    assert posts == ["template", "text"]

    client = _client()
    refused = client.post("/api/v1/whatsapp/send", json={
        "to": founder,
        "text": "please send the quote",
        "confirmed": False,
    })
    assert refused.status_code == 403
    assert "explicit confirmation" in refused.json()["detail"]
    old = str(int(time.time()) - 3 * 24 * 3600)
    note_customer_window(founder, old)
    blocked = client.post("/api/v1/whatsapp/send", json={
        "to": founder,
        "text": "please send the quote",
        "confirmed": True,
    })
    assert blocked.status_code == 403
    assert "24 hour" in blocked.json()["detail"]


def _long_reply() -> str:
    lines = ["Draft EST-9. Not sent."]
    lines.extend(f"Item {i}: ${i}.00" for i in range(1, 12))
    lines.append("Total: $66.00")
    return "\n".join(lines)


def test_voice_text_sends_ogg_voice_note_and_summary(monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setenv("WHATSAPP_REPLY_MODE", "voice_text")
    founder = _founder()
    note_customer_window(founder)
    spoken = []
    uploads = []
    posts = []

    async def _synth(text):
        spoken.append(text)
        return b"OggS" + b"\x00" * 80

    def _upload(url, data, mime, filename, headers):
        uploads.append({"mime": mime, "filename": filename, "data": data, "auth": headers.get("Authorization", "")[:7]})
        assert FAKE_TOKEN not in json.dumps({"mime": mime, "filename": filename})
        return {"id": f"media-{len(uploads)}"}

    def _post(url, body, headers):
        posts.append(body)
        assert FAKE_TOKEN not in json.dumps(body)
        return _GraphResponse({"messages": [{"id": "wamid.out"}]})

    import asyncio
    full = _long_reply()
    result = asyncio.run(reply_in_window(
        founder, full, http_post=_post, http_upload=_upload, synthesize=_synth,
    ))
    assert result["voice_sent"] is True
    assert result["voice_fallback"] == ""
    assert result["draft_sent"] is False
    assert spoken == [full]
    assert uploads[0]["mime"] == "audio/ogg"
    assert uploads[0]["data"].startswith(b"OggS")
    assert posts[0]["type"] == "audio"
    assert posts[0]["audio"]["voice"] is True
    assert posts[1]["type"] == "text"
    summary = posts[1]["text"]["body"]
    assert "Total: $66.00" in summary
    assert "Not sent" in summary
    assert len(summary) < len(full)
    assert "Voice note unavailable" not in summary


def test_tts_failure_falls_back_to_text_with_a_note(monkeypatch):
    _enable(monkeypatch)
    founder = _founder()
    note_customer_window(founder)
    uploads = []
    posts = []

    async def _synth(text):
        return None

    def _upload(url, data, mime, filename, headers):
        uploads.append(mime)
        return {"id": "should-not"}

    def _post(url, body, headers):
        posts.append(body)
        return _GraphResponse({"messages": [{"id": "wamid.out"}]})

    import asyncio
    full = _long_reply()
    result = asyncio.run(reply_in_window(
        founder, full, http_post=_post, http_upload=_upload, synthesize=_synth,
    ))
    assert result["voice_sent"] is False
    assert result["voice_fallback"]
    assert uploads == []
    assert [row["type"] for row in posts] == ["text"]
    body = posts[0]["text"]["body"]
    assert body.startswith("Voice note unavailable")
    assert "Text only." in body
    assert "Total: $66.00" in body


def test_text_mode_and_match_skip_voice_unless_the_note_was_voice(monkeypatch):
    _enable(monkeypatch)
    founder = _founder()
    note_customer_window(founder)
    posts = []

    async def _synth(text):
        raise AssertionError("text mode must not call TTS")

    def _post(url, body, headers):
        posts.append(body["type"])
        return _GraphResponse({"messages": [{"id": "wamid.out"}]})

    import asyncio
    monkeypatch.setenv("WHATSAPP_REPLY_MODE", "text")
    text_only = asyncio.run(reply_in_window(
        founder, "Draft ready. Not sent.", http_post=_post, synthesize=_synth,
    ))
    assert text_only["voice_sent"] is False
    assert posts == ["text"]

    monkeypatch.setenv("WHATSAPP_REPLY_MODE", "match")
    asyncio.run(reply_in_window(
        founder, "hello from chat", http_post=_post, synthesize=_synth, inbound_type="text",
    ))
    assert posts == ["text", "text"]

    async def _voice_synth(text):
        return b"OggSvoice"

    def _upload(url, data, mime, filename, headers):
        return {"id": "media-voice"}

    asyncio.run(reply_in_window(
        founder,
        "heard you",
        http_post=_post,
        http_upload=_upload,
        synthesize=_voice_synth,
        inbound_type="audio",
        inbound_voice=True,
    ))
    assert posts[-2:] == ["audio", "text"]


def test_documents_upload_as_pdf(monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setenv("WHATSAPP_REPLY_MODE", "text")
    founder = _founder()
    note_customer_window(founder)
    uploads = []
    posts = []

    def _upload(url, data, mime, filename, headers):
        uploads.append({"mime": mime, "filename": filename, "data": data})
        return {"id": "media-pdf"}

    def _post(url, body, headers):
        posts.append(body)
        return _GraphResponse({"messages": [{"id": "wamid.doc"}]})

    import asyncio
    result = asyncio.run(reply_in_window(
        founder,
        "Draft EST-2. Not sent.",
        http_post=_post,
        http_upload=_upload,
        documents=[{"filename": "EST-2.pdf", "data": b"%PDF-1.4 draft"}],
    ))
    assert result["draft_sent"] is False
    assert uploads[0]["mime"] == "application/pdf"
    assert uploads[0]["filename"] == "EST-2.pdf"
    assert uploads[0]["data"].startswith(b"%PDF")
    assert posts[1]["type"] == "document"
    assert posts[1]["document"]["filename"] == "EST-2.pdf"
    assert posts[1]["document"]["caption"] == "Draft. Not sent."


def test_founder_documents_use_the_quote_pdf_service(monkeypatch):
    def _pdf(quote_id):
        assert quote_id == "q-1"
        return b"%PDF-1.4 quote"

    def _drawing(drawings, output_path):
        Path(output_path).write_bytes(b"%PDF-1.4 drawing")
        return output_path

    monkeypatch.setattr("app.services.quote_pdf_service.generate_quote_pdf", _pdf)
    monkeypatch.setattr("app.services.vision.bench_renderer.drawings_to_pdf", _drawing)
    docs, note = wa.founder_documents({
        "handled": True,
        "quote_id": "q-1",
        "quote_number": "EST-3",
        "drawing": {"svg": "<svg></svg>"},
    })
    kinds = {row["kind"] for row in docs}
    assert kinds == {"quote", "drawing"}
    assert all(row["data"].startswith(b"%PDF") for row in docs)
    assert note == ""
    assert all(row["filename"].endswith(".pdf") for row in docs)


def test_route_is_loaded_on_the_app():
    main_src = Path(__file__).resolve().parents[1].joinpath("app", "main.py").read_text(encoding="utf-8")
    assert 'load_router("app.routers.whatsapp", "/api/v1", ["whatsapp"])' in main_src
    paths = {getattr(route, "path", "") for route in whatsapp_router.router.routes}
    assert "/whatsapp/webhook" in paths
    assert "/whatsapp/status" in paths
    assert "/whatsapp/send" in paths
