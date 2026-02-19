from sqlalchemy import Column, String, Integer, DateTime, Float, Boolean
from app.database import Base
from datetime import datetime
import uuid

class PreOrder(Base):
    __tablename__ = "preorders"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Customer info
    customer_email = Column(String, nullable=False, index=True)
    customer_name = Column(String, nullable=False)
    customer_phone = Column(String, nullable=True)
    
    # Shipping address
    shipping_street1 = Column(String, nullable=False)
    shipping_street2 = Column(String, nullable=True)
    shipping_city = Column(String, nullable=False)
    shipping_state = Column(String, nullable=False)
    shipping_zip = Column(String, nullable=False)
    shipping_country = Column(String, default="US")
    
    # Bundle info
    bundle_type = Column(String, nullable=False)  # seeker_pro, budget_mobile, full_empire
    quantity = Column(Integer, default=1)
    
    # Pricing
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    
    # Payment
    stripe_payment_intent_id = Column(String, nullable=True)
    payment_status = Column(String, default="pending")  # pending, paid, refunded
    
    # Status
    fulfillment_status = Column(String, default="pending")  # pending, processing, shipped, delivered
    tracking_number = Column(String, nullable=True)
    
    # License key
    license_key = Column(String, nullable=True)  # Generated license key for this order
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)
    shipped_at = Column(DateTime, nullable=True)
    
    # Metadata
    notes = Column(String, nullable=True)
