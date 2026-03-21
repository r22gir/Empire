# AMP Vision Analysis

**Document:** Co-Founder Vision vs. Current Implementation Audit
**Date:** 2026-03-20
**Source:** Audio transcription (2026-02-23) + codebase review
**Platform:** AMP — Actitud Mental Positiva (actitudmentalpositiva.com)

---

## 1. Co-Founder's Vision

### Original Transcription (Spanish)

> "El proyecto principal se llama actitudmentalpositiva.com www.actitudmentalpositiva.com Y la idea es tener una plataforma para ayudar a generar un cambio mental en las personas que brinde la oportunidad de manifestar bienestar y superar situaciones complejas que se presentan en la vida utilizando herramientas maravillosas que nos han apoyado en nuestro proceso de aprendizaje y sanación y que se puedan compartir con los demás. Esta plataforma también la llamamos el portal de la alegría Y es como hacer una fusión entre manvalley.com y puramente.app. La una tiene cursos en línea, audios y la otra, la puramente app, es para seguir meditaciones de diferentes temas y mirar el estado del ánimo de cada día."

### English Translation

> "The main project is called actitudmentalpositiva.com. The idea is to have a platform to help generate a mental change in people that provides the opportunity to manifest wellbeing and overcome complex situations that arise in life, using wonderful tools that have supported us in our learning and healing process, and that can be shared with others. We also call this platform 'The Joy Portal' (El Portal de la Alegría). It's like making a fusion between mindbodyvalley.com and puramente.app. One has online courses and audio content, and the other (Puramente app) is for following meditations on different topics and tracking daily mood."

### Core Vision Pillars (extracted from audio)

| Pillar | Description |
|--------|-------------|
| **Mental Transformation** | Help people generate a genuine mental shift — not surface-level motivation |
| **Wellbeing Manifestation** | Provide tools to manifest wellbeing and overcome complex life situations |
| **Shared Healing** | Tools rooted in the founders' own learning and healing journey, meant to be shared |
| **Joy as Identity** | The platform IS "The Joy Portal" — joy is the brand, not a feature |
| **Fusion Model** | Combines structured courses/audio (MindValley-style) with daily meditation & mood tracking (Puramente-style) |

---

## 2. Inspiration Sources Analysis

### 2.1 MindValley (mindvalley.com)

MindValley is a global personal growth education platform. Key features relevant to the co-founder's vision:

- **Structured course ("Quest") format** — multi-week programs with daily lessons (video + audio)
- **World-class instructor marketplace** — curated teachers with distinct methodologies
- **Community layer** — forums, cohort-based learning, peer accountability
- **Audio-first content** — meditations, affirmations, and lessons available as audio
- **Progress tracking** — streaks, completion badges, certificates
- **Subscription model** — all-access membership unlocks full library

**Takeaway for AMP:** The co-founder envisions AMP having a course/content library with structured programs, audio content, and progressive learning paths — not just standalone affirmations.

### 2.2 Puramente (puramente.app)

Puramente is a Spanish-language meditation and mindfulness app. Key features:

- **Guided meditations** — categorized by theme (anxiety, sleep, focus, gratitude, etc.)
- **Daily mood tracker** — simple emoji/slider check-in with historical view
- **Daily meditation recommendation** — personalized based on mood input
- **Session history** — track meditation minutes, streaks, consistency
- **Calm, minimal UX** — low cognitive load, soothing color palette
- **Push notifications** — gentle daily reminders

**Takeaway for AMP:** The co-founder specifically wants mood tracking tied to meditation recommendations — the mood input should drive what content is surfaced.

### 2.3 The Fusion

The vision is not "pick features from both." It is a single cohesive experience where:

1. Users check in daily (mood) — Puramente influence
2. The platform recommends content based on that mood — bridge between both
3. Content includes both quick sessions (meditations, affirmations) AND deep courses — MindValley influence
4. Progress is tracked across both micro-habits (daily) and macro-journeys (courses)

---

