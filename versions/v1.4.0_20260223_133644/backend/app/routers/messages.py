"""
Message routes for fetching and replying to messages.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from app.database import get_db
from app.models import User
from app.middleware import get_current_user
from app.schemas.message import MessageResponse, SendMessageRequest, AIMessageDraftResponse
from app.services.message_service import (
    get_user_messages,
    get_message_by_id,
    mark_message_read
)
from app.services.ai_service import AIService

router = APIRouter(prefix="/messages", tags=["Messages"])


@router.get("", response_model=List[MessageResponse])
async def get_messages(
    source: Optional[str] = Query("all"),
    unread: Optional[bool] = Query(None),
    limit: int = Query(50, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's messages with optional filters.
    """
    messages = await get_user_messages(current_user, db, source, unread, limit)
    return messages


@router.get("/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific message by ID.
    """
    message = await get_message_by_id(message_id, current_user, db)
    return message


@router.post("/{message_id}/read", response_model=MessageResponse)
async def read_message(
    message_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark a message as read.
    """
    message = await mark_message_read(message_id, current_user, db)
    return message


@router.post("/{message_id}/reply")
async def reply_to_message(
    message_id: UUID,
    reply_data: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Reply to a message.
    """
    message = await get_message_by_id(message_id, current_user, db)
    
    # TODO: Implement actual message sending through appropriate channel
    
    return {
        "message": "Reply sent successfully",
        "original_message_id": message_id
    }


@router.post("/{message_id}/ai-draft", response_model=AIMessageDraftResponse)
async def generate_ai_draft(
    message_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate AI draft response for a message.
    """
    message = await get_message_by_id(message_id, current_user, db)
    
    ai_service = AIService(current_user)
    draft = await ai_service.draft_message_response(message.body)
    
    return AIMessageDraftResponse(draft_response=draft)
