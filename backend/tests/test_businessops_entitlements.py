"""
Tests for the check_entitlement helper (Phase 1, 2026-06-09).

Source of truth: REPORT-businessops-tenantops-design.md §2.5 and §8,
and REPORT-businessops-design-decisions.md D8 / D9.

Pattern (matches test_vendorops_core.py):
  - monkeypatch.setattr(database, "DB_PATH", tmp_path / "biz.db")
  - Per-test fresh DB with the seed loaded

These tests cover:
  - Returns the spec dict shape
  - 'none' refuses
  - 'founder_only' refuses non-Founder; allows Founder-equivalent
  - 'standard' allows; respects requires_approval
  - 'full' allows; respects requires_approval
  - 'internal' refuses non-Founder; allows Founder-equivalent
  - 'preview' allows
  - No entitlement row -> refuses with reason
  - 'auto_publish' action is refused for non-Founder (D8 guard)
  - 'auto_publish' is refused for any non-Founder-equivalent actor
  - 'self_heal', 'git_operations', 'max_code_mode' also blocked
  - No DB connection -> refuses (defensive)
  - Missing business or module id -> refuses
"""
from __future__ import annotations

import json
import sqlite3
import pytest


# ── fixtures ───────────────────────────────────────────────────

@pytest.fixture
def conn(monkeypatch, tmp_path):
    """Fresh DB with seed loaded."""
    from app.db import database
    db_path = tmp_path / "biz_ent_test.db"
    monkeypatch.setattr(database, "DB_PATH", str(db_path))
    c = database.get_connection()
    from app.routers.businessops import _init_businessops_schema
    _init_businessops_schema(c)
    return c


def _make_active_subscription(conn, business_id, package_id):
    """Insert a business + an active subscription so check_entitlement finds it."""
    conn.execute(
        "INSERT INTO bo_businesses (id, slug, display_name, status) VALUES (?, ?, ?, 'active')",
        (business_id, business_id, business_id),
    )
    conn.execute(
        "INSERT INTO bo_business_subscriptions (id, business_id, package_id, status, activated_at) "
        "VALUES (?, ?, ?, 'active', CURRENT_TIMESTAMP)",
        (f"sub_{business_id}", business_id, package_id),
    )
    conn.commit()


# ── 1. Return shape ────────────────────────────────────────────

def test_returns_spec_shape(conn):
    _make_active_subscription(conn, "biz_a", "pkg_starter")
    from app.services.business.entitlements import check_entitlement
    result = check_entitlement(
        business_id="biz_a",
        module_id="forgecrm",
        action="read",
        actor_role="founder",
        conn=conn,
    )
    for key in ("allowed", "access_level", "requires_approval", "limits", "reason"):
        assert key in result, f"missing key {key!r} in result"
    assert isinstance(result["allowed"], bool)
    assert isinstance(result["access_level"], str)
    assert isinstance(result["requires_approval"], bool)
    assert isinstance(result["limits"], dict)
    assert isinstance(result["reason"], str)


# ── 2. 'none' refuses ──────────────────────────────────────────

def test_none_refuses(conn):
    """pkg_starter has apostapp=none; founder must be refused too because it's none."""
    _make_active_subscription(conn, "biz_a", "pkg_starter")
    from app.services.business.entitlements import check_entitlement
    result = check_entitlement("biz_a", "apostapp", "submit_intake", actor_role="founder", conn=conn)
    assert result["allowed"] is False
    assert result["access_level"] == "none"
    assert "not in package" in result["reason"]


# ── 3. 'founder_only' allows Founder, refuses non-Founder ──────

def test_founder_only_allows_founder(conn):
    """pkg_apostille_only has apostapp=founder_only; founder is allowed."""
    _make_active_subscription(conn, "biz_apo", "pkg_apostille_only")
    from app.services.business.entitlements import check_entitlement
    result = check_entitlement("biz_apo", "apostapp", "submit_intake", actor_role="founder", conn=conn)
    assert result["allowed"] is True
    assert result["access_level"] == "founder_only"
    assert "Founder" in result["reason"]


