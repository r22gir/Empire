from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID


class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = Field(None, max_length=255)
    comment: Optional[str] = None


class ReviewResponse(BaseModel):
    id: UUID
    order_id: UUID
    reviewer_id: UUID
    reviewee_id: UUID
    review_type: str
    rating: int
    title: Optional[str] = None
    comment: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class UserReviewsResponse(BaseModel):
    reviews: list[ReviewResponse]
    average_rating: float
    total_reviews: int
