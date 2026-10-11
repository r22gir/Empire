# Honest marketplace status. Nothing here reports a successful connect.
from fastapi import APIRouter

from app.services.accounts.etsy import marketplace_connection_state

router = APIRouter(tags=["Marketplaces"])


@router.get("")
async def get_marketplaces():
    """Available marketplaces and whether a real connection exists."""
    names = ("etsy", "ebay", "amazon", "facebook", "craigslist")
    return [marketplace_connection_state(name) for name in names]


@router.post("/{marketplace_name}/connect")
async def connect_marketplace(marketplace_name: str):
    """Do not claim a marketplace is connected when it is not."""
    return marketplace_connection_state(marketplace_name)


@router.delete("/{marketplace_name}/disconnect")
async def disconnect_marketplace(marketplace_name: str):
    state = marketplace_connection_state(marketplace_name)
    state["status"] = "not_connected"
    state["connected"] = False
    return state
