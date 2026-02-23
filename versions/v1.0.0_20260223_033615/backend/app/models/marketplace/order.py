import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class OrderStatus(str, enum.Enum):
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"


class EscrowStatus(str, enum.Enum):
    PENDING = "pending"
    HELD = "held"
    PARTIAL_RELEASE = "partial_release"
    RELEASED = "released"
    REFUNDED = "refunded"


class MarketFOrder(Base):
    __tablename__ = "marketf_orders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_number = Column(String(20), unique=True, nullable=False)
    
    # Parties
    buyer_id = Column(UUID(as_uuid=True), nullable=False)
    seller_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Product
    product_id = Column(UUID(as_uuid=True), ForeignKey("marketf_products.id"), nullable=False)
    product_title = Column(String(255), nullable=False)
    product_price = Column(Float, nullable=False)
    
    # Shipping
    shipping_price = Column(Float, nullable=False)
    shipping_address = Column(JSON, nullable=False)
    tracking_number = Column(String(100), nullable=True)
    carrier = Column(String(50), nullable=True)
    shipment_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Fees
    subtotal = Column(Float, nullable=False)
    marketplace_fee = Column(Float, nullable=False)
    payment_processing_fee = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    seller_payout = Column(Float, nullable=False)
    
    # Escrow
    escrow_status = Column(Enum(EscrowStatus), default=EscrowStatus.PENDING)
    escrow_held_at = Column(DateTime, nullable=True)
    escrow_released_at = Column(DateTime, nullable=True)
    
    # Status
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING_PAYMENT)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)
    shipped_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    product = relationship("MarketFProduct", back_populates="orders")
    reviews = relationship("MarketFReview", back_populates="order")
    escrow = relationship("Escrow", back_populates="order", uselist=False)
