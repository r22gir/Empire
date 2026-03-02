"""
Configuration file for EmpireBox hybrid AI system.

Defines subscription tiers, token limits, model configurations,
and API endpoint templates.
"""

from typing import Dict, List, Any
from enum import Enum


class SubscriptionTier(Enum):
    """Subscription tier enumeration."""
    FREE = "free"
    LITE = "lite"
    PRO = "pro"
    EMPIRE = "empire"


# Subscription tier configurations
SUBSCRIPTION_TIERS: Dict[str, Dict[str, Any]] = {
    "free": {
        "name": "Free",
        "monthly_cost": 0,
        "monthly_token_limit": 500_000,  # 500K tokens
        "description": "Basic tier with limited token budget"
    },
    "lite": {
        "name": "Lite",
        "monthly_cost": 29,
        "monthly_token_limit": 2_000_000,  # 2M tokens
        "description": "Entry-level paid tier"
    },
    "pro": {
        "name": "Pro",
        "monthly_cost": 59,
        "monthly_token_limit": 5_000_000,  # 5M tokens
        "description": "Professional tier for regular users"
    },
    "empire": {
        "name": "Empire",
        "monthly_cost": 99,
        "monthly_token_limit": 15_000_000,  # 15M tokens
        "description": "Premium tier for power users"
    }
}

# Usage warning threshold (percentage)
USAGE_WARNING_THRESHOLD = 0.80  # Warn at 80% usage

# Task complexity levels
TASK_COMPLEXITY_LEVELS: List[str] = ["low", "medium", "high"]

# Local tasks (simple, can use Ollama)
LOCAL_TASKS: List[str] = [
    "format_text",
    "categorize_product",
    "fill_template",
    "extract_fields",
    "simple_validation",
    "basic_lookup"
]

# Cloud tasks (complex, require cloud APIs)
CLOUD_TASKS: List[str] = [
    "complex_reasoning",
    "content_generation",
    "price_optimization",
    "customer_service",
    "multi_turn_conversation"
]

# Local model configurations (Ollama)
LOCAL_MODELS: Dict[str, Dict[str, Any]] = {
    "phi-3-mini": {
        "name": "phi-3-mini",
        "provider": "ollama",
        "context_length": 4096,
        "use_cases": ["format_text", "categorize_product", "fill_template"],
        "cost_per_token": 0.0  # Free local inference
    },
    "llama-3.2-3b": {
        "name": "llama-3.2-3b",
        "provider": "ollama",
        "context_length": 8192,
        "use_cases": ["extract_fields", "simple_validation", "basic_lookup"],
        "cost_per_token": 0.0  # Free local inference
    }
}

# Cloud model configurations
CLOUD_MODELS: Dict[str, Dict[str, Any]] = {
    "grok-2-fast": {
        "name": "grok-2-fast",
        "provider": "grok",
        "context_length": 32768,
        "use_cases": ["complex_reasoning", "content_generation"],
        "cost_per_token": 0.00002  # $0.02 per 1K tokens
    },
    "claude-sonnet": {
        "name": "claude-3-5-sonnet-20241022",
        "provider": "anthropic",
        "context_length": 200000,
        "use_cases": ["content_generation", "customer_service"],
        "cost_per_token": 0.000003  # $0.003 per 1K tokens
    },
    "gpt-4o": {
        "name": "gpt-4o",
        "provider": "openai",
        "context_length": 128000,
        "use_cases": ["price_optimization", "multi_turn_conversation"],
        "cost_per_token": 0.0000025  # $0.0025 per 1K tokens
    }
}

# API endpoint templates
API_ENDPOINTS: Dict[str, str] = {
    "ollama": "http://localhost:11434/api/generate",
    "grok": "https://api.x.ai/v1/chat/completions",
    "anthropic": "https://api.anthropic.com/v1/messages",
    "openai": "https://api.openai.com/v1/chat/completions"
}

# Default settings
DEFAULT_TIER = "free"
DEFAULT_LOCAL_MODEL = "phi-3-mini"
DEFAULT_CLOUD_MODEL = "grok-2-fast"
DEFAULT_TIMEOUT = 30  # seconds
DEFAULT_MAX_RETRIES = 3

# Token estimation settings
AVERAGE_CHARS_PER_TOKEN = 4  # Rough estimation: 1 token ≈ 4 characters
