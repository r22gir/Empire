"""
Listing schemas for requests and responses.
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from uuid import UUID


class PhotoSchema(BaseModel):
    """Photo information."""
    url: str
    thumbnail_url: str


class ListingBase(BaseModel):
    """Base listing schema."""
    title: str
    description: Optional[str] = None
    price: Decimal
    category: Optional[str] = None
    condition: Optional[str] = None
    location: Optional[str] = None


class ListingCreate(ListingBase):
    """Schema for creating a listing."""
    photos: Optional[List[PhotoSchema]] = []


class ListingUpdate(BaseModel):
    """Schema for updating a listing."""
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    category: Optional[str] = None
    condition: Optional[str] = None
    location: Optional[str] = None
    photos: Optional[List[PhotoSchema]] = None
    status: Optional[str] = None


class ListingResponse(ListingBase):
    """Listing response schema."""
    id: UUID
    user_id: UUID
    photos: List[dict]
    status: str
    marketplace_listings: dict
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class PublishRequest(BaseModel):
    """Request to publish listing to marketplaces."""
    marketplaces: List[str]  # ["ebay", "facebook", "craigslist"]


class PublishResult(BaseModel):
    """Result of publishing to one marketplace."""
    marketplace: str
    status: str  # success, failed
    listing_url: Optional[str] = None
    error: Optional[str] = None


class PublishResponse(BaseModel):
    """Response for publishing to multiple marketplaces."""
    results: List[PublishResult]
