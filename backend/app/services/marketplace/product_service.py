from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID
from app.models.marketplace.product import MarketFProduct, ProductStatus
from app.schemas.marketplace.product import ProductCreate, ProductUpdate


class ProductService:
    
    @staticmethod
    def create_product(db: Session, product_data: ProductCreate, seller_id: UUID) -> MarketFProduct:
        """Create a new product listing"""
        product = MarketFProduct(
            **product_data.model_dump(),
            seller_id=seller_id,
            status=ProductStatus.DRAFT
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        return product
    
    @staticmethod
    def get_product(db: Session, product_id: UUID) -> Optional[MarketFProduct]:
        """Get a single product by ID"""
        return db.query(MarketFProduct).filter(MarketFProduct.id == product_id).first()
    
    @staticmethod
    def list_products(
        db: Session,
        category_id: Optional[UUID] = None,
        condition: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        status: Optional[str] = None,
        seller_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 24
    ) -> tuple[List[MarketFProduct], int]:
        """List products with filters"""
        query = db.query(MarketFProduct)
        
        if category_id:
            query = query.filter(MarketFProduct.category_id == category_id)
        if condition:
            query = query.filter(MarketFProduct.condition == condition)
        if min_price is not None:
            query = query.filter(MarketFProduct.price >= min_price)
        if max_price is not None:
            query = query.filter(MarketFProduct.price <= max_price)
        if status:
            query = query.filter(MarketFProduct.status == status)
        else:
            query = query.filter(MarketFProduct.status == ProductStatus.ACTIVE)
        if seller_id:
            query = query.filter(MarketFProduct.seller_id == seller_id)
        
        total = query.count()
        products = query.offset(skip).limit(limit).all()
        
        return products, total
    
    @staticmethod
    def update_product(
        db: Session,
        product_id: UUID,
        product_data: ProductUpdate,
        seller_id: UUID
    ) -> Optional[MarketFProduct]:
        """Update a product (seller only)"""
        product = db.query(MarketFProduct).filter(
            MarketFProduct.id == product_id,
            MarketFProduct.seller_id == seller_id
        ).first()
        
        if not product:
            return None
        
        update_dict = product_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(product, key, value)
        
        db.commit()
        db.refresh(product)
        return product
    
    @staticmethod
    def delete_product(db: Session, product_id: UUID, seller_id: UUID) -> bool:
        """Delete a product (seller only)"""
        product = db.query(MarketFProduct).filter(
            MarketFProduct.id == product_id,
            MarketFProduct.seller_id == seller_id
        ).first()
        
        if not product:
            return False
        
        db.delete(product)
        db.commit()
        return True
    
    @staticmethod
    def increment_views(db: Session, product_id: UUID) -> None:
        """Increment product view count"""
        product = db.query(MarketFProduct).filter(MarketFProduct.id == product_id).first()
        if product:
            product.views += 1
            db.commit()
