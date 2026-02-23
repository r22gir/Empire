"""
SupportForge Ticket Service.
Business logic for ticket management.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from app.models.supportforge_ticket import Ticket
from app.models.supportforge_message import Message
from app.models.supportforge_customer import Customer
from app.schemas.supportforge_ticket import TicketCreate, TicketUpdate, MessageCreate


class TicketService:
    """Service class for ticket operations."""
    
    @staticmethod
    def create_ticket(db: Session, tenant_id: UUID, ticket_data: TicketCreate, author_id: UUID) -> Ticket:
        """
        Create a new ticket with initial message.
        
        Args:
            db: Database session
            tenant_id: Tenant UUID
            ticket_data: Ticket creation data
            author_id: ID of the user/customer creating the ticket
            
        Returns:
            Created Ticket object
        """
        # Get or create customer
        customer = db.query(Customer).filter(
            and_(
                Customer.tenant_id == tenant_id,
                Customer.email == ticket_data.customer_email
            )
        ).first()
        
        if not customer:
            customer = Customer(
                tenant_id=tenant_id,
                email=ticket_data.customer_email,
                name=ticket_data.customer_name
            )
            db.add(customer)
            db.flush()
        
        # Get next ticket number for this tenant
        max_ticket_number = db.query(func.max(Ticket.ticket_number)).filter(
            Ticket.tenant_id == tenant_id
        ).scalar() or 0
        
        # Create ticket
        ticket = Ticket(
            tenant_id=tenant_id,
            ticket_number=max_ticket_number + 1,
            customer_id=customer.id,
            subject=ticket_data.subject,
            status='new',
            priority=ticket_data.priority,
            channel=ticket_data.channel,
            tags=ticket_data.tags,
            category=ticket_data.category
        )
        db.add(ticket)
        db.flush()
        
        # Create initial message
        message = Message(
            ticket_id=ticket.id,
            sender_type='customer',
            sender_id=customer.id,
            content=ticket_data.content,
            is_internal_note=False
        )
        db.add(message)
        db.commit()
        db.refresh(ticket)
        
        return ticket
    
    @staticmethod
    def get_ticket(db: Session, tenant_id: UUID, ticket_id: UUID) -> Optional[Ticket]:
        """Get a ticket by ID."""
        return db.query(Ticket).filter(
            and_(
                Ticket.id == ticket_id,
                Ticket.tenant_id == tenant_id
            )
        ).first()
    
    @staticmethod
    def list_tickets(
        db: Session,
        tenant_id: UUID,
        status: Optional[str] = None,
        assigned_agent_id: Optional[UUID] = None,
        priority: Optional[str] = None,
        page: int = 1,
        per_page: int = 50
    ):
        """
        List tickets with filtering and pagination.
        
        Returns:
            Tuple of (tickets, total_count)
        """
        query = db.query(Ticket).filter(Ticket.tenant_id == tenant_id)
        
        if status:
            query = query.filter(Ticket.status == status)
        if assigned_agent_id:
            query = query.filter(Ticket.assigned_agent_id == assigned_agent_id)
        if priority:
            query = query.filter(Ticket.priority == priority)
        
        total = query.count()
        
        tickets = query.order_by(Ticket.created_at.desc()).offset(
            (page - 1) * per_page
        ).limit(per_page).all()
        
        return tickets, total
    
    @staticmethod
    def update_ticket(
        db: Session,
        tenant_id: UUID,
        ticket_id: UUID,
        update_data: TicketUpdate
    ) -> Optional[Ticket]:
        """Update a ticket."""
        ticket = TicketService.get_ticket(db, tenant_id, ticket_id)
        if not ticket:
            return None
        
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(ticket, key, value)
        
        # Track status changes
        if update_data.status == 'resolved' and not ticket.resolved_at:
            ticket.resolved_at = datetime.utcnow()
        elif update_data.status == 'closed' and not ticket.closed_at:
            ticket.closed_at = datetime.utcnow()
        
        ticket.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(ticket)
        
        return ticket
    
    @staticmethod
    def add_message(
        db: Session,
        tenant_id: UUID,
        ticket_id: UUID,
        message_data: MessageCreate,
        sender_type: str,
        sender_id: UUID
    ) -> Optional[Message]:
        """Add a message to a ticket."""
        ticket = TicketService.get_ticket(db, tenant_id, ticket_id)
        if not ticket:
            return None
        
        message = Message(
            ticket_id=ticket_id,
            sender_type=sender_type,
            sender_id=sender_id,
            content=message_data.content,
            content_html=message_data.content_html,
            is_internal_note=message_data.is_internal_note,
            attachments=message_data.attachments
        )
        db.add(message)
        
        # Update ticket status and first response time
        if sender_type == 'agent' and not ticket.first_response_at:
            ticket.first_response_at = datetime.utcnow()
        
        if ticket.status == 'new':
            ticket.status = 'open'
        
        ticket.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(message)
        
        return message
    
    @staticmethod
    def get_ticket_messages(db: Session, tenant_id: UUID, ticket_id: UUID) -> List[Message]:
        """Get all messages for a ticket."""
        ticket = TicketService.get_ticket(db, tenant_id, ticket_id)
        if not ticket:
            return []
        
        return db.query(Message).filter(
            Message.ticket_id == ticket_id
        ).order_by(Message.created_at.asc()).all()
    
    @staticmethod
    def assign_ticket(
        db: Session,
        tenant_id: UUID,
        ticket_id: UUID,
        agent_id: UUID
    ) -> Optional[Ticket]:
        """Assign a ticket to an agent."""
        ticket = TicketService.get_ticket(db, tenant_id, ticket_id)
        if not ticket:
            return None
        
        ticket.assigned_agent_id = agent_id
        ticket.updated_at = datetime.utcnow()
        
        if ticket.status == 'new':
            ticket.status = 'open'
        
        db.commit()
        db.refresh(ticket)
        
        return ticket
