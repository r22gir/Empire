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

    # 2026-10-04: voice notes are transcribed first and routed like text. Dictation of a
    # new document joins the voice draft ...
    from app.services.max.stt_service import stt_service

    async def _transcribe(path, language="en"):
        return seen["transcript"]

    def _ingest(text, **kwargs):
        assert kwargs["channel"] == "whatsapp"
        assert kwargs["session_key"].startswith("whatsapp:")
        return {"handled": True, "sent": False, "reply_text": "Draft updated. Not sent."}

    monkeypatch.setattr(stt_service, "transcribe", _transcribe)
    monkeypatch.setattr("app.services.voice_documents.pipeline.ingest_transcript", _ingest)
    monkeypatch.setattr("app.services.voice_documents.session.active_session", lambda key: None)
    seen["transcript"] = "New quote for Marley's, one bench cushion 60 inches by 20 inches"
    direct = asyncio.run(wa.default_voice_handler(b"OggS-voice", "audio/ogg", _founder()))
    assert direct == "Draft updated. Not sent."

    # ... while a greeting or a question about an existing quote goes to Max chat, never intake.
    chats = []

    async def _chat(text, wa_id):
        chats.append(text)
        return "chat reply"

    monkeypatch.setattr(wa, "max_chat", _chat)
    monkeypatch.setattr("app.services.voice_documents.session.active_session", lambda key: object())
    monkeypatch.setattr("app.services.max.quick_replies.direct_reply", lambda *a, **k: None)
    for said in ("Hi", "Can you send me like a voice message, like a status on the last Marley's quote?",
                 "Send me last quote"):
        seen["transcript"] = said
        assert asyncio.run(wa.default_voice_handler(b"OggS-voice", "audio/ogg", _founder())) == "chat reply"
    assert len(chats) == 3
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


def _call_payload(call_event: dict) -> bytes:
    body = {
        "object": "whatsapp_business_account",
        "entry": [{
            "changes": [{
                "field": "calls",
                "value": {
                    "calls": [call_event]
                },
            }]
        }],
    }
    return json.dumps(body).encode()


def test_calling_feature_flag_and_status(monkeypatch):
    _enable(monkeypatch)
    monkeypatch.delenv("WHATSAPP_CALLING_ENABLED", raising=False)
    status = channel_status()
    assert status["calling_enabled"] is False

    monkeypatch.setenv("WHATSAPP_CALLING_ENABLED", "1")
    status = channel_status()
    assert status["calling_enabled"] is True


