"""OAuth2 connect for Meta, and a generic provider used by Pinterest and LinkedIn.

Providers with missing client id or secret report ``needs_keys`` and do not
build an authorize URL. Tokens are sealed in the vault. Redirect URIs are
``{EMPIRE_PUBLIC_BASE_URL}/api/v1/socialforge/oauth/{provider}/callback``.
"""
from __future__ import annotations

import os
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlencode

from app.services.accounts.catalog import public_base_url
from app.services.accounts.store import mark_connected
from app.services.accounts.vault import Vault, put_secret


@dataclass(frozen=True)
class OAuthProvider:
    name: str
    authorize_url: str
    token_url: str
    scopes: tuple[str, ...]
    client_id_env: str
    client_secret_env: str
    redirect_path: str
    use_basic_auth: bool = False

    def client_id(self) -> str:
        return os.getenv(self.client_id_env, "").strip()

    def client_secret(self) -> str:
        return os.getenv(self.client_secret_env, "").strip()

    def configured(self) -> bool:
        return bool(self.client_id() and self.client_secret())

    def redirect_uri(self) -> str:
        return public_base_url() + self.redirect_path

    def status(self) -> str:
        return "ready" if self.configured() else "needs_keys"


META = OAuthProvider(
    name="meta",
    authorize_url="https://www.facebook.com/v21.0/dialog/oauth",
    token_url="https://graph.facebook.com/v21.0/oauth/access_token",
    scopes=(
        "pages_show_list",
        "pages_manage_posts",
        "pages_read_engagement",
        "instagram_basic",
        "instagram_content_publish",
        "business_management",
    ),
    client_id_env="META_APP_ID",
    client_secret_env="META_APP_SECRET",
    redirect_path="/api/v1/socialforge/oauth/meta/callback",
)

PINTEREST = OAuthProvider(
    name="pinterest",
    authorize_url="https://www.pinterest.com/oauth/",
    token_url="https://api.pinterest.com/v5/oauth/token",
    scopes=("boards:read", "pins:read", "pins:write"),
    client_id_env="PINTEREST_APP_ID",
    client_secret_env="PINTEREST_APP_SECRET",
    redirect_path="/api/v1/socialforge/oauth/pinterest/callback",
    use_basic_auth=True,
)

LINKEDIN = OAuthProvider(
    name="linkedin",
    authorize_url="https://www.linkedin.com/oauth/v2/authorization",
    token_url="https://www.linkedin.com/oauth/v2/accessToken",
    scopes=("openid", "profile", "w_member_social"),
    client_id_env="LINKEDIN_CLIENT_ID",
    client_secret_env="LINKEDIN_CLIENT_SECRET",
    redirect_path="/api/v1/socialforge/oauth/linkedin/callback",
)

PROVIDERS: dict[str, OAuthProvider] = {
    "meta": META,
    "facebook": META,
    "instagram": META,
    "pinterest": PINTEREST,
    "linkedin": LINKEDIN,
}

# Platforms a single Meta consent connects.
META_PLATFORMS = ("facebook", "instagram")


def provider_for(name: str) -> OAuthProvider | None:
    return PROVIDERS.get(name)


def provider_catalog() -> list[dict]:
    seen: list[dict] = []
    listed = set()
    for provider in (META, PINTEREST, LINKEDIN):
        if provider.name in listed:
            continue
        listed.add(provider.name)
        seen.append({
            "provider": provider.name,
            "status": provider.status(),
            "redirect_uri": provider.redirect_uri(),
            "scopes": list(provider.scopes),
            "client_id_env": provider.client_id_env,
            "client_secret_env": provider.client_secret_env,
        })
    return seen


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_authorize_url(conn: sqlite3.Connection, provider: OAuthProvider, business_key: str, platform: str) -> dict:
    if not provider.configured():
        return {
            "provider": provider.name,
            "status": "needs_keys",
            "authorize_url": None,
            "redirect_uri": provider.redirect_uri(),
        }
    state = secrets.token_urlsafe(24)
    conn.execute(
        "INSERT INTO oauth_states (state, provider, business_key, platform, code_verifier, created_at) VALUES (?, ?, ?, ?, '', ?)",
        (state, provider.name, business_key, platform, _now()),
    )
    conn.commit()
    query = urlencode({
        "response_type": "code",
        "client_id": provider.client_id(),
        "redirect_uri": provider.redirect_uri(),
        "scope": " ".join(provider.scopes) if provider.name != "meta" else ",".join(provider.scopes),
        "state": state,
    })
    return {
        "provider": provider.name,
        "status": "ready",
        "authorize_url": f"{provider.authorize_url}?{query}",
        "redirect_uri": provider.redirect_uri(),
        "state": state,
    }


def token_request(provider: OAuthProvider, code: str) -> dict:
    """Describe the token exchange. The caller performs it via a transport."""
    body = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": provider.redirect_uri(),
        "client_id": provider.client_id(),
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if provider.use_basic_auth:
        import base64
        pair = f"{provider.client_id()}:{provider.client_secret()}".encode()
        headers["Authorization"] = "Basic " + base64.b64encode(pair).decode("ascii")
    else:
        body["client_secret"] = provider.client_secret()
    return {"url": provider.token_url, "body": body, "headers": headers}


def refresh_request(provider: OAuthProvider, refresh_token: str) -> dict:
    """Token refresh. Meta long-lived exchange uses the current access token."""
    if provider.name == "meta":
        return {
            "url": provider.token_url,
            "method": "GET",
            "params": {
                "grant_type": "fb_exchange_token",
                "client_id": provider.client_id(),
                "client_secret": provider.client_secret(),
                "fb_exchange_token": refresh_token,
            },
        }
    body = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": provider.client_id(),
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if provider.use_basic_auth:
        import base64
        pair = f"{provider.client_id()}:{provider.client_secret()}".encode()
        headers["Authorization"] = "Basic " + base64.b64encode(pair).decode("ascii")
    else:
        body["client_secret"] = provider.client_secret()
    return {"url": provider.token_url, "method": "POST", "body": body, "headers": headers}


def consume_state(conn: sqlite3.Connection, state: str) -> sqlite3.Row | None:
    row = conn.execute("SELECT * FROM oauth_states WHERE state = ?", (state,)).fetchone()
    if row:
        conn.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
        conn.commit()
    return row


def store_token_response(
    conn: sqlite3.Connection,
    vault: Vault,
    *,
    business_key: str,
    platform: str,
    token_payload: dict,
    external_id: str = "",
) -> str:
    """Seal the provider token JSON. Returns the secret id, not the token."""
    import json
    secret_id = f"oauth:{business_key}:{platform}"
    put_secret(conn, vault, secret_id, json.dumps(token_payload))
    mark_connected(conn, business_key, platform, secret_id, external_id)
    return secret_id
