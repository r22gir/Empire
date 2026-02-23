"""
SupportForge Knowledge Base Article database model.
"""
from sqlalchemy import Column, String, Integer, DateTime, func, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
import uuid
from app.database import Base


class KBArticle(Base):
    """Knowledge base article model."""
    
    __tablename__ = "sf_kb_articles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('sf_tenants.id', ondelete='CASCADE'), nullable=False)
    title = Column(String(500), nullable=False)
    slug = Column(String(500), nullable=False)
    content = Column(String, nullable=False)
    content_html = Column(String, nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey('sf_kb_categories.id'), nullable=True)
    tags = Column(ARRAY(String), default=[])
    status = Column(String(20), nullable=False, default='draft')  # draft, published, archived
    
    # Engagement metrics
    view_count = Column(Integer, default=0)
    helpful_count = Column(Integer, default=0)
    not_helpful_count = Column(Integer, default=0)
    
    author_id = Column(UUID(as_uuid=True), ForeignKey('sf_support_agents.id'), nullable=False)
    
    # Timestamps
    published_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<KBArticle {self.title}>"


class KBCategory(Base):
    """Knowledge base category model."""
    
    __tablename__ = "sf_kb_categories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('sf_tenants.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False)
    description = Column(String)
    parent_id = Column(UUID(as_uuid=True), ForeignKey('sf_kb_categories.id'), nullable=True)
    sort_order = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<KBCategory {self.name}>"
