"""D48 STEP 2 — trust-mode writer hardening.

Seven writers used to pass whatever customer link they were handed straight
into a chain INSERT. STEP 1 made `invoices.customer_id` and `jobs.customer_id`
NOT NULL, which turned that from silent corruption into a bare
`sqlite3.IntegrityError` surfacing as HTTP 500. These tests assert the writers
now *reject* explicitly, before writing.

Every test here fails without the writer change:
  - the service-level ones raise `sqlite3.IntegrityError` instead of
    `MissingCustomerLink`
  - the route-level ones return 500 instead of 400

Note on the empty-string fixtures: `jobs.customer_id` is NOT NULL, so a job
with a *NULL* customer cannot be inserted at all. An empty string satisfies
NOT NULL while still being an absent link — it is the reachable form of the
defect for the writers that inherit their customer from a job (W4, W6), and a
realistic dirty value.
"""
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.services.chain_guard import MissingCustomerLink, require_customer


CUSTOMER_ID = "d48w_cust_real"
QUOTE_NULL_CUSTOMER = "d48w_quote_nocust"
JOB_EMPTY_CUSTOMER = "d48w_job_emptycust"
JOB_GOOD = "d48w_job_good"


@pytest.fixture
def chain_db(isolated_empire_db):
    """Seed the chain fixtures this module needs, on the isolated test DB.

    The test schema is brought up to production shape by conftest's
    `isolated_empire_db` (it re-runs jobs_unified.init_schema after the tables
    exist), so this fixture only seeds data.
    """
    conn = sqlite3.connect(isolated_empire_db)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(
            "INSERT INTO customers (id, name, email) VALUES (?, ?, ?)",
            (CUSTOMER_ID, "D48 Writer Test Customer", "d48w@example.test"),
        )
        # quotes_v2.customer_id is nullable — this is the real shape of 197 of
        # the 199 live quotes.
        conn.execute(
            "INSERT INTO quotes_v2 (id, quote_number, customer_id, total, status, project_name) "
            "VALUES (?, ?, NULL, ?, ?, ?)",
            (QUOTE_NULL_CUSTOMER, "Q-D48W-001", 1000.0, "approved", "D48 Writer Test Project"),
        )
        conn.execute(
            "INSERT INTO jobs (id, title, customer_id, job_number) VALUES (?, ?, ?, ?)",
            (JOB_EMPTY_CUSTOMER, "Job with absent customer link", "", "JOB-D48W-001"),
        )
        conn.execute(
            "INSERT INTO jobs (id, title, customer_id, job_number) VALUES (?, ?, ?, ?)",
            (JOB_GOOD, "Job with a real customer", CUSTOMER_ID, "JOB-D48W-002"),
        )
        conn.commit()
    finally:
        conn.close()
    return isolated_empire_db


@pytest.fixture
def client(chain_db):
    """The real router objects, mounted exactly as main.py mounts them.

    `app.main` cannot be imported here: `app/modules/label_station.py:52`
    connects to a hardcoded production path at import time (main.py:702 pulls
    it in), which trips conftest's prod-write guard. That is the known
    module-level DB_PATH defect class the D28 dispatch deferred, so it is not
    fixed here. Mounting the routers directly still enters through the real
    route handlers, dependency resolution and request/response cycle — only
    main.py's unrelated import side effects are skipped.
    """
    from fastapi import FastAPI
    from app.routers import finance, jobs_unified

    app = FastAPI()
    app.include_router(finance.router, prefix="/api/v1")
    app.include_router(jobs_unified.router, prefix="/api/v1")
    return TestClient(app)


def _count(db, table, where="1=1", params=()):
    conn = sqlite3.connect(db)
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}", params).fetchone()[0]
    finally:
        conn.close()


# ── the guard itself ───────────────────────────────────────────────

@pytest.mark.parametrize("absent", [None, "", "   ", "\t"])
def test_require_customer_rejects_absent_links(absent):
    with pytest.raises(MissingCustomerLink):
        require_customer(absent, writer="w", source="s")


def test_require_customer_passes_a_real_id_through():
    assert require_customer("abc123", writer="w", source="s") == "abc123"


