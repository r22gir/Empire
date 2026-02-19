from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from app.core.database import get_db
from app.schemas.marketplace.review import ReviewCreate, ReviewResponse, UserReviewsResponse
from app.services.marketplace.review_service import ReviewService

router = APIRouter(prefix="/marketplace", tags=["marketplace-reviews"])


def get_current_user():
    """Mock function - replace with real authentication"""
    return {"id": UUID("00000000-0000-0000-0000-000000000001")}


@router.post("/orders/{order_id}/review", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
def create_review(
    order_id: UUID,
    review_data: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Leave a review for an order"""
    review = ReviewService.create_review(
        db=db,
        order_id=order_id,
        review_data=review_data,
        reviewer_id=UUID(current_user["id"])
    )
    
    if not review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create review. Order not found, not delivered, or review already exists."
        )
    
    return review


@router.get("/users/{user_id}/reviews", response_model=UserReviewsResponse)
def get_user_reviews(
    user_id: UUID,
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db)
):
    """Get reviews for a user (as seller)"""
    skip = (page - 1) * per_page
    
    reviews, avg_rating, total = ReviewService.get_user_reviews(
        db=db,
        user_id=user_id,
        skip=skip,
        limit=per_page
    )
    
    return UserReviewsResponse(
        reviews=reviews,
        average_rating=avg_rating,
        total_reviews=total
    )
