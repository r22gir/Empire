"""
AI service for SupportForge - provides intelligent features like smart replies,
categorization, and sentiment analysis.
"""
from typing import Dict, Any, List, Optional
import os
import json


class AIService:
    """Service for AI-powered support features."""
    
    def __init__(self):
        """Initialize AI service."""
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.ai_enabled = bool(self.openai_api_key)
    
    async def suggest_response(
        self,
        ticket_subject: str,
        conversation_history: List[Dict[str, str]],
        customer_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate AI-powered response suggestion.
        
        Args:
            ticket_subject: Subject of the ticket
            conversation_history: List of previous messages
            customer_context: Additional customer information
        
        Returns:
            Dictionary with suggested response and confidence score
        """
        if not self.ai_enabled:
            return {
                "suggested_response": "AI suggestions are not enabled. Please configure OpenAI API key.",
                "confidence": 0.0,
                "suggestions": []
            }
        
        # Build context for AI
        context = f"Ticket Subject: {ticket_subject}\n\n"
        context += "Conversation History:\n"
        
        for msg in conversation_history[-5:]:  # Last 5 messages for context
            sender = msg.get("sender_type", "unknown")
            content = msg.get("content", "")
            context += f"{sender}: {content}\n"
        
        if customer_context:
            context += f"\nCustomer Context: {json.dumps(customer_context, indent=2)}\n"
        
        # In a real implementation, this would call OpenAI API
        # For now, return a placeholder
        return {
            "suggested_response": "Thank you for contacting support. I'm looking into your issue and will get back to you shortly with a solution.",
            "confidence": 0.85,
            "suggestions": [
                "Thank you for reaching out. Let me help you with that.",
                "I understand your concern. Here's what we can do...",
                "I've reviewed your account and found the following..."
            ],
            "tone": "professional",
            "estimated_response_time": "2-3 minutes"
        }
    
    async def categorize_ticket(
        self,
        subject: str,
        content: str
    ) -> Dict[str, Any]:
        """
        Auto-categorize ticket based on content.
        
        Args:
            subject: Ticket subject
            content: Ticket content
        
        Returns:
            Dictionary with category, tags, and priority
        """
        if not self.ai_enabled:
            return {
                "category": "general",
                "tags": [],
                "priority": "normal",
                "confidence": 0.0
            }
        
        # Simple keyword-based categorization for MVP
        subject_lower = subject.lower()
        content_lower = content.lower()
        
        categories = {
            "billing": ["billing", "invoice", "payment", "charge", "refund"],
            "technical": ["error", "bug", "not working", "crash", "issue"],
            "account": ["login", "password", "account", "access"],
            "feature": ["feature", "request", "suggestion", "enhancement"]
        }
        
        detected_category = "general"
        detected_tags = []
        
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in subject_lower or keyword in content_lower:
                    detected_category = category
                    detected_tags.append(keyword)
                    break
        
        # Determine priority based on keywords
        urgent_keywords = ["urgent", "critical", "emergency", "down", "broken"]
        priority = "urgent" if any(kw in subject_lower or kw in content_lower for kw in urgent_keywords) else "normal"
        
        return {
            "category": detected_category,
            "tags": list(set(detected_tags)),
            "priority": priority,
            "confidence": 0.7
        }
    
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of customer message.
        
        Args:
            text: Message text to analyze
        
        Returns:
            Dictionary with sentiment analysis results
        """
        if not self.ai_enabled:
            return {
                "sentiment": "neutral",
                "score": 0.0,
                "is_frustrated": False
            }
        
        # Simple keyword-based sentiment for MVP
        text_lower = text.lower()
        
        negative_keywords = ["angry", "frustrated", "disappointed", "terrible", "awful", "worst"]
        positive_keywords = ["thank", "great", "excellent", "happy", "appreciate"]
        
        negative_count = sum(1 for kw in negative_keywords if kw in text_lower)
        positive_count = sum(1 for kw in positive_keywords if kw in text_lower)
        
        if negative_count > positive_count:
            sentiment = "negative"
            score = -0.5
            is_frustrated = negative_count >= 2
        elif positive_count > negative_count:
            sentiment = "positive"
            score = 0.5
            is_frustrated = False
        else:
            sentiment = "neutral"
            score = 0.0
            is_frustrated = False
        
        return {
            "sentiment": sentiment,
            "score": score,
            "is_frustrated": is_frustrated,
            "escalate_recommended": is_frustrated
        }
    
    async def summarize_conversation(
        self,
        messages: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Summarize a ticket conversation.
        
        Args:
            messages: List of conversation messages
        
        Returns:
            Dictionary with summary and key points
        """
        if not self.ai_enabled or len(messages) == 0:
            return {
                "summary": "No messages to summarize",
                "key_points": [],
                "resolution": None
            }
        
        # Simple summary for MVP
        first_message = messages[0].get("content", "")
        last_message = messages[-1].get("content", "") if len(messages) > 1 else ""
        
        return {
            "summary": f"Customer initially reported: {first_message[:100]}...",
            "key_points": [
                f"Total messages: {len(messages)}",
                f"Latest update: {last_message[:50]}..." if last_message else "Awaiting response"
            ],
            "resolution": "Pending" if len(messages) < 3 else "In progress"
        }
    
    async def search_knowledge_base(
        self,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search knowledge base for relevant articles.
        
        Args:
            query: Search query
            limit: Maximum number of results
        
        Returns:
            List of relevant article suggestions
        """
        # Placeholder for KB search - would integrate with Elasticsearch
        return [
            {
                "article_id": "kb-001",
                "title": "Getting Started Guide",
                "relevance_score": 0.9,
                "excerpt": "Learn how to set up your account..."
            }
        ]
