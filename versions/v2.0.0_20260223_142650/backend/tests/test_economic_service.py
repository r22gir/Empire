"""
Unit tests for Economic Intelligence System.
"""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
import uuid

from app.services.economic_service import EconomicService
from app.models.economic import EconomicLedger, EconomicTransaction


class TestEconomicService:
    """Test suite for EconomicService."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = AsyncMock()
        return db
    
    @pytest.fixture
    def economic_service(self, mock_db):
        """Create EconomicService instance with mock DB."""
        return EconomicService(mock_db)
    
    def test_calculate_status_thriving(self, economic_service):
        """Test status calculation for thriving balance."""
        status = economic_service._calculate_status(Decimal("150.00"))
        assert status == "thriving"
    
    def test_calculate_status_stable(self, economic_service):
        """Test status calculation for stable balance."""
        status = economic_service._calculate_status(Decimal("50.00"))
        assert status == "stable"
    
    def test_calculate_status_struggling(self, economic_service):
        """Test status calculation for struggling balance."""
        status = economic_service._calculate_status(Decimal("5.00"))
        assert status == "struggling"
    
    def test_calculate_status_failing(self, economic_service):
        """Test status calculation for failing balance."""
        status = economic_service._calculate_status(Decimal("-10.00"))
        assert status == "failing"
    
    @pytest.mark.asyncio
    async def test_calculate_ai_token_cost(self, economic_service):
        """Test AI token cost calculation."""
        # Mock settings
        from app.config import settings
        settings.economic_token_input_price_per_1m = 2.50
        settings.economic_token_output_price_per_1m = 10.00
        
        cost = await economic_service.calculate_ai_token_cost(
            input_tokens=1000,
            output_tokens=500,
            model="gpt-4"
        )
        
        # Expected: (1000 * 2.50 / 1,000,000) + (500 * 10.00 / 1,000,000)
        # = 0.0025 + 0.005 = 0.0075
        assert abs(cost - 0.0075) < 0.0001
    
    @pytest.mark.asyncio
    async def test_record_transaction_disabled(self, mock_db, economic_service):
        """Test that transactions are not recorded when economic tracking is disabled."""
        from app.config import settings
        settings.economic_enabled = False
        
        user_id = uuid.uuid4()
        transaction = await economic_service.record_transaction(
            entity_type="user",
            entity_id=user_id,
            transaction_type="ai_token_cost",
            amount=-0.50,
            description="Test transaction"
        )
        
        # Should return a mock transaction without DB operations
        assert transaction is not None
        assert transaction.entity_type == "user"
        assert transaction.transaction_type == "ai_token_cost"
        
        # DB should not have been called
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
