from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from uuid import UUID
from app.models.marketplace.review import MarketFReview, ReviewType
from app.models.marketplace.order import MarketFOrder, OrderStatus
from app.schemas.marketplace.review import ReviewCreate


class ReviewService:
    
    @staticmethod
    def create_review(
        db: Session,
        order_id: UUID,
        review_data: ReviewCreate,
        reviewer_id: UUID
    ) -> Optional[MarketFReview]:
        """Create a review for an order"""
        # Get order
        order = db.query(MarketFOrder).filter(MarketFOrder.id == order_id).first()
        
        if not order or order.status != OrderStatus.DELIVERED:
            return None
        
        # Determine review type and reviewee
        if order.buyer_id == reviewer_id:
            review_type = ReviewType.BUYER_TO_SELLER
            reviewee_id = order.seller_id
        elif order.seller_id == reviewer_id:
            review_type = ReviewType.SELLER_TO_BUYER
            reviewee_id = order.buyer_id
        else:
            return None
        
        # Check if review already exists
        existing = db.query(MarketFReview).filter(
            MarketFReview.order_id == order_id,
            MarketFReview.reviewer_id == reviewer_id
        ).first()
        
        if existing:
            return None
        
        # Create review
        review = MarketFReview(
            order_id=order_id,
            reviewer_id=reviewer_id,
            reviewee_id=reviewee_id,
            review_type=review_type,
            **review_data.model_dump()
        )
        
        db.add(review)
        db.commit()
        db.refresh(review)
        return review
    
    @staticmethod
    def get_user_reviews(
        db: Session,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[List[MarketFReview], float, int]:
        """Get all reviews for a user (as seller)"""
        query = db.query(MarketFReview).filter(
            MarketFReview.reviewee_id == user_id,
            MarketFReview.review_type == ReviewType.BUYER_TO_SELLER
        )
        
        total = query.count()
        reviews = query.offset(skip).limit(limit).all()
        
        # Calculate average rating
        avg_rating = db.query(func.avg(MarketFReview.rating)).filter(
            MarketFReview.reviewee_id == user_id,
            MarketFReview.review_type == ReviewType.BUYER_TO_SELLER
        ).scalar()
        
        avg_rating = float(avg_rating) if avg_rating else 0.0
        
        return reviews, avg_rating, total
