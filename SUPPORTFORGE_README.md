# SupportForge - Enterprise Customer Support Platform

## Overview

SupportForge is a comprehensive multi-channel customer support platform that integrates seamlessly with all Empire Box products (ContractorForge, MarketForge, etc.) to provide scalable, AI-powered customer support infrastructure.

## Features

### Phase 1: MVP (Implemented)
✅ **Core Ticket Management**
- Create, read, update, delete tickets
- Multi-status workflow (new, open, pending, resolved, closed)
- Priority levels (low, normal, high, urgent)
- Multi-channel support (email, chat, phone, SMS, portal)
- Ticket assignment to agents
- Message threading with attachments
- Internal notes for agents

✅ **Customer Management**
- Customer profiles with contact information
- Link customers to Empire products (ContractorForge, etc.)
- Customer tagging and metadata
- Ticket history per customer
- Customer context integration

✅ **Multi-Tenancy**
- Isolated tenant data (organizations)
- Tenant-specific branding and settings
- Subdomain-based access
- Multiple pricing plans (starter, growth, enterprise)

✅ **Support Agents**
- Agent profiles with roles (agent, admin, supervisor)
- Department and skill assignments
- Agent status tracking (online, offline, away, busy)
- Concurrent ticket limits

✅ **Database Schema**
- PostgreSQL with JSONB for flexible data
- Optimized indexes for performance
- Foreign key constraints for data integrity
- Soft delete support

### Phase 2: Enhancement (Planned)
🔄 **AI Features**
- AI-powered response suggestions
- Auto-categorization of tickets
- Sentiment analysis
- Ticket summarization
- AI-powered KB search

🔄 **Knowledge Base**
- Article creation and management
- Categories and hierarchies
- Public help center
- Search functionality
- Article voting (helpful/not helpful)

🔄 **Automation & SLA**
- Workflow automation rules
- SLA policies with time tracking
- Canned/templated responses
- Auto-assignment algorithms

🔄 **Analytics**
- Dashboard with key metrics
- Agent performance reports
- Ticket trends and insights
- Customer satisfaction tracking

### Phase 3: Scale (Planned)
📋 **Real-time Features**
- WebSocket support for live updates
- Live chat widget
- Agent presence indicators
- Real-time collaboration

📋 **Multi-channel**
- Email integration (SendGrid/SES)
- SMS support (Twilio)
- Social media integration
- WhatsApp support

📋 **Performance & Security**
- Redis caching layer
- Rate limiting
- GDPR compliance
- Audit logs

## Architecture

### Backend (FastAPI)
```
backend/app/
├── models/                     # SQLAlchemy models
│   ├── supportforge_tenant.py
│   ├── supportforge_agent.py
│   ├── supportforge_customer.py
│   ├── supportforge_ticket.py
│   ├── supportforge_message.py
│   ├── supportforge_kb.py
│   ├── supportforge_automation.py
│   └── supportforge_integration.py
├── schemas/                    # Pydantic schemas
│   ├── supportforge_ticket.py
│   ├── supportforge_customer.py
│   └── supportforge_kb.py
├── services/                   # Business logic
│   ├── supportforge_ticket.py
│   └── supportforge_customer.py
├── routers/                    # API endpoints
│   ├── supportforge_tickets.py
│   └── supportforge_customers.py
└── main.py                    # FastAPI app
```

### Database Tables
- `sf_tenants` - Support organizations
- `sf_support_agents` - Customer support agents
- `sf_customers` - Ticket submitters
- `sf_tickets` - Support tickets
- `sf_messages` - Ticket messages/conversations
- `sf_kb_articles` - Knowledge base articles
- `sf_kb_categories` - KB categories
- `sf_automations` - Automation rules
- `sf_sla_policies` - SLA policies
- `sf_canned_responses` - Template responses
- `sf_integrations` - Third-party integrations
- `sf_satisfaction_ratings` - Customer feedback

## API Endpoints

