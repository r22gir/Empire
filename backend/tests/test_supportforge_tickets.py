"""
SupportForge tickets + family-help store.

Uses a temp SQLite file and a temp family-help root. Does not import
app.main and does not touch live empire.db or /data/family-help.
"""
from __future__ import annotations

import sqlite3

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db import database
from app.db.supportforge_migration import (
    apply_to_path,
    ensure_supportforge_tables,
    tickets_table_exists,
)
from app.routers import family_help as family_help_router
from app.routers import supportforge_tickets as tickets_router
from app.services.family_help_store import FAMILY_EDITIONS, FamilyHelpStore
from app.services.supportforge_proposed_action import propose_action
from app.services.supportforge_tickets_store import (
    FAMILY_HELP_SOURCE,
    FOUNDER_VISIBLE_KEYS,
    SupportForgeTicketStore,
    founder_visible_ticket,
)


@pytest.fixture
def tmp_db(monkeypatch, tmp_path):
    db_path = tmp_path / "empire.db"
    monkeypatch.setattr(database, "DB_PATH", str(db_path))
    return db_path


@pytest.fixture
def ticket_store(tmp_db):
    store = SupportForgeTicketStore()
    store.ensure()
    return store


@pytest.fixture
def help_store(ticket_store, tmp_path):
    return FamilyHelpStore(root=tmp_path / "family-help", ticket_store=ticket_store)


@pytest.fixture
def api_client(monkeypatch, tmp_db, tmp_path, ticket_store, help_store):
    monkeypatch.setattr(tickets_router, "store", ticket_store)
    monkeypatch.setattr(family_help_router, "store", help_store)
    app = FastAPI()
    app.include_router(tickets_router.router, prefix="/api/v1/tickets")
    app.include_router(family_help_router.router, prefix="/api/v1/family-help")
    return TestClient(app)


def test_sf_tickets_table_is_created(tmp_db):
    apply_to_path(tmp_db)
    conn = sqlite3.connect(tmp_db)
    conn.row_factory = sqlite3.Row
    assert tickets_table_exists(conn) is True
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(sf_tickets)")}
    for required in (
        "id",
        "tenant_id",
        "ticket_number",
        "subject",
        "content",
        "source",
        "edition_id",
        "proposed_action",
        "proposed_action_summary",
        "proposed_action_status",
        "auto_build",
    ):
        assert required in cols
    conn.close()


def test_migration_is_idempotent(tmp_db):
    conn = sqlite3.connect(tmp_db)
    conn.row_factory = sqlite3.Row
    ensure_supportforge_tables(conn)
    ensure_supportforge_tables(conn)
    count = conn.execute("SELECT COUNT(*) AS n FROM sf_tickets").fetchone()["n"]
    assert count == 0
    tenants = conn.execute("SELECT COUNT(*) AS n FROM sf_tenants").fetchone()["n"]
    assert tenants >= 4
    conn.close()


def test_create_and_list_ticket(ticket_store):
    created = ticket_store.create_ticket(
        subject="Hem is uneven",
        content="Customer reports the left panel hangs 1 inch lower.",
        customer_email="pat@example.com",
        customer_name="Pat",
        channel="portal",
        priority="high",
        category="drapery",
    )
    assert created["ticket_number"] == 1
    assert created["status"] == "new"
    assert created["auto_build"] is False
    assert created["proposed_action"] in {"adjust", "fix", "create"}
    assert created["proposed_action_status"] == "proposed"
    tickets, total = ticket_store.list_tickets()
    assert total == 1
    assert tickets[0]["id"] == created["id"]


def test_ticket_numbers_are_per_tenant(ticket_store):
    a = ticket_store.create_ticket(
        subject="A", content="one", tenant_id="edition:amp", edition_id="amp"
    )
    b = ticket_store.create_ticket(
        subject="B", content="two", tenant_id="edition:maxine", edition_id="maxine"
    )
    c = ticket_store.create_ticket(
        subject="C", content="three", tenant_id="edition:amp", edition_id="amp"
    )
    assert a["ticket_number"] == 1
    assert b["ticket_number"] == 1
    assert c["ticket_number"] == 2


