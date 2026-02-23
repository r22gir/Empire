from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class Address(BaseModel):
    name: str
    street1: str
    street2: Optional[str] = None
    city: str
    state: str
    zip: str
    country: str = "US"

class Parcel(BaseModel):
    length: float = Field(..., description="Length in inches")
    width: float = Field(..., description="Width in inches")
    height: float = Field(..., description="Height in inches")
    weight: float = Field(..., description="Weight in ounces")

class ShippingRate(BaseModel):
    carrier: str
    service: str
    rate: float
    our_price: float
    delivery_days: Optional[int]
    shipment_id: str
    rate_id: str

class RateRequest(BaseModel):
    from_address: Address
    to_address: Address
    parcel: Parcel

class RateResponse(BaseModel):
    rates: List[ShippingRate]

class LabelPurchaseRequest(BaseModel):
    shipment_id: str
    rate_id: str
    listing_id: Optional[str] = None

class ShipmentLabel(BaseModel):
    id: str
    tracking_number: str
    label_url: str
    label_pdf_url: str
    carrier: str
    service: str
    our_price: float
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class TrackingEvent(BaseModel):
    datetime: str
    message: str
    city: Optional[str]
    state: Optional[str]

class TrackingInfo(BaseModel):
    status: str
    status_detail: Optional[str]
    events: List[TrackingEvent]

class EmailLabelRequest(BaseModel):
    email: str
