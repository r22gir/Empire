"""Etsy Open API v3 is real. Other marketplaces do not pretend to connect."""
from __future__ import annotations

import json

from cryptography.fernet import Fernet

from app.services.accounts.etsy import (
    ETSY_API,
    create_draft_listing,
    etsy_redirect_uri,
    finish_etsy_oauth,
    marketplace_connection_state,
    start_etsy_connect,
    sync_listings,
    sync_orders,
)
from app.services.accounts.store import connect
from app.services.accounts.vault import Vault
from app.services.marketplace.ebay import EbayService


def test_etsy_needs_keys_and_names_the_redirect(monkeypatch, tmp_path):
    monkeypatch.delenv("ETSY_CLIENT_ID", raising=False)
    monkeypatch.setenv("EMPIRE_DB", str(tmp_path / "empire.db"))
    monkeypatch.setenv("EMPIRE_PUBLIC_BASE_URL", "https://studio.empirebox.store")
    conn = connect()
    try:
        started = start_etsy_connect(conn, "workroom")
    finally:
        conn.close()
    assert started["status"] == "needs_keys"
    assert started["connected"] is False
    assert started["authorize_url"] is None
    assert started["redirect_uri"] == "https://studio.empirebox.store/api/v1/marketforge/oauth/etsy/callback"
    assert etsy_redirect_uri() == started["redirect_uri"]
    for name in ("ebay", "amazon", "craigslist"):
        state = marketplace_connection_state(name)
        assert state["connected"] is False
        assert state["listing_url"] is None
        assert state["authorize_url"] is None
        assert state["status"] in {"needs_keys", "not_connected"}


def test_etsy_pkce_connect_seals_the_token(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_DB", str(tmp_path / "empire.db"))
    monkeypatch.setenv("EMPIRE_PUBLIC_BASE_URL", "https://studio.empirebox.store")
    monkeypatch.setenv("ETSY_CLIENT_ID", "etsy-keystring")
    monkeypatch.setenv("EMPIRE_VAULT_KEY", Fernet.generate_key().decode())
    conn = connect()
    started = start_etsy_connect(conn, "woodcraft")
    assert started["authorize_url"].startswith("https://www.etsy.com/oauth/connect?")
    assert "code_challenge_method=S256" in started["authorize_url"]
    assert "etsy-keystring" in started["authorize_url"]
    state = started["authorize_url"].split("state=")[1].split("&")[0]
    vault = Vault()

    def transport(method, url, **kwargs):
        assert method == "POST"
        assert url.endswith("/oauth/token")
        assert kwargs["data"]["code_verifier"]
        return {"access_token": "etsy-token", "refresh_token": "etsy-refresh", "shop_id": "444"}

    result = finish_etsy_oauth(conn, vault, state, "auth-code", transport)
    assert result["connected"] is True
    assert result["shop_id"] == "444"
    assert "etsy-token" not in json.dumps(result)
    conn.close()


def test_etsy_listings_are_drafts_and_orders_are_read_only():
    calls = []

    def transport(method, url, **kwargs):
        calls.append((method, url, kwargs.get("json")))
        return {"listing_id": 7, "count": 1}

    created = create_draft_listing(transport, "444", "etsy-token", {"title": "Shade", "state": "active"})
    assert created["status"] == "draft"
    assert calls[0][0] == "POST"
    assert calls[0][1] == f"{ETSY_API}/shops/444/listings"
    assert calls[0][2]["state"] == "draft"
    sync_listings(transport, "444", "etsy-token")
    sync_orders(transport, "444", "etsy-token")
    assert calls[1][0] == "GET"
    assert calls[1][1].endswith("/listings")
    assert calls[2][0] == "GET"
    assert calls[2][1].endswith("/receipts")


def test_ebay_authenticate_and_publish_are_not_a_fake_success():
    import asyncio
    service = EbayService()
    auth = asyncio.run(service.authenticate({}))
    published = asyncio.run(service.publish_listing({}))
    assert auth["status"] == "needs_keys"
    assert auth["access_token"] is None
    assert published["url"] is None
    assert published["status"] == "needs_keys"
    assert "ebay.com/itm" not in json.dumps(published)
