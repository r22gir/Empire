"""
Listing routes for CRUD operations and publishing.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from app.database import get_db
from app.models import User
from app.middleware import get_current_user
from app.schemas.listing import (
    ListingCreate,
    ListingUpdate,
    ListingResponse,
    PublishRequest,
    PublishResponse
)
from app.services.listing_service import (
    create_listing,
    get_user_listings,
    get_listing_by_id,
    update_listing,
    delete_listing,
    publish_listing
)

router = APIRouter(prefix="/listings", tags=["Listings"])


@router.get("", response_model=List[ListingResponse])
async def get_listings(
    status: Optional[str] = Query(None),
    marketplace: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's listings with optional filters.
    """
    listings = await get_user_listings(current_user, db, status, marketplace, limit)
    return listings


@router.post("", response_model=ListingResponse)
async def create_new_listing(
    listing_data: ListingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new listing.
    """
    listing = await create_listing(current_user, listing_data, db)
    return listing


@router.get("/{listing_id}", response_model=ListingResponse)
async def get_listing(
    listing_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific listing by ID.
    """
    listing = await get_listing_by_id(listing_id, current_user, db)
    return listing


@router.put("/{listing_id}", response_model=ListingResponse)
async def update_existing_listing(
    listing_id: UUID,
    update_data: ListingUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a listing.
    """
    listing = await update_listing(listing_id, current_user, update_data, db)
    return listing


@router.delete("/{listing_id}")
async def delete_existing_listing(
    listing_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a listing.
    """
    await delete_listing(listing_id, current_user, db)
    return {"message": "Listing deleted successfully"}


@router.post("/{listing_id}/publish", response_model=PublishResponse)
async def publish_listing_to_marketplaces(
    listing_id: UUID,
    publish_data: PublishRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Publish listing to multiple marketplaces.
    """
    result = await publish_listing(listing_id, current_user, publish_data, db)
    return result
