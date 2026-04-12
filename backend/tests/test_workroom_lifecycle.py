import importlib
import asyncio
import json

from starlette.requests import Request


def _request() -> Request:
    return Request({"type": "http", "method": "GET", "path": "/test", "headers": []})


def _load_lifecycle_modules(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))

    from app.db import database

    importlib.reload(database)

    from app.db import init_db

    importlib.reload(init_db)
    init_db.init_database()

    from app.routers import jobs_unified

    importlib.reload(jobs_unified)

    from app.routers import customer_mgmt, finance, quotes

    importlib.reload(quotes)
    importlib.reload(finance)
    importlib.reload(customer_mgmt)

    quotes_dir = tmp_path / "quotes"
    quotes_dir.mkdir()
    monkeypatch.setattr(quotes, "QUOTES_DIR", str(quotes_dir))
    monkeypatch.setattr(quotes, "COUNTER_FILE", str(quotes_dir / "_counter.json"))
    monkeypatch.setattr(finance, "QUOTES_DIR", quotes_dir)
    monkeypatch.setattr(customer_mgmt, "QUOTES_DIR", quotes_dir)

    return quotes, finance, customer_mgmt, quotes_dir


def _write_quote(quotes_dir, quote):
    (quotes_dir / f"{quote['id']}.json").write_text(json.dumps(quote))


def test_workroom_quote_invoice_payment_crm_lifecycle(monkeypatch, tmp_path):
    quotes, finance, customer_mgmt, quotes_dir = _load_lifecycle_modules(monkeypatch, tmp_path)

    workroom_quote = {
        "id": "workroom-quote",
        "quote_number": "EST-2026-001",
        "status": "accepted",
        "customer_name": "Ada Client",
        "customer_email": "ada@example.com",
        "customer_phone": "555-0100",
        "customer_address": "10 Drapery Ln",
        "project_name": "Living Room Panels",
        "project_description": "Install drapery panels from intake",
        "line_items": [
            {"description": "Panels", "quantity": 3, "rate": 100, "amount": 300}
        ],
        "subtotal": 300,
        "tax_rate": 0.1,
        "tax_amount": 30,
        "discount_amount": 20,
        "discount_type": "dollar",
        "total": 310,
        "deposit": {"deposit_percent": 50, "deposit_amount": 155},
        "terms": "50% deposit, balance on install",
        "notes": "Carry intake notes",
        "business_unit": "workroom",
        "created_at": "2026-04-11T10:00:00",
        "updated_at": "2026-04-11T10:00:00",
    }
    woodcraft_quote = {
        **workroom_quote,
        "id": "woodcraft-quote",
        "quote_number": "EST-2026-002",
        "customer_name": "Wood Client",
        "customer_email": "wood@example.com",
        "business_unit": "woodcraft",
    }
    _write_quote(quotes_dir, workroom_quote)
    _write_quote(quotes_dir, woodcraft_quote)

    workroom_list = asyncio.run(quotes.list_quotes(
        status=None, limit=50, offset=0, business="workroom", summary=True
    ))
    woodcraft_list = asyncio.run(quotes.list_quotes(
        status=None, limit=50, offset=0, business="woodcraft", summary=True
    ))

    assert [q["id"] for q in workroom_list["quotes"]] == ["workroom-quote"]
    assert [q["id"] for q in woodcraft_list["quotes"]] == ["woodcraft-quote"]

    invoice_response = finance.create_invoice_from_quote(_request(), "workroom-quote")
    invoice = invoice_response["invoice"]

    assert invoice["quote_id"] == "workroom-quote"
    assert invoice["customer_id"]
    assert invoice["client_name"] == "Ada Client"
    assert invoice["client_email"] == "ada@example.com"
    assert invoice["client_phone"] == "555-0100"
    assert invoice["client_address"] == "10 Drapery Ln"
    assert invoice["business_unit"] == "workroom"
    assert invoice["deposit_required"] == 155
    assert invoice["deposit_received"] == 0
    assert invoice["discount_amount"] == 20
    assert invoice["discount_type"] == "dollar"
    assert invoice["total"] == 310
    assert invoice["balance_due"] == 310
    assert invoice["line_items"][0]["description"] == "Panels"

    payment_response = finance.record_payment(
        _request(),
        invoice["id"],
        finance.PaymentCreate(amount=155, method="check", reference="CHK-155"),
    )
    paid_invoice = payment_response["invoice"]

    assert paid_invoice["amount_paid"] == 155
    assert paid_invoice["balance_due"] == 155
    assert paid_invoice["status"] == "partial"

    customer_response = customer_mgmt.get_customer(_request(), invoice["customer_id"])
    customer = customer_response["customer"]

    assert customer["business"] == "workroom"
    assert customer["email"] == "ada@example.com"
    assert len(customer["quotes"]) == 1
    assert customer["quotes"][0]["id"] == "workroom-quote"
    assert len(customer["invoices"]) == 1
    assert customer["invoices"][0]["quote_id"] == "workroom-quote"
    assert len(customer["payments"]) == 1
    assert customer["payments"][0]["amount"] == 155
