# EmpireBox Website - URLs & Hosting Information

## Domain Information

### Primary Domain
- **Domain**: empirebox.com
- **Status**: To be registered
- **Registrar**: Namecheap / Google Domains / Cloudflare
- **DNS Provider**: Cloudflare (recommended)
- **SSL Certificate**: Let's Encrypt (free) or Cloudflare SSL

### Domain Setup Steps
1. Register domain at your preferred registrar
2. Point nameservers to Cloudflare
3. Add A/CNAME records for hosting
4. Enable SSL (Always Use HTTPS)
5. Set up www redirect (www → non-www or vice versa)

### DNS Records (Example)
```
Type    Name    Content              TTL
A       @       76.76.21.21          Auto
CNAME   www     empirebox.com        Auto
TXT     @       (verification codes)  Auto
```

## Hosting Options

### Option 1: Vercel (Recommended for Next.js)
- **URL**: vercel.com
- **Cost**: Free tier available
- **Features**:
  - Automatic deployments from Git
  - Global CDN
  - Automatic SSL
  - Serverless functions
  - Analytics
  - Preview deployments
- **Setup**:
  1. Connect GitHub repo
  2. Vercel auto-detects Next.js
  3. Click Deploy
  4. Add custom domain in settings

### Option 2: Netlify (Alternative)
- **URL**: netlify.com
- **Cost**: Free tier available
- **Features**:
  - Git integration
  - Form handling
  - CDN
  - SSL
  - Split testing
- **Setup**:
  1. Connect GitHub repo
  2. Set build command: `npm run build`
  3. Set publish directory: `.next`
  4. Deploy

### Option 3: Cloudflare Pages (Budget-Friendly)
- **URL**: pages.cloudflare.com
- **Cost**: Free
- **Features**:
  - Global edge network
  - Unlimited bandwidth
  - SSL included
  - GitHub integration
- **Setup**: Similar to Vercel/Netlify

### Option 4: AWS (Advanced)
- **Services**: S3 + CloudFront + Route 53
- **Cost**: Pay-as-you-go (~$1-5/month for small site)
- **Complexity**: Higher, but more control

### Option 5: Framer Hosting (For Framer Build)
- **URL**: framer.com
- **Cost**: Free tier available
- **Features**:
  - Built-in CMS
  - No code deployments
  - Custom domain support
  - Automatic SSL
- **Custom Domain**: empirebox.com → Framer site

## Static HTML Hosting

For the static HTML version (`website/static/index.html`):

### Option 1: GitHub Pages
- **Cost**: Free
- **URL**: https://r22gir.github.io/Empire/website/static/
- **Setup**:
  1. Enable GitHub Pages in repo settings
  2. Select branch and folder
  3. Access at username.github.io/repo

### Option 2: Netlify Drop
- **URL**: app.netlify.com/drop
- **Cost**: Free
- **Setup**: Drag and drop HTML file

### Option 3: Surge.sh
- **Cost**: Free
- **Setup**:
  ```bash
  npm install -g surge
  cd website/static
  surge
  ```

## Email Setup

### Email Address: hello@empirebox.com

### Option 1: Google Workspace
- **Cost**: $6/user/month
- **Features**: Gmail interface, Calendar, Drive, Meet
- **Setup**: Add MX records to DNS

### Option 2: Zoho Mail
- **Cost**: Free (up to 5 users)
- **Features**: Email, Calendar, Docs
- **Setup**: Add MX records to DNS

### Option 3: Forward to Personal Email
- **Cost**: Free
- **Setup**: Use Cloudflare Email Routing or domain registrar forwarding

### Email Service Provider (ESP) for Marketing

For sending welcome emails and newsletters:

#### Option 1: ConvertKit
- **Cost**: Free up to 1,000 subscribers
- **Features**: Landing pages, automation, forms
- **Use Case**: Email marketing, welcome sequences

#### Option 2: Mailchimp
- **Cost**: Free up to 500 subscribers
- **Features**: Templates, automation, analytics

#### Option 3: SendGrid
- **Cost**: Free up to 100 emails/day
- **Features**: API-based, transactional emails
- **Use Case**: Form submissions, notifications

## Form Submission Endpoints

### Email Form Backend Options

#### Option 1: Formspree
- **URL**: formspree.io
- **Cost**: Free tier available
- **Setup**:
  ```html
  <form action="https://formspree.io/f/YOUR_ID" method="POST">
    <input type="email" name="email">
    <button type="submit">Submit</button>
  </form>
  ```

#### Option 2: Netlify Forms
- **Cost**: Free (100 submissions/month)
- **Setup**: Add `data-netlify="true"` to form

#### Option 3: Custom API
- **Setup**: Create serverless function (Vercel/Netlify)
- **Integration**: Send to ESP (ConvertKit, Mailchimp)

