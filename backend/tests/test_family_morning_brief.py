"""Family 8:00 AM Morning Brief — owner email only, mocked sends.

Fake addresses only. Never live SMTP. Studio contacts must never be the recipient.
"""
from __future__ import annotations

import asyncio
import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

from app.services.max import scheduler as sched


FAKE_OWNER_EMAIL = "camilo.owner@example.com"
FAKE_OWNER_EMAIL_2 = "camilo.work@example.com"
FAKE_SIBLING_EMAIL = "juan.owner@example.com"

_ENC_STUDIO_EMAIL_A = "726166613232676972616c646f40676d61696c2e636f6d"
_ENC_STUDIO_EMAIL_B = "656d70697265626f783230323640676d61696c2e636f6d"


def _from_hex(encoded: str) -> str:
    return bytes.fromhex(encoded).decode("utf-8")


def _maxine_env(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_EDITION", "maxine")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_DEFAULT_LOCALE", "es")
    monkeypatch.setenv("ASSISTANT_NAME", "Maxine")
    monkeypatch.delenv("FOUNDER_EMAIL", raising=False)
    monkeypatch.delenv("AMP_OWNER_EMAIL", raising=False)
    monkeypatch.delenv("EDITION_OWNER_EMAIL", raising=False)
    monkeypatch.delenv("EDITION_DENY_EMAIL", raising=False)
    monkeypatch.delenv("EDITION_OWNER_WHATSAPP", raising=False)
    monkeypatch.delenv("EDITION_DENY_WHATSAPP", raising=False)


@pytest.fixture()
def maxine(tmp_path, monkeypatch):
    _maxine_env(monkeypatch, tmp_path)
    monkeypatch.setenv("EDITION_OWNER_EMAIL", f"{FAKE_OWNER_EMAIL},{FAKE_OWNER_EMAIL_2}")
    monkeypatch.setenv("EDITION_DENY_EMAIL", FAKE_SIBLING_EMAIL)
    yield tmp_path


def test_brief_is_spanish_with_manito_and_edition_data(maxine, tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "one.json").write_text("{}")
    (inbox / "two.json").write_text("{}")
    now = datetime(2026, 10, 15, 8, 0, 0)
    brief = sched.compile_daily_brief(now)
    assert "manito" in brief.lower()
    assert "Resumen de la mañana" in brief
    assert "jueves 15 de octubre de 2026" in brief
    assert "Bandeja:" in brief
    assert "2 elementos" in brief
    assert "Maxine" in brief
    assert "ConstructionForge" in brief
    assert "Cibernettic" not in brief
    assert "Max-e" not in brief
    assert "empire-repo" not in brief


def test_emails_first_owner_address_with_no_cc(maxine, monkeypatch):
    captured = {}

    class _Svc:
        is_configured = True

        def send(self, **kwargs):
            captured.update(kwargs)
            return True

    monkeypatch.setattr(sched, "_refuse_live_brief_send", lambda: None)
    monkeypatch.setattr("app.services.max.email_service.EmailService", _Svc)
    out = sched.email_daily_brief("hola manito", datetime(2026, 10, 15, 8, 0, 0))
    assert out["sent"] is True
    assert captured.get("to") == FAKE_OWNER_EMAIL
    assert captured.get("cc") in (None, "", [])
    assert out["cc"] is None
    assert "Resumen de la mañana" in captured.get("subject", "")


def test_skips_when_owner_email_unset(tmp_path, monkeypatch):
    _maxine_env(monkeypatch, tmp_path)
    sent = []
    monkeypatch.setattr(sched, "_refuse_live_brief_send", lambda: (_ for _ in ()).throw(AssertionError("must skip")))
    monkeypatch.setattr(
        "app.services.max.email_service.EmailService.send",
        lambda *a, **k: sent.append(k) or True,
    )
    out = sched.email_daily_brief("hola")
    assert out["sent"] is False
    assert out["skipped"] is True
    assert out["to"] is None
    assert not sent