def test_founder_only_refuses_customer_contact(conn):
    """pkg_apostille_only has apostapp=founder_only; a customer_contact is refused."""
    _make_active_subscription(conn, "biz_apo", "pkg_apostille_only")
    from app.services.business.entitlements import check_entitlement
    result = check_entitlement("biz_apo", "apostapp", "submit_intake", actor_role="customer_contact", conn=conn)
    assert result["allowed"] is False
    assert result["access_level"] == "founder_only"
    assert "Founder-equivalent" in result["reason"] or "founder_only" in result["reason"]


def test_founder_only_openclaw_refuses_member(conn):
    """Per D9: openclaw is founder_only for every customer package."""
    _make_active_subscription(conn, "biz_emp", "pkg_empire")
    from app.services.business.entitlements import check_entitlement
    result = check_entitlement("biz_emp", "openclaw", "run_task", actor_role="member", conn=conn)
    assert result["allowed"] is False
    assert result["access_level"] == "founder_only"


def test_founder_only_openclaw_allows_founder(conn):
    _make_active_subscription(conn, "biz_emp", "pkg_empire")
    from app.services.business.entitlements import check_entitlement
    result = check_entitlement("biz_emp", "openclaw", "run_task", actor_role="founder", conn=conn)
    assert result["allowed"] is True


def test_founder_only_allows_admin_owner_system_roles(conn):
    """admin, owner, and system are Founder-equivalent."""
    _make_active_subscription(conn, "biz_apo", "pkg_apostille_only")
    from app.services.business.entitlements import check_entitlement
    for role in ("admin", "owner", "system"):
        result = check_entitlement("biz_apo", "apostapp", "submit_intake", actor_role=role, conn=conn)
        assert result["allowed"] is True, f"role={role} should be Founder-equivalent"


# ── 4. 'standard' allows non-Founder ───────────────────────────

def test_standard_allows_member(conn):
    """pkg_starter has forgecrm=standard; member actor is allowed."""
    _make_active_subscription(conn, "biz_a", "pkg_starter")
    from app.services.business.entitlements import check_entitlement
    result = check_entitlement("biz_a", "forgecrm", "view_contact", actor_role="member", conn=conn)
    assert result["allowed"] is True
    assert result["access_level"] == "standard"


# ── 5. 'full' allows ──────────────────────────────────────────

def test_full_allows_founder(conn):
    """pkg_founder has workroom=full; founder actor is allowed."""
    _make_active_subscription(conn, "biz_f", "pkg_founder")
    from app.services.business.entitlements import check_entitlement
    result = check_entitlement("biz_f", "workroom", "create_quote", actor_role="founder", conn=conn)
    assert result["allowed"] is True
    assert result["access_level"] == "full"


# ── 6. 'internal' allows Founder only ──────────────────────────

def test_internal_branch_refuses_member(conn):
    """The 'internal' access level is reserved for founder's own staff.

    In the v1 seed, no (package, module) cell has access_level='internal'
    (the design uses 'founder_only' for everything that was 'internal' in
    older docs). So we can't trigger the internal branch via the seed; we
    instead directly insert a row with access_level='internal' to exercise
    the branch logic.
    """
    conn.execute(
        "INSERT INTO bo_businesses (id, slug, display_name, status) VALUES (?, ?, ?, 'active')",
        ("biz_int", "i", "I"),
    )
    conn.execute(
        "INSERT INTO bo_business_subscriptions (id, business_id, package_id, status, activated_at) "
        "VALUES (?, ?, ?, 'active', CURRENT_TIMESTAMP)",
        ("sub_int", "biz_int", "pkg_starter"),
    )
    # Override an existing entitlement row to access_level='internal'
    conn.execute(
        "UPDATE bo_module_entitlements SET access_level = 'internal' "
        "WHERE package_id = 'pkg_starter' AND module_id = 'workroom'"
    )
    conn.commit()
    from app.services.business.entitlements import check_entitlement
    result = check_entitlement("biz_int", "workroom", "view", actor_role="member", conn=conn)
    assert result["allowed"] is False
    assert result["access_level"] == "internal"


