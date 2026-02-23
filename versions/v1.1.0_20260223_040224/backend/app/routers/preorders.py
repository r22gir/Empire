from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.schemas.preorder import (
    PreOrderCreate,
    PreOrderResponse,
    PreOrderUpdate
)
from app.services.preorder_service import PreOrderService

router = APIRouter()

@router.post("/", response_model=PreOrderResponse)
async def create_preorder(
    preorder_data: PreOrderCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new pre-order
    """
    try:
        preorder = PreOrderService.create_preorder(db, preorder_data)
        return preorder
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[PreOrderResponse])
async def get_preorders(
    email: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get pre-orders, optionally filtered by email
    """
    preorders = PreOrderService.get_preorders(db, email, limit)
    return preorders

@router.get("/{preorder_id}", response_model=PreOrderResponse)
async def get_preorder(
    preorder_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific pre-order
    """
    from app.models.preorder import PreOrder
    
    preorder = db.query(PreOrder).filter(PreOrder.id == preorder_id).first()
    
    if not preorder:
        raise HTTPException(status_code=404, detail="Pre-order not found")
    
    return preorder

@router.patch("/{preorder_id}", response_model=PreOrderResponse)
async def update_preorder(
    preorder_id: str,
    update_data: PreOrderUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a pre-order (admin only in production)
    """
    preorder = PreOrderService.update_preorder(db, preorder_id, update_data)
    
    if not preorder:
        raise HTTPException(status_code=404, detail="Pre-order not found")
    
    return preorder

@router.post("/{preorder_id}/process-payment", response_model=PreOrderResponse)
async def process_payment(
    preorder_id: str,
    stripe_payment_intent_id: str,
    db: Session = Depends(get_db)
):
    """
    Process payment for a pre-order and generate license keys
    """
    try:
        preorder = PreOrderService.process_payment(
            db, preorder_id, stripe_payment_intent_id
        )
        return preorder
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
