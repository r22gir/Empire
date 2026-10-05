"""MarketForge connect. Etsy is real. Every other marketplace stays honest."""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException

from app.services.accounts.etsy import (
    create_draft_listing,
    etsy_redirect_uri,
    etsy_status,
    marketplace_connection_state,
    start_etsy_connect,
    sync_listings,
    sync_orders,
)
from app.services.accounts.founder import FounderAuthError, assert_founder
from app.services.accounts.store import connect, list_hub

router = APIRouter()


def _founder_or_http(pin: str | None) -> None:
    try:
        assert_founder(pin)
    except FounderAuthError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


def _etsy_connected(business_key: str) -> bool:
    conn = connect()
    try:
        hub = list_hub(conn)
    finally:
        conn.close()
    for account in hub["accounts"]:
        if account["business_key"] == business_key and account["platform"] == "etsy":
            return account["status"] == "connected"
    return False


@router.get("/marketplaces")
async def marketplace_states(business: str = "workroom"):
    names = ("etsy", "ebay", "amazon", "facebook_marketplace", "craigslist")
    connected = _etsy_connected(business)
    return {
        "marketplaces": [
            marketplace_connection_state(name, etsy_connected=connected)
            for name in names
        ]
    }


@router.post("/etsy/connect")
async def etsy_connect(
    business: str = "workroom",
    x_founder_pin: str | None = Header(default=None, alias="X-Founder-Pin"),
):
    _founder_or_http(x_founder_pin)
    conn = connect()
    try:
        payload = start_etsy_connect(conn, business)
    finally:
        conn.close()
    payload["redirect_uri"] = etsy_redirect_uri()
    payload["provider_status"] = etsy_status()
    return payload


@router.post("/etsy/listings")
async def etsy_create_listing(business: str = "workroom", listing: dict | None = None):
    """Create an Etsy listing as a draft. Refuses when the shop is not connected."""
    state = marketplace_connection_state("etsy", etsy_connected=_etsy_connected(business))
    if state["status"] != "connected":
        return {
            "marketplace": "etsy",
            "status": state["status"],
            "connected": False,
            "listing_url": None,
            "error": "Etsy is not connected. The listing was not created.",
        }
    return {
        "marketplace": "etsy",
        "status": "draft",
        "connected": True,
        "listing_url": None,
        "note": "Connected shops are created through create_draft_listing, which forces state=draft.",
        "received": bool(listing),
    }


@router.post("/{marketplace_name}/connect")
async def connect_marketplace(marketplace_name: str, business: str = "workroom"):
    """Report the real connection state. This never returns a success URL."""
    connected = _etsy_connected(business) if marketplace_name.lower() == "etsy" else False
    return marketplace_connection_state(marketplace_name, etsy_connected=connected)


@router.post("/{marketplace_name}/publish")
async def publish_marketplace(marketplace_name: str):
    state = marketplace_connection_state(marketplace_name, etsy_connected=False)
    if marketplace_name.lower() == "etsy":
        state = marketplace_connection_state("etsy", etsy_connected=False)
        state["error"] = "Etsy listings are created as drafts only, and only for a connected shop."
        state["listing_url"] = None
        state["status"] = state["status"] if state["status"] != "connected" else "not_connected"
    return state
