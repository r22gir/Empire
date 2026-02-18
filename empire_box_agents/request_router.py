"""
Request routing system for EmpireBox hybrid AI system.

Contains two routers:
1. SimpleRequestRouter - For quick AI responses to buyer messages (messaging system)
2. RequestRouter - For hybrid local/cloud AI routing with budget management
"""

import re
import logging
from typing import Dict, Optional, Any, List

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# SIMPLE REQUEST ROUTER (for messaging/buyer responses)
# =============================================================================

class SimpleRequestRouter:
    """Routes simple AI requests for buyer message responses"""
    
    def __init__(self, local_threshold: int = 100):
        """
        Initialize request router
        
        Args:
            local_threshold: Character count threshold for using local AI
        """
        self.local_threshold = local_threshold
        self.simple_patterns = [
            r"is (this|it) (still )?available",
            r"do you (still )?have (this|it)",
            r"can you ship to",
            r"what'?s (the |your )?lowest",
            r"will you take",
            r"firm on (the )?price",
        ]
    
    def route_request(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Route AI request based on complexity
        
        Args:
            prompt: The input prompt/message
            context: Optional context (message details, listing info, etc.)
            
        Returns:
            AI-generated response
        """
        if self._is_simple_query(prompt):
            return self._handle_local(prompt, context)
        else:
            return self._handle_cloud(prompt, context)
    
    def _is_simple_query(self, prompt: str) -> bool:
        """Determine if query is simple enough for local handling"""
        prompt_lower = prompt.lower()
        
        # Check against known simple patterns
        for pattern in self.simple_patterns:
            if re.search(pattern, prompt_lower):
                return True
        
        # Check length threshold
        if len(prompt) < self.local_threshold:
            return True
        
        return False
    
    def _handle_local(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Handle simple queries locally with rule-based responses"""
        prompt_lower = prompt.lower()
        
        # Availability queries
        if re.search(r"is (this|it) (still )?available", prompt_lower) or \
           re.search(r"do you (still )?have (this|it)", prompt_lower):
            return "Yes! It's still available. Ready to ship today!"
        
        # Shipping queries
        if re.search(r"(can|do) you ship to", prompt_lower):
            location = self._extract_location(prompt)
            if location:
                return f"Yes! I can ship to {location}. Shipping cost will be calculated based on the item's weight and dimensions."
            return "Yes! I ship to most locations. Where are you located? I can calculate shipping for you."
        
        # Price negotiation
        if re.search(r"what'?s (the |your )?lowest", prompt_lower) or \
           re.search(r"will you take", prompt_lower) or \
           re.search(r"firm on (the )?price", prompt_lower):
            if context and context.get('price'):
                price = context['price']
                # Offer 10% discount
                discount_price = price * 0.9
                return f"I can do ${discount_price:.2f}, that's my best price for this quality item."
            return "I have some flexibility on the price. What did you have in mind?"
        
        # Generic response for other simple queries
        return "Thanks for your interest! I'm happy to answer any questions you have about this item."
    
    def _handle_cloud(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Handle complex queries with cloud AI (placeholder)"""
        return (
            "Thanks for your message! Let me provide you with detailed information. "
            "Feel free to ask any follow-up questions you might have."
        )
    
    def _extract_location(self, text: str) -> Optional[str]:
        """Extract location from shipping query"""
        match = re.search(r"ship to ([\w\s,]+?)[\?\.]?$", text.lower())
        if match:
            return match.group(1).strip()
        return None


# =============================================================================
# HYBRID REQUEST ROUTER (for local/cloud AI with budget management)
# =============================================================================

# Import config - these may not exist yet, so handle gracefully
try:
    from .config import (
        LOCAL_TASKS,
        CLOUD_TASKS,
        LOCAL_MODELS,
        CLOUD_MODELS,
        API_ENDPOINTS,
        DEFAULT_LOCAL_MODEL,
        DEFAULT_CLOUD_MODEL,
        AVERAGE_CHARS_PER_TOKEN,
        TASK_COMPLEXITY_LEVELS
    )
    from .token_manager import TokenManager
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    # Define defaults if config not available
    LOCAL_TASKS = ["format_text", "categorize_product", "fill_template", "extract_fields", "simple_validation", "basic_lookup"]
    CLOUD_TASKS = ["complex_reasoning", "content_generation", "price_optimization", "customer_service", "multi_turn_conversation"]
    LOCAL_MODELS = {"phi-3-mini": {"use_cases": LOCAL_TASKS}}
    CLOUD_MODELS = {"grok-2-fast": {"provider": "grok", "use_cases": CLOUD_TASKS}}
    API_ENDPOINTS = {"ollama": "http://localhost:11434", "grok": "https://api.x.ai/v1"}
    DEFAULT_LOCAL_MODEL = "phi-3-mini"
    DEFAULT_CLOUD_MODEL = "grok-2-fast"
    AVERAGE_CHARS_PER_TOKEN = 4
    TASK_COMPLEXITY_LEVELS = ["low", "medium", "high"]


class RequestRouter:
    """
    Routes AI inference requests between local and cloud providers.
    
    Features:
    - Task complexity classification
    - Smart model selection based on task type
    - Budget-aware routing with local fallback
    """
    
    def __init__(self, token_manager=None, default_local_model: str = None,
                 default_cloud_model: str = None):
        """
        Initialize RequestRouter.
        
        Args:
            token_manager: TokenManager instance for budget tracking (optional)
            default_local_model: Default local model to use
            default_cloud_model: Default cloud model to use
        """
        self.token_manager = token_manager
        self.default_local_model = default_local_model or DEFAULT_LOCAL_MODEL
        self.default_cloud_model = default_cloud_model or DEFAULT_CLOUD_MODEL
    
    def classify_task(self, task_type: str, complexity: Optional[str] = None) -> str:
        """Classify task complexity based on task type and optional complexity hint."""
        if complexity and complexity in TASK_COMPLEXITY_LEVELS:
            return complexity
        
        if task_type in LOCAL_TASKS:
            return "low"
        elif task_type in CLOUD_TASKS:
            return "high"
        else:
            logger.warning(f"Unknown task type: {task_type}. Defaulting to medium complexity.")
            return "medium"
    
    def estimate_tokens(self, prompt: str, response_length: int = 500) -> int:
        """Estimate token count for a request."""
        prompt_chars = len(prompt)
        total_chars = prompt_chars + response_length
        estimated_tokens = total_chars // AVERAGE_CHARS_PER_TOKEN
        return max(estimated_tokens, 10)
    
    def select_model(self, task_type: str, complexity: str, 
                    force_local: bool = False) -> Dict[str, Any]:
        """Select appropriate model based on task and complexity."""
        if force_local or complexity == "low":
            return self._get_local_model(task_type)
        
        if complexity == "medium":
            if task_type in LOCAL_TASKS:
                return self._get_local_model(task_type)
            else:
                return self._get_cloud_model(task_type)
        
        if complexity == "high":
            return self._get_cloud_model(task_type)
        
        return self._get_local_model(task_type)
    
    def _get_local_model(self, task_type: str) -> Dict[str, Any]:
        """Get local model configuration."""
        for model_name, model_config in LOCAL_MODELS.items():
            if task_type in model_config.get("use_cases", []):
                return {
                    "model_name": model_name,
                    "provider": "ollama",
                    "is_local": True,
                    "config": model_config
                }
        
        default_config = LOCAL_MODELS.get(self.default_local_model, {})
        return {
            "model_name": self.default_local_model,
            "provider": "ollama",
            "is_local": True,
            "config": default_config
        }
    
    def _get_cloud_model(self, task_type: str) -> Dict[str, Any]:
        """Get cloud model configuration."""
        for model_name, model_config in CLOUD_MODELS.items():
            if task_type in model_config.get("use_cases", []):
                return {
                    "model_name": model_name,
                    "provider": model_config.get("provider", "grok"),
                    "is_local": False,
                    "config": model_config
                }
        
        default_config = CLOUD_MODELS.get(self.default_cloud_model, {})
        return {
            "model_name": self.default_cloud_model,
            "provider": default_config.get("provider", "grok"),
            "is_local": False,
            "config": default_config
        }
    
    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        """Get provider configuration including API endpoint."""
        if provider not in API_ENDPOINTS:
            raise ValueError(f"Unknown provider: {provider}")
        
        return {
            "provider": provider,
            "endpoint": API_ENDPOINTS[provider],
            "requires_auth": provider != "ollama"
        }
    
    def route_request(self, task_type: str = None, prompt: str = "", 
                     complexity: Optional[str] = None,
                     estimated_response_length: int = 500,
                     context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Route an AI inference request to appropriate provider.
        """
        # If no task_type, use simple routing for messaging
        if task_type is None:
            simple_router = SimpleRequestRouter()
            response = simple_router.route_request(prompt, context)
            return {
                "model": {"model_name": "rule-based", "provider": "local", "is_local": True},
                "response": response,
                "estimated_tokens": 0,
                "budget_status": {"ok": True},
                "fallback_used": False
            }
        
        classified_complexity = self.classify_task(task_type, complexity)
        estimated_tokens = self.estimate_tokens(prompt, estimated_response_length)
        selected_model = self.select_model(task_type, classified_complexity, force_local=False)
        
        fallback_used = False
        budget_ok = True
        
        if not selected_model["is_local"] and self.token_manager:
            if not self.token_manager.can_use_tokens(estimated_tokens):
                logger.warning(f"Budget exceeded. Falling back to local model.")
                selected_model = self.select_model(task_type, classified_complexity, force_local=True)
                fallback_used = True
                budget_ok = False
        
        provider_config = self.get_provider_config(selected_model["provider"])
        
        return {
            "model": selected_model,
            "provider_config": provider_config,
            "estimated_tokens": estimated_tokens,
            "budget_status": {
                "ok": budget_ok,
                "can_use_cloud": self.token_manager.can_use_tokens(estimated_tokens) if self.token_manager else True
            },
            "fallback_used": fallback_used,
            "task_type": task_type,
            "complexity": classified_complexity
        }
    
    def execute_request(self, routing_result: Dict[str, Any], prompt: str) -> Dict[str, Any]:
        """Execute the routed request (placeholder for actual API calls)."""
        model = routing_result["model"]
        estimated_tokens = routing_result.get("estimated_tokens", 0)
        
        logger.info(f"Executing request on {model['provider']} with model {model['model_name']}")
        
        response = {
            "success": True,
            "response": routing_result.get("response") or f"[Simulated response from {model['model_name']}]",
            "tokens_used": estimated_tokens if not model["is_local"] else 0,
            "provider": model["provider"],
            "model": model["model_name"],
            "is_local": model["is_local"]
        }
        
        if not model["is_local"] and self.token_manager:
            self.token_manager.track_usage(estimated_tokens)
        
        return response


# Example usage
if __name__ == "__main__":
    # Test SimpleRequestRouter
    print("=== SimpleRequestRouter (Messaging) ===")
    simple_router = SimpleRequestRouter()
    print(simple_router.route_request("Is this still available?"))
    print(simple_router.route_request("What's the lowest you'll go?", {"price": 100}))
    
    # Test RequestRouter
    print("\n=== RequestRouter (Hybrid AI) ===")
    router = RequestRouter()
    result = router.route_request(
        task_type="categorize_product",
        prompt="Categorize: Blue Nike shoes"
    )
    print(f"Model: {result['model']['model_name']}, Local: {result['model']['is_local']}")