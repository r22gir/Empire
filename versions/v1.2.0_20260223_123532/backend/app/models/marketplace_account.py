"""
MarketplaceAccount database model.
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSON
import uuid
from app.database import Base


class MarketplaceAccount(Base):
    """Marketplace connection credentials."""
    
    __tablename__ = "marketplace_accounts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Marketplace info
    marketplace = Column(String(50), nullable=False)  # ebay, facebook, etc.
    
    # Encrypted credentials (OAuth tokens, API keys, etc.)
    credentials = Column(JSON, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    connected_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<MarketplaceAccount {self.marketplace}>"
