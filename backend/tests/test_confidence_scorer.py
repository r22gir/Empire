"""Shadow confidence scorer: heuristics, report, draft improvement feed.

Isolated temp EMPIRE_DATA_DIR / EMPIRE_TASK_DB. No WhatsApp, SMTP, or live writes.
"""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

TWEET = "https://x.com/someuser/status/1845123456789012345"
JOB = "Quote for Maggie. Straight bench 48 inches long."


@pytest.fixture()
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path / "edition-data"))
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))
    monkeypatch.setenv("MAX_CONFIDENCE_DB", str(tmp_path / "confidence.db"))
    monkeypatch.setenv("MAX_CONFIDENCE_LOG", str(tmp_path / "confidence.log"))
    monkeypatch.setenv("MAX_CONFIDENCE_GATE", "shadow")
    monkeypatch.setenv("MAX_IMPROVE_SPEC_DIR", str(tmp_path / "specs"))
    monkeypatch.delenv("MAX_CONFIDENCE_MODEL_CHECK", raising=False)
    monkeypatch.delenv("EMPIRE_EDITION", raising=False)
    monkeypatch.delenv("WHATSAPP_EDITION_OWNER", raising=False)
    from app.services.max import confidence

    importlib.reload(confidence)
    from app.db import database, init_db

    importlib.reload(database)
    importlib.reload(init_db)
    init_db.init_database()
    from app.services.leadforge import growth
    from app.services.max import improvements

    importlib.reload(growth)
    importlib.reload(improvements)
    return dict(conf=confidence, imp=improvements, tmp=tmp_path)


def test_x_link_scores_low_for_quote_intake(isolated):
    conf = isolated["conf"]
    hit = conf.score_intent(TWEET, chosen_path="quote_intake")
    assert hit["chosen_path"] == "quote_intake"
    assert hit["best_path"] == "article_link"
    assert hit["score"] < 0.55
    assert hit["would_gate"] is True
    assert hit["behavior_changed"] is False
    assert "quote" in (hit["gated_action"] or "").lower() or "link" in (hit["gated_action"] or "").lower()
    assert hit["scores"]["quote_intake"] < 0.2
    assert hit["scores"]["article_link"] >= 0.9


def test_x_link_scores_high_for_article_path(isolated):
    conf = isolated["conf"]
    hit = conf.score_intent(TWEET, chosen_path="article_link")
    assert hit["score"] >= 0.9
    assert hit["would_gate"] is False
    assert hit["behavior_changed"] is False


def test_real_job_scores_high_for_quote_intake(isolated):
    conf = isolated["conf"]
    hit = conf.score_intent(JOB, chosen_path="quote_intake")
    assert hit["score"] >= 0.85
    assert hit["would_gate"] is False


def test_shadow_mode_does_not_change_behavior(isolated):
    conf = isolated["conf"]
    assert conf.gate_mode() == "shadow"
    hit = conf.score_intent(TWEET, chosen_path="quote_intake")
    assert hit["behavior_changed"] is False
    assert hit["mode"] == "shadow"


def test_juan_camilo_editions_flagged_when_low(isolated, monkeypatch):
    conf = isolated["conf"]
    monkeypatch.setenv("EMPIRE_EDITION", "max_e")
    juan = conf.score_intent(TWEET, chosen_path="quote_intake", edition="max_e", requester="juan")
    assert juan["family_flag"] is True
    assert juan["edition"] == "max_e"
    camilo = conf.score_intent(TWEET, chosen_path="quote_intake", edition="maxine", requester="camilo")
    assert camilo["family_flag"] is True
    main = conf.score_intent(TWEET, chosen_path="quote_intake", edition="studio")
    assert main["family_flag"] is False


def test_tool_create_quote_on_x_link_is_low(isolated):
    conf = isolated["conf"]
    hit = conf.score_tool("create_quote", {}, text=TWEET, known=True)
    assert hit["score"] < 0.2
    assert hit["would_gate"] is True
    assert hit["behavior_changed"] is False


def test_week_report_counts_scores_and_corrections(isolated):
    conf = isolated["conf"]
    conf.score_intent(TWEET, chosen_path="quote_intake")
    conf.score_intent(JOB, chosen_path="quote_intake")
    conf.mark_correction("Dude, no. read article")
    report = conf.week_report(7)
    assert report["total"] >= 3
    assert report["low_confidence"] >= 1
    assert report["corrections"] >= 1
    assert report["behavior_changed"] is False
    assert "quote_intake" in report["paths"]


