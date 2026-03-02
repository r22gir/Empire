"""
SupportForge Customer database model.
Represents customers who submit support tickets.
"""
from sqlalchemy import Column, String, DateTime, func, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
import uuid
from app.database import Base


class Customer(Base):
    """Customer model for support ticket submitters."""
    
    __tablename__ = "sf_customers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('sf_tenants.id', ondelete='CASCADE'), nullable=False)
    email = Column(String(255), nullable=False)
    name = Column(String(255))
    phone = Column(String(50))
    company = Column(String(255))
    
    # Integration with other Empire products
    empire_product_type = Column(String(100))  # contractorforge, marketforge, etc.
    empire_product_id = Column(UUID(as_uuid=True))
    
    # Additional data and tags
    custom_metadata = Column('metadata', JSONB, default={})
    tags = Column(ARRAY(String), default=[])
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Customer {self.name} ({self.email})>"
