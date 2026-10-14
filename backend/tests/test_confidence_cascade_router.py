"""Router-level confidence cascade: founder session, inbox replace vs skip.

Tests the production hook both /chat and /chat/stream call
(`apply_router_cascade` / `_apply_confidence_cascade_to_reply`).
Isolated temp EMPIRE_DATA_DIR / EMPIRE_TASK_DB. No WhatsApp, SMTP, or live writes.
Does not import app.routers.max.router (that module mkdir's live data).
"""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest

TWEET = "https://x.com/someuser/status/1845123456789012345"
LOW_ANSWER = "I think I'll start a quote from that tweet."
HIGH_ANSWER = "Quote for Maggie: straight bench 48 inches. I have the dims."
ROUTER = Path(__file__).resolve().parents[1] / "app" / "routers" / "max" / "router.py"


@pytest.fixture()
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path / "edition-data"))
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))
    monkeypatch.setenv("MAX_CONFIDENCE_DB", str(tmp_path / "confidence.db"))
    monkeypatch.setenv("MAX_CONFIDENCE_LOG", str(tmp_path / "confidence.log"))
    monkeypatch.setenv("MAX_IMPROVE_SPEC_DIR", str(tmp_path / "specs"))
    monkeypatch.delenv("MAX_CONFIDENCE_MODEL_CHECK", raising=False)
    monkeypatch.delenv("EMPIRE_EDITION", raising=False)
    monkeypatch.delenv("WHATSAPP_EDITION_OWNER", raising=False)
    monkeypatch.delenv("MAX_CONFIDENCE_GATE", raising=False)
    from app.db import database, init_db

    importlib.reload(database)
    importlib.reload(init_db)
    init_db.init_database()
    from app.services.max import confidence
    from app.services.max.desks import founder_inbox

    importlib.reload(confidence)
    importlib.reload(founder_inbox)
    return dict(conf=confidence, inbox=founder_inbox, tmp=tmp_path)


def _envelope(conf, channel: str, meta: dict) -> dict:
    extra = conf.cascade_metadata_extra(meta)
    base = {"surface": channel or "web"}
    if extra:
        base.update(extra)
    return base


def test_unset_router_helper_no_db_write_no_metadata_key(isolated, monkeypatch):
    conf = isolated["conf"]
    monkeypatch.delenv("MAX_CONFIDENCE_GATE", raising=False)
    importlib.reload(conf)

    dest = conf.db_path()
    log = conf.log_path()
    text, meta = conf.apply_router_cascade(
        TWEET, LOW_ANSWER, channel="web", is_founder=True,
    )
    assert text == LOW_ANSWER
    assert meta == {}
    envelope = _envelope(conf, "web", meta)
    assert "confidence_cascade" not in envelope
    assert conf.cascade_metadata_extra(meta) is None
    assert not dest.exists()
    assert not log.exists() or log.stat().st_size == 0


def test_both_chat_doors_use_shared_helper_and_founder_flag():
    src = ROUTER.read_text(encoding="utf-8")
    assert src.count("def _apply_confidence_cascade_to_reply(") == 1
    assert src.count("_apply_confidence_cascade_to_reply(") >= 3
    assert src.count("is_founder=") >= 2
    assert "canonical_founder and _cascade_founder()" in src
    assert "_founder_session = _fs.resolve_founder_session(http_request)" in src
    assert "is_founder=bool((_founder_session or {}).get(\"verified\"))" in src
    assert "apply_router_cascade" in src
    assert "FOUNDER_CASCADE_CHANNELS" not in src
    assert "'whatsapp'" not in src.split("def _apply_confidence_cascade_to_reply")[1][:800]
    assert "''" not in "".join(
        line for line in src.splitlines()
        if "FOUNDER_CASCADE" in line or "cascade_allowed" in line
    )


def test_web_channel_without_founder_session_untouched(isolated, monkeypatch):
    """channel='web' without a verified founder session must not rewrite."""
    conf = isolated["conf"]
    monkeypatch.setenv("MAX_CONFIDENCE_GATE", "on")
    importlib.reload(conf)

    dest = conf.db_path()
    text, meta = conf.apply_router_cascade(
        TWEET, LOW_ANSWER, channel="web", is_founder=False, chosen_path="quote_intake",
    )
    assert text == LOW_ANSWER
    assert "need a call from you" not in text.lower()
    assert meta == {}
    assert "confidence_cascade" not in _envelope(conf, "web", meta)
    assert not dest.exists()


