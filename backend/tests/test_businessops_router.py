"""
Tests for BusinessOps read-only router (Phase 1, 2026-06-09).

Source of truth: REPORT-businessops-tenantops-design.md §9 Phase 1.

Pattern (matches test_vendorops_core.py):
  - Use the live FastAPI app via TestClient
  - monkeypatch.setattr(database, "DB_PATH", tmp_path / "biz.db")
  - Per-test fresh DB

These tests cover:
  - All GET endpoints return sane responses
  - No POST/PUT/PATCH/DELETE exists on the router (route inventory)
  - The entitlement matrix endpoint returns 6 packages
  - Filters work (status, business_type, provider, etc.)
  - 404 for missing ids
  - OpenAPI shows the router surface
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


# ── fixtures ───────────────────────────────────────────────────

@pytest.fixture
def client(monkeypatch, tmp_path):
    """Fresh DB per test, mounted via TestClient(app)."""
    from app.db import database
    db_path = tmp_path / "biz_router_test.db"
    monkeypatch.setattr(database, "DB_PATH", str(db_path))
    from app.main import app
    return TestClient(app)


# ── 1. /info and /health ───────────────────────────────────────

def test_info_endpoint(client):
    r = client.get("/api/v1/businessops/info")
    assert r.status_code == 200
    body = r.json()
    assert body["product"] == "BusinessOps"
    assert body["route_prefix"] == "/api/v1/businessops"
    assert body["db_prefix"] == "bo_"
    assert body["phase"] == 1


def test_health_endpoint_after_init(client):
    """After the first request, the schema is initialized and seeded."""
    client.get("/api/v1/businessops/info")  # triggers init
    r = client.get("/api/v1/businessops/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["tables"]["bo_packages"] == 6
    assert body["tables"]["bo_module_entitlements"] == 222
    # All other tables start empty
    for tbl in ("bo_businesses", "bo_business_subscriptions", "bo_provisioning_checklists",
                "bo_business_users", "bo_business_integrations", "bo_business_audit_events"):
        assert body["tables"][tbl] == 0, f"{tbl} should be 0 after init"


# ── 2. /packages ───────────────────────────────────────────────

def test_list_packages(client):
    r = client.get("/api/v1/businessops/packages")
    assert r.status_code == 200
    body = r.json()
    ids = [p["id"] for p in body["items"]]
    # The router orders by monthly_price_usd ASC, id ASC.
    # All 6 prices: pkg_founder(0), pkg_custom(0), pkg_starter(29), pkg_apostille_only(49),
    # pkg_growth(79), pkg_empire(199).
    assert ids == [
        "pkg_custom",      # price 0, id 'pkg_custom'
        "pkg_founder",     # price 0, id 'pkg_founder'
        "pkg_starter",     # price 29
        "pkg_apostille_only",  # price 49
        "pkg_growth",      # price 79
        "pkg_empire",      # price 199
    ]


def test_list_packages_filter_internal(client):
    r = client.get("/api/v1/businessops/packages?is_internal=true")
    assert r.status_code == 200
    body = r.json()
    # pkg_founder has is_internal=TRUE; is_internal is returned as 1 (SQLite int)
    assert [p["id"] for p in body["items"]] == ["pkg_founder"]


def test_get_package_404(client):
    r = client.get("/api/v1/businessops/packages/pkg_does_not_exist")
    assert r.status_code == 404


def test_get_package_ok(client):
    r = client.get("/api/v1/businessops/packages/pkg_starter")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "pkg_starter"
    assert body["monthly_price_usd"] == 29
    # is_internal is stored as INTEGER (0 or 1) in SQLite; the router returns it raw
    assert body["is_internal"] in (0, False)


def test_get_package_founder_is_internal(client):
    r = client.get("/api/v1/businessops/packages/pkg_founder")
    assert r.status_code == 200
    body = r.json()
    assert body["is_internal"] in (1, True)


# ── 3. /entitlements ───────────────────────────────────────────

def test_list_entitlements(client):
    r = client.get("/api/v1/businessops/entitlements")
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 222


def test_list_entitlements_filter_module(client):
    r = client.get("/api/v1/businessops/entitlements?module_id=apostapp")
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 6  # 1 per package
    by_pkg = {it["package_id"]: it["access_level"] for it in body["items"]}
    assert by_pkg["pkg_apostille_only"] == "founder_only"
    assert by_pkg["pkg_empire"] == "founder_only"
    assert by_pkg["pkg_founder"] == "full"
    assert by_pkg["pkg_starter"] == "none"
    assert by_pkg["pkg_growth"] == "none"


def test_list_entitlements_filter_package(client):
    r = client.get("/api/v1/businessops/entitlements?package_id=pkg_empire")
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 37  # 37 modules
    # ApostApp should be founder_only with requires_approval
    apostapp = [it for it in body["items"] if it["module_id"] == "apostapp"][0]
    assert apostapp["access_level"] == "founder_only"
    # requires_approval is stored as INTEGER (0/1) in SQLite; the router returns it raw
    assert apostapp["requires_approval"] in (1, True)


def test_entitlement_matrix(client):
    r = client.get("/api/v1/businessops/entitlements/matrix")
    assert r.status_code == 200
    body = r.json()
    matrix = body["matrix"]
    assert set(matrix.keys()) == {"pkg_starter", "pkg_growth", "pkg_empire", "pkg_custom", "pkg_apostille_only", "pkg_founder"}
    # Each package has 37 modules
    for pkg, mods in matrix.items():
        assert len(mods) == 37, f"{pkg} should have 37 modules"
    # Spot check
    assert matrix["pkg_empire"]["apostapp"]["access_level"] == "founder_only"
    assert matrix["pkg_starter"]["apostapp"]["access_level"] == "none"
    assert matrix["pkg_founder"]["apostapp"]["access_level"] == "full"


# ── 4. Empty list endpoints ───────────────────────────────────

def test_list_businesses_empty(client):
    r = client.get("/api/v1/businessops/businesses")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0
    assert body["items"] == []


def test_list_subscriptions_empty(client):
    r = client.get("/api/v1/businessops/subscriptions")
    assert r.status_code == 200
    assert r.json()["items"] == []


def test_list_business_users_empty(client):
    r = client.get("/api/v1/businessops/business-users")
    assert r.status_code == 200
    assert r.json()["items"] == []


def test_list_integrations_empty(client):
    r = client.get("/api/v1/businessops/integrations")
    assert r.status_code == 200
    assert r.json()["items"] == []


def test_list_audit_events_empty(client):
    r = client.get("/api/v1/businessops/audit-events")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0
    assert body["items"] == []


def test_list_provisioning_empty(client):
    r = client.get("/api/v1/businessops/provisioning-checklists")
    assert r.status_code == 200
    assert r.json()["items"] == []


# ── 5. 404s ────────────────────────────────────────────────────

def test_get_business_404(client):
    r = client.get("/api/v1/businessops/businesses/biz_does_not_exist")
    assert r.status_code == 404


def test_get_subscription_404(client):
    r = client.get("/api/v1/businessops/subscriptions/sub_does_not_exist")
    assert r.status_code == 404


# ── 6. Router has no write methods (Phase 1 contract) ─────────

def test_router_has_no_write_methods():
    """Phase 1 contract: read-only. No PUT/PATCH/DELETE on the router.

    The one POST allowed in Phase 1 is /entitlements/check — a read-only
    check that takes a body. No other write verbs are permitted.
    """
    from app.routers.businessops import router

    # Forbidden write verbs (POST is the only verb that may exist, and only on
    # the /entitlements/check endpoint, which is a read operation that takes a body).
    forbidden = {"PUT", "PATCH", "DELETE"}

    # The only allowed POST path in Phase 1.
    # route.path is the path relative to the APIRouter (which is mounted
    # at /api/v1). The full URL is /api/v1/businessops/entitlements/check.
    allowed_post_paths = {"/businessops/entitlements/check"}

    violations = []
    for route in router.routes:
        if hasattr(route, "methods"):
            methods = set(route.methods) - {"HEAD"}
            path = getattr(route, "path", str(route))
            # POST is allowed only on /entitlements/check
            for verb in methods:
                if verb in forbidden:
                    violations.append((path, verb))
                elif verb == "POST" and path not in allowed_post_paths:
                    violations.append((path, verb))

    assert not violations, f"Phase 1 has forbidden write endpoints: {violations}"


def test_router_route_count():
    """Phase 1: 16 routes (info + health + 14 list/get/check endpoints)."""
    from app.routers.businessops import router
    routes = [r for r in router.routes if hasattr(r, "methods")]
    assert len(routes) == 16, f"expected 16 routes, got {len(routes)}"


# ── 7. Filter by status / type ─────────────────────────────────

def test_businesses_filter_by_status(client):
    r = client.get("/api/v1/businessops/businesses?status=active")
    assert r.status_code == 200
    # No businesses yet
    assert r.json()["total"] == 0


# ── 8. OpenAPI surface ─────────────────────────────────────────

def test_openapi_includes_businessops(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    spec = r.json()
    paths = spec.get("paths", {})
    bo_paths = [p for p in paths if "/businessops" in p]
    assert len(bo_paths) >= 10, f"expected >= 10 businessops paths, got {len(bo_paths)}: {bo_paths}"
