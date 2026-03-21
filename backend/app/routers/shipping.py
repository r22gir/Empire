# STATUS: PLACEHOLDER — This module contains scaffold endpoints only.
# Real integration pending: EasyPost API (rates, label purchase, tracking all return simulated data).
# The ShippingService uses hardcoded test rates and fake tracking events.
# To activate: set EASYPOST_API_KEY and EASYPOST_TEST_MODE=false in .env,
# then implement real easypost SDK calls in services/shipping_service.py.

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.schemas.shipment import (
    RateRequest,
    RateResponse,
    LabelPurchaseRequest,
    ShipmentLabel,
    TrackingInfo,
    EmailLabelRequest
)
from app.services.shipping_service import ShippingService

router = APIRouter()
shipping_service = ShippingService()

@router.post("/rates", response_model=RateResponse)
async def get_shipping_rates(
    rate_request: RateRequest,
    db: Session = Depends(get_db)
):
    """
    Get shipping rates from multiple carriers
    """
    rates = await shipping_service.get_rates(
        rate_request.from_address,
        rate_request.to_address,
        rate_request.parcel
    )
    
    return RateResponse(rates=rates)

@router.post("/labels", response_model=ShipmentLabel)
async def purchase_label(
    purchase_request: LabelPurchaseRequest,
    user_id: str = "test_user",  # In production, get from authenticated user
    db: Session = Depends(get_db)
):
    """
    Purchase a shipping label
    """
    # In a real implementation, we would need to store the addresses and parcel
    # from the rate request. For now, using dummy data.
    from app.schemas.shipment import Address, Parcel
    
    # This would come from the stored rate request
    from_address = Address(
        name="Test Seller",
        street1="123 Main St",
        city="Los Angeles",
        state="CA",
        zip="90001"
    )
    
    to_address = Address(
        name="Test Buyer",
        street1="456 Oak Ave",
        city="New York",
        state="NY",
        zip="10001"
    )
    
    parcel = Parcel(
        length=10.0,
        width=8.0,
        height=6.0,
        weight=16.0
    )
    
    shipment = await shipping_service.purchase_label(
        db=db,
        user_id=user_id,
        shipment_id=purchase_request.shipment_id,
        rate_id=purchase_request.rate_id,
        from_address=from_address,
        to_address=to_address,
        parcel=parcel,
        listing_id=purchase_request.listing_id
    )
    
    return shipment

@router.get("/labels/{label_id}", response_model=ShipmentLabel)
async def get_label(
    label_id: str,
    db: Session = Depends(get_db)
):
    """
    Get label details
    """
    from app.models.shipment import Shipment
    
    shipment = db.query(Shipment).filter(Shipment.id == label_id).first()
    
    if not shipment:
        raise HTTPException(status_code=404, detail="Label not found")
    
    return shipment

@router.get("/track/{tracking_number}", response_model=TrackingInfo)
async def track_shipment(
    tracking_number: str
):
    """
    Track a shipment
    """
    tracking_info = await shipping_service.track_shipment(tracking_number)
    return tracking_info

@router.get("/history", response_model=List[ShipmentLabel])
async def get_shipment_history(
    user_id: str = "test_user",  # In production, get from authenticated user
    limit: int = 50,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get shipment history for user
    """
    shipments = await shipping_service.get_user_shipments(
        db, user_id, limit, status
    )
    return shipments

@router.post("/labels/{label_id}/email")
async def email_label(
    label_id: str,
    email_request: EmailLabelRequest,
    db: Session = Depends(get_db)
):
    """
    Email label PDF to user
    """
    from app.models.shipment import Shipment
    
    shipment = db.query(Shipment).filter(Shipment.id == label_id).first()
    
    if not shipment:
        raise HTTPException(status_code=404, detail="Label not found")
    
    # TODO: Implement email sending
    # For now, just return success
    
    return {
        "sent": True,
        "email": email_request.email,
        "label_url": shipment.label_pdf_url
    }
