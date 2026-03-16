"""
AI service for interfacing with Empire AI routing.
Routes through ai_router.py (Grok -> Claude -> Groq -> Ollama).
"""
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User


class AIService:
    """
    Service for AI-powered features using Empire AI routing.
    Routes all calls through app.services.max.ai_router.
    """

    def __init__(self, user: User, db: Optional[AsyncSession] = None):
        self.user = user
        self.db = db

    async def _call_ai(self, prompt: str, system: str = "You are a helpful business assistant.", max_tokens: int = 500) -> str:
        """Route AI call through Empire AI router."""
        try:
            from app.services.max.ai_router import route_ai_call
            result = await route_ai_call(
                messages=[{"role": "user", "content": prompt}],
                system=system,
                max_tokens=max_tokens
            )
            return result.get("content", "")
        except Exception:
            return ""

    async def generate_description(self, product_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate product description using AI."""
        title = product_info.get('title', 'item')
        category = product_info.get('category', '')
        condition = product_info.get('condition', 'good')

        prompt = f"Write a compelling 2-3 sentence product listing description for: {title}. Category: {category}. Condition: {condition}."
        description = await self._call_ai(prompt, system="You are an expert product copywriter. Write concise, compelling descriptions.")

        if not description:
            description = f"High-quality {title} in {condition} condition."

        return {
            "description": description,
            "tokens_used": len(description.split()) * 2,
            "input_tokens": len(prompt.split()),
            "output_tokens": len(description.split())
        }

    async def enhance_description(self, current_description: str) -> Dict[str, Any]:
        """Enhance existing product description."""
        prompt = f"Improve this product description with better details and SEO keywords. Keep it concise:\n\n{current_description}"
        enhanced = await self._call_ai(prompt, system="You are an expert product copywriter. Enhance descriptions for better sales.")

        if not enhanced:
            enhanced = current_description

        return {
            "enhanced_description": enhanced,
            "tokens_used": len(enhanced.split()) * 2,
            "input_tokens": len(current_description.split()),
            "output_tokens": len(enhanced.split())
        }

    async def suggest_price(self, product_info: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest pricing for a product."""
        title = product_info.get('title', 'item')
        category = product_info.get('category', '')
        condition = product_info.get('condition', 'good')

        prompt = f"Suggest a fair market price for: {title}. Category: {category}. Condition: {condition}. Reply with JSON: {{\"price\": X, \"min\": X, \"max\": X, \"reasoning\": \"...\"}}"
        response = await self._call_ai(prompt, system="You are a pricing expert. Always respond with valid JSON.")

        # Try to parse JSON response, fallback to defaults
        try:
            import json
            data = json.loads(response)
            return {
                "suggested_price": data.get("price", 49.99),
                "price_range": {"min": data.get("min", 39.99), "max": data.get("max", 59.99)},
                "reasoning": data.get("reasoning", "Based on market analysis"),
                "tokens_used": len(response.split()) * 2,
            }
        except Exception:
            return {
                "suggested_price": 49.99,
                "price_range": {"min": 39.99, "max": 59.99},
                "reasoning": "Default estimate — AI pricing unavailable",
                "tokens_used": 0,
            }

    async def draft_message_response(
        self,
        message_content: str,
        context: Optional[str] = None
    ) -> str:
        """Generate AI draft response for a message."""
        ctx = f"\nContext: {context}" if context else ""
        prompt = f"Draft a professional, friendly reply to this customer message:{ctx}\n\nMessage: {message_content}"

        response = await self._call_ai(prompt, system="You are a professional business assistant. Write friendly, helpful responses.")

        if not response:
            response = f"Thank you for reaching out! I'll review your message and get back to you shortly."

        return response
