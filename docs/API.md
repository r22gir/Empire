# ContractorForge API Documentation

REST API documentation for ContractorForge backend.

## Base URL

```
Development: http://localhost:8000/api/v1
Production: https://api.contractorforge.com/api/v1
```

## Authentication

Most endpoints require authentication via JWT Bearer token:

```
Authorization: Bearer <your-token>
```

## Endpoints

### Health Check

#### GET /
Get API status

**Response:**
```json
{
  "name": "ContractorForge API",
  "version": "1.0.0",
  "status": "online"
}
```

### Industries

#### GET /industries
List available industry templates

**Response:**
```json
{
  "industries": [
    {
      "code": "workroom",
      "name": "LuxeForge - Custom Workrooms",
      "color": "#8B4789",
      "features": {
        "production_queue": true,
        "sample_management": true
      }
    }
  ]
}
```

### Authentication (Coming Soon)

#### POST /auth/signup
Create new tenant and user account

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword",
  "full_name": "John Doe",
  "business_name": "John's Drapery",
  "industry_code": "workroom",
  "subscription_tier": "pro"
}
```

#### POST /auth/login
Authenticate and get access token

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1Q...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "tenant_id": 1
  }
}
```

### Projects (Coming Soon)

#### GET /projects
List all projects for authenticated tenant

**Query Parameters:**
- `status` - Filter by status
- `page` - Page number
- `per_page` - Items per page

**Response:**
```json
{
  "projects": [
    {
      "id": 1,
      "name": "Living Room Drapery",
      "status": "quoted",
      "customer": {
        "id": 1,
        "name": "Jane Smith"
      },
      "created_at": "2026-02-17T10:00:00Z"
    }
  ],
  "total": 25,
  "page": 1,
  "pages": 3
}
```

#### POST /projects
Create new project

**Request Body:**
```json
{
  "customer_id": 1,
  "name": "Kitchen Windows",
  "description": "Roman shades for 3 kitchen windows"
}
```

#### GET /projects/{id}
Get project details

**Response:**
```json
{
  "id": 1,
  "name": "Living Room Drapery",
  "status": "quoted",
  "measurements": {
    "windows": [
      {
        "width": 48,
        "height": 72,
        "treatment_type": "drapery"
      }
    ]
  },
  "estimates": [...]
}
```

### AI Conversation (Coming Soon)

#### POST /ai/conversation/start
Start new AI conversation

**Request Body:**
```json
{
  "project_id": 1,
  "industry_code": "workroom"
}
```

**Response:**
```json
{
  "conversation_id": 1,
  "message": "Hello! I'm here to help with your window treatment project...",
  "extracted_data": {}
}
```

#### POST /ai/conversation/{id}/message
Send message in conversation

**Request Body:**
```json
{
  "message": "I have 3 windows that need drapery"
}
```

**Response:**
```json
{
  "message": "Great! Can you provide measurements for each window?",
  "extracted_data": {
    "window_count": 3
  },
  "is_complete": false
}
```

### Photo Measurement (Coming Soon)

#### POST /measurement/photo
Measure from uploaded photo

**Request:** multipart/form-data
- `file` - Image file
- `reference_type` - Optional: "credit_card", "dollar_bill"
- `measurement_type` - Optional: "window", "panel", "area"

**Response:**
```json
{
  "success": true,
  "measurements": {
    "width": 48.5,
    "height": 72.0,
    "area_sqft": 24.25,
    "type": "window"
  },
  "confidence": "high",
  "reference_detected": true
}
```

### Estimates (Coming Soon)

#### POST /projects/{id}/estimate
Generate estimate for project

**Response:**
```json
{
  "id": 1,
  "estimate_number": "EST-2026-001",
  "line_items": [
    {
      "description": "Drapery - Window 1 (48\" wide)",
      "quantity": 2,
      "unit": "width",
      "rate": 120.00,
      "amount": 240.00
    }
  ],
  "subtotal": 240.00,
  "tax_amount": 19.20,
  "total": 259.20,
  "deposit_amount": 129.60
}
```

#### GET /estimates/{id}
Get estimate details

#### PATCH /estimates/{id}
Update estimate

#### POST /estimates/{id}/send
Send estimate to customer

## Error Responses

All errors follow this format:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Invalid input data",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ]
  }
}
```

### Common Error Codes

- `400` - Bad Request (validation error)
- `401` - Unauthorized (invalid/missing token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `422` - Unprocessable Entity
- `500` - Internal Server Error

## Rate Limiting

API requests are limited to:
- **Solo:** 100 requests/minute
- **Pro:** 500 requests/minute
- **Enterprise:** 2000 requests/minute

## Webhooks

### Stripe Webhooks

**POST /webhooks/stripe**

Handles Stripe events:
- `payment_intent.succeeded`
- `customer.subscription.updated`
- `customer.subscription.deleted`

## Interactive Documentation

Visit `/docs` for interactive Swagger UI documentation.

Visit `/redoc` for ReDoc documentation.
