from typing import List, Optional
import os
from app.models.shipment import Shipment
from app.schemas.shipment import Address, Parcel, ShippingRate, TrackingInfo, TrackingEvent
from sqlalchemy.orm import Session

# Note: EasyPost integration is simulated here for development
# In production, import easypost and use real API calls

class ShippingService:
    def __init__(self):
        self.easypost_api_key = os.getenv("EASYPOST_API_KEY", "test_key")
        self.test_mode = os.getenv("EASYPOST_TEST_MODE", "true").lower() == "true"
    
    async def get_rates(
        self,
        from_address: Address,
        to_address: Address,
        parcel: Parcel
    ) -> List[ShippingRate]:
        """
        Compare rates from USPS, FedEx, UPS
        Returns sorted by price (cheapest first)
        
        In production, this would use:
        import easypost
        easypost.api_key = self.easypost_api_key
        shipment = easypost.Shipment.create(...)
        """
        
        # Simulated rates for development
        if self.test_mode:
            # Calculate base rate based on weight and distance estimate
            base_rate = 5.0 + (parcel.weight / 16) * 2.0
            
            rates = [
                ShippingRate(
                    carrier="USPS",
                    service="Priority Mail",
                    rate=base_rate + 3.0,
                    our_price=self.calculate_markup(base_rate + 3.0),
                    delivery_days=2,
                    shipment_id="shp_test_123",
                    rate_id="rate_usps_priority"
                ),
                ShippingRate(
                    carrier="USPS",
                    service="First Class",
                    rate=base_rate,
                    our_price=self.calculate_markup(base_rate),
                    delivery_days=4,
                    shipment_id="shp_test_123",
                    rate_id="rate_usps_first"
                ),
                ShippingRate(
                    carrier="UPS",
                    service="Ground",
                    rate=base_rate + 4.5,
                    our_price=self.calculate_markup(base_rate + 4.5),
                    delivery_days=5,
                    shipment_id="shp_test_123",
                    rate_id="rate_ups_ground"
                ),
                ShippingRate(
                    carrier="FedEx",
                    service="Home Delivery",
                    rate=base_rate + 5.0,
                    our_price=self.calculate_markup(base_rate + 5.0),
                    delivery_days=5,
                    shipment_id="shp_test_123",
                    rate_id="rate_fedex_home"
                ),
            ]
            
            return sorted(rates, key=lambda r: r.our_price)
        
        # TODO: Production EasyPost implementation
        # shipment = easypost.Shipment.create(
        #     from_address=from_address.dict(),
        #     to_address=to_address.dict(),
        #     parcel=parcel.dict()
        # )
        # ...
        
        return []
    
    def calculate_markup(self, base_rate: float) -> float:
        """
        Add our margin to the rate
        We get ~15% discount from EasyPost, pass half to user
        Example: $10 label, we pay $8.50, charge $9.25
        User saves $0.75, we profit $0.75
        """
        discount_rate = base_rate * 0.85  # Our cost
        markup = (base_rate - discount_rate) * 0.5  # Half the savings
        return round(discount_rate + markup, 2)
    
    async def purchase_label(
        self,
        db: Session,
        user_id: str,
        shipment_id: str,
        rate_id: str,
        from_address: Address,
        to_address: Address,
        parcel: Parcel,
        listing_id: Optional[str] = None
    ) -> Shipment:
        """
        Purchase the selected rate and get label
        
        In production:
        shipment = easypost.Shipment.retrieve(shipment_id)
        shipment.buy(rate={'id': rate_id})
        """
        
        # Simulated label purchase for development
        if self.test_mode:
            import uuid
            tracking_number = f"EZ{random.randint(1000000000, 9999999999)}"
            
            # Determine carrier and service from rate_id
            carrier = "USPS"
            service = "Priority Mail"
            cost = 8.45
            
            if "ups" in rate_id:
                carrier = "UPS"
                service = "Ground"
                cost = 9.20
            elif "fedex" in rate_id:
                carrier = "FedEx"
                service = "Home Delivery"
                cost = 9.50
            
            shipment = Shipment(
                user_id=user_id,
                from_name=from_address.name,
                from_street1=from_address.street1,
                from_street2=from_address.street2,
                from_city=from_address.city,
                from_state=from_address.state,
                from_zip=from_address.zip,
                from_country=from_address.country,
                to_name=to_address.name,
                to_street1=to_address.street1,
                to_street2=to_address.street2,
                to_city=to_address.city,
                to_state=to_address.state,
                to_zip=to_address.zip,
                to_country=to_address.country,
                length=parcel.length,
                width=parcel.width,
                height=parcel.height,
                weight=parcel.weight,
                carrier=carrier,
                service=service,
                tracking_number=tracking_number,
                label_url=f"https://example.com/labels/{tracking_number}.png",
                label_pdf_url=f"https://example.com/labels/{tracking_number}.pdf",
                base_rate=cost,
                our_price=self.calculate_markup(cost),
                easypost_shipment_id=shipment_id,
                easypost_rate_id=rate_id,
                status="pending",
                listing_id=listing_id
            )
            
            db.add(shipment)
            db.commit()
            db.refresh(shipment)
            
            return shipment
        
        # TODO: Production EasyPost implementation
        return None
    
    async def track_shipment(self, tracking_number: str) -> TrackingInfo:
        """
        Get tracking updates for a shipment
        
        In production:
        tracker = easypost.Tracker.create(tracking_code=tracking_number)
        """
        
        # Simulated tracking for development
        if self.test_mode:
            return TrackingInfo(
                status="in_transit",
                status_detail="Package is in transit",
                events=[
                    TrackingEvent(
                        datetime="2026-02-16T10:30:00Z",
                        message="Shipment information received",
                        city="Los Angeles",
                        state="CA"
                    ),
                    TrackingEvent(
                        datetime="2026-02-16T14:00:00Z",
                        message="Package picked up",
                        city="Los Angeles",
                        state="CA"
                    ),
                    TrackingEvent(
                        datetime="2026-02-17T08:00:00Z",
                        message="In transit",
                        city="Phoenix",
                        state="AZ"
                    ),
                ]
            )
        
        # TODO: Production EasyPost implementation
        return TrackingInfo(status="unknown", status_detail="Tracking not available", events=[])
    
    async def get_user_shipments(
        self,
        db: Session,
        user_id: str,
        limit: int = 50,
        status: Optional[str] = None
    ) -> List[Shipment]:
        """
        Get shipment history for a user
        """
        query = db.query(Shipment).filter(Shipment.user_id == user_id)
        
        if status:
            query = query.filter(Shipment.status == status)
        
        return query.order_by(Shipment.created_at.desc()).limit(limit).all()

import random
