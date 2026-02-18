# EmpireBox - Complete Platform for Resellers

![EmpireBox](https://img.shields.io/badge/EmpireBox-Platform-blue)
![License](https://img.shields.io/badge/License-Proprietary-red)
![Status](https://img.shields.io/badge/Status-Development-yellow)

A comprehensive system combining Setup Portal, License Management, ShipForge shipping, agent safeguards, emergency stop protocols, and mobile marketplace functionality.

## 🎯 Project Overview

This repository contains the complete EmpireBox ecosystem:

1. **Setup Portal** - Web-based QR code activation flow for hardware bundles
2. **License System** - Generate, validate, and activate subscription licenses
3. **ShipForge** - Integrated shipping solution with EasyPost (compare rates, buy labels, print from phone)
4. **Hardware Bundles** - Pre-order system for Solana Seeker phones + subscriptions
5. **Agent Safeguards** - Production-ready safety system for autonomous agents
6. **Mobile App** - Flutter app with shipping integration and deep linking

## 📁 Repository Structure

```
Empire/
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── models/            # SQLAlchemy models (License, Shipment, PreOrder)
│   │   ├── schemas/           # Pydantic schemas for validation
│   │   ├── routers/           # API endpoints (licenses, shipping, preorders)
│   │   ├── services/          # Business logic (license gen, EasyPost integration)
│   │   ├── database.py        # Database configuration
│   │   └── main.py            # FastAPI app entry point
│   ├── requirements.txt       # Python dependencies
│   └── README.md              # Backend documentation
│
├── website/nextjs/            # Next.js Website
│   ├── src/
│   │   ├── app/
│   │   │   ├── setup/         # Setup portal pages
│   │   │   │   ├── page.tsx                    # Landing page
│   │   │   │   └── [licenseKey]/page.tsx      # Setup flow
│   │   │   ├── bundles/       # Hardware bundles showcase
│   │   │   ├── privacy/       # Privacy Policy (Stripe-required)
│   │   │   ├── terms/         # Terms of Service (Stripe-required)
│   │   │   ├── refund-policy/ # Refund Policy (Stripe-required)
│   │   │   ├── contact/       # Contact page
│   │   │   └── page.tsx       # Homepage
│   │   ├── components/
│   │   │   ├── setup/         # Setup flow components
│   │   │   ├── bundles/       # Bundle components
│   │   │   ├── Footer.tsx     # Site-wide footer
│   │   │   └── LegalPageLayout.tsx
│   │   └── lib/
│   │       └── api.ts         # API client
│   ├── package.json
│   └── README.md              # Website documentation
│
├── market_forge_app/          # Flutter Mobile App
│   ├── lib/
│   │   ├── models/            # Data models (Shipment, Address, etc.)
│   │   ├── services/          # API services (shipping, deep linking)
│   │   ├── providers/         # State management
│   │   ├── screens/           # App screens
│   │   │   ├── shipping_screen.dart
│   │   │   └── shipping/      # Shipping flow screens
│   │   ├── widgets/           # Reusable widgets
│   │   │   └── shipping/      # Shipping-specific widgets
│   │   └── main.dart          # App entry point
│   ├── pubspec.yaml
│   └── README.md              # App documentation
│
├── empire_box_agents/         # Agent Safeguards System
│   ├── emergency_stop.py      # Emergency stop protocol
│   ├── safeguards.py          # Rate limiting and budget management
│   ├── integration_guide.py   # Complete usage example
│   ├── test_emergency_stop.py # Unit tests
│   ├── test_safeguards.py     # Unit tests
│   ├── README.md              # Agent system documentation
│   └── CAPABILITIES.md        # Detailed capabilities guide
│
├── docs/                      # Comprehensive Documentation
│   ├── HARDWARE_BUNDLES.md    # Bundle specifications, pricing, sourcing
│   ├── QUICK_START_CARD.md    # QR card design specs
│   ├── SETUP_FLOW.md          # Complete setup flow documentation
│   ├── SHIPPING_INTEGRATION.md # EasyPost integration guide
│   ├── STRIPE_COMPLIANCE_CHECKLIST.md # Stripe requirements
│   └── SOLANA_PARTNERSHIP.md  # Partnership proposal template
│
└── README.md                  # This file
```

## 🚀 Features

### Backend (FastAPI)

✅ **License Key System**
- Generate unique license keys in format: `EMPIRE-XXXX-XXXX-XXXX`
- Validate and activate licenses
- Link to user accounts and pre-orders
- Track status (pending, activated, expired, revoked)

✅ **Shipping Integration (ShipForge)**
- Compare rates from USPS, FedEx, UPS via EasyPost
- Purchase shipping labels
- Track shipments
- Email labels as PDF
- Automatic tracking updates via webhooks

✅ **Pre-order System**
- Accept hardware bundle pre-orders
- Stripe payment integration
- Auto-generate license keys on payment
- Fulfillment tracking

✅ **Economic Intelligence System** 🆕
- Real-time cost and revenue tracking for all operations
- Automatic tracking of AI token usage, compute costs, and API calls
- Quality evaluation system for listings (AI-powered scoring)
- Economic dashboard with balance, profit margin, and ROI metrics
- Transaction history and audit trail
- Status indicators (thriving/stable/struggling/failing)
- See [Economic Intelligence Documentation](docs/ECONOMIC_INTELLIGENCE.md)

### Website (Next.js)

✅ **Setup Portal**
- Mobile-first QR code scanning flow
- Device detection (Android/iOS/Desktop)
- Step-by-step setup wizard:
  1. Download MarketForge app
  2. Create Solana wallet (Seeker only)
  3. Activate subscription
  4. Success with deep link to app
- License validation and activation
- Progress tracking with visual stepper

✅ **Legal Pages (Stripe-Compliant)**
- Privacy Policy (/privacy) - GDPR/CCPA compliant
- Terms of Service (/terms) - Subscription terms, auto-renewal disclosure
- Refund Policy (/refund-policy) - Clear refund and cancellation policy
- Contact Page (/contact) - Form and business information

✅ **Hardware Bundles**
- Showcase 3 bundle tiers (Budget, Pro, Empire)
- Pre-order checkout form
- Bundle comparison
- Payment integration (Stripe)

### Mobile App (Flutter)

✅ **Shipping Features**
- Create shipment workflow (from/to addresses, package details)
- Compare rates from multiple carriers
- Purchase labels directly in app
- Print labels via AirPrint (iOS) or Android Print Service
- Email labels to self or others
- Save labels to photo gallery
- Shipment history with filtering
- Real-time tracking

✅ **Deep Linking**
- Handle setup portal links: `empirebox.store/setup/EMPIRE-XXX...`
- Auto-open app and prompt license activation

### Agent Safeguards System

✅ **Safety Features**
- Emergency stop (manual and automatic)
- Rate limiting (actions per minute)
- Budget management (total action limits)
- Action whitelisting (approved operations only)
- State preservation during shutdown
- Administrator alerting
- Thread-safe operations

**Quick Example:**
```python
from empire_box_agents.emergency_stop import EmergencyStop
from empire_box_agents.safeguards import AgentSafeguards

# Create safeguards
safeguards = AgentSafeguards(
    rate_limit=60,     # 60 actions per minute
    budget=100,        # 100 total actions
    action_whitelist=["read", "write", "analyze"]
)

# Execute actions safely
try:
    safeguards.can_execute_action("read")
    # Perform your action here
except Exception as e:
    print(f"Action blocked: {e}")
```

## 🛠️ Setup Instructions

### Prerequisites

- **Backend**: Python 3.9+, pip
- **Website**: Node.js 16+, npm
- **Mobile App**: Flutter SDK 3.0+
- **Database**: SQLite (included) or PostgreSQL
- **External APIs**: EasyPost account, Stripe account

### Backend Setup

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys (EasyPost, Stripe, etc.)

# Initialize database
python -m app.init_db

# Run server
uvicorn app.main:app --reload

# API will be available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Website Setup

```bash
cd website/nextjs

# Install dependencies
npm install

# Configure environment
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Run development server
npm run dev

# Website will be available at http://localhost:3000
```

### Mobile App Setup

```bash
cd market_forge_app

# Install dependencies
flutter pub get

# Update API endpoint in lib/services/shipping_service.dart
# Change baseUrl to your API URL

# Run app (iOS)
flutter run -d ios

# Run app (Android)
flutter run -d android
```

### Agent System Setup

```bash
# No installation required - uses only Python standard library

# Run the integration demo
python empire_box_agents/integration_guide.py

# Run tests
python empire_box_agents/test_emergency_stop.py
python empire_box_agents/test_safeguards.py
```

## 📚 Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[ECONOMIC_INTELLIGENCE.md](docs/ECONOMIC_INTELLIGENCE.md)** 🆕 - Economic Intelligence System feature documentation and usage guide
- **[API_ECONOMIC.md](docs/API_ECONOMIC.md)** 🆕 - Economic Intelligence API reference with examples
- **[LEGAL_COMPLIANCE_AUDIT.md](docs/LEGAL_COMPLIANCE_AUDIT.md)** - Legal compliance audit, IP protection, competitive landscape, market intelligence
- **[HARDWARE_BUNDLES.md](docs/HARDWARE_BUNDLES.md)** - Complete bundle specifications, pricing, sourcing details
- **[QUICK_START_CARD.md](docs/QUICK_START_CARD.md)** - Print-ready QR card design, production specifications
- **[SETUP_FLOW.md](docs/SETUP_FLOW.md)** - Detailed setup flow documentation with UI mockups
- **[SHIPPING_INTEGRATION.md](docs/SHIPPING_INTEGRATION.md)** - EasyPost setup guide, integration details
- **[STRIPE_COMPLIANCE_CHECKLIST.md](docs/STRIPE_COMPLIANCE_CHECKLIST.md)** - Stripe application requirements
- **[SOLANA_PARTNERSHIP.md](docs/SOLANA_PARTNERSHIP.md)** - Partnership proposal template
- **[THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)** - Third-party dependency license tracking (SBOM)
- **[Agent System](empire_box_agents/README.md)** - Agent safeguards documentation
- **[Agent Capabilities](empire_box_agents/CAPABILITIES.md)** - Detailed capabilities guide

## 🔐 Environment Variables

### Backend (.env)

```bash
# Database
DATABASE_URL=sqlite:///./empirebox.db

# EasyPost (Shipping)
EASYPOST_API_KEY=your_production_key
EASYPOST_TEST_KEY=your_test_key
EASYPOST_TEST_MODE=true

# Stripe (Payments)
STRIPE_API_KEY=your_stripe_key
STRIPE_WEBHOOK_SECRET=your_webhook_secret

# Email (Optional, for sending labels)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

### Website (.env.local)

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000  # Backend API URL
```

## 🧪 Testing

### Backend Tests

```bash
cd backend
pytest
```

### Agent System Tests

```bash
cd empire_box_agents
python test_emergency_stop.py  # 10/10 tests pass
python test_safeguards.py      # 15/15 tests pass
```

### Test License Keys

Generate test licenses via API:

```bash
curl -X POST http://localhost:8000/licenses/generate \
  -H "Content-Type: application/json" \
  -d '{
    "plan": "pro",
    "duration_months": 12,
    "hardware_bundle": "seeker_pro",
    "quantity": 1
  }'
```

## 📱 Mobile App Deep Linking

### iOS Setup

Add to `ios/Runner/Info.plist`:

```xml
<key>CFBundleURLTypes</key>
<array>
  <dict>
    <key>CFBundleURLSchemes</key>
    <array>
      <string>marketforge</string>
    </array>
  </dict>
</array>
```

### Android Setup

Add to `android/app/src/main/AndroidManifest.xml`:

```xml
<intent-filter>
  <action android:name="android.intent.action.VIEW" />
  <category android:name="android.intent.category.DEFAULT" />
  <category android:name="android.intent.category.BROWSABLE" />
  <data
    android:scheme="https"
    android:host="empirebox.store"
    android:pathPrefix="/setup" />
</intent-filter>
```

## 🚢 Deployment

### Backend (Production)

```bash
# Using Gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker

# Or using Docker
docker build -t empirebox-backend .
docker run -p 8000:8000 empirebox-backend
```

### Website (Production)

```bash
# Build
npm run build

# Deploy to Vercel (recommended)
vercel deploy --prod
```

### Mobile App (Production)

```bash
# iOS
flutter build ios --release

# Android
flutter build apk --release
```

## 🎯 Key Features Summary

| Feature | Status | Platform |
|---------|--------|----------|
| License Key Generation | ✅ Complete | Backend |
| License Validation | ✅ Complete | Backend + Website |
| License Activation | ✅ Complete | Backend + Website |
| Setup Portal UI | ✅ Complete | Website |
| QR Code Scanning | ✅ Complete | Website |
| Legal Pages (Stripe) | ✅ Complete | Website |
| Hardware Bundle Showcase | ✅ Complete | Website |
| Pre-order System | ✅ Complete | Backend + Website |
| Shipping Rate Comparison | ✅ Complete | Backend + App |
| Label Purchase | ✅ Complete | Backend + App |
| Label Printing | ✅ Complete | App |
| Shipment Tracking | ✅ Complete | Backend + App |
| Deep Linking | ✅ Complete | App |
| Agent Safeguards | ✅ Complete | Python |
| Emergency Stop | ✅ Complete | Python |
| Economic Intelligence System | ✅ Complete | Backend |
| Cost Tracking (AI/Compute/API) | ✅ Complete | Backend |
| Quality Evaluation | ✅ Complete | Backend |
| Economic Dashboard API | ✅ Complete | Backend |

## 📄 License

Copyright © 2026 EmpireBox. All rights reserved.

This is proprietary software. Unauthorized copying, distribution, or use is strictly prohibited.

## 📞 Support

- **Email**: support@empirebox.store
- **General**: hello@empirebox.store
- **Documentation**: [docs.empirebox.store](https://docs.empirebox.store)

---

**Built with ❤️ by the EmpireBox Team**

*Last Updated: 2026-02-18*