# SupportForge - Multi-Channel Customer Support Platform

## Overview

SupportForge is a comprehensive customer support SaaS platform that integrates deeply with all Empire Box products. It provides enterprise-grade support infrastructure with AI-powered features, multi-channel support, and advanced analytics.

## Core Features

### 1. Multi-Channel Support
- **Email** - Support email forwarding and management
- **Live Chat** - Embeddable chat widget for websites
- **SMS** - Text message support via Twilio
- **WhatsApp** - WhatsApp Business integration
- **API** - Programmatic ticket creation
- **Widget** - In-app support widget for SaaS products

### 2. Ticket Management
- Smart routing (auto-assign based on skills, workload)
- Priority levels (Urgent, High, Normal, Low)
- Status workflow (New → Open → Pending → Resolved → Closed)
- Tags & categories for organization
- Internal notes for agent communication
- Merge and split tickets
- Snooze and follow-up reminders

### 3. AI-Powered Intelligence
- **Smart Replies** - GPT-4 suggests responses based on context
- **Auto-Categorization** - AI tags tickets automatically
- **Sentiment Analysis** - Detect frustrated customers
- **Intent Detection** - Understand customer needs
- **Knowledge Base Search** - AI finds relevant articles
- **Auto-Translation** - Multi-language support
- **Summary Generation** - Summarize long conversations

### 4. Knowledge Base (Self-Service)
- Public help center with customer-facing documentation
- Rich text editor with images, videos, code blocks
- Elasticsearch-powered search
- Categories & collections for organized content
- Article versioning and analytics
- Suggested articles in chat widget

### 5. Customer Portal
- Ticket submission via web form
- View ticket history and status
- Real-time updates on ticket progress
- File attachments support
- Satisfaction ratings (CSAT)

### 6. Agent Dashboard
- Unified inbox for all tickets
- Quick actions and canned responses
- Customer context from Empire products
- Performance metrics dashboard
- Collision detection (warn if another agent viewing)

### 7. Admin & Analytics
- Team management (roles, permissions, departments)
- SLA configuration (response and resolution time targets)
- Business hours and holiday settings
- Automation rules (trigger-action workflows)
- Comprehensive reports:
  - Ticket volume trends
  - First response time
  - Resolution time
  - CSAT scores
  - Agent performance
  - Top issues

### 8. Empire Product Integrations
- **ContractorForge Integration**:
  - View customer's projects in ticket sidebar
  - See estimate history and AI usage
  - Check economic metrics
  - One-click access to customer workspace
  
- **Generic Empire API**:
  - Standard authentication
  - Customer data retrieval
  - Action triggers (refunds, credits, feature flags)

## API Endpoints

### Tickets
```
POST   /api/v1/supportforge/tickets              - Create ticket
GET    /api/v1/supportforge/tickets              - List tickets
GET    /api/v1/supportforge/tickets/{id}         - Get ticket details
PATCH  /api/v1/supportforge/tickets/{id}         - Update ticket
POST   /api/v1/supportforge/tickets/{id}/assign  - Assign agent
POST   /api/v1/supportforge/tickets/{id}/messages - Add message
GET    /api/v1/supportforge/tickets/{id}/messages - Get messages
POST   /api/v1/supportforge/tickets/{id}/tags    - Add tags
```

### AI Features
```
POST   /api/v1/supportforge/ai/suggest-response  - Get AI response suggestion
POST   /api/v1/supportforge/ai/categorize        - Auto-categorize ticket
POST   /api/v1/supportforge/ai/sentiment         - Analyze sentiment
POST   /api/v1/supportforge/ai/summarize         - Summarize conversation
POST   /api/v1/supportforge/ai/search-kb         - Search knowledge base
```

### Customers
```
POST   /api/v1/supportforge/customers                    - Create customer
GET    /api/v1/supportforge/customers                    - List customers
GET    /api/v1/supportforge/customers/{id}               - Get customer
PATCH  /api/v1/supportforge/customers/{id}               - Update customer
GET    /api/v1/supportforge/customers/{id}/tickets       - Customer tickets
GET    /api/v1/supportforge/customers/{id}/empire-context - Empire product data
```

## Database Schema

### Core Tables
- **supportforge_tenants** - Multi-tenant support organizations
- **supportforge_agents** - Support team members
- **supportforge_customers** - End customers seeking support
- **supportforge_tickets** - Support ticket records
- **supportforge_messages** - Ticket conversations
- **supportforge_kb_articles** - Help articles/documentation
- **supportforge_automations** - Workflow automation rules
- **supportforge_sla_policies** - Service level agreements
- **supportforge_integrations** - Connected Empire products

