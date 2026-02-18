"""
SupportForge Tenant model for multi-tenant support organizations.
"""
from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.database import Base


class SupportForgeTenant(Base):
    """Multi-tenant support organization."""
    
    __tablename__ = "supportforge_tenants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    subdomain = Column(String, unique=True, nullable=False)  # e.g., acme.supportforge.com
    plan = Column(String, nullable=False, default="starter")  # starter, professional, enterprise
    settings = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<SupportForgeTenant {self.name} ({self.subdomain})>"
