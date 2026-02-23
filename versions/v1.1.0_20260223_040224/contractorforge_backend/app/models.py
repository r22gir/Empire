"""
Database models for ContractorForge
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, 
    String, Text, Enum as SQLEnum, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
import enum

from app.database import Base


class IndustryType(str, enum.Enum):
    """Industry template types"""
    WORKROOM = "workroom"  # LuxeForge
    ELECTRICIAN = "electrician"  # ElectricForge
    LANDSCAPING = "landscaping"  # LandscapeForge


class SubscriptionTier(str, enum.Enum):
    """Subscription tiers"""
    SOLO = "solo"  # $79/month
    PRO = "pro"  # $249/month
    ENTERPRISE = "enterprise"  # $599/month


class ProjectStatus(str, enum.Enum):
    """Project status"""
    INQUIRY = "inquiry"
    QUOTED = "quoted"
    APPROVED = "approved"
    IN_PRODUCTION = "in_production"
    READY_TO_INSTALL = "ready_to_install"
    INSTALLED = "installed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class EstimateStatus(str, enum.Enum):
    """Estimate status"""
    DRAFT = "draft"
    SENT = "sent"
    VIEWED = "viewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class InvoiceStatus(str, enum.Enum):
    """Invoice status"""
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class Tenant(Base):
    """
    Tenant represents a business using ContractorForge
    """
    __tablename__ = "tenants"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    
    # Industry configuration
    industry_template = Column(SQLEnum(IndustryType), nullable=False)
    
    # Subscription
    subscription_tier = Column(SQLEnum(SubscriptionTier), nullable=False)
    stripe_customer_id = Column(String(255), nullable=True)
    stripe_subscription_id = Column(String(255), nullable=True)
    subscription_status = Column(String(50), default="active")
    
    # Branding (white-label)
    brand_name = Column(String(255), nullable=True)
    brand_logo_url = Column(String(500), nullable=True)
    primary_color = Column(String(7), default="#0066FF")  # Hex color
    
    # Industry-specific configuration
    pricing_config = Column(JSONB, default={})  # Pricing overrides
    workflow_stages = Column(JSONB, default=[])  # Custom workflow stages
    terminology = Column(JSONB, default={})  # Custom terminology
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    customers = relationship("Customer", back_populates="tenant", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="tenant", cascade="all, delete-orphan")


class User(Base):
    """
    User represents a team member of a tenant business
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    
    # Role & permissions
    role = Column(String(50), default="member")  # owner, admin, member
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")


class Customer(Base):
    """
    Customer represents a client of the tenant business
    """
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    
    # Contact info
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(50), nullable=True)
    
    # Address
    address_line1 = Column(String(500), nullable=True)
    address_line2 = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    zip_code = Column(String(20), nullable=True)
    country = Column(String(50), default="USA")
    
    # Client portal access
    portal_enabled = Column(Boolean, default=True)
    portal_password_hash = Column(String(255), nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="customers")
    projects = relationship("Project", back_populates="customer", cascade="all, delete-orphan")


class Project(Base):
    """
    Project represents a job/project for a customer
    """
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    
    # Basic info
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.INQUIRY)
    
    # Location (if different from customer address)
    project_address = Column(String(500), nullable=True)
    
    # Measurements (flexible JSONB for different industries)
    measurements = Column(JSONB, default={})
    # Example for workroom: {"windows": [{"width": 48, "height": 72, "type": "double_hung"}]}
    # Example for electrician: {"panels": [{"location": "basement", "amps": 200}]}
    # Example for landscaping: {"areas": [{"type": "patio", "sqft": 200}]}
    
    # AI conversation data
    intake_conversation = Column(JSONB, default=[])
    extracted_data = Column(JSONB, default={})
    
    # Dates
    inquiry_date = Column(DateTime, default=datetime.utcnow)
    target_completion_date = Column(DateTime, nullable=True)
    actual_completion_date = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="projects")
    customer = relationship("Customer", back_populates="projects")
    estimates = relationship("Estimate", back_populates="project", cascade="all, delete-orphan")
    media = relationship("Media", back_populates="project", cascade="all, delete-orphan")


