#!/usr/bin/env python3
"""
EmpireBox Hybrid AI System - Complete Demonstration

This script demonstrates all key features of the EmpireBox hybrid AI system:
1. Token management across subscription tiers
2. Smart routing between local and cloud models
3. Budget-aware fallback mechanisms
4. Integration with safety safeguards
5. Custom agent implementation

Run this script to see the system in action:
    python3 demo_empirebox_system.py
"""

import time
from empire_box_agents import (
    TokenManager, RequestRouter, BaseAgent,
    SUBSCRIPTION_TIERS
)


def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def demo_subscription_tiers():
    """Demonstrate different subscription tiers."""
    print_section("DEMO 1: Subscription Tiers")
    
    for tier_name, tier_config in SUBSCRIPTION_TIERS.items():
        print(f"{tier_config['name']} Tier (${tier_config['monthly_cost']}/month):")
        print(f"  Monthly tokens: {tier_config['monthly_token_limit']:,}")
        print(f"  Description: {tier_config['description']}")
        print()


def demo_token_management():
    """Demonstrate token tracking and management."""
    print_section("DEMO 2: Token Management")
    
    # Create token manager for Pro tier user
    tm = TokenManager(user_id="demo_user", tier="pro")
    print(f"Created TokenManager for user 'demo_user' (Pro tier)")
    print(f"Monthly limit: {tm.monthly_limit:,} tokens\n")
    
    # Simulate usage
    print("Simulating token usage...")
    tm.track_usage(500_000)
    stats = tm.get_usage_stats()
    print(f"After 500K usage: {stats['used']:,} used, {stats['remaining']:,} remaining ({stats['percentage']}%)")
    
    tm.track_usage(3_500_000)
    stats = tm.get_usage_stats()
    print(f"After 4M total usage: {stats['used']:,} used, {stats['remaining']:,} remaining ({stats['percentage']}%)")
    
    # Check budget status
    has_budget, message = tm.get_budget_status()
    print(f"\nBudget status: {message}")
    

def demo_request_routing():
    """Demonstrate smart request routing."""
    print_section("DEMO 3: Smart Request Routing")
    
    tm = TokenManager(user_id="routing_demo", tier="empire")
    router = RequestRouter(token_manager=tm)
    
    # Test 1: Simple local task
    print("Test 1: Simple categorization task")
    result = router.route_request(
        task_type="categorize_product",
        prompt="Categorize: Blue Nike running shoes, size 10, men's athletic wear",
        complexity="low"
    )
    print(f"  Task type: categorize_product")
    print(f"  Complexity: {result['complexity']}")
    print(f"  Selected model: {result['model']['model_name']}")
    print(f"  Provider: {result['model']['provider']}")
    print(f"  Is local: {result['model']['is_local']}")
    print(f"  Estimated tokens: {result['estimated_tokens']}")
    print()
    
    # Test 2: Complex cloud task
    print("Test 2: Complex content generation task")
    result = router.route_request(
        task_type="content_generation",
        prompt="Write a compelling 200-word product description for a vintage Rolex "
               "Submariner watch from 1965, highlighting its history and value.",
        complexity="high"
    )
    print(f"  Task type: content_generation")
    print(f"  Complexity: {result['complexity']}")
    print(f"  Selected model: {result['model']['model_name']}")
    print(f"  Provider: {result['model']['provider']}")
    print(f"  Is local: {result['model']['is_local']}")
    print(f"  Estimated tokens: {result['estimated_tokens']}")


def demo_budget_fallback():
    """Demonstrate automatic fallback when budget exceeded."""
    print_section("DEMO 4: Budget Exhaustion & Automatic Fallback")
    
    # Create user with limited budget (Free tier)
    tm = TokenManager(user_id="limited_user", tier="free")
    print(f"Created Free tier user with {tm.monthly_limit:,} token limit")
    
    # Exhaust the budget
    tm.track_usage(500_000)
    print(f"Exhausted all tokens: {tm.get_usage_stats()['percentage']}% used\n")
    
    # Try a complex task - should fallback to local
    router = RequestRouter(token_manager=tm)
    result = router.route_request(
        task_type="content_generation",
        prompt="Generate a product description",
        complexity="high"
    )
    
    print("Requested complex content generation (normally uses cloud):")
    print(f"  Fallback used: {result['fallback_used']}")
    print(f"  Selected model: {result['model']['model_name']}")
    print(f"  Is local: {result['model']['is_local']}")
    print(f"  Budget status: {'EXCEEDED - Using free local models' if result['fallback_used'] else 'OK'}")


