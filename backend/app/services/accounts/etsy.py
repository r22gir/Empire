"""Etsy Open API v3. OAuth PKCE, shop connect, draft listings, read-only sync.

Listings are always created with state ``draft``. Orders and listings are
fetched with GET only. Missing ETSY_CLIENT_ID is ``needs_keys``.
"""
from __future__ import annotations

import base64
import hashlib
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from urllib.parse import urlencode

from app.services.accounts.catalog import public_base_url
from app.services.accounts.store import mark_connected
from app.services.accounts.vault import Vault, put_secret

ETSY_AUTHORIZE = "https://www.etsy.com/oauth/connect"
ETSY_TOKEN = "https://api.etsy.com/v3/public/oauth/token"
ETSY_API = "https://openapi.etsy.com/v3/application"
ETSY_SCOPES = ("listings_r", "listings_w", "transactions_r", "shops_r")
ETSY_REDIRECT_PATH = "/api/v1/marketforge/oauth/etsy/callback"

HONEST_UNCONNECTED = {
    "ebay": "needs_keys",
    "amazon": "needs_keys",
    "facebook": "not_connected",
    "facebook_marketplace": "not_connected",
    "craigslist": "not_connected",
}


def etsy_client_id() -> str:
    return os.getenv("ETSY_CLIENT_ID", "").strip()


def etsy_redirect_uri() -> str:
    return public_base_url() + ETSY_REDIRECT_PATH


def etsy_status() -> str:
    return "ready" if etsy_client_id() else "needs_keys"


def pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def start_etsy_connect(conn: sqlite3.Connection, business_key: str) -> dict:
    redirect = etsy_redirect_uri()
    if not etsy_client_id():
        return {
            "marketplace": "etsy",
            "status": "needs_keys",
            "connected": False,
            "authorize_url": None,
            "redirect_uri": redirect,
        }
    verifier, challenge = pkce_pair()
    state = secrets.token_urlsafe(24)
    conn.execute(
        "INSERT INTO oauth_states (state, provider, business_key, platform, code_verifier, created_at) VALUES (?, 'etsy', ?, 'etsy', ?, ?)",
        (state, business_key, verifier, _now()),
    )
    conn.commit()
    query = urlencode({
        "response_type": "code",
        "client_id": etsy_client_id(),
        "redirect_uri": redirect,
        "scope": " ".join(ETSY_SCOPES),
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })
    return {
        "marketplace": "etsy",
        "status": "ready",
        "connected": False,
        "authorize_url": f"{ETSY_AUTHORIZE}?{query}",
        "redirect_uri": redirect,
    }


def etsy_token_request(code: str, verifier: str) -> dict:
    return {
        "url": ETSY_TOKEN,
        "body": {
            "grant_type": "authorization_code",
            "client_id": etsy_client_id(),
            "redirect_uri": etsy_redirect_uri(),
            "code": code,
            "code_verifier": verifier,
        },
    }


def finish_etsy_oauth(conn: sqlite3.Connection, vault: Vault, state: str, code: str, transport) -> dict:
    """Exchange the Etsy code and seal the token. The token is not returned."""
    row = conn.execute("SELECT * FROM oauth_states WHERE state = ?", (state,)).fetchone()
    if row is None:
        return {"marketplace": "etsy", "status": "not_connected", "connected": False, "listing_url": None, "error": "OAuth state is missing"}
    described = etsy_token_request(code, row["code_verifier"])
    response = transport("POST", described["url"], data=described["body"]) or {}
    if not response.get("access_token"):
        return {"marketplace": "etsy", "status": "not_connected", "connected": False, "listing_url": None, "error": "Etsy token exchange failed"}
    shop_id = str(response.get("shop_id") or "")
    store_etsy_token(conn, vault, row["business_key"], response, shop_id)
    conn.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
    conn.commit()
    return {
        "marketplace": "etsy",
        "status": "connected",
        "connected": True,
        "shop_id": shop_id,
        "listing_url": None,
    }


def store_etsy_token(conn: sqlite3.Connection, vault: Vault, business_key: str, payload: dict, shop_id: str = "") -> str:
    import json
    secret_id = f"oauth:{business_key}:etsy"
    put_secret(conn, vault, secret_id, json.dumps(payload))
    mark_connected(conn, business_key, "etsy", secret_id, shop_id)
    return secret_id


def create_draft_listing(transport, shop_id: str, token: str, listing: dict) -> dict:
    """POST a listing and force state=draft no matter what the caller asked."""
    body = dict(listing)
    body["state"] = "draft"
    response = transport(
        "POST",
        f"{ETSY_API}/shops/{shop_id}/listings",
        json=body,
        headers={
            "Authorization": f"Bearer {token}",
            "x-api-key": etsy_client_id(),
        },
    )
    return {"status": "draft", "listing": response, "requested_state": "draft"}


def sync_listings(transport, shop_id: str, token: str) -> dict:
    response = transport(
        "GET",
        f"{ETSY_API}/shops/{shop_id}/listings",
        headers={"Authorization": f"Bearer {token}", "x-api-key": etsy_client_id()},
    )
    return {"status": "ok", "mode": "read-only", "listings": response}


def sync_orders(transport, shop_id: str, token: str) -> dict:
    response = transport(
        "GET",
        f"{ETSY_API}/shops/{shop_id}/receipts",
        headers={"Authorization": f"Bearer {token}", "x-api-key": etsy_client_id()},
    )
    return {"status": "ok", "mode": "read-only", "orders": response}


def marketplace_connection_state(name: str, *, etsy_connected: bool = False) -> dict:
    """Honest state for every marketplace. No success URL is invented."""
    key = (name or "").strip().lower()
    if key == "etsy":
        if not etsy_client_id():
            status = "needs_keys"
        elif etsy_connected:
            status = "connected"
        else:
            status = "not_connected"
        return {
            "marketplace": "etsy",
            "connected": status == "connected",
            "status": status,
            "authorize_url": None,
            "listing_url": None,
        }
    status = HONEST_UNCONNECTED.get(key, "not_connected")
    return {
        "marketplace": key or name,
        "connected": False,
        "status": status,
        "authorize_url": None,
        "listing_url": None,
        "error": f"{name} is {status.replace('_', ' ')}. Nothing was published.",
    }
