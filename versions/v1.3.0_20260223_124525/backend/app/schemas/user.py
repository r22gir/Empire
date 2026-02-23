"""
User schemas for requests and responses.
"""
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    name: str


class UserCreate(UserBase):
    """Schema for creating a user."""
    password: str


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    name: Optional[str] = None
    notification_settings: Optional[dict] = None


class UserResponse(UserBase):
    """User response schema."""
    id: UUID
    marketforge_email: Optional[str] = None
    tier: str
    tokens_used_this_month: int
    tokens_limit: int = 0
    created_at: datetime
    
    class Config:
        from_attributes = True


class SubscriptionInfo(BaseModel):
    """User subscription information."""
    tier: str
    tokens_used: int
    tokens_limit: int
    percent_used: float
    renewal_date: Optional[datetime] = None


class SubscriptionUpgrade(BaseModel):
    """Request to upgrade subscription."""
    new_tier: str
    payment_method_id: str
