"""Safe glue from the October 2026 module audit.

Read-only / temp-DB only. Does not write live tenant data.
"""
from app.db.init_db import SCHEMA_SQL
from app.services.lifecycle_service import command_center_href


def test_command_center_href_maps_estimate_job_client():
    assert command_center_href("quote", "q-1") == "/?screen=quote&id=q-1"
    assert command_center_href("job", "j-1") == "/?screen=jobs&id=j-1"
    assert command_center_href("invoice", "i-1") == "/?screen=invoices&id=i-1"
    assert command_center_href("customer", "c-1") == "/?screen=crm&id=c-1"
    assert command_center_href("work_order", "wo-1") == "/?screen=jobs&id=wo-1"
    assert command_center_href("unknown", "x") == "/?screen=dashboard"


def test_schema_sql_includes_audit_indexes():
    for name in (
        "idx_customers_email",
        "idx_customers_phone",
        "idx_customers_business",
        "idx_invoices_quote",
        "idx_invoices_due",
        "idx_jobs_quote",
        "idx_payments_customer",
    ):
        assert f"CREATE INDEX IF NOT EXISTS {name}" in SCHEMA_SQL


def test_leadforge_schema_has_customer_id_and_indexes():
    from pathlib import Path

    # Read source only — importing leadforge.py runs _init_tables() against the
    # configured DB, which this audit must not do.
    src = (Path(__file__).resolve().parents[1] / "app" / "routers" / "leadforge.py").read_text()
    assert "customer_id TEXT" in src
    assert "idx_lf_leads_email" in src
    assert "idx_lf_leads_customer" in src
    # Activity CHECK does not include forge_crm_promoted; promote must use an allowed type.
    assert '"note"' in src or "'note'" in src
