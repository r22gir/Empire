"""WhatsApp Cloud API with mocked Meta payloads. No live token is used."""
from __future__ import annotations

import hashlib
import hmac
import json
import time

import asyncio
from pathlib import Path


def _sign(body: bytes, secret: str = "test-secret") -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return "sha256=" + digest


def _ready(monkeypatch, tmp_path, edition: str = "amp"):
    monkeypatch.setenv("EMPIRE_EDITION", edition)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("VOICE_DRAFTS_DB", str(tmp_path / "voice.db"))
    monkeypatch.setenv("WHATSAPP_STATE_DB", str(tmp_path / "wa.db"))
    monkeypatch.setenv("PHOTOS_DB", str(tmp_path / "photos.db"))
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "5551234")
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "test-secret")
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "verify-me")
    monkeypatch.setenv("WHATSAPP_OWNER_NUMBERS", "+57 300 111 2233")
    monkeypatch.setenv("WHATSAPP_APPROVED_TEMPLATES", "aviso_borrador")


def _payload(message: dict, phone_id: str = "5551234") -> bytes:
    return json.dumps({
        "object": "whatsapp_business_account",
        "entry": [{"changes": [{"value": {"metadata": {"phone_number_id": phone_id}, "messages": [message]}}]}],
    }).encode("utf-8")


def _text(body: str, message_id: str = "wamid.1") -> dict:
    return {
        "from": "573001112233",
        "id": message_id,
        "timestamp": str(int(time.time())),
        "type": "text",
        "text": {"body": body},
    }


def test_status_is_off_until_env_is_complete(monkeypatch):
    from app.services.whatsapp_cloud import channel_status

    for name in (
        "WHATSAPP_ACCESS_TOKEN",
        "WHATSAPP_PHONE_NUMBER_ID",
        "WHATSAPP_APP_SECRET",
        "WHATSAPP_VERIFY_TOKEN",
        "WHATSAPP_OWNER_NUMBERS",
    ):
        monkeypatch.delenv(name, raising=False)
    status = channel_status()
    assert status["enabled"] is False
    assert status["status"] == "disabled"
    assert status["webhook_path"] == "/api/v1/whatsapp/webhook"
    assert "test-token" not in json.dumps(status)


def test_owner_text_voice_photo_and_confirmed_pdf(monkeypatch, tmp_path):
    _ready(monkeypatch, tmp_path, "maxine")
    monkeypatch.setenv("WHATSAPP_REPLY_MODE", "text")
    from app.services import whatsapp_cloud as wa
    from app.services.instance_files import photo_timeline
    from app.services.voice_doc.store import get_draft

    calls = []

    def fake(method, url, token="", body=None, headers=None):
        calls.append({"method": method, "url": url, "token": token, "body": body or b""})
        assert token == "test-token"
        if url.endswith("/media-audio"):
            return 200, b'{"url":"https://lookaside.example/audio"}'
        if url == "https://lookaside.example/audio":
            return 200, b"OggS"
        if url.endswith("/media-img"):
            return 200, b'{"url":"https://lookaside.example/img"}'
        if url == "https://lookaside.example/img":
            return 200, b"jpeg"
        if url.endswith("/media") and method == "POST":
            return 200, b'{"id":"media-pdf"}'
        if url.endswith("/messages"):
            return 200, b'{"messages":[{"id":"wamid.out"}]}'
        raise AssertionError(url)

    monkeypatch.setattr(wa, "graph_request", fake)
    quote = _payload(_text("Cotiza el curso de liderazgo para Ana Gómez, precio 1500000. listo", "wamid.quote"))
    first = wa.handle_webhook(quote, _sign(quote))
    assert first["http_status"] == 200
    assert first["processed"] == 1
    assert first["edition"] == "maxine"
    assert all(b'"type": "document"' not in call["body"] and b'"document"' not in call["body"] for call in calls)
    status = wa.channel_status()
    blob = json.dumps(status)
    assert "test-token" not in blob
    assert "test-secret" not in blob
    assert status["enabled"] is True
    assert status["edition"] == "maxine"
    assert status["phone_number_id_last4"] == "1234"

    voice = _payload({
        "from": "573001112233",
        "id": "wamid.voice",
        "timestamp": str(int(time.time())),
        "type": "audio",
        "audio": {"id": "media-audio", "mime_type": "audio/ogg"},
    })
    heard = wa.handle_webhook(voice, _sign(voice), transcribe=lambda _path: "Nota de voz recibida")
    assert heard["processed"] == 1
    assert any(call["url"].endswith("/media-audio") for call in calls)

    photo = _payload({
        "from": "573001112233",
        "id": "wamid.photo",
        "timestamp": str(int(time.time())),
        "type": "image",
        "image": {"id": "media-img", "caption": "proyecto Portal lote 12 etapa cimentacion"},
    })
    saved = wa.handle_webhook(photo, _sign(photo))
    assert saved["processed"] == 1
    timeline = photo_timeline("Portal")
    assert timeline[0]["source"] == "whatsapp"
    assert timeline[0]["lot"] == "12"
    assert timeline[0]["stage"] == "cimentacion"

    before = len(calls)
    send = _payload(_text("envía el borrador", "wamid.send"))
    delivered = wa.handle_webhook(send, _sign(send))
    assert delivered["document"] is True
    document_calls = [call for call in calls[before:] if b'"document"' in call["body"]]
    assert document_calls
    draft = get_draft(delivered["draft_id"])
    assert draft["sent"] is False

    again = wa.handle_webhook(send, _sign(send))
    assert again["processed"] == 0


