# Economic Intelligence System - Quick Start Guide

## Setup

### 1. Apply Database Migration

```bash
cd backend
alembic upgrade head
```

This creates the `economic_ledgers` and `economic_transactions` tables.

### 2. Configure Environment Variables

Add to your `.env` file:

```bash
# Enable economic tracking
ECONOMIC_ENABLED=true
ECONOMIC_DEFAULT_BALANCE=1000.00

# AI token pricing (GPT-4)
ECONOMIC_TOKEN_INPUT_PRICE_PER_1M=2.50
ECONOMIC_TOKEN_OUTPUT_PRICE_PER_1M=10.00

# Other costs
ECONOMIC_COMPUTE_COST_PER_MINUTE=0.10
ECONOMIC_LISTING_COMMISSION_RATE=0.05

# Quality evaluation
QUALITY_EVAL_ENABLED=true
QUALITY_EVAL_MODEL=gpt-4-turbo-preview
```

### 3. Restart the Server

```bash
uvicorn app.main:app --reload
```

## Usage Examples

### Check Your Economic Dashboard

```bash
curl -X GET "http://localhost:8000/api/v1/economic/dashboard/overview" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "ledger": {
    "balance": 985.50,
    "total_income": 150.00,
    "total_costs": 164.50,
    "total_profit": -14.50,
    "status": "stable",
    "transaction_count": 25
  },
  "metrics": {
    "profit_margin": -9.67,
    "roi": -8.81,
    "recent_income_30d": 75.00,
    "recent_costs_30d": 82.50
  },
  "recent_transactions": [...]
}
```

### Create a Listing (with automatic quality evaluation)

```bash
curl -X POST "http://localhost:8000/listings" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Vintage Leather Jacket - Size M",
    "description": "Classic brown leather jacket in excellent condition",
    "price": 79.99,
    "category": "clothing",
    "condition": "like_new",
    "photos": [
      {"url": "photo1.jpg"},
      {"url": "photo2.jpg"}
    ]
  }'
```

The system will:
1. Create the listing
2. Evaluate its quality (automatic)
3. Record the listing value in your economic ledger
4. Return the created listing

### Manually Evaluate Quality

```bash
curl -X POST "http://localhost:8000/api/v1/economic/quality/evaluate" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "listing_data": {
      "title": "Vintage Camera",
      "description": "Classic film camera in excellent condition",
      "price": 150.00,
      "photos": ["photo1.jpg", "photo2.jpg", "photo3.jpg"],
      "category": "electronics"
    },
    "category": "electronics"
  }'
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
    "Write a more detailed description"
  ]
}
```

### View Transaction History

```bash
curl -X GET "http://localhost:8000/api/v1/economic/transactions?limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Check Project/Listing Efficiency

```bash
curl -X GET "http://localhost:8000/api/v1/economic/projects/LISTING_UUID/efficiency" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Understanding Your Status

| Status | Balance | What It Means |
|--------|---------|---------------|
| 🌟 **Thriving** | > $100 | Excellent financial health! |
| ✅ **Stable** | $10 - $100 | Good position, keep monitoring |
| ⚠️ **Struggling** | $0 - $10 | Warning: Low balance |
| ❌ **Failing** | < $0 | Urgent: Negative balance |

## Cost Tracking

### Automatic Tracking

The system automatically tracks costs when you:

- **Use AI features** (generate descriptions, enhance text, suggest prices)
  - Input tokens: $2.50 per 1M tokens
  - Output tokens: $10.00 per 1M tokens
  
- **Process images** (photo analysis, object detection)
  - $0.10 per minute of compute time
  
- **Call external APIs** (Stripe, EasyPost, etc.)
  - Varies by service

### Value Creation

The system records value when you:

- **Create listings** 
  - Base value = price × 5% commission
  - Adjusted by quality score
  
- **Sell items**
  - Actual revenue recorded
  
- **Generate licenses**
  - License revenue tracked

## Tips for Success

### 1. Monitor Your Balance
Check your dashboard daily:
```bash
curl "http://localhost:8000/api/v1/economic/dashboard/overview" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 2. Optimize AI Usage
- Use AI features strategically
- Batch operations when possible
- Monitor token costs in transaction history

### 3. Improve Quality Scores
Higher quality = more value created:
- Add detailed descriptions (100+ characters)
- Include 3-5 high-quality photos
- Specify all relevant details
- Use proper grammar and formatting

### 4. Track Project Efficiency
Monitor individual listings:
```bash
curl "http://localhost:8000/api/v1/economic/projects/{listing_id}/efficiency" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 5. Review Transactions
Audit your costs regularly:
```bash
# Filter by type
curl "http://localhost:8000/api/v1/economic/transactions?transaction_type=ai_token_cost" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Troubleshooting

### Issue: Economic tracking not working

**Solution:**
1. Check `ECONOMIC_ENABLED=true` in `.env`
2. Verify migration ran: `alembic current`
3. Check logs for errors

### Issue: Quality scores always 100

**Solution:**
1. Check `QUALITY_EVAL_ENABLED=true` in `.env`
2. System uses heuristic evaluation by default
3. For LLM evaluation, configure API key (future enhancement)

### Issue: Balance not updating

**Solution:**
1. Verify operations are being performed (create listings, use AI)
2. Check transaction history for recorded events
3. Ensure database connection is working

### Issue: API returns 403 Forbidden

**Solution:**
1. Verify JWT token is valid
2. Check you're accessing your own data (user_id matches)
3. Ensure proper Authorization header format

## Next Steps

1. **Integrate with Frontend**
   - Build React components for economic dashboard
   - Display quality scores on listings
   - Show transaction history

2. **Set Up Alerts**
   - Email notifications for low balance
   - Slack alerts for status changes
   - Daily/weekly reports

3. **Optimize Costs**
   - Review transaction patterns
   - Identify expensive operations
   - Batch AI operations

4. **Improve Quality**
   - Analyze quality trends
   - Compare against benchmarks
   - Iterate on listing formats

## API Documentation

For complete API reference, see:
- [API_ECONOMIC.md](API_ECONOMIC.md) - Full API documentation
- [ECONOMIC_INTELLIGENCE.md](ECONOMIC_INTELLIGENCE.md) - Feature guide

## Support

Need help?
- **Documentation**: https://docs.empirebox.store
- **Email**: support@empirebox.store
- **GitHub Issues**: https://github.com/r22gir/Empire/issues

---

**Pro Tip:** Start by creating a few listings and watching your balance. The system will automatically track costs and create value. Monitor your status and adjust your strategy based on the metrics!
