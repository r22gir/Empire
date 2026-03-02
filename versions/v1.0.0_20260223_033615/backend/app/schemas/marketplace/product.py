from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class ProductBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    category_id: UUID
    condition: str = Field(..., pattern="^(new|like_new|good|fair|poor)$")
    price: float = Field(..., gt=0)
    shipping_price: Optional[float] = Field(None, ge=0)
    offers_enabled: bool = False
    minimum_offer: Optional[float] = Field(None, gt=0)
    images: List[str] = []
    package_weight_oz: int = Field(..., gt=0)
    package_length_in: int = Field(..., gt=0)
    package_width_in: int = Field(..., gt=0)
    package_height_in: int = Field(..., gt=0)
    ships_from_zip: str = Field(..., pattern=r"^\d{5}$")
    quantity: int = Field(default=1, ge=1)


class ProductCreate(ProductBase):
    marketforge_listing_id: Optional[UUID] = None


class ProductUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    category_id: Optional[UUID] = None
    condition: Optional[str] = Field(None, pattern="^(new|like_new|good|fair|poor)$")
    price: Optional[float] = Field(None, gt=0)
    shipping_price: Optional[float] = Field(None, ge=0)
    offers_enabled: Optional[bool] = None
    minimum_offer: Optional[float] = Field(None, gt=0)
    images: Optional[List[str]] = None
    package_weight_oz: Optional[int] = Field(None, gt=0)
    package_length_in: Optional[int] = Field(None, gt=0)
    package_width_in: Optional[int] = Field(None, gt=0)
    package_height_in: Optional[int] = Field(None, gt=0)
    ships_from_zip: Optional[str] = Field(None, pattern=r"^\d{5}$")
    quantity: Optional[int] = Field(None, ge=1)
    status: Optional[str] = Field(None, pattern="^(draft|active|sold|removed)$")


class ProductResponse(ProductBase):
    id: UUID
    seller_id: UUID
    marketforge_listing_id: Optional[UUID] = None
    status: str
    views: int
    favorites: int
    created_at: datetime
    updated_at: datetime
    sold_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class ProductListResponse(BaseModel):
    products: List[ProductResponse]
    total: int
    page: int
    pages: int
