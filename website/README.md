# EmpireBox Website

Complete marketing website for EmpireBox - The Operating System for Resellers.

## Overview

This directory contains two versions of the EmpireBox marketing website:

1. **Static HTML** (`/static`) - Single-file HTML version for reference and Framer builds
2. **Next.js** (`/nextjs`) - Production-ready modern web application
3. **Documentation** (`/docs`) - Complete website documentation and guides

## Project Structure

```
website/
├── static/                          # Static HTML version
│   └── index.html                   # Complete single-file website
│
├── nextjs/                          # Next.js production version
│   ├── src/
│   │   ├── app/                     # Pages (home, about, pricing, faq)
│   │   ├── components/              # React components
│   │   └── lib/                     # Constants and utilities
│   ├── public/                      # Static assets
│   ├── package.json
│   ├── tailwind.config.js
│   └── README.md                    # Next.js setup instructions
│
└── docs/                            # Documentation
    ├── WEBSITE_COMPLETE_PACKAGE.md  # Complete website specs
    ├── FRAMER_BUILD_CHECKLIST.md    # Framer build guide
    └── WEBSITE_URLS.md               # Hosting & domain info
```

## Quick Start

### View Static HTML Version

Simply open `static/index.html` in your browser:

```bash
open website/static/index.html
```

Or use a local server:

```bash
cd website/static
python -m http.server 8000
# Visit http://localhost:8000
```

### Run Next.js Version

```bash
cd website/nextjs
npm install
npm run dev
# Visit http://localhost:3000
```

See `nextjs/README.md` for detailed setup instructions.

## Features

### Landing Page Sections
- ✅ Sticky Navigation with mobile menu
- ✅ Hero section with gradient and CTA
- ✅ 3 Feature cards (MarketForge, MarketF, AI Agents)
- ✅ 4 Testimonials with stats bar
- ✅ How It Works (3 steps)
- ✅ 4 Pricing tiers (with featured card)
- ✅ FAQ accordion (6 questions)
- ✅ CTA section with email capture
- ✅ Footer with links

### Additional Pages
- ✅ About page
- ✅ Pricing page
- ✅ FAQ page

### Technical Features
- ✅ Fully responsive (mobile, tablet, desktop)
- ✅ SEO optimized with meta tags
- ✅ Smooth scroll navigation
- ✅ Animations with Framer Motion
- ✅ Email form validation
- ✅ TypeScript for type safety
- ✅ Tailwind CSS for styling

## Design Specs

### Color Scheme
- **Primary Blue**: #0066FF
- **Secondary Orange**: #FF6600
- **Dark**: #1A1A1A
- **Light**: #F9F9F9

### Typography
- **Headlines**: Montserrat (Bold)
- **Body**: Inter (Regular)

### Key Metrics
- Load Time: < 2 seconds
- Mobile-first responsive design
- Accessibility: WCAG 2.1 AA compliant

## Documentation

### For Developers
- `nextjs/README.md` - Development setup and deployment
- `docs/WEBSITE_COMPLETE_PACKAGE.md` - Complete website specifications

### For Designers
- `docs/FRAMER_BUILD_CHECKLIST.md` - Step-by-step Framer build guide
- `static/index.html` - Reference implementation

### For DevOps
- `docs/WEBSITE_URLS.md` - Hosting, domains, and infrastructure

## Deployment

### Next.js (Production)

**Vercel (Recommended)**:
```bash
cd website/nextjs
npm install -g vercel
vercel
```

See `nextjs/README.md` for other deployment options (Netlify, Cloudflare Pages, AWS).

### Static HTML

Deploy to any static host:
- GitHub Pages
- Netlify Drop
- Surge.sh
- S3 + CloudFront

## Development Workflow

1. **Edit Components**: Modify files in `nextjs/src/components/`
2. **Update Content**: Edit `nextjs/src/lib/constants.ts`
3. **Test Locally**: `npm run dev`
4. **Build**: `npm run build`
5. **Deploy**: Push to main branch (auto-deploy on Vercel)

## Content Updates

### Pricing Changes
Edit `nextjs/src/lib/constants.ts`:
```typescript
export const PRICING_TIERS = [
  // Update pricing info here
];
```

### FAQ Updates
Edit `nextjs/src/lib/constants.ts`:
```typescript
export const FAQ_DATA = [
  // Add/edit questions here
];
```

### Testimonials
Edit `nextjs/src/lib/constants.ts`:
```typescript
export const TESTIMONIALS = [
  // Add/edit testimonials here
];
```

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)
- Mobile browsers (iOS Safari, Android Chrome)

## Performance

- Lighthouse Score: 90+
- First Contentful Paint: < 1.5s
- Time to Interactive: < 3s
- Total Bundle Size: < 500KB

## Accessibility

- Semantic HTML
- ARIA labels
- Keyboard navigation
- Color contrast 4.5:1+
- Screen reader friendly

## Testing

### Manual Testing Checklist
- [ ] Navigation links work
- [ ] Mobile menu toggles
- [ ] FAQ accordion expands/collapses
- [ ] Email form validates
- [ ] CTA buttons navigate correctly
- [ ] All sections visible on mobile
- [ ] Smooth scrolling works
- [ ] Hover effects work

### Browser Testing
- [ ] Chrome desktop
- [ ] Firefox desktop
- [ ] Safari desktop
- [ ] iOS Safari
- [ ] Android Chrome

## Maintenance

### Regular Updates
- Content: Monthly
- Dependencies: Quarterly
- Security patches: As needed

### Monitoring
- Set up Google Analytics
- Monitor Core Web Vitals
- Track conversion rates
- Monitor uptime (UptimeRobot)

## Contact

For questions or issues:
- **Email**: hello@empirebox.com
- **GitHub**: https://github.com/r22gir/Empire

## License

Proprietary - EmpireBox © 2026

---

**Ready to launch?** Follow the deployment guide in `nextjs/README.md` or `docs/WEBSITE_URLS.md`.
