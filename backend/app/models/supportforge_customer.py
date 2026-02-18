"""
SupportForge Customer model for end customers seeking support.
"""
from sqlalchemy import Column, String, DateTime, JSON, ARRAY, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.database import Base


class SupportForgeCustomer(Base):
    """End customer seeking support."""
    
    __tablename__ = "supportforge_customers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("supportforge_tenants.id"), nullable=False)
    email = Column(String, nullable=False)
    name = Column(String, nullable=False)
    phone = Column(String)
    company = Column(String)
    empire_product_id = Column(UUID(as_uuid=True))  # Link to Empire product user
    empire_product_type = Column(String)  # e.g., 'contractorforge', 'marketforge'
    metadata = Column(JSON, default=dict)
    tags = Column(ARRAY(String), default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<SupportForgeCustomer {self.name} ({self.email})>"
