"""
Customer service for SupportForge - manages customer records and context.
"""
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.models.supportforge_customer import SupportForgeCustomer
from app.schemas.supportforge import SupportForgeCustomerCreate


class CustomerService:
    """Service for managing support customers."""
    
    @staticmethod
    def create_customer(
        db: Session,
        customer_data: SupportForgeCustomerCreate
    ) -> SupportForgeCustomer:
        """Create a new customer."""
        customer = SupportForgeCustomer(
            tenant_id=customer_data.tenant_id,
            email=customer_data.email,
            name=customer_data.name,
            phone=customer_data.phone,
            company=customer_data.company,
            empire_product_id=customer_data.empire_product_id,
            empire_product_type=customer_data.empire_product_type,
            metadata=customer_data.metadata,
            tags=customer_data.tags
        )
        
        db.add(customer)
        db.commit()
        db.refresh(customer)
        
        return customer
    
    @staticmethod
    def get_customer(db: Session, customer_id: UUID) -> Optional[SupportForgeCustomer]:
        """Get customer by ID."""
        return db.query(SupportForgeCustomer).filter(
            SupportForgeCustomer.id == customer_id
        ).first()
    
    @staticmethod
    def get_customer_by_email(
        db: Session,
        tenant_id: UUID,
        email: str
    ) -> Optional[SupportForgeCustomer]:
        """Get customer by email within a tenant."""
        return db.query(SupportForgeCustomer).filter(
            SupportForgeCustomer.tenant_id == tenant_id,
            SupportForgeCustomer.email == email
        ).first()
    
    @staticmethod
    def get_or_create_customer(
        db: Session,
        tenant_id: UUID,
        email: str,
        name: str,
        **kwargs
    ) -> SupportForgeCustomer:
        """Get existing customer or create new one."""
        customer = CustomerService.get_customer_by_email(db, tenant_id, email)
        
        if customer:
            return customer
        
        customer_data = SupportForgeCustomerCreate(
            tenant_id=tenant_id,
            email=email,
            name=name,
            **kwargs
        )
        
        return CustomerService.create_customer(db, customer_data)
    
    @staticmethod
    def list_customers(
        db: Session,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 50
    ) -> List[SupportForgeCustomer]:
        """List customers for a tenant."""
        return db.query(SupportForgeCustomer).filter(
            SupportForgeCustomer.tenant_id == tenant_id
        ).offset(skip).limit(limit).all()
    
    @staticmethod
    def update_customer(
        db: Session,
        customer_id: UUID,
        updates: Dict[str, Any]
    ) -> Optional[SupportForgeCustomer]:
        """Update customer information."""
        customer = db.query(SupportForgeCustomer).filter(
            SupportForgeCustomer.id == customer_id
        ).first()
        
        if not customer:
            return None
        
        for key, value in updates.items():
            if hasattr(customer, key):
                setattr(customer, key, value)
        
        db.commit()
        db.refresh(customer)
        
        return customer
    
    @staticmethod
    async def get_empire_product_context(
        db: Session,
        customer_id: UUID
    ) -> Dict[str, Any]:
        """
        Get customer's Empire product context (ContractorForge, etc.).
        
        This would integrate with other Empire services to fetch:
        - Project history
        - Payment status
        - Usage metrics
        - Feature flags
        """
        customer = CustomerService.get_customer(db, customer_id)
        
        if not customer or not customer.empire_product_id:
            return {
                "has_empire_product": False,
                "message": "No Empire product linked"
            }
        
        # Placeholder - would make actual API calls to Empire products
        return {
            "has_empire_product": True,
            "product_type": customer.empire_product_type,
            "product_id": str(customer.empire_product_id),
            "subscription_status": "active",
            "projects_count": 5,
            "recent_activity": "Last login 2 hours ago",
            "usage_this_month": {
                "ai_requests": 150,
                "cost": 12.50
            }
        }
