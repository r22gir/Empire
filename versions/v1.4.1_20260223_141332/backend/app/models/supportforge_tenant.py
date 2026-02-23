"""
SupportForge Tenant database model.
Tenants represent support organizations using the platform.
"""
from sqlalchemy import Column, String, DateTime, func, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.types import TEXT
import uuid
from app.database import Base


class Tenant(Base):
    """Tenant model for multi-tenant support organizations."""
    
    __tablename__ = "sf_tenants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    subdomain = Column(String(100), unique=True, nullable=False)
    plan = Column(String(50), nullable=False, default='starter')  # starter, growth, enterprise
    settings = Column(JSONB, default={})
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<Tenant {self.name} ({self.subdomain})>"
