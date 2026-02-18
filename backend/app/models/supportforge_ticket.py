"""
SupportForge Ticket model for support ticket records.
"""
from sqlalchemy import Column, String, DateTime, Integer, ARRAY, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class SupportForgeTicket(Base):
    """Support ticket record."""
    
    __tablename__ = "supportforge_tickets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("supportforge_tenants.id"), nullable=False)
    ticket_number = Column(Integer, nullable=False)  # Human-readable #1234
    customer_id = Column(UUID(as_uuid=True), ForeignKey("supportforge_customers.id"), nullable=False)
    assigned_agent_id = Column(UUID(as_uuid=True), ForeignKey("supportforge_agents.id"))
    subject = Column(String, nullable=False)
    status = Column(String, nullable=False, default="new")  # new, open, pending, resolved, closed
    priority = Column(String, nullable=False, default="normal")  # urgent, high, normal, low
    channel = Column(String, nullable=False)  # email, chat, sms, api, widget
    tags = Column(ARRAY(String), default=list)
    category = Column(String)
    sla_policy_id = Column(UUID(as_uuid=True), ForeignKey("supportforge_sla_policies.id"))
    first_response_at = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))
    closed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<SupportForgeTicket #{self.ticket_number}: {self.subject}>"
