from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON
from app.database import Base
from datetime import datetime
import uuid


class Quote(Base):
    __tablename__ = "quotes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    quote_number = Column(String, unique=True, nullable=False, index=True)

    # Status: draft, sent, accepted, rejected, expired, invoiced
    status = Column(String, default="draft")

    # Customer info
    customer_name = Column(String, nullable=False)
    customer_email = Column(String, nullable=True)
    customer_phone = Column(String, nullable=True)
    customer_address = Column(Text, nullable=True)

    # Project info
    project_name = Column(String, nullable=True)
    project_description = Column(Text, nullable=True)
    desk_id = Column(String, nullable=True)

    # Line items stored as JSON array
    # Each: { description, quantity, unit, rate, amount, category }
    # category: "labor" | "materials" | "other"
    line_items = Column(JSON, default=list)

    # Measurements stored as JSON
    # { width, height, depth, unit, notes, room, window_type }
    measurements = Column(JSON, default=dict)

    # Financials
    subtotal = Column(Float, default=0.0)
    tax_rate = Column(Float, default=0.0)       # e.g. 0.08 for 8%
    tax_amount = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    total = Column(Float, default=0.0)

    # Deposit schedule as JSON
    # { deposit_percent, deposit_amount, deposit_due, balance_due }
    deposit = Column(JSON, default=dict)

    # Terms and dates
    terms = Column(Text, nullable=True)          # Payment terms text
    valid_days = Column(Integer, default=30)      # Quote validity in days
    install_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)           # Internal notes

    # Business info (for PDF header)
    business_name = Column(String, nullable=True)
    business_logo_url = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)
    accepted_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