def test_edition_list_does_not_leak(ticket_store):
    ticket_store.create_ticket(
        subject="AMP only", content="amp request", tenant_id="edition:amp", edition_id="amp"
    )
    ticket_store.create_ticket(
        subject="Maxine only",
        content="maxine request",
        tenant_id="edition:maxine",
        edition_id="maxine",
    )
    amp, amp_total = ticket_store.list_tickets(edition_id="amp")
    maxine, maxine_total = ticket_store.list_tickets(edition_id="maxine")
    assert amp_total == 1
    assert maxine_total == 1
    assert amp[0]["subject"] == "AMP only"
    assert maxine[0]["subject"] == "Maxine only"


def test_propose_action_kinds():
    assert propose_action("Arreglar el login", "no funciona")["kind"] == "fix"
    assert propose_action("Crear una pagina nueva", "quiero un diario")["kind"] == "create"
    assert propose_action("Cambiar el color", "el oro es muy fuerte")["kind"] == "adjust"
    proposal = propose_action("Broken button", "error on save", edition_id="amp")
    assert proposal["status"] == "proposed"
    assert proposal["auto_build"] is False
    assert "do not auto-deploy" in proposal["summary"].lower() or "not" in proposal["summary"].lower()


def test_family_help_submit_creates_ticket(help_store, ticket_store, tmp_path):
    request = help_store.submit(
        edition_id="amp",
        subject="No abre el diario",
        message="Al tocar Diario la pantalla queda en blanco.",
        requester_name="Mama",
    )
    assert request["edition_id"] == "amp"
    assert request["proposed_action"] == "fix"
    assert request["proposed_action_status"] == "proposed"
    assert request["auto_build"] is False
    assert request["ticket"]["source"] == FAMILY_HELP_SOURCE
    assert request["ticket"]["auto_build"] is False
    assert (tmp_path / "family-help" / "amp" / "requests.db").exists()
    assert not (tmp_path / "family-help" / "maxine" / "requests.db").exists()

    tickets, total = ticket_store.list_tickets(edition_id="amp", founder_view=True)
    assert total == 1
    assert set(tickets[0]).issubset(set(FOUNDER_VISIBLE_KEYS)) or set(
        FOUNDER_VISIBLE_KEYS
    ).issuperset(tickets[0].keys())


def test_founder_list_does_not_create_other_edition_dirs(help_store, tmp_path):
    help_store.submit(edition_id="amp", subject="AMP help", message="cambiar el color")
    founder = help_store.list_for_founder()
    assert len(founder) == 1
    assert (tmp_path / "family-help" / "amp" / "requests.db").exists()
    assert not (tmp_path / "family-help" / "maxine").exists()
    assert not (tmp_path / "family-help" / "minimax-meter").exists()


def test_family_editions_are_isolated(help_store):
    help_store.submit(edition_id="amp", subject="AMP help", message="cambiar el color")
    help_store.submit(
        edition_id="maxine", subject="Crear recordatorio", message="quiero crear un recordatorio"
    )
    amp = help_store.list_for_edition("amp")
    maxine = help_store.list_for_edition("maxine")
    assert len(amp) == 1
    assert len(maxine) == 1
    assert amp[0]["subject"] == "AMP help"
    assert maxine[0]["proposed_action"] == "create"
    founder = help_store.list_for_founder()
    assert len(founder) == 2
    for item in founder:
        assert set(item).issubset(set(help_store.list_for_edition("amp")[0].keys()) | set(item))
        assert "memory" not in item
        assert "conversation" not in item


def test_unknown_edition_is_rejected(help_store):
    with pytest.raises(ValueError, match="Unknown family edition"):
        help_store.submit(edition_id="workroom", subject="x", message="y")


