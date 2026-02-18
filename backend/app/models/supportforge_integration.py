"""
SupportForge Integration model for connected Empire products.
"""
from sqlalchemy import Column, String, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.database import Base


class SupportForgeIntegration(Base):
    """Connected Empire product integration."""
    
    __tablename__ = "supportforge_integrations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("supportforge_tenants.id"), nullable=False)
    integration_type = Column(String, nullable=False)  # contractorforge, marketforge, custom_api
    config = Column(JSON, nullable=False, default=dict)
    api_key = Column(String)
    webhook_url = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<SupportForgeIntegration {self.integration_type}>"
