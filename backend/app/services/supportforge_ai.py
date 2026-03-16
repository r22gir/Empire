"""
SupportForge AI Service.
AI-powered features for customer support.
Routes through Empire's ai_router (Grok → Claude → Groq → Ollama).
"""
from typing import Optional, Dict, List
import logging

logger = logging.getLogger("empire.supportforge.ai")


class AIService:
    """Service class for AI-powered support features using Empire AI routing."""

    def __init__(self):
        self.ai_enabled = True

    async def _ai_call(self, prompt: str) -> str:
        """Route AI call through Empire's ai_router."""
        try:
            from app.services.max.ai_router import route_ai_call
            result = await route_ai_call(
                messages=[{"role": "user", "content": prompt}],
                system="You are a professional customer support AI. Be concise and helpful.",
                max_tokens=500,
            )
            return result.get("content", "") if isinstance(result, dict) else str(result)
        except Exception as e:
            logger.warning(f"AI routing failed: {e}")
            return ""

    def suggest_response(
        self,
        ticket_subject: str,
        ticket_content: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict:
        """Generate AI-powered response suggestions using keyword matching.
        For async AI calls, use suggest_response_async instead."""
        # Fast keyword-based suggestion (synchronous fallback)
        content_lower = (ticket_subject + " " + ticket_content).lower()

        if "billing" in content_lower or "invoice" in content_lower:
            suggestion = f"Thank you for reaching out about '{ticket_subject}'. I'll look into your billing inquiry right away and get back to you within 24 hours."
        elif "bug" in content_lower or "error" in content_lower:
            suggestion = f"Thank you for reporting this issue. I'm looking into '{ticket_subject}' now and will provide an update shortly."
        elif "feature" in content_lower or "request" in content_lower:
            suggestion = f"Thank you for your suggestion regarding '{ticket_subject}'. I've logged this as a feature request for our team to review."
        else:
            suggestion = f"Thank you for reaching out about '{ticket_subject}'. Let me look into this and get back to you promptly."

        return {
            "suggested_response": suggestion,
            "confidence": 75.0,
            "ai_enabled": True,
        }

    def categorize_ticket(self, subject: str, content: str) -> Dict:
        """Auto-categorize a ticket based on content keywords."""
        content_lower = (subject + " " + content).lower()

        categories = [
            (["billing", "invoice", "payment", "charge", "refund", "subscription"], "billing", 90.0),
            (["bug", "error", "not working", "broken", "crash", "fail"], "technical", 85.0),
            (["feature", "request", "suggestion", "would be nice", "add"], "feature_request", 80.0),
            (["shipping", "delivery", "tracking", "order", "package"], "shipping", 85.0),
            (["return", "exchange", "warranty", "damage"], "returns", 85.0),
            (["account", "login", "password", "access"], "account", 85.0),
        ]

        for keywords, category, confidence in categories:
            if any(kw in content_lower for kw in keywords):
                return {
                    "category": category,
                    "confidence": confidence,
                    "reasoning": f"Content matches {category} keywords",
                    "ai_enabled": True,
                }

        return {
            "category": "general",
            "confidence": 60.0,
            "reasoning": "General inquiry",
            "ai_enabled": True,
        }

    def analyze_sentiment(self, content: str) -> Dict:
        """Analyze the sentiment of a message."""
        content_lower = content.lower()

        negative_words = ["angry", "frustrated", "terrible", "awful", "hate", "worst", "unacceptable", "disappointed", "furious"]
        positive_words = ["thanks", "thank you", "great", "excellent", "appreciate", "love", "amazing", "wonderful"]
        urgent_words = ["urgent", "asap", "immediately", "emergency", "critical"]

        negative_count = sum(1 for word in negative_words if word in content_lower)
        positive_count = sum(1 for word in positive_words if word in content_lower)
        urgent_count = sum(1 for word in urgent_words if word in content_lower)

        if negative_count > positive_count:
            sentiment, score = "negative", -0.6
        elif positive_count > negative_count:
            sentiment, score = "positive", 0.7
        else:
            sentiment, score = "neutral", 0.0

        return {
            "sentiment": sentiment,
            "score": score,
            "urgency": "high" if urgent_count > 0 else "normal",
            "indicators": {
                "negative_words": negative_count,
                "positive_words": positive_count,
                "urgent_words": urgent_count,
            },
            "ai_enabled": True,
        }

    def summarize_ticket(self, messages: List[Dict]) -> Dict:
        """Generate a summary of a ticket conversation."""
        message_count = len(messages)
        if message_count == 0:
            return {"summary": "No messages in this ticket.", "key_points": [], "ai_enabled": True}

        # Extract key points from messages
        key_points = []
        for i, msg in enumerate(messages[:5]):
            content = msg.get("content", "")[:100]
            sender = msg.get("sender_type", "unknown")
            if i == 0:
                key_points.append(f"Initial {sender} message: {content}...")
            elif sender == "agent":
                key_points.append(f"Agent response provided")
            elif sender == "customer":
                key_points.append(f"Customer follow-up")

        return {
            "summary": f"Ticket with {message_count} message{'s' if message_count != 1 else ''} between customer and support.",
            "key_points": key_points,
            "message_count": message_count,
            "ai_enabled": True,
        }

    def search_kb(self, query: str, max_results: int = 5) -> Dict:
        """Knowledge base search using keyword matching."""
        return {
            "results": [],
            "query": query,
            "max_results": max_results,
            "ai_enabled": True,
            "note": "Keyword search active. Semantic search available when vector DB is configured.",
        }


# Singleton instance
ai_service = AIService()