## 3. Current Implementation Status

### 3.1 Codebase Locations

| Component | Path | Status |
|-----------|------|--------|
| Standalone App | `~/empire-repo/amp/` | Next.js on port 3003 |
| Command Center Integration | `~/empire-repo/empire-command-center/app/amp/` | Integrated pages |
| Backend API | `~/empire-repo/backend/app/routers/amp.py` | FastAPI router |
| Database | `amp.db` | SQLite, 4 tables, all empty |

### 3.2 Database Schema

| Table | Purpose | Records |
|-------|---------|---------|
| `amp_users` | User accounts | 0 |
| `amp_moods` | Daily mood entries | 0 |
| `amp_journal` | Journal entries | 0 |
| `amp_progress` | Course/challenge progress | 0 |

### 3.3 Implemented Features

| Feature | Status | Notes |
|---------|--------|-------|
| Landing page | Built | 3 pillars: Mentalidad, Bienestar, Liderazgo |
| Daily page | Built | Shows affirmation + meditation |
| Challenges (Retos) | Built | 21-day program structure |
| Mood tracker (Animo) | Built | Basic UI exists |
| Profile page | Built | User profile shell |
| Pricing page | Built | Free tier + $9.99/mo Premium |
| Spanish language | Yes | Consistent throughout |
| Color palette | Done | Warm gold / sage / sunrise — on brand |

### 3.4 What Works Well

- **Language & tone** — Spanish-first approach matches the target audience
- **Color palette** — warm gold/sage/sunrise feels aligned with "Portal de la Alegria"
- **3-pillar structure** — Mentalidad, Bienestar, Liderazgo maps well to the vision
- **Challenge format** — 21-day programs align with the MindValley "Quest" concept
- **Database tables** — mood, journal, and progress tables anticipate the right data model

---

## 4. Gap Analysis: Vision vs. Reality

### 4.1 Critical Gaps

| Gap | Vision | Current State | Severity |
|-----|--------|---------------|----------|
| **No content library** | MindValley-style courses with audio/video | Only single daily affirmation + meditation | HIGH |
| **No audio infrastructure** | Audio content is core to both inspirations | No audio player, no audio files, no streaming | HIGH |
| **Mood-to-content loop missing** | Mood check-in should drive recommendations | Mood tracker exists but does not influence content | HIGH |
| **"Joy Portal" identity absent** | "El Portal de la Alegria" is the brand name | Not referenced anywhere in the UI | MEDIUM |
| **No guided meditations** | Puramente-style themed meditation library | Only one static meditation placeholder | HIGH |
| **Empty database** | Should have seed content at minimum | All 4 tables have 0 records | HIGH |

### 4.2 Feature Gaps (Detailed)

#### Content & Courses
- No course creation or management system
- No lesson/module structure within courses
- No audio file upload, storage, or playback
- No video embed support
- No instructor/author profiles
- No content categorization by theme (anxiety, sleep, gratitude, etc.)

#### Daily Experience (Puramente-style)
- Mood tracker UI exists but has no backend loop to recommend content
- No meditation timer or session tracking
- No daily streak or consistency metrics
- No push notification or reminder system
- No "how did this session make you feel" post-meditation check-in

#### Community & Sharing
- Vision explicitly mentions sharing tools "with others"
- No sharing mechanism, community feed, or peer features
- No ability to recommend content to friends

#### Monetization
- Pricing page exists ($9.99/mo) but no payment integration is wired up
- No content gating (free vs. premium)
- No trial period logic

### 4.3 Alignment Score

| Dimension | Score (1-10) | Notes |
|-----------|:------------:|-------|
| Brand identity | 5 | Good palette, missing "Joy Portal" naming |
| Content depth | 2 | Placeholder content only |
| Daily ritual UX | 3 | Basic structure, no feedback loop |
| Course platform | 1 | No course infrastructure |
| Audio experience | 1 | No audio capability |
| Mood intelligence | 2 | Tracker exists, no intelligence |
| Monetization readiness | 2 | Pricing page only |
| **Overall alignment** | **2.3 / 10** | Foundation laid, core experience missing |

