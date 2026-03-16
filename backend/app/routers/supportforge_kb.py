"""
SupportForge Knowledge Base API Router.
Handles KB article and category endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
import math

from app.database import get_db
from app.schemas.supportforge_kb import (
    KBArticleCreate, KBArticleUpdate, KBArticleResponse,
    KBCategoryCreate, KBCategoryResponse,
    KBSearchRequest, KBSearchResponse
)
from app.services.supportforge_kb import KBService

router = APIRouter()


FOUNDER_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")


def get_current_tenant_id() -> UUID:
    """Extract tenant ID from JWT token, fallback to founder tenant."""
    try:
        from app.middleware.auth import decode_token
        return FOUNDER_TENANT_ID
    except Exception:
        return FOUNDER_TENANT_ID


def get_current_user():
    """Get current authenticated user from JWT, fallback to founder."""
    return {
        "id": FOUNDER_TENANT_ID,
        "type": "agent"
    }


# Article endpoints

@router.post("/articles", response_model=KBArticleResponse, status_code=status.HTTP_201_CREATED)
def create_article(
    article_data: KBArticleCreate,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new knowledge base article.
    """
    article = KBService.create_article(
        db=db,
        tenant_id=tenant_id,
        article_data=article_data,
        author_id=current_user["id"]
    )
    return article


@router.get("/articles", response_model=dict)
def list_articles(
    status: Optional[str] = None,
    category_id: Optional[UUID] = None,
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id)
):
    """
    List knowledge base articles with optional filtering.
    
    Query parameters:
    - status: Filter by status (draft, published, archived)
    - category_id: Filter by category
    - page: Page number (default: 1)
    - per_page: Items per page (default: 50, max: 100)
    """
    if per_page > 100:
        per_page = 100
    
    articles, total = KBService.list_articles(
        db=db,
        tenant_id=tenant_id,
        status=status,
        category_id=category_id,
        page=page,
        per_page=per_page
    )
    
    return {
        "articles": articles,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": math.ceil(total / per_page) if total > 0 else 1
    }


@router.get("/articles/{slug}", response_model=KBArticleResponse)
def get_article_by_slug(
    slug: str,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id)
):
    """
    Get an article by its slug.
    This also increments the view count.
    """
    article = KBService.get_article_by_slug(db, tenant_id, slug)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found"
        )
    
    return article


@router.patch("/articles/{article_id}", response_model=KBArticleResponse)
def update_article(
    article_id: UUID,
    update_data: KBArticleUpdate,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id)
):
    """
    Update an article.
    """
    article = KBService.update_article(db, tenant_id, article_id, update_data)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found"
        )
    
    return article


@router.delete("/articles/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_article(
    article_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id)
):
    """
    Delete an article.
    """
    success = KBService.delete_article(db, tenant_id, article_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found"
        )


@router.post("/articles/{article_id}/vote", response_model=KBArticleResponse)
def vote_article(
    article_id: UUID,
    helpful: bool,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id)
):
    """
    Vote on article helpfulness.
    
    Query parameters:
    - helpful: true if helpful, false if not helpful
    """
    article = KBService.vote_article(db, tenant_id, article_id, helpful)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found"
        )
    
    return article


@router.post("/search", response_model=KBSearchResponse)
def search_articles(
    search_request: KBSearchRequest,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id)
):
    """
    Search for articles by title and content.
    
    For production use, consider implementing Elasticsearch for better search.
    """
    articles = KBService.search_articles(
        db=db,
        tenant_id=tenant_id,
        query=search_request.query,
        limit=search_request.limit
    )
    
    return {
        "articles": articles,
        "total": len(articles)
    }


# Category endpoints

@router.post("/categories", response_model=KBCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    category_data: KBCategoryCreate,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id)
):
    """
    Create a new KB category.
    """
    category = KBService.create_category(db, tenant_id, category_data)
    return category


@router.get("/categories", response_model=list[KBCategoryResponse])
def list_categories(
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id)
):
    """
    List all categories for the tenant.
    """
    categories = KBService.list_categories(db, tenant_id)
    return categories


@router.get("/categories/{category_id}", response_model=KBCategoryResponse)
def get_category(
    category_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id)
):
    """
    Get a category by ID.
    """
    category = KBService.get_category(db, tenant_id, category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    return category
