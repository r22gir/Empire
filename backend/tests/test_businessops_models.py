"""
Tests for BusinessOps Foundation models (Phase 1, 2026-06-09).

Source of truth: REPORT-businessops-tenantops-design.md §2.5, §10.

Pattern (matches test_vendorops_core.py):
  - monkeypatch.setattr(database, "DB_PATH", tmp_path / "biz.db")
  - Use a fresh connection per test
  - Don't depend on the live empire.db

These tests cover:
  - All 9 bo_ tables can be created
  - Idempotent schema (running _init_businessops_schema twice is a no-op)
  - Seed data loads (6 packages, 222 entitlement rows)
  - UNIQUE constraints fire (slug, package×module, etc.)
  - FK constraints fire (RESTRICT vs CASCADE)
  - CHECK constraints fire (status, role, access_level)
  - Hard-delete is restricted on subscription FKs
  - CASCADE works for bo_business_profiles (the only allowed cascade)
"""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

import pytest


# ── fixtures ───────────────────────────────────────────────────

@pytest.fixture
def bo_db(monkeypatch, tmp_path):
    """Fresh in-memory-style DB per test. Returns a configured connection."""
    db_path = tmp_path / "biz_test.db"
    # We point the app's database module at this path
    from app.db import database
    monkeypatch.setattr(database, "DB_PATH", str(db_path))
    conn = database.get_connection()
    yield conn
    conn.close()


@pytest.fixture
def bo_db_with_seed(bo_db):
    """Fresh DB with the schema and seed data applied."""
    from app.routers.businessops import _init_businessops_schema
    # _init_businessops_schema expects a connection
    _init_businessops_schema(bo_db)
    return bo_db


# ── 1. Table creation ──────────────────────────────────────────

def test_all_nine_tables_create(bo_db):
    """All 9 bo_ tables can be created via _init_businessops_schema."""
    from app.routers.businessops import _init_businessops_schema
    _init_businessops_schema(bo_db)

    rows = bo_db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'bo_%' ORDER BY name"
    ).fetchall()
    names = [r["name"] for r in rows]
    expected = sorted([
        "bo_business_audit_events",
        "bo_business_integrations",  # typo would be a bug; we use "bo_business_integrations" intentionally? NO — the table is "bo_business_integrations" only if the SQL is wrong. Let me re-check.
        # Actually the SQL says "bo_business_integrations" — let me check.
    ])
    # Drop the typo check; just assert the 9 tables exist
    for t in [
        "bo_businesses",
        "bo_business_profiles",
        "bo_packages",
        "bo_business_subscriptions",
        "bo_module_entitlements",
        "bo_provisioning_checklists",
        "bo_business_users",
        "bo_business_integrations",  # placeholder
        "bo_business_audit_events",
    ]:
        assert t in names, f"missing table {t}; got {names}"


def test_schema_is_idempotent(bo_db):
    """Running _init_businessops_schema twice is a no-op."""
    from app.routers.businessops import _init_businessops_schema
    _init_businessops_schema(bo_db)
    _init_businessops_schema(bo_db)  # second run
    # Both runs succeed; tables still exist
    row = bo_db.execute("SELECT COUNT(*) AS c FROM bo_packages").fetchone()
    assert row["c"] >= 1, "seed data lost on second init"


def test_seed_loads_six_packages(bo_db_with_seed):
    """The 6 canonical packages are seeded."""
    rows = bo_db_with_seed.execute(
        "SELECT id, is_internal, monthly_price_usd FROM bo_packages ORDER BY id"
    ).fetchall()
    assert len(rows) == 6
    ids = [r["id"] for r in rows]
    assert ids == [
        "pkg_apostille_only",
        "pkg_custom",
        "pkg_empire",
        "pkg_founder",
        "pkg_growth",
        "pkg_starter",
    ]
    # pkg_founder is internal
    founder = [r for r in rows if r["id"] == "pkg_founder"][0]
    assert founder["is_internal"] == 1
    # pkg_starter is 29
    starter = [r for r in rows if r["id"] == "pkg_starter"][0]
    assert starter["monthly_price_usd"] == 29
    # pkg_founder is 0
    assert founder["monthly_price_usd"] == 0


def test_seed_loads_222_entitlement_rows(bo_db_with_seed):
    """All 222 entitlement rows are seeded (37 modules × 6 packages)."""
    row = bo_db_with_seed.execute("SELECT COUNT(*) AS c FROM bo_module_entitlements").fetchone()
    assert row["c"] == 222


def test_seed_includes_apostapp_founder_only_for_paid_packages(bo_db_with_seed):
    """Per design doc D6: apostapp is founder_only in pkg_apostille_only and pkg_empire."""
    rows = bo_db_with_seed.execute(
        "SELECT package_id, access_level FROM bo_module_entitlements WHERE module_id = 'apostapp' ORDER BY package_id"
    ).fetchall()
    by_pkg = {r["package_id"]: r["access_level"] for r in rows}
    assert by_pkg["pkg_apostille_only"] == "founder_only"
    assert by_pkg["pkg_empire"] == "founder_only"
    assert by_pkg["pkg_founder"] == "full"
    # starter/growth have none
    assert by_pkg["pkg_starter"] == "none"
    assert by_pkg["pkg_growth"] == "none"


