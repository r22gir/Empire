"""
Pydantic schemas for SupportForge Ticket API.
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# Ticket schemas
class TicketCreate(BaseModel):
    """Schema for creating a new ticket."""
    customer_email: Optional[EmailStr] = None
    customer_name: Optional[str] = None
    subject: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    channel: str = Field(default="portal", pattern="^(email|chat|phone|sms|portal|family-help)$")
    priority: str = Field(default="normal", pattern="^(low|normal|medium|high|urgent)$")
    tags: List[str] = Field(default=[])
    category: Optional[str] = None


class TicketUpdate(BaseModel):
    """Schema for updating a ticket."""
    subject: Optional[str] = Field(None, min_length=1, max_length=500)
    status: Optional[str] = Field(None, pattern="^(new|open|pending|progress|in_progress|waiting|resolved|closed)$")
    priority: Optional[str] = Field(None, pattern="^(low|normal|medium|high|urgent)$")
    assigned_agent_id: Optional[UUID] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    proposed_action_status: Optional[str] = Field(
        None, pattern="^(proposed|accepted|rejected|completed)$"
    )


class MessageCreate(BaseModel):
    """Schema for creating a message."""
    content: str = Field(..., min_length=1)
    content_html: Optional[str] = None
    is_internal_note: bool = False
    attachments: List[dict] = Field(default=[])


class TicketResponse(BaseModel):
    """Schema for ticket response."""
    id: str
    tenant_id: Optional[str] = None
    ticket_number: int
    customer_id: Optional[str] = None
    assigned_agent_id: Optional[str] = None
    subject: str
    content: Optional[str] = None
    status: str
    priority: str
    channel: str
    tags: List[str] = []
    category: Optional[str] = None
    source: Optional[str] = None
    edition_id: Optional[str] = None
    family_help_request_id: Optional[str] = None
    proposed_action: Optional[str] = None
    proposed_action_summary: Optional[str] = None
    proposed_action_status: Optional[str] = None
    auto_build: bool = False
    first_response_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Schema for message response."""
    id: UUID
    ticket_id: UUID
    sender_type: str
    sender_id: UUID
    content: str
    content_html: Optional[str]
    is_internal_note: bool
    attachments: List[dict]
    ai_suggested: bool
    ai_confidence: Optional[float]
    created_at: datetime
    
    class Config:
        from_attributes = True


class TicketDetailResponse(BaseModel):
    """Schema for detailed ticket response with messages."""
    ticket: TicketResponse
    messages: List[MessageResponse]
    customer: dict
    assigned_agent: Optional[dict]


class TicketListResponse(BaseModel):
    """Schema for paginated ticket list."""
    tickets: List[TicketResponse]
    total: int
    page: int
    per_page: int
    pages: int
