# MarketForge Backend

FastAPI backend server for MarketForge - AI-powered marketplace automation platform.

## Features

- **Authentication**: JWT-based auth with signup, login, and token refresh
- **User Management**: Profile management and subscription tiers
- **Listings**: CRUD operations for product listings
- **Multi-Marketplace Publishing**: Publish listings to eBay, Facebook, Craigslist
- **Unified Messaging**: Aggregate messages from multiple sources
- **AI Integration**: AI-powered descriptions, pricing, and message responses
- **Webhooks**: Receive notifications from email services and marketplaces

## Tech Stack

- **FastAPI**: Modern, fast web framework
- **SQLAlchemy 2.0**: Async ORM for database operations
- **PostgreSQL**: Primary database with async support
- **Alembic**: Database migrations
- **JWT**: Secure authentication
- **Pydantic**: Data validation and settings

## Quick Start

### Using Docker (Recommended)

1. Clone the repository:
```bash
cd backend
```

2. Copy environment file:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Start services:
```bash
docker-compose up -d
```

The API will be available at `http://localhost:8000`

API documentation: `http://localhost:8000/docs`

### Local Development

1. Install Python 3.11+

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up PostgreSQL database:
```bash
# Install PostgreSQL, then create database
createdb marketforge
```

5. Configure environment:
```bash
cp .env.example .env
# Edit .env with your database URL and settings
```

6. Run database migrations:
```bash
alembic upgrade head
```

7. Start the server:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration settings
│   ├── database.py          # Database setup
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── routers/             # API route handlers
│   ├── services/            # Business logic
│   ├── middleware/          # Authentication middleware
│   └── utils/               # Utility functions
├── alembic/                 # Database migrations
├── requirements.txt         # Python dependencies
├── Dockerfile              # Container image
├── docker-compose.yml      # Local dev environment
└── README.md               # This file
```

## API Endpoints

### Authentication
- `POST /auth/signup` - Create new user account
- `POST /auth/login` - Login and get tokens
- `POST /auth/refresh` - Refresh access token

### Users
- `GET /users/me` - Get current user profile
- `PUT /users/me` - Update profile
- `GET /users/me/subscription` - Get subscription info

### Listings
- `GET /listings` - List user's listings
- `POST /listings` - Create new listing
- `GET /listings/{id}` - Get listing details
- `PUT /listings/{id}` - Update listing
- `DELETE /listings/{id}` - Delete listing
- `POST /listings/{id}/publish` - Publish to marketplaces

### Messages
- `GET /messages` - List messages
- `GET /messages/{id}` - Get message details
- `POST /messages/{id}/read` - Mark as read
- `POST /messages/{id}/reply` - Reply to message
- `POST /messages/{id}/ai-draft` - Generate AI response

### AI
- `POST /ai/generate-description` - Generate product description
- `POST /ai/enhance-description` - Enhance description
- `POST /ai/suggest-price` - Get price suggestion

### Marketplaces
- `GET /marketplaces` - List available marketplaces
- `POST /marketplaces/{name}/connect` - Connect marketplace
- `DELETE /marketplaces/{name}/disconnect` - Disconnect

### Webhooks
- `POST /webhooks/email/inbound` - Email webhook
- `POST /webhooks/ebay/notification` - eBay webhook
- `POST /webhooks/stripe` - Stripe webhook

## Database Migrations

Create a new migration:
```bash
alembic revision --autogenerate -m "Description of changes"
```

Apply migrations:
```bash
alembic upgrade head
```

Rollback migration:
```bash
alembic downgrade -1
```

## Environment Variables

See `.env.example` for all available configuration options.

Required variables:
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - Secret key for JWT signing

Optional variables:
- `EBAY_APP_ID`, `EBAY_CERT_ID`, `EBAY_DEV_ID` - eBay API credentials
- `STRIPE_SECRET_KEY` - Stripe payment integration
- `CLOUDFLARE_API_KEY` - Email routing
- `GROK_API_KEY`, `OLLAMA_BASE_URL` - AI services

## Integration with EmpireBox Agents

The backend integrates with the `empire_box_agents` module for AI features:

```python
from app.services.ai_service import AIService

ai_service = AIService(user)
description = await ai_service.generate_description(product_info)
```

## Testing

Run tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=app tests/
```

## Deployment

### Docker Deployment

1. Build image:
```bash
docker build -t marketforge-backend .
```

2. Run container:
```bash
docker run -p 8000:8000 \
  -e DATABASE_URL=your_db_url \
  -e SECRET_KEY=your_secret_key \
  marketforge-backend
```

### Production Considerations

- Set `SECRET_KEY` to a secure random value
- Use production-grade PostgreSQL instance
- Enable HTTPS/TLS
- Set up proper CORS origins
- Configure rate limiting
- Set up logging and monitoring
- Use environment-specific settings

## License

See LICENSE file in repository root.

## Support

For issues and questions, please open an issue on GitHub.
