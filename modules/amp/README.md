# AMP — Actitud Mental Positiva

> Wellness and personal development platform — affirmations, journaling, mood tracking, mentorship.

## Status: Active

## Overview
AMP is a Spanish-language wellness coaching platform based on actitudmentalpositiva.com. Features daily affirmations, mood check-ins, guided meditations, micro-lessons, journaling, and mentorship. Separate JWT auth system.

## Backend
- **Router:** `backend/app/routers/amp.py`
- **Prefix:** `/api/v1/amp`
- **Storage:** SQLite (`backend/data/amp.db`)
- **Auth:** JWT tokens (72-hour expiry)
- **Tables:** amp_users, amp_moods, amp_journal, amp_progress

### Key Endpoints
- `POST /api/v1/amp/signup` — User registration
- `POST /api/v1/amp/login` — User login
- `GET /api/v1/amp/me` — User profile
- `POST /api/v1/amp/moods` — Log mood
- `POST /api/v1/amp/journal` — Journal entry
- `POST /api/v1/amp/progress` — Track course progress
- `GET /api/v1/amp/admin/stats` — Admin analytics

## Frontend
- **Landing:** `app/amp/page.tsx` (team, services, values, mission)
- **Auth:** `app/amp/login/page.tsx`, `app/amp/signup/page.tsx`
- **Dashboard:** `app/amp/dashboard/page.tsx` (affirmations, mood, meditation, journal)
- **Nav:** `app/components/amp/AmpNav.tsx`
- **Auth Lib:** `app/lib/amp-auth.ts`
- **Public URL:** `http://localhost:3009/amp`

## Design System
- Gold: #D4A030, Sage Green: #7CB98B, Lavender: #9B8EC4
- Dark Brown: #2D2A26, Warm White: #FFF9F0
- Fonts: Playfair Display + Nunito

## Team
Andrea Silva, Dericielo Jimenez, Lina Valencia Trivino, Juan Diego Giraldo
