"""LeadForge execute honesty + confirmed sends. Fake prospects only. No live SMTP."""
from __future__ import annotations

import asyncio
import importlib
from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


FAKE_PROSPECT = "prospect1@example.com"
FAKE_DENIED = "denied.owner@example.com"
FAKE_OPTED = "opted.out@example.com"


@pytest.fixture(autouse=True)
def _block_outbound(monkeypatch):
    def _boom(*_a, **_k):
        raise RuntimeError("outbound send blocked in tests")

    monkeypatch.setattr(
        "app.services.max.email_service.EmailService.send",
        _boom,
        raising=False,
    )


@pytest.fixture()
def lf(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_EDITION", "maxine")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))
    monkeypatch.setenv("AMP_JWT_SECRET", "test-leadforge-secret")
    monkeypatch.delenv("LEADFORGE_REAL_SEND_ENABLED", raising=False)
    monkeypatch.setenv("EDITION_DENY_EMAIL", FAKE_DENIED)
    monkeypatch.delenv("FOUNDER_EMAIL", raising=False)

    from app.db import database, init_db
    importlib.reload(database)
    importlib.reload(init_db)
    init_db.init_database()

    from app.services.leadforge import prospect_engine, campaign_service
    from app.routers import leadforge
    importlib.reload(prospect_engine)
    importlib.reload(campaign_service)
    importlib.reload(leadforge)

    sent = []

    class _Svc:
        is_configured = True

        def send(self, **kwargs):
            sent.append(kwargs)
            return True

    monkeypatch.setattr(
        "app.services.max.email_service.EmailService",
        _Svc,
    )

    app = FastAPI()
    app.include_router(leadforge.router, prefix="/api/v1")
    return {
        "client": TestClient(app),
        "cs": campaign_service,
        "sent": sent,
        "pe": prospect_engine,
    }


def _insert_prospect(cs, email, name="Prospect Example"):
    with cs._db() as conn:
        cur = conn.execute(
            "INSERT INTO prospects (name, email, phone) VALUES (?, ?, ?)",
            (name, email, "555-0100"),
        )
        return cur.lastrowid


def _seed_campaign(cs, *, status="active", skip_weekends=0):
    camp = cs.create_campaign({
        "name": "Maxine test campaign",
        "status": status,
        "skip_weekends": bool(skip_weekends),
        "send_window_start": "00:00",
        "send_window_end": "23:59",
        "business_unit": "workroom",
    })
    cs.add_step(camp["id"], {
        "step_type": "email",
        "subject": "Hola {name}",
        "body_template": "Hola manito",
        "delay_days": 0,
        "is_manual": False,
    })
    return camp["id"]


def test_execute_zero_campaigns_spanish_mensaje(lf):
    client = lf["client"]
    res = client.post("/api/v1/leads/leadforge/campaigns/execute")
    assert res.status_code == 200
    data = res.json()
    assert data["executed"] == 0
    assert "Manito" in data["mensaje"]
    assert "no se preparó nada" in data["mensaje"]
    with lf["cs"]._db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM campaign_drafts").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM campaign_activity").fetchone()[0] == 0
    assert lf["sent"] == []


def test_execute_active_enrollment_drafts_not_sent(lf):
    cs = lf["cs"]
    cid = _seed_campaign(cs)
    pid = _insert_prospect(cs, FAKE_PROSPECT)
    cs.enroll_prospects(cid, [pid])
    data = asyncio.run(cs.execute_next_steps())
    assert data["drafted"] == 1
    assert "borradores" in data["mensaje"]
    assert "No se envió nada" in data["mensaje"]
    with cs._db() as conn:
        acts = [r["action_type"] for r in conn.execute("SELECT action_type FROM campaign_activity").fetchall()]
        assert acts == ["drafted"]
        assert "auto_sent" not in acts
        sent_count = conn.execute("SELECT sent_count FROM campaigns WHERE id = ?", (cid,)).fetchone()[0]
        drafted_count = conn.execute("SELECT drafted_count FROM campaigns WHERE id = ?", (cid,)).fetchone()[0]
        assert sent_count == 0
        assert drafted_count == 1
        drafts = conn.execute("SELECT COUNT(*) FROM campaign_drafts").fetchone()[0]
        assert drafts == 1
    assert lf["sent"] == []


def _reviewed_draft(cs, email=FAKE_PROSPECT, enrollment_status="active"):
    cid = _seed_campaign(cs)
    pid = _insert_prospect(cs, email)
    cs.enroll_prospects(cid, [pid])
    asyncio.run(cs.execute_next_steps())
    with cs._db() as conn:
        draft = conn.execute("SELECT * FROM campaign_drafts ORDER BY id DESC LIMIT 1").fetchone()
        draft_id = draft["id"]
        conn.execute(
            "UPDATE campaign_drafts SET status = 'reviewed' WHERE id = ?",
            (draft_id,),
        )
        if enrollment_status != "active":
            conn.execute(
                "UPDATE campaign_enrollments SET status = ? WHERE campaign_id = ?",
                (enrollment_status, cid),
            )
    return cid, draft_id


