# SocialForge

> Social media management — post scheduling, AI content generation, analytics across platforms.

## Status: Dev

## Overview
Manages social media presence across Instagram, Facebook, Pinterest, LinkedIn, and TikTok. Features AI-powered content generation, post scheduling, campaign management, and analytics dashboard.

## Backend
- **Router:** `backend/app/routers/socialforge.py`
- **Prefix:** `/api/v1/socialforge`
- **Storage:** JSON files in `backend/data/socialforge/`

### Key Endpoints
- `GET /api/v1/socialforge/posts` — List posts
- `POST /api/v1/socialforge/posts` — Create post
- `POST /api/v1/socialforge/generate` — AI content generation
- `GET /api/v1/socialforge/campaigns` — List campaigns
- `GET /api/v1/socialforge/dashboard` — Analytics overview
- `GET /api/v1/socialforge/calendar` — Content calendar
- `GET /api/v1/socialforge/accounts` — Connected accounts
- `POST /api/v1/socialforge/accounts/ai-guide` — AI setup guidance

## Frontend
- **Screen:** `app/components/screens/SocialForgePage.tsx`
- **Platforms:** Instagram, Facebook, Pinterest, LinkedIn, TikTok
