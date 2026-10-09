"""Quote → deposit invoice → Stripe Checkout link, including a double-click."""
import importlib
import json
from types import SimpleNamespace

from starlette.requests import Request


class _StripeError(Exception):
    pass


class _SessionAPI:
    created = []

    @classmethod
    def reset(cls):
        cls.created = []

    @classmethod
    def create(cls, **kwargs):
        session = SimpleNamespace(
            id=f"cs_test_{len(cls.created) + 1}",
            url=f"https://checkout.stripe.com/c/pay/cs_test_{len(cls.created) + 1}",
            payment_status="unpaid",
            status="open",
        )
        cls.created.append(kwargs)
        return session

    @classmethod
    def retrieve(cls, session_id):
        index = int(session_id.rsplit("_", 1)[-1]) - 1
        kwargs = cls.created[index]
        return SimpleNamespace(
            id=session_id,
            url=f"https://checkout.stripe.com/c/pay/{session_id}",
            payment_status="unpaid",
            status="open",
            metadata=kwargs.get("metadata") or {},
        )


def _request() -> Request:
    return Request({"type": "http", "method": "POST", "path": "/test", "headers": []})


def _load(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)

    from app.db import database
    importlib.reload(database)
    from app.db import init_db
    importlib.reload(init_db)
    init_db.init_database()

    # Ensure payments_v2 (canonical Sprint-1d table) exists alongside payments.
    from app.db.database import get_db
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS payments_v2 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payment_number TEXT,
                invoice_id TEXT,
                customer_id TEXT,
                amount REAL,
                payment_method TEXT,
                payment_reference TEXT,
                payment_type TEXT,
                status TEXT,
                account_code TEXT,
                notes TEXT,
                business_unit TEXT,
                stripe_session_id TEXT,
                payment_date TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)

    from app.routers import payments, finance
    importlib.reload(payments)
    importlib.reload(finance)

    quotes_dir = tmp_path / "quotes"
    quotes_dir.mkdir()
    monkeypatch.setattr(finance, "QUOTES_DIR", quotes_dir)

    _SessionAPI.reset()
    fake = SimpleNamespace(
        checkout=SimpleNamespace(Session=_SessionAPI),
        error=SimpleNamespace(StripeError=_StripeError),
    )
    monkeypatch.setattr(payments, "stripe", fake)
    return finance, payments, quotes_dir


def _quote(quote_id, business="workroom", **extra):
    quote = {
        "id": quote_id,
        "quote_number": f"EST-{quote_id}",
        "status": "accepted",
        "customer_name": "Ada Client",
        "customer_email": "ada@example.com",
        "customer_phone": "555-0100",
        "customer_address": "10 Drapery Ln",
        "business_unit": business,
        "line_items": [{"description": "Panels", "quantity": 2, "rate": 100, "amount": 200}],
        "subtotal": 200,
        "tax_rate": 0.1,
        "tax_amount": 20,
        "total": 220,
        "deposit": {"deposit_percent": 50, "deposit_amount": 110},
        "terms": "50% deposit to begin",
    }
    quote.update(extra)
    return quote


def _write(quotes_dir, quote):
    (quotes_dir / f"{quote['id']}.json").write_text(json.dumps(quote))


def test_quote_deposit_pay_link_is_idempotent_and_unpaid(monkeypatch, tmp_path):
    finance, payments, quotes_dir = _load(monkeypatch, tmp_path)
    _write(quotes_dir, _quote("q-deposit"))

    first = finance.create_quote_deposit_pay_link("q-deposit")
    second = finance.quote_deposit_pay_link(_request(), "q-deposit", finance.DepositPayLinkRequest())

    assert first["invoice_created"] is True
    assert second["invoice_created"] is False
    assert first["invoice"]["id"] == second["invoice"]["id"]
    assert first["invoice"]["invoice_stage"] == "deposit"
    assert first["invoice"]["business_unit"] == "workroom"
    assert first["invoice"]["client_name"] == "Ada Client"
    assert first["invoice"]["client_email"] == "ada@example.com"
    assert first["invoice"]["client_phone"] == "555-0100"
    assert first["invoice"]["client_address"] == "10 Drapery Ln"
    assert first["copied_from_quote"] is True
    assert first["customer"] == {
        "name": "Ada Client",
        "email": "ada@example.com",
        "phone": "555-0100",
        "address": "10 Drapery Ln",
    }
    assert round(first["invoice"]["total"], 2) == 110
    assert first["pay_link"]["checkout_url"] == second["pay_link"]["checkout_url"]
    assert first["pay_link"]["checkout_url"].startswith("https://checkout.stripe.com/c/pay/")
    assert second["pay_link"]["reused"] is True
    assert first["payment_status"] == "link_ready"
    assert second["payment_status"] == "link_ready"
    assert first["invoice"]["status"] != "paid"
    assert len(_SessionAPI.created) == 1
    assert _SessionAPI.created[0]["customer_email"] == "ada@example.com"
    assert _SessionAPI.created[0]["metadata"]["flow"] == "workroom_invoice"
    assert "studio.empirebox.store" not in (_SessionAPI.created[0]["success_url"])
    assert "127.0.0.1:3005" in _SessionAPI.created[0]["success_url"]

    from app.db.database import get_db
    with get_db() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM invoices WHERE quote_id = ? AND invoice_stage = 'deposit'",
            ("q-deposit",),
        ).fetchone()[0]
        payments_n = conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
    assert count == 1
    assert payments_n == 0


