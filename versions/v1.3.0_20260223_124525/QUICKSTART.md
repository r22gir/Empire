# ContractorForge - Quick Start Guide

Get ContractorForge running in **5 minutes** using Docker Compose.

## Prerequisites

- Docker & Docker Compose installed
- Git installed
- OpenAI API key (optional, for AI features)

## Step 1: Clone Repository

```bash
git clone https://github.com/r22gir/Empire.git
cd Empire
```

## Step 2: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your settings (or use defaults for testing)
nano .env
```

**Minimum required for testing:**
```env
DB_PASSWORD=postgres
SECRET_KEY=test-secret-key-change-in-production
ENVIRONMENT=development
```

**For full functionality, add:**
```env
OPENAI_API_KEY=sk-your-key-here
STRIPE_SECRET_KEY=sk_test_your-key
STRIPE_PUBLISHABLE_KEY=pk_test_your-key
```

## Step 3: Start Services

```bash
# Start all services (backend, frontend, database, redis)
docker-compose up -d

# Check status
docker-compose ps
```

## Step 4: Access Application

- **Frontend:** http://localhost:3001
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

## Step 5: Test Industry Templates

Open your browser and visit http://localhost:3001

You should see:
- ✅ Homepage with 3 industry cards
- ✅ LuxeForge (Custom Workrooms)
- ✅ ElectricForge (Electricians)  
- ✅ LandscapeForge (Landscaping)

## Verify Backend

Test the API:

```bash
# Health check
curl http://localhost:8000/health

# List industries
curl http://localhost:8000/api/v1/industries
```

## Test Estimate Calculations

```bash
# Enter backend container
docker-compose exec backend python

# In Python shell:
from app.templates import get_template

template = get_template('workroom')
estimate = template.calculate_estimate({
    'measurements': {'windows': [{'width': 48, 'height': 84, 'treatment_type': 'drapery'}]},
    'options': {'installation_required': True, 'fabric_provided': False, 'fabric_cost_per_yard': 50.0},
    'tax_rate': 0.08
})
print(f"Total: ${estimate['total']:.2f}")
# Should show: Total: $890.14
```

## Common Commands

```bash
# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Restart services
docker-compose restart

# Rebuild after code changes
docker-compose up -d --build

# Run database migrations
docker-compose exec backend alembic upgrade head

# Access database
docker-compose exec postgres psql -U contractorforge -d contractorforge
```

## Manual Setup (Without Docker)

### Backend

```bash
cd contractorforge_backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env

# Setup database
createdb contractorforge
alembic upgrade head

# Start server
uvicorn app.main:app --reload
```

### Frontend

```bash
cd contractorforge_web

# Install dependencies
npm install

# Configure environment
echo "NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1" > .env.local

# Start development server
npm run dev
```

## Troubleshooting

### Port Already in Use

```bash
# Check what's using the port
lsof -i :8000  # Backend
lsof -i :3001  # Frontend

# Change ports in docker-compose.yml if needed
```

### Database Connection Error

```bash
# Ensure PostgreSQL is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Reset database
docker-compose down -v
docker-compose up -d
```

### Frontend Can't Connect to Backend

```bash
# Check backend is running
curl http://localhost:8000/health

# Check environment variable
docker-compose exec frontend env | grep API_URL

# Rebuild frontend if needed
docker-compose up -d --build frontend
```

## Next Steps

1. **Explore the API:**
   - Visit http://localhost:8000/docs for interactive API documentation
   
2. **Try Pricing Page:**
   - Visit http://localhost:3001/pricing to see subscription tiers

3. **Read Documentation:**
   - `docs/SETUP.md` - Detailed setup instructions
   - `docs/INDUSTRY_TEMPLATES.md` - Create new industries
   - `docs/API.md` - API endpoints
   - `docs/DEPLOYMENT.md` - Production deployment

4. **Customize an Industry:**
   - Edit `contractorforge_backend/app/templates/workroom.py`
   - Change pricing, colors, or features
   - Restart backend: `docker-compose restart backend`

5. **Add Your Branding:**
   - Update colors in `contractorforge_web/tailwind.config.js`
   - Edit homepage at `contractorforge_web/src/app/page.tsx`

## Development Workflow

```bash
# Make changes to code
# Auto-reload is enabled for both backend and frontend

# Backend changes (Python):
docker-compose restart backend

# Frontend changes (React/TypeScript):
# Auto-reloads automatically

# Database schema changes:
docker-compose exec backend alembic revision --autogenerate -m "description"
docker-compose exec backend alembic upgrade head
```

## Production Deployment

See `docs/DEPLOYMENT.md` for:
- Railway deployment
- Heroku deployment
- AWS/GCP/Azure deployment
- SSL/TLS setup
- Monitoring and logging

## Get Help

- **Documentation:** Check `/docs` directory
- **Issues:** https://github.com/r22gir/Empire/issues
- **Questions:** Create a GitHub discussion

## Success Checklist

- [ ] Docker services running
- [ ] Frontend accessible at http://localhost:3001
- [ ] Backend API responding at http://localhost:8000
- [ ] Three industry cards displayed on homepage
- [ ] Pricing page showing 3 tiers
- [ ] API docs accessible at http://localhost:8000/docs
- [ ] Industries endpoint returns 3 templates

If all checked ✅ - **You're ready to build!** 🎉
