"""
Listing service for CRUD operations and publishing.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from typing import List, Optional
from uuid import UUID
from app.models import Listing, User
from app.schemas.listing import (
    ListingCreate,
    ListingUpdate,
    PublishRequest,
    PublishResponse,
    PublishResult
)


async def create_listing(user: User, listing_data: ListingCreate, db: AsyncSession) -> Listing:
    """
    Create a new listing.
    
    Args:
        user: Current user
        listing_data: Listing creation data
        db: Database session
        
    Returns:
        Created listing
    """
    new_listing = Listing(
        user_id=user.id,
        title=listing_data.title,
        description=listing_data.description,
        price=listing_data.price,
        category=listing_data.category,
        condition=listing_data.condition,
        location=listing_data.location,
        photos=[photo.dict() for photo in (listing_data.photos or [])],
        status="draft"
    )
    
    db.add(new_listing)
    await db.commit()
    await db.refresh(new_listing)
    
    return new_listing


async def get_user_listings(
    user: User,
    db: AsyncSession,
    status: Optional[str] = None,
    marketplace: Optional[str] = None,
    limit: int = 50
) -> List[Listing]:
    """
    Get user's listings with optional filters.
    
    Args:
        user: Current user
        db: Database session
        status: Filter by status
        marketplace: Filter by marketplace
        limit: Maximum number of results
        
    Returns:
        List of listings
    """
    query = select(Listing).where(Listing.user_id == user.id)
    
    if status:
        query = query.where(Listing.status == status)
    
    # Marketplace filtering would require JSON query
    # For simplicity, filter in Python for now
    
    query = query.limit(limit)
    
    result = await db.execute(query)
    listings = result.scalars().all()
    
    return list(listings)


async def get_listing_by_id(listing_id: UUID, user: User, db: AsyncSession) -> Listing:
    """
    Get a specific listing by ID.
    
    Args:
        listing_id: Listing UUID
        user: Current user
        db: Database session
        
    Returns:
        Listing object
        
    Raises:
        HTTPException: If listing not found or not owned by user
    """
    result = await db.execute(
        select(Listing).where(Listing.id == listing_id, Listing.user_id == user.id)
    )
    listing = result.scalar_one_or_none()
    
    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing not found"
        )
    
    return listing


async def update_listing(
    listing_id: UUID,
    user: User,
    update_data: ListingUpdate,
    db: AsyncSession
) -> Listing:
    """
    Update a listing.
    
    Args:
        listing_id: Listing UUID
        user: Current user
        update_data: Update data
        db: Database session
        
    Returns:
        Updated listing
    """
    listing = await get_listing_by_id(listing_id, user, db)
    
    # Update fields
    if update_data.title is not None:
        listing.title = update_data.title
    if update_data.description is not None:
        listing.description = update_data.description
    if update_data.price is not None:
        listing.price = update_data.price
    if update_data.category is not None:
        listing.category = update_data.category
    if update_data.condition is not None:
        listing.condition = update_data.condition
    if update_data.location is not None:
        listing.location = update_data.location
    if update_data.photos is not None:
        listing.photos = [photo.dict() for photo in update_data.photos]
    if update_data.status is not None:
        listing.status = update_data.status
    
    await db.commit()
    await db.refresh(listing)
    
    return listing


async def delete_listing(listing_id: UUID, user: User, db: AsyncSession) -> None:
    """
    Delete a listing.
    
    Args:
        listing_id: Listing UUID
        user: Current user
        db: Database session
    """
    listing = await get_listing_by_id(listing_id, user, db)
    await db.delete(listing)
    await db.commit()


async def publish_listing(
    listing_id: UUID,
    user: User,
    publish_data: PublishRequest,
    db: AsyncSession
) -> PublishResponse:
    """
    Publish listing to multiple marketplaces.
    
    Args:
        listing_id: Listing UUID
        user: Current user
        publish_data: Marketplaces to publish to
        db: Database session
        
    Returns:
        Publish results for each marketplace
    """
    listing = await get_listing_by_id(listing_id, user, db)
    
    results = []
    
    for marketplace in publish_data.marketplaces:
        # TODO: Implement actual marketplace publishing
        # For now, return mock results
        result = PublishResult(
            marketplace=marketplace,
            status="success",
            listing_url=f"https://{marketplace}.com/listing/{listing.id}",
            error=None
        )
        results.append(result)
        
        # Update listing marketplace_listings
        if not listing.marketplace_listings:
            listing.marketplace_listings = {}
        
        listing.marketplace_listings[marketplace] = {
            "id": str(listing.id),
            "url": result.listing_url,
            "status": "active"
        }
    
    # Update listing status to active
    listing.status = "active"
    
    await db.commit()
    await db.refresh(listing)
    
    return PublishResponse(results=results)
