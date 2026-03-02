# Economic Intelligence System - Feature Documentation

## Overview

The Economic Intelligence System is a comprehensive financial tracking and analytics platform built into EmpireBox. It provides real-time monitoring of costs, revenue, and ROI for every operation, along with AI-powered quality evaluation and actionable insights.

## Key Features

### 1. Economic Ledger System

Every entity in the system (users, listings, shipments, licenses) has its own economic ledger that tracks:

- **Balance**: Current financial position
- **Total Income**: All revenue generated
- **Total Costs**: All expenses incurred
- **Total Profit**: Net profit/loss
- **Status**: Financial health indicator (thriving/stable/struggling/failing)
- **Transaction History**: Complete audit trail

### 2. Automatic Cost Tracking

The system automatically tracks costs for:

#### AI Operations
- Tracks token usage for GPT-4 and other language models
- Records input and output tokens separately
- Calculates costs based on current model pricing
- Supports multiple models with different pricing tiers

**Example:**
```python
# When generating a product description
input_tokens = 100
output_tokens = 200
cost = (100 * $2.50 / 1M) + (200 * $10.00 / 1M) = $0.0025
```

#### Compute Operations
- Tracks processing time for image analysis
- Records OpenCV processing costs
- Monitors background job execution time

**Example:**
```python
# When processing product photos
processing_time = 0.5 minutes
cost = 0.5 * $0.10/minute = $0.05
```

#### API Costs
- Tracks external API usage (Stripe, EasyPost, eBay)
- Records transaction fees
- Monitors third-party service costs

### 3. Value Creation Tracking

The system tracks value created from:

#### Listings
- Calculates potential commission value from listings
- Formula: `listing_price × commission_rate`
- Adjusts value based on quality score
- Records actual revenue when items sell

**Example:**
```python
# Listing created at $100 with 85% quality score
base_value = $100 * 0.05 (5% commission) = $5.00
adjusted_value = $5.00 * 0.85 = $4.25
```

#### Services
- License sales revenue
- Shipping service profits
- Premium feature subscriptions

### 4. Quality Evaluation System

AI-powered quality assessment for listings and content:

#### Evaluation Criteria

1. **Accuracy (0-100)**
   - Pricing appropriateness
   - Information correctness
   - Condition assessment honesty

2. **Completeness (0-100)**
   - Presence of required fields
   - Description detail level
   - Number of photos
   - Specification coverage

3. **Professionalism (0-100)**
   - Grammar and spelling
   - Formatting and organization
   - Professional tone
   - Content appropriateness

#### Overall Score Calculation
```
Overall Score = (Accuracy × 0.40) + (Completeness × 0.30) + (Professionalism × 0.30)
```

#### Category-Specific Rubrics

**Electronics:**
- Technical specifications emphasis
- Condition of components
- Model numbers and compatibility

**Clothing:**
- Size information clarity
- Material and care instructions
- Wear and damage disclosure

**Furniture:**
- Dimension accuracy
- Material quality details
- Assembly requirements

### 5. Performance Analytics

#### Dashboard Metrics

**Financial Health Indicators:**
- Current balance and status
- Income vs. costs trend
- Profit margin percentage
- Return on Investment (ROI)

**Operational Metrics:**
- Total transactions processed
- Average transaction cost
- Cost per listing created
- Revenue per listing sold

**Quality Metrics:**
- Average quality score
- Quality trend over time
- Category performance comparison

#### Project-Level Efficiency

Track efficiency for individual listings/projects:
- Total costs incurred
- Revenue generated
- Net profit/loss
- Cost per transaction
- Efficiency ratio (income/costs)

### 6. Status System

Automatic financial health classification:

| Status | Criteria | Actions |
|--------|----------|---------|
| **Thriving** | Balance > $100 | Operating normally, no restrictions |
| **Stable** | $10 < Balance ≤ $100 | Operating normally, monitor costs |
| **Struggling** | $0 < Balance ≤ $10 | Warning alerts, consider optimization |
| **Failing** | Balance ≤ $0 | Limited operations, urgent action needed |

