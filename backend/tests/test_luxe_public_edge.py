"""Anonymous public Luxe hosts must not read quotes, invoices, or CRM dumps.

Localhost and Tailscale hosts are outside the gate so EmpireDell cash-path
smokes keep working.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.security.luxe_public_edge import (
    DENIAL_ERROR,
    RATE_LIMIT_ERROR,
    SENSITIVE_ANONYMOUS_PATHS,
    clear_public_edge_rate_buckets,
    is_public_luxe_path_allowed,
    normalize_host,
    public_luxe_hosts,
)

MIDDLEWARE_TS = Path(__file__).resolve().parents[2] / "empire-command-center" / "middleware.ts"

# raise_server_exceptions=False: a route that 500s on a missing local table is
# still "not denied by the public edge". The denial tests check status and body.
LUXE = TestClient(app, base_url="https://luxe.empirebox.store", raise_server_exceptions=False)
TEST_LUXE = TestClient(app, base_url="https://test-luxe.empirebox.store", raise_server_exceptions=False)
LOCAL = TestClient(app, base_url="http://127.0.0.1", raise_server_exceptions=False)
TAILSCALE = TestClient(app, base_url="http://100.64.0.2", raise_server_exceptions=False)
STUDIO = TestClient(app, base_url="https://studio.empirebox.store", raise_server_exceptions=False)


def _error(response) -> str:
    try:
        body = response.json()
    except json.JSONDecodeError:
        return ""
    if isinstance(body, dict):
        return str(body.get("error") or "")
    return ""


@pytest.mark.parametrize("method,path", SENSITIVE_ANONYMOUS_PATHS)
def test_public_luxe_host_denies_sensitive_routes(method, path):
    response = LUXE.request(method, path)
    assert response.status_code == 401, f"{method} {path} -> {response.status_code}"
    assert _error(response) == DENIAL_ERROR
    assert response.headers.get("x-empire-edge") == "luxe-public-denied"
    # Denial body is a fixed sentence. It must not grow into a data dump.
    assert len(response.content) < 200


@pytest.mark.parametrize("method,path", SENSITIVE_ANONYMOUS_PATHS)
def test_test_luxe_host_denies_the_same_routes(method, path):
    response = TEST_LUXE.request(method, path)
    assert response.status_code == 401
    assert _error(response) == DENIAL_ERROR


@pytest.mark.parametrize("method,path", SENSITIVE_ANONYMOUS_PATHS)
def test_localhost_cash_path_is_not_edge_denied(method, path):
    response = LOCAL.request(method, path)
    assert _error(response) != DENIAL_ERROR
    assert response.headers.get("x-empire-edge") != "luxe-public-denied"


def test_tailscale_host_is_not_edge_denied():
    response = TAILSCALE.get("/api/v1/quotes?limit=1")
    assert _error(response) != DENIAL_ERROR


def test_studio_host_is_not_edge_denied():
    """studio is Access-protected at Cloudflare. This process must still serve it."""
    response = STUDIO.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_forwarded_public_host_is_denied_even_if_host_is_local():
    response = LOCAL.get(
        "/api/v1/finance/invoices?limit=1",
        headers={"x-forwarded-host": "luxe.empirebox.store"},
    )
    assert response.status_code == 401
    assert _error(response) == DENIAL_ERROR


def test_public_intake_login_and_signup_stay_reachable():
    login = LUXE.post("/api/v1/intake/login", json={})
    signup = LUXE.post("/api/v1/intake/signup", json={})
    assert _error(login) != DENIAL_ERROR
    assert _error(signup) != DENIAL_ERROR
    assert login.status_code != 401 or _error(login) != DENIAL_ERROR


def test_public_intake_project_list_uses_route_auth_not_a_dump():
    response = LUXE.get("/api/v1/intake/projects")
    assert response.status_code == 401
    assert _error(response) != DENIAL_ERROR
    assert response.json()["detail"] == "Not authenticated"


def test_password_reset_and_admin_are_closed_on_the_public_edge():
    reset = LUXE.post(
        "/api/v1/intake/reset-password",
        json={"email": "person@example.com", "new_password": "whatever"},
    )
    admin = LUXE.get("/api/v1/intake/admin/projects")
    assert reset.status_code == 401 and _error(reset) == DENIAL_ERROR
    assert admin.status_code == 401 and _error(admin) == DENIAL_ERROR


def test_fabric_catalog_closed_but_intake_project_fabrics_open():
    catalog = LUXE.get("/api/v1/fabrics")
    rows = LUXE.get("/api/v1/fabrics/intake-project/example/fabrics")
    match = LUXE.put("/api/v1/fabrics/intake-project/example/fabrics/1/match")
    assert _error(catalog) == DENIAL_ERROR
    assert _error(rows) != DENIAL_ERROR
    assert _error(match) == DENIAL_ERROR


def test_health_on_localhost_still_ok():
    response = LOCAL.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "empirebox-backend"


def test_public_edge_rate_limits_capture(monkeypatch):
    monkeypatch.setenv("LUXE_PUBLIC_EDGE_RATE_PER_MINUTE", "2")
    clear_public_edge_rate_buckets()
    first = LUXE.post("/api/v1/intake/login", json={})
    second = LUXE.post("/api/v1/intake/login", json={})
    third = LUXE.post("/api/v1/intake/login", json={})
    assert _error(first) != RATE_LIMIT_ERROR
    assert _error(second) != RATE_LIMIT_ERROR
    assert third.status_code == 429
    assert _error(third) == RATE_LIMIT_ERROR
    clear_public_edge_rate_buckets()


def test_defaults_survive_empty_extra_hosts(monkeypatch):
    monkeypatch.setenv("LUXE_PUBLIC_EDGE_HOSTS", "")
    assert "luxe.empirebox.store" in public_luxe_hosts()
    assert "test-luxe.empirebox.store" in public_luxe_hosts()


def test_extra_public_host_can_be_added(monkeypatch):
    monkeypatch.setenv("LUXE_PUBLIC_EDGE_HOSTS", "preview-luxe.empirebox.store")
    assert "preview-luxe.empirebox.store" in public_luxe_hosts()
    assert "luxe.empirebox.store" in public_luxe_hosts()


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Luxe.EmpireBox.Store:443", "luxe.empirebox.store"),
        ("luxe.empirebox.store.", "luxe.empirebox.store"),
        ("127.0.0.1:8000", "127.0.0.1"),
        ("[100::1]:8000", "[100::1]"),
    ],
)
def test_normalize_host(raw, expected):
    assert normalize_host(raw) == expected


def test_allowlist_rejects_traversal_and_quote_reads():
    assert not is_public_luxe_path_allowed("GET", "/api/v1/intake/projects/../../quotes")
    assert not is_public_luxe_path_allowed("GET", "/api/v1/quotes")
    assert is_public_luxe_path_allowed("POST", "/api/v1/intake/signup")
    assert not is_public_luxe_path_allowed("GET", "/api/v1/intake/signup")
    assert is_public_luxe_path_allowed("GET", "/api/v1/photos/serve/intake/abc/swatch.jpg")
    assert not is_public_luxe_path_allowed("GET", "/api/v1/photos/serve/quote/abc/file.jpg")


def test_next_middleware_mentions_the_same_gate():
    text = MIDDLEWARE_TS.read_text()
    for snippet in (
        "luxe_public_edge_denied",
        "luxe.empirebox.store",
        "test-luxe.empirebox.store",
        "/api/v1/intake/reset-password",
        "/api/v1/intake/admin",
        "/api/v1/intake/signup",
        "/api/v1/fabrics/intake-project/",
        "/api/v1/photos/upload",
        "/api/v1/photos/serve/intake/",
    ):
        assert snippet in text, snippet
