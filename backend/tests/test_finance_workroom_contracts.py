import importlib
import json
from itertools import count
from pathlib import Path

from starlette.requests import Request

_request_count = count()

def _request() -> Request:
    return Request({"type": "http", "method": "GET", "path": f"/test/{next(_request_count)}", "headers": []})


def _load_finance(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))

    from app.db import database

    importlib.reload(database)

    from app.db import init_db

    importlib.reload(init_db)
    init_db.init_database()

    from app.routers import finance

    importlib.reload(finance)
    return finance, database


def test_canonical_finance_router_precedes_legacy_financial_router():
    main_source = Path(__file__).resolve().parents[1].joinpath("app", "main.py").read_text()

    assert main_source.index('load_router("app.routers.finance"') < main_source.index(
        'load_router("app.routers.financial"'
    )


def test_workroom_finance_ui_contracts_preserve_customer_and_list_shapes(monkeypatch, tmp_path):
    finance, database = _load_finance(monkeypatch, tmp_path)

    invoice_response = finance.create_invoice(
        _request(),
        finance.InvoiceCreate(
            customer_name="Mina Manual",
            customer_email="mina@example.com",
            customer_phone="555-0444",
            customer_address="44 Ledger Lane",
            business_unit="workroom",
            subtotal=200,
            tax_rate=0.1,
            line_items=[{"description": "Manual Workroom Invoice", "qty": 2, "rate": 100, "amount": 200}],
        ),
    )
    invoice = invoice_response["invoice"]

    assert invoice["customer_id"]
    assert invoice["customer_name"] == "Mina Manual"
    assert invoice["client_email"] == "mina@example.com"
    assert invoice["client_phone"] == "555-0444"
    assert invoice["client_address"] == "44 Ledger Lane"
    assert invoice["business_unit"] == "workroom"
    assert invoice["amount"] == 220
    assert invoice["balance"] == 220

    finance.record_payment(
        _request(),
        invoice["id"],
        finance.PaymentCreate(amount=70, method="check", reference="CHK-70", payment_date="2026-04-12"),
    )
    finance.create_expense(
        _request(),
        finance.ExpenseCreate(
            category="tools",
            vendor="Tool Vendor",
            description="Clamp set",
            amount=30,
            date="2026-04-12",
        ),
    )
    finance.create_expense(
        _request(),
        finance.ExpenseCreate(
            category="materials",
            vendor="Wood Vendor",
            description="Woodcraft material",
            amount=45,
            expense_date="2026-04-12",
            business="woodcraft",
        ),
    )
    sent_response = finance.mark_invoice_sent(_request(), invoice["id"])

    listed_invoices = finance.list_invoices(_request(), limit=100, offset=0)
    workroom_invoices = finance.list_invoices(_request(), business="workroom", limit=100, offset=0)
    woodcraft_invoices = finance.list_invoices(_request(), business="woodcraft", limit=100, offset=0)
    listed_payments = finance.list_payments(_request(), limit=100, offset=0)
    listed_expenses = finance.list_expenses(_request(), limit=100, offset=0)
    workroom_expenses = finance.list_expenses(_request(), business="workroom", limit=100, offset=0)
    woodcraft_expenses = finance.list_expenses(_request(), business="woodcraft", limit=100, offset=0)
    dashboard = finance.finance_dashboard(_request())

    assert sent_response["status"] == "sent"
    assert sent_response["invoice"]["status"] == "sent"
    assert sent_response["invoice"]["sent_at"]
    assert sent_response["invoice"]["sent_date"]

    assert listed_invoices["items"] == listed_invoices["invoices"]
    assert listed_invoices["items"][0]["customer_name"] == "Mina Manual"
    assert listed_invoices["items"][0]["amount"] == 220
    assert listed_invoices["items"][0]["balance"] == 150
    assert [inv["id"] for inv in workroom_invoices["items"]] == [invoice["id"]]
    assert woodcraft_invoices["items"] == []

    assert listed_payments["items"] == listed_payments["payments"]
    assert listed_payments["items"][0]["customer_id"] == invoice["customer_id"]

    assert listed_expenses["items"] == listed_expenses["expenses"]
    assert {exp["business_unit"] for exp in listed_expenses["items"]} == {"workroom", "woodcraft"}
    assert workroom_expenses["items"][0]["vendor"] == "Tool Vendor"
    assert workroom_expenses["items"][0]["expense_date"] == "2026-04-12"
    assert workroom_expenses["items"][0]["date"] == "2026-04-12"
    assert woodcraft_expenses["items"][0]["vendor"] == "Wood Vendor"
    assert woodcraft_expenses["items"][0]["category"] == "hardware"

    assert dashboard["revenue"]["mtd"] == 70
    assert dashboard["expenses"]["mtd"] == 75
    assert dashboard["net_profit"]["mtd"] == -5
    assert dashboard["outstanding"]["total"] == 150
    assert dashboard["revenue_mtd"] == 70
    assert dashboard["expenses_mtd"] == 75
    assert dashboard["net_profit_mtd"] == -5
    assert dashboard["outstanding_total"] == 150
    assert dashboard["aging"] == [
        {"label": "0-30 days", "amount": 150},
        {"label": "31-60 days", "amount": 0},
        {"label": "61-90 days", "amount": 0},
        {"label": "90+ days", "amount": 0},
    ]
    assert dashboard["top_customers"][0]["name"] == "Mina Manual"

    with database.get_db() as conn:
        customer = conn.execute(
            "SELECT * FROM customers WHERE id = ?", (invoice["customer_id"],)
        ).fetchone()
        assert customer["name"] == "Mina Manual"
        assert customer["email"] == "mina@example.com"
        assert customer["phone"] == "555-0444"
        assert customer["address"] == "44 Ledger Lane"
        assert customer["business"] == "workroom"