### 7. Transaction Types

The system tracks various transaction types:

| Type | Description | Impact |
|------|-------------|--------|
| `ai_token_cost` | AI model token usage | Cost (negative) |
| `compute_cost` | Processing time costs | Cost (negative) |
| `api_cost` | External API calls | Cost (negative) |
| `listing_value` | Listing commission value | Income (positive) |
| `shipping_cost` | Shipping service costs | Cost (negative) |
| `license_revenue` | License sales | Income (positive) |

## Implementation Details

### Database Schema

#### Economic Ledgers Table
```sql
CREATE TABLE economic_ledgers (
    id UUID PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    balance NUMERIC(12, 2) DEFAULT 0.00,
    total_income NUMERIC(12, 2) DEFAULT 0.00,
    total_costs NUMERIC(12, 2) DEFAULT 0.00,
    total_profit NUMERIC(12, 2) DEFAULT 0.00,
    transaction_count NUMERIC(10, 0) DEFAULT 0,
    last_transaction_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'stable',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX ix_economic_ledgers_entity ON economic_ledgers(entity_type, entity_id);
```

#### Economic Transactions Table
```sql
CREATE TABLE economic_transactions (
    id UUID PRIMARY KEY,
    ledger_id UUID REFERENCES economic_ledgers(id),
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    transaction_type VARCHAR(50) NOT NULL,
    amount NUMERIC(12, 4) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    resource_details JSONB DEFAULT '{}',
    quality_score NUMERIC(5, 2),
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX ix_economic_transactions_entity ON economic_transactions(entity_type, entity_id);
CREATE INDEX ix_economic_transactions_type_created ON economic_transactions(transaction_type, created_at);
CREATE INDEX ix_economic_transactions_resource_details_gin ON economic_transactions USING GIN(resource_details);
```

### Service Architecture

```
┌─────────────────────────────────────────┐
│         Economic Intelligence           │
│              System                     │
└─────────────┬───────────────────────────┘
              │
    ┌─────────┴─────────┐
    │                   │
┌───▼────────┐   ┌─────▼──────────┐
│  Economic  │   │    Quality     │
│  Service   │   │   Evaluator    │
└───┬────────┘   └─────┬──────────┘
    │                   │
    │  Integrates with  │
    │                   │
┌───▼────────┬──────────▼──────────┐
│ AI Service │ Listing Service ... │
└────────────┴─────────────────────┘
```

### Integration Points

1. **AI Service**: Tracks token usage after every AI call
2. **Listing Service**: Records value creation and evaluates quality
3. **Shipping Service**: Tracks shipping costs
4. **License Service**: Records revenue from sales

### Configuration

All features are configurable via environment variables:

```bash
# Economic tracking
ECONOMIC_ENABLED=true                           # Master switch
ECONOMIC_DEFAULT_BALANCE=1000.00               # Starting balance
ECONOMIC_TOKEN_INPUT_PRICE_PER_1M=2.50         # GPT-4 input pricing
ECONOMIC_TOKEN_OUTPUT_PRICE_PER_1M=10.00       # GPT-4 output pricing
ECONOMIC_COMPUTE_COST_PER_MINUTE=0.10          # Compute pricing
ECONOMIC_LISTING_COMMISSION_RATE=0.05          # 5% commission

# Quality evaluation
QUALITY_EVAL_ENABLED=true                       # Enable quality eval
QUALITY_EVAL_MODEL=gpt-4-turbo-preview         # Model for evaluation
```

## Usage Examples

### Example 1: Monitor Economic Health

```python
from app.services.economic_service import EconomicService

# Get dashboard overview
economic_service = EconomicService(db)
overview = await economic_service.get_dashboard_overview("user", user.id)

print(f"Balance: ${overview['ledger']['balance']:.2f}")
print(f"Status: {overview['ledger']['status']}")
print(f"Profit Margin: {overview['metrics']['profit_margin']:.2f}%")
print(f"ROI: {overview['metrics']['roi']:.2f}%")
```

