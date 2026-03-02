from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID
from app.core.database import get_db
from app.schemas.marketplace.order import OrderListResponse
from app.services.marketplace.order_service import OrderService
import math

router = APIRouter(prefix="/marketplace/seller", tags=["marketplace-seller"])


def get_current_user():
    """Mock function - replace with real authentication"""
    return {"id": UUID("00000000-0000-0000-0000-000000000001")}


@router.get("/orders", response_model=OrderListResponse)
def list_seller_orders(
    status: str = None,
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List seller's orders (orders to fulfill)"""
    skip = (page - 1) * per_page
    
    orders, total = OrderService.list_seller_orders(
        db=db,
        seller_id=UUID(current_user["id"]),
        status=status,
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
