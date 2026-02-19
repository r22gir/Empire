"""
Message schemas for requests and responses.
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class MessageResponse(BaseModel):
    """Message response schema."""
    id: UUID
    user_id: UUID
    listing_id: Optional[UUID] = None
    source: str
    sender_name: Optional[str] = None
    sender_email: Optional[str] = None
    subject: Optional[str] = None
    body: str
    is_read: bool
    ai_draft_response: Optional[str] = None
    thread_id: Optional[str] = None
    received_at: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


class SendMessageRequest(BaseModel):
    """Request to send/reply to a message."""
    body: str
    use_ai_draft: bool = False


class AIMessageDraftResponse(BaseModel):
    """AI-generated message draft."""
    draft_response: str
