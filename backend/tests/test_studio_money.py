"""Studio Money figures from mocked invoice/payment/quote rows. No live DB, no mail."""
from datetime import date

from app.services.studio_money import compute_studio_money

TODAY = date(2026, 10, 16)


def test_paid_mtd_and_deposits_due_from_mocked_records():
    invoices = [
        {
            "id": "inv-overdue",
            "status": "sent",
            "due_date": "2026-09-01",
            "balance_due": 120.50,
            "invoice_stage": "final",
        },
        {
            "id": "inv-deposit-open",
            "status": "sent",
            "due_date": "2026-10-20",
            "balance_due": 400.00,
            "invoice_stage": "deposit",
            "quote_id": "q-has-invoice",
            "deposit_required": 400.00,
            "deposit_received": 0,
        },
        {
            "id": "inv-deposit-paid",
            "status": "paid",
            "invoice_stage": "deposit",
            "quote_id": "q-paid",
            "balance_due": 0,
        },
        {
            "id": "inv-current",
            "status": "sent",
            "due_date": "2026-10-30",
            "balance_due": 999.00,
            "invoice_stage": "final",
        },
    ]
    payments = [
        {"id": "pay-mtd", "amount": 250.25, "payment_date": "2026-10-05"},
        {"id": "pay-prior", "amount": 80.00, "payment_date": "2026-09-20"},
    ]
    quotes = [
        {
            "id": "q-open-deposit",
            "status": "approved",
            "deposit_required": 300.00,
            "deposit_paid": 50.00,
        },
        {
            "id": "q-has-invoice",
            "status": "approved",
            "deposit_required": 400.00,
            "deposit_paid": 0,
        },
        {
            "id": "q-draft",
            "status": "draft",
            "deposit_required": 500.00,
            "deposit_paid": 0,
        },
    ]

    result = compute_studio_money(invoices, payments, quotes, today=TODAY)

    assert result["to_collect"] == 120.50
    assert result["deposits_due"] == 650.00  # 400 open deposit invoice + 250 remaining on q-open-deposit
    assert result["paid_mtd"] == 250.25
    assert result["connected"] == {
        "to_collect": True,
        "deposits_due": True,
        "paid_mtd": True,
    }
    blob = str(result)
    assert "Nelma" not in blob
    assert "McLean" not in blob
    assert "@gmail.com" not in blob


def test_empty_records_are_zero_not_example():
    result = compute_studio_money([], [], [], today=TODAY)
    assert result["to_collect"] == 0
    assert result["deposits_due"] == 0
    assert result["paid_mtd"] == 0
    assert "EXAMPLE" not in str(result)
    assert "Client A" not in str(result)


def test_disconnected_sources_return_null_amounts():
    result = compute_studio_money(
        [],
        [],
        [],
        today=TODAY,
        invoices_connected=False,
        payments_connected=False,
        quotes_connected=False,
    )
    assert result["to_collect"] is None
    assert result["deposits_due"] is None
    assert result["paid_mtd"] is None
    assert result["connected"]["to_collect"] is False
    assert result["connected"]["paid_mtd"] is False
    assert result["connected"]["deposits_due"] is False


def test_paid_deposit_invoice_does_not_double_count_quote():
    invoices = [
        {
            "id": "inv-dep",
            "status": "paid",
            "invoice_stage": "deposit",
            "quote_id": "q1",
            "balance_due": 0,
        }
    ]
    quotes = [
        {"id": "q1", "status": "approved", "deposit_required": 200, "deposit_paid": 0},
    ]
    result = compute_studio_money(invoices, [], quotes, today=TODAY)
    assert result["deposits_due"] == 0
