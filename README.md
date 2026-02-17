# EmpireBox - Complete Setup Portal, License System & ShipForge Integration

![EmpireBox](https://img.shields.io/badge/EmpireBox-Setup%20Portal-blue)
![License](https://img.shields.io/badge/License-Proprietary-red)
![Status](https://img.shields.io/badge/Status-Development-yellow)

Complete implementation of EmpireBox Setup Portal, License Key Management System, Hardware Bundle Pre-orders, and ShipForge shipping integration for MarketForge reselling platform.

## 🎯 Project Overview

This repository contains the complete EmpireBox ecosystem:

1. **Setup Portal** - Web-based QR code activation flow for hardware bundles
2. **License System** - Generate, validate, and activate subscription licenses
3. **ShipForge** - Integrated shipping solution with EasyPost (compare rates, buy labels, print from phone)
4. **Hardware Bundles** - Pre-order system for Solana Seeker phones + subscriptions
5. **Mobile App** - Flutter app with shipping integration and deep linking

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
│   │   │   └── page.tsx       # Homepage
│   │   ├── components/
│   │   │   ├── setup/         # Setup flow components
│   │   │   └── bundles/       # Bundle components
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
├── docs/                      # Comprehensive Documentation
│   ├── HARDWARE_BUNDLES.md    # Bundle specifications, pricing, sourcing
│   ├── QUICK_START_CARD.md    # QR card design specs
│   ├── SETUP_FLOW.md          # Complete setup flow documentation
│   ├── SHIPPING_INTEGRATION.md # EasyPost integration guide
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

## 📚 Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[HARDWARE_BUNDLES.md](docs/HARDWARE_BUNDLES.md)** - Complete bundle specifications, pricing, sourcing details, fulfillment options
- **[QUICK_START_CARD.md](docs/QUICK_START_CARD.md)** - Print-ready QR card design, production specifications
- **[SETUP_FLOW.md](docs/SETUP_FLOW.md)** - Detailed setup flow documentation with UI mockups
- **[SHIPPING_INTEGRATION.md](docs/SHIPPING_INTEGRATION.md)** - EasyPost setup guide, integration details, testing
- **[SOLANA_PARTNERSHIP.md](docs/SOLANA_PARTNERSHIP.md)** - Partnership proposal template for Solana Foundation

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

### Test License Keys

The backend automatically generates test licenses. You can also generate them via API:

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

### Test Shipping (EasyPost Test Mode)

The shipping service runs in test mode by default. Use these test addresses:

**From Address:**
```json
{
  "name": "EmpireBox",
  "street1": "388 Townsend St",
  "city": "San Francisco",
  "state": "CA",
  "zip": "94107"
}
```

**To Address:**
```json
{
  "name": "Test Customer",
  "street1": "179 N Harbor Dr",
  "city": "Redondo Beach",
  "state": "CA",
  "zip": "90277"
}
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

# Or deploy to any static host
npm run build && npm run start
```

### Mobile App (Production)

```bash
# iOS
flutter build ios --release

# Android
flutter build apk --release
# or
flutter build appbundle --release
```

## 🎯 Key Features Summary

| Feature | Status | Platform |
|---------|--------|----------|
| License Key Generation | ✅ Complete | Backend |
| License Validation | ✅ Complete | Backend + Website |
| License Activation | ✅ Complete | Backend + Website |
| Setup Portal UI | ✅ Complete | Website |
| QR Code Scanning | ✅ Complete | Website |
| Device Detection | ✅ Complete | Website |
| Wallet Setup Guide | ✅ Complete | Website |
| Hardware Bundle Showcase | ✅ Complete | Website |
| Pre-order System | ✅ Complete | Backend + Website |
| Shipping Rate Comparison | ✅ Complete | Backend + App |
| Label Purchase | ✅ Complete | Backend + App |
| Label Printing | ✅ Complete | App |
| Shipment Tracking | ✅ Complete | Backend + App |
| Deep Linking | ✅ Complete | App |

## 🤝 Contributing

This is a proprietary project for EmpireBox. Internal team members should follow the contribution guidelines in the team wiki.

## 📄 License

Copyright © 2026 EmpireBox. All rights reserved.

This is proprietary software. Unauthorized copying, distribution, or use is strictly prohibited.

## 📞 Support

- **Email**: support@empirebox.store
- **Documentation**: [docs.empirebox.store](https://docs.empirebox.store)
- **Status Page**: [status.empirebox.store](https://status.empirebox.store)

---

**Built with ❤️ by the EmpireBox Team**

*Last Updated: 2026-02-17*
