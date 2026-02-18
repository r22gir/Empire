"""
SupportForge API routes for ticket management.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.schemas.supportforge import (
    SupportForgeTicket,
    SupportForgeTicketCreate,
    SupportForgeMessage,
    SupportForgeMessageCreate
)
from app.services.supportforge_ticket_service import TicketService


router = APIRouter()


@router.post("/", response_model=SupportForgeTicket, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    ticket_data: SupportForgeTicketCreate,
    db: Session = Depends(get_db)
):
    """Create a new support ticket."""
    try:
        ticket = TicketService.create_ticket(db, ticket_data)
        return ticket
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create ticket: {str(e)}"
        )


@router.get("/", response_model=List[SupportForgeTicket])
async def list_tickets(
    tenant_id: UUID,
    status_filter: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_agent_id: Optional[UUID] = None,
    customer_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List tickets with optional filtering."""
    tickets = TicketService.list_tickets(
        db=db,
        tenant_id=tenant_id,
        status=status_filter,
        priority=priority,
        assigned_agent_id=assigned_agent_id,
        customer_id=customer_id,
        skip=skip,
        limit=limit
    )
    return tickets


@router.get("/{ticket_id}", response_model=SupportForgeTicket)
async def get_ticket(
    ticket_id: UUID,
    db: Session = Depends(get_db)
):
    """Get ticket details by ID."""
    ticket = TicketService.get_ticket(db, ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    return ticket


@router.patch("/{ticket_id}", response_model=SupportForgeTicket)
async def update_ticket(
    ticket_id: UUID,
    updates: dict,
    db: Session = Depends(get_db)
):
    """Update ticket fields."""
    ticket = TicketService.update_ticket(db, ticket_id, updates)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    return ticket


@router.post("/{ticket_id}/assign", response_model=SupportForgeTicket)
async def assign_ticket(
    ticket_id: UUID,
    agent_id: UUID,
    db: Session = Depends(get_db)
):
    """Assign ticket to an agent."""
    ticket = TicketService.assign_ticket(db, ticket_id, agent_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    return ticket


@router.post("/{ticket_id}/messages", response_model=SupportForgeMessage, status_code=status.HTTP_201_CREATED)
async def add_message(
    ticket_id: UUID,
    message_data: SupportForgeMessageCreate,
    db: Session = Depends(get_db)
):
    """Add a message to a ticket."""
    # Verify ticket exists
    ticket = TicketService.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Ensure message is for the correct ticket
    if message_data.ticket_id != ticket_id:
        message_data.ticket_id = ticket_id
    
    try:
        message = TicketService.add_message(db, message_data)
        return message
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add message: {str(e)}"
        )


@router.get("/{ticket_id}/messages", response_model=List[SupportForgeMessage])
async def get_ticket_messages(
    ticket_id: UUID,
    include_internal: bool = False,
    db: Session = Depends(get_db)
):
    """Get all messages for a ticket."""
    # Verify ticket exists
    ticket = TicketService.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    messages = TicketService.get_ticket_messages(db, ticket_id, include_internal)
    return messages


@router.post("/{ticket_id}/tags", response_model=SupportForgeTicket)
async def add_tags(
    ticket_id: UUID,
    tags: List[str],
    db: Session = Depends(get_db)
):
    """Add tags to a ticket."""
    ticket = TicketService.add_tags(db, ticket_id, tags)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    return ticket
