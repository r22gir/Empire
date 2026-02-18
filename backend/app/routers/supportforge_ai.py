"""
SupportForge API routes for AI-powered features.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from uuid import UUID
from pydantic import BaseModel

from app.database import get_db
from app.services.supportforge_ai_service import AIService
from app.services.supportforge_ticket_service import TicketService


router = APIRouter()
ai_service = AIService()


class SuggestResponseRequest(BaseModel):
    """Request model for AI response suggestion."""
    ticket_id: UUID
    customer_context: Optional[Dict[str, Any]] = None


class CategorizeRequest(BaseModel):
    """Request model for ticket categorization."""
    subject: str
    content: str


class SentimentRequest(BaseModel):
    """Request model for sentiment analysis."""
    text: str


class SummarizeRequest(BaseModel):
    """Request model for conversation summarization."""
    ticket_id: UUID


class KBSearchRequest(BaseModel):
    """Request model for knowledge base search."""
    query: str
    limit: int = 5


@router.post("/suggest-response")
async def suggest_response(
    request: SuggestResponseRequest,
    db: Session = Depends(get_db)
):
    """
    Get AI-powered response suggestion for a ticket.
    
    Returns suggested responses based on ticket context and conversation history.
    """
    # Get ticket details
    ticket = TicketService.get_ticket(db, request.ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Get conversation history
    messages = TicketService.get_ticket_messages(db, request.ticket_id)
    conversation_history = [
        {
            "sender_type": msg.sender_type,
            "content": msg.content
        }
        for msg in messages
    ]
    
    # Generate suggestion
    try:
        suggestion = await ai_service.suggest_response(
            ticket_subject=ticket.subject,
            conversation_history=conversation_history,
            customer_context=request.customer_context
        )
        return suggestion
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate response suggestion: {str(e)}"
        )


@router.post("/categorize")
async def categorize_ticket(request: CategorizeRequest):
    """
    Auto-categorize a ticket based on its content.
    
    Returns suggested category, tags, and priority.
    """
    try:
        result = await ai_service.categorize_ticket(
            subject=request.subject,
            content=request.content
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to categorize ticket: {str(e)}"
        )


@router.post("/sentiment")
async def analyze_sentiment(request: SentimentRequest):
    """
    Analyze sentiment of customer message.
    
    Returns sentiment analysis including frustration detection.
    """
    try:
        result = await ai_service.analyze_sentiment(request.text)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze sentiment: {str(e)}"
        )


@router.post("/summarize")
async def summarize_conversation(
    request: SummarizeRequest,
    db: Session = Depends(get_db)
):
    """
    Summarize a ticket conversation.
    
    Returns a summary with key points and resolution status.
    """
    # Get ticket messages
    ticket = TicketService.get_ticket(db, request.ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    messages = TicketService.get_ticket_messages(db, request.ticket_id)
    message_list = [
        {
            "sender_type": msg.sender_type,
            "content": msg.content
        }
        for msg in messages
    ]
    
    try:
        summary = await ai_service.summarize_conversation(message_list)
        return summary
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to summarize conversation: {str(e)}"
        )


@router.post("/search-kb")
async def search_knowledge_base(request: KBSearchRequest):
    """
    Search knowledge base for relevant articles.
    
    Returns suggested articles based on query.
    """
    try:
        results = await ai_service.search_knowledge_base(
            query=request.query,
            limit=request.limit
        )
        return {"results": results}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search knowledge base: {str(e)}"
        )
