"""
SupportForge Ticket API Router.
Handles ticket-related HTTP endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
import math

from app.database import get_db
from app.schemas.supportforge_ticket import (
    TicketCreate, TicketUpdate, TicketResponse, TicketListResponse,
    MessageCreate, MessageResponse, TicketDetailResponse
)
from app.services.supportforge_ticket import TicketService
from app.services.supportforge_customer import CustomerService
from app.models.supportforge_agent import SupportAgent

router = APIRouter()


# Mock function to get current tenant - replace with actual auth
def get_current_tenant_id() -> UUID:
    """Get current tenant ID from authentication context."""
    # TODO: Implement actual authentication and tenant extraction
    return UUID("00000000-0000-0000-0000-000000000001")


# Mock function to get current user - replace with actual auth
def get_current_user():
    """Get current authenticated user."""
    # TODO: Implement actual authentication
    return {
        "id": UUID("00000000-0000-0000-0000-000000000001"),
        "type": "agent"  # or "customer"
    }


@router.post("/", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(
    ticket_data: TicketCreate,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new support ticket.
    
    Creates a ticket with an initial message from the customer.
    """
    try:
        ticket = TicketService.create_ticket(
            db=db,
            tenant_id=tenant_id,
            ticket_data=ticket_data,
            author_id=current_user["id"]
        )
        return ticket
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create ticket: {str(e)}"
        )


@router.get("/", response_model=TicketListResponse)
def list_tickets(
    status: Optional[str] = None,
    assigned_agent_id: Optional[UUID] = None,
    priority: Optional[str] = None,
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id)
):
    """
    List tickets with optional filtering and pagination.
    
    Query parameters:
    - status: Filter by ticket status (new, open, pending, resolved, closed)
    - assigned_agent_id: Filter by assigned agent
    - priority: Filter by priority (low, normal, high, urgent)
    - page: Page number (default: 1)
    - per_page: Items per page (default: 50, max: 100)
    """
    if per_page > 100:
        per_page = 100
    
    tickets, total = TicketService.list_tickets(
        db=db,
        tenant_id=tenant_id,
        status=status,
        assigned_agent_id=assigned_agent_id,
        priority=priority,
        page=page,
        per_page=per_page
    )
    
    return {
        "tickets": tickets,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": math.ceil(total / per_page) if total > 0 else 1
    }


@router.get("/{ticket_id}", response_model=TicketDetailResponse)
def get_ticket(
    ticket_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id)
):
    """
    Get detailed ticket information including messages.
    """
    ticket = TicketService.get_ticket(db, tenant_id, ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    messages = TicketService.get_ticket_messages(db, tenant_id, ticket_id)
    customer = CustomerService.get_customer(db, tenant_id, ticket.customer_id)
    
    assigned_agent = None
    if ticket.assigned_agent_id:
        agent = db.query(SupportAgent).filter(
            SupportAgent.id == ticket.assigned_agent_id
        ).first()
        if agent:
            assigned_agent = {
                "id": agent.id,
                "name": agent.name,
                "email": agent.email,
                "avatar_url": agent.avatar_url
            }
    
    return {
        "ticket": ticket,
        "messages": messages,
        "customer": {
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "company": customer.company,
            "phone": customer.phone
        } if customer else None,
        "assigned_agent": assigned_agent
    }


@router.patch("/{ticket_id}", response_model=TicketResponse)
def update_ticket(
    ticket_id: UUID,
    update_data: TicketUpdate,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id)
):
    """
    Update ticket properties (status, priority, assignment, etc.).
    """
    ticket = TicketService.update_ticket(db, tenant_id, ticket_id, update_data)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    return ticket


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket(
    ticket_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id)
):
    """
    Delete a ticket (soft delete).
    """
    ticket = TicketService.get_ticket(db, tenant_id, ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Soft delete by setting status to closed
    ticket.status = 'closed'
    ticket.closed_at = None  # Mark as deleted
    db.commit()


@router.post("/{ticket_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def add_message(
    ticket_id: UUID,
    message_data: MessageCreate,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """
    Add a message to a ticket.
    """
    message = TicketService.add_message(
        db=db,
        tenant_id=tenant_id,
        ticket_id=ticket_id,
        message_data=message_data,
        sender_type=current_user["type"],
        sender_id=current_user["id"]
    )
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    return message


@router.post("/{ticket_id}/assign", response_model=TicketResponse)
def assign_ticket(
    ticket_id: UUID,
    agent_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id)
):
    """
    Assign a ticket to a support agent.
    """
    # Verify agent exists and belongs to tenant
    agent = db.query(SupportAgent).filter(
        SupportAgent.id == agent_id,
        SupportAgent.tenant_id == tenant_id
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    ticket = TicketService.assign_ticket(db, tenant_id, ticket_id, agent_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    return ticket


@router.post("/{ticket_id}/tags", response_model=TicketResponse)
def update_ticket_tags(
    ticket_id: UUID,
    tags: List[str],
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id)
):
    """
    Update ticket tags.
    """
    ticket = TicketService.get_ticket(db, tenant_id, ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    ticket.tags = tags
    db.commit()
    db.refresh(ticket)
    
    return ticket
