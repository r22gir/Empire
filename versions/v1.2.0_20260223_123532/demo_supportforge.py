#!/usr/bin/env python3
"""
SupportForge Demo Script
Demonstrates core functionality of the SupportForge platform.
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.supportforge_ai import ai_service

def demo_ai_features():
    """Demonstrate AI-powered features."""
    print("\n" + "="*60)
    print("SupportForge AI Features Demo")
    print("="*60)
    
    # 1. Response Suggestion
    print("\n1. AI Response Suggestion")
    print("-" * 40)
    suggestion = ai_service.suggest_response(
        ticket_subject="Need help with billing",
        ticket_content="I was charged twice for my subscription this month."
    )
    print(f"Subject: Need help with billing")
    print(f"Content: I was charged twice for my subscription this month.")
    print(f"\nSuggested Response:")
    print(f"  {suggestion['suggested_response']}")
    print(f"  Confidence: {suggestion['confidence']}%")
    
    # 2. Ticket Categorization
    print("\n2. Auto-Categorization")
    print("-" * 40)
    category = ai_service.categorize_ticket(
        subject="Feature Request",
        content="It would be great to have dark mode support"
    )
    print(f"Subject: Feature Request")
    print(f"Content: It would be great to have dark mode support")
    print(f"\nCategory: {category['category']}")
    print(f"Confidence: {category['confidence']}%")
    print(f"Reasoning: {category['reasoning']}")
    
    # 3. Sentiment Analysis
    print("\n3. Sentiment Analysis")
    print("-" * 40)
    
    messages = [
        "Thank you so much for the quick help!",
        "This is unacceptable! I need this fixed immediately!",
        "Could you please help me understand this feature?"
    ]
    
    for msg in messages:
        sentiment = ai_service.analyze_sentiment(msg)
        print(f"\nMessage: '{msg}'")
        print(f"  Sentiment: {sentiment['sentiment']}")
        print(f"  Score: {sentiment['score']}")
        print(f"  Urgency: {sentiment['urgency']}")
    
    # 4. Ticket Summarization
    print("\n4. Ticket Summarization")
    print("-" * 40)
    messages_list = [
        {"content": "I can't access my dashboard", "sender_type": "customer"},
        {"content": "Let me help you with that", "sender_type": "agent"},
        {"content": "Please try clearing your cache", "sender_type": "agent"},
        {"content": "That worked! Thank you!", "sender_type": "customer"}
    ]
    summary = ai_service.summarize_ticket(messages_list)
    print(f"Conversation with {len(messages_list)} messages")
    print(f"\nSummary: {summary['summary']}")
    print(f"Key Points:")
    for point in summary['key_points']:
        print(f"  - {point}")
    
    print("\n" + "="*60)
    print("Demo Complete!")
    print("="*60)
    
    if not ai_service.ai_enabled:
        print("\nNote: AI features are in demo mode.")
        print("To enable full AI capabilities:")
        print("1. Set OPENAI_API_KEY environment variable")
        print("2. Set AI_FEATURES_ENABLED=true")
        print("3. Implement OpenAI integration in services/supportforge_ai.py")


def show_api_info():
    """Display API endpoint information."""
    print("\n" + "="*60)
    print("SupportForge API Endpoints")
    print("="*60)
    
    endpoints = {
        "Tickets": [
            "POST   /api/v1/tickets              - Create ticket",
            "GET    /api/v1/tickets              - List tickets",
            "GET    /api/v1/tickets/{id}         - Get ticket details",
            "PATCH  /api/v1/tickets/{id}         - Update ticket",
            "POST   /api/v1/tickets/{id}/messages - Add message",
            "POST   /api/v1/tickets/{id}/assign  - Assign agent",
        ],
        "Customers": [
            "POST   /api/v1/customers            - Create customer",
            "GET    /api/v1/customers            - List customers",
            "GET    /api/v1/customers/{id}       - Get customer",
            "GET    /api/v1/customers/{id}/tickets - Get customer tickets",
        ],
        "Knowledge Base": [
            "POST   /api/v1/kb/articles          - Create article",
            "GET    /api/v1/kb/articles          - List articles",
            "GET    /api/v1/kb/articles/{slug}   - Get article",
            "POST   /api/v1/kb/search            - Search articles",
            "POST   /api/v1/kb/categories        - Create category",
        ],
        "AI Features": [
            "POST   /api/v1/ai/suggest-response  - Get AI response suggestion",
            "POST   /api/v1/ai/categorize        - Auto-categorize ticket",
            "POST   /api/v1/ai/sentiment         - Analyze sentiment",
            "POST   /api/v1/ai/summarize         - Summarize ticket",
            "POST   /api/v1/ai/search-kb         - AI-powered KB search",
        ]
    }
    
    for category, endpoint_list in endpoints.items():
        print(f"\n{category}:")
        for endpoint in endpoint_list:
            print(f"  {endpoint}")
    
    print("\n" + "="*60)
    print("Start the API server:")
    print("  cd backend")
    print("  uvicorn app.main:app --reload")
    print("\nAPI Documentation:")
    print("  http://localhost:8000/docs")
    print("="*60)


if __name__ == "__main__":
    print("\n🚀 SupportForge - Enterprise Customer Support Platform")
    print("Part of the Empire Box Ecosystem\n")
    
    # Run demos
    demo_ai_features()
    show_api_info()
    
    print("\n✅ SupportForge is ready for development!")
    print("📚 See SUPPORTFORGE_README.md for complete documentation\n")
