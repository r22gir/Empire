"""
SupportForge Automation model for workflow automation rules.
"""
from sqlalchemy import Column, String, DateTime, Boolean, Integer, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.database import Base


class SupportForgeAutomation(Base):
    """Workflow automation rule."""
    
    __tablename__ = "supportforge_automations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("supportforge_tenants.id"), nullable=False)
    name = Column(String, nullable=False)
    trigger_type = Column(String, nullable=False)  # ticket_created, message_received, etc.
    conditions = Column(JSON, nullable=False, default=dict)
    actions = Column(JSON, nullable=False, default=list)
    is_active = Column(Boolean, default=True)
    execution_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<SupportForgeAutomation {self.name}>"
