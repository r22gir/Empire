"""
Request routing system for EmpireBox hybrid AI system.

Routes AI requests between local (Ollama) and cloud (Grok/Claude/OpenAI)
models based on task complexity, user budget, and model capabilities.
"""

import logging
from typing import Dict, Optional, Any, List
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


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RequestRouter:
    """
    Routes AI inference requests between local and cloud providers.
    
    Features:
    - Task complexity classification
    - Smart model selection based on task type
    - Budget-aware routing with local fallback
    - Provider configuration management
    
    Example:
        >>> token_mgr = TokenManager("user123", "pro")
        >>> router = RequestRouter(token_manager=token_mgr)
        >>> result = router.route_request(
        ...     task_type="categorize_product",
        ...     prompt="Categorize: Blue Nike shoes",
        ...     complexity="low"
        ... )
        >>> result['provider']
        'ollama'
    """
    
    def __init__(self, token_manager: TokenManager, default_local_model: str = DEFAULT_LOCAL_MODEL,
                 default_cloud_model: str = DEFAULT_CLOUD_MODEL):
        """
        Initialize RequestRouter.
        
        Args:
            token_manager: TokenManager instance for budget tracking
            default_local_model: Default local model to use
            default_cloud_model: Default cloud model to use
        """
        self.token_manager = token_manager
        self.default_local_model = default_local_model
        self.default_cloud_model = default_cloud_model
    
    def classify_task(self, task_type: str, complexity: Optional[str] = None) -> str:
        """
        Classify task complexity based on task type and optional complexity hint.
        
        Args:
            task_type: Type of task (e.g., 'categorize_product', 'content_generation')
            complexity: Optional complexity hint ('low', 'medium', 'high')
            
        Returns:
            Complexity level: 'low', 'medium', or 'high'
            
        Example:
            >>> router = RequestRouter(TokenManager("user123", "pro"))
            >>> router.classify_task("categorize_product")
            'low'
            >>> router.classify_task("content_generation")
            'high'
        """
        # If explicit complexity provided and valid, use it
        if complexity and complexity in TASK_COMPLEXITY_LEVELS:
            return complexity
        
        # Classify based on task type
        if task_type in LOCAL_TASKS:
            return "low"
        elif task_type in CLOUD_TASKS:
            return "high"
        else:
            # Unknown task type, default to medium
            logger.warning(f"Unknown task type: {task_type}. Defaulting to medium complexity.")
            return "medium"
    
    def estimate_tokens(self, prompt: str, response_length: int = 500) -> int:
        """
        Estimate token count for a request.
        
        Args:
            prompt: Input prompt text
            response_length: Estimated response length in characters
            
        Returns:
            Estimated total token count (prompt + response)
            
        Example:
            >>> router = RequestRouter(TokenManager("user123", "pro"))
            >>> router.estimate_tokens("Short prompt", 100)
            28
        """
        prompt_chars = len(prompt)
        total_chars = prompt_chars + response_length
        estimated_tokens = total_chars // AVERAGE_CHARS_PER_TOKEN
        return max(estimated_tokens, 10)  # Minimum 10 tokens
    
    def select_model(self, task_type: str, complexity: str, 
                    force_local: bool = False) -> Dict[str, Any]:
        """
        Select appropriate model based on task and complexity.
        
        Args:
            task_type: Type of task
            complexity: Task complexity level
            force_local: Force local model selection (for budget overflow)
            
        Returns:
            Dictionary with model information:
            - model_name: Name of the selected model
            - provider: Provider name (ollama, grok, anthropic, openai)
            - is_local: Boolean indicating if model is local
            - config: Full model configuration
            
        Example:
            >>> router = RequestRouter(TokenManager("user123", "pro"))
            >>> model = router.select_model("categorize_product", "low")
            >>> model['is_local']
            True
        """
        # Force local if requested (budget overflow)
        if force_local:
            return self._get_local_model(task_type)
        
        # For low complexity, always use local
        if complexity == "low":
            return self._get_local_model(task_type)
        
        # For medium complexity, prefer local if task supports it
        if complexity == "medium":
            if task_type in LOCAL_TASKS:
                return self._get_local_model(task_type)
            else:
                return self._get_cloud_model(task_type)
        
        # For high complexity, use cloud
        if complexity == "high":
            return self._get_cloud_model(task_type)
        
        # Fallback to local
        return self._get_local_model(task_type)
    
    def _get_local_model(self, task_type: str) -> Dict[str, Any]:
        """Get local model configuration."""
        # Find best local model for task
        for model_name, model_config in LOCAL_MODELS.items():
            if task_type in model_config["use_cases"]:
                return {
                    "model_name": model_name,
                    "provider": "ollama",
                    "is_local": True,
                    "config": model_config
                }
        
        # Fallback to default local model
        default_config = LOCAL_MODELS[self.default_local_model]
        return {
            "model_name": self.default_local_model,
            "provider": "ollama",
            "is_local": True,
            "config": default_config
        }
    
    def _get_cloud_model(self, task_type: str) -> Dict[str, Any]:
        """Get cloud model configuration."""
        # Find best cloud model for task
        for model_name, model_config in CLOUD_MODELS.items():
            if task_type in model_config["use_cases"]:
                return {
                    "model_name": model_name,
                    "provider": model_config["provider"],
                    "is_local": False,
                    "config": model_config
                }
        
        # Fallback to default cloud model
        default_config = CLOUD_MODELS[self.default_cloud_model]
        return {
            "model_name": self.default_cloud_model,
            "provider": default_config["provider"],
            "is_local": False,
            "config": default_config
        }
    
    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        """
        Get provider configuration including API endpoint.
        
        Args:
            provider: Provider name (ollama, grok, anthropic, openai)
            
        Returns:
            Dictionary with provider configuration
            
        Example:
            >>> router = RequestRouter(TokenManager("user123", "pro"))
            >>> config = router.get_provider_config("ollama")
            >>> 'endpoint' in config
            True
        """
        if provider not in API_ENDPOINTS:
            raise ValueError(f"Unknown provider: {provider}")
        
        return {
            "provider": provider,
            "endpoint": API_ENDPOINTS[provider],
            "requires_auth": provider != "ollama"
        }
    
    def route_request(self, task_type: str, prompt: str, 
                     complexity: Optional[str] = None,
                     estimated_response_length: int = 500) -> Dict[str, Any]:
        """
        Route an AI inference request to appropriate provider.
        
        Main entry point for request routing. Handles:
        - Task complexity classification
        - Token budget checking
        - Model selection
        - Fallback to local when over budget
        
        Args:
            task_type: Type of task to perform
            prompt: Input prompt for the model
            complexity: Optional complexity hint
            estimated_response_length: Expected response length in chars
            
        Returns:
            Dictionary with routing decision:
            - model: Selected model information
            - provider_config: Provider configuration
            - estimated_tokens: Estimated token usage
            - budget_status: Budget availability
            - fallback_used: Whether local fallback was used
            
        Example:
            >>> token_mgr = TokenManager("user123", "pro")
            >>> router = RequestRouter(token_manager=token_mgr)
            >>> result = router.route_request(
            ...     task_type="categorize_product",
            ...     prompt="Categorize: Blue Nike shoes",
            ...     complexity="low"
            ... )
            >>> result['model']['is_local']
            True
        """
        # Classify task complexity
        classified_complexity = self.classify_task(task_type, complexity)
        
        # Estimate token usage
        estimated_tokens = self.estimate_tokens(prompt, estimated_response_length)
        
        # Select model based on complexity
        selected_model = self.select_model(task_type, classified_complexity, force_local=False)
        
        # Check budget if using cloud model
        fallback_used = False
        budget_ok = True
        
        if not selected_model["is_local"]:
            # Check if user has budget for cloud request
            if not self.token_manager.can_use_tokens(estimated_tokens):
                logger.warning(
                    f"Budget exceeded for user {self.token_manager.user_id}. "
                    f"Falling back to local model."
                )
                selected_model = self.select_model(task_type, classified_complexity, force_local=True)
                fallback_used = True
                budget_ok = False
        
        # Get provider configuration
        provider_config = self.get_provider_config(selected_model["provider"])
        
        return {
            "model": selected_model,
            "provider_config": provider_config,
            "estimated_tokens": estimated_tokens,
            "budget_status": {
                "ok": budget_ok,
                "can_use_cloud": self.token_manager.can_use_tokens(estimated_tokens)
            },
            "fallback_used": fallback_used,
            "task_type": task_type,
            "complexity": classified_complexity
        }
    
    def execute_request(self, routing_result: Dict[str, Any], prompt: str) -> Dict[str, Any]:
        """
        Execute the routed request (placeholder for actual API calls).
        
        This method provides the interface for executing requests.
        In production, this would make actual API calls to the selected provider.
        
        Args:
            routing_result: Result from route_request()
            prompt: The prompt to send to the model
            
        Returns:
            Dictionary with execution result:
            - success: Boolean indicating success
            - response: Model response (or error message)
            - tokens_used: Actual tokens used
            - provider: Provider used
            - model: Model used
            
        Example:
            >>> token_mgr = TokenManager("user123", "pro")
            >>> router = RequestRouter(token_manager=token_mgr)
            >>> routing = router.route_request("categorize_product", "Blue shoes")
            >>> result = router.execute_request(routing, "Blue shoes")
            >>> result['success']
            True
        """
        model = routing_result["model"]
        provider_config = routing_result["provider_config"]
        estimated_tokens = routing_result["estimated_tokens"]
        
        # Placeholder for actual API call
        # In production, this would make real HTTP requests to the provider
        logger.info(
            f"Executing request on {model['provider']} "
            f"with model {model['model_name']}"
        )
        
        # Simulate successful execution
        response = {
            "success": True,
            "response": f"[Simulated response from {model['model_name']}]",
            "tokens_used": estimated_tokens if not model["is_local"] else 0,
            "provider": model["provider"],
            "model": model["model_name"],
            "is_local": model["is_local"]
        }
        
        # Track token usage if cloud model
        if not model["is_local"]:
            self.token_manager.track_usage(estimated_tokens)
            logger.info(
                f"Tracked {estimated_tokens} tokens for user {self.token_manager.user_id}"
            )
        
        return response


