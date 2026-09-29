"""D48 STEP 2 — schema parity guard.

Ruling 3: the test schema must carry the same chain constraints as
production. Before this, `unified_business_migration.create_all_tables`
did not create `invoices` or `jobs` at all, so no test could reach the
NOT NULL constraints that STEP 1 applied to the live database — and the
STEP 1 suite reported a clean delta purely because the constraint was
unreachable in tests.

These tests fail if that regresses.
"""
import sqlite3

import pytest


CHAIN_TABLES = ("customers", "invoices", "jobs", "payments")

# (table, column, expected_notnull)
CHAIN_CONSTRAINTS = (
    ("invoices", "customer_id", 1),
    ("jobs", "customer_id", 1),
    ("payments", "invoice_id", 1),
    # Deliberately nullable in production — asserted so an over-eager
    # future tightening also shows up here.
    ("payments", "customer_id", 0),
    ("jobs", "invoice_id", 0),
)


def _conn(isolated_empire_db):
    conn = sqlite3.connect(isolated_empire_db)
    conn.row_factory = sqlite3.Row
    return conn


@pytest.mark.parametrize("table", CHAIN_TABLES)
def test_chain_table_exists_in_test_schema(isolated_empire_db, table):
    conn = _conn(isolated_empire_db)
    try:
        found = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()[0]
    finally:
        conn.close()
    assert found == 1, (
        f"{table} missing from the test schema — chain writers cannot be "
        f"tested against production-shaped constraints"
    )


@pytest.mark.parametrize("table,column,expected", CHAIN_CONSTRAINTS)
def test_chain_constraint_matches_production(isolated_empire_db, table, column, expected):
    conn = _conn(isolated_empire_db)
    try:
        info = {r["name"]: r["notnull"] for r in conn.execute(f"PRAGMA table_info({table})")}
    finally:
        conn.close()
    assert column in info, f"{table}.{column} absent from test schema"
    assert info[column] == expected, (
        f"{table}.{column} notnull={info[column]}, production has {expected}"
    )


def test_null_customer_is_rejected_by_the_test_schema(isolated_empire_db):
    """The constraint must actually fire here, not merely be declared.

    NOT NULL is enforced without PRAGMA foreign_keys, so this holds on
    every connection.
    """
    conn = _conn(isolated_empire_db)
    try:
        with pytest.raises(sqlite3.IntegrityError, match="NOT NULL constraint failed"):
            conn.execute(
                "INSERT INTO invoices (invoice_number, customer_id) VALUES (?, NULL)",
                ("D48-PARITY-PROBE",),
            )
        conn.rollback()
    finally:
        conn.close()
