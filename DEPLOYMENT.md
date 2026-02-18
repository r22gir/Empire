# MarketForge Deployment Guide

This guide provides step-by-step instructions for deploying MarketForge's components: the Flutter web app, marketing website, and backend API.

## 🚀 Quick Deploy (One-Click)

### Deploy Flutter App to Vercel
[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/r22gir/Empire&project-name=marketforge-app&root-directory=market_forge_app)

### Deploy Website to Vercel
[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/r22gir/Empire&project-name=marketforge-website&root-directory=website/nextjs)

### Deploy Backend to Railway
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/r22gir/Empire&plugins=postgresql&envs=DATABASE_URL,JWT_SECRET,CORS_ORIGINS&root-directory=backend)

---

## 📋 Prerequisites

Before deploying, ensure you have:

1. **GitHub Account** - For repository access and CI/CD
2. **Vercel Account** - For frontend deployments (free tier available)
3. **Railway Account** - For backend deployment (free trial available)
4. **Domain Names** (optional) - For custom domains

---

## 🔧 Environment Variables

### Backend (Railway)

Required environment variables for the backend:

```bash
# Database
DATABASE_URL=postgresql://user:password@host:port/database

# Authentication
JWT_SECRET=your-super-secret-jwt-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
CORS_ORIGINS=["https://your-app.vercel.app","https://your-website.vercel.app"]

# API Keys (Optional - for marketplace integrations)
FACEBOOK_APP_ID=your-facebook-app-id
FACEBOOK_APP_SECRET=your-facebook-app-secret
EBAY_APP_ID=your-ebay-app-id
EBAY_CERT_ID=your-ebay-cert-id
```

### Flutter App (Vercel)

No environment variables required for build. API endpoint is configured in `market_forge_app/lib/config/app_config.dart`.

### Website (Vercel)

No environment variables required for static Next.js deployment.

---

## 📦 Manual Deployment Instructions

### 1. Deploy Flutter Web App to Vercel

#### Option A: Using Vercel CLI

```bash
# Install Vercel CLI
npm install -g vercel

# Navigate to the Flutter app directory
cd market_forge_app

# Deploy
vercel --prod
```

#### Option B: Using Vercel Dashboard

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Click "Add New Project"
3. Import your GitHub repository
4. Configure:
   - **Framework Preset**: Other
   - **Root Directory**: `market_forge_app`
   - **Build Command**: `flutter build web`
   - **Output Directory**: `build/web`
   - **Install Command**: `git clone https://github.com/aspect-build/aspect-workflows.git && ./aspect-workflows/flutter/setup.sh`
5. Click "Deploy"

**Note**: Flutter requires custom build setup. The install command sets up Flutter in the Vercel build environment.

### 2. Deploy Marketing Website to Vercel

#### Option A: Using Vercel CLI

```bash
# Install Vercel CLI
npm install -g vercel

# Navigate to the Next.js directory
cd website/nextjs

# Install dependencies
npm install

# Build locally to test
npm run build

# Deploy
vercel --prod
```

#### Option B: Using Vercel Dashboard

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Click "Add New Project"
3. Import your GitHub repository
4. Configure:
   - **Framework Preset**: Next.js
   - **Root Directory**: `website/nextjs`
   - **Build Command**: `npm run build`
   - **Output Directory**: `.next`
5. Click "Deploy"

Vercel will auto-detect Next.js and configure appropriately.

### 3. Deploy Backend to Railway

#### Option A: Using Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Navigate to backend directory
cd backend

# Initialize Railway project (first time only)
railway init

# Add PostgreSQL database
railway add postgresql

# Set environment variables
railway variables set JWT_SECRET="your-secret-key"
railway variables set CORS_ORIGINS='["https://your-app.vercel.app"]'

