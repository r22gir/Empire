from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class OrderCreate(BaseModel):
    product_id: UUID
    shipping_address: Dict[str, Any] = Field(..., description="Buyer's shipping address")
    payment_method_id: Optional[str] = None


class OrderUpdate(BaseModel):
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(pending_payment|paid|shipped|delivered|completed|cancelled|disputed)$")


class OrderResponse(BaseModel):
    id: UUID
    order_number: str
    buyer_id: UUID
    seller_id: UUID
    product_id: UUID
    product_title: str
    product_price: float
    shipping_price: float
    shipping_address: Dict[str, Any]
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    shipment_id: Optional[UUID] = None
    subtotal: float
    marketplace_fee: float
    payment_processing_fee: float
    total: float
    seller_payout: float
    escrow_status: str
    escrow_held_at: Optional[datetime] = None
    escrow_released_at: Optional[datetime] = None
    status: str
    created_at: datetime
    paid_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class ShipOrderRequest(BaseModel):
    tracking_number: str = Field(..., min_length=1)
    carrier: str = Field(..., min_length=1)


class OrderListResponse(BaseModel):
    orders: list[OrderResponse]
    total: int
    page: int
    pages: int
