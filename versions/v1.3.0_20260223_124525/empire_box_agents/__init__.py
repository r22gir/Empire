"""
EmpireBox Agents - Hybrid AI System

A comprehensive system for managing AI agents with token budgets,
smart routing between local and cloud models, and integrated safeguards.

Main Components:
- TokenManager: Token budget tracking and subscription tier management
- RequestRouter: Smart routing between local (Ollama) and cloud (Grok/Claude/OpenAI) models
- BaseAgent: Base class for all AI agents with integrated safety features
- AgentSafeguards: Rate limiting and action control
- EmergencyStop: Emergency stop protocol

Example Usage:
    >>> from empire_box_agents import TokenManager, RequestRouter, BaseAgent
    >>> 
    >>> # Initialize for a Pro tier user
    >>> token_mgr = TokenManager(user_id="user123", tier="pro")
    >>> router = RequestRouter(token_manager=token_mgr)
    >>> 
    >>> # Route a simple request (uses local Ollama)
    >>> result = router.route_request(
    ...     task_type="categorize_product",
    ...     prompt="Categorize this item: Blue Nike shoes size 10"
    ... )
    >>> print(f"Uses local: {result['model']['is_local']}")
    >>> 
    >>> # Or use BaseAgent for full integration
    >>> agent = BaseAgent(user_id="user456", tier="empire")
    >>> result = agent.run_inference(
    ...     task_type="content_generation",
    ...     prompt="Write a product description",
    ...     complexity="high"
    ... )
"""

__version__ = "1.0.0"
__author__ = "EmpireBox Team"

# Import configuration
from .config import (
    SubscriptionTier,
    SUBSCRIPTION_TIERS,
    USAGE_WARNING_THRESHOLD,
    TASK_COMPLEXITY_LEVELS,
    LOCAL_TASKS,
    CLOUD_TASKS,
    LOCAL_MODELS,
    CLOUD_MODELS,
    API_ENDPOINTS,
    DEFAULT_TIER,
    DEFAULT_LOCAL_MODEL,
    DEFAULT_CLOUD_MODEL,
)

# Import core components
from .token_manager import TokenManager
from .request_router import RequestRouter
from .base_agent import BaseAgent

# Import existing components
from .safeguards import AgentSafeguards
from .emergency_stop import EmergencyStop

__all__ = [
    # Core classes
    "TokenManager",
    "RequestRouter",
    "BaseAgent",
    
    # Existing safety components
    "AgentSafeguards",
    "EmergencyStop",
    
    # Configuration
    "SubscriptionTier",
    "SUBSCRIPTION_TIERS",
    "USAGE_WARNING_THRESHOLD",
    "TASK_COMPLEXITY_LEVELS",
    "LOCAL_TASKS",
    "CLOUD_TASKS",
    "LOCAL_MODELS",
    "CLOUD_MODELS",
    "API_ENDPOINTS",
    "DEFAULT_TIER",
    "DEFAULT_LOCAL_MODEL",
    "DEFAULT_CLOUD_MODEL",
]
