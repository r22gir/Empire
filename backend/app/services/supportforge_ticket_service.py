"""
Ticket service for SupportForge - handles ticket creation, management, and assignment.
"""
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from app.models.supportforge_ticket import SupportForgeTicket
from app.models.supportforge_message import SupportForgeMessage
from app.schemas.supportforge import (
    SupportForgeTicketCreate,
    SupportForgeMessageCreate
)


class TicketService:
    """Service for managing support tickets."""
    
    @staticmethod
    def create_ticket(db: Session, ticket_data: SupportForgeTicketCreate) -> SupportForgeTicket:
        """Create a new support ticket."""
        # Get next ticket number for this tenant
        last_ticket = db.query(SupportForgeTicket).filter(
            SupportForgeTicket.tenant_id == ticket_data.tenant_id
        ).order_by(desc(SupportForgeTicket.ticket_number)).first()
        
        next_ticket_number = (last_ticket.ticket_number + 1) if last_ticket else 1
        
        ticket = SupportForgeTicket(
            tenant_id=ticket_data.tenant_id,
            ticket_number=next_ticket_number,
            customer_id=ticket_data.customer_id,
            subject=ticket_data.subject,
            status=ticket_data.status,
            priority=ticket_data.priority,
            channel=ticket_data.channel,
            tags=ticket_data.tags,
            category=ticket_data.category,
            assigned_agent_id=ticket_data.assigned_agent_id,
            sla_policy_id=ticket_data.sla_policy_id
        )
        
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        
        return ticket
    
    @staticmethod
    def get_ticket(db: Session, ticket_id: UUID) -> Optional[SupportForgeTicket]:
        """Get ticket by ID."""
        return db.query(SupportForgeTicket).filter(
            SupportForgeTicket.id == ticket_id
        ).first()
    
    @staticmethod
    def list_tickets(
        db: Session,
        tenant_id: UUID,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_agent_id: Optional[UUID] = None,
        customer_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[SupportForgeTicket]:
        """List tickets with filtering and pagination."""
        query = db.query(SupportForgeTicket).filter(
            SupportForgeTicket.tenant_id == tenant_id
        )
        
        if status:
            query = query.filter(SupportForgeTicket.status == status)
        if priority:
            query = query.filter(SupportForgeTicket.priority == priority)
        if assigned_agent_id:
            query = query.filter(SupportForgeTicket.assigned_agent_id == assigned_agent_id)
        if customer_id:
            query = query.filter(SupportForgeTicket.customer_id == customer_id)
        
        return query.order_by(desc(SupportForgeTicket.created_at)).offset(skip).limit(limit).all()
    
    @staticmethod
    def update_ticket(
        db: Session,
        ticket_id: UUID,
        updates: Dict[str, Any]
    ) -> Optional[SupportForgeTicket]:
        """Update ticket fields."""
        ticket = db.query(SupportForgeTicket).filter(
            SupportForgeTicket.id == ticket_id
        ).first()
        
        if not ticket:
            return None
        
        for key, value in updates.items():
            if hasattr(ticket, key):
                setattr(ticket, key, value)
        
        # Set timestamps based on status changes
        if "status" in updates:
            if updates["status"] == "resolved" and not ticket.resolved_at:
                ticket.resolved_at = datetime.utcnow()
            elif updates["status"] == "closed" and not ticket.closed_at:
                ticket.closed_at = datetime.utcnow()
        
        db.commit()
        db.refresh(ticket)
        
        return ticket
    
    @staticmethod
    def assign_ticket(
        db: Session,
        ticket_id: UUID,
        agent_id: UUID
    ) -> Optional[SupportForgeTicket]:
        """Assign ticket to an agent."""
        return TicketService.update_ticket(db, ticket_id, {
            "assigned_agent_id": agent_id,
            "status": "open" if db.query(SupportForgeTicket).filter(
                SupportForgeTicket.id == ticket_id
            ).first().status == "new" else None
        })
    
    @staticmethod
    def add_message(
        db: Session,
        message_data: SupportForgeMessageCreate
    ) -> SupportForgeMessage:
        """Add a message to a ticket."""
        message = SupportForgeMessage(
            ticket_id=message_data.ticket_id,
            sender_type=message_data.sender_type,
            sender_id=message_data.sender_id,
            content=message_data.content,
            content_html=message_data.content_html,
            is_internal_note=message_data.is_internal_note,
            attachments=message_data.attachments,
            ai_suggested=message_data.ai_suggested
        )
        
        db.add(message)
        
        # Update first_response_at if this is the first agent response
        if message_data.sender_type == "agent":
            ticket = db.query(SupportForgeTicket).filter(
                SupportForgeTicket.id == message_data.ticket_id
            ).first()
            
            if ticket and not ticket.first_response_at:
                ticket.first_response_at = datetime.utcnow()
        
        db.commit()
        db.refresh(message)
        
        return message
    
    @staticmethod
    def get_ticket_messages(
        db: Session,
        ticket_id: UUID,
        include_internal: bool = False
    ) -> List[SupportForgeMessage]:
        """Get all messages for a ticket."""
        query = db.query(SupportForgeMessage).filter(
            SupportForgeMessage.ticket_id == ticket_id
        )
        
        if not include_internal:
            query = query.filter(SupportForgeMessage.is_internal_note == False)
        
        return query.order_by(SupportForgeMessage.created_at).all()
    
    @staticmethod
    def add_tags(db: Session, ticket_id: UUID, tags: List[str]) -> Optional[SupportForgeTicket]:
        """Add tags to a ticket."""
        ticket = db.query(SupportForgeTicket).filter(
            SupportForgeTicket.id == ticket_id
        ).first()
        
        if not ticket:
            return None
        
        # Merge new tags with existing, avoiding duplicates
        current_tags = set(ticket.tags or [])
        current_tags.update(tags)
        ticket.tags = list(current_tags)
        
        db.commit()
        db.refresh(ticket)
        
        return ticket
