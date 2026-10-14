"""Founder WhatsApp channel: routing, persist, chunking, format, logs.

Mocks Graph and SMTP. Writes only under the test EMPIRE_DATA_DIR.
Never sends a real WhatsApp or email, never touches live data.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import re
import time
from pathlib import Path

import pytest

import app.services.max.whatsapp_channel as wa
from app.services.max.whatsapp_channel import (
    REQUIRED_ENV,
    process_webhook,
    reply_in_window,
)
from app.services.max.whatsapp_format import (
    chunk_whatsapp_text,
    compact_sources_footer,
    extract_image_payloads,
    images_from_desk_result,
    has_real_job_signals,
    is_frustration_correction,
    is_link_or_article_message,
    markdown_to_whatsapp,
    number_chunks,
    prepare_whatsapp_text,
    strip_empty_markdown,
)
from app.services.max.whatsapp_founder_chat import (
    FOUNDER_CHAT_ID,
    append_founder_whatsapp,
    founder_whatsapp_path,
    load_founder_whatsapp,
)
from app.services.max.whatsapp_logging import ensure_whatsapp_file_logging, log_path
from app.services.voice_documents.extract import extract_transcript
from app.services.voice_documents.pipeline import ingest_transcript
from tests._live_data_guard import assert_isolated_env

FAKE_TOKEN = "test-access-token"
FAKE_SECRET = "test-app-secret"
FAKE_VERIFY = "test-verify-token"
TWEET = "https://x.com/someuser/status/1845123456789012345"


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
    monkeypatch.setattr(wa, "_state_path", lambda: tmp_path / "wa-state.json")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path / "edition-data"))
    monkeypatch.setenv("WHATSAPP_JOBS_ROOT", str(tmp_path / "jobs"))
    monkeypatch.setenv("VOICE_DOC_SESSIONS_PATH", str(tmp_path / "voice-sessions.json"))
    monkeypatch.setenv("EMPIRE_BOX_MEMORY_DIR", str(tmp_path / "memory"))
    monkeypatch.setenv("MAX_DRAWINGS_OUTPUT_DIR", str(tmp_path / "drawings"))
    monkeypatch.setenv("WHATSAPP_REPLY_MODE", "text")
    monkeypatch.setenv("WHATSAPP_FOUNDER_PHONES", "12022996975")
    assert_isolated_env()
    live_chat = Path(__file__).resolve().parents[1] / "data" / "chats" / "founder" / "whatsapp.json"
    assert founder_whatsapp_path() != live_chat


def _enable(monkeypatch):
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", FAKE_TOKEN)
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123456")
    monkeypatch.setenv("WHATSAPP_APP_SECRET", FAKE_SECRET)
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", FAKE_VERIFY)


def _sign(body: bytes) -> str:
    digest = hmac.new(FAKE_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _founder() -> str:
    numbers = wa.founder_allowlist()
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


# ── 1. Link-only / article never creates an estimate ──────────────


def test_tweet_url_is_link_not_job():
    assert is_link_or_article_message(TWEET) is True
    assert is_link_or_article_message(f"read this {TWEET}") is True
    assert is_link_or_article_message("Quote for Maggie. Straight bench 48 inches long.") is False
    probe = extract_transcript(TWEET)
    assert probe.document_intent is False
    assert has_real_job_signals(TWEET, probe) is False


def test_url_only_does_not_create_zero_estimate(monkeypatch):
    quotes = []

    def _create(body):
        quotes.append(body)
        return {"id": "q-bad", "quote_number": "EST-2026-307", "status": "draft", "total": 0, "line_items": []}

    monkeypatch.setattr("app.services.quote_service.create_quote", _create)
    result = ingest_transcript(TWEET, channel="whatsapp", session_key="whatsapp:test")
    assert result.get("handled") is False
    assert quotes == []
    assert "EST-2026" not in (result.get("reply_text") or "")
    assert "Total: $0.00" not in (result.get("reply_text") or "")


def test_quote_intake_requires_job_signals():
    assert has_real_job_signals("Quote for Maggie. Straight bench 48 inches long.") is True
    assert has_real_job_signals("https://example.com/a-blog-post") is False
    assert has_real_job_signals("1845123456789012345") is False


def test_job_signals_win_over_link_host_and_fabric_link():
    banquette = "Banquette 96 inches for Smith, fabric link https://site.com/f.jpg"
    lopez = 'Quote for Lopez: bench 48" like this https://x.com/a/status/123'
    ana = 'Make estimate for Ana, 2 cushions 22 1/2" x 18" https://pin.it/abc'
    linkedin_job = "Chair 36 inches for Rivera, see https://www.linkedin.com/in/someone"
    ruiz = "sofa slipcover foam chair for Ruiz https://p.com/a"
    shades = "Quote 3 roman shades 34 1/2 x 60 for kitchen https://x.com/a/status/1"
    for text in (banquette, lopez, ana, linkedin_job, ruiz, shades):
        assert is_link_or_article_message(text) is False, text
        assert has_real_job_signals(text) is True, text
    assert is_link_or_article_message(TWEET) is True
    assert has_real_job_signals(TWEET) is False
    assert is_link_or_article_message("https://x.com/a/status/1") is True
    assert has_real_job_signals("https://x.com/a/status/1") is False
    assert is_link_or_article_message(f"read this {TWEET}") is True
    assert is_link_or_article_message(f"read this link {TWEET}") is True
    assert is_link_or_article_message("read article https://example.com/post") is True


def test_dims_without_inch_marks_request_verbs_and_room_are_job_signals():
    """N x N / N N/N x N / NxN, quote/estimate/price/bid, and item-for-room."""
    jobs = (
        "roman shades 34 1/2 x 60 https://x.com/a/status/1",
        "bench 48 x 18 https://x.com/a/status/1",
        "bench 48x18 https://x.com/a/status/1",
        "cushion 40 x 40 cm https://x.com/a/status/1",
        'valance 36in x 12" https://x.com/a/status/1',
        "Quote 3 roman shades https://x.com/a/status/1",
        "Estimate a bench https://x.com/a/status/1",
        "Price 4 cushions https://x.com/a/status/1",
        "Bid 1 headboard https://x.com/a/status/1",
        "roman shades for kitchen https://x.com/a/status/1",
        "drapes for the living room https://x.com/a/status/1",
        "Quote 3 roman shades 34 1/2 x 60 for kitchen https://x.com/a/status/1",
    )
    for text in jobs:
        assert is_link_or_article_message(text) is False, text
        assert has_real_job_signals(text) is True, text
    assert is_link_or_article_message("https://x.com/a/status/1") is True
    assert has_real_job_signals("https://x.com/a/status/1") is False
    assert is_link_or_article_message(TWEET) is True
    assert has_real_job_signals(TWEET) is False


def test_url_goes_to_max_chat_not_intake(monkeypatch):
    _enable(monkeypatch)
    chats = []
    mail = []

    async def _chat(text, wa_id):
        chats.append(text)
        return "Article: Example title\nSummary: A tweet about chairs."

    monkeypatch.setattr(wa, "max_chat", _chat)
    monkeypatch.setattr(
        "app.services.email.sender.send_email",
        lambda *a, **k: mail.append("sent") or True,
    )

    def _create(*a, **k):
        raise AssertionError("must not create an estimate for a tweet URL")

    monkeypatch.setattr("app.services.quote_service.create_quote", _create)
    reply = asyncio.run(wa.default_text_handler(TWEET, _founder()))
    shown = reply["text"] if isinstance(reply, dict) else reply
    assert chats == [TWEET]
    assert "EST-" not in shown
    assert "Total: $0.00" not in shown
    assert mail == []


def test_open_draft_does_not_swallow_a_tweet_url(monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr("app.services.voice_documents.session.active_session", lambda key: object())
    chats = []

    async def _chat(text, wa_id):
        chats.append(text)
        return "read the article"

    monkeypatch.setattr(wa, "max_chat", _chat)
    monkeypatch.setattr("app.services.max.quick_replies.direct_reply", lambda *a, **k: None)
    reply = asyncio.run(wa.default_text_handler(TWEET, _founder()))
    assert chats == [TWEET]
    assert "Draft" not in str(reply)


# ── 2. Persist every inbound/outbound to founder/whatsapp.json ──


def test_founder_json_records_link_and_reply(monkeypatch):
    _enable(monkeypatch)
    posts = []

    async def _chat(text, wa_id):
        return "Article summary of the tweet."

    def _post(url, body, headers):
        posts.append(body)
        return _GraphResponse({"messages": [{"id": f"wamid.out{len(posts)}"}]})

    monkeypatch.setattr(wa, "max_chat", _chat)
    raw = _payload({"type": "text", "text": {"body": TWEET}, "id": "wamid.link1"})
    result = asyncio.run(process_webhook(raw, _sign(raw), http_post=_post))
    assert result["results"][0]["reply_sent"] is True
    data = load_founder_whatsapp()
    assert data["id"] == FOUNDER_CHAT_ID
    roles = [m["role"] for m in data["messages"]]
    assert "user" in roles and "assistant" in roles
    bodies = " ".join(m["content"] for m in data["messages"])
    assert TWEET in bodies
    assert "Article summary of the tweet." in bodies
    assert founder_whatsapp_path().is_file()


def test_founder_json_records_media_and_attachments(tmp_path):
    append_founder_whatsapp(
        direction="inbound",
        body="[photo] living room",
        message_type="image",
        attachments=[{"filename": "photo.jpg", "mime_type": "image/jpeg", "media_type": "image", "size_bytes": 12}],
    )
    append_founder_whatsapp(
        direction="outbound",
        body="Got 1 photo.",
        message_type="text",
        attachments=[{"filename": "EST-1.pdf", "mime_type": "application/pdf", "media_type": "document"}],
    )
    data = load_founder_whatsapp()
    assert len(data["messages"]) == 2
    assert data["messages"][0]["attachments"][0]["filename"] == "photo.jpg"
    assert data["messages"][1]["attachments"][0]["filename"] == "EST-1.pdf"


# ── 3. Chunking ────────────────────────────────────────────────


def test_chunking_splits_on_paragraphs_and_numbers_parts():
    para = "Paragraph one about the job.\n\n" + ("Long section. " * 80)
    para = para + "\n\nClosing paragraph."
    chunks = chunk_whatsapp_text(para, limit=200)
    assert len(chunks) >= 2
    assert all(len(c) <= 200 for c in chunks)
    numbered = number_chunks(chunks)
    assert numbered[0].startswith("(1/")
    assert numbered[-1].startswith(f"({len(chunks)}/")


def test_reply_in_window_sends_numbered_chunks(monkeypatch):
    _enable(monkeypatch)
    founder = _founder()
    wa.note_customer_window(founder)
    posts = []

    def _post(url, body, headers):
        posts.append(body)
        return _GraphResponse({"messages": [{"id": f"wamid.c{len(posts)}"}]})

    long = "\n\n".join(f"Section {i}. " + ("word " * 120) for i in range(16))
    result = asyncio.run(reply_in_window(founder, long, http_post=_post))
    texts = [p["text"]["body"] for p in posts if p.get("type") == "text"]
    assert len(texts) >= 2
    assert texts[0].startswith("(1/")
    assert all(len(t) <= 4096 for t in texts)
    assert result["chunks"] == len(texts)


# ── 4. Empty markdown / WhatsApp formatting ───────────────────


def test_empty_bold_title_is_stripped():
    raw = "****\n\nThe article is about chairs."
    out = prepare_whatsapp_text(raw)
    assert "****" not in out
    assert "chairs" in out


def test_markdown_converts_to_whatsapp_markup():
    raw = "## Title\n\nThis is **bold** and [src](https://example.com/a)."
    out = markdown_to_whatsapp(raw)
    assert "*" in out and "bold" in out
    assert "##" not in out
    assert "src" in out
    assert "****" not in strip_empty_markdown("** **")


def test_empty_bold_then_real_bold_leaves_no_stray_asterisks():
    raw = "**** x **a** 2*3*4 [t](http://u)"
    out = markdown_to_whatsapp(raw)
    assert "****" not in out
    assert "**" not in out
    assert "*a*" in out
    assert "2*3*4" in out
    assert "t" in out
    assert "http://u" in out
    assert out.startswith("x ")
    # No glued leftover from empty **** + **a** (was 'x*a**').
    assert "x*a" not in out
    assert not re.search(r"\*{2,}", out)


# ── 5. Sources footer ─────────────────────────────────────────


def test_sources_compact_one_line_max_three():
    raw = (
        "Answer here.\n\n"
        "Sources:\n"
        "1. First site — example.com (2026-01-01)\n"
        "2. Second site — two.com (2026-02-02)\n"
        "3. Third site — three.com (date not shown)\n"
        "4. Fourth should drop — four.com (2026-04-04)\n"
    )
    out = compact_sources_footer(raw, max_sources=3)
    assert out.count("Sources:") == 1
    assert "\n" not in out.split("Sources:")[1].strip() or out.split("Sources:")[1].strip().count("\n") == 0
    footer = out.split("Sources:")[1]
    assert "First site" in footer
    assert "Fourth" not in footer
    assert footer.count(",") <= 2


# ── 6. Frustration / correction ───────────────────────────────


def test_frustration_rereads_last_url_not_repeat(monkeypatch):
    _enable(monkeypatch)
    founder = _founder()
    wa.whatsapp_conversation(founder)
    wa.remember_whatsapp_turn(founder, TWEET, "Short wrong summary about something else.")
    seen = []

    async def _chat(text, wa_id):
        seen.append(text)
        return "Re-read: the tweet is about shop lighting, not a quote."

    monkeypatch.setattr(wa, "max_chat", _chat)
    reply = asyncio.run(wa.default_text_handler("Dude, no. read article", founder))
    shown = reply["text"] if isinstance(reply, dict) else reply
    assert seen and "PREVIOUS ANSWER MISSED" in seen[0]
    assert TWEET in seen[0]
    assert "do not repeat" in seen[0].lower()
    assert "Short wrong summary" not in shown
    assert is_frustration_correction("Dude") is True
    assert is_frustration_correction("No, read the article") is True
    assert is_frustration_correction("Quote for Maggie. Straight bench 48 inches.") is False


# ── 7. Logging ────────────────────────────────────────────────


def test_whatsapp_logs_go_to_rotated_file(monkeypatch, caplog):
    dest = ensure_whatsapp_file_logging()
    assert dest == log_path()
    assert "edition-data" in str(dest)
    logger = logging.getLogger("max.whatsapp")
    logger.warning("WhatsApp graph send failed status=400 error=test-mock")
    logged = dest.read_text(encoding="utf-8")
    assert "graph send failed" in logged
    assert FAKE_TOKEN not in logged


# ── 8. Image task delivery (0641b8ef class) ───────────────────


def test_images_from_tool_results_and_desk_notify(monkeypatch, tmp_path):
    img = tmp_path / "beetle.png"
    img.write_bytes(b"\x89PNG" + b"\x00" * 80)
    payloads = extract_image_payloads([{
        "tool": "minimax_text_to_image",
        "success": True,
        "result": {"data": {"images": [{"local_path": str(img), "filename": "beetle.png"}]}},
    }])
    assert payloads and payloads[0]["filename"] == "beetle.png"
    assert payloads[0]["data"].startswith(b"\x89PNG")

    from_path = images_from_desk_result(f"Saved VW Beetle to {img}")
    assert from_path and from_path[0]["filename"] == "beetle.png"

    _enable(monkeypatch)
    founder = _founder()
    wa.note_customer_window(founder)
    posts = []

    def _post(url, body, headers):
        posts.append(body)
        return _GraphResponse({"messages": [{"id": f"wamid.i{len(posts)}"}]})

    def _upload(url, data, mime, filename, headers):
        return {"id": "media-img"}

    result = asyncio.run(reply_in_window(
        founder,
        "Desk task #0641b8ef COMPLETED: VW Beetle",
        http_post=_post,
        http_upload=_upload,
        images=payloads,
    ))
    types = [p["type"] for p in posts]
    assert "image" in types
    assert result["images"][0]["filename"] == "beetle.png"


def test_notify_founder_whatsapp_requires_open_window(monkeypatch):
    _enable(monkeypatch)
    sent = asyncio.run(wa.notify_founder_whatsapp("task done"))
    assert sent.get("sent") is False
    assert sent.get("reason") == "no_open_founder_window"


def test_no_real_smtp_or_live_paths(monkeypatch):
    mail = []
    monkeypatch.setattr(
        "app.services.email.sender.send_email",
        lambda *a, **k: mail.append("sent") or True,
    )
    assert mail == []
    assert_isolated_env()
    path = str(founder_whatsapp_path())
    assert "empire-data" not in path.replace("edition-data", "")
    assert "backend/data/chats" not in path or "edition-data" in path