def _graph(calls):
    def fake(method, url, token="", body=None, headers=None):
        calls.append({"method": method, "url": url, "token": token, "body": body or b"", "headers": headers or {}})
        assert token == "test-token"
        payload = body or b""
        if method == "POST" and url.endswith("/media"):
            if b"audio/ogg" in payload:
                assert b"OggS" in payload
                return 200, b'{"id":"media-voice"}'
            return 200, b'{"id":"media-pdf"}'
        if url.endswith("/messages"):
            return 200, b'{"messages":[{"id":"wamid.out"}]}'
        raise AssertionError(url)

    return fake


def test_default_reply_is_ogg_voice_plus_summary(monkeypatch, tmp_path):
    _ready(monkeypatch, tmp_path, "amp")
    monkeypatch.delenv("WHATSAPP_REPLY_MODE", raising=False)
    from app.services import whatsapp_cloud as wa

    calls = []
    spoken = []

    def synth(text, language):
        spoken.append((text, language))
        return b"OggS" + b"o" * 80

    monkeypatch.setattr(wa, "graph_request", _graph(calls))
    wa.remember_inbound("573001112233", int(time.time()))
    full = ("El borrador de la cotización ya está listo y falta tu confirmación. " * 8).strip()
    sent = wa.send_reply("573001112233", full, now=int(time.time()), synthesize=synth)
    assert wa.reply_mode() == "voice_text"
    assert sent["voice"] is True
    assert sent["fallback"] is False
    assert sent["language"] == "es-CO"
    assert spoken == [(full, "es-CO")]
    audio = [call for call in calls if b'"type": "audio"' in call["body"]]
    texts = [call for call in calls if b'"type": "text"' in call["body"]]
    assert len(audio) == 1
    assert b'"voice": true' in audio[0]["body"]
    assert len(texts) == 1
    assert len(texts[0]["body"]) < len(full)
    assert "cotizaci" in texts[0]["body"].decode("utf-8")
    monkeypatch.setenv("EMPIRE_EDITION", "workroom")
    assert wa.reply_language() == "en"


def test_text_mode_and_match_follow_the_inbound_kind(monkeypatch, tmp_path):
    _ready(monkeypatch, tmp_path, "maxine")
    from app.services import whatsapp_cloud as wa

    calls = []
    monkeypatch.setattr(wa, "graph_request", _graph(calls))
    now = int(time.time())
    wa.remember_inbound("573001112233", now)
    monkeypatch.setenv("WHATSAPP_REPLY_MODE", "text")

    def unused(_text, _language):
        raise AssertionError("text mode must not call TTS")

    quiet = wa.send_reply("573001112233", "Solo texto.", now=now, synthesize=unused)
    assert quiet["voice"] is False
    assert quiet["fallback"] is False
    assert b'"type": "audio"' not in calls[-1]["body"]
    assert "Solo texto." in calls[-1]["body"].decode("utf-8")

    monkeypatch.setenv("WHATSAPP_REPLY_MODE", "match")
    calls.clear()
    typed = wa.send_reply("573001112233", "Respuesta escrita.", now=now, inbound_kind="text", synthesize=unused)
    assert typed["voice"] is False
    assert calls and b'"type": "text"' in calls[-1]["body"]

    def synth(text, language):
        assert language == "es-CO"
        assert text == "Respuesta hablada."
        return b"OggS" + b"v" * 80

    heard = wa.send_reply("573001112233", "Respuesta hablada.", now=now, inbound_kind="audio", synthesize=synth)
    assert heard["voice"] is True
    assert any(b'"type": "audio"' in call["body"] for call in calls)


