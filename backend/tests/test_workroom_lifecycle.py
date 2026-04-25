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


def test_from_rooms_uses_selected_catalog_pricing_and_syncs_crm(monkeypatch, tmp_path):
    quotes, _, _, quotes_dir = _load_lifecycle_modules(monkeypatch, tmp_path)

    with quotes.get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS fabrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                color_pattern TEXT,
                material_type TEXT,
                supplier TEXT,
                supplier_link TEXT,
                cost_per_yard REAL DEFAULT 0,
                margin_percent REAL DEFAULT 0,
                durability TEXT,
                pattern_repeat_h REAL DEFAULT 0,
                pattern_repeat_v REAL DEFAULT 0,
                width_inches REAL DEFAULT 54,
                backing_fabric_id INTEGER,
                swatch_photo_path TEXT,
                notes TEXT,
                is_active INTEGER DEFAULT 1,
                source TEXT DEFAULT 'owner',
                submitted_by_customer_id TEXT,
                client_description TEXT,
                client_swatch_photo_path TEXT,
                needs_review INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
            """
        )
        backing_id = conn.execute(
            """INSERT INTO fabrics
               (code, name, material_type, cost_per_yard, margin_percent)
               VALUES (?, ?, ?, ?, ?)""",
            ("NCOP-04", "Founder Backing", "Backing", 42.95, 10),
        ).lastrowid
        fabric_id = conn.execute(
            """INSERT INTO fabrics
               (code, name, material_type, cost_per_yard, margin_percent, backing_fabric_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("V639", "Founder Spruce", "Upholstery", 39.95, 25, backing_id),
        ).lastrowid

    base_body = {
        "customer_name": "Catalog Client",
        "customer_email": "catalog@example.com",
        "customer_phone": "555-0200",
        "customer_address": "24 Fabric Way",
        "rooms": [{
            "name": "Breakfast Nook",
            "items": [{
                "type": "cornice",
                "quantity": 1,
                "dimensions": {"width": 120, "height": 18, "depth": 8},
                "fabric_yards_needed": 6,
                "backing_yards_needed": 6,
            }],
        }],
        "options": {"lining_type": "none"},
    }

    without_selected = asyncio.run(quotes.create_quote_from_rooms(base_body))
    with_selected = asyncio.run(quotes.create_quote_from_rooms({
        **base_body,
        "rooms": [{
            "name": "Breakfast Nook",
            "items": [{
                "type": "cornice",
                "quantity": 1,
                "dimensions": {"width": 120, "height": 18, "depth": 8},
                "fabric_id": fabric_id,
                "fabric_name": "Founder Spruce",
                "fabric_code": "V639",
                "fabric_yards_needed": 6,
                "backing_fabric_id": backing_id,
                "backing_fabric_name": "Founder Backing",
                "backing_fabric_code": "NCOP-04",
                "backing_yards_needed": 6,
            }],
        }],
    }))

    without_quote = without_selected["quote"]
    with_quote = with_selected["quote"]

    assert without_quote["tiers"]["A"]["total"] != with_quote["tiers"]["A"]["total"]

    tier_a_items = with_quote["tiers"]["A"]["items"][0]["line_items"]
    fabric_line = next(li for li in tier_a_items if li["category"] == "fabric")
    backing_line = next(li for li in tier_a_items if li["category"] == "backing")

    assert fabric_line["description"] == "Founder Spruce (6.0 yd)"
    assert fabric_line["rate"] == 49.94
    assert backing_line["description"] == "Founder Backing (6.0 yd)"
    assert backing_line["rate"] == 47.25

    saved_quote = json.loads((quotes_dir / f"{with_quote['id']}.json").read_text())
    assert saved_quote["customer_email"] == "catalog@example.com"

    with quotes.get_db() as conn:
        customer = conn.execute(
            "SELECT * FROM customers WHERE lower(email) = lower(?)",
            ("catalog@example.com",),
        ).fetchone()

    assert customer is not None
    assert customer["name"] == "Catalog Client"
    assert customer["business"] == "workroom"
    assert customer["lifetime_quotes"] == 2


def test_selected_tier_materializes_totals_and_line_items(monkeypatch, tmp_path):
    quotes, _, _, quotes_dir = _load_lifecycle_modules(monkeypatch, tmp_path)

    response = asyncio.run(quotes.create_quote_from_rooms({
        "customer_name": "Tier Client",
        "customer_email": "tier@example.com",
        "rooms": [{
            "name": "Dining Room",
            "items": [{
                "type": "cornice",
                "quantity": 1,
                "dimensions": {"width": 96, "height": 18, "depth": 8},
            }],
        }],
        "options": {"lining_type": "none"},
    }))

    quote = response["quote"]
    assert quote.get("total") in (None, 0)

    updated = asyncio.run(quotes.update_quote(
        quote["id"],
        quotes.QuoteUpdate(status="accepted", selected_tier="B"),
    ))
    selected_quote = updated["quote"]

    assert selected_quote["selected_tier"] == "B"
    assert selected_quote["status"] == "accepted"
    assert selected_quote["total"] == selected_quote["tiers"]["B"]["total"]
    assert selected_quote["subtotal"] == selected_quote["tiers"]["B"]["subtotal"]
    assert selected_quote["line_items"]
    assert selected_quote["deposit"]["deposit_amount"] == round(selected_quote["total"] * 0.5, 2)

    saved_quote = json.loads((quotes_dir / f"{quote['id']}.json").read_text())
    assert saved_quote["selected_tier"] == "B"
    assert saved_quote["total"] == saved_quote["tiers"]["B"]["total"]


def test_create_quote_number_advances_past_existing_files(monkeypatch, tmp_path):
    quotes, _, _, quotes_dir = _load_lifecycle_modules(monkeypatch, tmp_path)

    _write_quote(quotes_dir, {
        "id": "older-high",
        "quote_number": "EST-2026-117",
        "customer_name": "Existing Customer",
        "status": "draft",
    })
    (quotes_dir / "_counter.json").write_text(json.dumps({"year": 2026, "seq": 5}))

    created = asyncio.run(quotes.create_quote(quotes.QuoteCreate(
        customer_name="New Customer",
        customer_email="new-customer@example.com",
        line_items=[],
    )))

    assert created["quote"]["quote_number"] == "EST-2026-118"
