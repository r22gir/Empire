"""
SupportForge Message model for ticket conversations.
"""
from sqlalchemy import Column, String, DateTime, Boolean, JSON, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.database import Base


class SupportForgeMessage(Base):
    """Ticket conversation message."""
    
    __tablename__ = "supportforge_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("supportforge_tickets.id"), nullable=False)
    sender_type = Column(String, nullable=False)  # customer, agent, system
    sender_id = Column(UUID(as_uuid=True))  # Agent or Customer ID
    content = Column(Text, nullable=False)
    content_html = Column(Text)
    is_internal_note = Column(Boolean, default=False)
    attachments = Column(JSON, default=list)
    ai_suggested = Column(Boolean, default=False)  # Was this an AI suggestion?
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<SupportForgeMessage from {self.sender_type}>"