class Estimate(Base):
    """
    Estimate/Quote for a project
    """
    __tablename__ = "estimates"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    # Estimate details
    estimate_number = Column(String(50), unique=True, nullable=False)
    status = Column(SQLEnum(EstimateStatus), default=EstimateStatus.DRAFT)
    
    # Line items (flexible JSONB)
    line_items = Column(JSONB, default=[])
    # Example: [{"description": "Drapery Installation", "quantity": 2, "unit": "window", "rate": 150, "total": 300}]
    
    # Totals
    subtotal = Column(Float, default=0.0)
    tax_rate = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    
    # Payment terms
    deposit_percentage = Column(Float, default=50.0)
    deposit_amount = Column(Float, default=0.0)
    balance_due = Column(Float, default=0.0)
    
    # Validity
    valid_until = Column(DateTime, nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    internal_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)
    viewed_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="estimates")
    invoices = relationship("Invoice", back_populates="estimate", cascade="all, delete-orphan")


class Invoice(Base):
    """
    Invoice for payment collection
    """
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, index=True)
    estimate_id = Column(Integer, ForeignKey("estimates.id", ondelete="CASCADE"), nullable=False)
    
    # Invoice details
    invoice_number = Column(String(50), unique=True, nullable=False)
    status = Column(SQLEnum(InvoiceStatus), default=InvoiceStatus.DRAFT)
    invoice_type = Column(String(50))  # deposit, progress, final, balance
    
    # Amounts
    amount = Column(Float, nullable=False)
    amount_paid = Column(Float, default=0.0)
    amount_due = Column(Float, nullable=False)
    
    # Stripe
    stripe_payment_intent_id = Column(String(255), nullable=True)
    
    # Dates
    issue_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    estimate = relationship("Estimate", back_populates="invoices")


class CatalogItem(Base):
    """
    Universal catalog for products/materials (fabrics, hardware, plants, etc.)
    """
    __tablename__ = "catalog_items"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)  # Null = global catalog
    
    # Item details
    sku = Column(String(100), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Category/tags (for filtering by industry)
    category = Column(String(100), nullable=False)  # fabric, hardware, plant, electrical_fixture, etc.
    tags = Column(JSONB, default=[])
    
    # Pricing
    cost_price = Column(Float, nullable=True)
    sell_price = Column(Float, nullable=True)
    markup_percentage = Column(Float, nullable=True)
    
    # Unit
    unit_type = Column(String(50), default="each")  # each, yard, sqft, linear_ft, etc.
    
    # Supplier info
    supplier_name = Column(String(255), nullable=True)
    supplier_sku = Column(String(100), nullable=True)
    
    # Media
    image_url = Column(String(500), nullable=True)
    additional_data = Column(JSONB, default={})  # Industry-specific data
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProductionItem(Base):
    """
    Production queue for manufacturing businesses (workrooms, etc.)
    """
    __tablename__ = "production_items"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    # Item details
    item_type = Column(String(100), nullable=False)  # drapery, roman_shade, valance, etc.
    specifications = Column(JSONB, default={})
    
    # Production status
    status = Column(String(50), default="pending")  # pending, cutting, sewing, finished
    priority = Column(Integer, default=0)
    
    # Dates
    due_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ScheduledEvent(Base):
    """
    Calendar events for appointments, installations, consultations
    """
    __tablename__ = "scheduled_events"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=True)
    
    # Event details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    event_type = Column(String(100), nullable=False)  # consultation, installation, measurement, etc.
    
    # Date/time
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    all_day = Column(Boolean, default=False)
    
    # Location
    location = Column(String(500), nullable=True)
    
    # Status
    status = Column(String(50), default="scheduled")  # scheduled, completed, cancelled
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Media(Base):
    """
    Media files (photos, 3D scans) for projects
    """
    __tablename__ = "media"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    # File details
    file_type = Column(String(50), nullable=False)  # photo, video, 3d_scan, document
    file_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500), nullable=True)
    file_size = Column(Integer, nullable=True)  # bytes
    
    # Measurement data (if applicable)
    measurement_data = Column(JSONB, default={})
    confidence_score = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="media")


class Conversation(Base):
    """
    AI conversation history for project intake
    """
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    # Conversation data
    messages = Column(JSONB, default=[])
    # Example: [{"role": "assistant", "content": "What type of windows?", "timestamp": "..."}]
    
    # Status
    is_complete = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Initialize relationships (if needed for back_populates)
Estimate.invoices = relationship("Invoice", back_populates="estimate", cascade="all, delete-orphan")
Project.estimates = relationship("Estimate", back_populates="project", cascade="all, delete-orphan")
