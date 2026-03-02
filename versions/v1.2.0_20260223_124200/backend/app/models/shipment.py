from sqlalchemy import Column, String, Integer, DateTime, Float, Boolean
from app.database import Base
from datetime import datetime
import uuid

class Shipment(Base):
    __tablename__ = "shipments"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    
    # Addresses
    from_name = Column(String, nullable=False)
    from_street1 = Column(String, nullable=False)
    from_street2 = Column(String, nullable=True)
    from_city = Column(String, nullable=False)
    from_state = Column(String, nullable=False)
    from_zip = Column(String, nullable=False)
    from_country = Column(String, default="US")
    
    to_name = Column(String, nullable=False)
    to_street1 = Column(String, nullable=False)
    to_street2 = Column(String, nullable=True)
    to_city = Column(String, nullable=False)
    to_state = Column(String, nullable=False)
    to_zip = Column(String, nullable=False)
    to_country = Column(String, default="US")
    
    # Package details
    length = Column(Float, nullable=False)  # inches
    width = Column(Float, nullable=False)  # inches
    height = Column(Float, nullable=False)  # inches
    weight = Column(Float, nullable=False)  # ounces
    
    # Shipping details
    carrier = Column(String, nullable=False)  # USPS, FedEx, UPS
    service = Column(String, nullable=False)  # Priority, Ground, etc.
    tracking_number = Column(String, nullable=False, unique=True)
    
    # Label URLs
    label_url = Column(String, nullable=False)
    label_pdf_url = Column(String, nullable=False)
    
    # Costs
    base_rate = Column(Float, nullable=False)
    our_price = Column(Float, nullable=False)
    
    # EasyPost IDs
    easypost_shipment_id = Column(String, nullable=False)
    easypost_rate_id = Column(String, nullable=False)
    
    # Status
    status = Column(String, default="pending")  # pending, in_transit, delivered, returned
    
    # Metadata
    listing_id = Column(String, nullable=True)  # If linked to a marketplace listing
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
