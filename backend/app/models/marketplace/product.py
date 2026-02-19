import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, Enum, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class ProductStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    SOLD = "sold"
    REMOVED = "removed"


class ProductCondition(str, enum.Enum):
    NEW = "new"
    LIKE_NEW = "like_new"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


class MarketFProduct(Base):
    __tablename__ = "marketf_products"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seller_id = Column(UUID(as_uuid=True), nullable=False)
    
    # From MarketForge listing (if cross-posted)
    marketforge_listing_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Product info
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("marketf_categories.id"), nullable=False)
    condition = Column(Enum(ProductCondition), nullable=False)
    
    # Pricing
    price = Column(Float, nullable=False)
    shipping_price = Column(Float, nullable=True)
    offers_enabled = Column(Boolean, default=False)
    minimum_offer = Column(Float, nullable=True)
    
    # Media
    images = Column(ARRAY(String), nullable=False, default=[])
    
    # Shipping
    package_weight_oz = Column(Integer, nullable=False)
    package_length_in = Column(Integer, nullable=False)
    package_width_in = Column(Integer, nullable=False)
    package_height_in = Column(Integer, nullable=False)
    ships_from_zip = Column(String(10), nullable=False)
    
    # Status
    status = Column(Enum(ProductStatus), default=ProductStatus.DRAFT)
    quantity = Column(Integer, default=1)
    views = Column(Integer, default=0)
    favorites = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    sold_at = Column(DateTime, nullable=True)
    
    # Relationships
    category = relationship("MarketFCategory", back_populates="products")
    orders = relationship("MarketFOrder", back_populates="product")
