import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class DisputeStatus(str, enum.Enum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    CLOSED = "closed"


class DisputeResolution(str, enum.Enum):
    REFUND_BUYER = "refund_buyer"
    PARTIAL_REFUND = "partial_refund"
    RELEASE_SELLER = "release_seller"
    NO_ACTION = "no_action"


class MarketFDispute(Base):
    __tablename__ = "marketf_disputes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("marketf_orders.id"), nullable=False)
    
    # Parties
    opened_by_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Details
    reason = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    evidence = Column(JSON, nullable=True)  # URLs to images, documents
    
    # Status
    status = Column(Enum(DisputeStatus), default=DisputeStatus.OPEN)
    resolution = Column(Enum(DisputeResolution), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # Admin
    admin_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
