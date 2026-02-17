"""
Token management system for EmpireBox hybrid AI system.

Manages user token budgets, tracks usage, handles subscription tiers,
and provides thread-safe operations for concurrent agent access.
"""

import time
import threading
from typing import Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from .config import (
    SUBSCRIPTION_TIERS,
    USAGE_WARNING_THRESHOLD,
    DEFAULT_TIER
)


class TokenManager:
    """
    Manages token budgets and usage tracking for users.
    
    Features:
    - Per-user token tracking (used, remaining, percentage)
    - Monthly budget limits based on subscription tier
    - Usage warnings at configurable threshold
    - Thread-safe operations
    - Monthly reset functionality
    
    Example:
        >>> token_mgr = TokenManager(user_id="user123", tier="pro")
        >>> if token_mgr.can_use_tokens(1000):
        ...     token_mgr.track_usage(1000)
        ...     print("Tokens used successfully")
        >>> stats = token_mgr.get_usage_stats()
        >>> print(f"Used: {stats['used']}, Remaining: {stats['remaining']}")
    """
    
    def __init__(self, user_id: str, tier: str = DEFAULT_TIER):
        """
        Initialize TokenManager for a user.
        
        Args:
            user_id: Unique identifier for the user
            tier: Subscription tier (free, lite, pro, empire)
        
        Raises:
            ValueError: If tier is invalid
        """
        if tier not in SUBSCRIPTION_TIERS:
            raise ValueError(f"Invalid tier: {tier}. Must be one of {list(SUBSCRIPTION_TIERS.keys())}")
        
        self.user_id = user_id
        self.tier = tier
        self.tier_config = SUBSCRIPTION_TIERS[tier]
        self.monthly_limit = self.tier_config["monthly_token_limit"]
        
        # Token tracking
        self.tokens_used = 0
        self.last_reset = datetime.now()
        self.warning_sent = False
        
        # Thread safety
        self.lock = threading.Lock()
    
    def can_use_tokens(self, token_count: int) -> bool:
        """
        Check if user has enough tokens available in their budget.
        
        Args:
            token_count: Number of tokens requested
            
        Returns:
            True if tokens are available, False otherwise
            
        Example:
            >>> token_mgr = TokenManager("user123", "lite")
            >>> token_mgr.can_use_tokens(1000)
            True
            >>> token_mgr.track_usage(2_000_000)  # Use all tokens
            >>> token_mgr.can_use_tokens(1000)
            False
        """
        with self.lock:
            # Check if monthly reset is needed
            self._check_monthly_reset()
            
            remaining = self.monthly_limit - self.tokens_used
            return token_count <= remaining
    
    def track_usage(self, token_count: int) -> None:
        """
        Track token usage and update budget.
        
        Args:
            token_count: Number of tokens used
            
        Raises:
            ValueError: If token_count is negative
            
        Example:
            >>> token_mgr = TokenManager("user123", "pro")
            >>> token_mgr.track_usage(5000)
            >>> stats = token_mgr.get_usage_stats()
            >>> stats['used']
            5000
        """
        if token_count < 0:
            raise ValueError("Token count cannot be negative")
        
        with self.lock:
            # Check if monthly reset is needed
            self._check_monthly_reset()
            
            self.tokens_used += token_count
            
            # Check if warning threshold reached
            usage_percentage = self.tokens_used / self.monthly_limit
            if usage_percentage >= USAGE_WARNING_THRESHOLD and not self.warning_sent:
                self.send_usage_warning(usage_percentage)
                self.warning_sent = True
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get current usage statistics for the user.
        
        Returns:
            Dictionary containing usage stats:
            - user_id: User identifier
            - tier: Subscription tier
            - monthly_limit: Total monthly token limit
            - used: Tokens used this month
            - remaining: Tokens remaining
            - percentage: Usage percentage (0-100)
            - last_reset: Last reset timestamp
            
        Example:
            >>> token_mgr = TokenManager("user123", "empire")
            >>> token_mgr.track_usage(1_000_000)
            >>> stats = token_mgr.get_usage_stats()
            >>> stats['percentage']
            6.67
        """
        with self.lock:
            # Check if monthly reset is needed
            self._check_monthly_reset()
            
            remaining = max(0, self.monthly_limit - self.tokens_used)
            percentage = (self.tokens_used / self.monthly_limit) * 100
            
            return {
                "user_id": self.user_id,
                "tier": self.tier,
                "tier_name": self.tier_config["name"],
                "monthly_limit": self.monthly_limit,
                "used": self.tokens_used,
                "remaining": remaining,
                "percentage": round(percentage, 2),
                "last_reset": self.last_reset.isoformat(),
                "warning_sent": self.warning_sent
            }
    
    def reset_monthly(self) -> None:
        """
        Reset monthly token usage (typically called at billing cycle).
        
        Example:
            >>> token_mgr = TokenManager("user123", "lite")
            >>> token_mgr.track_usage(1_000_000)
            >>> token_mgr.reset_monthly()
            >>> stats = token_mgr.get_usage_stats()
            >>> stats['used']
            0
        """
        with self.lock:
            self.tokens_used = 0
            self.last_reset = datetime.now()
            self.warning_sent = False
            print(f"[TokenManager] Monthly reset for user {self.user_id}. Budget refreshed.")
    
    def send_usage_warning(self, usage_percentage: float) -> None:
        """
        Send usage warning when threshold is reached.
        
        Args:
            usage_percentage: Current usage as decimal (e.g., 0.85 for 85%)
            
        Example:
            >>> token_mgr = TokenManager("user123", "free")
            >>> token_mgr.send_usage_warning(0.85)
            [TokenManager] WARNING: User user123 has used 85.0% of monthly token budget
        """
        percentage_display = usage_percentage * 100
        print(f"[TokenManager] WARNING: User {self.user_id} has used {percentage_display:.1f}% "
              f"of monthly token budget ({self.tokens_used:,}/{self.monthly_limit:,} tokens)")
        # In production, this would send email/notification
    
    def _check_monthly_reset(self) -> None:
        """
        Internal method to check if monthly reset is needed.
        Should be called within lock context.
        """
        now = datetime.now()
        # Reset if more than 30 days have passed
        if now - self.last_reset > timedelta(days=30):
            self.tokens_used = 0
            self.last_reset = now
            self.warning_sent = False
            print(f"[TokenManager] Auto-reset triggered for user {self.user_id}")
    
    def upgrade_tier(self, new_tier: str) -> None:
        """
        Upgrade user to a new subscription tier.
        
        Args:
            new_tier: New subscription tier name
            
        Raises:
            ValueError: If new_tier is invalid
            
        Example:
            >>> token_mgr = TokenManager("user123", "free")
            >>> token_mgr.upgrade_tier("pro")
            >>> token_mgr.tier
            'pro'
        """
        if new_tier not in SUBSCRIPTION_TIERS:
            raise ValueError(f"Invalid tier: {new_tier}")
        
        with self.lock:
            old_limit = self.monthly_limit
            self.tier = new_tier
            self.tier_config = SUBSCRIPTION_TIERS[new_tier]
            self.monthly_limit = self.tier_config["monthly_token_limit"]
            
            print(f"[TokenManager] User {self.user_id} upgraded from "
                  f"{old_limit:,} to {self.monthly_limit:,} tokens/month")
    
    def get_budget_status(self) -> Tuple[bool, str]:
        """
        Get budget status with a descriptive message.
        
        Returns:
            Tuple of (has_budget: bool, message: str)
            
        Example:
            >>> token_mgr = TokenManager("user123", "lite")
            >>> has_budget, msg = token_mgr.get_budget_status()
            >>> has_budget
            True
        """
        with self.lock:
            self._check_monthly_reset()
            
            remaining = self.monthly_limit - self.tokens_used
            
            if remaining <= 0:
                return False, f"Budget exceeded. Used {self.tokens_used:,}/{self.monthly_limit:,} tokens."
            
            percentage = (self.tokens_used / self.monthly_limit) * 100
            
            if percentage >= 95:
                status = "CRITICAL"
            elif percentage >= USAGE_WARNING_THRESHOLD * 100:
                status = "WARNING"
            else:
                status = "OK"
            
            return True, f"Status: {status}. {remaining:,} tokens remaining ({100-percentage:.1f}% available)"


# Example usage and testing
if __name__ == "__main__":
    print("=== TokenManager Example Usage ===\n")
    
    # Example 1: Basic usage
    print("Example 1: Basic token tracking")
    token_mgr = TokenManager(user_id="user123", tier="pro")
    print(f"Initial stats: {token_mgr.get_usage_stats()}")
    
    # Simulate token usage
    if token_mgr.can_use_tokens(1000):
        token_mgr.track_usage(1000)
        print("✓ Used 1000 tokens")
    
    stats = token_mgr.get_usage_stats()
    print(f"After usage: {stats['used']} used, {stats['remaining']} remaining\n")
    
    # Example 2: Budget exceeded
    print("Example 2: Budget exceeded scenario")
    small_mgr = TokenManager(user_id="user456", tier="free")
    small_mgr.track_usage(500_000)  # Use all free tier tokens
    
    if not small_mgr.can_use_tokens(1000):
        print("✓ Correctly blocked: Budget exceeded")
        has_budget, msg = small_mgr.get_budget_status()
        print(f"Status: {msg}\n")
    
    # Example 3: Warning threshold
    print("Example 3: Usage warning")
    warning_mgr = TokenManager(user_id="user789", tier="lite")
    warning_mgr.track_usage(1_700_000)  # 85% of 2M limit
    print(f"Warning sent: {warning_mgr.warning_sent}\n")
    
    # Example 4: Tier upgrade
    print("Example 4: Tier upgrade")
    upgrade_mgr = TokenManager(user_id="user101", tier="free")
    print(f"Before upgrade: {upgrade_mgr.monthly_limit:,} tokens")
    upgrade_mgr.upgrade_tier("empire")
    print(f"After upgrade: {upgrade_mgr.monthly_limit:,} tokens")
