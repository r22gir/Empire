"""Guided WhatsApp setup + family data-dir refuse. Temp dirs, no live Meta send."""
from __future__ import annotations

import json
import stat
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _env(monkeypatch, tmp_path, edition="amp"):
    monkeypatch.setenv("EMPIRE_EDITION", edition)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("WHATSAPP_STATE_DB", str(tmp_path / "wa.db"))
    monkeypatch.setenv("AMP_OWNER_EMAIL", "owner@example.com")
    monkeypatch.setenv("AMP_JWT_SECRET", "test-secret")
    for key in (
        "WHATSAPP_ACCESS_TOKEN",
        "WHATSAPP_PHONE_NUMBER_ID",
        "WHATSAPP_APP_SECRET",
        "WHATSAPP_VERIFY_TOKEN",
        "WHATSAPP_OWNER_NUMBERS",
    ):
        monkeypatch.delenv(key, raising=False)


def _client():
    from app.middleware.edition_gate import amp_access_middleware
    from app.routers.whatsapp import router

    app = FastAPI()
    app.middleware("http")(amp_access_middleware)
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


def _cookie(client, email="owner@example.com"):
    from app.services.amp_access import SESSION_COOKIE, create_session_token

    client.cookies.set(SESSION_COOKIE, create_session_token(email))


def test_credentials_mode_600_no_secret_echo_no_home_fallback(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from app.services import whatsapp_cloud as wa

    safe = wa.save_stored_credentials(
        phone_number_id="109876543210123",
        access_token="super-secret-meta-token-xyz",
        app_secret="super-secret-meta-app-secret-abc",
        verify_token="custom-verify-123",
        owner_numbers=["+57 300 999 8877"],
    )
    blob = json.dumps(safe)
    assert "super-secret-meta-token-xyz" not in blob
    assert "super-secret-meta-app-secret-abc" not in blob
    assert safe["phone_number_id_last4"] == "0123"
    path = tmp_path / "whatsapp_credentials.json"
    assert path.is_file()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert wa.configured() is True
    status = wa.channel_status()
    assert "super-secret-meta-token-xyz" not in json.dumps(status)
    assert "empire-data" not in str(wa._credentials_file_path())


def test_family_refuses_credentials_without_data_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.delenv("EMPIRE_DATA_DIR", raising=False)
    from app.edition import EditionPathError
    from app.services import whatsapp_cloud as wa

    try:
        wa._credentials_file_path()
        raise AssertionError("family edition must refuse without EMPIRE_DATA_DIR")
    except EditionPathError as exc:
        assert "EMPIRE_DATA_DIR" in str(exc)


def test_env_overrides_stored_file(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from app.services import whatsapp_cloud as wa

    wa.save_stored_credentials(
        phone_number_id="111",
        access_token="file-token",
        app_secret="file-secret",
        verify_token="file-verify",
    )
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "env-token")
    assert wa.get_config_value("WHATSAPP_ACCESS_TOKEN") == "env-token"
    assert wa.get_config_value("WHATSAPP_APP_SECRET") == "file-secret"


def test_owner_required_for_credentials_and_test(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from app.services.amp_allowlist import add_entry

    add_entry(email="member@example.com", role="member")
    client = _client()
    _cookie(client, "member@example.com")
    denied = client.post(
        "/api/v1/whatsapp/credentials",
        json={"phone_number_id": "1", "access_token": "tok", "app_secret": "sec"},
    )
    assert denied.status_code == 403
    assert client.post("/api/v1/whatsapp/test", json={}).status_code == 403

    _cookie(client, "owner@example.com")
    saved = client.post(
        "/api/v1/whatsapp/credentials",
        json={
            "phone_number_id": "999888777",
            "access_token": "my-secret-access-token",
            "app_secret": "my-secret-app-secret",
            "owner_numbers": ["+57 300 555 1234"],
        },
    )
    assert saved.status_code == 200
    body = json.dumps(saved.json())
    assert "my-secret-access-token" not in body
    assert "my-secret-app-secret" not in body
    assert saved.json()["credentials"]["phone_number_id_last4"] == "8777"


def test_test_connection_is_get_only(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from app.services import whatsapp_cloud as wa

    calls = []

    def fake(method, url, token="", body=None, headers=None):
        calls.append({"method": method, "url": url, "token": token})
        assert method == "GET"
        assert "messages" not in url
        return 200, json.dumps({
            "display_phone_number": "+57 300 000 0000",
            "verified_name": "Max-e",
        }).encode("utf-8")

    monkeypatch.setattr(wa, "graph_request", fake)
    result = wa.test_connection(phone_number_id="88888888", access_token="mock-token")
    assert result["ok"] is True
    assert result["verified_name"] == "Max-e"
    assert "mock-token" not in json.dumps(result)
    assert len(calls) == 1


def test_no_live_paths_in_this_module():
    text = Path("backend/app/services/whatsapp_cloud.py").read_text(encoding="utf-8")
    assert 'Path(os.path.expanduser("~/empire-data"))' not in text or "family" in text
    # Family credentials path must not assign ~/empire-data.
    cred_fn = text.split("def _credentials_file_path")[1].split("def ")[0]
    assert "~/empire-data" not in cred_fn
