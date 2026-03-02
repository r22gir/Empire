"""
Message service for fetching and managing messages.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from typing import List, Optional
from uuid import UUID
from app.models import Message, User


async def get_user_messages(
    user: User,
    db: AsyncSession,
    source: Optional[str] = None,
    unread: Optional[bool] = None,
    limit: int = 50
) -> List[Message]:
    """
    Get user's messages with optional filters.
    
    Args:
        user: Current user
        db: Database session
        source: Filter by source (email, ebay, facebook, etc.)
        unread: Filter by read status
        limit: Maximum number of results
        
    Returns:
        List of messages
    """
    query = select(Message).where(Message.user_id == user.id)
    
    if source and source != "all":
        query = query.where(Message.source == source)
    
    if unread is not None:
        query = query.where(Message.is_read == (not unread))
    
    query = query.order_by(Message.received_at.desc()).limit(limit)
    
    result = await db.execute(query)
    messages = result.scalars().all()
    
    return list(messages)


async def get_message_by_id(message_id: UUID, user: User, db: AsyncSession) -> Message:
    """
    Get a specific message by ID.
    
    Args:
        message_id: Message UUID
        user: Current user
        db: Database session
        
    Returns:
        Message object
        
    Raises:
        HTTPException: If message not found or not owned by user
    """
    result = await db.execute(
        select(Message).where(Message.id == message_id, Message.user_id == user.id)
    )
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    return message


async def mark_message_read(message_id: UUID, user: User, db: AsyncSession) -> Message:
    """
    Mark a message as read.
    
    Args:
        message_id: Message UUID
        user: Current user
        db: Database session
        
    Returns:
        Updated message
    """
    message = await get_message_by_id(message_id, user, db)
    message.is_read = True
    
    await db.commit()
    await db.refresh(message)
    
    return message