def test_customer_finance_ledger_statement_and_business_filter(monkeypatch, tmp_path):
    finance, database = _load_finance(monkeypatch, tmp_path)

    workroom_invoice = finance.create_invoice(
        _request(),
        finance.InvoiceCreate(
            customer_name="Ledger Client",
            customer_email="ledger@example.com",
            business_unit="workroom",
            subtotal=1000,
            tax_rate=0,
            line_items=[{"description": "Workroom statement invoice", "quantity": 1, "rate": 1000, "amount": 1000}],
            due_date="2026-04-01",
        ),
    )["invoice"]
    finance.mark_invoice_sent(_request(), workroom_invoice["id"])

    finance.record_payment(
        _request(),
        workroom_invoice["id"],
        finance.PaymentCreate(amount=400, method="check", reference="LEDGER-400", payment_date="2026-04-12"),
    )

    woodcraft_invoice = finance.create_invoice(
        _request(),
        finance.InvoiceCreate(
            customer_id=workroom_invoice["customer_id"],
            customer_name="Ledger Client",
            customer_email="ledger@example.com",
            business_unit="woodcraft",
            subtotal=700,
            tax_rate=0,
            line_items=[{"description": "Woodcraft statement invoice", "quantity": 1, "rate": 700, "amount": 700}],
            due_date="2026-04-01",
        ),
    )["invoice"]
    finance.mark_invoice_sent(_request(), woodcraft_invoice["id"])

    all_ledger = finance.customer_finance_ledger(_request(), workroom_invoice["customer_id"])
    workroom_ledger = finance.customer_finance_ledger(_request(), workroom_invoice["customer_id"], business="workroom")
    woodcraft_ledger = finance.customer_finance_ledger(_request(), workroom_invoice["customer_id"], business="woodcraft")

    assert all_ledger["customer"]["email"] == "ledger@example.com"
    assert all_ledger["summary"]["invoice_count"] == 2
    assert all_ledger["summary"]["payment_count"] == 1
    assert all_ledger["summary"]["total_invoiced"] == 1700
    assert all_ledger["summary"]["total_paid"] == 400
    assert all_ledger["summary"]["current_balance"] == 1300
    assert all_ledger["summary"]["aging_total"] == 1300
    assert {txn["type"] for txn in all_ledger["transactions"]} == {"invoice", "payment"}
    assert any(txn["reference"] == "LEDGER-400" for txn in all_ledger["transactions"] if txn["type"] == "payment")

    assert [inv["id"] for inv in workroom_ledger["invoices"]] == [workroom_invoice["id"]]
    assert workroom_ledger["summary"]["total_invoiced"] == 1000
    assert workroom_ledger["summary"]["total_paid"] == 400
    assert workroom_ledger["summary"]["current_balance"] == 600
    assert workroom_ledger["summary"]["aging_total"] == 600

    assert [inv["id"] for inv in woodcraft_ledger["invoices"]] == [woodcraft_invoice["id"]]
    assert woodcraft_ledger["payments"] == []
    assert woodcraft_ledger["summary"]["current_balance"] == 700

    statement = finance.customer_statement_export(_request(), workroom_invoice["customer_id"], business="workroom")
    assert statement["statement"]["customer_email"] == "ledger@example.com"
    assert statement["statement"]["business"] == "workroom"
    assert statement["summary"]["current_balance"] == 600
    assert statement["summary"]["overdue_balance"] == 600
    assert statement["overdue_invoices"][0]["id"] == workroom_invoice["id"]

    reminder = finance.log_customer_collection_reminder(
        _request(),
        workroom_invoice["customer_id"],
        finance.CollectionReminderRequest(
            business="workroom",
            action="reminder_logged",
            notes="Reminder logged from test",
        ),
    )
    assert reminder["status"] == "logged"
    assert reminder["delivered"] is False
    assert reminder["event"]["business_unit"] == "workroom"
    assert reminder["event"]["open_balance"] == 600
    assert reminder["event"]["overdue_balance"] == 600
    assert reminder["statement"]["collections"][0]["notes"] == "Reminder logged from test"

    second_workroom_invoice = finance.create_invoice(
        _request(),
        finance.InvoiceCreate(
            customer_name="Second AR Client",
            customer_email="second-ar@example.com",
            business_unit="workroom",
            subtotal=300,
            tax_rate=0,
            due_date="2026-04-20",
        ),
    )["invoice"]
    finance.mark_invoice_sent(_request(), second_workroom_invoice["id"])

    workroom_queue = finance.collections_worklist(_request(), business="workroom")
    woodcraft_queue = finance.collections_worklist(_request(), business="woodcraft")
    all_queue = finance.collections_worklist(_request())

    ledger_client = next(item for item in workroom_queue["items"] if item["customer_name"] == "Ledger Client")
    second_client = next(item for item in workroom_queue["items"] if item["customer_name"] == "Second AR Client")

    assert workroom_queue["business"] == "workroom"
    assert workroom_queue["totals"]["open_balance"] == 900
    assert workroom_queue["totals"]["overdue_balance"] == 600
    assert workroom_queue["totals"]["open_invoice_count"] == 2
    assert workroom_queue["totals"]["overdue_invoice_count"] == 1
    assert ledger_client["open_balance"] == 600
    assert ledger_client["overdue_balance"] == 600
    assert ledger_client["last_collection_action"] == "reminder_logged"
    assert ledger_client["last_collection_notes"] == "Reminder logged from test"
    assert ledger_client["next_action"] == "follow_up"
    assert second_client["open_balance"] == 300
    assert second_client["overdue_balance"] == 0
    assert second_client["next_action"] == "monitor_open_balance"

    assert woodcraft_queue["business"] == "woodcraft"
    assert woodcraft_queue["totals"]["open_balance"] == 700
    assert woodcraft_queue["items"][0]["customer_name"] == "Ledger Client"
    assert woodcraft_queue["items"][0]["last_collection_action"] is None
    assert all_queue["totals"]["open_balance"] == 1600
    assert {item["business_unit"] for item in all_queue["items"]} == {"workroom", "woodcraft"}


