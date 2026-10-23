"""Family /api/v1 owner-session gate. Audit + HTTP. No live data."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


LIVE_FAMILY_ROOTS = (Path("/data/amp"), Path("/data/maxine"))
ROOT = Path(__file__).resolve().parents[2]
MAIN = (ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")

# Every load_router / include_router that mounts under /api/v1.
API_V1_MOUNTS = (
    "app.routers.max",
    "app.api.v1.files",
    "app.api.v1.quote_requests",
    "app.api.v1.chats",
    "app.api.v1.license",
    "app.routers.shipping",
    "app.routers.listings",
    "app.routers.preorders",
    "app.routers.relistapp",
    "app.routers.archiveforge",
    "app.routers.relist",
    "app.routers.vendorops",
    "app.routers.businessops",
    "app.routers.presentations",
    "app.routers.marketforge_connect",
    "app.routers.supportforge_tickets",
    "app.routers.supportforge_customers",
    "app.routers.supportforge_kb",
    "app.routers.supportforge_ai",
    "app.routers.crypto_payments",
    "app.routers.economic",
    "app.routers.chat_backup",
    "app.routers.memory",
    "app.routers.portal_button_compat",
    "app.routers.quotes",
    "app.routers.quotes_v2",
    "app.routers.pricing",
    "app.routers.channels",
    "app.routers.work_orders",
    "app.routers.lifecycle",
    "app.routers.finance",
    "app.routers.financial",
    "app.routers.inbox",
    "app.routers.client_portal",
    "app.routers.craftforge",
    "app.routers.socialforge",
    "app.routers.social_setup",
    "app.routers.avatar",
    "app.routers.simli_avatar",
    "app.routers.recovery",
    "app.routers.dev",
    "app.routers.qr",
    "app.routers.costs",
    "app.routers.accuracy",
    "app.routers.maintenance",
    "app.routers.payments",
    "app.routers.crypto_checkout",
    "app.routers.emails",
    "app.routers.customer_mgmt",
    "app.routers.inventory",
    "app.routers.jobs_unified",
    "app.routers.journey",
    "app.routers.intake_auth",
    "app.routers.amp",
    "app.routers.edition",
    "app.routers.cursor_requests",
    "app.routers.family_help",
    "app.routers.minimax_meter",
    "app.routers.llcfactory",
    "app.routers.apostapp",
    "app.routers.apostapp_public",
    "app.routers.construction",
    "app.routers.public_sales",
    "app.routers.voice_documents",
    "app.routers.instance_files",
    "app.routers.whatsapp",
    "app.routers.storefront",
    "app.routers.notes_extraction",
    "app.routers.pattern_templates",
    "app.routers.custom_shapes",
    "app.routers.drawings",
    "app.routers.fabrics",
    "app.routers.photos",
    "app.routers.analysis_sessions",
    "app.routers.orchestration",
    "app.routers.docker_manager",
    "app.routers.system_monitor",
    "app.routers.ollama_manager",
    "app.routers.recovery_control",
    "app.routers.notifications",
    "app.routers.desks",
    "app.routers.tasks",
    "app.routers.contacts",
    "app.routers.leadforge",
    "app.routers.growth",
    "app.routers.home_center",
    "app.routers.workroom_capture",
    "app.routers.onboarding",
)

# Paths that used to answer without an owner session on family.
PREVIOUSLY_OPEN = (
    "/api/v1/edition",
    "/api/v1/public/ventas/projects",
    "/api/v1/public/ventas/projects/demo/sitemap",
)
SAMPLE_ALREADY_GATED = (
    "/api/v1/whatsapp/status",
    "/api/v1/whatsapp/chats",
    "/api/v1/amp/content",
    "/api/v1/businesses",
    "/api/v1/whoami",
    "/api/v1/family-help/inbox",
)
KEEP_OPEN = (
    ("GET", "/health"),
    ("POST", "/api/v1/amp/auth/request"),
    ("POST", "/api/v1/amp/auth/verify"),
    ("GET", "/api/v1/amp/auth/magic"),
    ("POST", "/api/v1/amp/auth/logout"),
    ("GET", "/api/v1/whatsapp/webhook"),
    ("POST", "/api/v1/whatsapp/webhook"),
)


def _assert_not_live(path: Path) -> None:
    resolved = path.expanduser().resolve()
    for banned in LIVE_FAMILY_ROOTS:
        if resolved == banned or banned in resolved.parents:
            raise AssertionError(f"refusing live family data dir {resolved}")


def _family_env(monkeypatch, tmp_path, edition: str = "amp"):
    _assert_not_live(tmp_path)
    monkeypatch.setenv("EMPIRE_EDITION", edition)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_DEFAULT_LOCALE", "es")
    monkeypatch.setenv("ASSISTANT_NAME", "Maxine" if edition == "maxine" else "Max-e")
    monkeypatch.setenv("AMP_JWT_SECRET", "test-secret")
    monkeypatch.setenv("AMP_OWNER_EMAIL", "owner@example.com")
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "5551234")
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "test-app-secret")
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "verify-me")
    from app.edition import apply_amp_process_paths

    apply_amp_process_paths()


def _client(monkeypatch, tmp_path, edition: str = "amp"):
    _family_env(monkeypatch, tmp_path, edition)
    from app.middleware.edition_gate import amp_access_middleware
    from app.routers.edition import router as edition_router
    from app.routers.public_sales import router as sales_router
    from app.routers.whatsapp import router as whatsapp_router
    from app.routers.amp import router as amp_router

    app = FastAPI()
    app.middleware("http")(amp_access_middleware)

    @app.get("/health")
    def health():
        return {"status": "healthy", "service": "empirebox-backend"}

    @app.get("/api/v1/whoami")
    def whoami():
        return {"ok": True}

    app.include_router(edition_router, prefix="/api/v1")
    app.include_router(sales_router, prefix="/api/v1")
    app.include_router(whatsapp_router, prefix="/api/v1")
    app.include_router(amp_router, prefix="/api/v1/amp")
    return TestClient(app)


def _owner_cookie(client, email="owner@example.com"):
    from app.services.amp_access import SESSION_COOKIE, create_session_token

    client.cookies.set(SESSION_COOKIE, create_session_token(email))


def test_main_mounts_every_api_v1_router_under_the_family_middleware():
    """Audit: these modules are mounted at /api/v1 in main.py."""
    assert 'app.middleware("http")(amp_access_middleware)' in MAIN
    assert '@app.get("/health")' in MAIN
    assert '@app.post("/api/v1/voice/transcribe")' in MAIN
    for module in API_V1_MOUNTS:
        assert module in MAIN, f"missing mount {module}"
        assert (
            f'load_router("{module}"' in MAIN
            or f"from {module}" in MAIN
            or module.split(".")[-1] in MAIN
        )


def test_family_exempt_list_is_only_health_login_and_webhook():
    from app.edition import _ALLOWLIST_EXEMPT, access_exempt, public_sales_exempt

    api_exempt = {(m, p) for m, p in _ALLOWLIST_EXEMPT if str(p).startswith("/api/v1/")}
    assert api_exempt == set(KEEP_OPEN) - {("GET", "/health")}
    for method, path in KEEP_OPEN:
        assert access_exempt(method, path) is True, (method, path)
    for path in PREVIOUSLY_OPEN + SAMPLE_ALREADY_GATED:
        assert access_exempt("GET", path) is False, path
        assert access_exempt("POST", path) is False, path
    # Helper still describes Maxine ventas, but family access no longer uses it.
    assert public_sales_exempt("GET", "/api/v1/public/ventas/projects") is True
    assert access_exempt("GET", "/api/v1/public/ventas/projects") is False
    assert access_exempt("POST", "/api/v1/public/ventas/projects/demo/lead") is False
    assert ("GET", "/api/v1/edition") not in _ALLOWLIST_EXEMPT


def test_anonymous_family_api_v1_is_denied_including_previous_holes(monkeypatch, tmp_path):
    for edition in ("amp", "maxine"):
        root = tmp_path / edition
        root.mkdir()
        client = _client(monkeypatch, root, edition)
        for path in PREVIOUSLY_OPEN + SAMPLE_ALREADY_GATED:
            denied = client.get(path)
            assert denied.status_code in {401, 403}, (edition, path, denied.status_code, denied.text)
            body = denied.json()
            blob = str(body.get("detail") or "") + str(body.get("code") or "")
            assert body.get("code") == "sin_acceso" or "Sin acceso" in blob
        health = client.get("/health")
        assert health.status_code == 200
        logout = client.post("/api/v1/amp/auth/logout")
        assert logout.status_code == 200


def test_owner_session_opens_previous_holes_and_samples(monkeypatch, tmp_path):
    root = tmp_path / "amp-owner"
    root.mkdir()
    client = _client(monkeypatch, root, "amp")
    _owner_cookie(client)
    edition = client.get("/api/v1/edition")
    assert edition.status_code == 200, edition.text
    assert edition.json()["edition"] == "amp"
    status = client.get("/api/v1/whatsapp/status")
    assert status.status_code == 200
    whoami = client.get("/api/v1/whoami")
    assert whoami.status_code == 200
    businesses = client.get("/api/v1/businesses")
    assert businesses.status_code == 200
    # AMP edition: public ventas router itself 404s (Maxine-only).
    ventas = client.get("/api/v1/public/ventas/projects")
    assert ventas.status_code in {200, 404}
    assert ventas.json().get("code") != "sin_acceso"


def test_founder_edition_still_serves_edition_without_a_family_cookie(monkeypatch, tmp_path):
    monkeypatch.delenv("EMPIRE_EDITION", raising=False)
    monkeypatch.delenv("EMPIRE_DATA_DIR", raising=False)
    monkeypatch.setenv("EMPIRE_EDITION", "workroom")
    from app.edition import is_family_edition
    from app.middleware.edition_gate import amp_access_middleware
    from app.routers.edition import router as edition_router

    assert is_family_edition() is False
    app = FastAPI()
    app.middleware("http")(amp_access_middleware)
    app.include_router(edition_router, prefix="/api/v1")
    client = TestClient(app)
    open_edition = client.get("/api/v1/edition")
    assert open_edition.status_code == 200
    assert open_edition.json()["edition"] in {"workroom", "main"} or "assistant" in open_edition.json()


def test_webhook_and_login_request_still_work_without_a_cookie(monkeypatch, tmp_path):
    root = tmp_path / "amp-open"
    root.mkdir()
    client = _client(monkeypatch, root, "amp")
    ok = client.get(
        "/api/v1/whatsapp/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "verify-me", "hub.challenge": "challenge-123"},
    )
    assert ok.status_code == 200
    assert ok.text == "challenge-123"
    posted = client.post(
        "/api/v1/whatsapp/webhook",
        content=b"{}",
        headers={"X-Hub-Signature-256": "sha256=dead"},
    )
    assert posted.status_code == 403
    assert posted.json()["reason"] == "Firma inválida"
    assert posted.json().get("code") != "sin_acceso"
    asked = client.post("/api/v1/amp/auth/request", json={"email": "owner@example.com"})
    assert asked.status_code == 200
    assert asked.json()["ok"] is True


def test_edition_owner_whatsapp_allowlist_untouched():
    text = (ROOT / "backend" / "app" / "services" / "max" / "send_me_link.py").read_text(encoding="utf-8")
    assert 'os.getenv("EDITION_OWNER_WHATSAPP")' in text
    gate = (ROOT / "backend" / "app" / "middleware" / "edition_gate.py").read_text(encoding="utf-8")
    assert "disabled_module_for_path" in gate
    assert "amp_allowlist.is_allowed" in gate
