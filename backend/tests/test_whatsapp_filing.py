"""WhatsApp media store, job filing, export. Mocks only."""
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
from app.services.max.doc_lookup import probe_job_text, resolve_job_folder
from app.services.max.whatsapp_log import (
    JOB_ASK_TEXT,
    consume_job_answer,
    conversation_copy_text,
    conversation_export_pdf,
    file_into_job,
    get_conversation_messages,
    get_pending_filings,
    inbox_dir,
    jobs_root,
    media_dir,
    prepare_inbound_attachment,
    refile_attachment,
    store_edition_media,
    unique_dest,
)

pytest_plugins = ["tests._live_data_guard"]

from tests._live_data_guard import assert_isolated_env

FAKE_TOKEN = "test-access-token-secret"
FAKE_SECRET = "test-app-secret"
FAKE_VERIFY = "test-verify-token"
FOUNDER_PIN = "test-founder-pin"
RAFAEL = "12022996975"


class _GraphResponse:
    def __init__(self, body=None, content=b"", status_code=200):
        self.status_code = status_code
        self.content = content
        self._body = body or {}

    def json(self):
        return self._body


@pytest.fixture(autouse=True)
def _isolate(monkeypatch, tmp_path, isolated_whatsapp_edition):
    monkeypatch.setattr(wa, "_state_path", lambda: tmp_path / "wa-state.json")
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", FAKE_TOKEN)
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123456")
    monkeypatch.setenv("WHATSAPP_APP_SECRET", FAKE_SECRET)
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", FAKE_VERIFY)
    monkeypatch.setenv("WHATSAPP_REPLY_MODE", "text")
    assert_isolated_env()


def _sign(body: bytes) -> str:
    return "sha256=" + hmac.new(FAKE_SECRET.encode(), body, hashlib.sha256).hexdigest()


def _payload(message: dict, sender: str = RAFAEL) -> bytes:
    return json.dumps({
        "object": "whatsapp_business_account",
        "entry": [{"changes": [{"field": "messages", "value": {
            "messages": [{
                "from": sender,
                "id": message.get("id") or "wamid.1",
                "timestamp": message.get("timestamp") or str(int(time.time())),
                "type": message["type"],
                **{k: v for k, v in message.items() if k not in {"id", "timestamp", "type"}},
            }]
        }}]}],
    }).encode()


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(whatsapp_router.router, prefix="/api/v1")
    return TestClient(app)


def test_doc_lookup_unique_ambiguous_unknown():
    assert resolve_job_folder("photo for Maggie")["slug"] == "maggie-frolich"
    assert probe_job_text("Maggie and Willard")["status"] == "ambiguous"
    assert resolve_job_folder("Maggie and Willard") is None
    assert resolve_job_folder("random caption") is None


def test_never_overwrite_uses_timestamp_suffix(isolated_whatsapp_edition, tmp_path):
    folder = tmp_path / "dup"
    first = unique_dest(folder, "site.jpg")
    first.write_bytes(b"one")
    second = unique_dest(folder, "site.jpg")
    assert second != first
    second.write_bytes(b"two")
    assert first.read_bytes() == b"one"


def test_size_cap_skips_store(isolated_whatsapp_edition, monkeypatch):
    monkeypatch.setenv("WHATSAPP_MAX_ATTACHMENT_SIZE_BYTES", "8")
    stored = store_edition_media(b"0123456789", "big.jpg", "image/jpeg", "image")
    assert stored["skipped"] is True
    assert stored["local_path"] == ""


def test_files_named_client_into_jobs(isolated_whatsapp_edition):
    rec = prepare_inbound_attachment(
        b"\xff\xd8photo",
        filename="site.jpg",
        mime_type="image/jpeg",
        media_type="image",
        wa_id=RAFAEL,
        hint_text="Maggie porch",
    )
    assert rec["filing_status"] == "filed"
    assert rec["job_slug"] == "maggie-frolich"
    assert Path(rec["filed_path"]).is_file()
    assert "photos" in rec["filed_path"]
    assert Path(rec["local_path"]).is_file()
    assert str(media_dir()) in rec["local_path"]


def test_ambiguous_parks_inbox_and_asks(isolated_whatsapp_edition, monkeypatch):
    import asyncio

    posts = []

    def _post(url, body, headers):
        posts.append(body)
        return _GraphResponse({"messages": [{"id": "wamid.out"}]})

    def _get(url, headers):
        if str(url).endswith("/media-amb"):
            return _GraphResponse({"url": "https://example.test/img", "mime_type": "image/jpeg"})
        return _GraphResponse(content=b"\xff\xd8img")

    async def _photo(image, mime, caption, wa_id):
        return "Photo draft. Not sent."

    raw = _payload({
        "type": "image",
        "id": "wamid.amb",
        "image": {"id": "media-amb", "mime_type": "image/jpeg", "caption": "Maggie and Willard both?"},
    })
    result = asyncio.run(wa.process_webhook(
        raw, _sign(raw), photo_handler=_photo, http_get=_get, http_post=_post,
    ))
    assert result["results"][0]["reply_sent"] is True
    sent = posts[0]["text"]["body"]
    assert JOB_ASK_TEXT in sent
    messages, _ = get_conversation_messages(RAFAEL)
    inbound = [m for m in messages if m["direction"] == "inbound"][0]
    att = inbound["attachments"][0]
    assert att["filing_status"] == "inbox"
    assert Path(inbox_dir()).is_dir()
    assert get_pending_filings(RAFAEL)


