# Shipping Integration (ShipForge) - EasyPost Setup Guide

## Overview

ShipForge is EmpireBox's integrated shipping solution that allows resellers to compare rates, purchase labels, and track shipments directly from the MarketForge app. This guide covers setting up the EasyPost integration.

## Why EasyPost?

- **Multi-Carrier**: Access USPS, FedEx, UPS, DHL, and 100+ carriers with one API
- **Discounted Rates**: ~15% discount on shipping labels
- **Simple API**: Well-documented REST API with excellent SDKs
- **Test Mode**: Full-featured testing environment
- **Address Validation**: Built-in address verification
- **Tracking**: Automatic tracking updates via webhooks

---

## Account Setup

### Step 1: Create EasyPost Account

1. Go to [easypost.com](https://www.easypost.com)
2. Click "Sign Up" (top right)
3. Fill in business information:
   - Company Name: EmpireBox LLC
   - Email: dev@empirebox.store
   - Phone: Your business phone
   - Use Case: "E-commerce / Marketplace Platform"
4. Verify email address

### Step 2: Billing Setup

**Important**: You need to add payment method before using production API

1. Go to Settings > Billing
2. Add credit card or ACH bank account
3. Set auto-recharge: $500 when balance drops below $100
4. Enable email notifications for low balance

**Pricing Structure**:
- No monthly fees
- Pay only for labels purchased
- Rates typically 15-20% below retail
- Example: USPS Priority Mail that costs $10 retail = $8.50 on EasyPost

### Step 3: Get API Keys

1. Go to Settings > API Keys
2. You'll see two keys:
   - **Test API Key**: Starts with `EZ TEST...` (for development)
   - **Production API Key**: Starts with `EZ PROD...` (for live labels)

**Store these securely**:
```bash
# In your .env file
EASYPOST_TEST_KEY=EZTESTXXXXXXXXXXXXX
EASYPOST_API_KEY=EZPRODXXXXXXXXXXXXX
```

---

## Backend Integration

### Step 1: Install Python SDK

```bash
pip install easypost
```

### Step 2: Configure Service

Update `backend/app/services/shipping_service.py`:

```python
import easypost
import os

class ShippingService:
    def __init__(self):
        # Use test key in development, production key in production
        is_production = os.getenv('ENVIRONMENT') == 'production'
        
        if is_production:
            easypost.api_key = os.getenv('EASYPOST_API_KEY')
        else:
            easypost.api_key = os.getenv('EASYPOST_TEST_KEY')
        
        self.test_mode = not is_production
    
    async def get_rates(self, from_address, to_address, parcel):
        """Get shipping rates from multiple carriers"""
        
        # Create shipment with EasyPost
        shipment = easypost.Shipment.create(
            from_address={
                'name': from_address.name,
                'street1': from_address.street1,
                'street2': from_address.street2,
                'city': from_address.city,
                'state': from_address.state,
                'zip': from_address.zip,
                'country': from_address.country,
            },
            to_address={
                'name': to_address.name,
                'street1': to_address.street1,
                'street2': to_address.street2,
                'city': to_address.city,
                'state': to_address.state,
                'zip': to_address.zip,
                'country': to_address.country,
            },
            parcel={
                'length': parcel.length,
                'width': parcel.width,
                'height': parcel.height,
                'weight': parcel.weight,
            }
        )
        
        # EasyPost returns rates from all carriers
        rates = []
        for rate in shipment.rates:
            # Calculate our markup (pass savings to customer)
            our_price = self.calculate_markup(float(rate.rate))
            
            rates.append(ShippingRate(
                carrier=rate.carrier,
                service=rate.service,
                rate=float(rate.rate),
                our_price=our_price,
                delivery_days=rate.delivery_days,
                shipment_id=shipment.id,
                rate_id=rate.id,
            ))
        
        # Sort by price (cheapest first)
        return sorted(rates, key=lambda r: r.our_price)
    
    def calculate_markup(self, base_rate):
        """
        Apply our margin to the shipping rate
        EasyPost gives us ~15% discount
        We pass ~half the discount to customer, keep half as profit
        """
        # Example: $10 label
        # EasyPost charges us: $8.50 (15% discount)
        # We charge customer: $9.25 (split savings)
        # Customer saves: $0.75
        # We profit: $0.75
        
        discount_rate = base_rate * 0.85  # Our cost from EasyPost
        markup = (base_rate - discount_rate) * 0.5  # Half of savings
        return round(discount_rate + markup, 2)
    
    async def purchase_label(self, shipment_id, rate_id):
        """Purchase a shipping label"""
        
        # Retrieve the shipment
        shipment = easypost.Shipment.retrieve(shipment_id)
        
        # Buy the label with selected rate
        shipment.buy(rate={'id': rate_id})
        
        # EasyPost returns label URLs
        label_data = {
            'tracking_number': shipment.tracking_code,
            'label_url': shipment.postage_label.label_url,  # PNG image
            'label_pdf_url': shipment.postage_label.label_pdf_url,  # PDF for printing
            'carrier': shipment.selected_rate.carrier,
            'service': shipment.selected_rate.service,
            'cost': float(shipment.selected_rate.rate),
        }
        
        return label_data
```

### Step 3: Test the Integration

Create a test script:

```python
# test_easypost.py

import easypost
import os

easypost.api_key = os.getenv('EASYPOST_TEST_KEY')

# Test addresses (provided by EasyPost)
from_address = {
    'name': 'EmpireBox',
    'street1': '388 Townsend St',
    'city': 'San Francisco',
    'state': 'CA',
    'zip': '94107',
    'country': 'US',
}

to_address = {
    'name': 'Dr. Steve Brule',
    'street1': '179 N Harbor Dr',
    'city': 'Redondo Beach',
    'state': 'CA',
    'zip': '90277',
    'country': 'US',
}

parcel = {
    'length': 10,
    'width': 8,
    'height': 6,
    'weight': 16,  # ounces
}

# Create shipment
shipment = easypost.Shipment.create(
    from_address=from_address,
    to_address=to_address,
    parcel=parcel
)

print(f"Shipment ID: {shipment.id}")
print(f"Found {len(shipment.rates)} rates:")

for rate in shipment.rates[:5]:  # Show first 5
    print(f"  {rate.carrier} {rate.service}: ${rate.rate} ({rate.delivery_days} days)")

# Buy cheapest rate
cheapest = min(shipment.rates, key=lambda r: float(r.rate))
print(f"\nBuying cheapest rate: {cheapest.carrier} {cheapest.service}")

shipment.buy(rate=cheapest)

print(f"Label URL: {shipment.postage_label.label_url}")
print(f"Tracking: {shipment.tracking_code}")
```

Run test:
```bash
python test_easypost.py
```

---

## Carrier Accounts

### Default Carrier Accounts

EasyPost provides default carrier accounts for:
- **USPS**: Instant access, no setup needed
- **UPS**: Instant access, slightly higher rates
- **FedEx**: Instant access, slightly higher rates

### Custom Carrier Accounts (Optional)

For better rates, connect your own carrier accounts:

#### USPS Commercial Plus
1. Sign up at usps.com/business
2. Apply for Commercial Plus pricing (requires volume)
3. In EasyPost: Settings > Carrier Accounts > Add USPS Account
4. Enter your USPS credentials

**Benefits**:
- 5-10% additional discount
- Access to cubic pricing (for small, heavy items)

#### UPS Account
1. Create UPS account at ups.com
2. Negotiate rates with UPS rep (mention shipping volume)
3. Connect to EasyPost: Settings > Carrier Accounts > Add UPS

**Benefits**:
- Negotiate custom rates based on volume
- Access to UPS SurePost (cheaper for residential)

#### FedEx Account
Similar process to UPS.

---

## Address Validation

EasyPost includes free address validation:

```python
# Validate address before creating shipment
address = easypost.Address.create(
    street1='388 Townsend St',
    city='San Francisco',
    state='CA',
    zip='94107',
    country='US',
    verify=['delivery']  # Verify address
)

if address.verifications.delivery.success:
    print("Address is valid!")
    # Use address.street1, address.city, etc. (normalized)
else:
    print("Address validation failed:")
    print(address.verifications.delivery.errors)
```

**Always validate addresses before purchasing labels** to avoid:
- Undeliverable packages
- Return fees ($15-20)
- Customer complaints

---

## Tracking & Webhooks

### Automatic Tracking Updates

Set up webhooks to receive tracking updates automatically:

1. Go to Settings > Webhooks
2. Add webhook: `https://api.empirebox.store/webhooks/easypost`
3. Select events:
   - `tracker.created`
   - `tracker.updated`

### Backend Webhook Handler

```python
# backend/app/routers/webhooks.py

from fastapi import APIRouter, Request
import hmac
import hashlib

router = APIRouter()

@router.post("/webhooks/easypost")
async def easypost_webhook(request: Request):
    # Verify webhook signature
    signature = request.headers.get('X-Webhook-Signature')
    body = await request.body()
    
    expected_signature = hmac.new(
        os.getenv('EASYPOST_WEBHOOK_SECRET').encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    if signature != expected_signature:
        return {"error": "Invalid signature"}, 401
    
    # Parse webhook data
    data = await request.json()
    event_type = data['description']
    
    if event_type == 'tracker.updated':
        tracker = data['result']
        tracking_number = tracker['tracking_code']
        status = tracker['status']
        
        # Update shipment in database
        await update_shipment_status(tracking_number, status)
        
        # Send notification to user
        await notify_user(tracking_number, status)
    
    return {"received": True}
```

### Manual Tracking

For on-demand tracking:

```python
def track_shipment(tracking_number):
    tracker = easypost.Tracker.create(
        tracking_code=tracking_number
    )
    
    return {
        'status': tracker.status,
        'status_detail': tracker.status_detail,
        'est_delivery_date': tracker.est_delivery_date,
        'events': [
            {
                'datetime': event.datetime,
                'message': event.message,
                'city': event.tracking_location.city,
                'state': event.tracking_location.state,
            }
            for event in tracker.tracking_details
        ]
    }
```

---

## Testing

### Test Mode Features

EasyPost test mode provides:
- **Test tracking numbers**: `EZ1000000001`, `EZ2000000002`, etc.
- **Test cards**: No real shipping charges
- **Test addresses**: Pre-defined addresses that simulate scenarios

### Test Scenarios

```python
# Successful delivery
to_address = {
    'street1': '179 N Harbor Dr',
    'city': 'Redondo Beach',
    'state': 'CA',
    'zip': '90277',
}

# Address validation failure
to_address = {
    'street1': '123 FAKE STREET',
    'city': 'Nowhere',
    'state': 'XX',
    'zip': '00000',
}

# International address
to_address = {
    'street1': '55 Rue du Faubourg Saint-Honoré',
    'city': 'Paris',
    'zip': '75008',
    'country': 'FR',
}
```

---

## Production Checklist

Before going live:

- [ ] Production API key configured in environment
- [ ] Billing information added to EasyPost account
- [ ] Auto-recharge enabled (recommend $500 threshold)
- [ ] Webhooks configured for tracking updates
- [ ] Address validation enabled for all shipments
- [ ] Error handling for failed purchases
- [ ] Logging for all API calls (for debugging)
- [ ] Test with real addresses and labels
- [ ] Confirm label printing works on target devices

---

## Cost Optimization Tips

### 1. Use Correct Packaging
- Flat Rate boxes often cheaper for heavy items
- Regional Rate boxes for zones 1-4
- Always measure accurately (wrong size = higher cost)

### 2. Compare All Carriers
- USPS best for lightweight (< 1 lb)
- FedEx/UPS better for heavy (> 5 lbs)
- UPS SurePost/FedEx SmartPost for non-urgent

### 3. Batch Shipping
- Ship all orders at once (morning pickup)
- Negotiate volume discounts with carriers

### 4. Address Validation
- Invalid addresses = return fees ($15-20 each)
- Always validate before purchasing

### 5. Insurance
- Only insure high-value items (> $100)
- Most packages don't need insurance

---

## Troubleshooting

### Common Issues

**Issue**: "Insufficient postage" error
- **Cause**: Weight or dimensions incorrect
- **Fix**: Remeasure package, update parcel details

**Issue**: Address validation fails
- **Cause**: Typo in address
- **Fix**: Ask customer to verify address

**Issue**: Rate not available for carrier
- **Cause**: Destination not serviced, or restrictions
- **Fix**: Offer alternative carrier

**Issue**: Label won't print
- **Cause**: PDF format incompatible with printer
- **Fix**: Use PNG label_url instead of PDF

### Support Contacts

- **EasyPost Support**: support@easypost.com
- **EasyPost Docs**: easypost.com/docs
- **EasyPost Status**: status.easypost.com

---

## Pricing Examples

Real-world cost comparison:

| Package | Destination | USPS Retail | EasyPost Cost | Our Price | Customer Saves |
|---------|-------------|-------------|---------------|-----------|----------------|
| Small (8oz) | CA to NY | $8.95 | $7.61 | $8.28 | $0.67 |
| Medium (1lb) | CA to TX | $12.50 | $10.63 | $11.56 | $0.94 |
| Large (3lbs) | CA to FL | $18.75 | $15.94 | $17.34 | $1.41 |

**Profit per label**: ~7-8% of retail price

---

*Document Version: 1.0*
*Last Updated: 2026-02-17*
*Owner: EmpireBox Engineering Team*