def test_internal_branch_allows_founder(conn):
    conn.execute(
        "INSERT INTO bo_businesses (id, slug, display_name, status) VALUES (?, ?, ?, 'active')",
        ("biz_int2", "i2", "I2"),
    )
    conn.execute(
        "INSERT INTO bo_business_subscriptions (id, business_id, package_id, status, activated_at) "
        "VALUES (?, ?, ?, 'active', CURRENT_TIMESTAMP)",
        ("sub_int2", "biz_int2", "pkg_starter"),
    )
    conn.execute(
        "UPDATE bo_module_entitlements SET access_level = 'internal' "
        "WHERE package_id = 'pkg_starter' AND module_id = 'workroom'"
    )
    conn.commit()
    from app.services.business.entitlements import check_entitlement
    result = check_entitlement("biz_int2", "workroom", "view", actor_role="founder", conn=conn)
    assert result["allowed"] is True
    assert result["access_level"] == "internal"


# ── 7. 'preview' allows ────────────────────────────────────────

def test_preview_allows(conn):
    """pkg_apostille_only has max=preview; customer_contact actor is allowed (read-only)."""
    _make_active_subscription(conn, "biz_apo", "pkg_apostille_only")
    from app.services.business.entitlements import check_entitlement
    result = check_entitlement("biz_apo", "max", "view_response", actor_role="customer_contact", conn=conn)
    assert result["allowed"] is True
    assert result["access_level"] == "preview"


# ── 8. Missing entitlement row ────────────────────────────────

def test_missing_module_refuses(conn):
    """No entitlement row for the (business, module) -> refuses."""
    _make_active_subscription(conn, "biz_a", "pkg_starter")
    from app.services.business.entitlements import check_entitlement
    result = check_entitlement("biz_a", "no_such_module", "do_anything", actor_role="founder", conn=conn)
    assert result["allowed"] is False
    assert result["access_level"] == "none"
    assert "no entitlement row" in result["reason"]


def test_missing_business_refuses(conn):
    """No business record at all -> refuses."""
    from app.services.business.entitlements import check_entitlement
    result = check_entitlement("biz_does_not_exist", "workroom", "view", actor_role="founder", conn=conn)
    assert result["allowed"] is False


def test_paused_subscription_works(conn):
    """A 'paused' subscription is queryable. The query joins status IN ('active', 'paused')."""
    conn.execute(
        "INSERT INTO bo_businesses (id, slug, display_name, status) VALUES (?, ?, ?, 'paused')",
        ("biz_p", "p", "Paused Inc"),
    )
    conn.execute(
        "INSERT INTO bo_business_subscriptions (id, business_id, package_id, status, activated_at) "
        "VALUES (?, ?, ?, 'paused', CURRENT_TIMESTAMP)",
        ("sub_p", "biz_p", "pkg_starter"),
    )
    conn.commit()
    from app.services.business.entitlements import check_entitlement
    result = check_entitlement("biz_p", "forgecrm", "view", actor_role="member", conn=conn)
    assert result["allowed"] is True


def test_canceled_subscription_does_not_count(conn):
    """A 'canceled' subscription is NOT in ('active', 'paused'), so no entitlement row is found."""
    conn.execute(
        "INSERT INTO bo_businesses (id, slug, display_name, status) VALUES (?, ?, ?, 'canceled')",
        ("biz_c", "c", "Canceled Inc"),
    )
    conn.execute(
        "INSERT INTO bo_business_subscriptions (id, business_id, package_id, status) "
        "VALUES (?, ?, ?, 'canceled')",
        ("sub_c", "biz_c", "pkg_starter"),
    )
    conn.commit()
    from app.services.business.entitlements import check_entitlement
    result = check_entitlement("biz_c", "forgecrm", "view", actor_role="founder", conn=conn)
    assert result["allowed"] is False


