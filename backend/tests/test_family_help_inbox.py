"""Founder inbox API — temp trees only. Does not import app.main."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture()
def api(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_TEST_GUARD", "1")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("FAMILY_HELP_INBOX_DIR", str(tmp_path / "family-help"))
    monkeypatch.setenv("FAMILY_REQUEST_LOG_DB", str(tmp_path / "data" / "family_request_log.db"))
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "data" / "empire.db"))
    monkeypatch.setenv("EMPIRE_EDITION", "main")
    from app.routers import family_help
    from app.services import family_help_store
    family_help_store.write_ticket_for_tests(
        edition="amp",
        ticket_id="fh-juan1",
        sender="Juan",
        message="El botón de perfil no funciona",
        created_at="2026-10-13T12:00:00+00:00",
        attachments=[{
            "id": "att-1",
            "kind": "file",
            "filename": "shot.png",
            "content_type": "image/png",
            "size": 4,
            "stored_name": "shot.png",
            "data": b"\x89PNG",
        }],
    )
    family_help_store.write_ticket_for_tests(
        edition="maxine",
        ticket_id="fh-camilo1",
        sender="Camilo",
        message="crear un recado nuevo para mamá",
        created_at="2026-10-13T13:00:00+00:00",
    )
    app = FastAPI()
    app.include_router(family_help.router, prefix="/api/v1")
    return dict(
        client=TestClient(app),
        tmp=tmp_path,
        help_amp=tmp_path / "family-help" / "amp" / "help.db",
    )


def test_inbox_lists_who_date_summary_attachments_type(api):
    res = api["client"].get("/api/v1/family-help/inbox")
    assert res.status_code == 200
    tickets = res.json()["tickets"]
    assert {t["id"] for t in tickets} == {"fh-juan1", "fh-camilo1"}
    juan = next(t for t in tickets if t["edition"] == "amp")
    camilo = next(t for t in tickets if t["edition"] == "maxine")
    assert juan["who_label"] == "Juan / Max-e"
    assert camilo["who_label"] == "Camilo / Maxine"
    assert juan["request_type"] == "fix"
    assert camilo["request_type"] == "create"
    assert juan["log_status"] == "new"
    assert juan["attachments"][0]["filename"] == "shot.png"
    assert juan["unread"] is True


def test_unread_count_and_mark_seen(api):
    res = api["client"].get("/api/v1/family-help/unread-count")
    assert res.json()["unread"] == 2
    api["client"].get("/api/v1/family-help/inbox/fh-juan1")
    res = api["client"].get("/api/v1/family-help/unread-count")
    assert res.json()["unread"] == 1


def test_patch_type_status_and_log_without_writing_help_db(api):
    before = api["help_amp"].read_bytes()
    res = api["client"].patch(
        "/api/v1/family-help/requests/amp/fh-juan1",
        json={"request_type": "adjust", "status": "in_progress"},
    )
    assert res.status_code == 200
    ticket = res.json()["ticket"]
    assert ticket["request_type"] == "adjust"
    assert ticket["log_status"] == "in_progress"
    res = api["client"].post(
        "/api/v1/family-help/requests/amp/fh-juan1/log",
        json={"body": "Opened draft PR", "href": "https://github.com/r22gir/Empire/pull/1", "href_label": "PR #1"},
    )
    assert res.status_code == 200
    log = res.json()["ticket"]["log"]
    assert any(e["href"] and "pull/1" in e["href"] for e in log)
    assert api["help_amp"].read_bytes() == before


def test_reply_stays_on_studio_log(api):
    before = api["help_amp"].read_bytes()
    res = api["client"].post(
        "/api/v1/family-help/inbox/fh-juan1/reply",
        json={"body": "Lo veo, lo arreglo esta tarde.", "author": "Max", "explicit_yes": True},
    )
    assert res.status_code == 200
    assert res.json()["wrote_help_db"] is False
    assert any(e["kind"] == "reply" for e in res.json()["ticket"]["log"])
    assert api["help_amp"].read_bytes() == before


def test_organizer_task_action(api):
    res = api["client"].post("/api/v1/family-help/requests/amp/fh-juan1/organizer-task", json={})
    assert res.status_code == 200
    task = res.json()["task"]
    assert task["area"] == "Empire"
    assert task["id"]
    assert "/?screen=tasks" in task["href"]


def test_family_edition_cannot_open_inbox(api, monkeypatch):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    res = api["client"].get("/api/v1/family-help/inbox")
    assert res.status_code == 403


def test_attachment_is_readable(api):
    res = api["client"].get("/api/v1/family-help/inbox/fh-juan1/attachments/att-1")
    assert res.status_code == 200
    assert res.content.startswith(b"\x89PNG")
