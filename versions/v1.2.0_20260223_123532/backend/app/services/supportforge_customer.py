"""
SupportForge Customer Service.
Business logic for customer management.
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, List
from uuid import UUID

from app.models.supportforge_customer import Customer
from app.models.supportforge_ticket import Ticket
from app.schemas.supportforge_customer import CustomerCreate, CustomerUpdate


class CustomerService:
    """Service class for customer operations."""
    
    @staticmethod
    def create_customer(db: Session, tenant_id: UUID, customer_data: CustomerCreate) -> Customer:
        """Create a new customer."""
        customer = Customer(
            tenant_id=tenant_id,
            email=customer_data.email,
            name=customer_data.name,
            phone=customer_data.phone,
            company=customer_data.company,
            empire_product_type=customer_data.empire_product_type,
            empire_product_id=customer_data.empire_product_id,
            custom_metadata=customer_data.custom_metadata,
            tags=customer_data.tags
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        
        return customer
    
    @staticmethod
    def get_customer(db: Session, tenant_id: UUID, customer_id: UUID) -> Optional[Customer]:
        """Get a customer by ID."""
        return db.query(Customer).filter(
            and_(
                Customer.id == customer_id,
                Customer.tenant_id == tenant_id
            )
        ).first()
    
    @staticmethod
    def get_customer_by_email(db: Session, tenant_id: UUID, email: str) -> Optional[Customer]:
        """Get a customer by email."""
        return db.query(Customer).filter(
            and_(
                Customer.email == email,
                Customer.tenant_id == tenant_id
            )
        ).first()
    
    @staticmethod
    def list_customers(
        db: Session,
        tenant_id: UUID,
        search: Optional[str] = None,
        page: int = 1,
        per_page: int = 50
    ):
        """
        List customers with search and pagination.
        
        Returns:
            Tuple of (customers, total_count)
        """
        query = db.query(Customer).filter(Customer.tenant_id == tenant_id)
        
        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                (Customer.email.ilike(search_filter)) |
                (Customer.name.ilike(search_filter)) |
                (Customer.company.ilike(search_filter))
            )
        
        total = query.count()
        
        customers = query.order_by(Customer.created_at.desc()).offset(
            (page - 1) * per_page
        ).limit(per_page).all()
        
        return customers, total
    
    @staticmethod
    def update_customer(
        db: Session,
        tenant_id: UUID,
        customer_id: UUID,
        update_data: CustomerUpdate
    ) -> Optional[Customer]:
        """Update a customer."""
        customer = CustomerService.get_customer(db, tenant_id, customer_id)
        if not customer:
            return None
        
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(customer, key, value)
        
        db.commit()
        db.refresh(customer)
        
        return customer
    
    @staticmethod
    def get_customer_tickets(db: Session, tenant_id: UUID, customer_id: UUID) -> List[Ticket]:
        """Get all tickets for a customer."""
        customer = CustomerService.get_customer(db, tenant_id, customer_id)
        if not customer:
            return []
        
        return db.query(Ticket).filter(
            and_(
                Ticket.customer_id == customer_id,
                Ticket.tenant_id == tenant_id
            )
        ).order_by(Ticket.created_at.desc()).all()
    
    @staticmethod
    def delete_customer(db: Session, tenant_id: UUID, customer_id: UUID) -> bool:
        """Delete a customer (soft delete by removing from tenant)."""
        customer = CustomerService.get_customer(db, tenant_id, customer_id)
        if not customer:
            return False
        
        # Check if customer has any tickets
        tickets_count = db.query(Ticket).filter(
            Ticket.customer_id == customer_id
        ).count()
        
        if tickets_count > 0:
            # Don't delete if customer has tickets
            return False
        
        db.delete(customer)
        db.commit()
        
        return True