---

## 5. Recommendations for UX Alignment

### 5.1 Rebrand the Experience

- Add "El Portal de la Alegria" as the tagline/subtitle throughout the UI
- Update the landing page hero to lead with the joy/transformation message from the audio
- Ensure every page reinforces the "portal" metaphor — entering a space of transformation

### 5.2 Build the Daily Ritual Loop

This is the single most important feature to align with the vision:

```
[User opens app] → [Mood check-in] → [Personalized recommendation]
                                          ├── Quick: 5-min meditation
                                          ├── Medium: Guided audio (15 min)
                                          └── Deep: Course lesson
                                     → [Post-session reflection]
                                     → [Progress updated]
```

### 5.3 Create Content Infrastructure

- Design a `ContentItem` model: type (meditation, affirmation, course_lesson, audio), theme, duration, premium flag
- Add `amp_content`, `amp_courses`, `amp_lessons` tables
- Build an admin interface to upload/manage content
- Support audio file upload and streaming playback
- Seed with at least 10-20 meditations and 1 complete course

### 5.4 Implement Audio Player

- Embed an audio player component (persistent across pages, like a podcast app)
- Support background playback
- Track listening progress and completion
- Display waveform or timer visualization for meditations

### 5.5 Add Mood Intelligence

- After mood check-in, query content library filtered by mood-to-theme mapping
- Example: "Sad" mood → suggest gratitude meditation + uplifting affirmation + relevant course
- Store mood-content-outcome data to improve recommendations over time

---

## 6. Priority Roadmap

### Phase 1: Foundation (Weeks 1-2)
**Goal:** Seed content and establish the daily loop

- [ ] Add "El Portal de la Alegria" branding to landing page and nav
- [ ] Create `amp_content` and `amp_courses` database tables
- [ ] Build content admin API (CRUD for meditations, affirmations, audio)
- [ ] Seed database with 15 guided meditations (can use AI-generated scripts initially)
- [ ] Seed database with 30 daily affirmations
- [ ] Wire mood tracker to content recommendations (mood → theme mapping)

### Phase 2: Audio Experience (Weeks 3-4)
**Goal:** Make audio a first-class citizen

- [ ] Build persistent audio player component
- [ ] Implement audio file upload to backend (S3 or local storage)
- [ ] Add meditation timer with ambient sound options
- [ ] Create meditation session tracking (start, pause, complete)
- [ ] Post-session mood re-check ("How do you feel now?")

### Phase 3: Course Platform (Weeks 5-8)
**Goal:** MindValley-style structured learning

- [ ] Design course → module → lesson hierarchy
- [ ] Build course catalog page with categories
- [ ] Implement lesson player (audio + text + optional video)
- [ ] Add progress tracking per course (% complete, current lesson)
- [ ] Create first complete course: "21 Dias de Transformacion Mental"
- [ ] Build streak system and achievement badges

### Phase 4: Monetization & Community (Weeks 9-12)
**Goal:** Revenue and sharing

- [ ] Wire Stripe subscription to Premium tier
- [ ] Implement content gating (free samples + premium library)
- [ ] Add "share with a friend" feature for affirmations/meditations
- [ ] Build simple community feed (optional — evaluate if aligned with vision)
- [ ] Add push notification reminders for daily check-in
- [ ] Launch beta to small test group

---

## Summary

The co-founder's vision is clear and compelling: AMP should be a Spanish-language fusion of MindValley (structured courses, audio content) and Puramente (daily meditations, mood tracking), unified under the brand identity of "El Portal de la Alegria" (The Joy Portal). The current implementation has a solid visual foundation and correct thematic structure, but lacks the core content infrastructure, audio capabilities, and mood-to-content intelligence loop that define the vision. The highest-impact next step is building the daily ritual loop (mood check-in → personalized content recommendation → post-session reflection) and seeding the platform with real audio content.
