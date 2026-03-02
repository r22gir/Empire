# SupportForge Integration Guide

## Quick Start

### 1. Backend Setup

```bash
# Navigate to backend
cd backend

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Run database migration
alembic upgrade head

# Start the server
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### 2. Verify Installation

```bash
# Run validation script
python test_supportforge_implementation.py

# Run demo
python demo_supportforge.py
```

### 3. Access API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Examples

### Create a Tenant

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/supportforge/tenants",
    json={
        "name": "My Company Support",
        "subdomain": "mycompany",
        "plan": "professional"
    }
)
tenant = response.json()
print(f"Tenant ID: {tenant['id']}")
```

### Create a Customer

```python
response = requests.post(
    "http://localhost:8000/api/v1/supportforge/customers",
    json={
        "tenant_id": tenant_id,
        "email": "customer@example.com",
        "name": "Jane Doe",
        "company": "Example Corp"
    }
)
customer = response.json()
```

### Create a Ticket

```python
response = requests.post(
    "http://localhost:8000/api/v1/supportforge/tickets",
    json={
        "tenant_id": tenant_id,
        "customer_id": customer['id'],
        "subject": "Unable to login",
        "channel": "email",
        "priority": "high"
    }
)
ticket = response.json()
print(f"Ticket #{ticket['ticket_number']} created")
```

### Add a Message to Ticket

```python
response = requests.post(
    f"http://localhost:8000/api/v1/supportforge/tickets/{ticket['id']}/messages",
    json={
        "ticket_id": ticket['id'],
        "sender_type": "customer",
        "content": "I'm getting an 'Invalid credentials' error when trying to log in."
    }
)
```

### Get AI Response Suggestion

```python
response = requests.post(
    "http://localhost:8000/api/v1/supportforge/ai/suggest-response",
    json={
        "ticket_id": ticket['id']
    }
)
suggestion = response.json()
print(f"AI Suggestion: {suggestion['suggested_response']}")
print(f"Confidence: {suggestion['confidence']}")
```

### Auto-Categorize Ticket

```python
response = requests.post(
    "http://localhost:8000/api/v1/supportforge/ai/categorize",
    json={
        "subject": "Payment failed",
        "content": "I tried to pay my invoice but my credit card was declined"
    }
)
result = response.json()
print(f"Category: {result['category']}")
print(f"Tags: {result['tags']}")
print(f"Priority: {result['priority']}")
```

### Get Customer Empire Context

```python
response = requests.get(
    f"http://localhost:8000/api/v1/supportforge/customers/{customer['id']}/empire-context"
)
context = response.json()
print(f"Product Type: {context['product_type']}")
print(f"Projects: {context['projects_count']}")
print(f"Usage: ${context['usage_this_month']['cost']}")
```

## Integration with ContractorForge

### Linking Customers

When creating a customer, link them to their ContractorForge account:

```python
response = requests.post(
    "http://localhost:8000/api/v1/supportforge/customers",
    json={
        "tenant_id": tenant_id,
        "email": "contractor@example.com",
        "name": "Bob Builder",
        "empire_product_id": contractorforge_user_id,
        "empire_product_type": "contractorforge"
    }
)
```

### Accessing Empire Context

The support agent can then access rich context:

```python
context = requests.get(
    f"http://localhost:8000/api/v1/supportforge/customers/{customer_id}/empire-context"
).json()

# Context includes:
# - Project history
# - Estimate data
# - AI usage metrics
# - Payment status
# - Recent activity
```

### Auto-Creating Tickets

ContractorForge can automatically create support tickets when issues occur:

```python
# From ContractorForge error handler
def handle_critical_error(user_id, error):
    # Create ticket in SupportForge
    response = requests.post(
        "http://localhost:8000/api/v1/supportforge/tickets",
        json={
            "tenant_id": SUPPORTFORGE_TENANT_ID,
            "customer_id": get_supportforge_customer_id(user_id),
            "subject": f"Critical Error: {error.type}",
            "channel": "api",
            "priority": "urgent",
            "category": "technical"
        },
        headers={
            "Authorization": f"Bearer {API_KEY}"
        }
    )
    
    # Add error details
    ticket = response.json()
    requests.post(
        f"http://localhost:8000/api/v1/supportforge/tickets/{ticket['id']}/messages",
        json={
            "ticket_id": ticket['id'],
            "sender_type": "system",
            "content": f"Error details:\n{error.traceback}"
        }
    )
```

## Embedding Chat Widget

### Basic HTML Integration

```html
<!-- Add to your website -->
<div id="supportforge-widget"></div>
<script src="https://cdn.supportforge.com/widget.js"></script>
<script>
  SupportForge.init({
    tenantId: 'your-tenant-id',
    apiKey: 'your-public-api-key',
    position: 'bottom-right',
    color: '#007bff'
  });
</script>
```

### React Integration

```jsx
import { SupportForgeWidget } from '@supportforge/react';

function App() {
  return (
    <div>
      {/* Your app content */}
      <SupportForgeWidget
        tenantId="your-tenant-id"
        apiKey="your-public-api-key"
        user={{
          email: currentUser.email,
          name: currentUser.name
        }}
      />
    </div>
  );
}
```

