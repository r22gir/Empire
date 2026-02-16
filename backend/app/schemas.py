from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# User Schemas
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# Listing Schemas
class ListingBase(BaseModel):
    title: str
    description: str
    price: float

class ListingCreate(ListingBase):
    platforms: List[str]  # ["ebay", "facebook", "poshmark", "mercari", "craigslist"]

class Listing(ListingBase):
    id: int
    user_id: int
    photo_url: str
    posted_ebay: bool
    posted_facebook: bool
    posted_poshmark: bool
    posted_mercari: bool
    posted_craigslist: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Sale Schemas
class SaleBase(BaseModel):
    platform: str
    sale_price: float

class SaleCreate(SaleBase):
    listing_id: int

class Sale(SaleBase):
    id: int
    user_id: int
    listing_id: int
    commission: float
    commission_paid: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Marketplace Credentials
class MarketplaceCredentials(BaseModel):
    ebay_token: Optional[str] = None
    facebook_token: Optional[str] = None
    poshmark_credentials: Optional[str] = None
    mercari_token: Optional[str] = None

# Dashboard Data
class DashboardData(BaseModel):
    total_listings: int
    total_sales: int
    total_earned: float
    commission_paid: float
    recent_listings: List[Listing]
    recent_sales: List[Sale]
