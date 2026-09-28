import asyncio
import importlib
import json

from starlette.requests import Request


def _request() -> Request:
    return Request({"type": "http", "method": "POST", "path": "/api/v1/crm/customers", "headers": []})


def _load_crm(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))

    from app.db import database, init_db

    importlib.reload(database)
    importlib.reload(init_db)
    init_db.init_database()

    from app.routers import customer_mgmt, leadforge, quotes
    from app.services.max.response_quality_engine import QualityResult

    importlib.reload(customer_mgmt)
    importlib.reload(quotes)
    importlib.reload(leadforge)

    quotes_dir = tmp_path / "quotes"
    quotes_dir.mkdir()
    monkeypatch.setattr(quotes, "QUOTES_DIR", str(quotes_dir))
    monkeypatch.setattr(quotes, "COUNTER_FILE", str(quotes_dir / "_counter.json"))
    monkeypatch.setattr(
        quotes.quality_engine,
        "validate",
        lambda content, channel, context: QualityResult(
            original=content,
            cleaned=content,
            channel=getattr(channel, "value", str(channel)),
            mode="test",
        ),
    )
    return customer_mgmt, leadforge, quotes, database


def _customer_count(database) -> int:
    with database.get_db() as conn:
        return conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]


def test_manual_workroom_upsert_is_case_insensitive_and_keeps_source(monkeypatch, tmp_path):
    customer_mgmt, _leadforge, _quotes, database = _load_crm(monkeypatch, tmp_path)

    first = customer_mgmt.create_customer(
        _request(),
        customer_mgmt.CustomerCreate(
            name="Ada Draper",
            email="Ada@Example.com",
            business_unit="workroom",
            capture="manual",
            source="showroom",
            source_url="https://empirebox.example/showroom",
            utm_source="qr",
            utm_medium="print",
            utm_campaign="georgetown",
            tags=["designer"],
        ),
    )
    second = customer_mgmt.create_customer(
        _request(),
        customer_mgmt.CustomerCreate(
            name="Ada Draper",
            email="ada@example.com",
            phone=None,
            business="workroom",
            capture="manual",
            source="website",
            utm_source="google",
            utm_campaign="other",
        ),
    )

    assert first["upsert_outcome"] == "created"
    assert second["upsert_outcome"] == "matched"
    assert first["customer_id"] == second["customer_id"]
    assert _customer_count(database) == 1

    customer = second["customer"]
    assert customer["phone"] in (None, "")
    assert customer["business"] == "workroom"
    assert customer["source"] == "showroom"
    assert customer["source_url"] == "https://empirebox.example/showroom"
    assert customer["utm_source"] == "qr"
    assert customer["utm_medium"] == "print"
    assert customer["utm_campaign"] == "georgetown"
    assert "workroom" in customer["tags"]
    assert "manual" in customer["tags"]
    assert "designer" in customer["tags"]


def test_leadforge_and_luxeforge_workroom_leads_share_one_contact(monkeypatch, tmp_path):
    customer_mgmt, leadforge, _quotes, database = _load_crm(monkeypatch, tmp_path)

    created = leadforge.create_lead(leadforge.LeadCreate(
        business_unit="workroom",
        first_name="Bea",
        last_name="Linen",
        email="Bea@Workroom.test",
        source="designer_referral",
        source_url="https://leadforge.example/bea",
        utm_source="instagram",
        utm_medium="social",
        utm_campaign="spring_drapery",
        tags=["trade"],
    ))
    again = leadforge.create_lead(leadforge.LeadCreate(
        business_unit="workroom",
        first_name="Bea",
        last_name="Linen",
        email="bea@workroom.test",
        phone="555-0142",
        source="cold_call",
        utm_source="email",
        utm_campaign="followup",
    ))

    assert created["upsert_outcome"] == "created"
    assert again["upsert_outcome"] == "matched"
    assert created["customer_id"] == again["customer_id"]
    assert again["customer"]["phone"] == "555-0142"
    assert again["customer"]["source"] == "designer_referral"
    assert again["customer"]["utm_source"] == "instagram"
    assert again["customer"]["utm_medium"] == "social"
    assert again["customer"]["utm_campaign"] == "spring_drapery"
    assert again["customer"]["business"] == "workroom"
    assert {"workroom", "leadforge", "trade"} <= set(again["customer"]["tags"])

    from app.routers import intake_auth

    intake_auth._capture_luxeforge_contact(intake_auth.SignupRequest(
        name="Bea Linen",
        email="BEA@workroom.test",
        password="secret123",
        business="workroom",
        source="luxeforge_form",
        utm_source="pinterest",
        utm_medium="social",
        utm_campaign="lookbook",
    ))

    assert _customer_count(database) == 1
    with database.get_db() as conn:
        row = conn.execute(
            "SELECT * FROM customers WHERE id = ?",
            (created["customer_id"],),
        ).fetchone()
    customer = customer_mgmt._enrich_customer(dict(row))
    assert customer["source"] == "designer_referral"
    assert customer["utm_campaign"] == "spring_drapery"
    assert "luxeforge" in customer["tags"]
    assert customer["business"] == "workroom"


