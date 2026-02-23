# SupportForge Quick Start Guide

## 🚀 Get Started in 5 Minutes

### 1. Prerequisites

Make sure you have:
- Python 3.11+
- PostgreSQL 15+ (or use SQLite for development)

### 2. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Setup Database

For development with SQLite (easiest):
```bash
# SQLite is used by default, no setup needed
python -c "from app.database import init_db; init_db()"
```

For production with PostgreSQL:
```bash
# Set environment variable
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost/supportforge"

# Run migrations
alembic upgrade head
```

### 4. Start the Server

```bash
cd backend
uvicorn app.main:app --reload
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 5. Try It Out

#### Create a Ticket via API

```bash
curl -X POST http://localhost:8000/api/v1/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "customer_email": "john@example.com",
    "customer_name": "John Doe",
    "subject": "Need help with my account",
    "content": "I cannot access my dashboard",
    "channel": "email",
    "priority": "normal"
  }'
```

#### List All Tickets

```bash
curl http://localhost:8000/api/v1/tickets
```

#### Create a Knowledge Base Article

```bash
curl -X POST http://localhost:8000/api/v1/kb/articles \
  -H "Content-Type: application/json" \
  -d '{
    "title": "How to Reset Your Password",
    "slug": "reset-password",
    "content": "Follow these steps...",
    "content_html": "<p>Follow these steps...</p>",
    "status": "published",
    "tags": ["account", "security"]
  }'
```

#### Get AI Response Suggestion

```bash
curl -X POST http://localhost:8000/api/v1/ai/categorize \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Billing question",
    "content": "I was charged twice this month"
  }'
```

### 6. Run the Demo

```bash
python demo_supportforge.py
```

This will show:
- AI features demonstration
- Complete API endpoint list
- Setup instructions

## 📊 What's Included

### ✅ Phase 1: MVP (Complete)
- **Core Ticket System**: Create, update, assign, and track tickets
- **Customer Management**: Store customer data with Empire product links
- **Message Threading**: Full conversation history with attachments
- **Multi-Tenancy**: Isolated data for multiple organizations
- **RESTful API**: Complete FastAPI backend with validation

### ✅ Phase 2: Enhancement (Complete)
- **Knowledge Base**: Articles, categories, search, voting
- **AI Features**: Response suggestions, categorization, sentiment analysis
- **Automation Ready**: Models for rules, SLA policies, canned responses

### 📋 Phase 3: Coming Soon
- Real-time WebSocket updates
- Email/SMS integration
- Live chat widget
- Frontend UI (React/Next.js)
- Advanced analytics

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/supportforge
# Or use SQLite (default)
# DATABASE_URL=sqlite:///./supportforge.db

# AI Features (Optional)
OPENAI_API_KEY=sk-your-key-here
AI_FEATURES_ENABLED=true

# Redis (for Phase 3)
REDIS_URL=redis://localhost:6379/0

# Email (for Phase 3)
SENDGRID_API_KEY=SG.your-key
SMTP_HOST=smtp.gmail.com

# SMS (for Phase 3)
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
```

## 📚 API Documentation

Once the server is running, visit:

**Interactive API Docs**: http://localhost:8000/docs

This provides:
- Complete API reference
- Try-it-out functionality
- Request/response schemas
- Authentication details

## 🎯 Next Steps

1. **Integrate with Your App**: Use the API endpoints in your application
2. **Customize Models**: Modify database schemas for your needs
3. **Add Authentication**: Implement JWT tokens for security
4. **Enable AI**: Set OPENAI_API_KEY for AI features
5. **Build Frontend**: Create React/Next.js UI for agents and customers

## 🆘 Need Help?

- **Documentation**: See [SUPPORTFORGE_README.md](../SUPPORTFORGE_README.md)
- **API Reference**: http://localhost:8000/docs
- **Main README**: See [README.md](../README.md) for Empire Box overview

## 🎉 You're Ready!

SupportForge is now running and ready to handle customer support tickets!

Try the interactive API docs at http://localhost:8000/docs to explore all endpoints.