def test_woodcraft_quote_gets_deposit_link_other_business_does_not(monkeypatch, tmp_path):
    finance, payments, quotes_dir = _load(monkeypatch, tmp_path)
    _write(quotes_dir, _quote("q-wood", business="woodcraft", customer_name="Oak Buyer", customer_email="oak@example.com"))
    _write(quotes_dir, _quote("q-market", business="marketplace"))

    wood = finance.create_quote_deposit_pay_link("q-wood")
    assert wood["business"] == "woodcraft"
    assert wood["invoice"]["business_unit"] == "woodcraft"
    assert wood["customer"]["name"] == "Oak Buyer"
    assert wood["pay_link"]["checkout_url"]

    try:
        finance.create_quote_deposit_pay_link("q-market")
        raised = False
    except Exception as exc:
        raised = True
        assert getattr(exc, "status_code", None) == 400
        assert "Workroom and WoodCraft" in str(exc.detail)
    assert raised


def test_stripe_paid_event_records_once_and_unpaid_event_does_not(monkeypatch, tmp_path):
    finance, payments, quotes_dir = _load(monkeypatch, tmp_path)
    _write(quotes_dir, _quote("q-pay"))
    issued = finance.create_quote_deposit_pay_link("q-pay")
    invoice_id = issued["invoice"]["id"]
    session_id = issued["pay_link"]["session_id"]

    waiting = payments.apply_workroom_checkout_event("checkout.session.completed", {
        "id": session_id,
        "payment_status": "unpaid",
        "metadata": {"flow": "workroom_invoice", "invoice_id": invoice_id},
    })
    assert waiting["payment_status"] == "awaiting_confirmation"

    from app.db.database import get_db, dict_row
    with get_db() as conn:
        row = dict_row(conn.execute("SELECT status, payment_status FROM invoices WHERE id = ?", (invoice_id,)).fetchone())
        pay_count = conn.execute("SELECT COUNT(*) FROM payments WHERE invoice_id = ?", (invoice_id,)).fetchone()[0]  # one payments table (job_ledger)
    assert row["status"] != "paid"
    assert row["payment_status"] == "awaiting_confirmation"
    assert pay_count == 0

    again_link = finance.create_quote_deposit_pay_link("q-pay")
    assert again_link["invoice"]["id"] == invoice_id
    assert again_link["pay_link"]["checkout_url"] == issued["pay_link"]["checkout_url"]
    assert again_link["pay_link"]["reused"] is True
    assert again_link["payment_status"] == "awaiting_confirmation"
    assert len(_SessionAPI.created) == 1

    paid = payments.apply_workroom_checkout_event("checkout.session.async_payment_succeeded", {
        "id": session_id,
        "payment_status": "paid",
        "metadata": {"flow": "workroom_invoice", "invoice_id": invoice_id},
    })
    again = payments.apply_workroom_checkout_event("checkout.session.async_payment_succeeded", {
        "id": session_id,
        "payment_status": "paid",
        "metadata": {"flow": "workroom_invoice", "invoice_id": invoice_id},
    })
    assert paid["payment_status"] == "paid"
    assert again["payment_status"] == "paid"

    with get_db() as conn:
        row = dict_row(conn.execute("SELECT status, payment_status, balance_due FROM invoices WHERE id = ?", (invoice_id,)).fetchone())
        pay_count = conn.execute("SELECT COUNT(*) FROM payments WHERE invoice_id = ?", (invoice_id,)).fetchone()[0]  # one payments table (job_ledger)
    assert row["status"] == "paid"
    assert row["payment_status"] == "paid"
    assert row["balance_due"] == 0
    assert pay_count == 1


def test_missing_stripe_keeps_invoice_and_does_not_invent_a_link(monkeypatch, tmp_path):
    finance, payments, quotes_dir = _load(monkeypatch, tmp_path)
    monkeypatch.setattr(payments, "stripe", None)
    _write(quotes_dir, _quote("q-nostripe"))

    first = finance.create_quote_deposit_pay_link("q-nostripe")
    second = finance.create_quote_deposit_pay_link("q-nostripe")

    assert first["invoice"]["id"] == second["invoice"]["id"]
    assert first["pay_link"]["checkout_url"] is None
    assert first["pay_link"]["stripe_configured"] is False
    assert first["payment_status"] == "unpaid"
    assert "STRIPE_SECRET_KEY" in first["pay_link"]["error"]
    assert second["invoice_created"] is False
