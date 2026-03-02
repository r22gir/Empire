# AMP - Actitud Mental Positiva — Build Prompt

**Date:** February 26, 2026
**Domain:** www.actitudmentalpositiva.com
**Language:** Spanish (primary), English (secondary)
**Status:** Existing project in ~/Empire, needs revival

---

## Business Model — Hybrid of Mindvalley + PuraMente

### Mindvalley Influence (Premium Courses/Quests)
- Multi-week "Quests" (programs) with daily 15-20 min lessons
- Expert-led video courses on personal development
- Community features, live events, certifications
- Membership model: unlimited access to all content
- High production value, premium positioning
- Business/entrepreneurship + personal growth

### PuraMente Influence (Accessible Wellness App)
- Freemium model: free basic content, premium subscription
- 300+ guided meditations/sessions in Spanish
- Live coaching sessions with certified guides
- Daily mood tracking and personalized recommendations
- WhatsApp community groups for engagement
- Pricing: ~$2.99/month, $29.99/year, $89.99 lifetime
- 4M+ downloads, #1 Spanish meditation app
- B2B plans for companies (team wellness)

### John Maxwell Influence (Leadership Content)
- Leadership development principles (21 Laws of Leadership)
- Character-based growth and personal responsibility
- Mentoring/coaching framework
- "Actitud Mental Positiva" = Positive Mental Attitude (Napoleon Hill/W. Clement Stone classic concept)
- Daily leadership and mindset content

---

## AMP Hybrid Model

| Feature | Source Inspiration | AMP Implementation |
|---------|-------------------|-------------------|
| Daily lessons (15-20 min) | Mindvalley Quests | "Retos AMP" — 21-day challenges |
| Guided meditations | PuraMente | Mindfulness + affirmation sessions |
| Leadership content | John Maxwell | Weekly leadership masterclass |
| Community | Both | WhatsApp groups + in-app community |
| Freemium + Premium | PuraMente | Free daily content, premium library |
| Certifications | Mindvalley | "Coach AMP" certification program |
| B2B/Corporate | Both | Workplace wellness + leadership training |
| Live events | Mindvalley | Monthly webinars, annual summit |

### Pricing Tiers
- **Free:** Daily affirmation, 1 meditation/day, community access
- **AMP Premium:** $4.99/month or $39.99/year — Full library, all challenges, live sessions
- **AMP Pro:** $14.99/month — Premium + 1:1 coaching sessions, certification track
- **AMP Empresas (B2B):** Custom pricing — Team wellness, leadership training, analytics

---

## Landing Page — actitudmentalpositiva.com

