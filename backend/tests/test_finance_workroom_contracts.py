import importlib

from starlette.requests import Request


def _request() -> Request:
    return Request({"type": "http", "method": "GET", "path": "/test", "headers": []})


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

    listed_invoices = finance.list_invoices(_request(), limit=100, offset=0)
    listed_payments = finance.list_payments(_request(), limit=100, offset=0)
    listed_expenses = finance.list_expenses(_request(), limit=100, offset=0)
    dashboard = finance.finance_dashboard(_request())

    assert listed_invoices["items"] == listed_invoices["invoices"]
    assert listed_invoices["items"][0]["customer_name"] == "Mina Manual"
    assert listed_invoices["items"][0]["amount"] == 220
    assert listed_invoices["items"][0]["balance"] == 150

    assert listed_payments["items"] == listed_payments["payments"]
    assert listed_payments["items"][0]["customer_id"] == invoice["customer_id"]

    assert listed_expenses["items"] == listed_expenses["expenses"]
    assert listed_expenses["items"][0]["expense_date"] == "2026-04-12"
    assert listed_expenses["items"][0]["date"] == "2026-04-12"

    assert dashboard["revenue"]["mtd"] == 70
    assert dashboard["expenses"]["mtd"] == 30
    assert dashboard["net_profit"]["mtd"] == 40
    assert dashboard["outstanding"]["total"] == 150
    assert dashboard["revenue_mtd"] == 70
    assert dashboard["expenses_mtd"] == 30
    assert dashboard["net_profit_mtd"] == 40
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
