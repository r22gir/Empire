"""
SupportForge Integration and Satisfaction database models.
"""
from sqlalchemy import Column, String, Integer, DateTime, Boolean, func, TIMESTAMP, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.database import Base


class Integration(Base):
    """Integration model for third-party services."""
    
    __tablename__ = "sf_integrations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('sf_tenants.id', ondelete='CASCADE'), nullable=False)
    integration_type = Column(String(100), nullable=False)  # contractorforge, email, sms, slack
    config = Column(JSONB, nullable=False, default={})
    api_key = Column(String(500))
    webhook_url = Column(String)
    is_active = Column(Boolean, default=True)
    
    last_sync_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<Integration {self.integration_type}>"


class SatisfactionRating(Base):
    """Customer satisfaction rating model."""
    
    __tablename__ = "sf_satisfaction_ratings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey('sf_tickets.id', ondelete='CASCADE'), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('sf_customers.id'), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(String)
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    __table_args__ = (
        CheckConstraint('rating >= 1 AND rating <= 5', name='check_rating_range'),
    )
    
    def __repr__(self):
        return f"<SatisfactionRating {self.rating}/5 for ticket {self.ticket_id}>"
