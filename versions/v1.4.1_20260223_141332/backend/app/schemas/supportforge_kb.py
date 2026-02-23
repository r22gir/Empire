"""
Pydantic schemas for SupportForge Knowledge Base API.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class KBArticleCreate(BaseModel):
    """Schema for creating a KB article."""
    title: str = Field(..., min_length=1, max_length=500)
    slug: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    content_html: str = Field(..., min_length=1)
    category_id: Optional[UUID] = None
    tags: List[str] = Field(default=[])
    status: str = Field(default="draft", pattern="^(draft|published|archived)$")


class KBArticleUpdate(BaseModel):
    """Schema for updating a KB article."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    slug: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = Field(None, min_length=1)
    content_html: Optional[str] = Field(None, min_length=1)
    category_id: Optional[UUID] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = Field(None, pattern="^(draft|published|archived)$")


class KBArticleResponse(BaseModel):
    """Schema for KB article response."""
    id: UUID
    tenant_id: UUID
    title: str
    slug: str
    content: str
    content_html: str
    category_id: Optional[UUID]
    tags: List[str]
    status: str
    view_count: int
    helpful_count: int
    not_helpful_count: int
    author_id: UUID
    published_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class KBCategoryCreate(BaseModel):
    """Schema for creating a KB category."""
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    sort_order: int = 0


class KBCategoryResponse(BaseModel):
    """Schema for KB category response."""
    id: UUID
    tenant_id: UUID
    name: str
    slug: str
    description: Optional[str]
    parent_id: Optional[UUID]
    sort_order: int
    
    class Config:
        from_attributes = True


class KBSearchRequest(BaseModel):
    """Schema for KB search request."""
    query: str = Field(..., min_length=1)
    limit: int = Field(default=10, ge=1, le=100)


class KBSearchResponse(BaseModel):
    """Schema for KB search results."""
    articles: List[KBArticleResponse]
    total: int