def test_feed_files_draft_improvement_never_approved(isolated):
    conf = isolated["conf"]
    imp = isolated["imp"]
    conf.score_intent(TWEET, chosen_path="quote_intake")
    filed = conf.feed_low_scores_to_improvements(7)
    assert filed
    assert all(row.get("status") == "proposed" for row in filed)
    row = imp.get(filed[0]["improvement_id"])
    assert row["status"] == "proposed"
    assert row["kind"] == "fix"
    assert row["requested_via"] == "confidence"
    again = conf.feed_low_scores_to_improvements(7)
    assert again == []


def test_gate_off_skips_persist(isolated, monkeypatch):
    conf = isolated["conf"]
    monkeypatch.setenv("MAX_CONFIDENCE_GATE", "off")
    importlib.reload(conf)
    hit = conf.score_intent(TWEET, chosen_path="quote_intake")
    assert hit["would_gate"] is True
    report = conf.week_report(7)
    assert report["total"] == 0


def test_model_nudge_skips_when_quota_stopped(isolated, monkeypatch):
    conf = isolated["conf"]
    monkeypatch.setenv("MAX_CONFIDENCE_MODEL_CHECK", "1")

    def _snap():
        return {
            "stopped": True,
            "calls_left": 0,
            "tokens_left": 0,
            "auto_credits": False,
        }

    monkeypatch.setattr(
        "app.services.max.improvement_planner.usage_snapshot",
        _snap,
    )
    nudge = conf.optional_model_nudge(TWEET, {"article_link": 0.9, "quote_intake": 0.08})
    assert nudge["skipped"] == "quota"
    assert nudge["auto_credits"] is False


def test_report_endpoint(isolated):
    conf = isolated["conf"]
    conf.score_intent(TWEET, chosen_path="quote_intake")
    from app.routers import growth as growth_router

    importlib.reload(growth_router)
    app = FastAPI()
    app.include_router(growth_router.router, prefix="/api/v1")
    client = TestClient(app)
    res = client.get("/api/v1/growth/confidence/report?days=7")
    assert res.status_code == 200
    body = res.json()
    assert body["low_confidence"] >= 1
    assert body["behavior_changed"] is False


def test_script_exists_and_is_read_only():
    script = Path(__file__).resolve().parents[1] / "scripts" / "confidence_report.py"
    assert script.is_file()
    text = script.read_text(encoding="utf-8")
    assert "week_report" in text
    assert "send_email" not in text
    assert "WHATSAPP_ACCESS_TOKEN" not in text


def test_on_mode_still_does_not_change_behavior(isolated, monkeypatch):
    conf = isolated["conf"]
    monkeypatch.setenv("MAX_CONFIDENCE_GATE", "on")
    importlib.reload(conf)
    hit = conf.score_intent(TWEET, chosen_path="quote_intake")
    assert hit["mode"] == "on"
    assert hit["would_gate"] is True
    assert hit["behavior_changed"] is False
    assert hit["gated_action"]


def test_unset_gate_defaults_to_shadow(isolated, monkeypatch):
    conf = isolated["conf"]
    monkeypatch.delenv("MAX_CONFIDENCE_GATE", raising=False)
    importlib.reload(conf)
    assert conf.gate_mode() == "shadow"


def test_confidence_log_file_records_decision(isolated):
    conf = isolated["conf"]
    dest = conf.ensure_confidence_file_logging()
    assert dest == conf.log_path()
    assert "edition-data" in str(dest) or "confidence" in str(dest)
    hit = conf.score_intent(TWEET, chosen_path="quote_intake")
    logged = dest.read_text(encoding="utf-8")
    assert "chosen=quote_intake" in logged
    assert "best=article_link" in logged
    assert "would_gate=True" in logged
    assert str(hit["score"]) in logged or "score=" in logged


def test_week_report_includes_unfiled_low(isolated):
    conf = isolated["conf"]
    conf.score_intent(TWEET, chosen_path="quote_intake")
    report = conf.week_report(7)
    assert report["unfiled_low"] >= 1
    assert report["behavior_changed"] is False
    assert report["auto_credits"] is False


