"""
SupportForge Message database model.
Represents individual messages within a ticket conversation.
"""
from sqlalchemy import Column, String, Boolean, Numeric, DateTime, func, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.database import Base


class Message(Base):
    """Message model for ticket conversation threads."""
    
    __tablename__ = "sf_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey('sf_tickets.id', ondelete='CASCADE'), nullable=False)
    sender_type = Column(String(20), nullable=False)  # customer, agent, system
    sender_id = Column(UUID(as_uuid=True), nullable=False)
    
    content = Column(String, nullable=False)
    content_html = Column(String)
    is_internal_note = Column(Boolean, default=False)
    attachments = Column(JSONB, default=[])
    
    # AI-related fields
    ai_suggested = Column(Boolean, default=False)
    ai_confidence = Column(Numeric(5, 2))  # 0.00 to 100.00
    
    # Timestamp
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<Message from {self.sender_type} in ticket {self.ticket_id}>"