def test_active_job_used_when_caption_empty(isolated_whatsapp_edition):
    prepare_inbound_attachment(
        b"aaa",
        filename="one.jpg",
        mime_type="image/jpeg",
        media_type="image",
        wa_id=RAFAEL,
        hint_text="for Maggie",
    )
    rec = prepare_inbound_attachment(
        b"bbb",
        filename="two.jpg",
        mime_type="image/jpeg",
        media_type="image",
        wa_id=RAFAEL,
        hint_text="",
    )
    assert rec["job_slug"] == "maggie-frolich"
    assert rec["filing_status"] == "filed"


def test_job_answer_files_parked_attachment(isolated_whatsapp_edition, monkeypatch):
    import asyncio

    def _post(url, body, headers):
        return _GraphResponse({"messages": [{"id": "wamid.out"}]})

    def _get(url, headers):
        if str(url).endswith("/media-x"):
            return _GraphResponse({"url": "https://example.test/x", "mime_type": "application/pdf"})
        return _GraphResponse(content=b"%PDF-x")

    raw = _payload({
        "type": "document",
        "id": "wamid.park",
        "document": {"id": "media-x", "filename": "notes.pdf", "caption": ""},
    })
    asyncio.run(wa.process_webhook(raw, _sign(raw), http_get=_get, http_post=_post))
    assert get_pending_filings(RAFAEL)
    answered = consume_job_answer(RAFAEL, "file that under McLean")
    assert answered["status"] == "filed"
    assert answered["job"]["slug"] == "mclean-residence"
    messages, _ = get_conversation_messages(RAFAEL)
    att = messages[0]["attachments"][0]
    assert att["job_slug"] == "mclean-residence"
    assert att["filing_status"] == "filed"
    assert "received" in (att.get("filed_path") or "")
    assert get_pending_filings(RAFAEL) == []


def test_refile_and_export_api(isolated_whatsapp_edition):
    rec = prepare_inbound_attachment(
        b"pdf-bytes",
        filename="scan.pdf",
        mime_type="application/pdf",
        media_type="document",
        wa_id=RAFAEL,
        hint_text="",
    )
    from app.services.max.whatsapp_log import log_message, last_attachment_ids

    mid = log_message(RAFAEL, "inbound", "document", body="[document: scan.pdf]", attachments=[rec])
    att_id = last_attachment_ids(mid)[0]["id"]
    moved = refile_attachment(att_id, "willard-hotel")
    assert moved["job_slug"] == "willard-hotel"
    assert Path(moved["filed_path"]).is_file()

    client = _client()
    headers = {"X-Founder-Pin": FOUNDER_PIN}
    media = client.get(f"/api/v1/whatsapp/media/{att_id}", headers=headers)
    assert media.status_code == 200
    assert media.content == b"pdf-bytes"

    denied = client.get(f"/api/v1/whatsapp/media/{att_id}")
    assert denied.status_code in (403, 503)

    jobs = client.get("/api/v1/whatsapp/jobs", headers=headers)
    assert jobs.status_code == 200
    slugs = {j["slug"] for j in jobs.json()["jobs"]}
    assert "maggie-frolich" in slugs

    copied = client.get(f"/api/v1/whatsapp/chats/{RAFAEL}/copy", headers=headers)
    assert copied.status_code == 200
    assert "scan.pdf" in copied.json()["text"]

    exported = client.get(f"/api/v1/whatsapp/chats/{RAFAEL}/export", headers=headers)
    assert exported.status_code == 200
    assert exported.content.startswith(b"%PDF")
    assert FAKE_TOKEN not in exported.text

    again = client.post(
        f"/api/v1/whatsapp/attachments/{att_id}/refile",
        headers=headers,
        json={"job_slug": "maggie-frolich"},
    )
    assert again.status_code == 200
    assert again.json()["job_slug"] == "maggie-frolich"


def test_export_helpers_redact_secrets(isolated_whatsapp_edition, monkeypatch):
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", FAKE_TOKEN)
    from app.services.max.whatsapp_log import log_message

    log_message(RAFAEL, "inbound", "text", body=f"Bearer {FAKE_TOKEN}")
    text = conversation_copy_text(RAFAEL)
    assert FAKE_TOKEN not in text
    pdf = conversation_export_pdf(RAFAEL)
    assert pdf.startswith(b"%PDF")
    assert FAKE_TOKEN.encode() not in pdf


def test_file_into_job_uses_received_for_docs(isolated_whatsapp_edition):
    path = file_into_job(b"abc", "plan.pdf", "document", "maggie-frolich")
    assert "/received/" in path.replace("\\", "/")
    assert Path(path).read_bytes() == b"abc"
    assert str(jobs_root()) in path
