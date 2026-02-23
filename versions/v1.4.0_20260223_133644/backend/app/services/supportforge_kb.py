"""
SupportForge Knowledge Base Service.
Business logic for KB article management.
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import Optional, List
from uuid import UUID

from app.models.supportforge_kb import KBArticle, KBCategory
from app.schemas.supportforge_kb import KBArticleCreate, KBArticleUpdate, KBCategoryCreate


class KBService:
    """Service class for knowledge base operations."""
    
    @staticmethod
    def create_article(
        db: Session,
        tenant_id: UUID,
        article_data: KBArticleCreate,
        author_id: UUID
    ) -> KBArticle:
        """Create a new KB article."""
        article = KBArticle(
            tenant_id=tenant_id,
            title=article_data.title,
            slug=article_data.slug,
            content=article_data.content,
            content_html=article_data.content_html,
            category_id=article_data.category_id,
            tags=article_data.tags,
            status=article_data.status,
            author_id=author_id
        )
        db.add(article)
        db.commit()
        db.refresh(article)
        
        return article
    
    @staticmethod
    def get_article(db: Session, tenant_id: UUID, article_id: UUID) -> Optional[KBArticle]:
        """Get an article by ID."""
        return db.query(KBArticle).filter(
            and_(
                KBArticle.id == article_id,
                KBArticle.tenant_id == tenant_id
            )
        ).first()
    
    @staticmethod
    def get_article_by_slug(db: Session, tenant_id: UUID, slug: str) -> Optional[KBArticle]:
        """Get an article by slug."""
        article = db.query(KBArticle).filter(
            and_(
                KBArticle.slug == slug,
                KBArticle.tenant_id == tenant_id
            )
        ).first()
        
        # Increment view count
        if article:
            article.view_count += 1
            db.commit()
            db.refresh(article)
        
        return article
    
    @staticmethod
    def list_articles(
        db: Session,
        tenant_id: UUID,
        status: Optional[str] = None,
        category_id: Optional[UUID] = None,
        page: int = 1,
        per_page: int = 50
    ):
        """
        List articles with filtering and pagination.
        
        Returns:
            Tuple of (articles, total_count)
        """
        query = db.query(KBArticle).filter(KBArticle.tenant_id == tenant_id)
        
        if status:
            query = query.filter(KBArticle.status == status)
        if category_id:
            query = query.filter(KBArticle.category_id == category_id)
        
        total = query.count()
        
        articles = query.order_by(KBArticle.created_at.desc()).offset(
            (page - 1) * per_page
        ).limit(per_page).all()
        
        return articles, total
    
    @staticmethod
    def search_articles(
        db: Session,
        tenant_id: UUID,
        query: str,
        limit: int = 10
    ) -> List[KBArticle]:
        """
        Search articles by title and content.
        For production, use Elasticsearch or full-text search.
        """
        search_filter = f"%{query}%"
        
        articles = db.query(KBArticle).filter(
            and_(
                KBArticle.tenant_id == tenant_id,
                KBArticle.status == 'published',
                or_(
                    KBArticle.title.ilike(search_filter),
                    KBArticle.content.ilike(search_filter)
                )
            )
        ).order_by(KBArticle.view_count.desc()).limit(limit).all()
        
        return articles
    
    @staticmethod
    def update_article(
        db: Session,
        tenant_id: UUID,
        article_id: UUID,
        update_data: KBArticleUpdate
    ) -> Optional[KBArticle]:
        """Update an article."""
        article = KBService.get_article(db, tenant_id, article_id)
        if not article:
            return None
        
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(article, key, value)
        
        db.commit()
        db.refresh(article)
        
        return article
    
    @staticmethod
    def delete_article(db: Session, tenant_id: UUID, article_id: UUID) -> bool:
        """Delete an article."""
        article = KBService.get_article(db, tenant_id, article_id)
        if not article:
            return False
        
        db.delete(article)
        db.commit()
        
        return True
    
    @staticmethod
    def vote_article(db: Session, tenant_id: UUID, article_id: UUID, helpful: bool) -> Optional[KBArticle]:
        """Vote on article helpfulness."""
        article = KBService.get_article(db, tenant_id, article_id)
        if not article:
            return None
        
        if helpful:
            article.helpful_count += 1
        else:
            article.not_helpful_count += 1
        
        db.commit()
        db.refresh(article)
        
        return article
    
    # Category methods
    
    @staticmethod
    def create_category(
        db: Session,
        tenant_id: UUID,
        category_data: KBCategoryCreate
    ) -> KBCategory:
        """Create a new KB category."""
        category = KBCategory(
            tenant_id=tenant_id,
            name=category_data.name,
            slug=category_data.slug,
            description=category_data.description,
            parent_id=category_data.parent_id,
            sort_order=category_data.sort_order
        )
        db.add(category)
        db.commit()
        db.refresh(category)
        
        return category
    
    @staticmethod
    def get_category(db: Session, tenant_id: UUID, category_id: UUID) -> Optional[KBCategory]:
        """Get a category by ID."""
        return db.query(KBCategory).filter(
            and_(
                KBCategory.id == category_id,
                KBCategory.tenant_id == tenant_id
            )
        ).first()
    
    @staticmethod
    def list_categories(db: Session, tenant_id: UUID) -> List[KBCategory]:
        """List all categories for a tenant."""
        return db.query(KBCategory).filter(
            KBCategory.tenant_id == tenant_id
        ).order_by(KBCategory.sort_order).all()