def test_missing_customer_link_is_a_valueerror():
    """routers/lifecycle.py maps ValueError to HTTP 400 — that mapping is the
    reason W1/W2 need no router change. If this breaks, they silently 500."""
    assert issubclass(MissingCustomerLink, ValueError)


# ── W1 · services/lifecycle_service.py create_job_from_quote ───────

def test_w1_create_job_from_quote_rejects_quote_without_customer(chain_db):
    from app.services.lifecycle_service import create_job_from_quote

    with pytest.raises(MissingCustomerLink) as err:
        create_job_from_quote(QUOTE_NULL_CUSTOMER, "d48test")

    assert "create_job_from_quote" in str(err.value)
    assert QUOTE_NULL_CUSTOMER in str(err.value)


def test_w1_writes_nothing_when_it_refuses(chain_db):
    """The refusal must precede the INSERT — no job row, no audit row, and the
    quote must not be left pointing at a job that was never created."""
    from app.services.lifecycle_service import create_job_from_quote

    before = _count(chain_db, "jobs")
    with pytest.raises(MissingCustomerLink):
        create_job_from_quote(QUOTE_NULL_CUSTOMER, "d48test")

    assert _count(chain_db, "jobs") == before
    assert _count(chain_db, "financial_audit_log",
                  "entity_type='job' AND action='created_from_quote'") == 0
    assert _count(chain_db, "quotes_v2",
                  "id=? AND job_id IS NOT NULL", (QUOTE_NULL_CUSTOMER,)) == 0


@pytest.mark.xfail(
    strict=True,
    reason="D48 STEP 2 finding, out of scope: create_job_from_quote cannot insert "
           "into `jobs` at all. It passes status='quoted' (not in the status CHECK) "
           "and job_type=business_unit i.e. 'workroom' (not in the job_type CHECK). "
           "Verified against a copy of the production DB — both CHECKs are identical "
           "there, so this writer is non-functional in production for EVERY quote, "
           "not just the 197 with no customer. Not fixed here: STEP 2's scope is the "
           "customer link. strict=True so this fails loudly once that is repaired.",
)
def test_w1_still_creates_a_job_when_the_quote_has_a_customer(chain_db):
    """The guard must reject only absent links, not working ones."""
    from app.services.lifecycle_service import create_job_from_quote

    conn = sqlite3.connect(chain_db)
    conn.execute("UPDATE quotes_v2 SET customer_id = ? WHERE id = ?",
                 (CUSTOMER_ID, QUOTE_NULL_CUSTOMER))
    conn.commit()
    conn.close()

    result = create_job_from_quote(QUOTE_NULL_CUSTOMER, "d48test")
    assert result["id"]
    assert _count(chain_db, "jobs", "customer_id = ?", (CUSTOMER_ID,)) >= 1


# ── W2 · services/lifecycle_service.py create_invoice_from_quote ───

def test_w2_create_invoice_from_quote_rejects_quote_without_customer(chain_db):
    from app.services.lifecycle_service import create_invoice_from_quote

    with pytest.raises(MissingCustomerLink) as err:
        create_invoice_from_quote(QUOTE_NULL_CUSTOMER, "d48test")

    assert "create_invoice_from_quote" in str(err.value)


def test_w2_writes_no_invoice_when_it_refuses(chain_db):
    from app.services.lifecycle_service import create_invoice_from_quote

    before = _count(chain_db, "invoices")
    with pytest.raises(MissingCustomerLink):
        create_invoice_from_quote(QUOTE_NULL_CUSTOMER, "d48test")

    assert _count(chain_db, "invoices") == before
    assert _count(chain_db, "financial_audit_log",
                  "entity_type='invoice' AND action='created_from_quote'") == 0


# ── W3 · routers/jobs_unified.py create_job (POST /api/v1/jobs) ────

def test_w3_post_jobs_without_customer_is_rejected_400(client, chain_db):
    before = _count(chain_db, "jobs")
    r = client.post("/api/v1/jobs", json={"title": "Job with no customer"})

    assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text[:400]}"
    assert "customer" in r.text.lower()
    assert _count(chain_db, "jobs") == before


