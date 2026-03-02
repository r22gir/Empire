"""
SupportForge Support Agent database model.
Represents customer support agents within a tenant organization.
"""
from sqlalchemy import Column, String, Integer, DateTime, func, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class SupportAgent(Base):
    """Support agent model for handling customer tickets."""
    
    __tablename__ = "sf_support_agents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('sf_tenants.id', ondelete='CASCADE'), nullable=False)
    email = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default='agent')  # agent, admin, supervisor
    departments = Column(ARRAY(String), default=[])
    skills = Column(ARRAY(String), default=[])
    status = Column(String(20), default='offline')  # online, offline, away, busy
    max_concurrent_tickets = Column(Integer, default=10)
    avatar_url = Column(String)
    
    # Timestamps
    last_active_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<SupportAgent {self.name} ({self.email})>"
