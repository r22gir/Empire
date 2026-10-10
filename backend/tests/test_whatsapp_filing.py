"""WhatsApp media store, job filing, export. Mocks only."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import whatsapp as whatsapp_router
from app.services.max import whatsapp_channel as wa
from app.services.max.doc_lookup import probe_job_text, resolve_job_folder, suggest_jobs
from app.services.max.whatsapp_channel import parse_inbound
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
    return _payloads([message], sender=sender)


def _payloads(messages: list[dict], sender: str = RAFAEL) -> bytes:
    packed = []
    now = int(time.time())
    for i, message in enumerate(messages):
        packed.append({
            "from": sender,
            "id": message.get("id") or f"wamid.{i+1}",
            "timestamp": message.get("timestamp") or str(now),
            "type": message["type"],
            **{k: v for k, v in message.items() if k not in {"id", "timestamp", "type"}},
        })
    return json.dumps({
        "object": "whatsapp_business_account",
        "entry": [{"changes": [{"field": "messages", "value": {"messages": packed}}]}],
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
    assert result["results"][0]["route"] == "file_photo"
    assert not any("Photo draft" in ((p.get("text") or {}).get("body") or "") for p in posts)
    assert any(r.get("route") == "file_photo_batch" and r.get("reply_sent") for r in result["results"])
    sent = posts[0]["text"]["body"]
    assert "Which job" in sent or "Closest" in sent or "Maggie" in sent
    messages, _ = get_conversation_messages(RAFAEL)
    inbound = [m for m in messages if m["direction"] == "inbound"][0]
    att = inbound["attachments"][0]
    assert att["filing_status"] == "inbox"
    assert Path(inbox_dir()).is_dir()
    assert get_pending_filings(RAFAEL)


def test_unnamed_text_never_files_into_sticky_active_job(isolated_whatsapp_edition):
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
    assert rec["job_slug"] == ""
    assert rec["filing_status"] == "inbox"
    assert rec["needs_job_ask"] is True


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


def test_job_answer_ignored_until_ask_then_skip(isolated_whatsapp_edition):
    rec = prepare_inbound_attachment(
        b"parked",
        filename="scan.pdf",
        mime_type="application/pdf",
        media_type="document",
        wa_id=RAFAEL,
        hint_text="",
    )
    from app.services.max.whatsapp_log import (
        finalize_photo_batch,
        last_attachment_ids,
        log_message,
        record_media_batch,
        set_pending_filings,
    )

    mid = log_message(RAFAEL, "inbound", "document", body="[document: scan.pdf]", attachments=[rec])
    att_id = last_attachment_ids(mid)[0]["id"]
    set_pending_filings(RAFAEL, [att_id])
    record_media_batch(RAFAEL, [att_id], "")
    assert consume_job_answer(RAFAEL, "how's the weather today") is None
    assert consume_job_answer(RAFAEL, "hello") is None
    assert get_pending_filings(RAFAEL) == [att_id]
    asked = finalize_photo_batch(RAFAEL, force_ask=True)
    assert asked and asked["status"] == "need_job"
    assert consume_job_answer(RAFAEL, "how's the weather today") is None
    skipped = consume_job_answer(RAFAEL, "skip")
    assert skipped["status"] == "skipped"
    assert get_pending_filings(RAFAEL) == []


def test_job_answer_timeout_falls_through(isolated_whatsapp_edition, monkeypatch):
    from datetime import datetime, timedelta, timezone

    rec = prepare_inbound_attachment(
        b"old",
        filename="old.pdf",
        mime_type="application/pdf",
        media_type="document",
        wa_id=RAFAEL,
        hint_text="",
    )
    from app.services.max.whatsapp_log import (
        _get_conn,
        _lock,
        init_db,
        last_attachment_ids,
        log_message,
        set_pending_filings,
    )

    mid = log_message(RAFAEL, "inbound", "document", body="[document: old.pdf]", attachments=[rec])
    att_id = last_attachment_ids(mid)[0]["id"]
    set_pending_filings(RAFAEL, [att_id])
    stale = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    init_db()
    with _lock:
        conn = _get_conn()
        try:
            conn.execute(
                "UPDATE whatsapp_pending_filings SET asked_at = ? WHERE wa_id = ?",
                (stale, RAFAEL),
            )
            conn.commit()
        finally:
            conn.close()
    monkeypatch.setenv("WHATSAPP_JOB_ANSWER_TIMEOUT_SECONDS", "60")
    assert consume_job_answer(RAFAEL, "hello Max") is None
    assert get_pending_filings(RAFAEL) == []


def test_refile_rejects_traversal_and_unknown_folders(isolated_whatsapp_edition):
    rec = prepare_inbound_attachment(
        b"pdf",
        filename="scan.pdf",
        mime_type="application/pdf",
        media_type="document",
        wa_id=RAFAEL,
        hint_text="",
    )
    from app.services.max.whatsapp_log import last_attachment_ids, log_message

    mid = log_message(RAFAEL, "inbound", "document", body="[document: scan.pdf]", attachments=[rec])
    att_id = last_attachment_ids(mid)[0]["id"]
    with pytest.raises(ValueError):
        refile_attachment(att_id, "../etc")
    with pytest.raises(ValueError):
        refile_attachment(att_id, "brand-new-arbitrary")


def test_media_serve_never_renders_html_or_svg(isolated_whatsapp_edition):
    rec = store_edition_media(b"<svg xmlns='http://www.w3.org/2000/svg'></svg>", "evil.svg", "image/svg+xml", "document")
    from app.services.max.whatsapp_log import last_attachment_ids, log_message

    mid = log_message(RAFAEL, "inbound", "document", body="[document: evil.svg]", attachments=[rec])
    att_id = last_attachment_ids(mid)[0]["id"]
    client = _client()
    res = client.get(f"/api/v1/whatsapp/media/{att_id}", headers={"X-Founder-Pin": FOUNDER_PIN})
    assert res.status_code == 200
    assert res.headers.get("content-type", "").startswith("application/octet-stream")
    assert res.headers.get("x-content-type-options") == "nosniff"
    assert "attachment" in (res.headers.get("content-disposition") or "")


def test_founder_pin_failures_are_rate_limited(isolated_whatsapp_edition):
    client = _client()
    headers = {"X-Founder-Pin": "wrong-pin", "X-Forwarded-For": "203.0.113.50"}
    last = None
    for _ in range(9):
        last = client.get("/api/v1/whatsapp/chats", headers=headers)
    assert last is not None
    assert last.status_code == 429
    assert FOUNDER_PIN not in last.text
    assert "wrong-pin" not in last.text


def test_filename_sanitize_strips_paths_and_controls(isolated_whatsapp_edition):
    from app.services.max.whatsapp_log import sanitize_filename

    assert sanitize_filename("../etc/passwd") == "passwd"
    assert "\x00" not in sanitize_filename("a\x00b.jpg")
    assert "/" not in sanitize_filename("a/b/c.jpg")
    long_name = sanitize_filename("x" * 400 + ".jpg")
    assert len(long_name) <= 120


def test_jobs_root_is_edition_scoped(monkeypatch, tmp_path):
    monkeypatch.delenv("WHATSAPP_JOBS_ROOT", raising=False)
    amp = tmp_path / "amp"
    maxine = tmp_path / "maxine"
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(amp))
    from app.services.max.doc_lookup import jobs_root

    assert jobs_root() == amp / "jobs"
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(maxine))
    assert jobs_root() == maxine / "jobs"


def test_family_edition_cannot_read_or_file_rafael_jobs(isolated_whatsapp_edition, monkeypatch, tmp_path):
    rec = prepare_inbound_attachment(
        b"rafael-bytes",
        filename="site.jpg",
        mime_type="image/jpeg",
        media_type="image",
        wa_id=RAFAEL,
        hint_text="Maggie porch",
    )
    from app.services.max.whatsapp_log import (
        file_into_job as file_job,
        get_conversation_messages,
        list_conversations,
        log_message,
    )

    log_message(RAFAEL, "inbound", "image", body="[photo]", attachments=[rec])
    rafael_jobs = jobs_root()
    assert list_conversations()
    family = tmp_path / "family-edition"
    family.mkdir()
    family_jobs = tmp_path / "family-jobs"
    family_jobs.mkdir()
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(family))
    monkeypatch.setenv("WHATSAPP_JOBS_ROOT", str(family_jobs))
    monkeypatch.delenv("WHATSAPP_LABELS", raising=False)
    assert list_conversations() == []
    msgs, total = get_conversation_messages(RAFAEL)
    assert msgs == []
    assert total == 0
    path = file_job(b"family-bytes", "family.jpg", "image", "maggie-frolich")
    assert str(family_jobs) in path
    assert str(rafael_jobs) not in path
    assert not list(Path(rafael_jobs).rglob("family.jpg"))
    with pytest.raises(ValueError):
        refile_attachment(1, "maggie-frolich")


def test_persist_failure_still_answers(isolated_whatsapp_edition, monkeypatch):
    import asyncio

    posts = []

    def _post(url, body, headers):
        posts.append(body)
        return _GraphResponse({"messages": [{"id": "wamid.out"}]})

    def _boom(*_a, **_k):
        raise OSError("disk full")

    async def _chat(text, wa_id):
        return "Max still answered. Not sent."

    monkeypatch.setattr(wa, "_persist_inbound_media", _boom)
    raw = _payload({"type": "text", "id": "wamid.persist-fail", "text": {"body": "hello after fail"}})
    result = asyncio.run(wa.process_webhook(raw, _sign(raw), text_handler=_chat, http_post=_post))
    assert result["results"][0]["reply_sent"] is True
    assert "Max still answered" in posts[0]["text"]["body"]


def test_parse_album_context_and_unknown_text_as_text():
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{"changes": [{"value": {"messages": [
            {
                "from": RAFAEL,
                "id": "wamid.ctx",
                "timestamp": "1",
                "type": "unknown",
                "text": {"body": "These are for Emmas client"},
                "context": {"from": RAFAEL, "id": "wamid.photo1"},
            },
            {
                "from": RAFAEL,
                "id": "wamid.nfm",
                "timestamp": "2",
                "type": "interactive",
                "interactive": {"nfm_reply": {"body": "These are for Emmas client"}},
            },
        ]}}]}],
    }
    parsed = parse_inbound(payload)
    assert [m["type"] for m in parsed] == ["text", "text"]
    assert all("Emmas" in m["text"] for m in parsed)
    assert parsed[0]["context_id"] == "wamid.photo1"
    assert parsed[0]["raw_type"] == "unknown"


def test_unknown_album_text_is_not_unhandled(isolated_whatsapp_edition, monkeypatch):
    import asyncio

    posts = []

    def _post(url, body, headers):
        posts.append(body)
        return _GraphResponse({"messages": [{"id": "wamid.out"}]})

    async def _chat(text, wa_id):
        return "should-not-run-for-album-mate"

    async def _photo(image, mime, caption, wa_id):
        return "Photo draft. Not sent."

    def _get(url, headers):
        if "/media-" in str(url) and not str(url).endswith("/img"):
            return _GraphResponse({"url": "https://example.test/img", "mime_type": "image/jpeg"})
        return _GraphResponse(content=b"\xff\xd8img")

    raw = _payloads([
        {"type": "image", "id": "wamid.p1", "image": {"id": "media-1", "mime_type": "image/jpeg"}},
        {
            "type": "unknown",
            "id": "wamid.txt",
            "text": {"body": "These are for Emmas client"},
            "context": {"id": "wamid.p1"},
        },
    ])
    result = asyncio.run(wa.process_webhook(
        raw, _sign(raw), text_handler=_chat, photo_handler=_photo, http_get=_get, http_post=_post,
    ))
    bodies = [p["text"]["body"] for p in posts]
    assert bodies
    assert all("not handled" not in b.lower() for b in bodies)
    assert all("Photo draft" not in b for b in bodies)
    assert all("should-not-run" not in b for b in bodies)
    assert any("Closest" in b or "Which job" in b or "Emma" in b for b in bodies)
    assert len(bodies) == 1


def test_photo_batch_files_once_from_nearby_job_text(isolated_whatsapp_edition, monkeypatch):
    import asyncio

    posts = []

    def _post(url, body, headers):
        posts.append(body)
        return _GraphResponse({"messages": [{"id": "wamid.out"}]})

    async def _photo(image, mime, caption, wa_id):
        raise AssertionError("photo_quote must not run without quote words")

    def _get(url, headers):
        if "/media-" in str(url) and not str(url).endswith("/img"):
            return _GraphResponse({"url": "https://example.test/img", "mime_type": "image/jpeg"})
        return _GraphResponse(content=b"\xff\xd8img")

    raw = _payloads([
        {"type": "image", "id": "wamid.b1", "image": {"id": "media-b1", "mime_type": "image/jpeg"}},
        {"type": "image", "id": "wamid.b2", "image": {"id": "media-b2", "mime_type": "image/jpeg"}},
        {"type": "image", "id": "wamid.b3", "image": {"id": "media-b3", "mime_type": "image/jpeg"}},
        {"type": "text", "id": "wamid.hint", "text": {"body": "These are for Maggie"}},
    ])
    result = asyncio.run(wa.process_webhook(
        raw, _sign(raw), photo_handler=_photo, http_get=_get, http_post=_post,
    ))
    bodies = [p["text"]["body"] for p in posts]
    assert len(bodies) == 1
    assert "Filed" in bodies[0] and "Maggie" in bodies[0]
    assert "3" in bodies[0]
    assert not any(r.get("route") == "photo_quote" for r in result["results"])
    messages, _ = get_conversation_messages(RAFAEL)
    atts = [a for m in messages if m["direction"] == "inbound" for a in m.get("attachments") or []]
    assert len(atts) == 3
    assert all(a["filing_status"] == "filed" and a["job_slug"] == "maggie-frolich" for a in atts)


def test_photo_batch_asks_once_when_job_unknown(isolated_whatsapp_edition, monkeypatch):
    import asyncio

    posts = []

    def _post(url, body, headers):
        posts.append(body)
        return _GraphResponse({"messages": [{"id": "wamid.out"}]})

    async def _photo(image, mime, caption, wa_id):
        return "Photo draft. Not sent."

    def _get(url, headers):
        if "/media-" in str(url) and not str(url).endswith("/img"):
            return _GraphResponse({"url": "https://example.test/img", "mime_type": "image/jpeg"})
        return _GraphResponse(content=b"\xff\xd8img")

    raw = _payloads([
        {"type": "image", "id": "wamid.c1", "image": {"id": "media-c1", "mime_type": "image/jpeg"}},
        {"type": "image", "id": "wamid.c2", "image": {"id": "media-c2", "mime_type": "image/jpeg"}},
    ])
    asyncio.run(wa.process_webhook(raw, _sign(raw), photo_handler=_photo, http_get=_get, http_post=_post))
    bodies = [p["text"]["body"] for p in posts]
    assert len(bodies) == 1
    assert "Photo draft" not in bodies[0]
    assert "Which job" in bodies[0] or "Closest" in bodies[0]


def test_unresolved_job_text_falls_through_after_ask(isolated_whatsapp_edition):
    rec = prepare_inbound_attachment(
        b"parked",
        filename="win.jpg",
        mime_type="image/jpeg",
        media_type="image",
        wa_id=RAFAEL,
        hint_text="",
    )
    from app.services.max.whatsapp_log import (
        finalize_photo_batch,
        last_attachment_ids,
        log_message,
        record_media_batch,
        set_pending_filings,
    )

    mid = log_message(RAFAEL, "inbound", "image", body="[photo]", attachments=[rec])
    att_id = last_attachment_ids(mid)[0]["id"]
    set_pending_filings(RAFAEL, [att_id])
    record_media_batch(RAFAEL, [att_id], "")
    finalize_photo_batch(RAFAEL, force_ask=True)
    # Isolated aliases only (Maggie/Willard/McLean/Emma). This phrase must
    # not resolve uniquely even if live client_aliases.json later adds more.
    assert consume_job_answer(RAFAEL, "These are for Zorblax skylight") is None
    assert get_pending_filings(RAFAEL) == [att_id]
    names = {row["client_name"] for row in suggest_jobs("Zorblax skylight")}
    assert names


def test_photo_with_quote_caption_still_creates_draft(isolated_whatsapp_edition, monkeypatch):
    import asyncio

    posts = []
    quotes = []

    def _post(url, body, headers):
        posts.append(body)
        return _GraphResponse({"messages": [{"id": "wamid.out"}]})

    def _get(url, headers):
        if str(url).endswith("/media-q"):
            return _GraphResponse({"url": "https://example.test/img", "mime_type": "image/jpeg"})
        return _GraphResponse(content=b"\xff\xd8img")

    async def _photo(image, mime, caption, wa_id):
        quotes.append({"caption": caption, "bytes": image})
        return "Photo draft EST-TEST. Not sent."

    raw = _payload({
        "type": "image",
        "id": "wamid.quote",
        "image": {"id": "media-q", "mime_type": "image/jpeg", "caption": "Please quote this window for Maggie"},
    })
    result = asyncio.run(wa.process_webhook(
        raw, _sign(raw), photo_handler=_photo, http_get=_get, http_post=_post,
    ))
    assert quotes
    assert any(r.get("route") == "photo_quote" for r in result["results"])
    assert "Not sent" in posts[0]["text"]["body"]
    assert "EST-TEST" in posts[0]["text"]["body"]


def test_nearby_quote_text_does_not_create_drafts(isolated_whatsapp_edition, monkeypatch):
    import asyncio

    quotes = []

    def _post(url, body, headers):
        return _GraphResponse({"messages": [{"id": "wamid.out"}]})

    def _get(url, headers):
        if "/media-" in str(url) and not str(url).endswith("/img"):
            return _GraphResponse({"url": "https://example.test/img", "mime_type": "image/jpeg"})
        return _GraphResponse(content=b"\xff\xd8img")

    async def _photo(image, mime, caption, wa_id):
        quotes.append(True)
        return "Photo draft. Not sent."

    images = [
        {"type": "image", "id": f"wamid.pq{i}", "image": {"id": f"media-pq{i}", "mime_type": "image/jpeg"}}
        for i in range(7)
    ]
    raw = _payloads([
        {"type": "text", "id": "wamid.askq", "text": {"body": "send me a quote for Emma"}},
        *images,
    ])
    result = asyncio.run(wa.process_webhook(raw, _sign(raw), photo_handler=_photo, http_get=_get, http_post=_post))
    assert quotes == []
    assert not any(r.get("route") == "photo_quote" for r in result["results"])
    assert sum(1 for r in result["results"] if r.get("route") == "file_photo") == 7


def _image_get(url, headers):
    if "/media-" in str(url) and not str(url).endswith("/img"):
        return _GraphResponse({"url": "https://example.test/img", "mime_type": "image/jpeg"})
    return _GraphResponse(content=b"\xff\xd8img")


def test_hello_after_photos_reaches_on_text(isolated_whatsapp_edition, monkeypatch):
    import asyncio

    chats = []
    posts = []

    def _post(url, body, headers):
        posts.append(body)
        return _GraphResponse({"messages": [{"id": "wamid.out"}]})

    async def _chat(text, wa_id):
        chats.append(text)
        return "Max chat hello. Not sent."

    async def _photo(image, mime, caption, wa_id):
        raise AssertionError("photos without a caption quote must not draft")

    photos = _payloads([
        {"type": "image", "id": "wamid.h1", "image": {"id": "media-h1", "mime_type": "image/jpeg"}},
        {"type": "image", "id": "wamid.h2", "image": {"id": "media-h2", "mime_type": "image/jpeg"}},
    ])
    asyncio.run(wa.process_webhook(
        photos, _sign(photos), text_handler=_chat, photo_handler=_photo,
        http_get=_image_get, http_post=_post,
    ))
    hello = _payload({"type": "text", "id": "wamid.hello", "text": {"body": "hello"}})
    result = asyncio.run(wa.process_webhook(
        hello, _sign(hello), text_handler=_chat, photo_handler=_photo, http_post=_post,
    ))
    assert chats == ["hello"]
    assert any(r.get("route") == "chat" for r in result["results"])
    hello_bodies = [p["text"]["body"] for p in posts if "hello" in (p.get("text") or {}).get("body", "").lower() or "Max chat" in (p.get("text") or {}).get("body", "")]
    assert any("Max chat hello" in b for b in hello_bodies)
    assert not any("Closest" in (p.get("text") or {}).get("body", "") and "hello" in str(p).lower() for p in posts[-1:])


def test_schedule_after_photos_reaches_on_text(isolated_whatsapp_edition, monkeypatch):
    import asyncio

    chats = []
    posts = []

    def _post(url, body, headers):
        posts.append(body)
        return _GraphResponse({"messages": [{"id": "wamid.out"}]})

    async def _chat(text, wa_id):
        chats.append(text)
        return "Here is today's schedule. Not sent."

    photos = _payloads([
        {"type": "image", "id": "wamid.s1", "image": {"id": "media-s1", "mime_type": "image/jpeg"}},
    ])
    asyncio.run(wa.process_webhook(
        photos, _sign(photos), text_handler=_chat, http_get=_image_get, http_post=_post,
    ))
    ask = "what's on my schedule today?"
    follow = _payload({"type": "text", "id": "wamid.sched", "text": {"body": ask}})
    result = asyncio.run(wa.process_webhook(
        follow, _sign(follow), text_handler=_chat, http_post=_post,
    ))
    assert chats == [ask]
    assert any(r.get("route") == "chat" for r in result["results"])
    assert any("schedule" in p["text"]["body"].lower() for p in posts)
    assert "Closest" not in posts[-1]["text"]["body"]


def test_same_message_caption_creates_one_draft_per_batch(isolated_whatsapp_edition, monkeypatch):
    import asyncio

    quotes = []

    def _post(url, body, headers):
        return _GraphResponse({"messages": [{"id": "wamid.out"}]})

    async def _photo(image, mime, caption, wa_id):
        quotes.append(caption)
        return "Photo draft. Not sent."

    raw = _payloads([
        {
            "type": "image",
            "id": f"wamid.cap{i}",
            "image": {
                "id": f"media-cap{i}",
                "mime_type": "image/jpeg",
                "caption": "Please quote this window for Maggie",
            },
        }
        for i in range(7)
    ])
    result = asyncio.run(wa.process_webhook(
        raw, _sign(raw), photo_handler=_photo, http_get=_image_get, http_post=_post,
    ))
    assert len(quotes) == 1
    assert sum(1 for r in result["results"] if r.get("route") == "photo_quote") == 1
    assert sum(1 for r in result["results"] if r.get("route") == "file_photo") == 6


def test_meta_redelivery_deduped_before_batch(isolated_whatsapp_edition, monkeypatch):
    import asyncio

    batch_calls = []
    from app.services.max import whatsapp_log as wlog

    real = wlog.record_media_batch

    def _record(wa_id, attachment_ids, hint_text=""):
        batch_calls.append(list(attachment_ids))
        return real(wa_id, attachment_ids, hint_text)

    monkeypatch.setattr(wlog, "record_media_batch", _record)

    def _post(url, body, headers):
        return _GraphResponse({"messages": [{"id": "wamid.out"}]})

    raw = _payload({
        "type": "image",
        "id": "wamid.redeliver",
        "image": {"id": "media-redeliver", "mime_type": "image/jpeg"},
    })
    first = asyncio.run(wa.process_webhook(raw, _sign(raw), http_get=_image_get, http_post=_post))
    second = asyncio.run(wa.process_webhook(raw, _sign(raw), http_get=_image_get, http_post=_post))
    assert first["results"][0].get("duplicate") is not True
    assert second["results"][0]["duplicate"] is True
    assert len(batch_calls) == 1
    messages, _ = get_conversation_messages(RAFAEL)
    atts = [a for m in messages if m["direction"] == "inbound" for a in m.get("attachments") or []]
    assert len(atts) == 1


def test_stale_photo_batch_expires_from_sqlite_after_restart(isolated_whatsapp_edition):
    from datetime import datetime, timedelta, timezone

    from app.services.max.whatsapp_log import (
        _get_conn,
        _load_batch,
        _lock,
        expire_stale_batches,
        init_db,
        record_media_batch,
    )

    record_media_batch(RAFAEL, [42], "windows")
    assert _load_batch(RAFAEL)["ids"] == [42]
    stale = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    init_db()
    with _lock:
        conn = _get_conn()
        try:
            conn.execute(
                "UPDATE whatsapp_media_batches SET last_at = ?, asked = 0, asked_at = '' WHERE wa_id = ?",
                (stale, RAFAEL),
            )
            conn.commit()
        finally:
            conn.close()
    # Restart: in-memory flush is gone; SQLite last_at must expire on load.
    assert expire_stale_batches(RAFAEL) == 1
    assert _load_batch(RAFAEL)["ids"] == []
    assert consume_job_answer(RAFAEL, "hello") is None


def _quote_spies(monkeypatch):
    created = {"quotes": 0, "leads": 0, "handoffs": 0}

    def _no_quote(*_a, **_k):
        created["quotes"] += 1
        raise AssertionError("Phase 0 must not create estimates")

    def _no_lead(*_a, **_k):
        created["leads"] += 1
        raise AssertionError("Phase 0 must not create LeadForge leads")

    def _no_handoff(*_a, **_k):
        created["handoffs"] += 1
        raise AssertionError("Phase 0 must not create LuxeForge jobs")

    monkeypatch.setattr("app.services.quote_service.create_quote", _no_quote, raising=False)
    monkeypatch.setattr(
        "app.services.workroom_lead_intake.submit_intake", _no_lead, raising=False,
    )
    monkeypatch.setattr(
        "app.services.luxeforge_intake_handoff.handoff_submitted_intake",
        _no_handoff,
        raising=False,
    )
    return created


def test_phase0_client_photos_write_job_record(isolated_whatsapp_edition, monkeypatch):
    import asyncio

    from app.services.max.whatsapp_folders import JOB_FACTS_NAME, JOB_RECORD_NAME, read_job_record

    _quote_spies(monkeypatch)
    posts = []

    def _post(url, body, headers):
        posts.append(body)
        return _GraphResponse({"messages": [{"id": "wamid.out"}]})

    raw = _payloads([
        {"type": "image", "id": "wamid.p0a", "image": {"id": "media-p0a", "mime_type": "image/jpeg"}},
        {"type": "image", "id": "wamid.p0b", "image": {"id": "media-p0b", "mime_type": "image/jpeg"}},
        {"type": "image", "id": "wamid.p0c", "image": {"id": "media-p0c", "mime_type": "image/jpeg"}},
        {"type": "text", "id": "wamid.p0t", "text": {"body": "These are for Maggie"}},
    ])
    asyncio.run(wa.process_webhook(raw, _sign(raw), http_get=_image_get, http_post=_post))
    record = read_job_record("maggie-frolich")
    assert record["kind"] == "client"
    assert record["intake_id"] is None
    assert record["quote_id"] is None
    assert record["lead_id"] is None
    assert len(record["attachments"]) == 3
    folder = jobs_root() / "maggie-frolich"
    assert (folder / JOB_RECORD_NAME).is_file()
    assert (folder / JOB_FACTS_NAME).is_file()
    photos = list((folder / "photos").glob("*"))
    assert len(photos) == 3
    messages, _ = get_conversation_messages(RAFAEL)
    atts = [a for m in messages if m["direction"] == "inbound" for a in m.get("attachments") or []]
    assert all(a.get("job_slug") == "maggie-frolich" for a in atts if a.get("media_type") == "image")


def test_phase0_personal_and_luxeforge_never_quote(isolated_whatsapp_edition, monkeypatch):
    import asyncio

    from app.services.max.whatsapp_folders import read_job_record

    _quote_spies(monkeypatch)
    quotes = []

    def _post(url, body, headers):
        return _GraphResponse({"messages": [{"id": "wamid.out"}]})

    async def _photo(*_a, **_k):
        quotes.append(True)
        return "Photo draft. Not sent."

    raw = _payloads([
        {
            "type": "image",
            "id": "wamid.pers1",
            "image": {
                "id": "media-pers1",
                "mime_type": "image/jpeg",
                "caption": "please quote this — personal",
            },
        },
        {"type": "image", "id": "wamid.pers2", "image": {"id": "media-pers2", "mime_type": "image/jpeg"}},
        {"type": "image", "id": "wamid.pers3", "image": {"id": "media-pers3", "mime_type": "image/jpeg"}},
    ])
    result = asyncio.run(wa.process_webhook(
        raw, _sign(raw), photo_handler=_photo, http_get=_image_get, http_post=_post,
    ))
    assert quotes == []
    assert not any(r.get("route") == "photo_quote" for r in result["results"])
    record = read_job_record("personal")
    assert record["kind"] == "personal"
    assert record["intake_id"] is None and record["lead_id"] is None and record["quote_id"] is None
    assert len(list((jobs_root() / "personal" / "photos").glob("*"))) == 3

    luxe = _payloads([
        {
            "type": "image",
            "id": "wamid.lf1",
            "image": {"id": "media-lf1", "mime_type": "image/jpeg", "caption": "luxeforge"},
        },
    ])
    asyncio.run(wa.process_webhook(luxe, _sign(luxe), photo_handler=_photo, http_get=_image_get, http_post=_post))
    luxe_rec = read_job_record("luxeforge")
    assert luxe_rec["kind"] == "luxeforge"
    assert luxe_rec["attachments"]
    assert quotes == []


def test_phase0_insurance_store_and_3d_pdf(isolated_whatsapp_edition, monkeypatch):
    import asyncio

    from app.services.max.whatsapp_folders import read_job_record

    _quote_spies(monkeypatch)
    posts = []

    def _post(url, body, headers):
        posts.append(body)
        return _GraphResponse({"messages": [{"id": "wamid.out"}]})

    def _get(url, headers):
        u = str(url)
        if u.endswith("/media-ins"):
            return _GraphResponse({"url": "https://example.test/img", "mime_type": "image/jpeg"})
        if u.endswith("/media-stl"):
            return _GraphResponse({"url": "https://example.test/m.stl", "mime_type": "model/stl"})
        if u.endswith("/media-pdf"):
            return _GraphResponse({"url": "https://example.test/p.pdf", "mime_type": "application/pdf"})
        if u.endswith("/media-usd"):
            return _GraphResponse({"url": "https://example.test/p.usdz", "mime_type": "model/vnd.usdz+zip"})
        if u.endswith(".stl") or "m.stl" in u:
            return _GraphResponse(content=b"solid test\nendsolid")
        if u.endswith(".pdf") or "p.pdf" in u:
            return _GraphResponse(content=b"%PDF-1.4 test")
        if "usdz" in u:
            return _GraphResponse(content=b"PK\x03\x04usdz")
        return _GraphResponse(content=b"\xff\xd8img")

    raw = _payloads([
        {
            "type": "image",
            "id": "wamid.ins",
            "image": {"id": "media-ins", "mime_type": "image/jpeg", "caption": "insurance claim photos"},
        },
        {
            "type": "document",
            "id": "wamid.stl",
            "document": {"id": "media-stl", "filename": "seat.stl", "mime_type": "model/stl"},
        },
        {
            "type": "document",
            "id": "wamid.pdf",
            "document": {"id": "media-pdf", "filename": "plan.pdf", "mime_type": "application/pdf"},
        },
        {
            "type": "document",
            "id": "wamid.usd",
            "document": {"id": "media-usd", "filename": "room.usdz", "mime_type": "model/vnd.usdz+zip"},
        },
    ])
    result = asyncio.run(wa.process_webhook(raw, _sign(raw), http_get=_get, http_post=_post))
    assert all("not handled" not in (p.get("text") or {}).get("body", "").lower() for p in posts)
    assert not any(r.get("route") == "photo_quote" for r in result["results"])
    rec = read_job_record("insurance")
    assert rec["kind"] == "insurance"
    assert rec["quote_id"] is None and rec["lead_id"] is None
    ins = jobs_root() / "insurance"
    assert list((ins / "photos").glob("*"))
    assert list((ins / "scans").glob("*.stl")) or list((ins / "scans").glob("*"))
    assert list((ins / "received").glob("*.pdf")) or list((ins / "received").glob("*"))

    store = _payload({"type": "image", "id": "wamid.store", "image": {
        "id": "media-ins", "mime_type": "image/jpeg", "caption": "for the store",
    }})
    asyncio.run(wa.process_webhook(store, _sign(store), http_get=_get, http_post=_post))
    assert read_job_record("store")["kind"] == "store"


def test_phase0_reserved_reply_after_ask(isolated_whatsapp_edition, monkeypatch):
    import asyncio

    from app.services.max.whatsapp_folders import read_job_record

    _quote_spies(monkeypatch)

    def _post(url, body, headers):
        return _GraphResponse({"messages": [{"id": "wamid.out"}]})

    raw = _payloads([
        {"type": "image", "id": "wamid.u1", "image": {"id": "media-u1", "mime_type": "image/jpeg"}},
    ])
    asyncio.run(wa.process_webhook(raw, _sign(raw), http_get=_image_get, http_post=_post))
    assert get_pending_filings(RAFAEL)
    answered = consume_job_answer(RAFAEL, "luxeforge")
    assert answered and answered["status"] == "filed"
    assert answered["job"]["slug"] == "luxeforge"
    rec = read_job_record("luxeforge")
    assert rec["kind"] == "luxeforge"
    assert rec["attachments"]
    assert rec["intake_id"] is None


def test_phase0_family_edition_reserved_folders_isolated(isolated_whatsapp_edition, monkeypatch, tmp_path):
    from app.services.max.whatsapp_folders import append_job_record, ensure_reserved_folders, read_job_record

    ensure_reserved_folders()
    append_job_record("personal", {"filename": "a.jpg", "filed_path": "/tmp/a.jpg", "media_type": "image"})
    rafael_root = jobs_root()
    assert read_job_record("personal")["attachments"]
    family = tmp_path / "family-edition"
    family.mkdir()
    family_jobs = tmp_path / "family-jobs"
    family_jobs.mkdir()
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(family))
    monkeypatch.setenv("WHATSAPP_JOBS_ROOT", str(family_jobs))
    ensure_reserved_folders()
    other = read_job_record("personal")
    assert other["attachments"] == []
    assert (rafael_root / "personal" / "JOB-RECORD.json").is_file()
    assert not (family_jobs / "personal" / "JOB-RECORD.json").is_file() or read_job_record("personal")["attachments"] == []


def test_file_into_job_and_append_reject_unsafe_slugs(isolated_whatsapp_edition):
    from app.services.max.whatsapp_folders import UnsafeJobSlug, append_job_record

    root = jobs_root().resolve()
    outside = root.parent / "zz"
    for slug in ("../../zz", "/tmp/zz", "foo/bar", r"foo\bar", "C:\\zz"):
        with pytest.raises(UnsafeJobSlug):
            file_into_job(b"x", "a.jpg", "image", slug)
        with pytest.raises(UnsafeJobSlug):
            append_job_record(slug, {"filename": "a.jpg", "filed_path": "/tmp/a.jpg"})
    assert not outside.exists()
    assert not (root / "zz").exists()
    leaked = [p for p in root.parent.iterdir() if p.name == "zz" or p.name.endswith("zz")]
    assert leaked == []


def test_unique_client_beats_reserved_store_word(isolated_whatsapp_edition):
    from app.services.max.whatsapp_folders import (
        match_reserved_folder,
        resolve_folder,
    )

    emma = resolve_folder("Emma's store order")
    assert emma and emma["slug"] == "emma-vita"
    assert emma["kind"] == "client"
    store = resolve_folder("for the store")
    assert store and store["slug"] == "store"
    assert match_reserved_folder("shop photos") is None
    assert match_reserved_folder("private photos") is None
    assert match_reserved_folder("claim photos") is None
    assert match_reserved_folder("showroom photos") is None
    assert resolve_folder("shop photos") is None
    rec = prepare_inbound_attachment(
        b"\xff\xd8emma",
        filename="order.jpg",
        mime_type="image/jpeg",
        media_type="image",
        wa_id=RAFAEL,
        hint_text="Emma's store order",
    )
    assert rec["filing_status"] == "filed"
    assert rec["job_slug"] == "emma-vita"
    assert "store" not in Path(rec["filed_path"]).parts or "emma-vita" in rec["filed_path"]
    assert "emma-vita" in rec["filed_path"]


def test_append_job_record_concurrent_photos_keep_both(isolated_whatsapp_edition):
    from concurrent.futures import ThreadPoolExecutor

    from app.services.max.whatsapp_folders import append_job_record, read_job_record

    def write(i: int) -> None:
        append_job_record(
            "personal",
            {
                "filename": f"p{i}.jpg",
                "filed_path": f"/tmp/p{i}.jpg",
                "media_type": "image",
                "whatsapp_attachment_id": f"att-{i}",
            },
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(write, range(8)))
    rec = read_job_record("personal")
    ids = {a.get("whatsapp_attachment_id") for a in rec["attachments"]}
    assert ids == {f"att-{i}" for i in range(8)}


def test_corrupt_job_record_is_quarantined_then_fresh(isolated_whatsapp_edition):
    from app.services.max.whatsapp_folders import (
        JOB_RECORD_NAME,
        append_job_record,
        read_job_record,
    )

    folder = jobs_root() / "personal"
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / JOB_RECORD_NAME
    dest.write_text("{not-json", encoding="utf-8")
    rec = append_job_record(
        "personal",
        {"filename": "a.jpg", "filed_path": "/tmp/a.jpg", "media_type": "image"},
    )
    assert rec["attachments"]
    corrupt = list(folder.glob(f"{JOB_RECORD_NAME}.corrupt-*"))
    assert len(corrupt) == 1
    assert "{not-json" in corrupt[0].read_text(encoding="utf-8")
    assert dest.is_file()
    fresh = json.loads(dest.read_text(encoding="utf-8"))
    assert fresh["attachments"]
    assert read_job_record("personal")["attachments"]


def test_job_record_owner_follows_edition_label(isolated_whatsapp_edition, monkeypatch, tmp_path):
    from app.services.max.whatsapp_folders import (
        append_job_record,
        edition_owner_label,
        empty_job_record,
        read_job_record,
    )

    monkeypatch.delenv("WHATSAPP_EDITION_OWNER", raising=False)
    monkeypatch.delenv("EMPIRE_OWNER_LABEL", raising=False)
    maxine = tmp_path / "maxine"
    maxine.mkdir()
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(maxine))
    assert edition_owner_label() == "Maxine"
    assert empty_job_record("personal")["owner"] == "Maxine"
    rec = append_job_record(
        "personal",
        {"filename": "a.jpg", "filed_path": "/tmp/a.jpg", "media_type": "image"},
    )
    assert rec["owner"] == "Maxine"
    assert read_job_record("personal")["owner"] == "Maxine"

    amp = tmp_path / "amp"
    amp.mkdir()
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(amp))
    assert edition_owner_label() == "Max-e"
    monkeypatch.setenv("WHATSAPP_EDITION_OWNER", "Nelma")
    assert edition_owner_label() == "Nelma"


def test_default_attachment_cap_fits_polycam(monkeypatch):
    monkeypatch.delenv("WHATSAPP_MAX_ATTACHMENT_SIZE_BYTES", raising=False)
    from app.services.max.whatsapp_log import (
        DEFAULT_MAX_ATTACHMENT_SIZE,
        get_max_attachment_size,
    )

    assert DEFAULT_MAX_ATTACHMENT_SIZE == 256 * 1024 * 1024
    assert get_max_attachment_size() == 256 * 1024 * 1024
    monkeypatch.setenv("WHATSAPP_MAX_ATTACHMENT_SIZE_BYTES", "1048576")
    assert get_max_attachment_size() == 1048576


def test_polycam_zip_files_as_scan(isolated_whatsapp_edition):
    from app.services.max.whatsapp_folders import classify_media_type, filing_subdir, is_scan_file

    assert is_scan_file("Room-Polycam.zip", "application/zip", "document")
    assert classify_media_type("document", "Room-Polycam.zip", "application/zip") == "scan"
    assert filing_subdir("document", "Room-Polycam.zip", "application/zip") == "scans"
    path = file_into_job(
        b"PK\x03\x04polycam",
        "Room-Polycam.zip",
        "document",
        "maggie-frolich",
        mime_type="application/zip",
    )
    assert "/scans/" in path.replace("\\", "/")
    assert Path(path).is_file()
    assert not is_scan_file("invoice.zip", "application/zip", "document")


def test_job_hint_drops_chat_and_keeps_captions(isolated_whatsapp_edition):
    from app.services.max.whatsapp_log import (
        combined_job_hint,
        is_job_hint_text,
        log_message,
        record_media_batch,
        _load_batch,
    )

    assert is_job_hint_text("New job home wood suites.")
    assert is_job_hint_text("These are for Maggie")
    assert not is_job_hint_text("You online?")
    assert not is_job_hint_text("Need to buy a case")
    assert not is_job_hint_text("Next 2 months")
    assert not is_job_hint_text("Are you vetting my pictures?")
    log_message(RAFAEL, "inbound", "text", body="Next 2 months")
    log_message(RAFAEL, "inbound", "text", body="You online?")
    log_message(RAFAEL, "inbound", "image", caption="New job home wood suites.", body="[photo]")
    hint = combined_job_hint(RAFAEL, "You online?", "Need to buy a case", "New job home wood suites.")
    assert "home wood" in hint.lower()
    assert "online" not in hint.lower()
    assert "buy a case" not in hint.lower()
    record_media_batch(RAFAEL, [1], "You online? Next 2 months New job home wood suites.")
    stored = _load_batch(RAFAEL)["hint_text"].lower()
    assert "online" not in stored
    assert "next 2 months" not in stored


def test_new_job_caption_creates_folder_and_files(isolated_whatsapp_edition, monkeypatch):
    import asyncio

    from app.services.max.doc_lookup import load_client_aliases
    from app.services.max.whatsapp_folders import read_job_record

    _quote_spies(monkeypatch)
    posts = []

    def _post(url, body, headers):
        posts.append(body)
        return _GraphResponse({"messages": [{"id": "wamid.out"}]})

    raw = _payload({
        "type": "image",
        "id": "wamid.newjob",
        "image": {
            "id": "media-new",
            "mime_type": "image/jpeg",
            "caption": "New job home wood suites.",
        },
    })
    asyncio.run(wa.process_webhook(raw, _sign(raw), http_get=_image_get, http_post=_post))
    bodies = [p.get("text", {}).get("body") for p in posts]
    assert any("Created job Home Wood Suites" in (b or "") and "filed" in (b or "").lower() for b in bodies)
    folder = jobs_root() / "home-wood-suites"
    assert (folder / "JOB-FACTS.md").is_file()
    rec = read_job_record("home-wood-suites")
    assert rec["kind"] == "client"
    assert rec["quote_id"] is None and rec["lead_id"] is None and rec["intake_id"] is None
    assert rec["attachments"]
    slugs = {c["slug"] for c in (load_client_aliases().get("clients") or [])}
    assert "home-wood-suites" in slugs
    bak = list((Path(os.environ["MAX_CLIENT_ALIASES_PATH"]).parent).glob("client_aliases.json.bak-*"))
    assert bak


def test_new_job_ambiguous_asks_once(isolated_whatsapp_edition):
    from app.services.max.whatsapp_folders import parse_new_job_name, resolve_or_create_folder

    assert parse_new_job_name("nuevo trabajo Casa Azul") == "Casa Azul"
    assert parse_new_job_name("new client Oak Lane") == "Oak Lane"
    assert resolve_or_create_folder("New job Maggie and Willard") is None


def test_purchase_text_asks_personal_or_store(isolated_whatsapp_edition, monkeypatch):
    import asyncio

    posts = []

    def _post(url, body, headers):
        posts.append(body)
        return _GraphResponse({"messages": [{"id": "wamid.out"}]})

    raw = _payloads([
        {"type": "image", "id": "wamid.case1", "image": {"id": "media-case", "mime_type": "image/jpeg"}},
        {"type": "text", "id": "wamid.case2", "text": {"body": "Need to buy a case"}},
    ])
    asyncio.run(wa.process_webhook(raw, _sign(raw), http_get=_image_get, http_post=_post))
    bodies = [p["text"]["body"] for p in posts]
    assert any("Personal or store folder?" in b for b in bodies)
    assert not any("Closest:" in b for b in bodies)


def test_photo_status_reply_knows_parked_and_filed(isolated_whatsapp_edition):
    from app.services.max.whatsapp_log import (
        last_attachment_ids,
        log_message,
        parked_photos_note,
        photo_status_reply,
        prepare_inbound_attachment,
        set_pending_filings,
    )

    rec = prepare_inbound_attachment(
        b"park",
        filename="a.jpg",
        mime_type="image/jpeg",
        media_type="image",
        wa_id=RAFAEL,
        hint_text="",
    )
    mid = log_message(RAFAEL, "inbound", "image", body="[photo]", attachments=[rec])
    att_id = last_attachment_ids(mid)[0]["id"]
    set_pending_filings(RAFAEL, [att_id])
    note = parked_photos_note(RAFAEL)
    assert "waiting to be filed" in note
    reply = photo_status_reply(RAFAEL, "Are you vetting my pictures?")
    assert reply and reply.startswith("Yes")
    assert "waiting" in reply.lower()


def test_live_oct10_sequence_new_job_and_truthful_photos(isolated_whatsapp_edition, monkeypatch):
    """Regression for the 10/10 5:35–5:42 PM Dell live test (chat log 34–47)."""
    import asyncio
    import os

    from app.services.max.whatsapp_folders import read_job_record
    from app.services.max.whatsapp_log import _load_batch, photo_status_reply

    _quote_spies(monkeypatch)
    chats = []
    posts = []

    def _post(url, body, headers):
        posts.append(body)
        return _GraphResponse({"messages": [{"id": "wamid.out"}]})

    async def _chat(text, wa_id):
        chats.append(text)
        return f"chat:{text}"

    async def _voice(audio, mime, wa_id):
        chats.append("[voice]")
        return "voice ok"

    def _run(messages):
        raw = _payloads(messages)
        return asyncio.run(wa.process_webhook(
            raw, _sign(raw), text_handler=_chat, voice_handler=_voice,
            http_get=_image_get, http_post=_post,
        ))

    _run([{"type": "audio", "id": "wamid.v1", "audio": {"id": "media-v", "mime_type": "audio/ogg", "voice": True}, "voice": True}])
    _run([{"type": "text", "id": "wamid.t1", "text": {"body": "Next 2 months"}}])
    _run([{
        "type": "image",
        "id": "wamid.p1",
        "image": {"id": "media-p1", "mime_type": "image/jpeg", "caption": "New job home wood suites."},
    }])
    _run([{"type": "text", "id": "wamid.t2", "text": {"body": "You online?"}}])
    _run([{"type": "image", "id": "wamid.p2", "image": {"id": "media-p2", "mime_type": "image/jpeg"}}])
    _run([{"type": "image", "id": "wamid.p3", "image": {"id": "media-p3", "mime_type": "image/jpeg"}}])
    _run([{"type": "text", "id": "wamid.t3", "text": {"body": "Need to buy a case"}}])
    _run([{"type": "text", "id": "wamid.t4", "text": {"body": "Are you vetting my pictures?"}}])

    hint = (_load_batch(RAFAEL).get("hint_text") or "").lower()
    assert "online" not in hint
    assert "next 2 months" not in hint
    assert "buy a case" not in hint
    assert "vetting" not in hint

    messages, _ = get_conversation_messages(RAFAEL)
    atts = [a for m in messages if m["direction"] == "inbound" for a in m.get("attachments") or []]
    photos = [a for a in atts if a.get("media_type") in {"image", "photo"}]
    assert len(photos) == 3
    assert all(a["filing_status"] == "filed" and a["job_slug"] == "home-wood-suites" for a in photos)
    rec = read_job_record("home-wood-suites")
    assert rec["quote_id"] is None and rec["lead_id"] is None
    assert len(rec["attachments"]) == 3

    bodies = [p["text"]["body"] for p in posts]
    assert any("Created job Home Wood Suites" in b for b in bodies)
    assert any("Filed under Home Wood Suites" in b or "filed" in b.lower() for b in bodies)
    assert any(b.startswith("Yes") and "Home Wood Suites" in b for b in bodies)
    assert not any("I don't have any new pictures" in b for b in bodies)
    assert "You online?" in chats
    assert "Need to buy a case" in chats
    assert "Are you vetting my pictures?" not in chats
    assert photo_status_reply(RAFAEL, "did you get my photos")
    aliases_path = Path(os.environ["MAX_CLIENT_ALIASES_PATH"])
    assert "home-wood-suites" in aliases_path.read_text(encoding="utf-8")
