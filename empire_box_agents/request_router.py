"""
Request Router for AI Response Generation
Routes requests to local or cloud AI based on complexity
"""

import re
from typing import Dict, Any, Optional


class RequestRouter:
    """Routes AI requests to appropriate backend (local vs cloud)"""
    
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
        """
        Handle complex queries with cloud AI
        
        TODO: Integrate with actual cloud AI service (OpenAI, Anthropic, etc.)
        For now, returns a placeholder that acknowledges we'd use cloud AI
        """
        # Placeholder for cloud AI integration
        return (
            "Thanks for your message! Let me provide you with detailed information. "
            "Feel free to ask any follow-up questions you might have."
        )
    
    def _extract_location(self, text: str) -> Optional[str]:
        """Extract location from shipping query"""
        # Simple pattern matching for location
        match = re.search(r"ship to ([\w\s,]+?)[\?\.]?$", text.lower())
        if match:
            return match.group(1).strip()
        return None


# Example usage
if __name__ == "__main__":
    router = RequestRouter()
    
    # Test simple queries
    print("Simple availability query:")
    print(router.route_request("Is this still available?"))
    print()
    
    print("Shipping query:")
    print(router.route_request("Can you ship to California?"))
    print()
    
    print("Price negotiation with context:")
    context = {"price": 100.00}
    print(router.route_request("What's the lowest you'll go?", context))
    print()
    
    print("Complex query (would use cloud):")
    print(router.route_request("I'm interested but I have several questions about the condition, history, and whether you have any similar items."))