def test_w3_post_jobs_with_customer_still_succeeds(client, chain_db):
    """Asserted against the stored row, not the response body: the handler
    reads back with `SELECT * FROM jobs ORDER BY created_at DESC LIMIT 1`
    (jobs_unified.py:1147), which returns whichever row shares the newest
    one-second timestamp — a pre-existing defect, noted in the STEP 2 mapping
    report and deliberately not fixed here."""
    title = "Job with customer D48W"
    r = client.post("/api/v1/jobs", json={"title": title, "customer_id": CUSTOMER_ID})

    assert r.status_code == 200, f"{r.status_code}: {r.text[:400]}"
    assert _count(chain_db, "jobs", "title = ? AND customer_id = ?",
                  (title, CUSTOMER_ID)) == 1


# ── W4 · routers/jobs_unified.py invoice_from_job ──────────────────

def test_w4_invoice_from_job_rejects_job_with_absent_customer(client, chain_db):
    before = _count(chain_db, "invoices")
    r = client.post(f"/api/v1/invoices/from-job/{JOB_EMPTY_CUSTOMER}")

    assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text[:400]}"
    assert "customer" in r.text.lower()
    assert _count(chain_db, "invoices") == before


# ── W5 · routers/finance.py create_invoice (narrow) ────────────────

def test_w5_finance_invoice_without_customer_or_name_is_rejected_400(client, chain_db):
    before = _count(chain_db, "invoices")
    r = client.post("/api/v1/finance/invoices", json={"subtotal": 100})

    assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text[:400]}"
    assert _count(chain_db, "invoices") == before


def test_w5_whitespace_only_customer_name_is_rejected_400(client, chain_db):
    """A blank-ish name passes the `if invoice.customer_name` check but makes
    _find_or_create_customer_for_invoice return None — the second NULL path."""
    r = client.post("/api/v1/finance/invoices",
                    json={"subtotal": 100, "customer_name": "   "})
    assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text[:400]}"


def test_w5_find_or_create_is_left_intact(client, chain_db):
    """Ruling 1 was 'narrow': the pre-existing find-or-create must still work.
    This is the regression guard proving the fix did not remove smart-mode
    behaviour from a writer that already had it."""
    r = client.post("/api/v1/finance/invoices",
                    json={"subtotal": 100, "customer_name": "Brand New D48 Client"})
    assert r.status_code == 200, f"{r.status_code}: {r.text[:400]}"
    assert _count(chain_db, "customers", "name = ?", ("Brand New D48 Client",)) == 1


# ── W6 · routers/finance.py create_invoice_from_job ────────────────

def test_w6_finance_invoice_from_job_rejects_absent_customer(client, chain_db):
    before = _count(chain_db, "invoices")
    r = client.post(f"/api/v1/finance/invoices/from-job/{JOB_EMPTY_CUSTOMER}")

    assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text[:400]}"
    assert _count(chain_db, "invoices") == before


# ── W7 · routers/jobs.py create_job (unmounted) ────────────────────

def test_w7_unmounted_create_job_still_refuses(chain_db):
    """routers/jobs.py is not mounted (main.py:179). Called directly, because
    there is no route to enter through — hardened per ruling 2 since it is one
    uncommented line from being live."""
    from fastapi import HTTPException
    from app.routers.jobs import create_job, JobCreate

    before = _count(chain_db, "jobs")
    with pytest.raises(HTTPException) as err:
        create_job(JobCreate(title="Job with no customer"))

    assert err.value.status_code == 400
    assert "customer" in str(err.value.detail).lower()
    assert _count(chain_db, "jobs") == before


def test_w7_is_still_unmounted():
    """If this fails, routers/jobs.py went live and its overlap with
    jobs_unified needs a ruling — see the STEP 2 mapping report.

    Checked statically rather than via `app.main`, which cannot be imported
    under test (see the `client` fixture).
    """
    from pathlib import Path

    main_py = Path(__file__).resolve().parent.parent / "app" / "main.py"
    lines = [
        ln.strip()
        for ln in main_py.read_text().splitlines()
        if 'load_router("app.routers.jobs"' in ln
    ]
    assert lines, 'no load_router line for "app.routers.jobs" found in main.py'
    assert all(ln.startswith("#") for ln in lines), (
        f"routers/jobs.py is mounted again — resolve the overlap: {lines}"
    )
