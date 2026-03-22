# AMP Revamp Plan — "El Portal de la Alegria"

> Actitud Mental Positiva: Spanish-language wellness and personal growth platform.
> A fusion of MindValley (structured courses, audio) and Puramente (daily meditation, mood tracking).
> Spanish-first. Premium wellness aesthetic. Mobile-first, PWA-ready.

---

## Vision

AMP is "El Portal de la Alegria" — a standalone superior platform built from the foundation of actitudmentalpositiva.com. The original website is REFERENCE ONLY; its content has been extracted, amplified, and enhanced into something far more complete.

**Mission:** Motivar e Inspirar a cada persona del mundo para que alcance su maximo potencial.

**Vision:** Ser la plataforma de transformacion personal con mas impacto global en los proximos 10 anos.

---

## Team (Real People — Use in About Page)

| Name | Role | Background |
|------|------|------------|
| **Andrea Silva** | Parent Mentor (0-12 years) | Marketing & International Business. Certifications in Spiritual/Ontological Coaching, NLP, Mindvalley Families, John Maxwell Leadership. |
| **Dericielo Jimenez** | Life Coach for Women | Specializes in trauma recovery, abuse healing, self-esteem. |
| **Lina Valencia Trivino** | Life Coach (Grief & Relationships) | ICF International Master Coach, Industrial Engineer, Master's in Economics. |
| **Juan Diego Giraldo** | Business & Life Coach | Systems Engineer, IT Management & Cybersecurity. |

---

## Content Strategy

### Extract from Original Site

- 11 Values: Confianza, Empatia, Respeto, Compasion, Comprension, Empoderamiento Personal, Optimismo, Crecimiento Continuo, Autenticidad, Gratitud, Amor Propio
- 9 Services offered
- 10 Blog posts (migrate content from HubSpot)
- 3 Pillars (see below)

### Three Pillars

| Pillar | Theme | Color |
|--------|-------|-------|
| Mentalidad | Mindset & mental strength | Gold #D4A030 |
| Bienestar | Wellness & daily practice | Sage #7CB98B |
| Liderazgo | Leadership & purpose | Lavender #9B8EC4 |

### Amplify

| Content Type | Current | Target | Notes |
|-------------|---------|--------|-------|
| Affirmations | 15 | 100+ | Organized by pillar and mood |
| Meditations | 6 | 50+ | With actual audio content |
| Micro-lessons | 3 | 30+ | Daily lesson scripts |
| Courses | 0 | 5 | 15-21 lessons each, structured multi-week programs |
| Team spotlights | 0 | 4 | One per team member |
| Blog posts | 10 | 10+ | Migrated from HubSpot, then new content |

---

## Feature List

### Phase 1 — Core

1. Wire backend to frontend (replace ALL localStorage with API calls)
2. User auth (signup/login/profile) using existing `amp.py` endpoints
3. Mood check-in leading to content recommendation engine (mood maps to pillar, suggests meditation/affirmation/lesson)
4. Audio player component (persistent bottom bar, background play, waveform visualization)
5. Content library database table: `amp_content`
6. Seed database with 50+ meditation scripts, 100+ affirmations, 30+ lesson outlines
7. "El Portal de la Alegria" as primary brand identity throughout

### Phase 2 — Enhanced

8. Course platform: `amp_courses` + `amp_lessons` tables, structured multi-week programs
9. Progress tracking with streaks, badges, completion certificates
10. Post-session reflection ("Como te sientes ahora?")
11. Meditation timer with ambient sounds
12. Push notifications for daily check-in reminders
13. Sharing: share affirmations/meditations via link or WhatsApp

### Phase 3 — Revenue

14. Stripe subscription tiers: Free / Premium ($4.99/mo or $39.99/yr) / Pro ($14.99/mo)
15. Content gating (free samples + premium library)
16. 1-on-1 coaching booking (Pro tier)
17. B2B/Corporate wellness packages

### Phase 4 — Advanced

18. AI-powered content recommendations (MAX integration)
19. Community feed and peer support
20. Video content support
21. Certification program ("Coach AMP")
22. Live events/webinar integration

---

## Design Direction

