"""Tests for the Customer Journey Linkage MVP.

The MVP is **read-only**: no live writes to the empire.db are performed.
The tests run against the live DB (read-only via the read-only URI
mode in journey_linkage._open_db). All tests assert either:
    - the function returns the expected dataclass shape, OR
    - the function raises an HTTPException with the expected status.

No live customer, invoice, or payment records are created.
No legacy tables are deleted or archived.
"""
import os
import sys
import sqlite3
import json
import tempfile
import pytest

LIVE_VENV = "/home/rg/empire-repo/backend/venv/lib/python3.12/site-packages"
if LIVE_VENV not in sys.path:
    sys.path.insert(0, LIVE_VENV)

# Make the app importable
APP_ROOT = "/home/rg/empire-repo-main/backend"
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

# Verify the live DB is accessible (read-only)
LIVE_DB = "/home/rg/empire-repo/backend/data/empire.db"
if not os.path.exists(LIVE_DB):
    pytest.skip(f"Live empire.db not found at {LIVE_DB}", allow_module_level=True)

from app.services.max.journey_linkage import (
    get_customer_journey,
    get_invoice_for_quote,
    get_quote_for_invoice,
    run_backfill_audit,
    _open_db,
    BACKFILL_AUDIT_PATH,
    DEFAULT_DB_PATH,
    TAG_ANONYMOUS,
    TAG_ORPHAN,
    TAG_NO_QUOTE,
    TAG_HAS_LINKED,
)


# ── Fixture: an isolated in-memory DB for shape tests ─────────────────


