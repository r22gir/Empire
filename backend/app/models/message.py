"""
Message database model.
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, func, Text
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.database import Base


class Message(Base):
    """Unified message model for all communication sources."""
    
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    listing_id = Column(UUID(as_uuid=True), ForeignKey("listings.id"), nullable=True, index=True)
    
    # Message source and identification
    source = Column(String(50), nullable=False)  # email, ebay, facebook, etc.
    external_id = Column(String(255), nullable=True)  # ID from source platform
    
    # Sender information
    sender_name = Column(String(255), nullable=True)
    sender_email = Column(String(255), nullable=True)
    
    # Message content
    subject = Column(String(500), nullable=True)
    body = Column(Text, nullable=False)
    
    # Status and AI
    is_read = Column(Boolean, default=False)
    ai_draft_response = Column(Text, nullable=True)
    
    # Threading
    thread_id = Column(String(255), nullable=True, index=True)
    
    # Timestamps
    received_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<Message from {self.sender_name} via {self.source}>"
