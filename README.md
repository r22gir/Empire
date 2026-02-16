# MarketForge MVP - Photo to Sale Marketplace

A complete mobile application for posting product listings to multiple marketplace platforms simultaneously.

## Overview

MarketForge allows users to:
1. Take a photo of their product
2. Set a price and description
3. Post to multiple marketplaces (eBay, Facebook, Poshmark, Mercari, Craigslist) with one click
4. Track sales and earnings
5. Automatic 3% commission processing via Stripe

## Project Structure

```
Empire/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py            # Main FastAPI app
│   │   ├── database.py        # Database configuration
│   │   ├── models.py          # SQLAlchemy models
│   │   ├── schemas.py         # Pydantic schemas
│   │   ├── auth.py            # Authentication logic
│   │   ├── routers/           # API route handlers
│   │   │   ├── auth_router.py
│   │   │   └── listings_router.py
│   │   └── services/          # Business logic
│   │       ├── marketplace_service.py
│   │       └── payment_service.py
│   ├── requirements.txt       # Python dependencies
│   ├── .env.example          # Environment variables template
│   └── README.md             # Backend documentation
│
└── market_forge_app/          # Flutter mobile app
    ├── lib/
    │   ├── main.dart          # App entry point
    │   ├── models/            # Data models
    │   │   └── models.dart
    │   ├── screens/           # UI screens
    │   │   ├── login_screen.dart
    │   │   ├── dashboard_screen.dart
    │   │   └── create_listing_screen.dart
    │   ├── services/          # API integration
    │   │   └── api_service.dart
    │   └── widgets/           # Reusable components
    ├── pubspec.yaml          # Flutter dependencies
    └── assets/               # Images and resources
```

## Quick Start

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your API keys
```

5. Run the server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

6. Access API docs at http://localhost:8000/docs

### Flutter App Setup

1. Navigate to app directory:
```bash
cd market_forge_app
```

2. Get Flutter dependencies:
```bash
flutter pub get
```

3. Update API URL in `lib/services/api_service.dart`:
```dart
static const String baseUrl = 'http://YOUR_BACKEND_IP:8000';
```

4. Run the app:
```bash
flutter run
```

## Features Implemented

### Phase 1: Core Infrastructure ✅
- [x] FastAPI backend with SQLAlchemy ORM
- [x] Database schema (User, Listing, Sale, Payout)
- [x] User authentication with JWT
- [x] Flutter project structure

### Phase 2: Authentication ✅
- [x] User registration endpoint
- [x] User login with JWT tokens
- [x] Secure token storage in Flutter
- [x] Login/Register UI screens

### Phase 3: Listing Creation ✅
- [x] Photo upload functionality
- [x] Listing creation API
- [x] Multi-platform posting framework
- [x] Camera/Gallery integration in Flutter
- [x] Listing form UI

### Phase 4: Dashboard ✅
- [x] View all user listings
- [x] Dashboard UI
- [x] Pull-to-refresh functionality

### Phase 5: Payment Framework ✅
- [x] Stripe integration setup
- [x] Commission calculation (3%)
- [x] Payment service structure

## Marketplace Integrations (To Be Completed)

The following marketplace integrations need API credentials and implementation:

### 1. eBay
- **Status**: Framework ready, needs API implementation
- **Required**: eBay Developer Account
- **Docs**: https://developer.ebay.com
- **Implementation**: `backend/app/services/marketplace_service.py::post_to_ebay()`

### 2. Facebook Marketplace
- **Status**: Framework ready, needs API implementation
- **Required**: Facebook Developer Account
- **Docs**: https://developers.facebook.com/docs/marketplace
- **Implementation**: `backend/app/services/marketplace_service.py::post_to_facebook()`

### 3. Poshmark
- **Status**: Framework ready, needs API/alternative implementation
- **Required**: Poshmark API access or automation approach
- **Implementation**: `backend/app/services/marketplace_service.py::post_to_poshmark()`

### 4. Mercari
- **Status**: Framework ready, needs API implementation
- **Required**: Mercari API access
- **Implementation**: `backend/app/services/marketplace_service.py::post_to_mercari()`

### 5. Craigslist
- **Status**: Framework ready, needs automation implementation
- **Required**: Automation approach (no official API)
- **Implementation**: `backend/app/services/marketplace_service.py::post_to_craigslist()`

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login and get JWT token
- `GET /auth/me` - Get current user info

### Listings
- `POST /listings/` - Create new listing (multipart/form-data)
- `GET /listings/` - Get all user listings
- `GET /listings/{id}` - Get specific listing

## Environment Variables

Required environment variables (see `.env.example`):

```env
# Database
DATABASE_URL=sqlite:///./marketforge.db

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Marketplace APIs
EBAY_APP_ID=...
FACEBOOK_APP_ID=...
POSHMARK_API_KEY=...
MERCARI_API_KEY=...
```

## Next Steps for Production

1. **Complete Marketplace Integrations**
   - Register for developer accounts on each platform
   - Implement OAuth flows
   - Test listing creation on each platform

2. **Payment Integration**
   - Set up Stripe webhooks
   - Test commission collection
   - Implement payout system

3. **Testing**
   - Write unit tests for backend
   - Write integration tests for API
   - Test Flutter UI on iOS and Android

4. **Deployment**
   - Deploy backend to cloud (AWS, GCP, or Heroku)
   - Set up production database (PostgreSQL)
   - Submit Flutter app to App Store and Play Store
   - Configure SSL/HTTPS
   - Set up monitoring and logging

5. **Beta Testing**
   - Recruit beta testers
   - Monitor first transactions
   - Collect feedback
   - Iterate on features

## Success Metrics

- ✅ User can register and login
- ✅ User can create listings with photos
- ✅ UI for platform selection
- ⏳ Listings post to at least one marketplace
- ⏳ User makes first sale
- ⏳ Commission correctly calculated
- ⏳ Payment processing via Stripe

## Contributing

This is the MVP foundation. To contribute:

1. Complete marketplace API implementations
2. Add tests for new features
3. Improve UI/UX based on user feedback
4. Add error handling and edge cases
5. Optimize performance

## License

See LICENSE file.

## Contact

For questions or support, please open an issue on GitHub.
