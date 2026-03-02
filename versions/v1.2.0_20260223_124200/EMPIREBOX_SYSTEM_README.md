# EmpireBox Hybrid AI System

A comprehensive infrastructure for managing AI agents with intelligent routing between local (Ollama) and cloud (Grok/Claude/OpenAI) models, token budget management, and integrated safety safeguards.

## Overview

The EmpireBox Hybrid AI System provides a complete solution for:
- **Token Budget Management**: Track and limit AI API usage per user based on subscription tiers
- **Smart Request Routing**: Automatically route requests to local or cloud models based on task complexity and budget
- **Safety Safeguards**: Rate limiting, action whitelisting, and emergency stop capabilities
- **Subscription Tiers**: Support for Free, Lite ($29/mo), Pro ($59/mo), and Empire ($99/mo) tiers

## Architecture

### Core Components

1. **TokenManager** (`token_manager.py`): 
   - Manages per-user token budgets
   - Tracks usage and remaining tokens
   - Sends warnings at 80% usage threshold
   - Thread-safe for concurrent operations

2. **RequestRouter** (`request_router.py`):
   - Classifies task complexity (low, medium, high)
   - Selects appropriate models based on task type
   - Falls back to local models when budget exceeded
   - Provides provider configuration

3. **BaseAgent** (`base_agent.py`):
   - Base class for all AI agents
   - Integrates TokenManager and RequestRouter
   - Includes safeguards and emergency stop hooks
   - Provides `run_inference()` method for AI tasks

4. **Configuration** (`config.py`):
   - Subscription tier definitions
   - Model configurations (local and cloud)
   - API endpoints and default settings

## Installation

```bash
# Clone the repository
git clone https://github.com/r22gir/Empire.git
cd Empire

# The package is ready to use - no additional dependencies for core functionality
# For actual API calls, you would need:
# pip install requests  # For HTTP API calls
```

## Quick Start

### Basic Usage

```python
from empire_box_agents import TokenManager, RequestRouter, BaseAgent

# Initialize for a Pro tier user
token_mgr = TokenManager(user_id="user123", tier="pro")
router = RequestRouter(token_manager=token_mgr)

# Route a simple request (uses local Ollama - free)
result = router.route_request(
    task_type="categorize_product",
    prompt="Categorize this item: Blue Nike shoes size 10",
    complexity="low"
)
print(f"Provider: {result['model']['provider']}")  # ollama
print(f"Model: {result['model']['model_name']}")   # phi-3-mini
print(f"Is Local: {result['model']['is_local']}")  # True

# Route a complex request (uses cloud API)
result = router.route_request(
    task_type="content_generation",
    prompt="Write a compelling product description for vintage Rolex watch",
    complexity="high"
)
print(f"Provider: {result['model']['provider']}")  # grok
print(f"Model: {result['model']['model_name']}")   # grok-2-fast
```

### Using BaseAgent (Recommended)

```python
from empire_box_agents import BaseAgent

# Create an agent for a user
agent = BaseAgent(user_id="user456", tier="empire")

# Run inference with automatic routing and safety checks
result = agent.run_inference(
    task_type="categorize_product",
    prompt="Blue Nike shoes size 10"
)

if result['success']:
    print(f"Response: {result['response']}")
    print(f"Model used: {result['model']}")
    print(f"Tokens used: {result['tokens_used']}")
else:
    print(f"Error: {result['error']}")

# Check agent status
status = agent.get_status()
print(f"Token usage: {status['token_usage']['percentage']}%")
print(f"Remaining: {status['token_usage']['remaining']} tokens")
```

### Creating Custom Agents

```python
from empire_box_agents import BaseAgent

class ProductAgent(BaseAgent):
    """Custom agent for product operations."""
    
    def categorize(self, product_description: str):
        """Categorize a product (simple task, uses local model)."""
        return self.run_inference(
            task_type="categorize_product",
            prompt=f"Categorize this product: {product_description}",
            complexity="low"
        )
    
    def generate_description(self, product_name: str):
        """Generate product description (complex task, uses cloud API)."""
        return self.run_inference(
            task_type="content_generation",
            prompt=f"Write a compelling description for: {product_name}",
            complexity="high"
        )

# Use the custom agent
product_agent = ProductAgent(user_id="user789", tier="pro")

result = product_agent.categorize("Vintage Rolex watch")
print(result['response'])

result = product_agent.generate_description("Vintage Rolex watch")
print(result['response'])
```

