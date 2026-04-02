# STATUS: PLACEHOLDER — This module contains scaffold endpoints only.
# Real integration pending: eBay API, Facebook Marketplace API, Craigslist scraping.
# All endpoints return hardcoded stub data; connect/disconnect do nothing.
# No MarketplaceAccount model or credential storage is implemented.

"""
Marketplace routes for connecting and managing marketplace accounts.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.database import get_db
from app.models import User
from app.middleware import get_current_user

router = APIRouter(tags=["Marketplaces"])


@router.get("")
async def get_marketplaces(
    current_user: User = Depends(get_current_user)
):
    """
    Get list of available marketplaces and their connection status.
    """
    marketplaces = [
        {
            "name": "ebay",
            "is_connected": False,
            "is_implemented": True,
            "icon_url": "https://example.com/icons/ebay.png"
        },
        {
            "name": "facebook",
            "is_connected": False,
            "is_implemented": False,
            "icon_url": "https://example.com/icons/facebook.png"
        },
        {
            "name": "craigslist",
            "is_connected": False,
            "is_implemented": False,
            "icon_url": "https://example.com/icons/craigslist.png"
        }
    ]
    
    return marketplaces


@router.post("/{marketplace_name}/connect")
async def connect_marketplace(
    marketplace_name: str,
    credentials: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Connect to a marketplace.
    """
    # TODO: Implement actual marketplace connection
    # Would create MarketplaceAccount record with encrypted credentials
    
    return {
        "message": f"Connected to {marketplace_name}",
        "marketplace": marketplace_name,
        "status": "connected"
    }


@router.delete("/{marketplace_name}/disconnect")
async def disconnect_marketplace(
    marketplace_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Disconnect from a marketplace.
    """
    # TODO: Implement actual marketplace disconnection
    # Would deactivate MarketplaceAccount record
    
    return {
        "message": f"Disconnected from {marketplace_name}",
        "marketplace": marketplace_name,
        "status": "disconnected"
    }
