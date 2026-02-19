from sqlalchemy import Column, String, Integer, DateTime, Boolean, Float
from app.database import Base
from datetime import datetime
import uuid

class License(Base):
    __tablename__ = "licenses"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    key = Column(String, unique=True, nullable=False, index=True)
    
    # What this license grants
    plan = Column(String, nullable=False)  # free, lite, pro, empire
    duration_months = Column(Integer, nullable=False)  # 1, 6, 12
    hardware_bundle = Column(String, nullable=True)  # seeker_pro, budget_mobile, full_empire, None
    
    # Status tracking
    status = Column(String, default="pending")  # pending, activated, expired, revoked
    created_at = Column(DateTime, default=datetime.utcnow)
    activated_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    
    # Links
    user_id = Column(String, nullable=True)  # Set when activated
    preorder_id = Column(String, nullable=True)  # If from pre-order
    
    # Metadata
    notes = Column(String, nullable=True)  # Admin notes
