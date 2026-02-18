# ContractorForge - Universal SaaS Platform for Service Businesses

ContractorForge is a complete, production-ready **universal SaaS platform** designed for service-based businesses. It features AI-powered conversational intake, photo-based measurements, intelligent quoting, and multi-tenant architecture.

## 🎯 Overview

ContractorForge provides a single codebase that serves multiple industries through **configurable templates**:

- **LuxeForge** - Custom workrooms (drapery, window treatments)
- **ElectricForge** - Electrical contractors
- **LandscapeForge** - Landscaping businesses

Each template customizes pricing methods, AI prompts, workflows, catalogs, and terminology while sharing the same core platform.

## ✨ Key Features

### Universal Platform Core
- 🤖 **AI Conversational Intake** - GPT-4 powered natural language project scoping
- 📸 **Photo Measurements** - Automatic measurements using OpenCV + depth estimation
- 💰 **Smart Quoting** - Industry-specific pricing rules and calculations
- 🏢 **Multi-Tenant SaaS** - Complete isolation with shared codebase
- 👥 **Universal CRM** - Customer management for any industry
- 📋 **Project Management** - Customizable workflow stages
- 📅 **Calendar/Scheduling** - Appointments and installations
- 💳 **Payments** - Stripe integration for deposits and invoices
- 🌐 **Client Portal** - Customer-facing project views
- 🎨 **White-Label** - Custom branding per tenant

### Industry Templates
Each industry template includes:
- Custom pricing methods (per-width, per-hour, per-sqft, per-item)
- Industry-specific catalogs and materials
- Tailored AI conversation prompts
- Customized workflow stages
- Specialized features (production queue, permit tracking, etc.)

## 🏗️ Architecture

### Backend (`contractorforge_backend/`)
- **FastAPI** - Modern async Python web framework
- **SQLAlchemy 2.0** - Async ORM with PostgreSQL
- **Alembic** - Database migrations
- **OpenAI GPT-4** - AI conversation engine
- **OpenCV** - Photo measurement processing
- **Stripe** - Payment processing
- **Celery** - Background task processing

### Frontend (`contractorforge_web/`)
- **Next.js 15** - React framework with App Router
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first styling
- **shadcn/ui** - Beautiful component library
- **Framer Motion** - Smooth animations

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Redis (for Celery)

### Backend Setup

```bash
cd contractorforge_backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys and database URL

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload
```

Backend will run at http://localhost:8000

### Frontend Setup

```bash
cd contractorforge_web

# Install dependencies
npm install

# Create environment file
echo "NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1" > .env.local

# Start development server
npm run dev
```

Frontend will run at http://localhost:3001

## 📚 Documentation

- **[SETUP.md](docs/SETUP.md)** - Detailed installation and configuration
- **[INDUSTRY_TEMPLATES.md](docs/INDUSTRY_TEMPLATES.md)** - How to create new industry templates
- **[API.md](docs/API.md)** - Complete API documentation
- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Production deployment guide

## 🎨 Industry Templates

### LuxeForge - Custom Workrooms
Perfect for drapery makers and soft furnishing businesses.

**Pricing:**
- $95-150 per width (drapery)
- $15-20 per sqft (roman shades)
- 30-50% fabric markup
- 50% hardware markup

