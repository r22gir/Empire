"""ForgeCRM unified WhatsApp/SMS thread — draft-only outbound, no auto-replies."""
import importlib

from fastapi import HTTPException


def _load(monkeypatch, tmp_path, **env):
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))
    monkeypatch.setenv("FEATURE_FORGECRM_MESSAGING", "true")
    for key, val in env.items():
        monkeypatch.setenv(key, val)

    from app.db import database

    importlib.reload(database)

    from app.db import init_db

    importlib.reload(init_db)
    init_db.init_database()

    from app.routers import crm_messaging
    from app.services import crm_messaging as crm

    importlib.reload(crm)
    importlib.reload(crm_messaging)
    return crm_messaging, crm, database


def _customer(database, name="Ada Client", phone="+1 (555) 010-1234"):
    with database.get_db() as conn:
        conn.execute(
            """INSERT INTO customers (id, name, phone, email, type, source, business)
               VALUES ('cust_ada', ?, ?, 'ada@example.com', 'residential', 'direct', 'empire')""",
            (name, phone),
        )
    return "cust_ada"


def test_inbound_whatsapp_and_sms_share_one_thread(monkeypatch, tmp_path):
    routes, crm, database = _load(monkeypatch, tmp_path)
    customer_id = _customer(database)

    wa = routes.whatsapp_inbound(
        routes.InboundWebhook(
            channel="whatsapp",
            body="Hola, is the sofa ready?",
            from_address="+15550101234",
            provider_message_id="wa-1",
        ),
    )
    sms = routes.sms_inbound(
        routes.InboundWebhook(
            channel="sms",
            body="Also sending this by text",
            from_address="555-010-1234",
            provider_message_id="sms-1",
        ),
    )
    thread = routes.get_customer_thread(customer_id)

    assert wa["auto_reply"] is False
    assert wa["reply"] is None
    assert sms["auto_reply"] is False
    assert thread["thread"]["id"] == wa["message"]["thread_id"] == sms["message"]["thread_id"]
    assert thread["counts"]["inbound"] == 2
    assert thread["counts"]["outbound_drafts"] == 0
    assert thread["policy"]["automatic_replies"] is False
    channels = {m["channel"] for m in thread["messages"]}
    assert channels == {"whatsapp", "sms"}
    assert all(m["direction"] == "inbound" for m in thread["messages"])


def test_inbound_never_creates_outbound_or_auto_reply(monkeypatch, tmp_path):
    routes, crm, database = _load(monkeypatch, tmp_path)
    _customer(database)
    with database.get_db() as conn:
        result = crm.ingest_inbound(
            conn,
            channel="whatsapp",
            body="Need a quote",
            from_address="5550101234",
        )
        crm.assert_no_auto_reply(result)
        payload = crm.webhook_ingest_only(result)
        assert payload["reply"] is None
        outbound = conn.execute(
            "SELECT COUNT(*) FROM crm_thread_messages WHERE direction = 'outbound'"
        ).fetchone()[0]
        assert outbound == 0


def test_compose_is_draft_only_and_send_requires_owner_approve(monkeypatch, tmp_path):
    routes, crm, database = _load(monkeypatch, tmp_path)
    customer_id = _customer(database)

    draft = routes.create_outbound_draft(
        customer_id,
        routes.DraftCreate(body="Thanks — we will confirm pickup.", channel="whatsapp"),
    )
    assert draft["sent"] is False
    assert draft["message"]["status"] == "draft"
    assert draft["message"]["needs_owner_approval"] is True
    message_id = draft["message"]["id"]

    try:
        routes.send_blocked_without_approval(customer_id, message_id)
        assert False, "send without approve must fail"
    except HTTPException as exc:
        assert exc.status_code == 403
        assert "approve" in str(exc.detail).lower()

    approved = routes.approve_outbound(
        customer_id,
        message_id,
        routes.ApproveRequest(owner_id="founder"),
    )
    assert approved["live_send"] is False
    assert approved["transport"] == "sandbox_local"
    assert approved["message"]["status"] == "sent_sandbox"
    assert approved["message"]["approved_by"] == "founder"

    thread = routes.get_customer_thread(customer_id)
    assert thread["counts"]["outbound_drafts"] == 0
    assert thread["counts"]["outbound_sent"] == 1


def test_approval_is_per_message_not_thread_wide(monkeypatch, tmp_path):
    routes, _crm, database = _load(monkeypatch, tmp_path)
    customer_id = _customer(database)
    first = routes.create_outbound_draft(
        customer_id, routes.DraftCreate(body="Draft one", channel="sms")
    )
    second = routes.create_outbound_draft(
        customer_id, routes.DraftCreate(body="Draft two", channel="sms")
    )
    routes.approve_outbound(
        customer_id,
        first["message"]["id"],
        routes.ApproveRequest(owner_id="owner"),
    )
    thread = routes.get_customer_thread(customer_id)
    by_id = {m["id"]: m for m in thread["messages"]}
    assert by_id[first["message"]["id"]]["status"] == "sent_sandbox"
    assert by_id[second["message"]["id"]]["status"] == "draft"
    assert by_id[second["message"]["id"]]["needs_owner_approval"] is True


def test_duplicate_provider_id_does_not_duplicate_or_reply(monkeypatch, tmp_path):
    routes, _crm, database = _load(monkeypatch, tmp_path)
    _customer(database)
    payload = routes.InboundWebhook(
        channel="sms",
        body="Same inbound twice",
        from_address="5550101234",
        provider_message_id="dup-9",
    )
    first = routes.sms_inbound(payload)
    second = routes.sms_inbound(payload)
    assert first["created"] is True
    assert second["created"] is False
    assert second["auto_reply"] is False
    thread = routes.get_customer_thread("cust_ada")
    assert thread["counts"]["inbound"] == 1
