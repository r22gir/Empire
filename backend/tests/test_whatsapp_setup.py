"""Tests for guided WhatsApp setup, credential storage, security, and read-only test connection."""
from __future__ import annotations

import json
import os
import stat
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.services import whatsapp_cloud as wa


def test_whatsapp_storage_mode_600_and_no_secret_leaks(tmp_path, monkeypatch):
    """Credentials must be saved mode 0600 in the edition data dir and never leaked."""
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("WHATSAPP_STATE_DB", str(tmp_path / "wa.db"))

    # Unset env vars to test file loading
    for key in (
        "WHATSAPP_ACCESS_TOKEN",
        "WHATSAPP_PHONE_NUMBER_ID",
        "WHATSAPP_APP_SECRET",
        "WHATSAPP_VERIFY_TOKEN",
        "WHATSAPP_OWNER_NUMBERS",
    ):
        monkeypatch.delenv(key, raising=False)

    # Save credentials via service
    safe_info = wa.save_stored_credentials(
        phone_number_id="109876543210123",
        access_token="super-secret-meta-token-xyz",
        app_secret="super-secret-meta-app-secret-abc",
        verify_token="custom-verify-123",
        owner_numbers=["+57 300 999 8877", "573112223344"],
    )

    # Check safe_info never exposes token or secret
    assert "super-secret-meta-token-xyz" not in json.dumps(safe_info)
    assert "super-secret-meta-app-secret-abc" not in json.dumps(safe_info)
    assert safe_info["phone_number_id_set"] is True
    assert safe_info["phone_number_id_last4"] == "0123"
    assert safe_info["access_token_set"] is True
    assert safe_info["app_secret_set"] is True
    assert safe_info["verify_token"] == "custom-verify-123"
    assert "573009998877" in safe_info["owner_numbers"]
    assert "https://wa-amp.empirebox.store/api/v1/whatsapp/webhook" in safe_info["webhook_url"]

    # Verify file mode is 0600
    creds_file = tmp_path / "whatsapp_credentials.json"
    assert creds_file.is_file()
    file_mode = stat.S_IMODE(creds_file.stat().st_mode)
    assert file_mode == 0o600

    # Verify whatsapp_cloud picks up configuration
    assert wa.configured() is True
    status = wa.channel_status()
    assert status["enabled"] is True
    assert status["status"] == "ready"
    assert "super-secret-meta-token-xyz" not in json.dumps(status)
    assert "super-secret-meta-app-secret-abc" not in json.dumps(status)


def test_whatsapp_env_overrides_stored_credentials(tmp_path, monkeypatch):
    """Process environment variables take precedence over file credentials."""
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("WHATSAPP_STATE_DB", str(tmp_path / "wa.db"))

    # Save credentials into file
    wa.save_stored_credentials(
        phone_number_id="111111111111",
        access_token="file-token",
        app_secret="file-secret",
        verify_token="file-verify",
        owner_numbers=["573001111111"],
    )

    # Set env override
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "222222222222")
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "env-token")

    assert wa.get_config_value("WHATSAPP_PHONE_NUMBER_ID") == "222222222222"
    assert wa.get_config_value("WHATSAPP_ACCESS_TOKEN") == "env-token"
    # Not overridden in env -> falls back to file
    assert wa.get_config_value("WHATSAPP_APP_SECRET") == "file-secret"
    assert wa.get_config_value("WHATSAPP_VERIFY_TOKEN") == "file-verify"


def test_whatsapp_test_connection_read_only(tmp_path, monkeypatch):
    """Test connection must call Graph API read-only and NOT send messages."""
    monkeypatch.setenv("EMPIRE_EDITION", "maxine")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("WHATSAPP_STATE_DB", str(tmp_path / "wa.db"))

    calls = []

    import urllib.request

    class FakeResponse:
        def __init__(self, body: bytes):
            self._body = body

        def read(self):
            return self._body

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    def fake_urlopen(req, timeout=15):
        calls.append({"url": req.full_url, "headers": req.headers, "method": req.get_method()})
        assert req.get_method() == "GET"
        assert "messages" not in req.full_url
        assert "fields=display_phone_number,verified_name" in req.full_url
        return FakeResponse(
            json.dumps({
                "display_phone_number": "+57 300 000 0000",
                "verified_name": "Maxine Construcción",
                "code_verification_status": "VERIFIED",
                "quality_rating": "GREEN",
            }).encode("utf-8")
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    res = wa.test_connection(phone_number_id="88888888", access_token="mock-token")
    assert res["ok"] is True
    assert res["display_phone_number"] == "+57 300 000 0000"
    assert res["verified_name"] == "Maxine Construcción"
    assert len(calls) == 1
    assert "88888888" in calls[0]["url"]


def test_whatsapp_api_routes(tmp_path, monkeypatch):
    """Test router endpoints for credentials, status, and test connection."""
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("WHATSAPP_STATE_DB", str(tmp_path / "wa.db"))

    # Unset env vars
    for key in (
        "WHATSAPP_ACCESS_TOKEN",
        "WHATSAPP_PHONE_NUMBER_ID",
        "WHATSAPP_APP_SECRET",
        "WHATSAPP_VERIFY_TOKEN",
        "WHATSAPP_OWNER_NUMBERS",
    ):
        monkeypatch.delenv(key, raising=False)

    from fastapi import FastAPI
    from app.routers.whatsapp import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    # Initially empty/disabled
    r_status = client.get("/api/v1/whatsapp/status")
    assert r_status.status_code == 200
    assert r_status.json()["enabled"] is False

    # POST credentials
    r_save = client.post(
        "/api/v1/whatsapp/credentials",
        json={
            "phone_number_id": "999888777",
            "access_token": "my-secret-access-token",
            "app_secret": "my-secret-app-secret",
            "owner_numbers": ["+57 300 555 1234"],
        },
    )
    assert r_save.status_code == 200
    saved_body = r_save.json()
    assert saved_body["ok"] is True
    # Secrets never returned in response
    assert "my-secret-access-token" not in json.dumps(saved_body)
    assert "my-secret-app-secret" not in json.dumps(saved_body)
    assert saved_body["credentials"]["phone_number_id_last4"] == "8777"
    assert saved_body["credentials"]["verify_token"] != ""

    # GET credentials (masked)
    r_get = client.get("/api/v1/whatsapp/credentials")
    assert r_get.status_code == 200
    get_body = r_get.json()
    assert "my-secret-access-token" not in json.dumps(get_body)
    assert "my-secret-app-secret" not in json.dumps(get_body)
    assert get_body["access_token_set"] is True
    assert get_body["app_secret_set"] is True
    assert get_body["webhook_url"] == "https://wa-amp.empirebox.store/api/v1/whatsapp/webhook"
