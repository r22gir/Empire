# Economic Intelligence API Documentation

## Overview

The Economic Intelligence System provides comprehensive tracking of costs, revenue, and ROI for all operations in EmpireBox. It includes quality evaluation, transaction tracking, and performance analytics.

## Base URL

All endpoints are prefixed with `/api/v1/economic`

## Authentication

All endpoints require authentication via JWT Bearer token in the `Authorization` header:

```
Authorization: Bearer <your_token>
```

## Endpoints

### 1. Get Economic Ledger

Get economic ledger information for a specific entity.

**Endpoint:** `GET /api/v1/economic/ledger/{entity_type}/{entity_id}`

**Parameters:**
- `entity_type` (path): Type of entity - `user`, `listing`, `shipment`, or `license`
- `entity_id` (path): UUID of the entity

**Response:**
```json
{
  "id": "uuid",
  "entity_type": "user",
  "entity_id": "uuid",
  "balance": 985.50,
  "total_income": 150.00,
  "total_costs": 164.50,
  "total_profit": -14.50,
  "status": "stable",
  "transaction_count": 25,
  "last_transaction_at": "2026-02-18T12:00:00Z",
  "created_at": "2026-02-01T10:00:00Z",
  "updated_at": "2026-02-18T12:00:00Z"
}
```

**Status Values:**
- `thriving`: balance > $100
- `stable`: $10 < balance <= $100
- `struggling`: $0 < balance <= $10
- `failing`: balance <= $0

---

### 2. Get Dashboard Overview

Get comprehensive dashboard overview for the current user.

**Endpoint:** `GET /api/v1/economic/dashboard/overview`

**Response:**
```json
{
  "ledger": {
    "balance": 985.50,
    "total_income": 150.00,
    "total_costs": 164.50,
    "total_profit": -14.50,
    "status": "stable",
    "transaction_count": 25,
    "last_transaction_at": "2026-02-18T12:00:00Z"
  },
  "metrics": {
    "profit_margin": -9.67,
    "roi": -8.81,
    "recent_income_30d": 75.00,
    "recent_costs_30d": 82.50
  },
  "recent_transactions": [
    {
      "id": "uuid",
      "type": "ai_token_cost",
      "amount": -0.15,
      "description": "AI token usage: 1000 input, 500 output tokens",
      "created_at": "2026-02-18T12:00:00Z",
      "resource_details": {
        "input_tokens": 1000,
        "output_tokens": 500,
        "model": "gpt-4"
      }
    }
  ]
}
```

---

### 3. Get Transactions

Get transaction history for an entity with filtering and pagination.

**Endpoint:** `GET /api/v1/economic/transactions`

**Query Parameters:**
- `entity_type` (optional): Type of entity (default: `user`)
- `entity_id` (optional): UUID of entity (default: current user)
- `transaction_type` (optional): Filter by transaction type
- `limit` (optional): Max transactions to return (default: 100, max: 500)
- `offset` (optional): Offset for pagination (default: 0)

**Transaction Types:**
- `ai_token_cost`: AI token usage cost
- `compute_cost`: Compute processing cost
- `api_cost`: External API cost
- `listing_value`: Value created from listing
- `shipping_cost`: Shipping cost
- `license_revenue`: Revenue from license

**Response:**
```json
{
  "transactions": [
    {
      "id": "uuid",
      "ledger_id": "uuid",
      "entity_type": "user",
      "entity_id": "uuid",
      "transaction_type": "ai_token_cost",
      "amount": -0.15,
      "currency": "USD",
      "resource_details": {
        "input_tokens": 1000,
        "output_tokens": 500,
        "model": "gpt-4",
        "input_price_per_1m": 2.50,
        "output_price_per_1m": 10.00
      },
      "quality_score": null,
      "description": "AI token usage: 1000 input, 500 output tokens",
      "created_at": "2026-02-18T12:00:00Z"
    }
  ],
  "count": 1,
  "limit": 100,
  "offset": 0
}
```

---

### 4. Get Project Efficiency

Get efficiency metrics for a specific project/listing.

**Endpoint:** `GET /api/v1/economic/projects/{project_id}/efficiency`

**Parameters:**
- `project_id` (path): UUID of the project/listing

**Response:**
```json
{
  "project_id": "uuid",
  "efficiency": 125.50,
  "total_income": 100.00,
  "total_costs": 79.68,
  "total_profit": 20.32,
  "cost_per_transaction": 7.97,
  "transaction_count": 10,
  "status": "thriving"
}
```

---

### 5. Evaluate Quality

Evaluate the quality of a listing or content.

**Endpoint:** `POST /api/v1/economic/quality/evaluate`

**Request Body:**
```json
{
  "listing_data": {
    "title": "Vintage Leather Jacket - Size M",
    "description": "Classic brown leather jacket in excellent condition...",
    "price": 79.99,
    "photos": ["photo1.jpg", "photo2.jpg"],
    "condition": "like_new"
  },
  "category": "clothing"
}
```

**Response:**
```json
{
  "overall_score": 85.50,
  "accuracy_score": 90.00,
  "completeness_score": 85.00,
  "professionalism_score": 82.00,
  "feedback": "Good quality overall with minor improvements possible.",
  "suggestions": [
    "Add more photos (aim for 3-5 images)",
    "Write a more detailed description (100+ characters)"
  ],
  "evaluation_method": "heuristic"
}
```