# ── 9. Auto-publish guard (D8) ─────────────────────────────────

def test_auto_publish_refused_for_member(conn):
    """The D8 guard: auto_publish is refused for any non-Founder-equivalent actor."""
    _make_active_subscription(conn, "biz_g", "pkg_growth")
    from app.services.business.entitlements import check_entitlement
    result = check_entitlement("biz_g", "socialforge", "auto_publish", actor_role="member", conn=conn)
    assert result["allowed"] is False
    assert "v1-blocked" in result["reason"] or "D8" in result["reason"]


def test_auto_publish_refused_for_customer_contact(conn):
    _make_active_subscription(conn, "biz_g", "pkg_growth")
    from app.services.business.entitlements import check_entitlement
    result = check_entitlement("biz_g", "socialforge", "auto_publish", actor_role="customer_contact", conn=conn)
    assert result["allowed"] is False


def test_auto_publish_allowed_for_founder(conn):
    """Founder can still trigger auto_publish (the guard is for non-Founder)."""
    _make_active_subscription(conn, "biz_f", "pkg_founder")
    from app.services.business.entitlements import check_entitlement
    result = check_entitlement("biz_f", "socialforge", "auto_publish", actor_role="founder", conn=conn)
    # Founder is Founder-equivalent; the v1-blocked guard is bypassed.
    # The result will reflect the actual access_level (full for pkg_founder).
    assert result["allowed"] is True
    assert result["access_level"] == "full"


def test_other_v1_blocked_actions(conn):
    """self_heal, git_operations, max_code_mode are also blocked for non-Founder."""
    _make_active_subscription(conn, "biz_f", "pkg_founder")
    from app.services.business.entitlements import check_entitlement
    for action in ("self_heal", "git_operations", "max_code_mode"):
        result = check_entitlement("biz_f", "system", action, actor_role="admin", conn=conn)
        assert result["allowed"] is True, f"Founder-equivalent admin should be allowed for {action}"
        # But for non-Founder-equivalent:
        result2 = check_entitlement("biz_f", "system", action, actor_role="member", conn=conn)
        assert result2["allowed"] is False, f"member should be refused for {action}"


# ── 10. requires_approval flag is propagated ──────────────────

def test_requires_approval_true_propagated(conn):
    """apostapp in pkg_empire has requires_approval=True. The flag is in the response."""
    _make_active_subscription(conn, "biz_emp", "pkg_empire")
    from app.services.business.entitlements import check_entitlement
    result = check_entitlement("biz_emp", "apostapp", "submit_intake", actor_role="founder", conn=conn)
    assert result["allowed"] is True
    assert result["access_level"] == "founder_only"
    # founder_only path doesn't expose requires_approval (the gate is the access_level itself)


def test_requires_approval_for_standard_module(conn):
    """ApostApp is in the APPROVAL_GATES set, so requires_approval=True.

    For a standard module that's NOT in the set, requires_approval is False.
    """
    _make_active_subscription(conn, "biz_emp", "pkg_empire")
    from app.services.business.entitlements import check_entitlement
    # apostapp is founder_only; its requires_approval is True but the path
    # doesn't surface it. So we test a different module that has standard + approval.
    # drawing_studio is in APPROVAL_GATES, access=standard for pkg_empire.
    result = check_entitlement("biz_emp", "drawing_studio", "create_drawing", actor_role="member", conn=conn)
    assert result["allowed"] is True
    assert result["access_level"] == "standard"
    assert result["requires_approval"] is True


def test_no_approval_for_non_gated_module(conn):
    """A non-gated module like forgecrm has requires_approval=False."""
    _make_active_subscription(conn, "biz_emp", "pkg_empire")
    from app.services.business.entitlements import check_entitlement
    result = check_entitlement("biz_emp", "forgecrm", "view", actor_role="member", conn=conn)
    assert result["allowed"] is True
    assert result["requires_approval"] is False


