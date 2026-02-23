import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class EscrowStatusEnum(str, enum.Enum):
    HELD = "held"
    PARTIAL = "partial"
    RELEASED = "released"
    REFUNDED = "refunded"
    DISPUTED = "disputed"


class Escrow(Base):
    __tablename__ = "escrows"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("marketf_orders.id"), nullable=False)
    
    # Amounts
    total_amount = Column(Float, nullable=False)
    released_amount = Column(Float, default=0.0)
    refunded_amount = Column(Float, default=0.0)
    
    # Stripe
    payment_intent_id = Column(String(255), nullable=False)
    transfer_id = Column(String(255), nullable=True)
    
    # Status
    status = Column(Enum(EscrowStatusEnum), default=EscrowStatusEnum.HELD)
    
    # Events (audit log)
    events = Column(JSON, default=[])
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    order = relationship("MarketFOrder", back_populates="escrow")