def test_founder_session_gate_on_can_rewrite(isolated, monkeypatch):
    conf = isolated["conf"]
    monkeypatch.setenv("MAX_CONFIDENCE_GATE", "on")
    importlib.reload(conf)

    text, meta = conf.apply_router_cascade(
        TWEET, LOW_ANSWER, channel="web", is_founder=True, chosen_path="quote_intake",
    )
    assert "need a call from you" in text.lower()
    assert meta.get("asked_founder") is True
    assert meta.get("behavior_changed") is True
    assert "confidence_cascade" in _envelope(conf, "web", meta)
    high, high_meta = conf.apply_router_cascade(
        "Quote for Maggie. Straight bench 48 inches long.",
        HIGH_ANSWER,
        channel="web",
        is_founder=True,
        tool_results=[{"tool": "create_quote", "success": True}],
    )
    assert high == HIGH_ANSWER
    assert high_meta.get("asked_founder") is False


def test_inbox_default_replace_reopens_resolved(isolated):
    inbox = isolated["inbox"]
    desk_src = (
        Path(__file__).resolve().parents[1]
        / "app" / "services" / "max" / "desks" / "desk_manager.py"
    ).read_text(encoding="utf-8")
    persist = desk_src.split("def _persist_inbox")[1].split("def ")[0]
    assert "founder_inbox.add(" in persist
    assert "skip_existing" not in persist
    first = inbox.add(task_id="desk-1", title="Unrouted", reason="no desk")
    assert first["status"] == "open"
    assert inbox.resolve("desk-1") is True
    assert inbox.get("desk-1")["status"] == "resolved"
    again = inbox.add(task_id="desk-1", title="Reopened by desk", reason="retry")
    assert not again.get("skipped")
    assert again["status"] == "open"
    assert inbox.get("desk-1")["status"] == "open"
    assert inbox.count_open() == 1


def test_inbox_skip_existing_used_by_cascade(isolated, monkeypatch):
    conf = isolated["conf"]
    inbox = isolated["inbox"]
    monkeypatch.setenv("MAX_CONFIDENCE_GATE", "on")
    importlib.reload(conf)

    record = {
        "kind": "answer",
        "chosen_path": "quote_intake",
        "best_path": "article_link",
        "text": TWEET,
        "gated_action": "Read this link, or start a quote from it?",
        "score": 0.08,
    }
    first = conf._file_founder_ask(record, TWEET)
    assert first and first.get("status") == "open"
    assert not first.get("skipped")
    task_id = first["id"]
    second = conf._file_founder_ask(record, TWEET)
    assert second.get("skipped") == "open"
    assert second["id"] == task_id
    assert inbox.count_open() == 1

    assert inbox.resolve(task_id) is True
    assert inbox.get(task_id)["status"] == "resolved"
    third = conf._file_founder_ask(record, TWEET)
    assert third.get("skipped") == "recently_resolved"
    assert inbox.get(task_id)["status"] == "resolved"
    assert inbox.count_open() == 0

    # Older than the recent window: skip_existing falls through to replace.
    from datetime import datetime, timedelta, timezone
    old = (datetime.now(timezone.utc) - timedelta(hours=48)).strftime("%Y-%m-%d %H:%M:%S")
    with inbox._conn() as conn:
        conn.execute(
            "UPDATE founder_inbox SET resolved_at=? WHERE id=?",
            (old, task_id),
        )
    fourth = conf._file_founder_ask(record, TWEET)
    assert not fourth.get("skipped")
    assert fourth["status"] == "open"
    assert inbox.get(task_id)["status"] == "open"


def test_inbox_daily_cap(isolated, monkeypatch):
    conf = isolated["conf"]
    inbox = isolated["inbox"]
    monkeypatch.setenv("MAX_CONFIDENCE_GATE", "on")
    monkeypatch.setenv("MAX_CONFIDENCE_INBOX_DAILY_CAP", "2")
    importlib.reload(conf)

    filed = []
    for i in range(3):
        record = {
            "kind": "answer",
            "chosen_path": "quote_intake",
            "best_path": "article_link",
            "text": f"{TWEET}?n={i}",
            "gated_action": "Read this link, or start a quote from it?",
            "score": 0.08,
        }
        filed.append(conf._file_founder_ask(record, f"{TWEET}-{i}"))
    assert filed[0].get("status") == "open"
    assert filed[1].get("status") == "open"
    assert filed[2].get("skipped") == "daily_cap"
    assert inbox.count_open() == 2
    assert inbox.count_by_source_since("confidence_cascade", "1970-01-01") == 2