# Example usage and testing
if __name__ == "__main__":
    print("=== RequestRouter Example Usage ===\n")
    
    # Example 1: Simple local task
    print("Example 1: Simple local task (categorize_product)")
    token_mgr = TokenManager(user_id="user123", tier="pro")
    router = RequestRouter(token_manager=token_mgr)
    
    result = router.route_request(
        task_type="categorize_product",
        prompt="Categorize this item: Blue Nike shoes size 10"
    )
    print(f"Selected model: {result['model']['model_name']}")
    print(f"Provider: {result['model']['provider']}")
    print(f"Is local: {result['model']['is_local']}")
    print(f"Estimated tokens: {result['estimated_tokens']}\n")
    
    # Example 2: Complex cloud task
    print("Example 2: Complex cloud task (content_generation)")
    result = router.route_request(
        task_type="content_generation",
        prompt="Write a compelling product description for a vintage Rolex watch",
        complexity="high"
    )
    print(f"Selected model: {result['model']['model_name']}")
    print(f"Provider: {result['model']['provider']}")
    print(f"Is local: {result['model']['is_local']}")
    print(f"Fallback used: {result['fallback_used']}\n")
    
    # Example 3: Budget exceeded fallback
    print("Example 3: Budget exceeded - fallback to local")
    small_token_mgr = TokenManager(user_id="user456", tier="free")
    small_token_mgr.track_usage(500_000)  # Use all budget
    
    limited_router = RequestRouter(token_manager=small_token_mgr)
    result = limited_router.route_request(
        task_type="content_generation",
        prompt="Generate content",
        complexity="high"
    )
    print(f"Selected model: {result['model']['model_name']}")
    print(f"Is local: {result['model']['is_local']}")
    print(f"Fallback used: {result['fallback_used']}")
    print(f"Budget OK: {result['budget_status']['ok']}\n")
    
    # Example 4: Execute request
    print("Example 4: Execute request")
    token_mgr2 = TokenManager(user_id="user789", tier="empire")
    router2 = RequestRouter(token_manager=token_mgr2)
    
    routing = router2.route_request(
        task_type="categorize_product",
        prompt="Categorize: Red sneakers"
    )
    execution_result = router2.execute_request(routing, "Categorize: Red sneakers")
    
    print(f"Success: {execution_result['success']}")
    print(f"Model used: {execution_result['model']}")
    print(f"Tokens used: {execution_result['tokens_used']}")
    print(f"Response: {execution_result['response']}")