## Analytics Setup

### Google Analytics 4
- **URL**: analytics.google.com
- **Setup**:
  1. Create GA4 property
  2. Get Measurement ID (G-XXXXXXXXXX)
  3. Add to website:
     ```html
     <script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
     ```

### Alternative: Plausible Analytics
- **URL**: plausible.io
- **Cost**: $9/month
- **Features**: Privacy-friendly, simple, lightweight

## Social Media Handles

### Recommended Handles
- **Twitter**: @EmpireBoxHQ or @EmpireBox
- **Instagram**: @empirebox
- **LinkedIn**: /company/empirebox
- **Facebook**: /EmpireBoxOfficial
- **TikTok**: @empirebox
- **YouTube**: EmpireBox

### Social Media Links
Add to footer once accounts are created:
- Twitter: https://twitter.com/EmpireBoxHQ
- Instagram: https://instagram.com/empirebox
- LinkedIn: https://linkedin.com/company/empirebox

## API Keys & Environment Variables

### Next.js Environment Variables

Create `.env.local` file:
```
# Analytics
NEXT_PUBLIC_GA_ID=G-XXXXXXXXXX

# Email
CONVERTKIT_API_KEY=your_api_key
CONVERTKIT_FORM_ID=your_form_id

# Other services
NEXT_PUBLIC_API_URL=https://api.empirebox.com
```

**Security Note**: Never commit `.env.local` to Git. Use `.env.example` for documentation.

## CDN & Performance

### Cloudflare (Recommended)
- **URL**: cloudflare.com
- **Cost**: Free tier available
- **Features**:
  - Global CDN
  - DDoS protection
  - SSL/TLS
  - Caching
  - Analytics
  - Email routing

### Setup Steps
1. Sign up for Cloudflare
2. Add empirebox.com
3. Update nameservers at registrar
4. Enable Orange Cloud (proxy)
5. Configure SSL (Full/Strict)
6. Set up Page Rules for caching

## Monitoring & Uptime

### Uptime Monitoring
- **UptimeRobot**: Free, checks every 5 minutes
- **Pingdom**: Paid, more detailed
- **StatusPage**: Public status page for users

## Deployment Workflow

### Recommended: Vercel + GitHub

1. **Development**:
   ```bash
   git checkout -b feature/new-feature
   # Make changes
   git commit -m "Add new feature"
   git push origin feature/new-feature
   ```

2. **Preview**: Vercel creates preview URL for PR

3. **Production**:
   ```bash
   git checkout main
   git merge feature/new-feature
   git push origin main
   ```
   Vercel auto-deploys to production

## Custom Domain Setup (Vercel)

1. Go to Vercel project settings
2. Add domain: empirebox.com
3. Add A records to DNS:
   ```
   A    @    76.76.21.21
   ```
4. Wait for DNS propagation (up to 48 hours)
5. Vercel automatically provisions SSL

## Backup & Version Control

### GitHub Repository
- **URL**: github.com/r22gir/Empire
- **Branch Strategy**:
  - `main`: Production
  - `develop`: Development
  - `feature/*`: Feature branches

### Automated Backups
- Code: GitHub (automatic)
- Database: (when added) Daily backups
- Media: S3/Cloudflare R2

## Support & Documentation

### Internal Documentation
- This file: Website URLs and hosting
- `WEBSITE_COMPLETE_PACKAGE.md`: Content and design
- `FRAMER_BUILD_CHECKLIST.md`: Build instructions
- Next.js `README.md`: Development guide

### External Resources
- Vercel Docs: vercel.com/docs
- Next.js Docs: nextjs.org/docs
- Tailwind CSS: tailwindcss.com/docs
- Framer: framer.com/docs

## Quick Reference

### Important URLs
- **Live Site**: https://empirebox.com (to be deployed)
- **Staging**: https://empirebox-staging.vercel.app
- **GitHub**: https://github.com/r22gir/Empire
- **Vercel Dashboard**: https://vercel.com/dashboard

### Login Credentials
Store securely in password manager:
- Vercel account
- Domain registrar
- Cloudflare account
- Email service
- Analytics account
- Social media accounts

### Contact Information
- **Technical Support**: hello@empirebox.com
- **Hosting Issues**: Vercel support (if on Vercel)
- **DNS Issues**: Cloudflare support

## Next Steps

- [ ] Register empirebox.com domain
- [ ] Set up Cloudflare DNS
- [ ] Deploy to Vercel
- [ ] Configure custom domain
- [ ] Set up email (hello@empirebox.com)
- [ ] Add Google Analytics
- [ ] Configure email capture (ConvertKit/Mailchimp)
- [ ] Create social media accounts
- [ ] Set up uptime monitoring
- [ ] Test all functionality
- [ ] Go live! 🚀
