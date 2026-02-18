"""
Demo script for SupportForge - Customer Support Platform

This script demonstrates the core functionality of SupportForge including:
- Creating tenants, agents, and customers
- Creating and managing tickets
- AI-powered features
- Empire product integration
"""

import uuid
from datetime import datetime


class SupportForgeDemo:
    """Demo class showcasing SupportForge functionality."""
    
    def __init__(self):
        """Initialize the demo."""
        self.tenant_id = uuid.uuid4()
        self.agent_id = uuid.uuid4()
        self.customer_id = uuid.uuid4()
        self.ticket_id = uuid.uuid4()
    
    def demo_tenant_creation(self):
        """Demonstrate tenant creation."""
        print("\n" + "="*60)
        print("1. TENANT CREATION")
        print("="*60)
        
        tenant = {
            "id": str(self.tenant_id),
            "name": "Acme Corp Support",
            "subdomain": "acme",
            "plan": "professional",
            "settings": {
                "business_hours": "9am-5pm EST",
                "languages": ["en", "es"],
                "auto_assign": True
            },
            "created_at": datetime.now().isoformat()
        }
        
        print(f"\n✓ Created tenant: {tenant['name']}")
        print(f"  Subdomain: {tenant['subdomain']}.supportforge.com")
        print(f"  Plan: {tenant['plan']}")
        print(f"  Tenant ID: {tenant['id']}")
        
        return tenant
    
    def demo_agent_creation(self):
        """Demonstrate agent creation."""
        print("\n" + "="*60)
        print("2. AGENT CREATION")
        print("="*60)
        
        agent = {
            "id": str(self.agent_id),
            "tenant_id": str(self.tenant_id),
            "name": "Sarah Johnson",
            "email": "sarah@acmecorp.com",
            "role": "agent",
            "departments": ["technical", "billing"],
            "skills": ["python", "api", "troubleshooting"],
            "status": "online",
            "max_concurrent_tickets": 10
        }
        
        print(f"\n✓ Created agent: {agent['name']}")
        print(f"  Email: {agent['email']}")
        print(f"  Departments: {', '.join(agent['departments'])}")
        print(f"  Skills: {', '.join(agent['skills'])}")
        print(f"  Status: {agent['status']}")
        
        return agent
    
    def demo_customer_creation(self):
        """Demonstrate customer creation."""
        print("\n" + "="*60)
        print("3. CUSTOMER CREATION")
        print("="*60)
        
        customer = {
            "id": str(self.customer_id),
            "tenant_id": str(self.tenant_id),
            "name": "John Smith",
            "email": "john@example.com",
            "company": "Example Inc",
            "empire_product_id": str(uuid.uuid4()),
            "empire_product_type": "contractorforge",
            "metadata": {
                "industry": "construction",
                "company_size": "50-100"
            },
            "tags": ["premium", "beta-tester"]
        }
        
        print(f"\n✓ Created customer: {customer['name']}")
        print(f"  Email: {customer['email']}")
        print(f"  Company: {customer['company']}")
        print(f"  Empire Product: {customer['empire_product_type']}")
        print(f"  Tags: {', '.join(customer['tags'])}")
        
        return customer
    
    def demo_ticket_creation(self):
        """Demonstrate ticket creation and workflow."""
        print("\n" + "="*60)
        print("4. TICKET CREATION & WORKFLOW")
        print("="*60)
        
        ticket = {
            "id": str(self.ticket_id),
            "tenant_id": str(self.tenant_id),
            "ticket_number": 1001,
            "customer_id": str(self.customer_id),
            "subject": "Cannot export project data to PDF",
            "status": "new",
            "priority": "high",
            "channel": "email",
            "category": "technical",
            "tags": ["api", "export", "pdf"],
            "created_at": datetime.now().isoformat()
        }
        
        print(f"\n✓ Created ticket #{ticket['ticket_number']}")
        print(f"  Subject: {ticket['subject']}")
        print(f"  Status: {ticket['status']}")
        print(f"  Priority: {ticket['priority']}")
        print(f"  Channel: {ticket['channel']}")
        print(f"  Category: {ticket['category']}")
        
        # Simulate workflow
        print("\n  Workflow simulation:")
        print("  → Auto-assigned to agent Sarah Johnson")
        print("  → Status changed: new → open")
        print("  → AI categorization: technical, export, pdf")
        print("  → Priority elevated: normal → high (urgent keywords detected)")
        
        return ticket
    
    def demo_ai_features(self, ticket):
        """Demonstrate AI-powered features."""
        print("\n" + "="*60)
        print("5. AI-POWERED FEATURES")
        print("="*60)
        
        # AI Response Suggestion
        print("\n📝 AI Response Suggestion:")
        suggestion = {
            "suggested_response": "Thank you for contacting support about the PDF export issue. "
                                "I've reviewed your account and see you're using ContractorForge. "
                                "The PDF export feature requires the latest version of the app. "
                                "Let me help you update and test the export functionality.",
            "confidence": 0.87,
            "tone": "professional",
            "estimated_response_time": "2-3 minutes"
        }
        print(f"  Confidence: {suggestion['confidence']*100:.0f}%")
        print(f"  Response: {suggestion['suggested_response'][:100]}...")
        
        # Sentiment Analysis
        print("\n🎭 Sentiment Analysis:")
        sentiment = {
            "sentiment": "negative",
            "score": -0.4,
            "is_frustrated": True,
            "escalate_recommended": True
        }
        print(f"  Sentiment: {sentiment['sentiment']}")
        print(f"  Frustration detected: {sentiment['is_frustrated']}")
        print(f"  Recommendation: Escalate to senior agent")
        
        # Auto-Categorization
        print("\n🏷️  Auto-Categorization:")
        categorization = {
            "category": "technical",
            "tags": ["export", "pdf", "api"],
            "priority": "high",
            "confidence": 0.82
        }
        print(f"  Category: {categorization['category']}")
        print(f"  Tags: {', '.join(categorization['tags'])}")
        print(f"  Suggested Priority: {categorization['priority']}")
        
        # Knowledge Base Search
        print("\n📚 Knowledge Base Search:")
        kb_results = [
            {
                "title": "How to Export Projects to PDF",
                "relevance": 0.95,
                "excerpt": "Learn how to export your project data as PDF..."
            },
            {
                "title": "PDF Export Troubleshooting",
                "relevance": 0.88,
                "excerpt": "Common issues and solutions for PDF exports..."
            }
        ]
        for i, result in enumerate(kb_results, 1):
            print(f"  {i}. {result['title']} (relevance: {result['relevance']*100:.0f}%)")
        
        return {
            "suggestion": suggestion,
            "sentiment": sentiment,
            "categorization": categorization,
            "kb_results": kb_results
        }
    
    def demo_empire_integration(self, customer):
        """Demonstrate Empire product integration."""
        print("\n" + "="*60)
        print("6. EMPIRE PRODUCT INTEGRATION")
        print("="*60)
        
        context = {
            "has_empire_product": True,
            "product_type": "contractorforge",
            "product_id": customer["empire_product_id"],
            "subscription_status": "active",
            "subscription_plan": "professional",
            "projects_count": 12,
            "recent_projects": [
                "Kitchen Remodel - $45,000",
                "Bathroom Renovation - $18,500",
                "Deck Construction - $12,000"
            ],
            "usage_this_month": {
                "ai_requests": 247,
                "estimates_created": 15,
                "cost": 24.70
            },
            "account_health": "good",
            "last_login": "2 hours ago",
            "support_history": {
                "total_tickets": 3,
                "resolved_tickets": 3,
                "avg_resolution_time": "4.2 hours",
                "satisfaction_score": 4.8
            }
        }
        
        print(f"\n✓ Empire Product Context Retrieved")
        print(f"  Product: {context['product_type'].title()}")
        print(f"  Subscription: {context['subscription_plan']} ({context['subscription_status']})")
        print(f"  Projects: {context['projects_count']} total")
        print(f"  Recent Projects:")
        for project in context['recent_projects'][:3]:
            print(f"    - {project}")
        print(f"\n  Monthly Usage:")
        print(f"    AI Requests: {context['usage_this_month']['ai_requests']}")
        print(f"    Estimates: {context['usage_this_month']['estimates_created']}")
        print(f"    Cost: ${context['usage_this_month']['cost']:.2f}")
        print(f"\n  Support History:")
        print(f"    Total Tickets: {context['support_history']['total_tickets']}")
        print(f"    Avg Resolution: {context['support_history']['avg_resolution_time']}")
        print(f"    CSAT Score: {context['support_history']['satisfaction_score']}/5.0")
        
        return context
    
    def demo_conversation_flow(self):
        """Demonstrate a complete ticket conversation."""
        print("\n" + "="*60)
        print("7. TICKET CONVERSATION FLOW")
        print("="*60)
        
        messages = [
            {
                "sender_type": "customer",
                "sender_name": "John Smith",
                "content": "Hi, I'm trying to export a project to PDF but I keep getting an error. "
                          "It says 'Export failed: Unknown error'. This is urgent as I need to "
                          "send this to my client today!",
                "timestamp": "2026-02-18 09:15:00",
                "is_internal_note": False
            },
            {
                "sender_type": "system",
                "content": "Ticket auto-categorized as 'technical'. Priority set to 'high'. "
                          "Assigned to Sarah Johnson.",
                "timestamp": "2026-02-18 09:15:02",
                "is_internal_note": True
            },
            {
                "sender_type": "agent",
                "sender_name": "Sarah Johnson",
                "content": "Hi John, thank you for reaching out! I see you're experiencing issues "
                          "with PDF export. I've checked your account and noticed you're on version 2.1. "
                          "There was a known issue with PDF exports in that version which was fixed in 2.2. "
                          "Could you please update your app and try again?",
                "timestamp": "2026-02-18 09:18:30",
                "is_internal_note": False,
                "ai_suggested": True
            },
            {
                "sender_type": "customer",
                "sender_name": "John Smith",
                "content": "Thanks for the quick response! I updated to 2.2 and the export works perfectly now. "
                          "Really appreciate your help!",
                "timestamp": "2026-02-18 09:25:15",
                "is_internal_note": False
            },
            {
                "sender_type": "agent",
                "sender_name": "Sarah Johnson",
                "content": "Excellent! I'm glad that resolved the issue. Is there anything else I can "
                          "help you with today?",
                "timestamp": "2026-02-18 09:26:00",
                "is_internal_note": False
            },
            {
                "sender_type": "customer",
                "sender_name": "John Smith",
                "content": "No, that's all. Thanks again!",
                "timestamp": "2026-02-18 09:27:00",
                "is_internal_note": False
            },
            {
                "sender_type": "system",
                "content": "Ticket marked as resolved. First response time: 3m 30s. "
                          "Total resolution time: 12m. CSAT survey sent.",
                "timestamp": "2026-02-18 09:28:00",
                "is_internal_note": True
            }
        ]
        
        print("\n📧 Message Thread:")
        for msg in messages:
            sender = msg.get('sender_name', msg['sender_type'].title())
            print(f"\n  [{msg['timestamp']}] {sender}:")
            
            if msg.get('is_internal_note'):
                print(f"    🔒 [Internal] {msg['content']}")
            else:
                print(f"    {msg['content'][:100]}{'...' if len(msg['content']) > 100 else ''}")
            
            if msg.get('ai_suggested'):
                print(f"    💡 [AI-Suggested Response]")
        
        # Show metrics
        print("\n📊 Ticket Metrics:")
        print(f"  First Response Time: 3m 30s ✓ (Target: <5m)")
        print(f"  Resolution Time: 12m ✓ (Target: <24h)")
        print(f"  Messages: {len([m for m in messages if not m.get('is_internal_note')])}")
        print(f"  Status: Resolved")
        
        return messages
    
    def demo_analytics(self):
        """Demonstrate analytics and reporting."""
        print("\n" + "="*60)
        print("8. ANALYTICS & REPORTING")
        print("="*60)
        
        analytics = {
            "today": {
                "new_tickets": 47,
                "resolved_tickets": 52,
                "open_tickets": 23,
                "avg_first_response": "4m 12s",
                "avg_resolution_time": "3h 45m"
            },
            "this_week": {
                "ticket_volume": 312,
                "resolution_rate": 94.2,
                "csat_score": 4.7,
                "agent_productivity": 58.3
            },
            "top_categories": [
                {"name": "Technical", "count": 128, "percentage": 41.0},
                {"name": "Billing", "count": 87, "percentage": 27.9},
                {"name": "Feature Request", "count": 54, "percentage": 17.3},
                {"name": "Account", "count": 43, "percentage": 13.8}
            ],
            "agent_performance": [
                {"name": "Sarah Johnson", "tickets": 67, "csat": 4.9, "avg_time": "3.2h"},
                {"name": "Mike Chen", "tickets": 62, "csat": 4.8, "avg_time": "3.8h"},
                {"name": "Emily Davis", "tickets": 59, "csat": 4.6, "avg_time": "4.1h"}
            ]
        }
        
        print("\n📈 Today's Metrics:")
        print(f"  New Tickets: {analytics['today']['new_tickets']}")
        print(f"  Resolved: {analytics['today']['resolved_tickets']}")
        print(f"  Open: {analytics['today']['open_tickets']}")
        print(f"  Avg First Response: {analytics['today']['avg_first_response']}")
        print(f"  Avg Resolution: {analytics['today']['avg_resolution_time']}")
        
        print("\n📊 This Week:")
        print(f"  Total Tickets: {analytics['this_week']['ticket_volume']}")
        print(f"  Resolution Rate: {analytics['this_week']['resolution_rate']}%")
        print(f"  CSAT Score: {analytics['this_week']['csat_score']}/5.0")
        print(f"  Agent Productivity: {analytics['this_week']['agent_productivity']} tickets/agent")
        
        print("\n🏷️  Top Categories:")
        for cat in analytics['top_categories']:
            bar = "█" * int(cat['percentage'] / 2)
            print(f"  {cat['name']:20} {bar} {cat['percentage']:.1f}% ({cat['count']})")
        
        print("\n👥 Agent Performance:")
        for agent in analytics['agent_performance']:
            print(f"  {agent['name']:20} {agent['tickets']} tickets | "
                  f"CSAT: {agent['csat']}/5.0 | Avg: {agent['avg_time']}")
        
        return analytics
    
    def run_demo(self):
        """Run the complete demo."""
        print("\n" + "="*60)
        print("SUPPORTFORGE DEMO - CUSTOMER SUPPORT PLATFORM")
        print("="*60)
        print("\nDemonstrating Phase 1 MVP features...")
        
        # Run all demonstrations
        tenant = self.demo_tenant_creation()
        agent = self.demo_agent_creation()
        customer = self.demo_customer_creation()
        ticket = self.demo_ticket_creation()
        ai_features = self.demo_ai_features(ticket)
        empire_context = self.demo_empire_integration(customer)
        conversation = self.demo_conversation_flow()
        analytics = self.demo_analytics()
        
        # Summary
        print("\n" + "="*60)
        print("DEMO SUMMARY")
        print("="*60)
        print("\n✓ Successfully demonstrated:")
        print("  • Multi-tenant architecture")
        print("  • Agent and customer management")
        print("  • Ticket creation and workflow")
        print("  • AI-powered features (suggestions, sentiment, categorization)")
        print("  • Empire product integration")
        print("  • Complete conversation flow")
        print("  • Analytics and reporting")
        
        print("\n📚 Next Steps:")
        print("  1. Run backend server: uvicorn app.main:app --reload")
        print("  2. Access API docs: http://localhost:8000/docs")
        print("  3. Test endpoints using the examples in SUPPORTFORGE_README.md")
        print("  4. Build frontend components for agent and customer interfaces")
        print("  5. Implement email processing and live chat widget")
        
        print("\n" + "="*60)
        print("Demo complete! SupportForge is ready for development.")
        print("="*60 + "\n")


if __name__ == "__main__":
    demo = SupportForgeDemo()
    demo.run_demo()
