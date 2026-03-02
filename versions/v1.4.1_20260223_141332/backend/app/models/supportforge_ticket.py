"""
SupportForge Ticket database model.
Represents support tickets/conversations.
"""
from sqlalchemy import Column, String, Integer, DateTime, func, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
import uuid
from app.database import Base


class Ticket(Base):
    """Ticket model for customer support requests."""
    
    __tablename__ = "sf_tickets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('sf_tenants.id', ondelete='CASCADE'), nullable=False)
    ticket_number = Column(Integer, nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('sf_customers.id'), nullable=False)
    assigned_agent_id = Column(UUID(as_uuid=True), ForeignKey('sf_support_agents.id'), nullable=True)
    
    subject = Column(String, nullable=False)
    status = Column(String(50), nullable=False, default='new')  # new, open, pending, resolved, closed
    priority = Column(String(20), nullable=False, default='normal')  # low, normal, high, urgent
    channel = Column(String(50), nullable=False)  # email, chat, phone, sms, portal
    tags = Column(ARRAY(String), default=[])
    category = Column(String(100))
    
    sla_policy_id = Column(UUID(as_uuid=True), nullable=True)
    
    # SLA and resolution tracking
    first_response_at = Column(TIMESTAMP(timezone=True))
    resolved_at = Column(TIMESTAMP(timezone=True))
    closed_at = Column(TIMESTAMP(timezone=True))
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Ticket #{self.ticket_number} - {self.subject}>"
