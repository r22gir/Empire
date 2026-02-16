# MarketForge API Documentation

## Base URL
```
http://localhost:8000
```

In production: `https://your-domain.com`

## Authentication

The API uses JWT (JSON Web Token) based authentication. After logging in, you'll receive an access token that must be included in the `Authorization` header for protected endpoints.

### Header Format
```
Authorization: Bearer <your_access_token>
```

## Endpoints

### Health & Info

#### GET /
Get API information
```bash
curl http://localhost:8000/
```

Response:
```json
{
  "message": "MarketForge API",
  "version": "1.0.0",
  "docs": "/docs"
}
```

#### GET /health
Health check endpoint
```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy"
}
```

---

### Authentication Endpoints

#### POST /auth/register
Register a new user

**Request:**
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123"
  }'
```

**Response:** (200 OK)
```json
{
  "id": 1,
  "email": "user@example.com",
  "created_at": "2026-02-16T03:00:00.000Z"
}
```

**Errors:**
- 400 Bad Request: Email already registered

#### POST /auth/login
Login and receive access token

**Request:**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=securepassword123"
```

**Response:** (200 OK)
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Errors:**
- 401 Unauthorized: Incorrect email or password

#### GET /auth/me
Get current user information (requires authentication)

**Request:**
```bash
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Response:** (200 OK)
```json
{
  "id": 1,
  "email": "user@example.com",
  "created_at": "2026-02-16T03:00:00.000Z"
}
```

---

### Listing Endpoints

#### POST /listings/
Create a new listing (requires authentication)

**Request:**
```bash
curl -X POST http://localhost:8000/listings/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "title=Vintage Watch" \
  -F "description=Beautiful vintage watch in excellent condition" \
  -F "price=99.99" \
  -F "platforms=ebay,facebook,poshmark" \
  -F "photo=@/path/to/image.jpg"
```

**Form Parameters:**
- `title` (string, required): Product title
- `description` (string, required): Product description
- `price` (number, required): Product price
- `platforms` (string, required): Comma-separated platform names (ebay, facebook, poshmark, mercari, craigslist)
- `photo` (file, required): Product image file

**Response:** (200 OK)
```json
{
  "id": 1,
  "user_id": 1,
  "title": "Vintage Watch",
  "description": "Beautiful vintage watch in excellent condition",
  "price": 99.99,
  "photo_url": "./uploads/1_20260216_030000_image.jpg",
  "posted_ebay": false,
  "posted_facebook": false,
  "posted_poshmark": false,
  "posted_mercari": false,
  "posted_craigslist": false,
  "created_at": "2026-02-16T03:00:00.000Z"
}
```

**Note:** Currently, `posted_*` fields will be `false` until marketplace API integrations are completed. The listing is saved in the database and ready to be posted once credentials are configured.

#### GET /listings/
Get all listings for the current user (requires authentication)

**Request:**
```bash
curl http://localhost:8000/listings/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Query Parameters:**
- `skip` (integer, optional): Number of listings to skip (default: 0)
- `limit` (integer, optional): Maximum number of listings to return (default: 100)

**Response:** (200 OK)
```json
[
  {
    "id": 1,
    "user_id": 1,
    "title": "Vintage Watch",
    "description": "Beautiful vintage watch in excellent condition",
    "price": 99.99,
    "photo_url": "./uploads/1_20260216_030000_image.jpg",
    "posted_ebay": false,
    "posted_facebook": false,
    "posted_poshmark": false,
    "posted_mercari": false,
    "posted_craigslist": false,
    "created_at": "2026-02-16T03:00:00.000Z"
  }
]
```

#### GET /listings/{listing_id}
Get a specific listing (requires authentication)

**Request:**
```bash
curl http://localhost:8000/listings/1 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Response:** (200 OK)
```json
{
  "id": 1,
  "user_id": 1,
  "title": "Vintage Watch",
  "description": "Beautiful vintage watch in excellent condition",
  "price": 99.99,
  "photo_url": "./uploads/1_20260216_030000_image.jpg",
  "posted_ebay": true,
  "posted_facebook": true,
  "posted_poshmark": false,
  "posted_mercari": false,
  "posted_craigslist": false,
  "created_at": "2026-02-16T03:00:00.000Z"
}
```

**Errors:**
- 404 Not Found: Listing not found or doesn't belong to current user

---

## Error Responses

All error responses follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

Common HTTP status codes:
- `200 OK`: Success
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Missing or invalid authentication token
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

---

## Interactive Documentation

FastAPI provides automatic interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
  - Test endpoints directly in the browser
  - View request/response schemas
  - Try authentication flows

- **ReDoc**: http://localhost:8000/redoc
  - Alternative documentation format
  - Better for reading and sharing

---

## Rate Limiting

Currently no rate limiting is implemented. In production, consider adding rate limiting to prevent abuse.

---

## Webhooks (Future)

Marketplace sale notifications will be received via webhooks:

- `POST /webhooks/stripe` - Stripe payment events
- `POST /webhooks/ebay` - eBay order notifications
- `POST /webhooks/facebook` - Facebook Marketplace orders
- `POST /webhooks/poshmark` - Poshmark sale notifications
- `POST /webhooks/mercari` - Mercari sale notifications

---

## Database Schema

### Users Table
- `id`: Integer (Primary Key)
- `email`: String (Unique)
- `hashed_password`: String
- `created_at`: DateTime
- `ebay_token`: Text (Encrypted)
- `facebook_token`: Text (Encrypted)
- `poshmark_credentials`: Text (Encrypted)
- `mercari_token`: Text (Encrypted)
- `stripe_customer_id`: String

### Listings Table
- `id`: Integer (Primary Key)
- `user_id`: Integer (Foreign Key → Users)
- `title`: String
- `description`: Text
- `price`: Float
- `photo_url`: String
- `posted_ebay`: Boolean
- `posted_facebook`: Boolean
- `posted_poshmark`: Boolean
- `posted_mercari`: Boolean
- `posted_craigslist`: Boolean
- `ebay_listing_id`: String
- `facebook_listing_id`: String
- `poshmark_listing_id`: String
- `mercari_listing_id`: String
- `craigslist_listing_id`: String
- `created_at`: DateTime
- `updated_at`: DateTime

### Sales Table
- `id`: Integer (Primary Key)
- `user_id`: Integer (Foreign Key → Users)
- `listing_id`: Integer (Foreign Key → Listings)
- `platform`: String
- `sale_price`: Float
- `commission`: Float (3% of sale_price)
- `buyer_info`: Text
- `stripe_payment_intent_id`: String
- `commission_paid`: Boolean
- `created_at`: DateTime

### Payouts Table
- `id`: Integer (Primary Key)
- `user_id`: Integer (Foreign Key → Users)
- `total_earned`: Float
- `commission_amount`: Float
- `payout_amount`: Float
- `stripe_payout_id`: String
- `status`: String (pending, completed, failed)
- `created_at`: DateTime
- `paid_at`: DateTime

---

## Development

### Running Tests
```bash
cd backend
python tests/test_setup.py
```

### Starting Development Server
```bash
cd backend
./start.sh
```

Or manually:
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing API
```bash
cd backend
./test_api.sh
```

---

## Production Considerations

1. **Database**: Switch from SQLite to PostgreSQL
2. **Environment**: Use production environment variables
3. **CORS**: Restrict allowed origins
4. **HTTPS**: Always use SSL in production
5. **Secrets**: Rotate SECRET_KEY regularly
6. **Monitoring**: Add logging and monitoring
7. **Rate Limiting**: Implement rate limiting
8. **Backups**: Regular database backups