def test_tts_failure_falls_back_to_text_with_a_note(monkeypatch, tmp_path):
    _ready(monkeypatch, tmp_path, "amp")
    monkeypatch.setenv("WHATSAPP_REPLY_MODE", "voice_text")
    from app.services import whatsapp_cloud as wa

    calls = []
    monkeypatch.setattr(wa, "graph_request", _graph(calls))
    now = int(time.time())
    wa.remember_inbound("573001112233", now)

    def broken(_text, _language):
        return None

    sent = wa.send_reply("573001112233", "El detalle completo del borrador.", now=now, synthesize=broken)
    assert sent["voice"] is False
    assert sent["fallback"] is True
    body = b"".join(call["body"] for call in calls)
    assert b'"type": "audio"' not in body
    assert "nota de voz" in body.decode("utf-8")
    assert "El detalle completo del borrador." in body.decode("utf-8")
    assert "test-token" not in body.decode("utf-8")


def test_rejects_bad_signature_strangers_and_other_numbers(monkeypatch, tmp_path):
    _ready(monkeypatch, tmp_path, "amp")
    from app.services import whatsapp_cloud as wa

    def fail(*_args, **_kwargs):
        raise AssertionError("Meta was called")

    monkeypatch.setattr(wa, "graph_request", fail)
    body = _payload(_text("hola", "wamid.no"))
    assert wa.handle_webhook(body, "sha256=dead")["http_status"] == 403
    stranger = _payload(_text("hola", "wamid.stranger") | {"from": "19995550100"})
    # dict merge order: _text already has from, the | override works if we rebuild
    stranger = _payload({**_text("hola", "wamid.stranger"), "from": "19995550100"})
    ignored = wa.handle_webhook(stranger, _sign(stranger))
    assert ignored["ignored"] == 1
    assert ignored["processed"] == 0
    other = _payload(_text("hola", "wamid.other"), phone_id="9990000")
    skipped = wa.handle_webhook(other, _sign(other))
    assert skipped["processed"] == 0


def test_service_window_and_approved_templates(monkeypatch, tmp_path):
    _ready(monkeypatch, tmp_path)
    from app.services import whatsapp_cloud as wa

    calls = []

    def fake(method, url, token="", body=None, headers=None):
        calls.append(body or b"")
        return 200, b'{"messages":[{"id":"wamid.tpl"}]}'

    monkeypatch.setattr(wa, "graph_request", fake)
    wa.remember_inbound("573001112233", int(time.time()) - (25 * 60 * 60))
    refused = wa.send_session_text("573001112233", "hola", now=int(time.time()))
    assert refused["sent"] is False
    assert calls == []
    blocked = wa.send_template("573001112233", "not_approved")
    assert blocked["sent"] is False
    assert calls == []
    sent = wa.send_template("573001112233", "aviso_borrador")
    assert sent["sent"] is True
    assert b"aviso_borrador" in calls[0]
    stranger = wa.send_template("19995550100", "aviso_borrador")
    assert stranger["sent"] is False


class _Request:
    def __init__(self, params=None, body=b"", headers=None):
        self.query_params = params or {}
        self._body = body
        self.headers = headers or {}

    async def body(self):
        return self._body


def test_webhook_verify_and_disabled_route(monkeypatch):
    from app.routers import whatsapp as routes

    for name in (
        "WHATSAPP_ACCESS_TOKEN",
        "WHATSAPP_PHONE_NUMBER_ID",
        "WHATSAPP_APP_SECRET",
        "WHATSAPP_VERIFY_TOKEN",
    ):
        monkeypatch.delenv(name, raising=False)
    off = asyncio.run(routes.whatsapp_inbound(_Request(body=b"{}")))
    assert off.status_code == 503
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "verify-me")
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "5551234")
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "test-secret")
    ok = routes.whatsapp_verify(_Request({
        "hub.mode": "subscribe",
        "hub.verify_token": "verify-me",
        "hub.challenge": "challenge-123",
    }))
    assert ok.status_code == 200
    assert ok.body == b"challenge-123"
    bad = routes.whatsapp_verify(_Request({
        "hub.mode": "subscribe",
        "hub.verify_token": "nope",
        "hub.challenge": "challenge-123",
    }))
    assert bad.status_code == 403
    status = routes.whatsapp_status()
    assert "test-token" not in json.dumps(status)
    assert "test-secret" not in json.dumps(status)
    mounted = Path(__file__).resolve().parents[1].joinpath("app/main.py").read_text(encoding="utf-8")
    assert 'load_router("app.routers.whatsapp", "/api/v1", ["whatsapp"])' in mounted