### Design Direction
- Clean, modern, inspirational
- Colors: Deep navy (#1a1a2e), gold (#D4AF37), white, soft gradients
- Typography: Premium serif for headings, clean sans-serif for body
- Hero section with video background or animated gradient
- Spanish first, English toggle option
- Mobile-first responsive design

### Page Sections

#### 1. Hero Section
```
"Transforma Tu Mente. Transforma Tu Vida."
Subtitle: "La plataforma #1 en español para desarrollo personal, liderazgo y bienestar mental"
[CTA: "Empieza Gratis" button — gold]
[CTA: "Ver Demo" button — outline]
Background: Gradient animation or inspirational video loop
```

#### 2. Social Proof Bar
```
"Únete a +10,000 personas transformando su vida"
Logos/badges: App Store rating, testimonials count, countries
```

#### 3. "¿Qué es AMP?" — What is AMP Section
```
AMP = Actitud Mental Positiva
Three pillars with icons:
🧠 Mentalidad — Daily mindset training and affirmations
🧘 Bienestar — Guided meditations and stress management  
👑 Liderazgo — Leadership principles inspired by John Maxwell
```

#### 4. Features Showcase
```
- "Retos de 21 Días" — Structured challenges for habit formation
- "Meditaciones Guiadas" — 100+ sessions from certified guides
- "Masterclass de Liderazgo" — Weekly video lessons
- "Comunidad AMP" — WhatsApp groups and live events
- "Coach AMP" — Path to becoming a certified coach
- "AMP Empresas" — Corporate wellness solutions
```

#### 5. How It Works
```
Step 1: Descarga la app o accede desde la web
Step 2: Elige tu reto de 21 días
Step 3: Practica 15 minutos al día
Step 4: Conecta con la comunidad
Step 5: Transforma tu vida
```

#### 6. Pricing Section
```
Three cards: Free / Premium / Pro
With feature comparison table
Annual savings highlighted
"AMP Empresas" link for B2B
```

#### 7. Testimonials
```
Video testimonials or quote cards
Real transformation stories
Before/after mindset shifts
```

#### 8. John Maxwell Section
```
"Inspirado en los principios de John Maxwell"
Quote: "El liderazgo comienza contigo mismo"
Brief connection to Maxwell's philosophy
Featured leadership content preview
```

#### 9. Newsletter / Lead Capture
```
"Recibe tu dosis diaria de AMP"
Email signup for daily affirmation
Free 7-day challenge as lead magnet
```

#### 10. Footer
```
Links: Sobre Nosotros, Blog, Contacto, Términos, Privacidad
Social: Instagram, YouTube, TikTok, Facebook
App Store / Google Play badges
© 2026 AMP — Actitud Mental Positiva
```

---

## Technical Implementation

### Option A: Static Landing Page (Fast Launch)
- Next.js static page in ~/Empire/amp/
- Tailwind CSS for styling
- Deployed to actitudmentalpositiva.com
- Lead capture form → email list (Mailchimp/ConvertKit)
- Port 3003 for local dev

### Option B: Full Platform (Phase 2)
- User auth (signup/login)
- Content library with video player
- Meditation audio player
- Challenge tracking (21-day streaks)
- Community feed
- Payment integration (Stripe)
- Admin dashboard for content management

---

## Claude Code Prompt — Phase 1 (Landing Page)

```
Build the AMP (Actitud Mental Positiva) landing page at ~/Empire/amp/

Create a Next.js 14 app with Tailwind CSS. Port 3003.

The site is a Spanish-language personal development platform inspired by Mindvalley + PuraMente + John Maxwell.

Design: Dark navy (#1a1a2e) and gold (#D4AF37) theme, premium feel, modern.
Language: Spanish primary.

Build these sections:
1. Hero: "Transforma Tu Mente. Transforma Tu Vida." with gradient background, two CTAs
2. Social proof bar with stats
3. Three pillars: Mentalidad, Bienestar, Liderazgo with icons
4. Features showcase (6 features with icons and descriptions)
5. How it works (5 steps)
6. Pricing (Free/Premium/Pro cards)
7. Testimonials (3 cards)
8. John Maxwell inspired section
9. Email signup / lead capture
10. Footer with social links

Make it responsive, mobile-first, animated on scroll.
Domain: actitudmentalpositiva.com
Add to the Empire Switchboard as a new service.

Commit and push when done.
```

---

## Content Strategy (Post-Launch)

### Daily Content
- Morning affirmation (free)
- Daily leadership tip (free)
- Guided meditation (1 free, rest premium)

### Weekly Content
- Leadership masterclass video (premium)
- Community live session (premium)
- Blog post for SEO

### Monthly Content
- New 21-day challenge
- Expert guest webinar
- Newsletter with highlights

### Social Media (Marketing Desk handles this)
- Instagram: Daily quotes, Reels with tips
- TikTok: Short mindset clips
- YouTube: Weekly masterclass clips
- Facebook: Community group
- Pinterest: Quote graphics, infographics

---

## Revenue Projections

| Month | Free Users | Premium | Pro | B2B | MRR |
|-------|-----------|---------|-----|-----|-----|
| 1-3 | 500 | 25 | 5 | 0 | $200 |
| 4-6 | 2,000 | 100 | 20 | 1 | $1,200 |
| 7-12 | 10,000 | 500 | 50 | 5 | $5,000 |
| Year 2 | 50,000 | 2,500 | 200 | 20 | $25,000 |

---

## References
- Mindvalley: mindvalley.com — Course structure, community, certifications
- PuraMente: puramente.app — Freemium model, Spanish content, meditation
- John Maxwell: johnmaxwell.com — Leadership principles, content inspiration
- Napoleon Hill: "Think and Grow Rich" — Original AMP/PMA concept
