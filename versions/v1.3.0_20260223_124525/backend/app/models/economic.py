"""
Economic Intelligence models for tracking costs, revenue, and ROI.
"""
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, func, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from app.database import Base


class EconomicLedger(Base):
    """
    Economic ledger tracking balance, income, and costs per entity.
    
    Entity types: 'user', 'listing', 'shipment', 'license'
    """
    
    __tablename__ = "economic_ledgers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Entity identification
    entity_type = Column(String(50), nullable=False, index=True)  # user, listing, shipment, license
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Financial tracking
    balance = Column(Numeric(12, 2), default=0.00, nullable=False)
    total_income = Column(Numeric(12, 2), default=0.00, nullable=False)
    total_costs = Column(Numeric(12, 2), default=0.00, nullable=False)
    total_profit = Column(Numeric(12, 2), default=0.00, nullable=False)
    
    # Performance metrics
    transaction_count = Column(Numeric(10, 0), default=0, nullable=False)
    last_transaction_at = Column(DateTime(timezone=True), nullable=True)
    
    # Status: thriving, stable, struggling, failing
    status = Column(String(20), default="stable", nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Soft delete
    
    def __repr__(self):
        return f"<EconomicLedger {self.entity_type}:{self.entity_id} balance={self.balance}>"


# Add composite index for efficient lookups
Index('ix_economic_ledgers_entity', EconomicLedger.entity_type, EconomicLedger.entity_id)


class EconomicTransaction(Base):
    """
    Individual economic transaction record (cost or income event).
    
    Transaction types: 'ai_token_cost', 'compute_cost', 'api_cost', 
                       'listing_value', 'shipping_cost', 'license_revenue'
    """
    
    __tablename__ = "economic_transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Link to ledger
    ledger_id = Column(UUID(as_uuid=True), ForeignKey("economic_ledgers.id"), nullable=False, index=True)
    
    # Entity identification (denormalized for easier querying)
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Transaction details
    transaction_type = Column(String(50), nullable=False, index=True)  # ai_token_cost, listing_value, etc.
    amount = Column(Numeric(12, 4), nullable=False)  # Positive for income, negative for costs
    currency = Column(String(3), default="USD", nullable=False)
    
    # Resource details stored as JSONB for flexibility
    # Examples:
    # - AI: {input_tokens: 100, output_tokens: 50, model: "gpt-4", input_price: 2.5, output_price: 10.0}
    # - Compute: {minutes: 5, cost_per_minute: 0.10}
    # - Listing: {listing_id: "...", commission_rate: 0.05, sale_price: 100.00}
    resource_details = Column(JSONB, default={}, nullable=False)
    
    # Quality metrics (for evaluations)
    quality_score = Column(Numeric(5, 2), nullable=True)  # 0-100 scale
    
    # Description
    description = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Soft delete
    
    def __repr__(self):
        return f"<EconomicTransaction {self.transaction_type} {self.amount}>"


# Add composite indexes for efficient querying
Index('ix_economic_transactions_entity', EconomicTransaction.entity_type, EconomicTransaction.entity_id)
Index('ix_economic_transactions_type_created', EconomicTransaction.transaction_type, EconomicTransaction.created_at)
