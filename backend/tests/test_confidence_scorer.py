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