def test_unset_gate_cascade_is_exact_shadow_score_only(isolated, monkeypatch):
    """Unset MAX_CONFIDENCE_GATE must match today's shadow mode: log only."""
    conf = isolated["conf"]
    monkeypatch.delenv("MAX_CONFIDENCE_GATE", raising=False)
    importlib.reload(conf)
    assert conf.gate_mode() == "shadow"
    assert conf.cascade_enabled() is False

    retries: list[str] = []
    asks: list[str] = []
    original = "I'll start a quote from that link."

    def _retry(*_a, **_k):
        retries.append("retry")
        return "retried answer"

    def _ask(*_a, **_k):
        asks.append("ask")
        return {"id": "should-not-file"}

    monkeypatch.setattr(conf, "_file_founder_ask", lambda *a, **k: asks.append("inbox") or {"id": "nope"})
    hit = conf.apply_answer_cascade(
        TWEET,
        original,
        chosen_path="quote_intake",
        retry_fn=_retry,
        ask_founder_fn=_ask,
    )
    assert hit["mode"] == "shadow"
    assert hit["action"] == "proceed"
    assert hit["behavior_changed"] is False
    assert hit["answer"] == original
    assert hit["retried"] is False
    assert hit["asked_founder"] is False
    assert hit["auto_credits"] is False
    assert retries == []
    assert asks == []
    report = conf.week_report(7)
    assert report["total"] >= 1
    assert report["behavior_changed"] is False
    assert report["mode"] == "shadow"


def test_explicit_shadow_matches_unset_cascade(isolated, monkeypatch):
    conf = isolated["conf"]
    monkeypatch.setenv("MAX_CONFIDENCE_GATE", "shadow")
    importlib.reload(conf)
    original = "I'll start a quote from that link."
    called = []
    shadow = conf.apply_answer_cascade(
        TWEET,
        original,
        chosen_path="quote_intake",
        retry_fn=lambda *a, **k: called.append("r") or "x",
        ask_founder_fn=lambda *a, **k: called.append("a") or {},
    )
    monkeypatch.delenv("MAX_CONFIDENCE_GATE", raising=False)
    importlib.reload(conf)
    unset = conf.apply_answer_cascade(
        TWEET,
        original,
        chosen_path="quote_intake",
        retry_fn=lambda *a, **k: called.append("r") or "x",
        ask_founder_fn=lambda *a, **k: called.append("a") or {},
    )
    assert shadow["mode"] == unset["mode"] == "shadow"
    assert shadow["action"] == unset["action"] == "proceed"
    assert shadow["behavior_changed"] is False
    assert unset["behavior_changed"] is False
    assert shadow["answer"] == unset["answer"] == original
    assert called == []


def test_gate_on_high_confidence_proceeds(isolated, monkeypatch):
    conf = isolated["conf"]
    monkeypatch.setenv("MAX_CONFIDENCE_GATE", "on")
    importlib.reload(conf)
    original = "Quote for Maggie: straight bench 48 inches. I have the dims."
    called = []
    hit = conf.apply_answer_cascade(
        JOB,
        original,
        chosen_path="quote_intake",
        tool_results=[{"tool": "create_quote", "success": True}],
        retry_fn=lambda *a, **k: called.append("retry") or "nope",
        ask_founder_fn=lambda *a, **k: called.append("ask") or {},
    )
    assert hit["mode"] == "on"
    assert hit["action"] == "proceed"
    assert hit["behavior_changed"] is False
    assert hit["answer"] == original
    assert hit["asked_founder"] is False
    assert called == []
    assert hit["score"]["would_gate"] is False


def test_gate_on_low_retries_then_asks_founder(isolated, monkeypatch):
    conf = isolated["conf"]
    monkeypatch.setenv("MAX_CONFIDENCE_GATE", "on")
    importlib.reload(conf)
    original = "I think I'll open a quote from that tweet."
    retries = []
    asks = []

    def _retry(text, answer, record, tools):
        retries.append({"text": text, "answer": answer})
        return "I think maybe it is still a quote?"

    def _ask(record, text, question):
        asks.append(question)
        return {"id": "inbox-test", "status": "open"}

    hit = conf.apply_answer_cascade(
        TWEET,
        original,
        chosen_path="quote_intake",
        retry_fn=_retry,
        ask_founder_fn=_ask,
    )
    assert len(retries) == 1
    assert hit["retried"] is True
    assert hit["action"] == "ask_founder"
    assert hit["behavior_changed"] is True
    assert hit["asked_founder"] is True
    assert hit["answer"] != original
    assert "need a call from you" in hit["answer"].lower()
    assert asks and ("quote" in asks[0].lower() or "link" in asks[0].lower())
    assert hit["auto_credits"] is False
    report = conf.week_report(7)
    assert report["behavior_changed"] is True
    assert report["cascade_asked_founder"] >= 1


