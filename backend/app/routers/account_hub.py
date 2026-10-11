"""Accounts hub HTTP API. Responses never include vault ciphertext or tokens."""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException

from app.services.accounts.founder import FounderAuthError, assert_founder
from app.services.accounts.oauth import (
    build_authorize_url,
    consume_state,
    provider_catalog,
    provider_for,
    refresh_request,
    store_token_response,
    token_request,
)
from app.services.accounts.store import (
    connect,
    list_hub,
    set_auto_publish,
    set_publish_paused,
)
from app.services.accounts.vault import VaultNotConfigured, migrate_plaintext_social_tokens, require_vault

router = APIRouter()


def _founder_or_http(pin: str | None) -> None:
    try:
        assert_founder(pin)
    except FounderAuthError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.get("/accounts/hub")
async def accounts_hub():
    """Every platform account SocialForge owns, per business."""
    conn = connect()
    try:
        return list_hub(conn)
    finally:
        conn.close()


@router.get("/oauth/providers")
async def oauth_providers():
    return {"providers": provider_catalog()}


@router.get("/oauth/{provider}/start")
async def oauth_start(
    provider: str,
    business: str = "workroom",
    platform: str | None = None,
    x_founder_pin: str | None = Header(default=None, alias="X-Founder-Pin"),
):
    _founder_or_http(x_founder_pin)
    spec = provider_for(provider)
    if spec is None:
        raise HTTPException(404, "Unknown OAuth provider")
    target = platform or (provider if provider in {"facebook", "instagram", "pinterest", "linkedin"} else "facebook")
    conn = connect()
    try:
        return build_authorize_url(conn, spec, business, target)
    finally:
        conn.close()


@router.get("/oauth/{provider}/refresh-request")
async def oauth_refresh_shape(
    provider: str,
    x_founder_pin: str | None = Header(default=None, alias="X-Founder-Pin"),
):
    """Describe the refresh call. The live token is not returned."""
    _founder_or_http(x_founder_pin)
    spec = provider_for(provider)
    if spec is None:
        raise HTTPException(404, "Unknown OAuth provider")
    if not spec.configured():
        return {"provider": spec.name, "status": "needs_keys", "request": None}
    described = refresh_request(spec, refresh_token="stored-in-vault")
    body = dict(described.get("body") or {})
    params = dict(described.get("params") or {})
    for bucket in (body, params):
        for key in ("refresh_token", "fb_exchange_token", "client_secret"):
            if key in bucket:
                bucket[key] = "[redacted]"
    return {"provider": spec.name, "status": "ready", "url": described["url"], "body": body, "params": params}


@router.get("/oauth/{provider}/callback")
async def oauth_callback(provider: str, code: str = "", state: str = "", error: str = ""):
    """Browser return path. The access token is sealed and is not in this response."""
    if error or not code or not state:
        return {"status": "not_connected", "connected": False, "error": error or "missing code"}
    spec = provider_for(provider)
    if spec is None or not spec.configured():
        return {"status": "needs_keys", "connected": False, "authorize_url": None}
    described = token_request(spec, code)
    try:
        import httpx
        response = httpx.post(described["url"], data=described["body"], headers=described["headers"], timeout=20)
        payload = response.json()
    except Exception:
        return {"status": "not_connected", "connected": False, "error": "token exchange failed"}
    if not isinstance(payload, dict) or not payload.get("access_token"):
        return {"status": "not_connected", "connected": False, "error": "token exchange failed"}
    try:
        result = complete_oauth_callback(provider, state, code, payload)
    except HTTPException as exc:
        return {"status": "not_connected", "connected": False, "error": exc.detail}
    return {
        "status": result["status"],
        "connected": result["connected"],
        "provider": result["provider"],
        "business_key": result["business_key"],
        "platform": result["platform"],
    }


@router.post("/accounts/hub/migrate-tokens")
async def migrate_tokens(x_founder_pin: str | None = Header(default=None, alias="X-Founder-Pin")):
    _founder_or_http(x_founder_pin)
    try:
        vault = require_vault()
    except VaultNotConfigured as exc:
        raise HTTPException(503, str(exc)) from exc
    conn = connect()
    try:
        moved = migrate_plaintext_social_tokens(conn, vault)
        return {"migrated": moved}
    finally:
        conn.close()


@router.post("/accounts/{business_key}/{platform}/auto-publish")
async def set_account_auto_publish(
    business_key: str,
    platform: str,
    enabled: bool = False,
    x_founder_pin: str | None = Header(default=None, alias="X-Founder-Pin"),
):
    _founder_or_http(x_founder_pin)
    conn = connect()
    try:
        if not set_auto_publish(conn, business_key, platform, enabled):
            raise HTTPException(404, "Account not found")
        return {"business_key": business_key, "platform": platform, "auto_publish": enabled}
    finally:
        conn.close()


@router.post("/publish/pause")
async def pause_publisher(
    paused: bool = True,
    x_founder_pin: str | None = Header(default=None, alias="X-Founder-Pin"),
):
    _founder_or_http(x_founder_pin)
    conn = connect()
    try:
        set_publish_paused(conn, paused)
        return {"publish_paused": paused}
    finally:
        conn.close()


def complete_oauth_callback(provider_name: str, state: str, code: str, token_payload: dict, external_id: str = "") -> dict:
    """Seal a token after the browser returns. Used by the callback route and tests."""
    spec = provider_for(provider_name)
    if spec is None:
        raise HTTPException(404, "Unknown OAuth provider")
    if not spec.configured():
        return {"status": "needs_keys", "connected": False}
    try:
        vault = require_vault()
    except VaultNotConfigured as exc:
        raise HTTPException(503, str(exc)) from exc
    conn = connect()
    try:
        saved = consume_state(conn, state)
        if saved is None:
            raise HTTPException(400, "OAuth state is missing or already used")
        secret_id = store_token_response(
            conn,
            vault,
            business_key=saved["business_key"],
            platform=saved["platform"],
            token_payload=token_payload,
            external_id=external_id,
        )
        exchange = token_request(spec, code)
        return {
            "status": "connected",
            "connected": True,
            "provider": spec.name,
            "business_key": saved["business_key"],
            "platform": saved["platform"],
            "secret_id": secret_id,
            "token_endpoint": exchange["url"],
        }
    finally:
        conn.close()
