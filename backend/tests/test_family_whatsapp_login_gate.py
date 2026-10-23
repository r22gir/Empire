"""Family WhatsApp admin/chats login gate. Mocks only. No cap changes."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


LIVE_FAMILY_ROOTS = (Path("/data/amp"), Path("/data/maxine"))
ADMIN_AND_CHAT_PATHS = (
    "/api/v1/whatsapp/status",
    "/api/v1/whatsapp/setup",
    "/api/v1/whatsapp/credentials",
    "/api/v1/whatsapp/chats",
    "/api/v1/whatsapp/chats/search",
    "/api/v1/whatsapp/chats/573001112233/messages",
)


def _assert_not_live(path: Path) -> None:
    resolved = path.expanduser().resolve()
    for banned in LIVE_FAMILY_ROOTS:
        if resolved == banned or banned in resolved.parents:
            raise AssertionError(f"refusing live family data dir {resolved}")


def _family_env(monkeypatch, tmp_path, edition: str):
    _assert_not_live(tmp_path)
    monkeypatch.setenv("EMPIRE_EDITION", edition)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_DEFAULT_LOCALE", "es")
    monkeypatch.setenv("ASSISTANT_NAME", "Maxine" if edition == "maxine" else "Max-e")
    monkeypatch.setenv("AMP_JWT_SECRET", "test-secret")
    monkeypatch.setenv("AMP_OWNER_EMAIL", "owner@example.com")
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "5551234")
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "test-secret")
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "verify-me")
    monkeypatch.delenv("WHATSAPP_OWNER_NUMBERS", raising=False)
    monkeypatch.delenv("EDITION_OWNER_WHATSAPP", raising=False)
    monkeypatch.setenv("WHATSAPP_STATE_DB", str(tmp_path / "wa.db"))
    from app.edition import apply_amp_process_paths

    apply_amp_process_paths()


def _client(monkeypatch, tmp_path, edition: str):
    _family_env(monkeypatch, tmp_path, edition)
    from app.middleware.edition_gate import amp_access_middleware
    from app.routers.whatsapp import router

    app = FastAPI()
    app.middleware("http")(amp_access_middleware)
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


def _owner_cookie(client, email="owner@example.com"):
    from app.services.amp_access import SESSION_COOKIE, create_session_token

    client.cookies.set(SESSION_COOKIE, create_session_token(email))


def test_chats_and_admin_are_not_allowlist_exempt():
    from app.edition import _ALLOWLIST_EXEMPT, access_exempt

    exempt = {(method, path) for method, path in _ALLOWLIST_EXEMPT}
    assert ("GET", "/api/v1/whatsapp/chats") not in exempt
    assert ("GET", "/api/v1/whatsapp/chats/search") not in exempt
    assert ("GET", "/api/v1/whatsapp/status") not in exempt
    assert ("GET", "/api/v1/whatsapp/setup") not in exempt
    assert ("GET", "/api/v1/whatsapp/credentials") not in exempt
    assert ("GET", "/api/v1/whatsapp/webhook") in exempt
    assert ("POST", "/api/v1/whatsapp/webhook") in exempt
    assert ("GET", "/api/v1/edition") not in exempt
    assert access_exempt("GET", "/api/v1/whatsapp/webhook") is True
    assert access_exempt("POST", "/api/v1/whatsapp/webhook") is True
    assert access_exempt("GET", "/api/v1/whatsapp/chats") is False
    assert access_exempt("GET", "/api/v1/whatsapp/status") is False
    assert access_exempt("GET", "/api/v1/edition") is False
    assert access_exempt("GET", "/api/v1/public/ventas/projects") is False


def test_anonymous_whatsapp_admin_and_chats_are_denied_on_amp_and_maxine(monkeypatch, tmp_path):
    for edition in ("amp", "maxine"):
        root = tmp_path / edition
        root.mkdir()
        client = _client(monkeypatch, root, edition)
        for path in ADMIN_AND_CHAT_PATHS:
            denied = client.get(path, params={"q": "hola"} if path.endswith("/search") else None)
            assert denied.status_code in {401, 403}, (edition, path, denied.status_code, denied.text)
            body = denied.json()
            blob = str(body.get("detail") or "") + str(body.get("code") or "")
            assert body.get("code") == "sin_acceso" or "Sin acceso" in blob


def test_logged_in_owner_can_read_admin_and_chats_on_amp_and_maxine(monkeypatch, tmp_path):
    from app.services.whatsapp_store import record_message

    for edition in ("amp", "maxine"):
        root = tmp_path / f"{edition}-ok"
        root.mkdir()
        client = _client(monkeypatch, root, edition)
        record_message("573001112233", direction="in", kind="text", body="hola dueño")
        _owner_cookie(client)
        status = client.get("/api/v1/whatsapp/status")
        assert status.status_code == 200, (edition, status.status_code, status.text)
        setup = client.get("/api/v1/whatsapp/setup")
        assert setup.status_code == 200
        assert setup.json()["secrets_in_page"] is False
        listed = client.get("/api/v1/whatsapp/chats")
        assert listed.status_code == 200, (edition, listed.status_code, listed.text)
        assert listed.json()["readonly"] is True
        thread = client.get("/api/v1/whatsapp/chats/573001112233/messages")
        assert thread.status_code == 200
        assert thread.json()["messages"][0]["body"] == "hola dueño"
        search = client.get("/api/v1/whatsapp/chats/search", params={"q": "dueño"})
        assert search.status_code == 200
        assert search.json()["matches"]


def test_member_session_cannot_read_family_whatsapp_admin_or_chats(monkeypatch, tmp_path):
    from app.services.amp_allowlist import add_entry

    root = tmp_path / "amp-member"
    root.mkdir()
    client = _client(monkeypatch, root, "amp")
    add_entry(email="member@example.com", role="member")
    _owner_cookie(client, "member@example.com")
    for path in ADMIN_AND_CHAT_PATHS:
        denied = client.get(path)
        assert denied.status_code == 403, (path, denied.status_code, denied.text)


def test_whatsapp_webhook_stays_reachable_without_login(monkeypatch, tmp_path):
    root = tmp_path / "amp-hook"
    root.mkdir()
    client = _client(monkeypatch, root, "amp")

    bad = client.get(
        "/api/v1/whatsapp/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "nope", "hub.challenge": "abc"},
    )
    assert bad.status_code == 403
    assert bad.json().get("code") != "sin_acceso"

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
    body = posted.json()
    assert body["reason"] == "Firma inválida"
    assert body.get("code") != "sin_acceso"
    assert "sha256=dead" not in posted.text


def test_login_gate_does_not_change_owner_whatsapp_allowlist(monkeypatch, tmp_path):
    """EDITION_OWNER_WHATSAPP / env owner numbers stay the allowlist source."""
    from app.services.whatsapp_cloud import owner_numbers

    root = tmp_path / "amp-allow"
    root.mkdir()
    _family_env(monkeypatch, root, "amp")
    monkeypatch.setenv("EDITION_OWNER_WHATSAPP", "573001112233")
    monkeypatch.setenv("WHATSAPP_OWNER_NUMBERS", "573001112233")
    assert owner_numbers() == ["573001112233"]
    send_me = Path(__file__).resolve().parents[1] / "app" / "services" / "max" / "send_me_link.py"
    text = send_me.read_text(encoding="utf-8")
    assert 'os.getenv("EDITION_OWNER_WHATSAPP")' in text
    assert "Never Studio send_me_this_link" in text
    assert "WHATSAPP_OWNER_NUMBERS" in text
    monkeypatch.delenv("EDITION_OWNER_WHATSAPP", raising=False)
    assert owner_numbers() == ["573001112233"]


def test_family_whatsapp_pages_send_session_cookie():
    root = Path(__file__).resolve().parents[2]
    setup = (root / "empire-command-center" / "app" / "amp" / "whatsapp" / "page.tsx").read_text(encoding="utf-8")
    chats = (root / "empire-command-center" / "app" / "amp" / "whatsapp" / "chats" / "page.tsx").read_text(encoding="utf-8")
    status = (root / "empire-command-center" / "app" / "components" / "voice" / "WhatsAppStatus.tsx").read_text(encoding="utf-8")
    router = (root / "backend" / "app" / "routers" / "whatsapp.py").read_text(encoding="utf-8")
    assert "credentials: 'include'" in setup
    assert "FAMILY_LOGIN_PATH" in setup
    assert "credentials: 'include'" in chats
    assert "FAMILY_LOGIN_PATH" in chats
    assert "credentials: 'include'" in status
    assert "require_family_whatsapp_login" in router
    assert "def whatsapp_verify" in router
    verify_block = router.split("def whatsapp_verify")[1].split("def whatsapp_inbound")[0]
    inbound_block = router.split("def whatsapp_inbound")[1].split("def whatsapp_list_chats")[0]
    assert "require_family_whatsapp_login" not in verify_block
    assert "require_family_whatsapp_login" not in inbound_block