## Subscription Tiers

| Tier | Monthly Cost | Token Limit | Best For |
|------|-------------|-------------|----------|
| **Free** | $0 | 500K tokens | Testing and light usage |
| **Lite** | $29 | 2M tokens | Small businesses |
| **Pro** | $59 | 5M tokens | Regular users |
| **Empire** | $99 | 15M tokens | Power users |

Usage warnings are automatically sent at 80% of monthly limit.

## Task Types and Model Selection

### Local Tasks (Free, uses Ollama)
- `format_text` - Text formatting operations
- `categorize_product` - Product categorization
- `fill_template` - Template filling
- `extract_fields` - Field extraction
- `simple_validation` - Basic validation
- `basic_lookup` - Simple lookups

**Local Models:**
- `phi-3-mini` - Fast, efficient for simple tasks
- `llama-3.2-3b` - More capable, still efficient

### Cloud Tasks (Uses paid APIs)
- `complex_reasoning` - Advanced reasoning tasks
- `content_generation` - High-quality content creation
- `price_optimization` - Pricing analysis
- `customer_service` - Customer support responses
- `multi_turn_conversation` - Context-aware conversations

**Cloud Models:**
- `grok-2-fast` (Grok API) - Fast cloud inference
- `claude-3-5-sonnet` (Anthropic) - High-quality responses
- `gpt-4o` (OpenAI) - Advanced reasoning

## Budget Management

### Checking Budget

```python
token_mgr = TokenManager(user_id="user123", tier="pro")

# Check if tokens are available
if token_mgr.can_use_tokens(1000):
    token_mgr.track_usage(1000)
    print("Tokens used successfully")

# Get detailed stats
stats = token_mgr.get_usage_stats()
print(f"Used: {stats['used']}")
print(f"Remaining: {stats['remaining']}")
print(f"Percentage: {stats['percentage']}%")

# Get budget status with message
has_budget, message = token_mgr.get_budget_status()
print(message)
```

### Automatic Fallback

When budget is exceeded, the system automatically falls back to local models:

```python
# User has exhausted cloud budget
agent = BaseAgent(user_id="user123", tier="free")
agent.token_manager.track_usage(500_000)  # Use all tokens

# Request will automatically use local model instead of cloud
result = agent.run_inference(
    task_type="content_generation",  # Normally uses cloud
    prompt="Generate content",
    complexity="high"
)

# Check if fallback was used
print(f"Fallback used: {result['routing']['fallback_used']}")  # True
print(f"Model: {result['model']}")  # Local model (phi-3-mini or llama)
```

### Monthly Reset

```python
# Reset monthly usage (typically called by billing system)
token_mgr.reset_monthly()

# Upgrade tier
token_mgr.upgrade_tier("empire")
```

## Safety Features

### Rate Limiting

```python
# BaseAgent includes rate limiting by default
agent = BaseAgent(
    user_id="user123",
    tier="pro",
    rate_limit=60,  # 60 actions per minute
    budget=10000,   # 10000 actions
    action_whitelist=["categorize_product", "content_generation"]
)
```

### Emergency Stop

```python
agent = BaseAgent(user_id="user123", tier="pro")

# Trigger emergency stop
agent.trigger_emergency_stop("Suspicious activity detected")

# Agent will no longer process requests
result = agent.run_inference(task_type="test", prompt="test")
print(result['error'])  # "Agent stopped due to emergency stop"
```

### Quota Checking

```python
agent = BaseAgent(user_id="user123", tier="free")

# Check quota status
quota_status = agent.check_quota_status()
print(f"Over quota: {quota_status['over_quota']}")
print(f"Can use local: {quota_status['can_use_local']}")  # Always True
print(f"Can use cloud: {quota_status['can_use_cloud']}")
print(f"Message: {quota_status['message']}")
```

## Integration with Existing Systems

The system integrates seamlessly with existing EmpireBox components:

```python
from empire_box_agents import BaseAgent, AgentSafeguards, EmergencyStop

# BaseAgent automatically uses existing safeguards
agent = BaseAgent(user_id="user123", tier="pro")

# Access existing components
safeguards = agent.safeguards  # AgentSafeguards instance
emergency_stop = agent.emergency_stop  # EmergencyStop instance

# These work with the existing safeguards.py and emergency_stop.py
```

## Thread Safety

All components are thread-safe and can be used in concurrent environments:

```python
import threading
from empire_box_agents import BaseAgent

agent = BaseAgent(user_id="user123", tier="pro")

def run_inference_task(task_id):
    result = agent.run_inference(
        task_type="categorize_product",
        prompt=f"Task {task_id}"
    )
    print(f"Task {task_id}: {result['success']}")

# Run multiple tasks concurrently
threads = [
    threading.Thread(target=run_inference_task, args=(i,))
    for i in range(10)
]

for thread in threads:
    thread.start()

for thread in threads:
    thread.join()

# Check total usage
stats = agent.token_manager.get_usage_stats()
print(f"Total tokens used: {stats['used']}")
```

## API Reference

### TokenManager

```python
TokenManager(user_id: str, tier: str = "free")
```

**Methods:**
- `can_use_tokens(token_count: int) -> bool` - Check if tokens available
- `track_usage(token_count: int) -> None` - Track token usage
- `get_usage_stats() -> Dict` - Get usage statistics
- `reset_monthly() -> None` - Reset monthly usage
- `upgrade_tier(new_tier: str) -> None` - Upgrade subscription tier
- `get_budget_status() -> Tuple[bool, str]` - Get budget status with message
- `send_usage_warning(usage_percentage: float) -> None` - Send usage warning

### RequestRouter

```python
RequestRouter(token_manager: TokenManager, 
              default_local_model: str = "phi-3-mini",
              default_cloud_model: str = "grok-2-fast")
```

**Methods:**
- `classify_task(task_type: str, complexity: Optional[str]) -> str` - Classify task complexity
- `estimate_tokens(prompt: str, response_length: int) -> int` - Estimate token count
- `select_model(task_type: str, complexity: str, force_local: bool) -> Dict` - Select model
- `get_provider_config(provider: str) -> Dict` - Get provider configuration
- `route_request(task_type: str, prompt: str, complexity: Optional[str], estimated_response_length: int) -> Dict` - Route request
- `execute_request(routing_result: Dict, prompt: str) -> Dict` - Execute request

### BaseAgent

```python
BaseAgent(user_id: str, 
          tier: str = "free",
          enable_safeguards: bool = True,
          rate_limit: int = 600,
          budget: int = 10000,
          action_whitelist: Optional[list] = None)
```

**Methods:**
- `run_inference(task_type: str, prompt: str, complexity: Optional[str], estimated_response_length: int) -> Dict` - Run AI inference
- `get_status() -> Dict` - Get agent status
- `trigger_emergency_stop(reason: str) -> None` - Trigger emergency stop
- `reset_safeguards() -> None` - Reset safeguard budget
- `check_quota_status() -> Dict` - Check quota status

## Testing

Run the built-in tests:

```bash
# Test TokenManager
python3 -m empire_box_agents.token_manager

# Test RequestRouter
python3 -m empire_box_agents.request_router

# Test BaseAgent
python3 -m empire_box_agents.base_agent
```

## Production Considerations

### API Integration

The current implementation includes placeholder API execution. For production:

1. **Add API credentials**: Set up environment variables for API keys
2. **Implement actual API calls**: Update `RequestRouter.execute_request()` to make real HTTP requests
3. **Handle retries**: Add retry logic for failed API calls
4. **Monitor performance**: Add logging and metrics collection

### Database Integration

For production deployment:

1. **Persist token usage**: Store usage data in database
2. **User management**: Integrate with user authentication system
3. **Billing integration**: Connect with payment processing
4. **Usage analytics**: Track and analyze usage patterns

### Scaling

The system is designed to scale:

- Thread-safe for concurrent requests
- Stateless request routing
- Can be deployed in distributed environments
- Supports load balancing across multiple instances

## License

See LICENSE file for details.

## Support

For questions or issues, please contact the EmpireBox team or open an issue on GitHub.
