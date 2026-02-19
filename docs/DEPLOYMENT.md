# ContractorForge Deployment Guide

Production deployment instructions for ContractorForge.

## Deployment Options

1. **Docker Compose** (Recommended for self-hosting)
2. **Cloud Platforms** (Railway, Render, Heroku)
3. **Vercel + Supabase** (For Next.js frontend)
4. **AWS/GCP/Azure** (Enterprise)

## Option 1: Docker Compose (Recommended)

### Prerequisites
- Docker 20+
- Docker Compose 2+
- Domain name with DNS configured

### 1. Create docker-compose.yml

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:14-alpine
    environment:
      POSTGRES_USER: contractorforge
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: contractorforge
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - contractorforge

  redis:
    image: redis:7-alpine
    networks:
      - contractorforge

  backend:
    build: ./contractorforge_backend
    environment:
      DATABASE_URL: postgresql+asyncpg://contractorforge:${DB_PASSWORD}@postgres:5432/contractorforge
      REDIS_URL: redis://redis:6379/0
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      STRIPE_SECRET_KEY: ${STRIPE_SECRET_KEY}
      SECRET_KEY: ${SECRET_KEY}
      ENVIRONMENT: production
    depends_on:
      - postgres
      - redis
    networks:
      - contractorforge
    ports:
      - "8000:8000"

  frontend:
    build: ./contractorforge_web
    environment:
      NEXT_PUBLIC_API_URL: https://api.yourdomain.com/api/v1
    ports:
      - "3000:3000"
    networks:
      - contractorforge

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - backend
      - frontend
    networks:
      - contractorforge

volumes:
  postgres_data:

networks:
  contractorforge:
```

### 2. Create .env File

```bash
DB_PASSWORD=your_secure_password
OPENAI_API_KEY=sk-your-key
STRIPE_SECRET_KEY=sk_your-key
SECRET_KEY=$(openssl rand -hex 32)
```

### 3. Deploy

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Run migrations
docker-compose exec backend alembic upgrade head

# Scale services
docker-compose up -d --scale backend=3
```

## Option 2: Cloud Platforms

### Railway (Recommended)

#### Backend Deployment

1. Go to https://railway.app/
2. Click "New Project" > "Deploy from GitHub repo"
3. Select your repository
4. Set root directory to `contractorforge_backend`
5. Add environment variables:
   ```
   DATABASE_URL (auto-provided by PostgreSQL plugin)
   REDIS_URL (auto-provided by Redis plugin)
   OPENAI_API_KEY
   STRIPE_SECRET_KEY
   SECRET_KEY
   ```
6. Add PostgreSQL and Redis plugins
7. Deploy!

#### Frontend Deployment

1. New service in same project
2. Set root directory to `contractorforge_web`
3. Add environment variable:
   ```
   NEXT_PUBLIC_API_URL=https://your-backend.railway.app/api/v1
   ```
4. Deploy!

### Vercel (Frontend Only)

```bash
cd contractorforge_web
vercel

# Set environment variable
vercel env add NEXT_PUBLIC_API_URL production
```

### Heroku

```bash
# Backend
cd contractorforge_backend
heroku create contractorforge-api
heroku addons:create heroku-postgresql:hobby-dev
heroku addons:create heroku-redis:hobby-dev
heroku config:set OPENAI_API_KEY=sk-your-key
git push heroku main

# Frontend
cd contractorforge_web
heroku create contractorforge-web
heroku config:set NEXT_PUBLIC_API_URL=https://contractorforge-api.herokuapp.com/api/v1
git push heroku main
```

## SSL/TLS Configuration

### Using Let's Encrypt (Free)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal
sudo certbot renew --dry-run
```

### Nginx Configuration

```nginx
upstream backend {
    server backend:8000;
}

upstream frontend {
    server frontend:3000;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;

    # Frontend
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Backend API
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Database Backups

### Automated Backups

```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"

docker-compose exec -T postgres pg_dump -U contractorforge contractorforge | gzip > "$BACKUP_DIR/backup_$DATE.sql.gz"

# Keep last 30 days
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +30 -delete
```

Add to crontab:
```bash
0 2 * * * /path/to/backup.sh
```

### Restore from Backup

```bash
gunzip -c backup_20260217_020000.sql.gz | docker-compose exec -T postgres psql -U contractorforge contractorforge
```

## Monitoring

### Health Checks

```yaml
# docker-compose.yml
backend:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

### Logging

Use logging service:
- Datadog
- New Relic
- Sentry (error tracking)
- LogRocket (frontend)

### Uptime Monitoring

Set up with:
- UptimeRobot (free)
- Pingdom
- StatusCake

## Scaling

### Horizontal Scaling

```bash
# Scale backend
docker-compose up -d --scale backend=5

# Load balancer handles distribution
```

### Database Scaling

1. **Read Replicas** - For heavy read workloads
2. **Connection Pooling** - Use PgBouncer
3. **Caching** - Redis for frequently accessed data

### CDN Integration

Use CDN for static assets:
- Cloudflare
- AWS CloudFront
- Fastly

## Environment Variables

### Required Variables

**Backend:**
```bash
DATABASE_URL
OPENAI_API_KEY
STRIPE_SECRET_KEY
STRIPE_PUBLISHABLE_KEY
STRIPE_WEBHOOK_SECRET
SENDGRID_API_KEY
SECRET_KEY
REDIS_URL
```

**Frontend:**
```bash
NEXT_PUBLIC_API_URL
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY
```

## Security Checklist

- [ ] Use HTTPS/TLS everywhere
- [ ] Set strong SECRET_KEY (32+ random bytes)
- [ ] Enable CORS only for your domains
- [ ] Use environment variables (never commit secrets)
- [ ] Enable database SSL connections
- [ ] Set up firewall rules
- [ ] Regular security updates
- [ ] Rate limiting enabled
- [ ] SQL injection protection (using ORM)
- [ ] XSS protection (React escaping)
- [ ] CSRF protection
- [ ] Password hashing (bcrypt)

## Performance Optimization

### Backend
- Use Redis caching
- Enable database query caching
- Optimize database indexes
- Use async/await properly
- Connection pooling

### Frontend
- Next.js SSR/SSG
- Image optimization
- Code splitting
- CDN for static assets
- Lazy loading

## Maintenance

### Update Dependencies

```bash
# Backend
pip list --outdated
pip install -U package_name

# Frontend
npm outdated
npm update
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply in production
docker-compose exec backend alembic upgrade head
```

## Rollback Strategy

1. **Database:** Keep recent backups, test rollback procedures
2. **Code:** Use Git tags for releases, easy revert
3. **Dependencies:** Lock versions in requirements.txt and package-lock.json

## Support

- Issues: https://github.com/r22gir/Empire/issues
- Email: devops@contractorforge.com
- Docs: https://docs.contractorforge.com
