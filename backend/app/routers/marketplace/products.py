from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
from app.core.database import get_db
from app.schemas.marketplace.product import (
    ProductCreate, ProductUpdate, ProductResponse, ProductListResponse
)
from app.services.marketplace.product_service import ProductService
import math

router = APIRouter(prefix="/marketplace/products", tags=["marketplace-products"])


# Mock current user function - replace with real auth
def get_current_user():
    """Mock function - replace with real authentication"""
    # This would return the authenticated user from JWT token
    return {"id": UUID("00000000-0000-0000-0000-000000000001")}


@router.get("", response_model=ProductListResponse)
def list_products(
    category: Optional[str] = None,
    condition: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort: str = "newest",
    page: int = 1,
    per_page: int = 24,
    db: Session = Depends(get_db)
):
    """List products with filters"""
    skip = (page - 1) * per_page
    
    products, total = ProductService.list_products(
        db=db,
        condition=condition,
        min_price=min_price,
        max_price=max_price,
        skip=skip,
        limit=per_page
    )
    
    total_pages = math.ceil(total / per_page)
    
    return ProductListResponse(
        products=products,
        total=total,
        page=page,
        pages=total_pages
    )


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a single product"""
    product = ProductService.get_product(db, product_id)
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Increment view count
    ProductService.increment_views(db, product_id)
    
    return product


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new product listing"""
    product = ProductService.create_product(
        db=db,
        product_data=product_data,
        seller_id=UUID(current_user["id"])
    )
    return product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: UUID,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a product (seller only)"""
    product = ProductService.update_product(
        db=db,
        product_id=product_id,
        product_data=product_data,
        seller_id=UUID(current_user["id"])
    )
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or unauthorized"
        )
    
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a product (seller only)"""
    success = ProductService.delete_product(
        db=db,
        product_id=product_id,
        seller_id=UUID(current_user["id"])
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or unauthorized"
        )
    
    return None
