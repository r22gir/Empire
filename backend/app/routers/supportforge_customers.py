"""
SupportForge Customer API Router.
Handles customer-related HTTP endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
import math

from app.database import get_db
from app.schemas.supportforge_customer import (
    CustomerCreate, CustomerUpdate, CustomerResponse, CustomerListResponse
)
from app.schemas.supportforge_ticket import TicketResponse
from app.services.supportforge_customer import CustomerService

router = APIRouter()


# Founder tenant ID — used when no JWT is present (single-tenant / founder mode)
FOUNDER_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")


def get_current_tenant_id() -> UUID:
    """Extract tenant ID from JWT token, fallback to founder tenant."""
    try:
        from fastapi import Request
        from app.middleware.auth import decode_token
        # In production, this reads from the request's Authorization header
        # For now, founder mode returns the default tenant
        return FOUNDER_TENANT_ID
    except Exception:
        return FOUNDER_TENANT_ID


@router.post("/", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(
    customer_data: CustomerCreate,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id)
):
    """
    Create a new customer.
    """
    # Check if customer already exists
    existing = CustomerService.get_customer_by_email(db, tenant_id, customer_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer with this email already exists"
        )
    
    customer = CustomerService.create_customer(db, tenant_id, customer_data)
    return customer


@router.get("/", response_model=CustomerListResponse)
def list_customers(
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id)
):
    """
    List customers with optional search and pagination.
    
    Query parameters:
    - search: Search by email, name, or company
    - page: Page number (default: 1)
    - per_page: Items per page (default: 50, max: 100)
    """
    if per_page > 100:
        per_page = 100
    
    customers, total = CustomerService.list_customers(
        db=db,
        tenant_id=tenant_id,
        search=search,
        page=page,
        per_page=per_page
    )
    
    return {
        "customers": customers,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": math.ceil(total / per_page) if total > 0 else 1
    }


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id)
):
    """
    Get customer details by ID.
    """
    customer = CustomerService.get_customer(db, tenant_id, customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    return customer


@router.patch("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: UUID,
    update_data: CustomerUpdate,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id)
):
    """
    Update customer information.
    """
    customer = CustomerService.update_customer(db, tenant_id, customer_id, update_data)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(
    customer_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id)
):
    """
    Delete a customer (only if they have no tickets).
    """
    success = CustomerService.delete_customer(db, tenant_id, customer_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete customer with existing tickets"
        )


@router.get("/{customer_id}/tickets", response_model=list[TicketResponse])
def get_customer_tickets(
    customer_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id)
):
    """
    Get all tickets for a specific customer.
    """
    tickets = CustomerService.get_customer_tickets(db, tenant_id, customer_id)
    return tickets


@router.get("/{customer_id}/context")
def get_customer_context(
    customer_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id)
):
    """
    Get customer context including Empire product integration data.
    
    This endpoint integrates with other Empire products (ContractorForge, etc.)
    to provide additional context about the customer.
    """
    customer = CustomerService.get_customer(db, tenant_id, customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    # Build customer context
    context = {
        "customer": {
            "id": customer.id,
            "email": customer.email,
            "name": customer.name,
            "company": customer.company,
            "phone": customer.phone,
            "tags": customer.tags,
            "metadata": customer.custom_metadata
        },
        "empire_integration": None
    }
    
    # If customer is linked to an Empire product, fetch additional context
    if customer.empire_product_type and customer.empire_product_id:
        # TODO: Implement integration with Empire products
        context["empire_integration"] = {
            "product": customer.empire_product_type,
            "product_id": customer.empire_product_id,
            "note": "Integration with Empire products coming soon"
        }
    
    # Get ticket statistics
    tickets = CustomerService.get_customer_tickets(db, tenant_id, customer_id)
    context["ticket_stats"] = {
        "total": len(tickets),
        "open": len([t for t in tickets if t.status in ['new', 'open', 'pending']]),
        "closed": len([t for t in tickets if t.status in ['resolved', 'closed']])
    }
    
    return context
