"""OAuth providers stay disabled until their env keys exist."""
from __future__ import annotations

import json

from cryptography.fernet import Fernet

from app.services.accounts.catalog import public_base_url
from app.services.accounts.oauth import (
    LINKEDIN,
    META,
    PINTEREST,
    build_authorize_url,
    provider_catalog,
    refresh_request,
    store_token_response,
)
from app.services.accounts.store import connect, list_hub
from app.services.accounts.vault import Vault, open_secret


def _silence_providers(monkeypatch):
    for name in (
        "META_APP_ID", "META_APP_SECRET",
        "PINTEREST_APP_ID", "PINTEREST_APP_SECRET",
        "LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET",
    ):
        monkeypatch.delenv(name, raising=False)


def test_providers_need_keys_until_env_is_set(monkeypatch):
    _silence_providers(monkeypatch)
    catalog = {item["provider"]: item for item in provider_catalog()}
    assert catalog["meta"]["status"] == "needs_keys"
    assert catalog["pinterest"]["status"] == "needs_keys"
    assert catalog["linkedin"]["status"] == "needs_keys"
    base = public_base_url()
    assert catalog["meta"]["redirect_uri"] == f"{base}/api/v1/socialforge/oauth/meta/callback"
    assert catalog["pinterest"]["redirect_uri"] == f"{base}/api/v1/socialforge/oauth/pinterest/callback"
    assert catalog["linkedin"]["redirect_uri"] == f"{base}/api/v1/socialforge/oauth/linkedin/callback"


def test_meta_authorize_url_includes_redirect_and_scopes(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_DB", str(tmp_path / "empire.db"))
    monkeypatch.setenv("EMPIRE_PUBLIC_BASE_URL", "https://studio.empirebox.store")
    monkeypatch.setenv("META_APP_ID", "meta-app")
    monkeypatch.setenv("META_APP_SECRET", "meta-secret")
    conn = connect()
    try:
        started = build_authorize_url(conn, META, "workroom", "facebook")
    finally:
        conn.close()
    assert started["status"] == "ready"
    url = started["authorize_url"]
    assert url.startswith("https://www.facebook.com/v21.0/dialog/oauth?")
    assert "client_id=meta-app" in url
    assert "redirect_uri=https%3A%2F%2Fstudio.empirebox.store%2Fapi%2Fv1%2Fsocialforge%2Foauth%2Fmeta%2Fcallback" in url
    assert "pages_manage_posts" in url
    assert "instagram_content_publish" in url
    assert "meta-secret" not in url


def test_pinterest_and_linkedin_are_generic_oauth(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_DB", str(tmp_path / "empire.db"))
    monkeypatch.setenv("EMPIRE_PUBLIC_BASE_URL", "https://studio.empirebox.store")
    monkeypatch.setenv("PINTEREST_APP_ID", "pin-app")
    monkeypatch.setenv("PINTEREST_APP_SECRET", "pin-secret")
    monkeypatch.setenv("LINKEDIN_CLIENT_ID", "li-app")
    monkeypatch.setenv("LINKEDIN_CLIENT_SECRET", "li-secret")
    conn = connect()
    try:
        pin = build_authorize_url(conn, PINTEREST, "workroom", "pinterest")
        li = build_authorize_url(conn, LINKEDIN, "woodcraft", "linkedin")
    finally:
        conn.close()
    assert pin["authorize_url"].startswith("https://www.pinterest.com/oauth/?")
    assert "redirect_uri=https%3A%2F%2Fstudio.empirebox.store%2Fapi%2Fv1%2Fsocialforge%2Foauth%2Fpinterest%2Fcallback" in pin["authorize_url"]
    assert li["authorize_url"].startswith("https://www.linkedin.com/oauth/v2/authorization?")
    assert "w_member_social" in li["authorize_url"]
    refresh = refresh_request(PINTEREST, "refresh-me")
    assert refresh["url"] == "https://api.pinterest.com/v5/oauth/token"
    assert refresh["body"]["grant_type"] == "refresh_token"
    meta_refresh = refresh_request(META, "current-token")
    assert meta_refresh["params"]["grant_type"] == "fb_exchange_token"
    assert "pin-secret" not in pin["authorize_url"]
    assert "li-secret" not in li["authorize_url"]


def test_callback_seals_the_token_and_hub_stays_redacted(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_DB", str(tmp_path / "empire.db"))
    monkeypatch.setenv("EMPIRE_VAULT_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("META_APP_ID", "meta-app")
    monkeypatch.setenv("META_APP_SECRET", "meta-secret")
    conn = connect()
    vault = Vault()
    secret_id = store_token_response(
        conn, vault,
        business_key="workroom",
        platform="facebook",
        token_payload={"access_token": "sealed-page-token", "page_id": "99"},
        external_id="99",
    )
    opened = json.loads(open_secret(conn, vault, secret_id))
    assert opened["access_token"] == "sealed-page-token"
    hub = list_hub(conn)
    conn.close()
    account = next(item for item in hub["accounts"] if item["id"] == "workroom:facebook")
    assert account["status"] == "connected"
    assert account["has_credentials"] is True
    assert account["last_sync_at"]
    blob = json.dumps(hub)
    assert "sealed-page-token" not in blob
    assert "meta-secret" not in blob
