from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Marketplace credentials (encrypted)
    ebay_token = Column(Text, nullable=True)
    facebook_token = Column(Text, nullable=True)
    poshmark_credentials = Column(Text, nullable=True)
    mercari_token = Column(Text, nullable=True)
    
    # Stripe
    stripe_customer_id = Column(String, nullable=True)
    
    # Relationships
    listings = relationship("Listing", back_populates="user")
    sales = relationship("Sale", back_populates="user")

class Listing(Base):
    __tablename__ = "listings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    price = Column(Float, nullable=False)
    photo_url = Column(String, nullable=False)
    
    # Platform posting status
    posted_ebay = Column(Boolean, default=False)
    posted_facebook = Column(Boolean, default=False)
    posted_poshmark = Column(Boolean, default=False)
    posted_mercari = Column(Boolean, default=False)
    posted_craigslist = Column(Boolean, default=False)
    
    # Platform listing IDs
    ebay_listing_id = Column(String, nullable=True)
    facebook_listing_id = Column(String, nullable=True)
    poshmark_listing_id = Column(String, nullable=True)
    mercari_listing_id = Column(String, nullable=True)
    craigslist_listing_id = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="listings")
    sales = relationship("Sale", back_populates="listing")

class Sale(Base):
    __tablename__ = "sales"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=False)
    
    platform = Column(String, nullable=False)  # ebay, facebook, poshmark, mercari
    sale_price = Column(Float, nullable=False)
    commission = Column(Float, nullable=False)  # 3% of sale_price
    buyer_info = Column(Text, nullable=True)
    
    # Stripe payment
    stripe_payment_intent_id = Column(String, nullable=True)
    commission_paid = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="sales")
    listing = relationship("Listing", back_populates="sales")

class Payout(Base):
    __tablename__ = "payouts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    total_earned = Column(Float, nullable=False)
    commission_amount = Column(Float, nullable=False)
    payout_amount = Column(Float, nullable=False)
    
    stripe_payout_id = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, completed, failed
    
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)
