"""
SupportForge SLA Policy model for service level agreements.
"""
from sqlalchemy import Column, String, DateTime, Boolean, Integer, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.database import Base


class SupportForgeSLAPolicy(Base):
    """Service level agreement policy."""
    
    __tablename__ = "supportforge_sla_policies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("supportforge_tenants.id"), nullable=False)
    name = Column(String, nullable=False)
    first_response_time_minutes = Column(Integer, nullable=False)
    resolution_time_minutes = Column(Integer, nullable=False)
    business_hours_only = Column(Boolean, default=False)
    priority_multipliers = Column(JSON, default=dict)  # e.g., {"urgent": 0.5, "high": 0.75}
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<SupportForgeSLAPolicy {self.name}>"
