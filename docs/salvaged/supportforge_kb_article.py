"""
SupportForge Knowledge Base Article model.
"""
from sqlalchemy import Column, String, DateTime, Integer, ARRAY, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.database import Base


class SupportForgeKBArticle(Base):
    """Knowledge base article."""
    
    __tablename__ = "supportforge_kb_articles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("supportforge_tenants.id"), nullable=False)
    title = Column(String, nullable=False)
    slug = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    content_html = Column(Text)
    category_id = Column(UUID(as_uuid=True))
    tags = Column(ARRAY(String), default=list)
    status = Column(String, nullable=False, default="draft")  # draft, published, archived
    view_count = Column(Integer, default=0)
    helpful_count = Column(Integer, default=0)
    not_helpful_count = Column(Integer, default=0)
    author_id = Column(UUID(as_uuid=True), ForeignKey("supportforge_agents.id"))
    published_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<SupportForgeKBArticle {self.title}>"