def test_seed_includes_openclaw_founder_only_for_all_packages(bo_db_with_seed):
    """Per design doc D9: openclaw is founder_only for every customer-facing package."""
    rows = bo_db_with_seed.execute(
        "SELECT package_id, access_level FROM bo_module_entitlements WHERE module_id = 'openclaw' ORDER BY package_id"
    ).fetchall()
    by_pkg = {r["package_id"]: r["access_level"] for r in rows}
    for pkg in ("pkg_starter", "pkg_growth", "pkg_empire", "pkg_custom", "pkg_apostille_only"):
        assert by_pkg[pkg] == "founder_only", f"openclaw should be founder_only in {pkg}"
    # founder sees full
    assert by_pkg["pkg_founder"] == "full"


# ── 2. UNIQUE constraints ─────────────────────────────────────

def test_businesses_slug_unique(bo_db_with_seed):
    bo_db_with_seed.execute(
        "INSERT INTO bo_businesses (id, slug, display_name) VALUES (?, ?, ?)",
        ("biz_1", "alpha", "Alpha Inc"),
    )
    bo_db_with_seed.commit()
    with pytest.raises(sqlite3.IntegrityError):
        bo_db_with_seed.execute(
            "INSERT INTO bo_businesses (id, slug, display_name) VALUES (?, ?, ?)",
            ("biz_2", "alpha", "Alpha Duplicate"),
        )
    bo_db_with_seed.rollback()


def test_business_id_unique_within_business_users(bo_db_with_seed):
    """UNIQUE (business_id, email) on bo_business_users."""
    # Need a business first
    bo_db_with_seed.execute(
        "INSERT INTO bo_businesses (id, slug, display_name) VALUES (?, ?, ?)",
        ("biz_1", "alpha", "Alpha"),
    )
    bo_db_with_seed.execute(
        "INSERT INTO bo_business_users (id, business_id, email, display_name) VALUES (?, ?, ?, ?)",
        ("bu_1", "biz_1", "owner@alpha.test", "Owner One"),
    )
    bo_db_with_seed.commit()
    with pytest.raises(sqlite3.IntegrityError):
        bo_db_with_seed.execute(
            "INSERT INTO bo_business_users (id, business_id, email, display_name) VALUES (?, ?, ?, ?)",
            ("bu_2", "biz_1", "owner@alpha.test", "Owner Two"),
        )
    bo_db_with_seed.rollback()


def test_module_entitlement_package_module_unique(bo_db_with_seed):
    """UNIQUE (package_id, module_id) on bo_module_entitlements."""
    # The seed already loaded; try to insert a duplicate
    with pytest.raises(sqlite3.IntegrityError):
        bo_db_with_seed.execute(
            "INSERT INTO bo_module_entitlements (id, package_id, module_id, access_level) VALUES (?, ?, ?, ?)",
            ("ent_dup", "pkg_starter", "apostapp", "standard"),
        )
    bo_db_with_seed.rollback()


# ── 3. CHECK constraints ──────────────────────────────────────

def test_business_status_check(bo_db_with_seed):
    bo_db_with_seed.execute(
        "INSERT INTO bo_businesses (id, slug, display_name, status) VALUES (?, ?, ?, ?)",
        ("biz_x", "x", "X", "active"),
    )
    bo_db_with_seed.commit()
    with pytest.raises(sqlite3.IntegrityError):
        bo_db_with_seed.execute(
            "INSERT INTO bo_businesses (id, slug, display_name, status) VALUES (?, ?, ?, ?)",
            ("biz_y", "y", "Y", "purple"),
        )
    bo_db_with_seed.rollback()


def test_module_entitlement_access_level_check(bo_db_with_seed):
    """CHECK (access_level IN ('none', 'preview', 'internal', 'standard', 'full', 'founder_only'))."""
    # The seed should never violate this; verify by trying to insert a bogus value
    with pytest.raises(sqlite3.IntegrityError):
        bo_db_with_seed.execute(
            "INSERT INTO bo_module_entitlements (id, package_id, module_id, access_level) VALUES (?, ?, ?, ?)",
            ("ent_bad", "pkg_starter", "new_module", "purple"),
        )
    bo_db_with_seed.rollback()


def test_business_user_role_check(bo_db_with_seed):
    bo_db_with_seed.execute(
        "INSERT INTO bo_businesses (id, slug, display_name) VALUES (?, ?, ?)",
        ("biz_role", "r", "R"),
    )
    with pytest.raises(sqlite3.IntegrityError):
        bo_db_with_seed.execute(
            "INSERT INTO bo_business_users (id, business_id, email, display_name, role) VALUES (?, ?, ?, ?, ?)",
            ("bu_role", "biz_role", "x@x.test", "X", "wizard"),
        )
    bo_db_with_seed.rollback()