## Webhooks

### Setting Up Webhooks

Configure webhooks to receive real-time notifications:

```python
response = requests.post(
    "http://localhost:8000/api/v1/supportforge/integrations",
    json={
        "tenant_id": tenant_id,
        "integration_type": "webhook",
        "webhook_url": "https://your-app.com/webhooks/supportforge",
        "is_active": True
    }
)
```

### Webhook Events

Your endpoint will receive:
- `ticket.created`
- `ticket.updated`
- `ticket.resolved`
- `message.received`
- `customer.created`

Example payload:
```json
{
  "event": "ticket.created",
  "timestamp": "2026-02-18T10:30:00Z",
  "data": {
    "ticket_id": "uuid",
    "ticket_number": 1001,
    "subject": "Help needed",
    "priority": "high",
    "customer": {
      "email": "customer@example.com",
      "name": "John Doe"
    }
  }
}
```

## Email Integration

### Incoming Email

Configure your email server to forward support emails:

```
support@yourcompany.com → supportforge@parse.supportforge.com
```

SupportForge will:
1. Parse the email
2. Create or update ticket
3. Extract attachments
4. Link to existing customer by email
5. Auto-categorize using AI

### Outgoing Email

Responses are automatically sent via email:

```python
# When agent replies, customer receives email
response = requests.post(
    f"http://localhost:8000/api/v1/supportforge/tickets/{ticket_id}/messages",
    json={
        "ticket_id": ticket_id,
        "sender_type": "agent",
        "sender_id": agent_id,
        "content": "Here's the solution to your issue...",
        "is_internal_note": False  # Customer will receive email
    }
)
```

## SMS Integration

### Enabling SMS Support

```bash
# Configure in .env
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=+1234567890
```

### Receiving SMS

When customer texts your support number:
1. Twilio webhook triggers SupportForge
2. Ticket is created or updated
3. Agent responds via dashboard
4. Response sent as SMS

## Automation Rules

### Creating Automation

```python
response = requests.post(
    "http://localhost:8000/api/v1/supportforge/automations",
    json={
        "tenant_id": tenant_id,
        "name": "Auto-assign billing tickets",
        "trigger_type": "ticket_created",
        "conditions": {
            "category": "billing"
        },
        "actions": [
            {
                "type": "assign_agent",
                "agent_email": "billing@company.com"
            },
            {
                "type": "add_tags",
                "tags": ["billing", "auto-assigned"]
            }
        ],
        "is_active": True
    }
)
```

### Supported Triggers
- `ticket_created`
- `message_received`
- `status_changed`
- `tag_added`
- `sla_breached`
- `no_response_timeout`

### Supported Actions
- `assign_agent`
- `add_tags`
- `change_priority`
- `send_webhook`
- `auto_reply`
- `escalate`

## SLA Policies

### Creating SLA Policy

```python
response = requests.post(
    "http://localhost:8000/api/v1/supportforge/sla-policies",
    json={
        "tenant_id": tenant_id,
        "name": "Premium Support",
        "first_response_time_minutes": 15,
        "resolution_time_minutes": 240,
        "business_hours_only": True,
        "priority_multipliers": {
            "urgent": 0.5,
            "high": 0.75,
            "normal": 1.0,
            "low": 2.0
        }
    }
)
```

### Monitoring SLA Compliance

```python
# Get SLA metrics
response = requests.get(
    f"http://localhost:8000/api/v1/supportforge/analytics/sla?tenant_id={tenant_id}"
)
metrics = response.json()
print(f"Compliance Rate: {metrics['compliance_rate']}%")
print(f"Breached Tickets: {metrics['breached_count']}")
```

## Best Practices

### 1. Multi-Tenant Isolation
Always include `tenant_id` in queries to ensure data isolation:

```python
# Good
tickets = list_tickets(tenant_id=current_tenant)

# Bad - could leak data
tickets = list_all_tickets()
```

### 2. AI Cost Management
Monitor AI usage to control costs:

```python
# Check AI costs before making request
if customer.ai_budget_remaining > 0:
    suggestion = get_ai_suggestion(ticket_id)
```

### 3. Rate Limiting
Implement rate limiting for public endpoints:

```python
from fastapi_limiter import Limiter

@app.post("/api/v1/supportforge/tickets")
@limiter.limit("10/minute")
async def create_ticket():
    pass
```

### 4. Security
- Always validate `tenant_id` matches authenticated user
- Use API keys for external integrations
- Encrypt sensitive customer data
- Implement RBAC for agents

## Troubleshooting

### Tickets Not Creating

1. Check database connection
2. Verify tenant exists
3. Check customer exists
4. Review API logs

### AI Features Not Working

1. Verify `OPENAI_API_KEY` is set
2. Check API quota/limits
3. Review error logs
4. Test with simple prompt

### Email Not Sending

1. Verify SMTP configuration
2. Check email credentials
3. Test with simple email
4. Review email service logs

## Support

For questions or issues:
- Email: support@empirebox.store
- Documentation: https://docs.empirebox.store/supportforge
- GitHub: https://github.com/r22gir/Empire

---

**Version**: 1.0.0  
**Last Updated**: 2026-02-18