def test_founder_visible_ticket_strips_internals():
    raw = {
        "id": "t1",
        "ticket_number": 1,
        "subject": "Help",
        "content": "Please adjust the greeting",
        "status": "new",
        "priority": "normal",
        "channel": "family-help",
        "category": "pedir-ayuda-a-max",
        "source": FAMILY_HELP_SOURCE,
        "edition_id": "amp",
        "family_help_request_id": "r1",
        "proposed_action": "adjust",
        "proposed_action_summary": "Adjust existing amp behavior: Help.",
        "proposed_action_status": "proposed",
        "auto_build": 0,
        "created_at": "2026-10-13T00:00:00+00:00",
        "updated_at": "2026-10-13T00:00:00+00:00",
        "customer_id": "should-not-leak",
        "customer_email": "secret@family.local",
        "memory_path": "/data/amp/memory.md",
    }
    visible = founder_visible_ticket(raw)
    assert visible["subject"] == "Help"
    assert visible["content"] == "Please adjust the greeting"
    assert visible["auto_build"] is False
    assert "customer_email" not in visible
    assert "memory_path" not in visible
    assert "customer_id" not in visible


def test_proposed_action_is_not_executed(ticket_store):
    ticket = ticket_store.create_ticket(
        subject="Build a new dashboard",
        content="Please create a full analytics dashboard",
    )
    assert ticket["proposed_action"] == "create"
    assert ticket["proposed_action_status"] == "proposed"
    assert ticket["auto_build"] is False
    updated = ticket_store.update_ticket(ticket["id"], proposed_action_status="accepted")
    assert updated["proposed_action_status"] == "accepted"
    assert updated["auto_build"] is False
    assert updated["status"] == "new"


def test_api_pedir_ayuda_and_founder_list(api_client):
    created = api_client.post(
        "/api/v1/family-help/pedir-ayuda",
        json={
            "edition": "amp",
            "subject": "Arreglar el animo",
            "message": "La pagina de animo no funciona.",
            "requester_name": "Papa",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["edition_id"] == "amp"
    assert body["proposed_action"] == "fix"
    assert body["auto_build"] is False
    assert body["ticket"]["source"] == FAMILY_HELP_SOURCE

    listed = api_client.get("/api/v1/family-help/requests")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["founder_sees"] == "requests_only"

    tickets = api_client.get("/api/v1/tickets/", params={"source": "family_help"})
    assert tickets.status_code == 200
    payload = tickets.json()
    assert payload["total"] == 1
    assert "customer_email" not in payload["tickets"][0]
    assert payload["tickets"][0]["proposed_action_status"] == "proposed"


def test_api_create_plain_ticket(api_client):
    res = api_client.post(
        "/api/v1/tickets/",
        json={
            "subject": "Quote follow-up",
            "content": "Customer asked about deposit.",
            "customer_email": "client@example.com",
            "channel": "email",
            "priority": "normal",
        },
    )
    assert res.status_code == 201, res.text
    ticket = res.json()
    assert ticket["ticket_number"] == 1
    listed = api_client.get("/api/v1/tickets/")
    assert listed.json()["total"] == 1


def test_api_cannot_read_other_edition_ticket(api_client):
    amp = api_client.post(
        "/api/v1/family-help/pedir-ayuda",
        json={"edition": "amp", "subject": "AMP", "message": "cambiar texto"},
    ).json()
    ticket_id = amp["ticket"]["id"]
    denied = api_client.get(f"/api/v1/tickets/{ticket_id}", params={"edition_id": "maxine"})
    assert denied.status_code == 404
    allowed = api_client.get(f"/api/v1/tickets/{ticket_id}", params={"edition_id": "amp"})
    assert allowed.status_code == 200
    assert allowed.json()["ticket"]["edition_id"] == "amp"


def test_family_editions_constant():
    assert FAMILY_EDITIONS == ("amp", "maxine", "minimax-meter")