**Features:**
- Production queue management
- Fabric catalog (Rowley Co, Kravet, Greenhouse)
- COM (Customer's Own Material) workflow
- Sample management

### ElectricForge - Electricians
Designed for electrical contractors and service calls.

**Pricing:**
- $55-125 hourly rates (by skill level)
- Per-fixture pricing ($100-2800)
- 30% materials markup
- 1.5x emergency multiplier

**Features:**
- Permit tracking
- Inspection checklists
- Crew dispatch management
- Emergency service scheduling

### LandscapeForge - Landscaping
Built for landscape design and installation.

**Pricing:**
- Per sqft (patio $15, sod $0.80)
- Per plant ($15-800 based on type)
- 40% materials markup
- Design fees

**Features:**
- Plant library with care instructions
- Seasonal scheduling
- Design mockups
- Area-based estimating

## 🔑 Core Concepts

### Multi-Tenancy
Each business (tenant) has complete data isolation while sharing the same codebase. Tenants can:
- Choose their industry template
- Customize pricing rules
- Apply white-label branding
- Manage their own team and customers

### Industry Templates
Templates are Python classes that implement the `IndustryTemplate` interface:

```python
class MyIndustryTemplate(IndustryTemplate):
    @property
    def industry_code(self) -> str:
        return "my_industry"
    
    def calculate_estimate(self, project_data: Dict) -> Dict:
        # Custom pricing logic
        pass
```

### AI Conversational Intake
The AI service adapts conversation based on industry:
- Asks relevant questions for each industry
- Extracts structured data from natural language
- Determines when enough info is collected
- Generates estimates automatically

### Photo Measurements
The measurement service can:
- Detect reference objects (credit card, dollar bill)
- Calculate pixels-per-inch scale
- Measure target objects
- Return confidence scores

## 💳 Pricing Plans

| Plan | Price | Projects | Team Members | Features |
|------|-------|----------|--------------|----------|
| **Solo** | $79/mo | 50/month | 1 | Core features |
| **Pro** | $249/mo | Unlimited | 5 | + Production queue, API |
| **Enterprise** | $599/mo | Unlimited | Unlimited | + White-label, SLA |

All plans include:
- AI conversational intake
- Photo measurements
- Auto-quote generation
- CRM & calendar
- Stripe payments
- Client portal

## 🧪 Testing

```bash
# Backend tests
cd contractorforge_backend
pytest

# Frontend tests
cd contractorforge_web
npm test
```

## 📦 Deployment

### Option 1: Docker Compose

```bash
docker-compose up -d
```

### Option 2: Cloud Platforms

**Backend:**
- Deploy to Railway, Render, or Heroku
- Set environment variables
- Connect PostgreSQL database

**Frontend:**
- Deploy to Vercel or Netlify
- Set `NEXT_PUBLIC_API_URL` environment variable

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed instructions.

## 🔐 Security

- ✅ JWT authentication
- ✅ Multi-tenant data isolation
- ✅ SQL injection protection (SQLAlchemy)
- ✅ XSS protection (React escaping)
- ✅ HTTPS enforcement
- ✅ API rate limiting
- ✅ Input validation (Pydantic)

## 🤝 Contributing

This is a proprietary platform. For support or custom development:
- Email: support@contractorforge.com
- Website: https://contractorforge.com

## 📄 License

Proprietary © 2026 ContractorForge. All rights reserved.

## 🎯 Roadmap

### Phase 1 ✅ (Current)
- [x] Core platform architecture
- [x] Three industry templates
- [x] AI conversational intake
- [x] Photo measurements
- [x] Multi-tenant SaaS

### Phase 2 🚧 (Q2 2026)
- [ ] 3D scanning integration (Polycam)
- [ ] Mobile apps (iOS/Android)
- [ ] Workflow automation
- [ ] Advanced analytics
- [ ] Integration marketplace

### Phase 3 📋 (Q3 2026)
- [ ] 10+ industry templates
- [ ] Team collaboration tools
- [ ] API marketplace
- [ ] Multi-language support
- [ ] Enterprise SSO

## 🌟 Why ContractorForge?

**Built for Scale:** From solo contractors to $100M+ enterprises

**AI-First:** GPT-4 powered conversations that convert browsers to customers

**Industry-Agnostic:** One platform, infinite industries

**Modern Stack:** Latest technologies (Next.js 15, FastAPI, PostgreSQL)

**Complete Solution:** From lead to invoice, everything in one place

---

**Built with ❤️ for service businesses worldwide.**
