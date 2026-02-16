# MarketForge Backend API

## Setup

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

4. Run the server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

5. Access the API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login and get access token
- `GET /auth/me` - Get current user info

### Listings
- `POST /listings/` - Create new listing (with photo upload)
- `GET /listings/` - Get all user listings
- `GET /listings/{id}` - Get specific listing

## Database

The application uses SQLAlchemy with SQLite by default. The database schema includes:
- Users (email, password, marketplace credentials)
- Listings (title, description, price, photo, platform statuses)
- Sales (sale info, commission tracking)
- Payouts (earnings and commission payments)

## Marketplace Integrations

The following integrations need to be implemented:
1. eBay API (OAuth + listing creation)
2. Facebook Marketplace (Graph API)
3. Poshmark (API or alternative method)
4. Mercari (API integration)
5. Craigslist (automation-based)

## Commission System

- 3% commission automatically calculated on each sale
- Tracked via Stripe payment intents
- Webhook listeners for marketplace sales notifications

## Development

Run tests:
```bash
pytest
```

Format code:
```bash
black app/
```

## Production Deployment

1. Set production environment variables
2. Use PostgreSQL instead of SQLite
3. Configure proper CORS origins
4. Set up SSL/HTTPS
5. Configure Stripe webhooks
6. Set up marketplace API webhooks
