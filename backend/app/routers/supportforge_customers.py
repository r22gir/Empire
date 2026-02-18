"""
SupportForge API routes for customer management.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.schemas.supportforge import (
    SupportForgeCustomer,
    SupportForgeCustomerCreate
)
from app.services.supportforge_customer_service import CustomerService
from app.services.supportforge_ticket_service import TicketService


router = APIRouter()


@router.post("/", response_model=SupportForgeCustomer, status_code=status.HTTP_201_CREATED)
async def create_customer(
    customer_data: SupportForgeCustomerCreate,
    db: Session = Depends(get_db)
):
    """Create a new customer."""
    try:
        customer = CustomerService.create_customer(db, customer_data)
        return customer
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create customer: {str(e)}"
        )


@router.get("/", response_model=List[SupportForgeCustomer])
async def list_customers(
    tenant_id: UUID,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List customers for a tenant."""
    customers = CustomerService.list_customers(db, tenant_id, skip, limit)
    return customers


@router.get("/{customer_id}", response_model=SupportForgeCustomer)
async def get_customer(
    customer_id: UUID,
    db: Session = Depends(get_db)
):
    """Get customer details by ID."""
    customer = CustomerService.get_customer(db, customer_id)
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    return customer


@router.patch("/{customer_id}", response_model=SupportForgeCustomer)
async def update_customer(
    customer_id: UUID,
    updates: dict,
    db: Session = Depends(get_db)
):
    """Update customer information."""
    customer = CustomerService.update_customer(db, customer_id, updates)
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    return customer


@router.get("/{customer_id}/tickets")
async def get_customer_tickets(
    customer_id: UUID,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get all tickets for a customer."""
    # Verify customer exists
    customer = CustomerService.get_customer(db, customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    tickets = TicketService.list_tickets(
        db=db,
        tenant_id=customer.tenant_id,
        customer_id=customer_id,
        skip=skip,
        limit=limit
    )
    
    return tickets


@router.get("/{customer_id}/empire-context")
async def get_empire_context(
    customer_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get customer's Empire product context (ContractorForge, etc.).
    
    Returns project history, usage metrics, and other relevant data
    from linked Empire products.
    """
    customer = CustomerService.get_customer(db, customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    try:
        context = await CustomerService.get_empire_product_context(db, customer_id)
        return context
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch Empire context: {str(e)}"
        )