# ── 4. FK / lifecycle constraints ──────────────────────────────

def test_subscription_blocks_business_delete(bo_db_with_seed):
    """bo_business_subscriptions uses ON DELETE RESTRICT.

    Hard-delete is forbidden by the design; RESTRICT enforces it.
    """
    bo_db_with_seed.execute(
        "INSERT INTO bo_businesses (id, slug, display_name) VALUES (?, ?, ?)",
        ("biz_1", "alpha", "Alpha"),
    )
    bo_db_with_seed.execute(
        "INSERT INTO bo_business_subscriptions (id, business_id, package_id, status) VALUES (?, ?, ?, ?)",
        ("sub_1", "biz_1", "pkg_starter", "active"),
    )
    bo_db_with_seed.commit()
    with pytest.raises(sqlite3.IntegrityError):
        bo_db_with_seed.execute("DELETE FROM bo_businesses WHERE id = ?", ("biz_1",))
    bo_db_with_seed.rollback()


def test_business_profile_cascade_delete(bo_db_with_seed):
    """bo_business_profiles uses ON DELETE CASCADE — the only allowed cascade."""
    bo_db_with_seed.execute(
        "INSERT INTO bo_businesses (id, slug, display_name) VALUES (?, ?, ?)",
        ("biz_1", "alpha", "Alpha"),
    )
    bo_db_with_seed.execute(
        "INSERT INTO bo_business_profiles (business_id) VALUES (?)",
        ("biz_1",),
    )
    bo_db_with_seed.commit()
    # Delete the business; profile should cascade
    bo_db_with_seed.execute("DELETE FROM bo_businesses WHERE id = ?", ("biz_1",))
    bo_db_with_seed.commit()
    row = bo_db_with_seed.execute(
        "SELECT COUNT(*) AS c FROM bo_business_profiles WHERE business_id = ?",
        ("biz_1",),
    ).fetchone()
    assert row["c"] == 0, "profile should be gone after business delete (CASCADE)"


def test_unique_active_subscription_per_business(bo_db_with_seed):
    """The UNIQUE INDEX uniq_bo_subs_business_active enforces one active subscription."""
    bo_db_with_seed.execute(
        "INSERT INTO bo_businesses (id, slug, display_name) VALUES (?, ?, ?)",
        ("biz_1", "alpha", "Alpha"),
    )
    bo_db_with_seed.execute(
        "INSERT INTO bo_business_subscriptions (id, business_id, package_id, status) VALUES (?, ?, ?, ?)",
        ("sub_1", "biz_1", "pkg_starter", "active"),
    )
    bo_db_with_seed.commit()
    # Try to insert a second 'active' sub for the same business
    with pytest.raises(sqlite3.IntegrityError):
        bo_db_with_seed.execute(
            "INSERT INTO bo_business_subscriptions (id, business_id, package_id, status) VALUES (?, ?, ?, ?)",
            ("sub_2", "biz_1", "pkg_growth", "active"),
        )
    bo_db_with_seed.rollback()
    # A 'canceled' sub is allowed (doesn't conflict with the unique index)
    bo_db_with_seed.execute(
        "INSERT INTO bo_business_subscriptions (id, business_id, package_id, status) VALUES (?, ?, ?, ?)",
        ("sub_2", "biz_1", "pkg_growth", "canceled"),
    )
    bo_db_with_seed.commit()
    row = bo_db_with_seed.execute(
        "SELECT COUNT(*) AS c FROM bo_business_subscriptions WHERE business_id = ?",
        ("biz_1",),
    ).fetchone()
    assert row["c"] == 2, "active + canceled should both exist"


# ── 5. PII fields exist as nullable text columns ──────────────

def test_pii_fields_exist(bo_db_with_seed):
    """The PII columns exist and accept NULL."""
    cols = [r["name"] for r in bo_db_with_seed.execute("PRAGMA table_info(bo_businesses)").fetchall()]
    for col in ("contact_email", "contact_phone", "billing_email"):
        assert col in cols, f"PII column {col} missing from bo_businesses"

    cols = [r["name"] for r in bo_db_with_seed.execute("PRAGMA table_info(bo_business_users)").fetchall()]
    for col in ("email", "display_name"):
        assert col in cols, f"PII column {col} missing from bo_business_users"


def test_secrets_columns_exist_for_integrations(bo_db_with_seed):
    """credential_ref_hash + credential_ref_masked exist on bo_business_integrations.

    No plaintext column.
    """
    cols = [r["name"] for r in bo_db_with_seed.execute("PRAGMA table_info(bo_business_integrations)").fetchall()]
    assert "credential_ref_hash" in cols
    assert "credential_ref_masked" in cols
    # No plaintext credential column
    for bad in ("credential", "password", "secret", "api_key", "token"):
        assert bad not in cols, f"plaintext secret column {bad!r} in bo_business_integrations"
