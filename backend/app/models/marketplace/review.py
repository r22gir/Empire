import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class ReviewType(str, enum.Enum):
    BUYER_TO_SELLER = "buyer_to_seller"
    SELLER_TO_BUYER = "seller_to_buyer"


class MarketFReview(Base):
    __tablename__ = "marketf_reviews"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("marketf_orders.id"), nullable=False)
    
    # Who is reviewing whom
    reviewer_id = Column(UUID(as_uuid=True), nullable=False)
    reviewee_id = Column(UUID(as_uuid=True), nullable=False)
    review_type = Column(Enum(ReviewType), nullable=False)
    
    # Content
    rating = Column(Integer, nullable=False)  # 1-5
    title = Column(String(255), nullable=True)
    comment = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    order = relationship("MarketFOrder", back_populates="reviews")