# Deploy
railway up
```

#### Option B: Using Railway Dashboard

1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your repository
5. Configure:
   - **Root Directory**: `backend`
   - **Build Command**: Auto-detected by Nixpacks
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Add PostgreSQL plugin:
   - Click "New" → "Database" → "PostgreSQL"
   - Railway will automatically set `DATABASE_URL`
7. Add environment variables (see section above)
8. Click "Deploy"

---

## 🔄 Automated CI/CD with GitHub Actions

The repository includes a GitHub Actions workflow that automatically deploys on push to `main` branch.

### Setup GitHub Secrets

Add these secrets to your GitHub repository (Settings → Secrets and variables → Actions):

#### For Vercel Deployments

```
VERCEL_TOKEN=<your-vercel-token>
VERCEL_ORG_ID=<your-org-id>
VERCEL_PROJECT_ID=<app-project-id>
VERCEL_WEBSITE_PROJECT_ID=<website-project-id>
```

**To get these values:**

1. Go to [Vercel Account Settings](https://vercel.com/account/tokens)
2. Create a new token (save as `VERCEL_TOKEN`)
3. Go to your project Settings → General
4. Copy "Project ID" (save as `VERCEL_PROJECT_ID`)
5. Copy "Organization ID" from your account settings (save as `VERCEL_ORG_ID`)

#### For Railway Deployment

```
RAILWAY_TOKEN=<your-railway-token>
```

**To get this value:**

1. Go to [Railway Account Settings](https://railway.app/account/tokens)
2. Create a new token
3. Copy and save as `RAILWAY_TOKEN`

### Workflow Features

The GitHub Actions workflow (`.github/workflows/deploy.yml`) will:

1. ✅ Build Flutter web app on every push to `main`
2. ✅ Deploy Flutter app to Vercel (if `VERCEL_TOKEN` is set)
3. ✅ Deploy website to Vercel (if `VERCEL_TOKEN` is set)
4. ✅ Deploy backend to Railway (if `RAILWAY_TOKEN` is set)

Jobs run in parallel where possible for faster deployments.

---

## 🌐 Custom Domains

### Vercel (Flutter App & Website)

1. Go to your project in Vercel Dashboard
2. Navigate to Settings → Domains
3. Add your custom domain (e.g., `app.marketforge.com`)
4. Follow DNS configuration instructions
5. Vercel will automatically provision SSL certificate

**Recommended domains:**
- Flutter App: `app.marketforge.com`
- Website: `marketforge.com` or `www.marketforge.com`

### Railway (Backend)

1. Go to your project in Railway Dashboard
2. Click Settings → Networking
3. Click "Generate Domain" for a free Railway domain
4. Or add custom domain:
   - Click "Custom Domain"
   - Enter your domain (e.g., `api.marketforge.com`)
   - Add CNAME record to your DNS: `CNAME api railway.app`

**Recommended domain:**
- Backend API: `api.marketforge.com`

---

## 🔍 Verifying Deployments

### Flutter App

```bash
# Test the deployed app
curl https://your-app.vercel.app

# Should return the index.html
```

### Website

```bash
# Test the deployed website
curl https://your-website.vercel.app

# Should return Next.js rendered HTML
```

### Backend

```bash
# Test health endpoint
curl https://your-backend.railway.app/health

# Expected response:
# {"status":"healthy","service":"marketforge-backend"}