def test_gate_on_retry_can_recover_and_proceed(isolated, monkeypatch):
    conf = isolated["conf"]
    monkeypatch.setenv("MAX_CONFIDENCE_GATE", "on")
    importlib.reload(conf)
    original = "I think?"

    def _retry(*_a, **_k):
        return (
            "This is an X/Twitter link, not a job. Here is the article reading: "
            "the post is a product announcement, not a quote request."
        )

    first = conf.score_answer(TWEET, original, chosen_path="article_link", persist=False)
    assert first["would_gate"] is True
    hit = conf.apply_answer_cascade(
        TWEET,
        original,
        chosen_path="article_link",
        retry_fn=_retry,
        ask_founder_fn=lambda *a, **k: {"id": "should-not"},
    )
    assert hit["retried"] is True
    assert hit["action"] == "proceed"
    assert hit["asked_founder"] is False
    assert "article" in hit["answer"].lower()
    assert hit["behavior_changed"] is True
    assert hit["score"]["would_gate"] is False


def test_stronger_check_never_spends_minimax_credits(isolated, monkeypatch):
    conf = isolated["conf"]
    monkeypatch.setenv("MAX_CONFIDENCE_GATE", "on")
    monkeypatch.setenv("MAX_CONFIDENCE_MODEL_CHECK", "1")
    importlib.reload(conf)

    def _snap():
        return {
            "stopped": True,
            "calls_left": 0,
            "tokens_left": 0,
            "auto_credits": False,
        }

    monkeypatch.setattr("app.services.max.improvement_planner.usage_snapshot", _snap)
    checked = conf.stronger_check(
        TWEET,
        "I think I'll start a quote.",
        {"scores": {"quote_intake": 0.08, "article_link": 0.94}, "chosen_path": "quote_intake"},
        tool_results=[],
    )
    assert checked["auto_credits"] is False
    assert (checked.get("nudge") or {}).get("auto_credits") is False
    assert (checked.get("nudge") or {}).get("skipped") == "quota"


def test_unset_gate_never_files_founder_inbox(isolated, monkeypatch):
    conf = isolated["conf"]
    monkeypatch.delenv("MAX_CONFIDENCE_GATE", raising=False)
    importlib.reload(conf)
    filed = []
    monkeypatch.setattr(conf, "_file_founder_ask", lambda *a, **k: filed.append(1) or {"id": "x"})
    conf.apply_answer_cascade(TWEET, "I'll start a quote.", chosen_path="quote_intake")
    assert filed == []


def test_cascade_source_never_sends_email_or_whatsapp():
    src = Path(__file__).resolve().parents[1] / "app" / "services" / "max" / "confidence.py"
    text = src.read_text(encoding="utf-8")
    assert "send_email(" not in text
    assert "send_quote_email(" not in text
    assert "WHATSAPP_ACCESS_TOKEN" not in text
    assert "smtp" not in text.lower()
    assert "auto_credits" in text
    assert "Never sends email or WhatsApp" in text


def test_chat_and_stream_share_confidence_cascade_helper():
    router = Path(__file__).resolve().parents[1] / "app" / "routers" / "max" / "router.py"
    src = router.read_text(encoding="utf-8")
    assert src.count("def _apply_confidence_cascade_to_reply(") == 1
    assert src.count("_apply_confidence_cascade_to_reply(") >= 3
    assert "Unset MAX_CONFIDENCE_GATE stays today's shadow mode" in src


def test_decide_cascade_shadow_always_proceeds(isolated, monkeypatch):
    conf = isolated["conf"]
    monkeypatch.delenv("MAX_CONFIDENCE_GATE", raising=False)
    importlib.reload(conf)
    low = {"would_gate": True, "score": 0.1}
    assert conf.decide_cascade(low, attempt=0) == "proceed"
    assert conf.decide_cascade(low, attempt=1) == "proceed"
    monkeypatch.setenv("MAX_CONFIDENCE_GATE", "on")
    importlib.reload(conf)
    assert conf.decide_cascade(low, attempt=0) == "retry"
    assert conf.decide_cascade(low, attempt=1) == "ask_founder"
    assert conf.decide_cascade({"would_gate": False, "score": 0.9}, attempt=0) == "proceed"
