"""6a — LeadForge honest execute + confirmed sends only.

Fake prospects at example.com. EmailService.send is mocked to record or raise.
Tmp EMPIRE_DATA_DIR only. No live data, no real contacts.
"""
from __future__ import annotations

import asyncio
from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.services.leadforge.send_guard import (
    MENSAJE_BAD_TOKEN,
    MENSAJE_NEED_CONFIRM,
    MENSAJE_SEND_DISABLED,
    make_confirm_token,
)


FAKE_OK = "prospect1@example.com"
FAKE_DENIED = "denied@example.com"
FAKE_OPTED = "opted@example.com"


class _RecordingEmail:
    is_configured = True
    sent: list

    def __init__(self):
        pass

    def send(self, **kwargs):
        _RecordingEmail.sent.append(kwargs)
        return True


class _RaisingEmail:
    is_configured = True

    def send(self, **kwargs):
        raise AssertionError("EmailService.send must not be called")


def _ensure_prospects(cs):
    with cs._db() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS prospects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                email TEXT,
                business_name TEXT,
                phone TEXT
            )"""
        )


def _env(monkeypatch, tmp_path, real_send="false"):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))
    monkeypatch.setenv("AMP_JWT_SECRET", "test-confirm-secret")
    monkeypatch.setenv("LEADFORGE_REAL_SEND_ENABLED", real_send)
    monkeypatch.setenv("LEADFORGE_MAX_SEND_PER_REQUEST", "10")
    monkeypatch.setenv("LEADFORGE_MAX_SEND_PER_DAY", "25")
    monkeypatch.setenv("EDITION_DENY_EMAIL", FAKE_DENIED)
    monkeypatch.delenv("FOUNDER_EMAIL", raising=False)


@pytest.fixture()
def lf(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, real_send="false")
    from app.services.leadforge import campaign_service as cs
    cs._init_tables()
    _ensure_prospects(cs)
    _RecordingEmail.sent = []
    monkeypatch.setattr("app.services.max.email_service.EmailService", _RaisingEmail)
    from app.routers import leadforge
    app = FastAPI()
    app.include_router(leadforge.router, prefix="/api/v1")
    return {
        "client": TestClient(app),
        "cs": cs,
        "monkeypatch": monkeypatch,
    }


def _insert_prospect(cs, email: str, name: str = "Prospect Example") -> int:
    with cs._db() as conn:
        cur = conn.execute(
            "INSERT INTO prospects (name, email, business_name, phone) VALUES (?, ?, ?, ?)",
            (name, email, "Example LLC", "555-0100"),
        )
        return int(cur.lastrowid)


def _seed_active_campaign(cs, emails: list[str], *, opted_out_email: str | None = None) -> dict:
    camp = cs.create_campaign({
        "name": "Campaña de prueba",
        "status": "active",
        "send_window_start": "00:00",
        "send_window_end": "23:59",
        "skip_weekends": False,
    })
    cs.add_step(camp["id"], {
        "step_type": "email",
        "subject": "Hola {first_name}",
        "body_template": "Hola {name}",
        "is_manual": False,
        "delay_days": 0,
    })
    pids = []
    opted_pid = None
    for email in emails:
        pid = _insert_prospect(cs, email)
        pids.append(pid)
        if email == opted_out_email:
            opted_pid = pid
    cs.enroll_prospects(camp["id"], pids)
    if opted_pid:
        with cs._db() as conn:
            conn.execute(
                "UPDATE campaign_enrollments SET status = 'opted_out' WHERE prospect_id = ?",
                (opted_pid,),
            )
    return camp


def test_execute_zero_active_campaigns_spanish(lf):
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


def test_execute_creates_drafts_not_sends(lf):
    camp = _seed_active_campaign(lf["cs"], [FAKE_OK])
    before_sent = None
    with lf["cs"]._db() as conn:
        before_sent = conn.execute(
            "SELECT sent_count FROM campaigns WHERE id = ?", (camp["id"],)
        ).fetchone()[0]

    data = asyncio.run(lf["cs"].execute_next_steps())
    assert data["executed"] == 1
    assert data["drafted"] == 1
    assert "borradores" in data["mensaje"]
    assert "No se envió nada" in data["mensaje"]

    with lf["cs"]._db() as conn:
        drafts = conn.execute("SELECT * FROM campaign_drafts").fetchall()
        assert len(drafts) == 1
        acts = conn.execute("SELECT action_type FROM campaign_activity").fetchall()
        assert any(a[0] == "drafted" for a in acts)
        assert not any(a[0] == "auto_sent" for a in acts)
        sent = conn.execute(
            "SELECT sent_count FROM campaigns WHERE id = ?", (camp["id"],)
        ).fetchone()[0]
        drafted = conn.execute(
            "SELECT drafted_count FROM campaigns WHERE id = ?", (camp["id"],)
        ).fetchone()[0]
        assert sent == before_sent
        assert drafted == 1
    assert _RecordingEmail.sent == []


def test_send_without_token_is_409(lf):
    camp = _seed_active_campaign(lf["cs"], [FAKE_OK])
    asyncio.run(lf["cs"].execute_next_steps())
    with lf["cs"]._db() as conn:
        did = conn.execute("SELECT id FROM campaign_drafts").fetchone()[0]
        conn.execute("UPDATE campaign_drafts SET status = 'reviewed' WHERE id = ?", (did,))
    client = lf["client"]
    res = client.post(f"/api/v1/leads/leadforge/campaigns/drafts/{did}/send")
    assert res.status_code == 409
    assert "Manito" in res.json()["detail"]
    res2 = client.post(
        f"/api/v1/leads/leadforge/campaigns/{camp['id']}/send-reviewed",
        json={"confirm": True},
    )
    assert res2.status_code == 409
    assert MENSAJE_NEED_CONFIRM.split(",")[0] in res2.json()["detail"]


def test_expired_and_mismatched_token_409(lf):
    camp = _seed_active_campaign(lf["cs"], [FAKE_OK])
    asyncio.run(lf["cs"].execute_next_steps())
    with lf["cs"]._db() as conn:
        did = conn.execute("SELECT id FROM campaign_drafts").fetchone()[0]
        conn.execute("UPDATE campaign_drafts SET status = 'reviewed' WHERE id = ?", (did,))
    expired, _ = make_confirm_token([did], now=int(datetime.now().timestamp()) - 3600)
    client = lf["client"]
    res = client.post(
        f"/api/v1/leads/leadforge/campaigns/drafts/{did}/send",
        json={"confirm_token": expired, "confirm": True},
    )
    assert res.status_code == 409
    assert MENSAJE_BAD_TOKEN.split(",")[0] in res.json()["detail"]

    other, _ = make_confirm_token([did + 99])
    res2 = client.post(
        f"/api/v1/leads/leadforge/campaigns/drafts/{did}/send",
        json={"confirm_token": other, "confirm": True},
    )
    assert res2.status_code == 409


def test_flag_false_does_not_send(lf):
    _seed_active_campaign(lf["cs"], [FAKE_OK])
    asyncio.run(lf["cs"].execute_next_steps())
    with lf["cs"]._db() as conn:
        did = conn.execute("SELECT id FROM campaign_drafts").fetchone()[0]
        conn.execute("UPDATE campaign_drafts SET status = 'reviewed' WHERE id = ?", (did,))
    preview = lf["client"].post(f"/api/v1/leads/leadforge/campaigns/drafts/{did}/send-preview")
    assert preview.status_code == 200
    body = preview.json()
    assert body["recipients"] == ["p***@example.com"]
    assert MENSAJE_SEND_DISABLED in (body.get("mensaje") or "")
    res = lf["client"].post(
        f"/api/v1/leads/leadforge/campaigns/drafts/{did}/send",
        json={"confirm_token": body["confirm_token"], "confirm": True},
    )
    assert res.status_code == 200
    assert res.json()["sent"] == 0
    assert MENSAJE_SEND_DISABLED in res.json()["mensaje"]
    with lf["cs"]._db() as conn:
        status = conn.execute("SELECT status FROM campaign_drafts WHERE id = ?", (did,)).fetchone()[0]
        assert status == "reviewed"


def test_flag_true_sends_confirmed_only_and_skips(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, real_send="true")
    monkeypatch.setenv("LEADFORGE_MAX_SEND_PER_REQUEST", "1")
    from app.services.leadforge import campaign_service as cs
    cs._init_tables()
    _ensure_prospects(cs)
    _RecordingEmail.sent = []
    monkeypatch.setattr("app.services.max.email_service.EmailService", _RecordingEmail)
    from app.routers import leadforge
    app = FastAPI()
    app.include_router(leadforge.router, prefix="/api/v1")
    client = TestClient(app)

    camp = _seed_active_campaign(cs, [FAKE_OK, FAKE_DENIED, FAKE_OPTED])
    asyncio.run(cs.execute_next_steps())
    with cs._db() as conn:
        conn.execute("UPDATE campaign_drafts SET status = 'reviewed'")
        conn.execute(
            """UPDATE campaign_enrollments SET status = 'opted_out'
               WHERE prospect_id = (SELECT id FROM prospects WHERE email = ?)""",
            (FAKE_OPTED,),
        )
        rows = conn.execute("SELECT id, to_email FROM campaign_drafts").fetchall()
        assert len(rows) == 3

    preview = client.post(f"/api/v1/leads/leadforge/campaigns/{camp['id']}/send-preview")
    assert preview.status_code == 200
    body = preview.json()
    assert body["count"] == 1
    assert body["recipients"] == ["p***@example.com"]

    res = client.post(
        f"/api/v1/leads/leadforge/campaigns/{camp['id']}/send-reviewed",
        json={"confirm_token": body["confirm_token"], "confirm": True},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["sent"] == 1
    assert len(_RecordingEmail.sent) == 1
    assert _RecordingEmail.sent[0]["to"] == FAKE_OK

    extras = [r[0] for r in rows if r[1] != FAKE_OK]
    if extras:
        token, _ = make_confirm_token(extras)
        blocked = client.post(
            f"/api/v1/leads/leadforge/campaigns/{camp['id']}/send-reviewed",
            json={"confirm_token": token, "confirm": True},
        )
        # Token ids are deny/opted — preview/send of those ids sends 0
        assert blocked.json().get("sent", 0) == 0
        assert len(_RecordingEmail.sent) == 1