# Test API docs
open https://your-backend.railway.app/docs
```

---

## 🐛 Troubleshooting

### Flutter Build Fails on Vercel

**Issue**: Build fails with "flutter: command not found"

**Solution**: Ensure the install command in `vercel.json` properly sets up Flutter:
```json
{
  "installCommand": "git clone https://github.com/aspect-build/aspect-workflows.git && ./aspect-workflows/flutter/setup.sh"
}
```

**Alternative**: If the external repository is unavailable, you can:
1. Pre-build the Flutter web app locally: `flutter build web`
2. Deploy the static `build/web` directory directly to Vercel
3. Or use a custom Docker container with Flutter pre-installed

### Backend Health Check Fails

**Issue**: Railway reports unhealthy service

**Solution**: 
1. Check logs in Railway Dashboard
2. Ensure `DATABASE_URL` is set (added PostgreSQL plugin?)
3. Verify `JWT_SECRET` is set
4. Check that `/health` endpoint returns 200

### CORS Errors

**Issue**: Frontend can't reach backend API

**Solution**: Update `CORS_ORIGINS` in backend environment variables:
```bash
CORS_ORIGINS='["https://your-app.vercel.app","https://your-website.vercel.app","http://localhost:3000"]'
```

### Next.js Build Fails

**Issue**: Website deployment fails during build

**Solution**: 
1. Test build locally: `cd website/nextjs && npm run build`
2. Check Node.js version (should be 18+)
3. Ensure all dependencies are in `package.json`

---

## 📊 Monitoring & Logs

### Vercel

- View deployment logs in Vercel Dashboard
- Monitor in real-time during deployments
- Set up monitoring integrations (optional)

### Railway

- View logs in Railway Dashboard
- Filter by severity (info, warning, error)
- Set up log drains to external services (optional)

### GitHub Actions

- View workflow runs in GitHub Actions tab
- Check individual job logs for debugging
- Receive email notifications on failures (configure in Settings)

---

## 🔐 Security Considerations

1. **Never commit secrets** - Always use environment variables
2. **Rotate tokens regularly** - Update GitHub secrets quarterly
3. **Use strong JWT secrets** - Minimum 32 characters, random
4. **Enable HTTPS only** - Disable HTTP in production
5. **Restrict CORS origins** - Only allow your domains
6. **Keep dependencies updated** - Run `npm audit` and `pip check` regularly

---

## 📝 Deployment Checklist

Before going live:

- [ ] All environment variables configured
- [ ] Database migrations run (`alembic upgrade head`)
- [ ] Backend health check passing
- [ ] Flutter app loads successfully
- [ ] Website displays correctly
- [ ] API endpoints respond correctly
- [ ] CORS configured properly
- [ ] Custom domains configured (if applicable)
- [ ] SSL certificates active
- [ ] Monitoring set up
- [ ] Backup strategy in place

---

## 🆘 Support

### Documentation
- [Vercel Documentation](https://vercel.com/docs)
- [Railway Documentation](https://docs.railway.app)
- [Flutter Web Deployment](https://docs.flutter.dev/deployment/web)
- [Next.js Deployment](https://nextjs.org/docs/deployment)

### Get Help
- **Issues**: Open a GitHub issue in this repository
- **Email**: hello@empirebox.com
- **Community**: Join our Discord (link in website)

---

## 📈 Scaling & Performance

### Vercel
- Automatically scales based on traffic
- CDN distribution worldwide
- Edge functions for dynamic content

### Railway
- Vertical scaling: Upgrade RAM/CPU in dashboard
- Horizontal scaling: Add more instances (Pro plan)
- Database: Upgrade PostgreSQL plan as needed

### Optimization Tips
1. Enable Vercel's Image Optimization
2. Use Railway's connection pooling for database
3. Implement caching strategies (Redis)
4. Monitor performance with built-in analytics

---

## 🔄 Update & Rollback

### Vercel
- Every deployment creates a unique URL
- Rollback via Dashboard → Deployments → "Promote to Production"
- Or use CLI: `vercel --prod` to redeploy previous version

### Railway
- Each deployment is versioned
- Rollback via Dashboard → Deployments → "Redeploy"
- Or use CLI: `railway rollback`

---

## 📅 Maintenance

### Regular Tasks
- **Weekly**: Review logs for errors
- **Monthly**: Update dependencies
- **Quarterly**: Rotate secrets and tokens
- **Yearly**: Review and optimize resource usage

### Backup Strategy
- Railway: Automated PostgreSQL backups (daily)
- Application: Git commits serve as version control
- Database: Export backups monthly to S3 or similar

---

**🎉 Congratulations!** Your MarketForge deployment is complete. Visit your live applications and start listing products across multiple marketplaces!

---

*Last updated: 2026-02-18*
