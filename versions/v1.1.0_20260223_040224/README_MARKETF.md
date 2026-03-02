# MarketF - Peer-to-Peer Marketplace Platform

MarketF is EmpireBox's own marketplace platform with only **8% fees** (vs eBay's 12.9%), integrated ShipForge shipping, escrow payments, and seamless integration with MarketForge.

## 🚀 Features

- **Lower Fees**: Only 8% marketplace fee (save $4.90 per $100 sale vs eBay)
- **Built-in Shipping**: Integrated with ShipForge for easy label creation
- **Secure Escrow**: Buyer payments held until delivery confirmed
- **Cross-Posting**: List items from MarketForge with one click
- **Mobile & Web**: Full-featured apps for all platforms
- **Seller Dashboard**: Manage listings, orders, and reviews

## 📁 Project Structure

```
Empire/
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── models/marketplace/ # Database models
│   │   ├── schemas/marketplace/# Pydantic schemas
│   │   ├── routers/marketplace/# API endpoints
│   │   └── services/marketplace/# Business logic
│   └── requirements.txt
│
├── marketf_web/               # Next.js Web App
│   ├── src/
│   │   ├── app/              # App router pages
│   │   ├── components/       # React components
│   │   ├── lib/              # API client & utilities
│   │   └── styles/           # Global styles
│   └── package.json
│
├── market_forge_app/          # Flutter Mobile App
│   └── lib/
│       ├── models/           # Data models
│       ├── screens/marketf/  # MarketF screens
│       ├── services/         # API services
│       └── widgets/marketf/  # UI widgets
│
└── docs/                      # Documentation
    ├── MARKETF_OVERVIEW.md
    ├── MARKETF_API.md
    ├── MARKETF_FEES.md
    └── MARKETF_SELLER_GUIDE.md
```

## 🛠️ Setup Instructions

### Backend (FastAPI)

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your database and Stripe credentials

# Run the server
python -m uvicorn app.main:app --reload --port 8000
```

API will be available at `http://localhost:8000`

### Web App (Next.js)

```bash
cd marketf_web

# Install dependencies
npm install

# Run development server
npm run dev
```

Web app will be available at `http://localhost:3001`

### Mobile App (Flutter)

```bash
cd market_forge_app

# Install dependencies
flutter pub get

# Run on device/emulator
flutter run
```

## 🔑 Environment Variables

### Backend (.env)
```env
DATABASE_URL=postgresql://user:password@localhost:5432/marketf
SECRET_KEY=your-secret-key-here
STRIPE_SECRET_KEY=sk_test_...
MARKETF_FEE_PERCENT=8.0
MARKETF_ESCROW_RELEASE_DELAY_HOURS=48
```

### Web App (marketf_web/.env.local)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
```

## 📖 API Documentation

API documentation is available at:
- Development: `http://localhost:8000/docs`
- See also: [docs/MARKETF_API.md](docs/MARKETF_API.md)

## 💰 Fee Structure

```
Sale Price:                     $100.00
───────────────────────────────────────
Marketplace Fee (8%):           - $8.00
Payment Processing (2.9% + 0.30): - $3.20
───────────────────────────────────────
Seller Receives:                $88.80
```

**Compare to eBay**: Save $4.90 per $100 sale!

See [docs/MARKETF_FEES.md](docs/MARKETF_FEES.md) for detailed fee breakdown.

## 🔄 Integration with EmpireBox Ecosystem

### MarketForge Integration
- Cross-post listings to MarketF with one click
- Inventory syncs automatically
- Unified dashboard

### ShipForge Integration  
- Auto-fill shipping details from orders
- One-click label purchase
- Automatic tracking updates

## 📱 Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Payments**: Stripe
- **Authentication**: JWT tokens

### Web Frontend
- **Framework**: Next.js 14 (React)
- **Styling**: Tailwind CSS
- **State Management**: Zustand
- **Data Fetching**: SWR

### Mobile Frontend
- **Framework**: Flutter
- **State Management**: Provider
- **HTTP Client**: http package
- **Image Caching**: cached_network_image

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest
```

### Web Tests
```bash
cd marketf_web
npm test
```

### Mobile Tests
```bash
cd market_forge_app
flutter test
```

## 📚 Documentation

- [Platform Overview](docs/MARKETF_OVERVIEW.md) - Learn about MarketF
- [API Documentation](docs/MARKETF_API.md) - API endpoints reference
- [Fee Structure](docs/MARKETF_FEES.md) - Detailed fee breakdown
- [Seller Guide](docs/MARKETF_SELLER_GUIDE.md) - How to sell on MarketF

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

See [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Email**: support@marketf.com
- **Help Center**: [marketf.com/help](https://marketf.com/help)
- **Issues**: [GitHub Issues](https://github.com/r22gir/Empire/issues)

---

**MarketF** - Part of the EmpireBox ecosystem
*The Operating System for Resellers*
