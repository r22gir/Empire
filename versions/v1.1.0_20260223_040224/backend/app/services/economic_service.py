"""
Economic service for tracking costs, revenue, and ROI.
"""
from typing import Optional, Dict, Any, List
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.economic import EconomicLedger, EconomicTransaction
from app.config import settings
import uuid


class EconomicService:
    """
    Service for managing economic tracking and analytics.
    
    Handles balance management, transaction recording, ROI calculations,
    and status determination for all entities in the system.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_or_create_ledger(
        self, 
        entity_type: str, 
        entity_id: uuid.UUID
    ) -> EconomicLedger:
        """
        Get existing ledger or create new one for an entity.
        
        Args:
            entity_type: Type of entity (user, listing, shipment, license)
            entity_id: UUID of the entity
            
        Returns:
            EconomicLedger instance
        """
        # Try to find existing ledger
        result = await self.db.execute(
            select(EconomicLedger).where(
                and_(
                    EconomicLedger.entity_type == entity_type,
                    EconomicLedger.entity_id == entity_id,
                    EconomicLedger.deleted_at.is_(None)
                )
            )
        )
        ledger = result.scalar_one_or_none()
        
        if ledger:
            return ledger
        
        # Create new ledger
        ledger = EconomicLedger(
            entity_type=entity_type,
            entity_id=entity_id,
            balance=Decimal(str(settings.economic_default_balance)),
            total_income=Decimal('0.00'),
            total_costs=Decimal('0.00'),
            total_profit=Decimal('0.00'),
            transaction_count=0,
            status="stable"
        )
        self.db.add(ledger)
        await self.db.commit()
        await self.db.refresh(ledger)
        
        return ledger
    
    async def record_transaction(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        transaction_type: str,
        amount: float,
        resource_details: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        quality_score: Optional[float] = None
    ) -> EconomicTransaction:
        """
        Record an economic transaction and update ledger.
        
        Args:
            entity_type: Type of entity
            entity_id: UUID of the entity
            transaction_type: Type of transaction (ai_token_cost, listing_value, etc.)
            amount: Transaction amount (positive for income, negative for costs)
            resource_details: Additional details about the transaction
            description: Human-readable description
            quality_score: Optional quality score (0-100)
            
        Returns:
            Created EconomicTransaction
        """
        if not settings.economic_enabled:
            # If economic tracking is disabled, return a mock transaction
            return EconomicTransaction(
                id=uuid.uuid4(),
                ledger_id=uuid.uuid4(),
                entity_type=entity_type,
                entity_id=entity_id,
                transaction_type=transaction_type,
                amount=Decimal(str(amount)),
                resource_details=resource_details or {},
                description=description
            )
        
        # Get or create ledger
        ledger = await self.get_or_create_ledger(entity_type, entity_id)
        
        # Create transaction
        transaction = EconomicTransaction(
            ledger_id=ledger.id,
            entity_type=entity_type,
            entity_id=entity_id,
            transaction_type=transaction_type,
            amount=Decimal(str(amount)),
            currency="USD",
            resource_details=resource_details or {},
            description=description,
            quality_score=Decimal(str(quality_score)) if quality_score is not None else None
        )
        self.db.add(transaction)
        
        # Update ledger
        amount_decimal = Decimal(str(amount))
        ledger.balance += amount_decimal
        ledger.transaction_count += 1
        ledger.last_transaction_at = datetime.utcnow()
        
        if amount_decimal > 0:
            ledger.total_income += amount_decimal
        else:
            ledger.total_costs += abs(amount_decimal)
        
        ledger.total_profit = ledger.total_income - ledger.total_costs
        
        # Update status based on balance
        ledger.status = self._calculate_status(ledger.balance)
        
        await self.db.commit()
        await self.db.refresh(transaction)
        
        return transaction
    
    def _calculate_status(self, balance: Decimal) -> str:
        """
        Calculate economic status based on balance.
        
        Args:
            balance: Current balance
            
        Returns:
            Status string: thriving, stable, struggling, failing
        """
        if balance > 100:
            return "thriving"
        elif balance > 10:
            return "stable"
        elif balance > 0:
            return "struggling"
        else:
            return "failing"
    
    async def get_ledger(
        self, 
        entity_type: str, 
        entity_id: uuid.UUID
    ) -> Optional[EconomicLedger]:
        """
        Get ledger for an entity.
        
        Args:
            entity_type: Type of entity
            entity_id: UUID of the entity
            
        Returns:
            EconomicLedger or None if not found
        """
        result = await self.db.execute(
            select(EconomicLedger).where(
                and_(
                    EconomicLedger.entity_type == entity_type,
                    EconomicLedger.entity_id == entity_id,
                    EconomicLedger.deleted_at.is_(None)
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_transactions(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        transaction_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[EconomicTransaction]:
        """
        Get transactions for an entity.
        
        Args:
            entity_type: Type of entity
            entity_id: UUID of the entity
            transaction_type: Optional filter by transaction type
            limit: Maximum number of transactions to return
            offset: Offset for pagination
            
        Returns:
            List of EconomicTransaction
        """
        query = select(EconomicTransaction).where(
            and_(
                EconomicTransaction.entity_type == entity_type,
                EconomicTransaction.entity_id == entity_id,
                EconomicTransaction.deleted_at.is_(None)
            )
        )
        
        if transaction_type:
            query = query.where(EconomicTransaction.transaction_type == transaction_type)
        
        query = query.order_by(EconomicTransaction.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_dashboard_overview(
        self,
        entity_type: str,
        entity_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get comprehensive dashboard overview for an entity.
        
        Args:
            entity_type: Type of entity
            entity_id: UUID of the entity
            
        Returns:
            Dictionary with dashboard data
        """
        ledger = await self.get_or_create_ledger(entity_type, entity_id)
        
        # Get recent transactions (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        result = await self.db.execute(
            select(EconomicTransaction).where(
                and_(
                    EconomicTransaction.entity_type == entity_type,
                    EconomicTransaction.entity_id == entity_id,
                    EconomicTransaction.created_at >= thirty_days_ago,
                    EconomicTransaction.deleted_at.is_(None)
                )
            ).order_by(EconomicTransaction.created_at.desc())
        )
        recent_transactions = list(result.scalars().all())
        
        # Calculate metrics
        recent_income = sum(
            t.amount for t in recent_transactions if t.amount > 0
        )
        recent_costs = sum(
            abs(t.amount) for t in recent_transactions if t.amount < 0
        )
        
        # Calculate profit margin
        profit_margin = 0.0
        if ledger.total_income > 0:
            profit_margin = float(ledger.total_profit / ledger.total_income * 100)
        
        # Calculate ROI
        roi = 0.0
        if ledger.total_costs > 0:
            roi = float(ledger.total_profit / ledger.total_costs * 100)
        
        return {
            "ledger": {
                "balance": float(ledger.balance),
                "total_income": float(ledger.total_income),
                "total_costs": float(ledger.total_costs),
                "total_profit": float(ledger.total_profit),
                "status": ledger.status,
                "transaction_count": int(ledger.transaction_count),
                "last_transaction_at": ledger.last_transaction_at.isoformat() if ledger.last_transaction_at else None,
            },
            "metrics": {
                "profit_margin": round(profit_margin, 2),
                "roi": round(roi, 2),
                "recent_income_30d": float(recent_income),
                "recent_costs_30d": float(recent_costs),
            },
            "recent_transactions": [
                {
                    "id": str(t.id),
                    "type": t.transaction_type,
                    "amount": float(t.amount),
                    "description": t.description,
                    "created_at": t.created_at.isoformat(),
                    "resource_details": t.resource_details,
                }
                for t in recent_transactions[:10]  # Last 10 transactions
            ]
        }
    
    async def calculate_ai_token_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str = "gpt-4"
    ) -> float:
        """
        Calculate cost of AI token usage.
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model name (for future pricing differentiation)
            
        Returns:
            Total cost in USD
        """
        input_cost = (input_tokens * settings.economic_token_input_price_per_1m) / 1_000_000
        output_cost = (output_tokens * settings.economic_token_output_price_per_1m) / 1_000_000
        return input_cost + output_cost
    
    async def record_ai_cost(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        input_tokens: int,
        output_tokens: int,
        model: str = "gpt-4",
        description: Optional[str] = None
    ) -> EconomicTransaction:
        """
        Record AI token usage cost.
        
        Args:
            entity_type: Type of entity
            entity_id: UUID of the entity
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model name
            description: Optional description
            
        Returns:
            Created EconomicTransaction
        """
        cost = await self.calculate_ai_token_cost(input_tokens, output_tokens, model)
        
        return await self.record_transaction(
            entity_type=entity_type,
            entity_id=entity_id,
            transaction_type="ai_token_cost",
            amount=-cost,  # Negative for costs
            resource_details={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "model": model,
                "input_price_per_1m": settings.economic_token_input_price_per_1m,
                "output_price_per_1m": settings.economic_token_output_price_per_1m,
            },
            description=description or f"AI token usage: {input_tokens} input, {output_tokens} output tokens"
        )
    
    async def record_listing_value(
        self,
        user_id: uuid.UUID,
        listing_id: uuid.UUID,
        sale_price: float,
        quality_score: Optional[float] = None
    ) -> EconomicTransaction:
        """
        Record value created from a listing.
        
        Args:
            user_id: UUID of the user
            listing_id: UUID of the listing
            sale_price: Sale price of the listing
            quality_score: Optional quality score
            
        Returns:
            Created EconomicTransaction
        """
        # Calculate commission value
        commission_value = sale_price * settings.economic_listing_commission_rate
        
        # Adjust by quality score if provided
        actual_value = commission_value
        if quality_score is not None:
            actual_value = commission_value * (quality_score / 100.0)
        
        return await self.record_transaction(
            entity_type="user",
            entity_id=user_id,
            transaction_type="listing_value",
            amount=actual_value,  # Positive for income
            resource_details={
                "listing_id": str(listing_id),
                "sale_price": sale_price,
                "commission_rate": settings.economic_listing_commission_rate,
                "commission_value": commission_value,
                "quality_score": quality_score,
                "actual_value": actual_value,
            },
            description=f"Listing value: ${sale_price:.2f} @ {settings.economic_listing_commission_rate*100}% commission",
            quality_score=quality_score
        )
    
    async def record_compute_cost(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        compute_minutes: float,
        description: Optional[str] = None
    ) -> EconomicTransaction:
        """
        Record compute cost (e.g., for photo processing).
        
        Args:
            entity_type: Type of entity
            entity_id: UUID of the entity
            compute_minutes: Number of compute minutes
            description: Optional description
            
        Returns:
            Created EconomicTransaction
        """
        cost = compute_minutes * settings.economic_compute_cost_per_minute
        
        return await self.record_transaction(
            entity_type=entity_type,
            entity_id=entity_id,
            transaction_type="compute_cost",
            amount=-cost,  # Negative for costs
            resource_details={
                "compute_minutes": compute_minutes,
                "cost_per_minute": settings.economic_compute_cost_per_minute,
            },
            description=description or f"Compute usage: {compute_minutes} minutes"
        )