def test_promote_reuses_workroom_contact_without_a_second_row(monkeypatch, tmp_path):
    _customer_mgmt, leadforge, _quotes, database = _load_crm(monkeypatch, tmp_path)

    leadforge.create_lead(leadforge.LeadCreate(
        business_unit="workroom",
        first_name="Dee",
        last_name="Hem",
        email="dee@workroom.test",
        source="showroom",
        utm_source="card",
        utm_medium="print",
        utm_campaign="desk",
    ))
    second = leadforge.create_lead(leadforge.LeadCreate(
        business_unit="workroom",
        first_name="Dee",
        last_name="Hem",
        email="DEE@workroom.test",
        source="website",
    ))
    # Clear the link so promote exercises the shared upsert instead of the no-op.
    with leadforge._db() as conn:
        conn.execute("UPDATE lf_leads SET customer_id = NULL WHERE id = ?", (second["lead"]["id"],))

    promoted = leadforge.promote_lead_to_forgecrm(second["lead"]["id"])

    assert promoted["promote_outcome"] == "promoted"
    assert promoted["dedupe_outcome"] == "matched"
    assert promoted["customer_id"] == second["customer_id"]
    assert promoted["customer"]["source"] == "showroom"
    assert promoted["customer"]["utm_campaign"] == "desk"
    assert promoted["customer"]["business"] == "workroom"
    assert "workroom" in promoted["customer"]["tags"]
    assert _customer_count(database) == 1

    again = leadforge.promote_lead_to_forgecrm(second["lead"]["id"])
    assert again["promote_outcome"] == "already_promoted"
    assert _customer_count(database) == 1


def test_workroom_quote_create_reuses_contact_and_copies_handoff(monkeypatch, tmp_path):
    customer_mgmt, _leadforge, quotes, database = _load_crm(monkeypatch, tmp_path)

    captured = customer_mgmt.create_customer(
        _request(),
        customer_mgmt.CustomerCreate(
            name="Cara Shade",
            email="Cara@Example.com",
            business_unit="workroom",
            capture="leadforge",
            source="trade_show",
            source_url="https://leadforge.example/cara",
            utm_source="qr",
            utm_medium="badge",
            utm_campaign="highpoint",
        ),
    )

    response = asyncio.run(quotes.create_quote(quotes.QuoteCreate(
        customer_name="Cara Shade",
        customer_email="cara@example.com",
        business_unit="workroom",
        project_name="Dining Room Drapery",
        line_items=[{"description": "Panels", "quantity": 2, "rate": 100}],
    )))
    quote = response["quote"]

    assert quote["customer_id"] == captured["customer_id"]
    assert quote["business_unit"] == "workroom"
    handoff = quote["crm_handoff"]
    assert handoff["customer_id"] == captured["customer_id"]
    assert handoff["email"] == "Cara@Example.com"
    assert handoff["business"] == "workroom"
    assert handoff["source"] == "trade_show"
    assert handoff["source_url"] == "https://leadforge.example/cara"
    assert handoff["utm_source"] == "qr"
    assert handoff["utm_medium"] == "badge"
    assert handoff["utm_campaign"] == "highpoint"
    assert "workroom" in handoff["tags"]
    assert "leadforge" in handoff["tags"]
    assert handoff["phone"] in (None, "")

    asyncio.run(quotes.create_quote(quotes.QuoteCreate(
        customer_name="Cara Shade",
        customer_email="CARA@example.com",
        customer_id=captured["customer_id"],
        business_unit="workroom",
        source="quote",
        utm_source="quote_form",
        line_items=[{"description": "Lining", "quantity": 1, "rate": 40}],
    )))

    assert _customer_count(database) == 1
    listed = customer_mgmt.get_customer(_request(), captured["customer_id"])["customer"]
    assert listed["source"] == "trade_show"
    assert listed["utm_source"] == "qr"
    assert listed["business"] == "workroom"
