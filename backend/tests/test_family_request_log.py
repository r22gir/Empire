"""Studio family request log — isolated temp trees only.

Never imports app.main. Never writes live empire.db or /data/family-help.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.services.supportforge_proposed_action import (
    classify_proposed_action,
    propose_action,
)


@pytest.fixture()
def studio(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_TEST_GUARD", "1")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("FAMILY_HELP_INBOX_DIR", str(tmp_path / "family-help"))
    monkeypatch.setenv("FAMILY_REQUEST_LOG_DB", str(tmp_path / "data" / "family_request_log.db"))
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "data" / "empire.db"))
    monkeypatch.setenv("EMPIRE_EDITION", "main")
    from app.services import family_help_store, family_request_log
    return dict(tmp=tmp_path, store=family_help_store, log=family_request_log)


def _ticket(store, **kwargs):
    defaults = dict(
        edition="amp",
        ticket_id="fh-juan1",
        sender="Juan",
        message="El botón de perfil no funciona",
        created_at="2026-10-13T12:00:00+00:00",
    )
    defaults.update(kwargs)
    return store.write_ticket_for_tests(**defaults)


def test_pr124_classifier_adjust_fix_create():
    assert classify_proposed_action("can you tweak the colors") == "adjust"
    assert classify_proposed_action("el botón está roto") == "fix"
    assert classify_proposed_action("crear una nueva página") == "create"
    proposed = propose_action("arreglar el login", edition_id="amp")
    assert proposed["kind"] == "fix"
    assert proposed["status"] == "proposed"
    assert proposed["auto_build"] is False


def test_store_reads_help_db_readonly(studio):
    store = studio["store"]
    path = _ticket(store, attachments=[{
        "id": "att-1", "kind": "file", "filename": "shot.png",
        "content_type": "image/png", "size": 4, "stored_name": "shot.png",
        "data": b"\x89PNG",
    }])
    before = path.read_bytes()
    rows = store.list_tickets()
    assert len(rows) == 1
    assert rows[0]["who_label"] == "Juan / Max-e"
    assert rows[0]["attachments"][0]["filename"] == "shot.png"
    assert path.read_bytes() == before
    assert store.get_ticket("fh-juan1")["edition"] == "amp"


def test_store_refuses_live_data_paths_in_tests(studio, monkeypatch, tmp_path):
    store = studio["store"]
    monkeypatch.setenv("FAMILY_HELP_INBOX_DIR", "/data/family-help")
    monkeypatch.setenv("FAMILY_HELP_AMP_DIR", "/data/amp/family-help/amp")
    assert store.help_db_path("amp") is None
    with pytest.raises(RuntimeError):
        store.write_ticket_for_tests(
            edition="amp",
            ticket_id="nope",
            sender="x",
            message="x",
            created_at="2026-10-13T12:00:00+00:00",
            base=Path("/data/family-help"),
        )


def test_studio_log_never_uses_help_db(studio):
    store, log = studio["store"], studio["log"]
    help_path = _ticket(store)
    before = help_path.read_bytes()
    log.ensure_meta("amp", "fh-juan1", message="El botón de perfil no funciona")
    log.update_meta("amp", "fh-juan1", status="planned")
    log.add_log("amp", "fh-juan1", body="Opened PR #999", href="https://example.com/p/999", href_label="PR")
    assert help_path.read_bytes() == before
    assert not str(log.log_db_path()).endswith("help.db")
    meta = log.get_meta("amp", "fh-juan1")
    assert meta["status"] == "planned"
    assert meta["proposal_status"] == "accepted"
    assert meta["request_type"] == "fix"
    assert meta["log"][-1]["href"] == "https://example.com/p/999"


def test_unread_until_seen(studio):
    store, log = studio["store"], studio["log"]
    _ticket(store)
    _ticket(store, edition="maxine", ticket_id="fh-camilo1", sender="Camilo", message="crear un recado")
    tickets = store.list_tickets()
    seen = log.unread_ticket_ids()
    unread = [t for t in tickets if (t["edition"], t["id"]) not in seen]
    assert len(unread) == 2
    log.mark_seen("amp", "fh-juan1", message="El botón de perfil no funciona")
    seen = log.unread_ticket_ids()
    unread = [t for t in tickets if (t["edition"], t["id"]) not in seen]
    assert len(unread) == 1
    assert unread[0]["edition"] == "maxine"


def test_type_is_editable(studio):
    store, log = studio["store"], studio["log"]
    _ticket(store)
    meta = log.ensure_meta("amp", "fh-juan1", message="El botón de perfil no funciona")
    assert meta["request_type"] == "fix"
    assert meta["type_edited"] is False
    meta = log.update_meta("amp", "fh-juan1", request_type="adjust")
    assert meta["request_type"] == "adjust"
    assert meta["type_edited"] is True


def test_organizer_task_area_empire(studio):
    store, log = studio["store"], studio["log"]
    _ticket(store)
    meta = log.create_organizer_task(
        "amp",
        "fh-juan1",
        title="Fix Max-e profile button",
        description="From Juan",
        message="El botón de perfil no funciona",
    )
    task = meta["organizer_task"]
    assert task["area"] == "Empire"
    assert task["id"]
    assert task["href"].startswith("/?screen=tasks")
    from app.db.database import get_db
    with get_db() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task["id"],)).fetchone()
        assert row["business"] == "empire"
        assert row["desk"] == "empire"
    help_path = studio["tmp"] / "family-help" / "amp" / "help.db"
    # help.db still only has the original ticket — no studio columns
    import sqlite3
    conn = sqlite3.connect(str(help_path))
    cols = {r[1] for r in conn.execute("PRAGMA table_info(tickets)")}
    conn.close()
    assert "request_type" not in cols
    assert "organizer_task_id" not in cols