def test_call_rejected_for_non_allowlisted(monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setenv("WHATSAPP_CALLING_ENABLED", "1")
    client = _client()

    calls_sent = []
    def _mock_post(url, body, headers):
        calls_sent.append({"url": url, "body": body})
        return _GraphResponse({"success": True})

    monkeypatch.setattr("app.services.max.whatsapp_channel._post_graph", _mock_post)

    payload = _call_payload({
        "id": "call-123",
        "from": "19999999999",  # not on allowlist
        "event": "connect",
        "session": {"sdp_type": "offer", "sdp": "v=0\r\no=- 1 1 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\nm=audio 5004 RTP/AVP 111\r\na=rtpmap:111 opus/48000/2\r\n"},
    })

    res = client.post(
        "/api/v1/whatsapp/webhook",
        content=payload,
        headers={"x-hub-signature-256": _sign(payload), "Content-Type": "application/json"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["accepted"] is True
    call_res = next(r for r in data["results"] if r.get("call_id") == "call-123")
    assert call_res["action"] == "rejected"
    assert call_res["reason"] == "not_allowlisted"


def test_call_rejected_when_calling_disabled(monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setenv("WHATSAPP_CALLING_ENABLED", "0")
    client = _client()

    calls_sent = []
    def _mock_post(url, body, headers):
        calls_sent.append({"url": url, "body": body})
        return _GraphResponse({"success": True})

    monkeypatch.setattr("app.services.max.whatsapp_channel._post_graph", _mock_post)

    payload = _call_payload({
        "id": "call-disabled",
        "from": _founder(),
        "event": "connect",
        "session": {"sdp_type": "offer", "sdp": "v=0\r\no=- 1 1 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\nm=audio 5004 RTP/AVP 111\r\na=rtpmap:111 opus/48000/2\r\n"},
    })

    res = client.post(
        "/api/v1/whatsapp/webhook",
        content=payload,
        headers={"x-hub-signature-256": _sign(payload), "Content-Type": "application/json"},
    )
    assert res.status_code == 200
    data = res.json()
    call_res = next(r for r in data["results"] if r.get("call_id") == "call-disabled")
    assert call_res["action"] == "rejected"
    assert call_res["reason"] == "calling_disabled"


class _NoTranscript:
    def __init__(self, *args, **kwargs):
        raise RuntimeError("transcripts disabled in tests")


def test_call_connect_and_terminate_allowlisted(monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setenv("WHATSAPP_CALLING_ENABLED", "1")
    monkeypatch.setenv("XAI_API_KEY", "test-xai-key")
    # Await the full setup inside the request, no ICE wait, no STUN, no transcript writes.
    monkeypatch.setenv("WHATSAPP_CALL_SETUP_INLINE", "1")
    monkeypatch.setenv("WHATSAPP_ACCEPT_WAIT_SECONDS", "0")
    monkeypatch.setenv("WHATSAPP_STUN_SERVER", "none")
    monkeypatch.setattr("app.services.max.voice_transcript.VoiceTranscript", _NoTranscript)
    client = _client()

    posted_calls = []
    async def _mock_post_calls(url, body, headers):
        posted_calls.append({"url": url, "body": body})
        return _GraphResponse({"success": True})

    class MockUpstreamWS:
        def __init__(self):
            self.sent = []
        async def send(self, msg):
            self.sent.append(msg)
        async def close(self):
            pass
        def __aiter__(self):
            return self
        async def __anext__(self):
            # End iteration
            raise StopAsyncIteration

    mock_upstream = MockUpstreamWS()

    # Mock xAI websockets.connect in whatsapp_calling
    async def _mock_connect(*args, **kwargs):
        return mock_upstream

    import websockets
    monkeypatch.setattr(websockets, "connect", _mock_connect)

    import httpx
    orig_post = httpx.AsyncClient.post
    async def _mock_client_post(self, url, *args, **kwargs):
        if "/calls" in str(url):
            body = kwargs.get("json", {})
            posted_calls.append({"url": str(url), "body": body})
            return _GraphResponse({"success": True})
        return await orig_post(self, url, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "post", _mock_client_post)

    valid_offer_sdp = (
        "v=0\r\n"
        "o=- 1495799811084970 1 IN IP4 127.0.0.1\r\n"
        "s=-\r\n"
        "t=0 0\r\n"
        "m=audio 9 RTP/SAVPF 111\r\n"
        "c=IN IP4 127.0.0.1\r\n"
        "a=rtcp:9 IN IP4 127.0.0.1\r\n"
        "a=ice-ufrag:testufrag\r\n"
        "a=ice-pwd:testpasswordtestpassword\r\n"
        "a=fingerprint:sha-256 00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00\r\n"
        "a=setup:actpass\r\n"
        "a=mid:0\r\n"
        "a=sendrecv\r\n"
        "a=rtpmap:111 opus/48000/2\r\n"
        "a=rtcp-mux\r\n"
    )

    payload = _call_payload({
        "id": "call-ok-1",
        "from": _founder(),
        "event": "connect",
        "session": {"sdp_type": "offer", "sdp": valid_offer_sdp},
    })

    res = client.post(
        "/api/v1/whatsapp/webhook",
        content=payload,
        headers={"x-hub-signature-256": _sign(payload), "Content-Type": "application/json"},
    )
    assert res.status_code == 200
    data = res.json()
    call_res = next(r for r in data["results"] if r.get("call_id") == "call-ok-1")
    assert call_res["action"] == "accepted"
    assert "sdp_answer" in call_res
    assert "v=0" in call_res["sdp_answer"]

    # Verify Graph calls were made: pre_accept then accept
    actions = [p["body"].get("action") for p in posted_calls]
    assert "pre_accept" in actions
    assert "accept" in actions

    # Now terminate call via webhook
    term_payload = _call_payload({
        "id": "call-ok-1",
        "from": _founder(),
        "event": "terminate",
    })
    res_term = client.post(
        "/api/v1/whatsapp/webhook",
        content=term_payload,
        headers={"x-hub-signature-256": _sign(term_payload), "Content-Type": "application/json"},
    )
    assert res_term.status_code == 200
    term_data = res_term.json()
    term_res = next(r for r in term_data["results"] if r.get("call_id") == "call-ok-1")
    assert term_res["action"] == "terminated"


@pytest.mark.asyncio
async def test_mid_call_documents_send_pdf(monkeypatch):
    _enable(monkeypatch)
    from app.services.max.whatsapp_calling import WhatsAppVoiceCall

    uploaded = []
    def _mock_upload(data, mime, filename, http_upload=None):
        uploaded.append({"filename": filename, "mime": mime, "data": data})
        return "media-doc-123"

    posted = []
    async def _mock_post(body, http_post=None):
        posted.append(body)
        return {"messages": [{"id": "wamid.doc1"}]}

    monkeypatch.setattr("app.services.max.whatsapp_channel.upload_media", _mock_upload)
    monkeypatch.setattr("app.services.max.whatsapp_channel._post_graph", _mock_post)
    monkeypatch.setattr("app.services.quote_pdf_service.generate_quote_pdf", lambda qid: b"%PDF-1.4 quote")

    call = WhatsAppVoiceCall("call-doc-test", _founder())
    await call._check_and_send_mid_call_documents("get_quote", {
        "success": True,
        "result": {"id": "quote-999", "quote_number": "EST-2026-999"}
    })

    assert len(uploaded) == 1
    assert uploaded[0]["filename"] == "EST-2026-999.pdf"
    assert uploaded[0]["data"] == b"%PDF-1.4 quote"
    assert len(posted) == 1
    assert posted[0]["type"] == "document"
    assert posted[0]["document"]["caption"] == "Draft quote from live voice call. Not sent to client."




# ── 2026-10-04 text fixes: one conversation per sender, Final Docs as PDFs ──

_HUB_DOCS = [
    {"id": "d-draw", "type": "drawing", "title": "Drawing EST-2026-297 · lr ripplefold layered", "version": "rev M",
     "isFinal": True, "client": "Nehal Elrefai", "quoteNumber": "EST-2026-297", "modified": "2026-10-03T00:24:15Z",
     "filename": "EST-2026-297-LR-ripplefold-layered-revM.pdf", "project": "Nehal Elrefai — Phase 1"},
    {"id": "d-photo", "type": "photo", "title": "EST-2026-297.png", "version": "rev M", "isFinal": True,
     "client": "Nehal Elrefai", "modified": "2026-10-03T00:24:16Z", "filename": "EST-2026-297.png"},
    {"id": "d-pres", "type": "presentation", "title": "Presentation EST-2026-297", "version": "rev M",
     "isFinal": True, "client": "Nehal Elrefai", "quoteNumber": "EST-2026-297", "modified": "2026-10-03T00:24:14Z",
     "filename": "EST-2026-297-presentation-revM.pdf"},
    {"id": "d-est", "type": "estimate", "title": "Estimate EST-2026-298", "version": "v1", "isFinal": True,
     "client": "Nehal Elrefai", "quoteNumber": "EST-2026-298", "modified": "2026-10-03T00:02:27Z",
     "filename": "EST-2026-298.pdf"},
    {"id": "d-lb", "type": "estimate", "title": "Estimate EST-2026-200", "version": "v2", "isFinal": True,
     "client": "Lauren Bassett", "quoteNumber": "EST-2026-200", "modified": "2026-09-20T00:00:00Z",
     "filename": "EST-2026-200.pdf"},
]


def _fake_hub(path, params):
    docs = list(_HUB_DOCS)
    if path.endswith("/resolve"):
        terms = [t for t in (params.get("q") or "").lower().split() if t]
        hits = [d for d in docs if d["type"] != "photo" and all(
            t in " ".join(str(v) for v in d.values()).lower() for t in terms)]
        return {"found": bool(hits), "doc": hits[0] if hits else None, "alternatives": hits[1:]}
    if params.get("client"):
        docs = [d for d in docs if params["client"].lower() in d["client"].lower()]
    if params.get("type"):
        docs = [d for d in docs if d["type"] == params["type"]]
    if params.get("quote"):
        docs = [d for d in docs if d.get("quoteNumber") == params["quote"]]
    docs.sort(key=lambda d: d["modified"], reverse=True)
    return {"total": len(docs), "docs": docs[: int(params.get("limit") or 500)],
            "facets": {"clients": sorted({d["client"] for d in _HUB_DOCS})}}


@pytest.fixture
def _docs_hub(monkeypatch, tmp_path):
    from app.services.max import doc_lookup

    aliases = tmp_path / "aliases.json"
    aliases.write_text(json.dumps({"clients": [{"name": "Nehal Elrefai", "aliases": ["Dahlia", "Dhalia"],
                                                "address": "9408 Old Courthouse Rd"}]}))
    monkeypatch.setenv("MAX_CLIENT_ALIASES_PATH", str(aliases))
    monkeypatch.setattr(doc_lookup, "default_hub_get", _fake_hub)
    fetched = []

    def _pdf(doc_id, http_get=None):
        fetched.append(doc_id)
        return b"%PDF-1.4 " + doc_id.encode()

    monkeypatch.setattr(doc_lookup, "fetch_pdf", _pdf)
    return fetched


def test_doc_lookup_aliases_address_and_last_n(_docs_hub):
    from app.services.max.doc_lookup import find_docs

    r = find_docs("Show me dhalias last 2 updated docs here")
    assert r["client"] == "Nehal Elrefai" and r["count"] == 2
    assert [d["doc_id"] for d in r["docs"]] == ["d-draw", "d-pres"]  # newest PDFs, photos skipped
    assert find_docs("docs for 9408 Old Courthouse")["client"] == "Nehal Elrefai"
    assert [d["doc_id"] for d in find_docs("send me Dahlia's estimate pdf here")["docs"]] == ["d-est"]
    assert find_docs("laurne basset estimate")["client"] == "Lauren Bassett"
    miss = find_docs("show me Zorblax final estimate")
    assert miss["found"] is False and miss["docs"] == []


def test_open_final_doc_tool_uses_aliases_and_reports_closest(_docs_hub):
    from app.services.max.tool_executor import _open_final_doc

    ok = _open_final_doc({"query": "Dahlia last 2 updated docs"})
    assert ok.success is True
    assert [d["doc_id"] for d in ok.result["docs"]] == ["d-draw", "d-pres"]


def _wa_text(monkeypatch, texts, *, chat=None):
    """Signed webhooks through process_webhook with Graph mocked. Returns (graph posts, uploads)."""
    _enable(monkeypatch)
    monkeypatch.setenv("WHATSAPP_REPLY_MODE", "text")
    posted, uploaded = [], []

    def _post(url, body, headers):
        posted.append(body)
        return _GraphResponse({"messages": [{"id": f"wamid.out{len(posted)}"}]})

    def _upload(url, data, mime, filename, headers):
        uploaded.append({"filename": filename, "data": data, "mime": mime})
        return _GraphResponse({"id": f"media-{len(uploaded)}"})

    async def _run():
        for i, text in enumerate(texts):
            raw = _payload({"type": "text", "id": f"wamid.t{i}-{time.time()}", "text": {"body": text}})
            await process_webhook(raw, _sign(raw), http_post=_post, http_upload=_upload)

    import asyncio as _asyncio
    _asyncio.run(_run())
    return posted, uploaded


def test_whatsapp_docs_here_then_pdf_here_one_conversation(monkeypatch, _docs_hub):
    posted, uploaded = _wa_text(monkeypatch, ["Show me Dahlia's last 2 updated docs here", "send me the pdf here"])
    docs = [p for p in posted if p["type"] == "document"]
    texts = [p["text"]["body"] for p in posted if p["type"] == "text"]
    assert len(docs) == 4 and len(uploaded) == 4
    assert {d["document"]["filename"] for d in docs} == {
        "EST-2026-297-LR-ripplefold-layered-revM.pdf", "EST-2026-297-presentation-revM.pdf"}
    assert all(u["data"].startswith(b"%PDF") and u["mime"] == "application/pdf" for u in uploaded)
    assert all("empirebox.store" not in t and "/docs/view" not in t for t in texts)
    assert "PDF attached (2)" in texts[0] and "PDF attached (2)" in texts[1]
    conv = wa.whatsapp_conversation(_founder())
    assert len(conv["history"]) == 4  # both exchanges in the same conversation
    assert [d["doc_id"] for d in conv["last_docs"]] == ["d-draw", "d-pres"]


def test_max_chat_keeps_one_conversation_and_attaches_tool_docs(monkeypatch, _docs_hub):
    # app.routers.max.__init__ re-exports `router` (APIRouter), which shadows the
    # submodule name — importlib gets the real module that max_chat imports from.
    import importlib
    router_mod = importlib.import_module("app.routers.max.router")

    seen = []

    async def _fake_chat(request, **kwargs):
        seen.append((request.conversation_id, len(request.history or [])))
        if "zorblax" in request.message.lower():
            results = [{"tool": "open_final_doc", "success": False,
                        "error": 'No saved document matched "Zorblax estimate".',
                        "result": {"closest": [{"client": "Lauren Bassett", "latest": {"title": "Estimate EST-2026-200"}}]}}]
            return router_mod.ChatResponse(response="Here is Zorblax's estimate, opened in the viewer.",
                                       model_used="mock", tool_results=results)
        results = [{"tool": "open_final_doc", "success": True,
                    "result": {"doc_id": "d-est", "title": "Estimate EST-2026-298", "filename": "EST-2026-298.pdf"}}]
        return router_mod.ChatResponse(
            response="Latest estimate: [EST-2026-298](http://studio.empirebox.store/docs/view?id=d-est) [1](/docs/view?id=d-est)",
            model_used="mock", tool_results=results)

    monkeypatch.setattr(router_mod, "_chat_with_max_service", _fake_chat)
    # Keep this test on max_chat: quick_replies would answer "newest estimate for that job"
    # from live quote data and skip the conversation/history path under test.
    async def _no_quick(body):
        return None
    monkeypatch.setattr(wa, "_quick_whatsapp_reply", _no_quick)
    posted, uploaded = _wa_text(monkeypatch, ["What's the newest estimate for that job?", "How about Zorblax?"])
    texts = [p["text"]["body"] for p in posted if p["type"] == "text"]
    assert seen[0][0] == seen[1][0] and seen[0][0].startswith("whatsapp-")
    assert seen[1][1] == 2  # previous exchange passed as history
    assert [p["document"]["filename"] for p in posted if p["type"] == "document"] == ["EST-2026-298.pdf"]
    assert "empirebox.store" not in texts[0] and "/docs/view" not in texts[0] and "EST-2026-298" in texts[0]
    # every lookup failed -> honest reply with closest matches, never "opened in the viewer"
    assert "could not find" in texts[1] and "Lauren Bassett" in texts[1] and "viewer" not in texts[1]


def test_whatsapp_conversation_rolls_over_after_idle(monkeypatch):
    from datetime import datetime, timedelta, timezone

    _enable(monkeypatch)
    t0 = datetime(2026, 10, 4, 21, 0, tzinfo=timezone.utc)
    first = wa.whatsapp_conversation(_founder(), now=t0)["conversation_id"]
    wa.remember_whatsapp_turn(_founder(), "hi", "hello", now=t0)
    assert wa.whatsapp_conversation(_founder(), now=t0 + timedelta(hours=11))["conversation_id"] == first
    later = wa.whatsapp_conversation(_founder(), now=t0 + timedelta(hours=13))["conversation_id"]
    assert later != first


def test_whatsapp_directive_says_here_means_this_chat():
    text = wa.WHATSAPP_DIRECTIVE.lower()
    assert "'here'" in text and "aquí" in text and "not an outbound send" in text
    assert "never offer to email" in text and "studio.empirebox.store" in text
    router_src = Path(__file__).resolve().parents[1].joinpath("app", "routers", "max", "router.py").read_text(encoding="utf-8")
    assert router_src.count("enriched_prompt += WHATSAPP_DIRECTIVE") == 2


def test_strip_studio_links():
    out = wa.strip_studio_links(
        "1. Drawing [1](http://studio.empirebox.store/docs/view?id=abc) and `/docs/view?id=4929d4873b29336f` "
        "see [Presentation](https://studio.empirebox.store/docs/view?id=x).")
    assert "empirebox" not in out and "/docs/view" not in out and "Presentation" in out


# ── 2026-10-04 calling fix: SDP Graph accepts, Meta-style offer handling ──

_META_OFFER = (
    "v=0\r\no=- 7602563789789945080 2 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\na=group:BUNDLE audio\r\n"
    "a=msid-semantic: WMS 6932bc1c\r\na=ice-lite\r\nm=audio 40012 UDP/TLS/RTP/SAVPF 111 126\r\n"
    "c=IN IP4 31.13.65.60\r\na=rtcp:9 IN IP4 0.0.0.0\r\n"
    "a=candidate:1972637320 1 udp 2113937151 31.13.65.60 40012 typ host generation 0 network-cost 50 ufrag 6k2qP1R6kBfI/2\r\n"
    "a=ice-ufrag:6k2qP1R6kBfI/2\r\na=ice-pwd:UApvJw3NcwFRDvIMKdM0vWCdlXah25E9\r\n"
    "a=fingerprint:sha-256 1B:B6:6B:40:A5:0B:8C:75:0D:8C:CB:90:2F:99:74:1E:26:45:AE:AF:45:C1:51:60:8F:73:C9:2D:10:6D:8A:88\r\n"
    "a=setup:actpass\r\na=mid:audio\r\na=sendrecv\r\na=rtcp-mux\r\na=rtpmap:111 opus/48000/2\r\n"
    "a=fmtp:111 minptime=10;useinbandfec=1\r\na=rtpmap:126 telephone-event/8000\r\na=ssrc:4208138518 cname:gAXq2V9TKltrnapv\r\n"
)


def test_call_answer_is_graph_acceptable(monkeypatch):
    """Graph rejects any non-sha-256 fingerprint (subcode 2494010); answer must be setup:active,
    sendrecv Opus with candidates; Meta's ICE-lite offer gets end-of-candidates."""
    import asyncio as _asyncio
    from aiortc import RTCConfiguration, RTCPeerConnection, RTCSessionDescription
    from aiortc.mediastreams import AudioStreamTrack
    from app.services.max import whatsapp_calling as wc

    monkeypatch.setenv("WHATSAPP_STUN_SERVER", "none")
    prepared = wc.prepare_offer(_META_OFFER)
    assert "a=end-of-candidates" in prepared

    async def _answer():
        wc.install_host_filter()
        pc = RTCPeerConnection(RTCConfiguration(iceServers=wc.get_ice_servers()))
        pc.addTrack(AudioStreamTrack())
        await pc.setRemoteDescription(RTCSessionDescription(sdp=prepared, type="offer"))
        await pc.setLocalDescription(await pc.createAnswer())
        raw = pc.localDescription.sdp
        controlling = pc.getTransceivers()[0].receiver.transport.transport._connection.ice_controlling
        await pc.close()
        return raw, controlling

    raw, controlling = _asyncio.run(_answer())
    assert "a=fingerprint:sha-512" in raw  # aiortc's default, which Graph refuses
    answer = wc.whatsapp_sdp(raw)
    assert wc.summarize_sdp(answer)["fingerprint_algos"] == ["sha-256"]
    assert "a=setup:active" in answer and "a=sendrecv" in answer
    assert controlling is True  # Meta is ICE-lite, we nominate
    problems = wc.answer_problems(answer)
    assert problems in ([], ["no ICE candidates"])  # CI boxes may have no usable interface