### Tickets
```
POST   /api/v1/tickets              - Create ticket
GET    /api/v1/tickets              - List tickets (with filters)
GET    /api/v1/tickets/{id}         - Get ticket details
PATCH  /api/v1/tickets/{id}         - Update ticket
DELETE /api/v1/tickets/{id}         - Delete ticket
POST   /api/v1/tickets/{id}/messages        - Add message
POST   /api/v1/tickets/{id}/assign          - Assign agent
POST   /api/v1/tickets/{id}/tags            - Update tags
```

### Customers
```
POST   /api/v1/customers            - Create customer
GET    /api/v1/customers            - List customers (with search)
GET    /api/v1/customers/{id}       - Get customer
PATCH  /api/v1/customers/{id}       - Update customer
DELETE /api/v1/customers/{id}       - Delete customer
GET    /api/v1/customers/{id}/tickets      - Get customer tickets
GET    /api/v1/customers/{id}/context      - Get customer context
```

## Setup Instructions

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis 7+ (for Phase 2+)

### Installation

1. **Install dependencies:**
```bash
cd backend
pip install -r requirements.txt
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your settings
```

Required environment variables:
```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/supportforge

# Optional (for later phases)
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=sk-...
SENDGRID_API_KEY=SG...
TWILIO_ACCOUNT_SID=AC...
```

3. **Run database migrations:**
```bash
alembic upgrade head
```

4. **Start the server:**
```bash
uvicorn app.main:app --reload
```

The API will be available at:
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Usage Examples

### Create a Ticket
```bash
curl -X POST http://localhost:8000/api/v1/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "customer_email": "customer@example.com",
    "customer_name": "John Doe",
    "subject": "Need help with billing",
    "content": "I have a question about my invoice.",
    "channel": "email",
    "priority": "normal"
  }'
```

### List Tickets
```bash
curl http://localhost:8000/api/v1/tickets?status=open&page=1&per_page=20
```

### Add Message to Ticket
```bash
curl -X POST http://localhost:8000/api/v1/tickets/{ticket_id}/messages \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Thank you for reaching out. Let me help you with that.",
    "is_internal_note": false
  }'
```

### Get Customer Context
```bash
curl http://localhost:8000/api/v1/customers/{customer_id}/context
```

## Integration with Empire Products

SupportForge integrates with other Empire products to provide rich customer context:

### ContractorForge Integration
When viewing a ticket from a ContractorForge customer:
- View all their projects
- See recent estimates
- Check AI usage and costs
- Review subscription status
- Quick actions: Grant credit, extend trial, toggle features

### Integration Pattern
```python
# Link customer to Empire product
customer = Customer(
    email="user@example.com",
    empire_product_type="contractorforge",
    empire_product_id=uuid4(),
    metadata={
        "subscription_tier": "pro",
        "monthly_usage": 1250
    }
)
```

## Security Features

- Multi-tenant data isolation (row-level security)
- JWT authentication (to be implemented)
- Rate limiting (to be implemented)
- SQL injection prevention (parameterized queries)
- XSS protection (input sanitization)
- GDPR compliance support

## Performance Targets

- Support 10,000+ tickets/month per tenant
- First response time < 5 minutes (with agents online)
- Page load time < 2 seconds
- 99.9% uptime SLA

## Development Roadmap

### Current Status: Phase 1 MVP ✅
- [x] Database schema
- [x] Core ticket CRUD
- [x] Customer management
- [x] Message threading
- [x] API endpoints
- [x] Multi-tenancy support

### Next: Phase 2 Enhancement
- [ ] AI response suggestions
- [ ] Knowledge base system
- [ ] Automation rules
- [ ] Analytics dashboard
- [ ] SLA tracking

### Future: Phase 3 Scale
- [ ] Real-time WebSocket
- [ ] Email/SMS integration
- [ ] Live chat widget
- [ ] Mobile apps
- [ ] Advanced reporting

## Contributing

This is part of the Empire Box ecosystem. For contribution guidelines, see the main Empire repository README.

## License

Proprietary - Copyright © 2026 EmpireBox. All rights reserved.

## Support

- **Email**: support@empirebox.store
- **Documentation**: See API docs at /docs endpoint
- **Issues**: Use GitHub issues in the main Empire repository

---

**Built with ❤️ as part of the Empire Box Platform**
