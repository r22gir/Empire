"""
SupportForge Agent model for support team members.
"""
from sqlalchemy import Column, String, DateTime, Integer, ARRAY, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class SupportForgeAgent(Base):
    """Support team member."""
    
    __tablename__ = "supportforge_agents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("supportforge_tenants.id"), nullable=False)
    email = Column(String, nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False, default="agent")  # admin, agent, viewer
    departments = Column(ARRAY(String), default=list)
    skills = Column(ARRAY(String), default=list)
    status = Column(String, nullable=False, default="offline")  # online, away, offline
    max_concurrent_tickets = Column(Integer, default=10)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<SupportForgeAgent {self.name} ({self.email})>"
