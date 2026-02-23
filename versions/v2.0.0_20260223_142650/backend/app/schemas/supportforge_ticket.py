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
    customer_email: EmailStr
    customer_name: Optional[str] = None
    subject: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    channel: str = Field(default="portal", pattern="^(email|chat|phone|sms|portal)$")
    priority: str = Field(default="normal", pattern="^(low|normal|high|urgent)$")
    tags: List[str] = Field(default=[])
    category: Optional[str] = None


class TicketUpdate(BaseModel):
    """Schema for updating a ticket."""
    subject: Optional[str] = Field(None, min_length=1, max_length=500)
    status: Optional[str] = Field(None, pattern="^(new|open|pending|resolved|closed)$")
    priority: Optional[str] = Field(None, pattern="^(low|normal|high|urgent)$")
    assigned_agent_id: Optional[UUID] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None


class MessageCreate(BaseModel):
    """Schema for creating a message."""
    content: str = Field(..., min_length=1)
    content_html: Optional[str] = None
    is_internal_note: bool = False
    attachments: List[dict] = Field(default=[])


class TicketResponse(BaseModel):
    """Schema for ticket response."""
    id: UUID
    tenant_id: UUID
    ticket_number: int
    customer_id: UUID
    assigned_agent_id: Optional[UUID]
    subject: str
    status: str
    priority: str
    channel: str
    tags: List[str]
    category: Optional[str]
    first_response_at: Optional[datetime]
    resolved_at: Optional[datetime]
    closed_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    
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