def test_skips_denied_and_hashed_studio_contacts(tmp_path, monkeypatch):
    _maxine_env(monkeypatch, tmp_path)
    sent = []

    def _capture(**kwargs):
        sent.append(kwargs)
        return True

    class _Svc:
        is_configured = True
        send = staticmethod(_capture)

    monkeypatch.setattr(sched, "_refuse_live_brief_send", lambda: None)
    monkeypatch.setattr("app.services.max.email_service.EmailService", _Svc)

    monkeypatch.setenv("EDITION_DENY_EMAIL", FAKE_SIBLING_EMAIL)
    monkeypatch.setenv("EDITION_OWNER_EMAIL", FAKE_SIBLING_EMAIL)
    denied = sched.email_daily_brief("hola")
    assert denied["skipped"] is True
    assert not sent

    studio_a = _from_hex(_ENC_STUDIO_EMAIL_A)
    studio_b = _from_hex(_ENC_STUDIO_EMAIL_B)
    for owner in (studio_a, studio_b):
        sent.clear()
        monkeypatch.setenv("EDITION_OWNER_EMAIL", owner)
        monkeypatch.delenv("EDITION_DENY_EMAIL", raising=False)
        monkeypatch.delenv("FOUNDER_EMAIL", raising=False)
        out = sched.email_daily_brief("hola")
        assert out["skipped"] is True, owner
        assert not sent
        assert sched.family_morning_brief_recipient() == ""


def test_send_never_targets_studio_contact_hashes(maxine, monkeypatch):
    captured = {}

    class _Svc:
        is_configured = True

        def send(self, **kwargs):
            captured.update(kwargs)
            return True

    monkeypatch.setattr(sched, "_refuse_live_brief_send", lambda: None)
    monkeypatch.setattr("app.services.max.email_service.EmailService", _Svc)
    sched.email_daily_brief("hola manito")
    to_hash = hashlib.sha256(captured["to"].encode("utf-8")).hexdigest()
    studio_hashes = {
        hashlib.sha256(bytes.fromhex(item)).hexdigest()
        for item in (_ENC_STUDIO_EMAIL_A, _ENC_STUDIO_EMAIL_B)
    }
    assert to_hash not in studio_hashes
    assert captured["to"] == FAKE_OWNER_EMAIL
    assert captured.get("cc") in (None, "", [])


def test_live_send_is_blocked_under_pytest(maxine):
    with pytest.raises(RuntimeError, match="mock EmailService.send"):
        sched.email_daily_brief("hola")


def _seed_overdue_task(data_dir) -> Path:
    db_path = Path(data_dir) / "empire.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'todo',
            priority TEXT NOT NULL DEFAULT 'normal',
            desk TEXT NOT NULL,
            due_date TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO tasks (id, title, status, priority, desk, due_date) "
        "VALUES (?, ?, 'todo', 'normal', 'finance', ?)",
        ("t-overdue-1", "Pagar factura", "2020-01-01"),
    )
    conn.commit()
    conn.close()
    return db_path


def test_brief_counts_one_overdue_task_from_temp_db(maxine, tmp_path):
    _seed_overdue_task(tmp_path)
    now = datetime(2026, 10, 15, 8, 0, 0)
    brief = sched.compile_daily_brief(now)
    assert "1 abiertas (1 vencidas" in brief
    assert "⚠️" in brief


def test_check_overdue_tasks_finds_seeded_task(maxine, tmp_path, monkeypatch):
    _seed_overdue_task(tmp_path)
    logged = []

    def _capture(*args, **kwargs):
        logged.append({"args": args, "kwargs": kwargs})
        return {"id": "n1"}

    monkeypatch.setattr("app.routers.notifications.notify_founder", _capture)
    asyncio.run(sched.MaxScheduler().check_overdue_tasks())
    assert logged
    title = logged[0]["args"][2] if len(logged[0]["args"]) > 2 else ""
    message = logged[0]["args"][3] if len(logged[0]["args"]) > 3 else ""
    blob = f"{title} {message}"
    assert "1 Overdue" in blob
    assert "Pagar factura" in blob
