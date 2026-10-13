"""On-demand family drafts — fixtures only. No live model, send, or help.db writes."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


async def _fake_reply(system: str, user: str) -> dict:
    assert "manito" in system.lower()
    assert "juan" not in system.lower() or "nunca" in system.lower()
    return {
        "text": "Claro, ya vi el botón. Lo reviso esta tarde.",
        "model_used": "minimax-MiniMax-M2.7",
        "included": True,
    }


async def _fake_manual(system: str, user: str) -> dict:
    assert "paso a paso" in system.lower() or "manual" in system.lower()
    assert "/?screen=" in user or "LIVE UI MAP" in user
    return {
        "text": (
            "Te dejo los pasos:\n"
            "1. Abre el chat de Max [Open Owner's Desk / Max chat](/?product=owner)\n"
            "2. Usa el buscador [Open Command Center](/)"
        ),
        "model_used": "minimax-MiniMax-M2.7",
        "included": True,
    }


async def _fake_names(system: str, user: str) -> dict:
    return {"text": "Juan, Camilo, ya lo vi.", "model_used": "minimax-MiniMax-M2.7", "included": True}


async def _empty_model(system: str, user: str) -> dict:
    return {"text": "", "model_used": "minimax-MiniMax-M2.7", "included": True}


@pytest.fixture()
def api(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_TEST_GUARD", "1")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("FAMILY_HELP_INBOX_DIR", str(tmp_path / "family-help"))
    monkeypatch.setenv("FAMILY_REQUEST_LOG_DB", str(tmp_path / "data" / "family_request_log.db"))
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "data" / "empire.db"))
    monkeypatch.setenv("EMPIRE_EDITION", "main")
    from app.routers import family_help
    from app.services import family_help_drafts, family_help_store

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
        help_maxine=tmp_path / "family-help" / "maxine" / "help.db",
        drafts=family_help_drafts,
        store=family_help_store,
    )


def test_included_model_refuses_live_call_under_test(api):
    with pytest.raises(RuntimeError, match="mocked"):
        import asyncio
        asyncio.run(api["drafts"].call_max_included_model("sys", "user"))


def test_polish_uses_manito_never_names():
    from app.services.family_help_drafts import polish_draft
    out = polish_draft("Juan, Camilo, ya lo arreglé.")
    assert "manito" in out.lower()
    assert "juan" not in out.lower()
    assert "camilo" not in out.lower()


def test_related_features_come_from_ui_map():
    from app.services.family_help_drafts import related_features
    feats = related_features("crear un recado nuevo para mamá")
    ids = {f.id for f in feats}
    assert "organizer" in ids or "tasks" in ids
    assert "workroom" not in ids
    assert "jobs" not in ids


def test_generate_reply_is_draft_only(api):
    import asyncio
    from app.services.family_help_store import get_ticket
    ticket = get_ticket("fh-juan1")
    draft = asyncio.run(api["drafts"].generate_reply(ticket, generate_fn=_fake_reply))
    assert draft["kind"] == "reply"
    assert draft["would_send"] is False
    assert draft["saved"] is False
    assert draft["included_model"] is True
    assert "minimax" in draft["model_used"]
    assert "manito" in draft["body"].lower()
    assert "juan" not in draft["body"].lower()


def test_generate_manual_injects_ui_map_links(api):
    import asyncio
    from app.services.family_help_store import get_ticket
    ticket = get_ticket("fh-camilo1")
    draft = asyncio.run(api["drafts"].generate_manual(ticket, generate_fn=_fake_manual))
    assert draft["kind"] == "manual"
    assert draft["would_send"] is False
    assert draft["saved"] is False
    assert draft["steps"]
    assert any(s.get("href") and s["href"].startswith("/") for s in draft["steps"])
    assert "manito" in draft["body"].lower()
    assert "camilo" not in draft["body"].lower()
    assert "studio.empirebox.store" not in draft["body"]
    assert any("/?screen=tasks" in (s.get("href") or "") or s.get("href") == "/" or "/?product=" in (s.get("href") or "") for s in draft["steps"]) or draft["screens"]


def test_generate_reply_endpoint_does_not_send_or_write_help_db(api, monkeypatch):
    async def fake(system, user):
        return await _fake_reply(system, user)

    monkeypatch.setattr(api["drafts"], "call_max_included_model", fake)
    before = api["help_amp"].read_bytes()
    res = api["client"].post("/api/v1/family-help/inbox/fh-juan1/generate-reply")
    assert res.status_code == 200
    body = res.json()
    assert body["would_send"] is False
    assert body["saved"] is False
    assert body["draft"]["kind"] == "reply"
    assert "manito" in body["draft"]["body"].lower()
    assert api["help_amp"].read_bytes() == before
    detail = api["client"].get("/api/v1/family-help/inbox/fh-juan1").json()["ticket"]
    assert not any(e["kind"] == "reply" for e in detail.get("log") or [])
    assert api["client"].get("/api/v1/family-help/guides?edition=amp").json()["guides"] == []


def test_generate_manual_endpoint_uses_ui_map(api, monkeypatch):
    async def fake(system, user):
        return await _fake_manual(system, user)

    monkeypatch.setattr(api["drafts"], "call_max_included_model", fake)
    before = api["help_maxine"].read_bytes()
    res = api["client"].post("/api/v1/family-help/inbox/fh-camilo1/generate-manual")
    assert res.status_code == 200
    draft = res.json()["draft"]
    assert draft["kind"] == "manual"
    assert draft["screens"]
    assert all(not s.get("href", "").startswith("https://studio") for s in draft["screens"])
    assert api["help_maxine"].read_bytes() == before


def test_send_draft_is_explicit_and_stays_on_studio_log(api, monkeypatch):
    async def fake(system, user):
        return await _fake_reply(system, user)

    monkeypatch.setattr(api["drafts"], "call_max_included_model", fake)
    gen = api["client"].post("/api/v1/family-help/inbox/fh-juan1/generate-reply")
    draft_body = gen.json()["draft"]["body"]
    before = api["help_amp"].read_bytes()
    res = api["client"].post(
        "/api/v1/family-help/inbox/fh-juan1/send-draft",
        json={"body": draft_body, "author": "Max", "explicit_yes": True},
    )
    assert res.status_code == 200
    assert res.json()["wrote_help_db"] is False
    assert any(e["kind"] == "reply" for e in res.json()["ticket"]["log"])
    assert api["help_amp"].read_bytes() == before


def test_save_guide_is_isolated_per_edition(api, monkeypatch):
    async def fake(system, user):
        return await _fake_manual(system, user)

    monkeypatch.setattr(api["drafts"], "call_max_included_model", fake)
    draft = api["client"].post("/api/v1/family-help/inbox/fh-camilo1/generate-manual").json()["draft"]
    before_amp = api["help_amp"].read_bytes()
    before_maxine = api["help_maxine"].read_bytes()
    res = api["client"].post(
        "/api/v1/family-help/inbox/fh-camilo1/save-guide",
        json={"title": draft["title"], "body": draft["body"], "steps": draft["steps"]},
    )
    assert res.status_code == 200
    assert res.json()["saved"] is True
    guide = res.json()["guide"]
    assert guide["edition"] == "maxine"
    listed = api["client"].get("/api/v1/family-help/guides?edition=maxine").json()["guides"]
    assert {g["id"] for g in listed} == {guide["id"]}
    other = api["client"].get("/api/v1/family-help/guides?edition=amp").json()["guides"]
    assert other == []
    assert api["help_amp"].read_bytes() == before_amp
    assert api["help_maxine"].read_bytes() == before_maxine


def test_family_edition_cannot_read_other_guides(api, monkeypatch):
    from app.services import family_request_log
    family_request_log.save_guide("amp", title="Max-e only", body="Manito, solo Max-e.")
    family_request_log.save_guide("maxine", title="Maxine only", body="Manito, solo Maxine.")
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    res = api["client"].get("/api/v1/family-help/guides?edition=maxine")
    assert res.status_code == 403
    mine = api["client"].get("/api/v1/family-help/guides")
    assert mine.status_code == 200
    assert {g["edition"] for g in mine.json()["guides"]} == {"amp"}


def test_family_edition_cannot_generate(api, monkeypatch):
    monkeypatch.setenv("EMPIRE_EDITION", "maxine")
    res = api["client"].post("/api/v1/family-help/inbox/fh-camilo1/generate-reply")
    assert res.status_code == 403


def test_fallback_manual_has_tappable_links(api):
    from app.services.family_help_drafts import fallback_manual, related_features
    ticket = api["store"].get_ticket("fh-camilo1")
    feats = related_features(ticket["message"])
    body = fallback_manual(ticket, feats)
    assert "manito" in body.lower()
    assert "](/" in body
    assert "camilo" not in body.lower()
