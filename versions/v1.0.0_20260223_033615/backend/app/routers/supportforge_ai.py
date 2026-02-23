"""
SupportForge AI API Router.
AI-powered features endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict
from uuid import UUID

from app.database import get_db
from app.services.supportforge_ai import ai_service
from app.services.supportforge_ticket import TicketService
from pydantic import BaseModel, Field

router = APIRouter()


# Mock function to get current tenant - replace with actual auth
def get_current_tenant_id() -> UUID:
    """Get current tenant ID from authentication context."""
    return UUID("00000000-0000-0000-0000-000000000001")


# Request/Response schemas

class SuggestResponseRequest(BaseModel):
    """Request schema for AI response suggestion."""
    ticket_id: UUID
    conversation_history: List[Dict] = Field(default=[])


class CategorizeRequest(BaseModel):
    """Request schema for ticket categorization."""
    subject: str
    content: str


class SentimentRequest(BaseModel):
    """Request schema for sentiment analysis."""
    content: str


class SummarizeRequest(BaseModel):
    """Request schema for ticket summarization."""
    ticket_id: UUID


class KBSearchRequest(BaseModel):
    """Request schema for AI-powered KB search."""
    query: str
    max_results: int = Field(default=5, ge=1, le=20)


# Endpoints

@router.post("/suggest-response")
def suggest_response(
    request: SuggestResponseRequest,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id)
):
    """
    Get AI-suggested response for a ticket.
    
    Uses GPT-4 to analyze the ticket and conversation history
    to generate a helpful response suggestion.
    """
    # Get ticket details
    ticket = TicketService.get_ticket(db, tenant_id, request.ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Get messages
    messages = TicketService.get_ticket_messages(db, tenant_id, request.ticket_id)
    
    # Get first message for context
    first_message = messages[0] if messages else None
    ticket_content = first_message.content if first_message else ""
    
    # Generate suggestion
    suggestion = ai_service.suggest_response(
        ticket_subject=ticket.subject,
        ticket_content=ticket_content,
        conversation_history=request.conversation_history
    )
    
    return suggestion


@router.post("/categorize")
def categorize_ticket(request: CategorizeRequest):
    """
    Auto-categorize a ticket based on its content.
    
    Uses AI to analyze the ticket and suggest an appropriate category.
    """
    result = ai_service.categorize_ticket(
        subject=request.subject,
        content=request.content
    )
    
    return result


@router.post("/sentiment")
def analyze_sentiment(request: SentimentRequest):
    """
    Analyze the sentiment of a message.
    
    Detects positive, neutral, or negative sentiment and urgency level.
    Useful for prioritizing tickets and identifying upset customers.
    """
    result = ai_service.analyze_sentiment(content=request.content)
    
    return result


@router.post("/summarize")
def summarize_ticket(
    request: SummarizeRequest,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id)
):
    """
    Generate a summary of a ticket conversation.
    
    Useful for quickly understanding long ticket threads.
    """
    # Get ticket
    ticket = TicketService.get_ticket(db, tenant_id, request.ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Get all messages
    messages = TicketService.get_ticket_messages(db, tenant_id, request.ticket_id)
    
    # Convert to dict format
    message_dicts = [
        {
            "content": msg.content,
            "sender_type": msg.sender_type,
            "created_at": str(msg.created_at)
        }
        for msg in messages
    ]
    
    # Generate summary
    summary = ai_service.summarize_ticket(messages=message_dicts)
    
    return summary


@router.post("/search-kb")
def search_kb(request: KBSearchRequest):
    """
    AI-powered semantic search of the knowledge base.
    
    Uses embeddings and vector search for better results than keyword matching.
    For production, implement with OpenAI embeddings + vector database.
    """
    result = ai_service.search_kb(
        query=request.query,
        max_results=request.max_results
    )
    
    return result