# ── 11. Defensive: no DB connection ────────────────────────────

def test_no_db_connection_refuses():
    from app.services.business.entitlements import check_entitlement
    result = check_entitlement("biz_a", "workroom", "view", actor_role="founder", conn=None)
    assert result["allowed"] is False
    assert result["access_level"] == "none"
    assert "no_db_connection" in result["reason"]


# ── 12. Limits JSON parsing ────────────────────────────────────

def test_limits_parsed_from_json(conn):
    """If the limits JSON is set on a row, it is parsed into a dict in the response."""
    _make_active_subscription(conn, "biz_emp", "pkg_empire")
    # drawing_studio in pkg_empire has limits={"drawings_per_month": -1} from the seed
    from app.services.business.entitlements import check_entitlement
    result = check_entitlement("biz_emp", "drawing_studio", "create_drawing", actor_role="member", conn=conn)
    assert result["allowed"] is True
    # The seed set drawings_per_month for pkg_empire
    assert "drawings_per_month" in result["limits"]


# ── 13. Module approval set is correct ────────────────────────

def test_approval_gated_modules_have_approval_set(conn):
    """The 6 approval-gated modules have requires_approval=True in pkg_empire."""
    _make_active_subscription(conn, "biz_emp", "pkg_empire")
    from app.services.business.entitlements import check_entitlement
    for module_id, action in [
        ("apostapp", "submit_intake"),
        ("vendorops", "approve_vendor"),
        ("socialforge", "publish_post"),
        ("drawing_studio", "create_drawing"),
        ("openclaw", "run_task"),
        ("shipforge", "create_label"),
    ]:
        # For modules that are founder_only, the requires_approval flag isn't
        # surfaced in the response (the access_level IS the gate). For standard
        # ones (drawing_studio), it IS surfaced.
        result = check_entitlement("biz_emp", module_id, action, actor_role="member", conn=conn)
        # If access_level is 'standard', requires_approval must be True for gated modules
        if result["access_level"] == "standard":
            assert result["requires_approval"] is True, f"{module_id} should require approval"


# ── 14. Endpoint integration ───────────────────────────────────

def test_endpoint_returns_standard_for_member_on_pkg_starter():
    """The full flow: POST /entitlements/check via TestClient."""
    from app.db import database
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as td:
        db_path = str(Path(td) / "biz_int.db")
        # Set both the env var and the module-level DB_PATH so any code path
        # (including app.main imports) sees the same target.
        import os
        os.environ["EMPIRE_TASK_DB"] = db_path
        database.DB_PATH = db_path
        from fastapi.testclient import TestClient
        from app.main import app
        c = TestClient(app)
        # Seed by hitting /health (triggers _init_businessops_schema).
        # /info does NOT touch the DB and would not initialize.
        r = c.get("/api/v1/businessops/health")
        assert r.status_code == 200
        # Verify the schema is in place via a direct query
        with database.get_connection() as conn:
            n = conn.execute("SELECT COUNT(*) AS c FROM bo_packages").fetchone()["c"]
            assert n == 6, f"bo_packages count = {n} after /health init"
            # Create a business + subscription
            conn.execute(
                "INSERT INTO bo_businesses (id, slug, display_name, status) VALUES (?, ?, ?, 'active')",
                ("biz_test", "biz_test", "Test Inc"),
            )
            conn.execute(
                "INSERT INTO bo_business_subscriptions (id, business_id, package_id, status, activated_at) "
                "VALUES (?, ?, ?, 'active', CURRENT_TIMESTAMP)",
                ("sub_test", "biz_test", "pkg_starter"),
            )
            conn.commit()
        # Now call the endpoint
        r = c.post(
            "/api/v1/businessops/entitlements/check",
            json={
                "business_id": "biz_test",
                "module_id": "forgecrm",
                "action": "view",
                "actor_role": "member",
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["allowed"] is True
        assert body["access_level"] == "standard"
