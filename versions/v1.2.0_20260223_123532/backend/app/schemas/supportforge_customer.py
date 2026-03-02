"""
Pydantic schemas for SupportForge Customer API.
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict
from datetime import datetime
from uuid import UUID


class CustomerCreate(BaseModel):
    """Schema for creating a customer."""
    email: EmailStr
    name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    empire_product_type: Optional[str] = None
    empire_product_id: Optional[UUID] = None
    custom_metadata: Dict = Field(default={}, alias="metadata")
    tags: List[str] = Field(default=[])


class CustomerUpdate(BaseModel):
    """Schema for updating a customer."""
    name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    custom_metadata: Optional[Dict] = Field(None, alias="metadata")
    tags: Optional[List[str]] = None


class CustomerResponse(BaseModel):
    """Schema for customer response."""
    id: UUID
    tenant_id: UUID
    email: str
    name: Optional[str]
    phone: Optional[str]
    company: Optional[str]
    empire_product_type: Optional[str]
    empire_product_id: Optional[UUID]
    custom_metadata: Dict = Field(alias="metadata")
    tags: List[str]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class CustomerListResponse(BaseModel):
    """Schema for paginated customer list."""
    customers: List[CustomerResponse]
    total: int
    page: int
    per_page: int
    pages: int
