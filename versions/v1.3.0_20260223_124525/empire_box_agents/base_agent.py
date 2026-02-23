"""
Base agent class for EmpireBox hybrid AI system.

Provides a foundation for all AI agents with integrated token management,
request routing, and safeguards support.
"""

import logging
from typing import Dict, Optional, Any
from .token_manager import TokenManager
from .request_router import RequestRouter
from .safeguards import AgentSafeguards
from .emergency_stop import EmergencyStop
from .config import DEFAULT_TIER


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseAgent:
    """
    Base class for all EmpireBox AI agents.
    
    Integrates:
    - Token management and budget tracking
    - Smart request routing (local vs cloud)
    - Safety safeguards (rate limiting, budget limits)
    - Emergency stop capability
    
    All specific agents (ListMaster, PhotoAgent, etc.) should inherit from this class.
    
    Example:
        >>> class ProductAgent(BaseAgent):
        ...     def categorize(self, product_description: str):
        ...         return self.run_inference(
        ...             task_type="categorize_product",
        ...             prompt=f"Categorize: {product_description}",
        ...             complexity="low"
        ...         )
        >>> 
        >>> agent = ProductAgent(user_id="user123", tier="pro")
        >>> result = agent.categorize("Blue Nike shoes")
        >>> result['success']
        True
    """
    
    def __init__(self, user_id: str, tier: str = DEFAULT_TIER,
                 enable_safeguards: bool = True,
                 rate_limit: int = 600,
                 budget: int = 10000,
                 action_whitelist: Optional[list] = None):
        """
        Initialize BaseAgent.
        
        Args:
            user_id: Unique identifier for the user
            tier: Subscription tier (free, lite, pro, empire)
            enable_safeguards: Whether to enable safety safeguards
            rate_limit: Actions per minute (for safeguards)
            budget: Action budget (for safeguards)
            action_whitelist: List of allowed actions (for safeguards)
        """
        self.user_id = user_id
        self.tier = tier
        
        # Initialize token manager
        self.token_manager = TokenManager(user_id=user_id, tier=tier)
        
        # Initialize request router
        self.router = RequestRouter(token_manager=self.token_manager)
        
        # Initialize safeguards if enabled
        self.enable_safeguards = enable_safeguards
        if enable_safeguards:
            if action_whitelist is None:
                action_whitelist = [
                    "categorize_product", "format_text", "fill_template",
                    "extract_fields", "simple_validation", "basic_lookup",
                    "complex_reasoning", "content_generation", "price_optimization",
                    "customer_service", "multi_turn_conversation"
                ]
            self.safeguards = AgentSafeguards(
                rate_limit=rate_limit,
                budget=budget,
                action_whitelist=action_whitelist
            )
        else:
            self.safeguards = None
        
        # Initialize emergency stop
        self.emergency_stop = EmergencyStop()
        
        logger.info(f"BaseAgent initialized for user {user_id} with tier {tier}")
    
    def run_inference(self, task_type: str, prompt: str,
                     complexity: Optional[str] = None,
                     estimated_response_length: int = 500) -> Dict[str, Any]:
        """
        Run AI inference with automatic routing and safety checks.
        
        This is the main method for executing AI tasks. It handles:
        - Emergency stop checks
        - Safeguard validation
        - Request routing (local vs cloud)
        - Token budget management
        - Error handling
        
        Args:
            task_type: Type of AI task (e.g., 'categorize_product')
            prompt: Input prompt for the model
            complexity: Optional complexity hint ('low', 'medium', 'high')
            estimated_response_length: Expected response length in characters
            
        Returns:
            Dictionary with inference result:
            - success: Boolean indicating success
            - response: Model response or error message
            - model: Model used
            - provider: Provider used
            - tokens_used: Tokens consumed
            - is_local: Whether local model was used
            - error: Error message if failed
            
        Example:
            >>> agent = BaseAgent("user123", "pro")
            >>> result = agent.run_inference(
            ...     task_type="categorize_product",
            ...     prompt="Blue Nike shoes"
            ... )
            >>> result['success']
            True
        """
        # Check emergency stop
        if not self.emergency_stop.is_running:
            return {
                "success": False,
                "error": "Agent stopped due to emergency stop",
                "emergency_stop": True
            }
        
        # Check safeguards if enabled
        if self.enable_safeguards:
            try:
                self.safeguards.can_execute_action(task_type)
            except Exception as e:
                logger.warning(f"Safeguard check failed: {e}")
                return {
                    "success": False,
                    "error": f"Safeguard violation: {str(e)}",
                    "safeguard_blocked": True
                }
        
        try:
            # Route the request
            routing_result = self.router.route_request(
                task_type=task_type,
                prompt=prompt,
                complexity=complexity,
                estimated_response_length=estimated_response_length
            )
            
            # Execute the request
            execution_result = self.router.execute_request(routing_result, prompt)
            
            # Add routing metadata to result
            execution_result["routing"] = {
                "complexity": routing_result["complexity"],
                "fallback_used": routing_result["fallback_used"],
                "budget_status": routing_result["budget_status"]
            }
            
            return execution_result
            
        except Exception as e:
            logger.error(f"Inference failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "exception": True
            }
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive agent status.
        
        Returns:
            Dictionary with status information:
            - user_id: User identifier
            - tier: Subscription tier
            - token_usage: Token usage statistics
            - emergency_stop: Emergency stop status
            - safeguards_enabled: Whether safeguards are active
            
        Example:
            >>> agent = BaseAgent("user123", "pro")
            >>> status = agent.get_status()
            >>> status['tier']
            'pro'
        """
        status = {
            "user_id": self.user_id,
            "tier": self.tier,
            "token_usage": self.token_manager.get_usage_stats(),
            "emergency_stop": {
                "is_running": self.emergency_stop.is_running,
                "manually_triggered": self.emergency_stop.manual_triggered
            },
            "safeguards_enabled": self.enable_safeguards
        }
        
        if self.enable_safeguards:
            status["safeguards"] = {
                "current_balance": self.safeguards.current_balance,
                "budget": self.safeguards.budget,
                "rate_limit": self.safeguards.rate_limit
            }
        
        return status
    
    def trigger_emergency_stop(self, reason: str = "Manual trigger") -> None:
        """
        Trigger emergency stop for the agent.
        
        Args:
            reason: Reason for emergency stop
            
        Example:
            >>> agent = BaseAgent("user123", "pro")
            >>> agent.trigger_emergency_stop("Suspicious activity detected")
            >>> agent.emergency_stop.is_running
            False
        """
        logger.warning(f"Emergency stop triggered for user {self.user_id}: {reason}")
        self.emergency_stop.manual_trigger()
    
    def reset_safeguards(self) -> None:
        """
        Reset safeguard budget (useful for testing or manual resets).
        
        Example:
            >>> agent = BaseAgent("user123", "pro")
            >>> # ... perform many actions ...
            >>> agent.reset_safeguards()  # Reset action budget
        """
        if self.enable_safeguards:
            self.safeguards.refill_budget(self.safeguards.budget)
            logger.info(f"Safeguards reset for user {self.user_id}")
        else:
            logger.warning("Safeguards not enabled")
    
    def check_quota_status(self) -> Dict[str, Any]:
        """
        Check if agent is over quota with detailed status.
        
        Returns:
            Dictionary with quota status:
            - over_quota: Boolean indicating if over quota
            - can_use_local: Whether local inference is still available
            - can_use_cloud: Whether cloud inference is available
            - message: Status message
            
        Example:
            >>> agent = BaseAgent("user123", "free")
            >>> status = agent.check_quota_status()
            >>> status['can_use_local']
            True
        """
        has_budget, message = self.token_manager.get_budget_status()
        
        return {
            "over_quota": not has_budget,
            "can_use_local": True,  # Local is always available
            "can_use_cloud": has_budget,
            "message": message,
            "usage_stats": self.token_manager.get_usage_stats()
        }


# Example usage and testing
if __name__ == "__main__":
    print("=== BaseAgent Example Usage ===\n")
    
    # Example 1: Basic agent usage
    print("Example 1: Basic agent with inference")
    agent = BaseAgent(user_id="user123", tier="pro")
    
    # Wait a moment to avoid rate limit on first call
    import time
    time.sleep(0.15)  # Wait slightly more than 1/rate_limit seconds
    
    result = agent.run_inference(
        task_type="categorize_product",
        prompt="Categorize this item: Blue Nike shoes size 10",
        complexity="low"
    )
    
    print(f"Success: {result['success']}")
    if result['success']:
        print(f"Model: {result['model']}")
        print(f"Is local: {result['is_local']}")
        print(f"Response: {result['response']}")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")
    print()
    
    # Example 2: Check agent status
    print("Example 2: Check agent status")
    status = agent.get_status()
    print(f"User: {status['user_id']}")
    print(f"Tier: {status['tier']}")
    print(f"Tokens used: {status['token_usage']['used']}")
    print(f"Tokens remaining: {status['token_usage']['remaining']}\n")
    
    # Example 3: Over-quota scenario
    print("Example 3: Over-quota handling")
    limited_agent = BaseAgent(user_id="user456", tier="free")
    limited_agent.token_manager.track_usage(500_000)  # Exhaust budget
    
    quota_status = limited_agent.check_quota_status()
    print(f"Over quota: {quota_status['over_quota']}")
    print(f"Can use local: {quota_status['can_use_local']}")
    print(f"Can use cloud: {quota_status['can_use_cloud']}")
    print(f"Message: {quota_status['message']}\n")
    
    # Should still work with local fallback
    time.sleep(0.15)  # Wait for rate limit
    result = limited_agent.run_inference(
        task_type="content_generation",
        prompt="Generate product description",
        complexity="high"
    )
    print(f"Success despite quota: {result['success']}")
    if result['success']:
        print(f"Used local fallback: {result['routing']['fallback_used']}")
    else:
        print(f"Error: {result.get('error', 'Unknown')}")
    print()
    
    # Example 4: Emergency stop
    print("Example 4: Emergency stop")
    stop_agent = BaseAgent(user_id="user789", tier="lite")
    print(f"Running before stop: {stop_agent.emergency_stop.is_running}")
    
    stop_agent.trigger_emergency_stop("Testing emergency stop")
    print(f"Running after stop: {stop_agent.emergency_stop.is_running}")
    
    time.sleep(0.15)  # Wait for rate limit
    result = stop_agent.run_inference(
        task_type="categorize_product",
        prompt="Test"
    )
    print(f"Inference after stop - Success: {result['success']}")
    print(f"Error: {result.get('error', 'N/A')}\n")
    
    # Example 5: Subclassing for specific agent
    print("Example 5: Subclassing BaseAgent")
    
    class ProductAgent(BaseAgent):
        """Example specific agent for product operations."""
        
        def categorize(self, product_description: str) -> Dict[str, Any]:
            """Categorize a product."""
            return self.run_inference(
                task_type="categorize_product",
                prompt=f"Categorize this product: {product_description}",
                complexity="low"
            )
        
        def generate_description(self, product_name: str) -> Dict[str, Any]:
            """Generate product description."""
            return self.run_inference(
                task_type="content_generation",
                prompt=f"Write a compelling description for: {product_name}",
                complexity="high"
            )
    
    product_agent = ProductAgent(user_id="user101", tier="empire")
    
    time.sleep(0.15)  # Wait for rate limit
    result = product_agent.categorize("Vintage Rolex watch")
    print(f"Categorization success: {result['success']}")
    if result['success']:
        print(f"Model used: {result['model']}")
    
    time.sleep(0.15)  # Wait for rate limit
    result = product_agent.generate_description("Vintage Rolex watch")
    print(f"Description generation success: {result['success']}")
    if result['success']:
        print(f"Model used: {result['model']}")
