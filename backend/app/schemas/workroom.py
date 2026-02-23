"""
Pydantic schemas for Workroom Forge API.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date


# ---------- Client schemas ----------

class ClientBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class ClientResponse(ClientBase):
    id: int
    total_orders: int
    total_spent: float
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------- Order schemas ----------

class OrderBase(BaseModel):
    product: str = Field(..., min_length=1, max_length=500)
    status: str = Field(default="pending")
    due_date: Optional[date] = None
    total: float = Field(default=0.0, ge=0)
    notes: Optional[str] = None
    images: Optional[str] = None  # JSON-encoded list of image URLs
    client_id: Optional[int] = None


class OrderCreate(OrderBase):
    pass


class OrderUpdate(BaseModel):
    product: Optional[str] = Field(None, min_length=1, max_length=500)
    status: Optional[str] = None
    due_date: Optional[date] = None
    total: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None
    images: Optional[str] = None
    client_id: Optional[int] = None


class OrderResponse(OrderBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------- Stats schema ----------

class WorkroomStats(BaseModel):
    total_orders: int
    pending_orders: int
    in_progress_orders: int
    completed_orders: int
    total_revenue: float
    total_clients: int