def test_send_without_token_409(lf):
    cs = lf["cs"]
    _cid, draft_id = _reviewed_draft(cs)
    client = lf["client"]
    res = client.post(f"/api/v1/leads/leadforge/campaigns/drafts/{draft_id}/send", json={})
    assert res.status_code == 409
    assert "Manito" in res.json()["detail"]
    assert lf["sent"] == []


def test_send_expired_or_mismatched_token_409(lf, monkeypatch):
    cs = lf["cs"]
    _cid, draft_id = _reviewed_draft(cs)
    client = lf["client"]
    past = datetime.utcnow() - timedelta(minutes=20)
    expired = cs.make_confirm_token([draft_id], now=past)
    res = client.post(
        f"/api/v1/leads/leadforge/campaigns/drafts/{draft_id}/send",
        json={"confirm_token": expired, "confirm": True},
    )
    assert res.status_code == 409
    other = cs.make_confirm_token([draft_id + 99])
    res2 = client.post(
        f"/api/v1/leads/leadforge/campaigns/drafts/{draft_id}/send",
        json={"confirm_token": other, "confirm": True},
    )
    assert res2.status_code == 409
    assert lf["sent"] == []


def test_flag_false_does_not_send(lf):
    cs = lf["cs"]
    _cid, draft_id = _reviewed_draft(cs)
    preview = cs.preview_send(draft_id=draft_id)
    client = lf["client"]
    res = client.post(
        f"/api/v1/leads/leadforge/campaigns/drafts/{draft_id}/send",
        json={"confirm_token": preview["confirm_token"], "confirm": True},
    )
    assert res.status_code == 403
    assert "desactivado" in res.json()["detail"]
    assert lf["sent"] == []


def test_flag_true_valid_token_sends_and_enforces_limits(lf, monkeypatch):
    monkeypatch.setenv("LEADFORGE_REAL_SEND_ENABLED", "true")
    monkeypatch.setenv("LEADFORGE_MAX_SEND_PER_REQUEST", "1")
    monkeypatch.setenv("LEADFORGE_MAX_SEND_PER_DAY", "1")
    cs = lf["cs"]
    cid, draft_id = _reviewed_draft(cs)
    preview = cs.preview_send(draft_id=draft_id)
    assert preview["count"] == 1
    assert preview["recipients"] == ["p***@example.com"]
    client = lf["client"]
    res = client.post(
        f"/api/v1/leads/leadforge/campaigns/drafts/{draft_id}/send",
        json={"confirm_token": preview["confirm_token"], "confirm": True},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "sent"
    assert len(lf["sent"]) == 1
    assert lf["sent"][0]["to"] == FAKE_PROSPECT

    cid2, draft2 = _reviewed_draft(cs)
    preview2 = cs.preview_send(draft_id=draft2)
    res2 = client.post(
        f"/api/v1/leads/leadforge/campaigns/drafts/{draft2}/send",
        json={"confirm_token": preview2["confirm_token"], "confirm": True},
    )
    assert res2.status_code == 409
    assert len(lf["sent"]) == 1


def test_opted_out_and_deny_list_skipped(lf, monkeypatch):
    monkeypatch.setenv("LEADFORGE_REAL_SEND_ENABLED", "true")
    cs = lf["cs"]
    _cid, denied_id = _reviewed_draft(cs, email=FAKE_DENIED)
    _cid2, opted_id = _reviewed_draft(cs, email=FAKE_OPTED, enrollment_status="opted_out")
    prev_denied = cs.preview_send(draft_id=denied_id)
    prev_opted = cs.preview_send(draft_id=opted_id)
    assert prev_denied["count"] == 0
    assert prev_opted["count"] == 0
    client = lf["client"]
    res = client.post(
        f"/api/v1/leads/leadforge/campaigns/drafts/{denied_id}/send",
        json={"confirm_token": prev_denied.get("confirm_token") or "x", "confirm": True},
    )
    assert res.status_code in (409, 400)
    assert lf["sent"] == []


def test_frontend_has_spanish_confirm_copy():
    from pathlib import Path
    text = (
        Path(__file__).resolve().parents[2]
        / "empire-command-center/app/components/screens/LeadForgePageNew.tsx"
    ).read_text(encoding="utf-8")
    assert "¿Seguro, manito? Vas a enviar" in text
    assert "prospectos reales" in text
    assert "send-preview" in text
    assert "confirm_token" in text
    assert "No se envió nada" in text