- **Palette:** Gold `#D4A030`, Sunrise `#FF8C42`, Sage `#7CB98B`, Lavender `#9B8EC4`
- **Fonts:** Playfair Display (headings) + Nunito (body)
- **Aesthetic:** Premium wellness — warm, inviting, NOT a copy of MindValley's dark theme
- **Layout:** Mobile-first, PWA-ready
- **Animations:** Subtle fade-ups, soft transitions
- **Audio player:** Bottom-fixed bar (Spotify-style) with album art, progress, play/pause

---

## Technical Plan

### Infrastructure (Reuses Existing Empire Stack)

| Component | Path / Detail |
|-----------|---------------|
| Frontend | `~/empire-repo/amp/` — Next.js 14, port 3003 (PRIMARY app) |
| Backend | `~/empire-repo/backend/app/routers/amp.py` — FastAPI, already has auth + CRUD |
| Database | `amp.db` (SQLite) — add content tables |
| CC Integration | `empire-command-center/app/amp/` — admin/marketing pages |
| Audio storage | `~/empire-repo/uploads/amp/audio/` (local) — migrate to S3 later |
| Auth | JWT tokens (existing in `amp.py`, 72-hour expiry) |

### New Database Tables

```sql
CREATE TABLE amp_content (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  type TEXT NOT NULL,              -- 'meditation', 'affirmation', 'lesson', 'exercise'
  title TEXT NOT NULL,
  description TEXT,
  content_text TEXT,               -- full text for affirmations/lessons
  audio_url TEXT,                  -- path to audio file
  duration_seconds INTEGER,
  pillar TEXT,                     -- 'mentalidad', 'bienestar', 'liderazgo'
  mood_tags TEXT,                  -- JSON array of mood tags
  category TEXT,                   -- 'sleep', 'anxiety', 'gratitude', 'focus', 'leadership', etc.
  author TEXT,                     -- team member name
  premium BOOLEAN DEFAULT 0,
  sort_order INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE amp_courses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  description TEXT,
  pillar TEXT,
  duration_days INTEGER,
  lesson_count INTEGER,
  image_url TEXT,
  premium BOOLEAN DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE amp_lessons (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  course_id INTEGER REFERENCES amp_courses(id),
  day_number INTEGER,
  title TEXT NOT NULL,
  description TEXT,
  content_text TEXT,
  audio_url TEXT,
  duration_seconds INTEGER,
  created_at TEXT DEFAULT (datetime('now'))
);
```

### New Backend Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/amp/content` | List content (filter by type, pillar, mood, premium) |
| GET | `/api/v1/amp/content/{id}` | Single content item |
| GET | `/api/v1/amp/recommend` | Mood-based recommendations |
| GET | `/api/v1/amp/courses` | List courses |
| GET | `/api/v1/amp/courses/{id}/lessons` | Course lessons |
| POST | `/api/v1/amp/content/seed` | Admin: seed initial content |

### Frontend Pages to Update

| Page | Action |
|------|--------|
| `/daily` | Wire to backend, show mood-based recommendations |
| `/retos` | Wire to backend courses, real progress tracking |
| `/animo` | Wire to backend moods, show analytics from real data |
| `/perfil` | Wire to backend user profile, real stats |
| **NEW** `/biblioteca` | Content library browser |
| **NEW** `/curso/[id]` | Course player with lesson list + audio player |

---

## Phase Breakdown

### Phase 1: Wire + Content (NOW)

- [ ] Wire all frontend pages to backend API
- [ ] Add `amp_content` table + seed endpoint
- [ ] Seed 50 meditation scripts + 100 affirmations + 30 lessons
- [ ] Build audio player component
- [ ] Implement mood-to-recommendation loop
- [ ] Update branding to "El Portal de la Alegria"

**Estimated:** 1 session

### Phase 2: Courses + Audio (NEXT)

- [ ] Add `amp_courses` + `amp_lessons` tables
- [ ] Build course player page
- [ ] Record/source initial audio content
- [ ] Implement streak system with badges
- [ ] Add post-session reflection

**Estimated:** 1-2 sessions

### Phase 3: Monetization (WEEK 2)

- [ ] Wire Stripe subscriptions
- [ ] Implement content gating
- [ ] Add coaching booking
- [ ] Build admin content management

**Estimated:** 1 session

### Phase 4: Growth (MONTH 2)

- [ ] AI recommendations via MAX
- [ ] Community features
- [ ] Video support
- [ ] Certification program

**Estimated:** 2-3 sessions