def demo_base_agent():
    """Demonstrate BaseAgent usage."""
    print_section("DEMO 5: BaseAgent Integration")
    
    # Create agent
    agent = BaseAgent(user_id="agent_demo", tier="pro")
    print(f"Created BaseAgent for Pro tier user")
    print(f"Safeguards enabled: {agent.enable_safeguards}")
    print()
    
    # Run inference
    time.sleep(0.2)  # Avoid rate limit
    print("Running inference: Product categorization")
    result = agent.run_inference(
        task_type="categorize_product",
        prompt="Apple iPhone 15 Pro Max, 256GB, Natural Titanium",
        complexity="low"
    )
    
    if result['success']:
        print(f"  Success: {result['success']}")
        print(f"  Model: {result['model']}")
        print(f"  Is local: {result['is_local']}")
        print(f"  Response: {result['response']}")
    
    # Check agent status
    status = agent.get_status()
    print(f"\nAgent Status:")
    print(f"  User ID: {status['user_id']}")
    print(f"  Tier: {status['tier']}")
    print(f"  Tokens used: {status['token_usage']['used']}")
    print(f"  Emergency stop active: {not status['emergency_stop']['is_running']}")


def demo_custom_agent():
    """Demonstrate creating a custom agent."""
    print_section("DEMO 6: Custom Agent Implementation")
    
    class ProductAgent(BaseAgent):
        """Custom agent for product-related tasks."""
        
        def categorize(self, product_description: str):
            """Categorize a product."""
            return self.run_inference(
                task_type="categorize_product",
                prompt=f"Categorize: {product_description}",
                complexity="low"
            )
        
        def generate_description(self, product_name: str, details: str = ""):
            """Generate a compelling product description."""
            prompt = f"Write a compelling product description for: {product_name}"
            if details:
                prompt += f"\nDetails: {details}"
            return self.run_inference(
                task_type="content_generation",
                prompt=prompt,
                complexity="high"
            )
        
        def optimize_price(self, product_info: str, market_data: str):
            """Optimize product pricing."""
            return self.run_inference(
                task_type="price_optimization",
                prompt=f"Product: {product_info}\nMarket: {market_data}\nOptimal price?",
                complexity="high"
            )
    
    # Use the custom agent
    print("Created custom ProductAgent class")
    product_agent = ProductAgent(user_id="product_user", tier="empire")
    print(f"Initialized for Empire tier user\n")
    
    # Categorize a product
    time.sleep(0.2)
    print("1. Categorizing product...")
    result = product_agent.categorize("Vintage Rolex Submariner 1965")
    print(f"   Success: {result['success']}, Model: {result.get('model', 'N/A')}")
    
    # Generate description
    time.sleep(0.2)
    print("2. Generating description...")
    result = product_agent.generate_description(
        "Vintage Rolex Submariner",
        "1965 model, excellent condition, original box"
    )
    print(f"   Success: {result['success']}, Model: {result.get('model', 'N/A')}")
    
    # Check token usage
    stats = product_agent.token_manager.get_usage_stats()
    print(f"\nToken usage: {stats['used']} tokens used ({stats['percentage']}%)")


def demo_safety_features():
    """Demonstrate safety features."""
    print_section("DEMO 7: Safety Features")
    
    # Emergency stop
    agent = BaseAgent(user_id="safety_demo", tier="lite")
    print("1. Emergency Stop:")
    print(f"   Agent running: {agent.emergency_stop.is_running}")
    
    agent.trigger_emergency_stop("Demonstrating emergency stop")
    print(f"   After trigger: {agent.emergency_stop.is_running}")
    
    time.sleep(0.2)
    result = agent.run_inference("test", "test")
    print(f"   Inference blocked: {not result['success']}")
    print()
    
    # Quota checking
    quota_agent = BaseAgent(user_id="quota_demo", tier="free")
    quota_agent.token_manager.track_usage(450_000)  # 90% usage
    
    print("2. Quota Monitoring:")
    quota_status = quota_agent.check_quota_status()
    print(f"   Usage: {quota_agent.token_manager.get_usage_stats()['percentage']}%")
    print(f"   Can use local: {quota_status['can_use_local']}")
    print(f"   Can use cloud: {quota_status['can_use_cloud']}")
    print(f"   Status: {quota_status['message']}")


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 70)
    print("  EMPIREBOX HYBRID AI SYSTEM - COMPLETE DEMONSTRATION")
    print("=" * 70)
    print("\nThis demonstration showcases all key features of the system.")
    print("Watch how the system intelligently manages AI resources!")
    
    try:
        demo_subscription_tiers()
        demo_token_management()
        demo_request_routing()
        demo_budget_fallback()
        demo_base_agent()
        demo_custom_agent()
        demo_safety_features()
        
        print_section("DEMONSTRATION COMPLETE")
        print("The EmpireBox Hybrid AI System is ready for production use!")
        print("\nKey Takeaways:")
        print("  ✓ Flexible subscription tiers (Free to Empire)")
        print("  ✓ Smart routing saves money (local vs cloud)")
        print("  ✓ Automatic fallback prevents service disruption")
        print("  ✓ Built-in safety features protect the system")
        print("  ✓ Easy to extend with custom agents")
        print("\nSee EMPIREBOX_SYSTEM_README.md for full documentation.")
        print()
        
    except KeyboardInterrupt:
        print("\n\nDemonstration interrupted by user.")
    except Exception as e:
        print(f"\n\nError during demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
