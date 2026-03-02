# ContractorForge Setup Guide

Complete installation and configuration guide for ContractorForge.

## Prerequisites

### Required Software
- **Python 3.11+**
- **Node.js 18+** and npm
- **PostgreSQL 14+**
- **Redis 6+**
- **Git**

## Backend Setup

```bash
cd contractorforge_backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your settings
alembic upgrade head
uvicorn app.main:app --reload
```

## Frontend Setup

```bash
cd contractorforge_web
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1" > .env.local
npm run dev
```

## External Services

1. **OpenAI API** - Get key from https://platform.openai.com/
2. **Stripe** - Get keys from https://stripe.com/
3. **SendGrid** - Get API key from https://sendgrid.com/

See full documentation in project README.
