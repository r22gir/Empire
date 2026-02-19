"""
User database model.
"""
from sqlalchemy import Column, String, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.database import Base


class User(Base):
    """User model for authentication and subscription management."""
    
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    marketforge_email = Column(String, unique=True, nullable=True)  # username@marketforge.app
    
    # Subscription tier
    tier = Column(String, default="free")  # free, lite, pro, empire
    tokens_used_this_month = Column(Integer, default=0)
    tokens_reset_date = Column(DateTime(timezone=True), nullable=True)
    
    # Stripe integration
    stripe_customer_id = Column(String, unique=True, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<User {self.email}>"
