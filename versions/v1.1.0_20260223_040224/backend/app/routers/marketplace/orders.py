from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from app.core.database import get_db
from app.schemas.marketplace.order import (
    OrderCreate, OrderResponse, OrderListResponse, ShipOrderRequest
)
from app.services.marketplace.order_service import OrderService
import math

router = APIRouter(prefix="/marketplace/orders", tags=["marketplace-orders"])


def get_current_user():
    """Mock function - replace with real authentication"""
    return {"id": UUID("00000000-0000-0000-0000-000000000001")}


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new order (purchase)"""
    order = OrderService.create_order(
        db=db,
        order_data=order_data,
        buyer_id=UUID(current_user["id"])
    )
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product not available"
        )
    
    # In real implementation, create Stripe Payment Intent here
    # and return the client_secret for frontend to complete payment
    
    return order


@router.get("", response_model=OrderListResponse)
def list_buyer_orders(
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List buyer's orders"""
    skip = (page - 1) * per_page
    
    orders, total = OrderService.list_buyer_orders(
        db=db,
        buyer_id=UUID(current_user["id"]),
        skip=skip,
        limit=per_page
    )
    
    total_pages = math.ceil(total / per_page)
    
    return OrderListResponse(
        orders=orders,
        total=total,
        page=page,
        pages=total_pages
    )


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get order details"""
    order = OrderService.get_order(db, order_id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check if user is buyer or seller
    user_id = UUID(current_user["id"])
    if order.buyer_id != user_id and order.seller_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized"
        )
    
    return order


@router.post("/{order_id}/ship", response_model=OrderResponse)
def ship_order(
    order_id: UUID,
    ship_data: ShipOrderRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Mark order as shipped (seller only)"""
    order = OrderService.mark_order_shipped(
        db=db,
        order_id=order_id,
        tracking_number=ship_data.tracking_number,
        carrier=ship_data.carrier,
        seller_id=UUID(current_user["id"])
    )
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found or unauthorized"
        )
    
    return order


@router.post("/{order_id}/confirm-payment", response_model=OrderResponse)
def confirm_payment(
    order_id: UUID,
    db: Session = Depends(get_db)
):
    """Confirm payment (called by Stripe webhook)"""
    order = OrderService.mark_order_paid(db, order_id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    return order