## Getting Started

### Installation

1. **Install Dependencies** (already included in main requirements.txt)
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Run Database Migration**
   ```bash
   cd backend
   alembic upgrade head
   ```

3. **Start Server**
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

4. **Access API Documentation**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### Create Your First Tenant

```python
import requests
import uuid

# Create a tenant
tenant_data = {
    "name": "Acme Corp Support",
    "subdomain": "acme",
    "plan": "professional",
    "settings": {
        "business_hours": "9am-5pm EST",
        "languages": ["en", "es"]
    }
}

# Note: You'll need to add a tenant creation endpoint or use direct DB access
```

### Create Your First Ticket

```python
import requests

# First, create a customer
customer_data = {
    "tenant_id": "your-tenant-id",
    "email": "customer@example.com",
    "name": "John Doe",
    "company": "Example Inc"
}

response = requests.post(
    "http://localhost:8000/api/v1/supportforge/customers",
    json=customer_data
)
customer = response.json()

# Then create a ticket
ticket_data = {
    "tenant_id": "your-tenant-id",
    "customer_id": customer["id"],
    "subject": "Need help with setup",
    "channel": "email",
    "priority": "normal"
}

response = requests.post(
    "http://localhost:8000/api/v1/supportforge/tickets",
    json=ticket_data
)
ticket = response.json()
print(f"Created ticket #{ticket['ticket_number']}")
```

### Add AI Response Suggestion

```python
import requests

# Get AI suggestion for a ticket
request_data = {
    "ticket_id": "your-ticket-id"
}

response = requests.post(
    "http://localhost:8000/api/v1/supportforge/ai/suggest-response",
    json=request_data
)

suggestion = response.json()
print(f"AI Suggestion: {suggestion['suggested_response']}")
print(f"Confidence: {suggestion['confidence']}")
```

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# OpenAI (for AI features)
OPENAI_API_KEY=your_openai_api_key

# Email (for notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# Twilio (for SMS)
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890
```

## Integration with Empire Products

SupportForge automatically enriches ticket context when customers are linked to Empire products:

```python
# Get Empire product context for a customer
response = requests.get(
    f"http://localhost:8000/api/v1/supportforge/customers/{customer_id}/empire-context"
)

context = response.json()
# Returns:
# {
#     "has_empire_product": true,
#     "product_type": "contractorforge",
#     "subscription_status": "active",
#     "projects_count": 5,
#     "usage_this_month": {
#         "ai_requests": 150,
#         "cost": 12.50
#     }
# }
```

## Pricing Strategy

### For Empire Internal Use
**Free** - Unlimited use for supporting Empire products

### External SaaS Offering
- **Starter**: $49/mo - 1 agent, 500 tickets/mo
- **Professional**: $99/agent/mo - Unlimited tickets, AI features
- **Enterprise**: Custom - White-label, custom SLAs

## Success Metrics

Target KPIs:
- First response time < 5 minutes
- Resolution time < 24 hours
- CSAT > 95%
- Self-service resolution rate > 40%
- AI suggestion acceptance rate > 60%
- Agent productivity: 50+ tickets/day/agent

## Development Roadmap

### Phase 1 MVP (Complete)
- ✅ Core ticket system
- ✅ API endpoints
- ✅ Database models
- ✅ AI service integration
- ✅ Customer management
- ✅ ContractorForge integration stub

### Phase 2 (In Progress)
- [ ] Live chat widget
- [ ] Email processing (incoming)
- [ ] SMS support
- [ ] Advanced AI features
- [ ] Automation rules engine
- [ ] SLA monitoring
- [ ] Detailed analytics dashboard

### Phase 3 (Planned)
- [ ] WhatsApp integration
- [ ] Video/screen sharing
- [ ] Mobile apps
- [ ] White-label option
- [ ] API marketplace
- [ ] Advanced reporting

## Security & Compliance

- Multi-tenant data isolation
- Role-based access control (RBAC)
- API rate limiting
- Audit logs for all actions
- GDPR compliance ready (data export, right to be forgotten)
- Future: SOC 2 Type II certification

## Testing

Run tests:
```bash
cd backend
pytest tests/test_supportforge_*.py -v
```

## Contributing

This is part of the EmpireBox ecosystem. See main repository README for contribution guidelines.

## Support

For questions or issues:
- Email: support@empirebox.store
- Documentation: docs.empirebox.store/supportforge

---

**Built with ❤️ by the EmpireBox Team**

*Last Updated: 2026-02-18*