### Example 2: Track AI Costs

```python
# Record AI token usage
await economic_service.record_ai_cost(
    entity_type="user",
    entity_id=user.id,
    input_tokens=1000,
    output_tokens=500,
    model="gpt-4",
    description="Generate product description"
)
```

### Example 3: Evaluate Listing Quality

```python
from app.services.quality_evaluator import QualityEvaluator

quality_evaluator = QualityEvaluator(db)
evaluation = await quality_evaluator.evaluate_listing(
    listing_data={
        "title": "Vintage Camera",
        "description": "Classic film camera...",
        "price": 150.00,
        "photos": ["photo1.jpg", "photo2.jpg", "photo3.jpg"]
    },
    category="electronics"
)

print(f"Quality Score: {evaluation['overall_score']:.2f}")
print(f"Feedback: {evaluation['feedback']}")
print(f"Suggestions: {evaluation['suggestions']}")
```

### Example 4: Record Listing Value

```python
# When a listing is created
await economic_service.record_listing_value(
    user_id=user.id,
    listing_id=listing.id,
    sale_price=float(listing.price),
    quality_score=85.50
)
```

## Security & Privacy

### Tenant Isolation
- All queries enforce user/tenant boundaries
- No cross-tenant data leakage
- Automatic filtering by user_id

### Access Control
- All endpoints require authentication
- User can only access their own data
- Admin endpoints require admin role

### Audit Trail
- Complete transaction history
- Soft deletes preserve data
- Immutable transaction records

## Performance Optimization

### Database Indexes
- Composite indexes on (entity_type, entity_id)
- GIN indexes on JSONB columns
- Time-based indexes for transaction queries

### Caching Strategy
- Economic status cached for 5 minutes
- Dashboard data cached per user
- Transaction lists paginated

### Query Optimization
- Use of database aggregations
- Efficient date range queries
- Limit result sets appropriately

## Monitoring & Alerting

### Key Metrics to Monitor

1. **System Health**
   - Average transaction processing time
   - Database query performance
   - API response times

2. **User Activity**
   - Number of transactions per day
   - Average cost per user
   - Quality score distribution

3. **Financial Health**
   - Number of users by status (thriving/stable/struggling/failing)
   - Average balance across platform
   - Total platform profit/loss

### Alert Conditions

- User balance drops below $10 (struggling)
- User balance goes negative (failing)
- Unusual cost spikes (fraud detection)
- Quality scores consistently low

## Future Enhancements

### Phase 3: Advanced Analytics

1. **Predictive Insights**
   - Forecast balance based on trends
   - Predict cost overruns
   - Suggest optimization opportunities

2. **Benchmark Comparison**
   - Compare against platform averages
   - Category-specific benchmarks
   - Peer comparison (anonymized)

3. **Cost Optimization**
   - Identify expensive operations
   - Suggest cheaper alternatives
   - Automated cost optimization

4. **Gamification**
   - Achievement badges for efficiency
   - Leaderboards (opt-in)
   - Quality score challenges

### Roadmap

- **Q1 2026**: Core infrastructure (✅ Complete)
- **Q2 2026**: Quality evaluation and analytics
- **Q3 2026**: Advanced insights and predictions
- **Q4 2026**: Gamification and social features

## Troubleshooting

### Common Issues

**Issue**: Economic tracking not working
- Check `ECONOMIC_ENABLED=true` in .env
- Verify database migration has run
- Check logs for errors

**Issue**: Quality evaluation returns 100 always
- Check `QUALITY_EVAL_ENABLED=true` in .env
- Verify LLM API key is configured (when using real LLM)

**Issue**: Transaction history is empty
- Verify operations are being performed (AI usage, listings created)
- Check entity_type and entity_id are correct
- Ensure soft deletes are not hiding records

## Support

For questions or issues:
- **Documentation**: https://docs.empirebox.store
- **Email**: support@empirebox.store
- **GitHub Issues**: https://github.com/r22gir/Empire/issues

---

*Last Updated: 2026-02-18*
*Version: 1.0.0*
