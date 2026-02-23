from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import Optional

class PreOrderBase(BaseModel):
    customer_email: EmailStr
    customer_name: str
    customer_phone: Optional[str] = None
    
    shipping_street1: str
    shipping_street2: Optional[str] = None
    shipping_city: str
    shipping_state: str
    shipping_zip: str
    shipping_country: str = "US"
    
    bundle_type: str = Field(..., description="seeker_pro, budget_mobile, or full_empire")
    quantity: int = Field(1, ge=1)

class PreOrderCreate(PreOrderBase):
    pass

class PreOrderResponse(PreOrderBase):
    id: str
    unit_price: float
    total_price: float
    stripe_payment_intent_id: Optional[str]
    payment_status: str
    fulfillment_status: str
    tracking_number: Optional[str]
    license_key: Optional[str]
    created_at: datetime
    paid_at: Optional[datetime]
    shipped_at: Optional[datetime]
    notes: Optional[str]
    
    class Config:
        from_attributes = True

class PreOrderUpdate(BaseModel):
    payment_status: Optional[str] = None
    fulfillment_status: Optional[str] = None
    tracking_number: Optional[str] = None
    license_key: Optional[str] = None
    notes: Optional[str] = None
