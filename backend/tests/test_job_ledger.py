"""Job-aware ledger: prior deposits / payments / change orders applied on a final invoice."""
import importlib
import json

from starlette.requests import Request


def _request():
    return Request({"type": "http", "method": "POST", "path": "/t", "headers": []})


def _load(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    from app.db import database
    importlib.reload(database)
    from app.db import init_db
    importlib.reload(init_db)
    init_db.init_database()
    from app.routers import finance, payments
    importlib.reload(payments)
    importlib.reload(finance)
    from app.services import job_ledger
    importlib.reload(job_ledger)
    return finance, payments, job_ledger


def _insert(conn, **kw):
    base = {"customer_id": "cust1", "status": "draft", "subtotal": kw.get("total", 0), "tax_rate": 0, "tax_amount": 0,
            "amount_paid": 0, "balance_due": kw.get("total", 0), "line_items": json.dumps(
                [{"room": "U banquette", "description": "Seat back", "quantity": 1, "unit": "ea",
                  "unit_price": kw.get("total", 0), "total": kw.get("total", 0)}]),
            "client_name": "Client Co · Attn Pat", "business_unit": "workroom", "created_at": kw.pop("created_at")}
    base.update(kw)
    have = {r[1] for r in conn.execute("PRAGMA table_info(invoices)")}
    base = {k: v for k, v in base.items() if k in have}
    conn.execute(f"INSERT INTO invoices ({', '.join(base)}) VALUES ({', '.join('?' * len(base))})", list(base.values()))


def _marleys(conn, job_ledger):
    job_ledger.ensure_ledger_schema(conn)
    conn.execute("INSERT OR IGNORE INTO customers (id, name) VALUES ('cust1', 'Client Co')")
    _insert(conn, id="old", invoice_number="INV-2026-123", total=9152.63, deposit_required=4576.31,
            terms="Superseded by INV-2026-124", created_at="2026-09-27 10:00:00")
    _insert(conn, id="co1", invoice_number="INV-2026-124", total=11328.65, quote_id="q299", source_type="quote",
            source_id="q299", invoice_stage="deposit", deposit_required=5664.33, deposit_received=4576.31,
            deposit_date="2026-09-27", balance_due=1088.02, payment_status="link_ready",
            stripe_checkout_url="https://buy.stripe.com/test_co1",
            pricing_snapshot_json=json.dumps({"change_order": {"number": 1, "credit_ref": "INV-2026-123 (EST-274B)"}}),
            created_at="2026-10-08 23:00:00")
    job_ledger.record_payment(conn, "old", 4576.31, method="card", reference="pi_1", payment_date="2026-09-27")


def test_final_invoice_applies_deposit_and_bills_balance_once(monkeypatch, tmp_path):
    finance, payments, jl = _load(monkeypatch, tmp_path)
    from app.db.database import get_db
    with get_db() as conn:
        _marleys(conn, jl)
        # the old superseded invoice does not show an open balance after its deposit
        assert conn.execute("select balance_due from invoices where id='old'").fetchone()[0] == 0
        s = jl.build_final_settlement(conn, "co1")
        assert s["contract_invoice_number"] == "INV-2026-124"
        assert s["contract_total"] == 11328.65
        assert [(c["invoice_number"], c["amount"]) for c in s["credits"]] == [("INV-2026-123", 4576.31)]
        assert s["balance_due"] == 6752.34
        made = jl.create_final_invoice(conn, "co1")
        fid = made["invoice"]["id"]
        assert made["invoice"]["invoice_stage"] == "final"
        assert made["invoice"]["balance_due"] == 6752.34
        open_ar = conn.execute("select round(sum(balance_due),2) from invoices").fetchone()[0]
        assert open_ar == 6752.34  # CO1's $1,088.02 is not billed twice
    # CO1 pay link paid AFTER the final was issued (Stripe webhook) -> final drops, no double count
    payments._update_invoice_status("co1", "paid", stripe_session_id="cs_test_co1", amount_cents=108802)
    payments._update_invoice_status("co1", "paid", stripe_session_id="cs_test_co1", amount_cents=108802)
    with get_db() as conn:
        assert conn.execute("select count(*) from payments where stripe_session_id='cs_test_co1'").fetchone()[0] == 1
        assert conn.execute("select balance_due from invoices where id=?", (fid,)).fetchone()[0] == 5664.32
        assert conn.execute("select round(sum(balance_due),2) from invoices").fetchone()[0] == 5664.32


def test_change_order_paid_by_webhook_closes_the_deposit_not_the_contract(monkeypatch, tmp_path):
    finance, payments, jl = _load(monkeypatch, tmp_path)
    from app.db.database import get_db
    with get_db() as conn:
        _marleys(conn, jl)
    payments._update_invoice_status("co1", "paid", stripe_session_id="cs_test_co1", amount_cents=108802)
    with get_db() as conn:
        row = conn.execute("select status, balance_due, amount_paid from invoices where id='co1'").fetchone()
        assert tuple(row) == ("paid", 0.0, 1088.02)  # was 10,240.63 'partial' before the ledger
        s = jl.build_final_settlement(conn, "co1")
        assert s["balance_due"] == 5664.32
        assert [c["label"] for c in s["credits"]] == ["Deposit received", "Change Order 1 payment"]


def test_manual_payment_partial_and_void(monkeypatch, tmp_path):
    finance, payments, jl = _load(monkeypatch, tmp_path)
    from app.db.database import get_db
    with get_db() as conn:
        _marleys(conn, jl)
        fid = jl.create_final_invoice(conn, "co1")["invoice"]["id"]
    with get_db() as conn:
        out = jl.record_payment(conn, fid, 2000, method="check", reference="CHK-1")
    assert out["invoice"]["status"] == "partial" and out["invoice"]["balance_due"] == 4752.34
    with get_db() as conn:
        pid = conn.execute("select id from payments where reference='CHK-1'").fetchone()[0]
        jl.void_payment(conn, pid, "bounced")
        row = conn.execute("select status, balance_due, amount_paid from invoices where id=?", (fid,)).fetchone()
        assert tuple(row) == ("draft", 6752.34, 0.0)


def test_cancelled_invoice_and_its_payments_are_ignored(monkeypatch, tmp_path):
    finance, payments, jl = _load(monkeypatch, tmp_path)
    from app.db.database import get_db
    with get_db() as conn:
        _marleys(conn, jl)
        _insert(conn, id="x", invoice_number="INV-2026-130", total=500, quote_id="q299", status="cancelled",
                created_at="2026-10-08 23:30:00")
        conn.execute("INSERT INTO payments (id, invoice_id, customer_id, amount, method, payment_date, status) "
                     "VALUES ('px', 'x', 'cust1', 500, 'cash', '2026-10-08', 'completed')")
        s = jl.build_final_settlement(conn, "co1")
        assert s["contract_invoice_number"] == "INV-2026-124"
        assert s["credit_total"] == 4576.31


def test_legacy_payments_v2_stripe_row_counted_once(monkeypatch, tmp_path):
    finance, payments, jl = _load(monkeypatch, tmp_path)
    from app.db.database import get_db
    with get_db() as conn:
        _marleys(conn, jl)
        conn.execute("""CREATE TABLE IF NOT EXISTS payments_v2 (id INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_number TEXT, invoice_id TEXT, customer_id TEXT, quote_id TEXT, amount REAL, payment_method TEXT,
            payment_reference TEXT, payment_type TEXT, status TEXT, account_code TEXT, notes TEXT,
            payment_date TEXT, created_at TEXT, updated_at TEXT, business_unit TEXT, stripe_session_id TEXT)""")
        conn.execute("INSERT INTO payments_v2 (invoice_id, amount, payment_method, status, stripe_session_id, payment_date) "
                     "VALUES ('co1', 1088.02, 'card', 'completed', 'cs_old', '2026-10-01')")
        assert jl.paid_on_invoice(conn, "co1") == 1088.02
        assert jl.session_already_recorded(conn, "cs_old")
    payments._update_invoice_status("co1", "paid", stripe_session_id="cs_old", amount_cents=108802)
    with get_db() as conn:
        assert jl.paid_on_invoice(conn, "co1") == 1088.02


def test_final_invoice_pdf_has_payments_section_and_balance_link(monkeypatch, tmp_path):
    finance, payments, jl = _load(monkeypatch, tmp_path)
    from app.db.database import get_db
    from app.services.invoice_pdf_service import render_client_invoice_html, invoice_pay_link
    with get_db() as conn:
        _marleys(conn, jl)
        fid = jl.create_final_invoice(conn, "co1")["invoice"]["id"]
        inv = finance._enrich_invoice(dict(conn.execute("select * from invoices where id=?", (fid,)).fetchone()))
    inv["stripe_checkout_url"] = "https://buy.stripe.com/test_final"
    inv["payment_status"] = "link_ready"
    html = render_client_invoice_html(inv)
    assert "Payments &amp; credits applied" in html
    assert "Deposit received" in html and "INV-2026-123" in html and "-$4,576.31" in html
    assert "$6,752.34" in html
    assert "Pay balance online: $6,752.34" in html
    assert "Empire Workroom" in html
    assert invoice_pay_link(inv)["amount"] == 6752.34


def test_header_label_keeps_whole_words():
    from app.services.estimates.mclean_estimate_pdf import _client_project, _fit_label
    client, _ = _client_project({"customer_name": "Marley's Bar & Grill · Attn Davonne Austin", "quote_number": "EST-2026-299"})
    assert client == "Marley's Bar & Grill · Attn Davonne Austin"
    assert _fit_label("Marley's Bar & Grill · Attn Davonne Austin", 30) == "Marley's Bar & Grill"
    assert _fit_label("A very long single client name without separators here", 30).endswith("…")
    assert not _fit_label("A very long single client name without separators here", 30)[:-1].endswith(" ")
