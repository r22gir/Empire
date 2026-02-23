"""
SupportForge Automation and SLA database models.
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, func, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.database import Base


class Automation(Base):
    """Automation rule model for workflow automation."""
    
    __tablename__ = "sf_automations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('sf_tenants.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    trigger_type = Column(String(50), nullable=False)  # ticket_created, ticket_updated, message_received
    conditions = Column(JSONB, nullable=False, default=[])
    actions = Column(JSONB, nullable=False, default=[])
    is_active = Column(Boolean, default=True)
    execution_count = Column(Integer, default=0)
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<Automation {self.name}>"


class SLAPolicy(Base):
    """SLA policy model for service level agreements."""
    
    __tablename__ = "sf_sla_policies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('sf_tenants.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    first_response_minutes = Column(Integer, nullable=False)
    resolution_minutes = Column(Integer, nullable=False)
    business_hours_only = Column(Boolean, default=True)
    priority_multipliers = Column(JSONB, default={})
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<SLAPolicy {self.name}>"


class CannedResponse(Base):
    """Canned response model for quick replies."""
    
    __tablename__ = "sf_canned_responses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('sf_tenants.id', ondelete='CASCADE'), nullable=False)
    title = Column(String(255), nullable=False)
    shortcut = Column(String(50))
    content = Column(String, nullable=False)
    category = Column(String(100))
    created_by = Column(UUID(as_uuid=True), ForeignKey('sf_support_agents.id'), nullable=False)
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<CannedResponse {self.title}>"