@pytest.fixture
def in_memory_db():
    """Build a fresh in-memory SQLite DB that mirrors the live schema
    for the 4 tables the journey service touches: customers, quotes_v2,
    invoices, payments. Lets us test behavior without touching the
    real empire.db.
    """
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.executescript("""
        CREATE TABLE customers (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            address TEXT
        );
        CREATE TABLE quotes_v2 (
            id TEXT PRIMARY KEY,
            quote_number TEXT NOT NULL,
            customer_id TEXT,
            customer_name TEXT,
            customer_email TEXT,
            status TEXT,
            total REAL DEFAULT 0,
            created_at TEXT,
            business_unit TEXT,
            project_name TEXT
        );
        CREATE TABLE quote_line_items (
            id INTEGER PRIMARY KEY,
            quote_id TEXT
        );
        CREATE TABLE invoices (
            id TEXT PRIMARY KEY,
            invoice_number TEXT NOT NULL,
            customer_id TEXT,
            quote_id TEXT,
            status TEXT,
            total REAL DEFAULT 0,
            amount_paid REAL DEFAULT 0,
            balance_due REAL DEFAULT 0,
            due_date TEXT,
            paid_at TEXT,
            created_at TEXT,
            line_items TEXT
        );
        CREATE TABLE payments (
            id TEXT PRIMARY KEY,
            customer_id TEXT,
            invoice_id TEXT,
            amount REAL,
            method TEXT,
            reference TEXT,
            payment_date TEXT,
            created_at TEXT
        );
    """)
    # Insert test data: 1 customer, 2 quotes (1 linked, 1 anonymous),
    # 2 invoices (1 with valid link, 1 dangling), 1 payment
    cur.execute("INSERT INTO customers VALUES (?,?,?,?,?)",
                ("cust-1", "Alice", "alice@example.com", "555-0001", "1 Main St"))
    cur.execute("INSERT INTO quotes_v2 VALUES (?,?,?,?,?,?,?,?,?,?)",
                ("q-1", "Q-001", "cust-1", "Alice", "alice@example.com", "sent", 100.0, "2026-01-01", "default", "P1"))
    cur.execute("INSERT INTO quotes_v2 VALUES (?,?,?,?,?,?,?,?,?,?)",
                ("q-2", "Q-002", None, "Bob", "bob@example.com", "draft", 50.0, "2026-01-02", "default", "P2"))
    cur.execute("INSERT INTO invoices VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                ("inv-1", "INV-001", "cust-1", "q-1", "partial", 100.0, 50.0, 50.0, "2026-02-01", None, "2026-01-15", "[]"))
    cur.execute("INSERT INTO invoices VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                ("inv-2", "INV-002", "cust-1", "q-does-not-exist", "draft", 200.0, 0, 200.0, "2026-02-02", None, "2026-01-16", "[]"))
    cur.execute("INSERT INTO payments VALUES (?,?,?,?,?,?,?,?)",
                ("pay-1", "cust-1", "inv-1", 50.0, "cash", "ref-1", "2026-02-15", "2026-02-15"))
    con.commit()
    yield con
    con.close()


# ── 1. Happy path: customer with full chain ───────────────────────────


def test_get_customer_journey_happy_path(in_memory_db):
    """A customer with 1 quote + 1 linked invoice + 1 payment returns
    the full chain in the expected shape.
    """
    # Use the in-memory DB
    path = in_memory_db_path_for(in_memory_db)
    j = get_customer_journey("cust-1", db_path=path)
    assert j is not None
    d = j.to_dict()
    assert d["customer_id"] == "cust-1"
    assert d["customer"]["name"] == "Alice"
    assert d["customer"]["email"] == "alice@example.com"
    # 1 linked quote
    assert d["totals"]["quote_count"] == 1
    assert len(d["quotes"]) == 1
    assert d["quotes"][0]["quote_id"] == "q-1"
    assert d["quotes"][0]["customer_link"] == "linked"
    # 1 linked invoice (linked through q-1) + 1 orphan invoice (dangling quote_id)
    # Note: inv-1 is linked to q-1 (which is in linked_quote_ids), so it shows
    # only in the totals.linked_invoice_count, not in orphan_invoices.
    # inv-2 has a quote_id of "q-does-not-exist" which is NOT in linked_quote_ids,
    # so it appears in orphan_invoices.
    assert d["totals"]["linked_invoice_count"] == 1
    assert d["totals"]["orphan_invoice_count"] == 1
    assert len(d["orphan_invoices"]) == 1
    assert d["orphan_invoices"][0]["invoice_id"] == "inv-2"
    assert d["orphan_invoices"][0]["quote_link"] == "no_quote"


# ── 2. Customer with no records ────────────────────────────────────────


def test_get_customer_journey_empty(in_memory_db):
    """A customer with no quotes/invoices/payments returns an empty journey."""
    # Insert a customer with no activity
    in_memory_db.execute("INSERT INTO customers VALUES (?,?,?,?,?)",
                          ("cust-empty", "Empty", None, None, None))
    in_memory_db.commit()
    path = in_memory_db_path_for(in_memory_db)
    j = get_customer_journey("cust-empty", db_path=path)
    assert j is not None
    d = j.to_dict()
    assert d["customer"]["name"] == "Empty"
    assert d["quotes"] == []
    assert d["orphan_invoices"] == []
    assert d["orphan_payments"] == []
    assert d["totals"]["quote_count"] == 0


# ── 3. Customer not found ─────────────────────────────────────────────


def test_get_customer_journey_not_found(in_memory_db):
    path = in_memory_db_path_for(in_memory_db)
    j = get_customer_journey("does-not-exist", db_path=path)
    assert j is None


# ── 4. Quote with linked invoice ──────────────────────────────────────


def test_get_invoice_for_quote_linked(in_memory_db):
    path = in_memory_db_path_for(in_memory_db)
    result = get_invoice_for_quote("q-1", db_path=path)
    assert result["link"] == "linked"
    assert result["invoice"]["id"] == "inv-1"
    assert result["invoice"]["invoice_number"] == "INV-001"


# ── 5. Quote with no invoice ──────────────────────────────────────────


def test_get_invoice_for_quote_no_invoice(in_memory_db):
    path = in_memory_db_path_for(in_memory_db)
    result = get_invoice_for_quote("q-2", db_path=path)
    assert result["link"] == "no_invoice"
    assert result["invoice"] is None


# ── 6. Quote does not exist ───────────────────────────────────────────


def test_get_invoice_for_quote_no_quote(in_memory_db):
    path = in_memory_db_path_for(in_memory_db)
    result = get_invoice_for_quote("does-not-exist", db_path=path)
    assert result["link"] == "no_quote"
    assert result["invoice"] is None


# ── 7. Invoice with linked quote ──────────────────────────────────────


def test_get_quote_for_invoice_linked(in_memory_db):
    path = in_memory_db_path_for(in_memory_db)
    result = get_quote_for_invoice("inv-1", db_path=path)
    assert result["link"] == "linked"
    assert result["quote"]["id"] == "q-1"


# ── 8. Invoice with dangling quote_id (the key scenario) ─────────────


def test_get_quote_for_invoice_dangling(in_memory_db):
    """An invoice whose quote_id points to a missing quote must return
    link='dangling', not 'no_quote' and not 'no_invoice'. This is
    the most important diagnostic case for the carry-forward audit.
    """
    path = in_memory_db_path_for(in_memory_db)
    result = get_quote_for_invoice("inv-2", db_path=path)
    assert result["link"] == "dangling"
    assert result["quote"] is None
    assert result["quote_id"] == "q-does-not-exist"


# ── 9. Backfill audit: produces correct shape ──────────────────────────


def test_run_backfill_audit_returns_audit_dict(in_memory_db):
    """The backfill audit must inspect the DB, produce a summary dict
    with quotes_v2/invoices/payments/recommendations, and write a JSON
    audit log under backend/data/.
    """
    # We can't easily point the audit at the in-memory DB because the
    # audit writes to a fixed JSON path under backend/data/. Instead,
    # we copy the in-memory DB to a temp file and use that.
    fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        # Copy the in-memory DB to the temp file
        in_memory_db.commit()
        new_con = sqlite3.connect(tmp_path)
        for line in in_memory_db.iterdump():
            new_con.execute(line)
        new_con.commit()
        new_con.close()

        # Run the audit against the temp DB
        audit = run_backfill_audit(db_path=tmp_path)
        d = audit.to_dict()
        assert d["db_path"] == tmp_path
        # quotes_v2: 2 total, 1 with customer_id, 1 anonymous
        assert d["quotes_v2"]["total"] == 2
        assert d["quotes_v2"]["with_customer_id"] == 1
        assert d["quotes_v2"]["anonymous"] == 1
        # invoices: 2 total, 2 with quote_id, 1 linked, 1 dangling
        assert d["invoices"]["total"] == 2
        assert d["invoices"]["with_quote_id"] == 2
        assert d["invoices"]["linked_to_real_quote"] == 1
        assert d["invoices"]["dangling_quote_id"] == 1
        # recommendations: at least the anonymous recommendation
        tags = [r["tag"] for r in d["recommendations"]]
        assert "anonymous" in tags
        assert "dangling_invoice" in tags
    finally:
        # Reset env override so subsequent tests see the live DB
        _reset_db_path_env()
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ── 10. Backfill audit: does NOT write to the live DB ─────────────────


def test_backfill_audit_does_not_modify_live_db():
    """The audit must be read-only. We measure the file size and mtime
    of the live DB before and after running the audit; both must be
    unchanged.
    """
    size_before = os.path.getsize(LIVE_DB)
    mtime_before = os.path.getmtime(LIVE_DB)
    audit = run_backfill_audit(db_path=LIVE_DB)
    size_after = os.path.getsize(LIVE_DB)
    mtime_after = os.path.getmtime(LIVE_DB)
    assert size_before == size_after, "backfill audit must not write to live DB (size changed)"
    assert mtime_before == mtime_after, "backfill audit must not write to live DB (mtime changed)"
    # And the audit still ran successfully
    assert audit.quotes_v2["total"] >= 0  # any non-negative number


# ── 11. Backfill audit: writes the JSON audit log ─────────────────────


def test_backfill_audit_writes_json():
    """The audit writes a JSON file under backend/data/. Running the
    audit should produce/update that file.
    """
    audit = run_backfill_audit(db_path=LIVE_DB)
    assert os.path.exists(BACKFILL_AUDIT_PATH)
    with open(BACKFILL_AUDIT_PATH) as f:
        data = json.load(f)
    assert "ran_at" in data
    assert "db_path" in data
    assert "quotes_v2" in data
    assert "invoices" in data
    assert "payments" in data
    assert "recommendations" in data
    # The audit's own db_path must match what the JSON says
    assert data["db_path"] == audit.db_path


# ── 12. _open_db is read-only ──────────────────────────────────────────


def test_open_db_is_read_only():
    """The internal _open_db helper must open the DB in read-only mode
    by default. Attempting a write through it should fail.
    """
    with _open_db() as conn:
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("DELETE FROM customers WHERE id = 'cust-1'")


# ── 13. No destructive legacy-table changes ───────────────────────────


def test_legacy_tables_untouched():
    """The audit and journey lookups must not touch the legacy tables:
        sf_customers, sf2_customers, assist_clients, payments_v2, cf_payments
    The audit only queries customers, quotes_v2, invoices, payments.
    """
    # Run the audit, then verify the legacy tables still have the same
    # row counts they had before.
    legacy_tables = ["sf_customers", "sf2_customers", "assist_clients",
                     "payments_v2", "cf_payments", "invoice_payments"]
    with _open_db() as conn:
        before = {}
        for t in legacy_tables:
            try:
                before[t] = conn.execute(f"SELECT COUNT(*) AS n FROM {t}").fetchone()["n"]
            except sqlite3.OperationalError:
                before[t] = -1  # table does not exist

    run_backfill_audit(db_path=LIVE_DB)

    with _open_db() as conn:
        for t, n in before.items():
            if n < 0:
                continue  # table didn't exist
            after = conn.execute(f"SELECT COUNT(*) AS n FROM {t}").fetchone()["n"]
            assert after == n, f"legacy table {t} changed: {n} -> {after}"


# ── 14. Live integration test: hit the real DB with a real customer ───


def test_live_journey_osteria_marzano():
    """OSTERIA MARZANO (4ea5a8c917600732) is a real customer in the
    live DB with 3 invoices and 1 payment. The journey must surface
    them honestly.
    """
    j = get_customer_journey("4ea5a8c917600732", db_path=LIVE_DB)
    assert j is not None
    d = j.to_dict()
    assert d["customer"]["name"] == "OSTERIA MARZANO"
    # All 3 quotes_v2 have no customer_id in the live DB → 0 linked
    assert d["totals"]["quote_count"] == 0
    # But the invoices have customer_id = this customer and quote_id
    # pointing to missing quotes → 3 orphan invoices
    assert d["totals"]["orphan_invoice_count"] == 3
    # 1 orphan payment (customer_id set, invoice_id dangling)
    assert d["totals"]["orphan_payment_count"] == 1


# ── 15. Live integration: real reverse lookups ────────────────────────


def test_live_invoice_for_quote_found():
    """64b5fc17b0e8feea is a real invoice. get_invoice_for_quote for
    its quote_id returns a 'linked' result (because the invoice has
    that quote_id), even though the underlying quote is missing.
    """
    r = get_invoice_for_quote("4a89449c-94ac-42e6-bb64-ac71b2d13150", db_path=LIVE_DB)
    assert r["link"] == "linked"
    assert r["invoice"]["id"] == "64b5fc17b0e8feea"


def test_live_quote_for_invoice_dangling():
    """The same invoice, looked up the other way, has a dangling
    quote_id (the quote doesn't exist in quotes_v2).
    """
    r = get_quote_for_invoice("64b5fc17b0e8feea", db_path=LIVE_DB)
    assert r["link"] == "dangling"
    assert r["quote_id"] == "4a89449c-94ac-42e6-bb64-ac71b2d13150"


# ── Helper ──────────────────────────────────────────────────────────────


def in_memory_db_path_for(in_memory_con):
    """Write the in-memory DB to a temp file and return the path.
    This lets us use the existing _open_db helper which expects a file.
    """
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    new_con = sqlite3.connect(path)
    new_con.row_factory = sqlite3.Row
    for line in in_memory_con.iterdump():
        new_con.execute(line)
    new_con.commit()
    new_con.close()
    # Use an env override so subsequent _resolve_db_path returns this
    os.environ["EMPIRE_DB_PATH"] = path
    return path


def _reset_db_path_env():
    """Reset EMPIRE_DB_PATH to the live path. Call this at the end of
    any test that touched the env var so subsequent tests see the
    real DB.
    """
    os.environ.pop("EMPIRE_DB_PATH", None)
