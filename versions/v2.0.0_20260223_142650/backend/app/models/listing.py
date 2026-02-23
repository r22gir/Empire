"""
Listing database model.
"""
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, func, Text
from sqlalchemy.dialects.postgresql import UUID, JSON
import uuid
from app.database import Base


class Listing(Base):
    """Product listing model."""
    
    __tablename__ = "listings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Product details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    category = Column(String(100), nullable=True)
    condition = Column(String(50), nullable=True)  # new, like_new, good, fair, poor
    location = Column(String(255), nullable=True)
    
    # Photos stored as JSON array: [{ url, thumbnail_url }]
    photos = Column(JSON, default=list)
    
    # Status
    status = Column(String(50), default="draft")  # draft, active, sold, archived
    
    # Marketplace listings as JSON: { ebay: { id, url, status }, facebook: {...} }
    marketplace_listings = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Listing {self.title}>"