def test_smart_invoice_composer_milestones_payments_and_sources(monkeypatch, tmp_path):
    finance, database = _load_finance(monkeypatch, tmp_path)

    from app.routers import jobs_unified

    importlib.reload(jobs_unified)

    quotes_dir = tmp_path / "quotes"
    designs_dir = tmp_path / "craftforge" / "designs"
    quotes_dir.mkdir()
    designs_dir.mkdir(parents=True)
    monkeypatch.setattr(finance, "QUOTES_DIR", quotes_dir)
    monkeypatch.setattr(finance, "DESIGNS_DIR", designs_dir)

    quote = {
        "id": "composer-quote",
        "quote_number": "EST-2026-099",
        "customer_name": "Composer Client",
        "customer_email": "composer@example.com",
        "customer_phone": "555-0999",
        "customer_address": "99 Ledger Way",
        "business_unit": "workroom",
        "line_items": [{"description": "Milestone Drapery", "quantity": 1, "rate": 1000, "amount": 1000}],
        "subtotal": 1000,
        "tax_rate": 0.1,
        "tax_amount": 100,
        "discount_amount": 100,
        "discount_type": "dollar",
        "total": 1000,
        "deposit": {"deposit_percent": 50},
        "terms": "50% deposit, progress draw, balance on install",
        "notes": "Carry composer notes",
    }
    (quotes_dir / "composer-quote.json").write_text(json.dumps(quote))

    with database.get_db() as conn:
        conn.execute(
            """INSERT INTO jobs
               (id, title, quote_id, status, business_unit, description, quoted_amount)
               VALUES ('composer-job', 'Composer Job', 'composer-quote', 'pending', 'workroom',
                       'Install milestone drapery', 1000)"""
        )

    deposit = finance.compose_invoice(
        _request(),
        finance.InvoiceComposeRequest(source_type="quote", source_id="composer-quote", invoice_type="deposit"),
    )["invoice"]
    progress = finance.compose_invoice(
        _request(),
        finance.InvoiceComposeRequest(source_type="quote", source_id="composer-quote", invoice_type="progress", percent=25),
    )["invoice"]
    final = finance.compose_invoice(
        _request(),
        finance.InvoiceComposeRequest(source_type="job", source_id="composer-job", invoice_type="final"),
    )["invoice"]

    assert deposit["invoice_stage"] == "deposit"
    assert deposit["source_type"] == "quote"
    assert deposit["source_id"] == "composer-quote"
    assert deposit["quote_id"] == "composer-quote"
    assert deposit["customer_id"]
    assert deposit["customer_name"] == "Composer Client"
    assert deposit["business_unit"] == "workroom"
    assert deposit["subtotal"] == 500
    assert deposit["tax_amount"] == 50
    assert deposit["discount_amount"] == 50
    assert deposit["discount_type"] == "dollar"
    assert deposit["total"] == 500
    assert deposit["deposit_required"] == 500
    assert deposit["balance_due"] == 500
    assert deposit["terms"] == "50% deposit, progress draw, balance on install"
    assert "Carry composer notes" in deposit["notes"]
    assert deposit["line_items"][0]["description"] == "Deposit 50% - Milestone Drapery"

    assert progress["invoice_stage"] == "progress"
    assert progress["total"] == 250
    assert progress["discount_amount"] == 25
    assert progress["deposit_required"] == 0

    assert final["invoice_stage"] == "final"
    assert final["source_type"] == "job"
    assert final["source_id"] == "composer-job"
    assert final["quote_id"] == "composer-quote"
    assert final["job_id"] == "composer-job"
    assert final["total"] == 250
    assert final["discount_amount"] == 25

    paid_deposit = finance.record_payment(
        _request(),
        deposit["id"],
        finance.PaymentCreate(amount=500, method="check", reference="DEP-500", payment_date="2026-04-12"),
    )["invoice"]
    paid_final = finance.record_payment(
        _request(),
        final["id"],
        finance.PaymentCreate(amount=250, method="zelle", reference="FINAL-250", payment_date="2026-04-12"),
    )["invoice"]

    assert paid_deposit["status"] == "paid"
    assert paid_deposit["balance_due"] == 0
    assert paid_final["status"] == "paid"
    assert paid_final["balance_due"] == 0

    detail = finance.get_invoice(_request(), final["id"])["invoice"]
    assert detail["customer"]["email"] == "composer@example.com"
    assert detail["payments"][0]["reference"] == "FINAL-250"

    design = {
        "id": "composer-design",
        "design_number": "CF-2026-099",
        "customer_name": "Design Composer",
        "customer_email": "design-composer@example.com",
        "customer_phone": "555-0888",
        "customer_address": "88 CNC Way",
        "description": "Walnut composer valance",
        "materials": [{"name": "Walnut", "quantity": 2, "cost_per_unit": 100}],
        "labor_cost": 100,
        "subtotal": 300,
        "tax_rate": 0.1,
        "tax_amount": 30,
        "discount_amount": 30,
        "discount_type": "dollar",
        "deposit_percent": 50,
        "total": 300,
        "notes": "Design notes carry",
    }
    (designs_dir / "composer-design.json").write_text(json.dumps(design))
    design_invoice = finance.compose_invoice(
        _request(),
        finance.InvoiceComposeRequest(source_type="design", source_id="composer-design", invoice_type="deposit"),
    )["invoice"]

    assert design_invoice["business_unit"] == "woodcraft"
    assert design_invoice["quote_id"] == "composer-design"
    assert design_invoice["invoice_stage"] == "deposit"
    assert design_invoice["total"] == 150
    assert design_invoice["deposit_required"] == 150
    assert "Design notes carry" in design_invoice["notes"]

    dashboard = finance.finance_dashboard(_request())
    assert dashboard["revenue"]["mtd"] == 750
    assert dashboard["outstanding"]["total"] == 400

    with database.get_db() as conn:
        customer = conn.execute(
            "SELECT * FROM customers WHERE id = ?", (deposit["customer_id"],)
        ).fetchone()
        job = conn.execute("SELECT * FROM jobs WHERE id = 'composer-job'").fetchone()

    assert customer["email"] == "composer@example.com"
    assert customer["total_revenue"] == 750
    assert job["invoice_id"] == final["id"]