**Quality Scores:**
- All scores range from 0-100
- `overall_score`: Weighted average (40% accuracy, 30% completeness, 30% professionalism)
- `accuracy_score`: Pricing correctness and information accuracy
- `completeness_score`: Presence of all required fields
- `professionalism_score`: Formatting, clarity, and presentation

---

### 6. Batch Evaluate Quality

Evaluate multiple listings in a single request.

**Endpoint:** `POST /api/v1/economic/quality/evaluate-batch`

**Request Body:**
```json
[
  {
    "id": "uuid1",
    "title": "Item 1",
    "description": "Description 1",
    "price": 50.00
  },
  {
    "id": "uuid2",
    "title": "Item 2",
    "description": "Description 2",
    "price": 75.00
  }
]
```

**Response:**
```json
{
  "evaluations": [
    {
      "listing_id": "uuid1",
      "evaluation": {
        "overall_score": 75.00,
        "accuracy_score": 80.00,
        "completeness_score": 70.00,
        "professionalism_score": 75.00,
        "feedback": "...",
        "suggestions": []
      }
    }
  ]
}
```

---

### 7. Get Evaluation Prompt Example

Get an example LLM evaluation prompt to understand how quality evaluation works.

**Endpoint:** `GET /api/v1/economic/quality/prompt-example`

**Response:**
```json
{
  "sample_listing": {
    "title": "...",
    "description": "...",
    "price": 79.99
  },
  "llm_prompt": "You are a quality evaluation expert..."
}
```

---

## Economic Tracking

### Automatic Cost Tracking

The system automatically tracks costs for:

1. **AI Operations**: Token usage for GPT-4 and other models
   - Input tokens: $2.50 per 1M tokens (configurable)
   - Output tokens: $10.00 per 1M tokens (configurable)

2. **Compute Operations**: Processing time for image analysis, etc.
   - $0.10 per minute (configurable)

3. **API Costs**: External API calls (Stripe, EasyPost, etc.)

### Value Creation Tracking

The system tracks value created from:

1. **Listings**: Commission value calculated as `price × commission_rate`
   - Default commission rate: 5% (configurable)
   - Adjusted by quality score if available

2. **Licenses**: Revenue from license sales

3. **Shipments**: Profit from shipping services

### Balance Calculation

```
Balance = Starting Balance + Total Income - Total Costs
Profit = Total Income - Total Costs
Profit Margin = (Profit / Total Income) × 100%
ROI = (Profit / Total Costs) × 100%
```

---

## Configuration

Environment variables for economic tracking:

```bash
# Enable/disable economic tracking
ECONOMIC_ENABLED=true

# Default starting balance
ECONOMIC_DEFAULT_BALANCE=1000.00

# AI token pricing (per 1M tokens)
ECONOMIC_TOKEN_INPUT_PRICE_PER_1M=2.50
ECONOMIC_TOKEN_OUTPUT_PRICE_PER_1M=10.00

# Compute pricing
ECONOMIC_COMPUTE_COST_PER_MINUTE=0.10

# Listing commission rate
ECONOMIC_LISTING_COMMISSION_RATE=0.05

# Quality evaluation
QUALITY_EVAL_ENABLED=true
QUALITY_EVAL_MODEL=gpt-4-turbo-preview
```

---

## Error Codes

- `400 Bad Request`: Invalid entity_id format or parameters
- `403 Forbidden`: User doesn't have access to the entity
- `404 Not Found`: Ledger or entity not found
- `500 Internal Server Error`: Server error

---

## Rate Limiting

Quality evaluation endpoints are rate-limited to prevent excessive LLM costs:
- 10 evaluations per minute per user
- 100 evaluations per day per user

---

## Best Practices

1. **Monitor Your Balance**: Check your dashboard regularly to ensure healthy finances
2. **Optimize AI Usage**: Use AI features judiciously to control costs
3. **Quality Over Quantity**: Higher quality listings create more value
4. **Track Project Efficiency**: Monitor individual listing performance
5. **Review Transactions**: Audit transaction history for unexpected costs

---

## Examples

### Example: Create Listing with Quality Evaluation

```python
import httpx

async with httpx.AsyncClient() as client:
    # Create listing
    response = await client.post(
        "http://localhost:8000/listings",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Vintage Camera",
            "description": "Classic film camera in excellent condition",
            "price": 150.00,
            "category": "electronics"
        }
    )
    
    listing = response.json()
    print(f"Quality Score: {listing['quality_evaluation']['overall_score']}")
```

### Example: Monitor Economic Health

```python
# Get dashboard overview
response = await client.get(
    "http://localhost:8000/api/v1/economic/dashboard/overview",
    headers={"Authorization": f"Bearer {token}"}
)

dashboard = response.json()
print(f"Balance: ${dashboard['ledger']['balance']:.2f}")
print(f"Status: {dashboard['ledger']['status']}")
print(f"ROI: {dashboard['metrics']['roi']:.2f}%")
```

---

## Support

For questions or issues with the Economic Intelligence System, contact:
- Email: support@empirebox.store
- Documentation: https://docs.empirebox.store/economic-intelligence
