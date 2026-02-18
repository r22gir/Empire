# EmpireBox Backend API

FastAPI backend for EmpireBox - combining Setup Portal, License Management, ShipForge shipping, and AI-powered marketplace automation.

## Features

- **License Key System**: Generate, validate, and activate license keys for hardware bundles
- **Shipping Integration**: EasyPost integration for comparing rates and purchasing labels
- **Pre-order Management**: Handle hardware bundle pre-orders with Stripe payments
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
- **SQLite/PostgreSQL**: Database support
- **Alembic**: Database migrations
- **JWT**: Secure authentication
- **Pydantic**: Data validation and settings
- **EasyPost**: Shipping integration
- **Stripe**: Payment processing

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

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your API keys (EasyPost, Stripe, etc.)
```

5. Initialize the database:
```bash
python -m app.init_db
```

6. Run database migrations (if using PostgreSQL):
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

### Licenses
- `POST /licenses/generate` - Generate license keys
- `GET /licenses/{key}/validate` - Validate a license key
- `POST /licenses/{key}/activate` - Activate a license
- `GET /licenses/my-licenses` - Get user's licenses

### Shipping
- `POST /shipping/rates` - Get shipping rates
- `POST /shipping/labels` - Purchase a shipping label
- `GET /shipping/labels/{id}` - Get label details
- `GET /shipping/track/{tracking_number}` - Track shipment
- `GET /shipping/history` - Get shipment history
- `POST /shipping/labels/{id}/email` - Email label PDF

### Pre-orders
- `POST /preorders/` - Create a pre-order
- `GET /preorders/` - List pre-orders
- `GET /preorders/{id}` - Get pre-order details
- `PATCH /preorders/{id}` - Update pre-order
- `POST /preorders/{id}/process-payment` - Process payment

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

## License Key Format

License keys use the format: `EMPIRE-XXXX-XXXX-XXXX`
- 16 alphanumeric characters (excluding confusing characters like O, 0, I, 1)
- Always starts with "EMPIRE-"
- Unique and randomly generated

## Database

Uses SQLite by default for development. For production, update `DATABASE_URL` in `.env` to use PostgreSQL:
```
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/empirebox
```

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
- `DATABASE_URL` - Database connection string
- `SECRET_KEY` - Secret key for JWT signing

Optional variables:
- `EASYPOST_API_KEY` - Shipping integration
- `STRIPE_API_KEY`, `STRIPE_SECRET_KEY` - Payment processing
- `EBAY_APP_ID`, `EBAY_CERT_ID`, `EBAY_DEV_ID` - eBay API credentials
- `CLOUDFLARE_API_KEY` - Email routing
- `GROK_API_KEY`, `OLLAMA_BASE_URL` - AI services

## Test Mode

The shipping service runs in test mode by default (using simulated data). To use real EasyPost API:
1. Set `EASYPOST_TEST_MODE=false` in `.env`
2. Add your production `EASYPOST_API_KEY`

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
docker build -t empirebox-backend .
```

2. Run container:
```bash
docker run -p 8000:8000 \
  -e DATABASE_URL=your_db_url \
  -e SECRET_KEY=your_secret_key \
  empirebox-backend
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

Copyright © 2026 EmpireBox. All rights reserved.

## Support

- **Email**: support@empirebox.store
- **Documentation**: [docs.empirebox.store](https://docs.empirebox.store)