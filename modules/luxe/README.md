# LuxeForge

> Premium design services — client intake portal, measurements, quotes, and project management.

## Status: Active

## Overview
LuxeForge provides a public-facing client intake system (separate JWT auth) where customers submit design projects with photos and measurements. Admin manages projects, generates quotes, and communicates through the portal.

## Backend
- **Routers:** `intake_auth.py` (17 endpoints), `luxeforge_measurements.py` (4 endpoints)
- **Prefixes:** `/api/v1/intake`, `/api/luxeforge/measurements`
- **Auth:** JWT tokens (72-hour expiry), SQLite

### Key Endpoints
- `POST /api/v1/intake/signup` — Client registration
- `POST /api/v1/intake/login` — Client login
- `POST /api/v1/intake/projects` — Submit new project
- `POST /api/v1/intake/projects/{id}/photos` — Upload project photos
- `POST /api/v1/intake/projects/{id}/submit` — Submit for review
- `GET /api/v1/intake/admin/projects` — Admin: all projects
- `POST /api/v1/intake/admin/projects/{id}/to-quote` — Convert to quote
- `POST /api/luxeforge/measurements/calibrate` — Reference calibration
- `POST /api/luxeforge/measurements/calculate` — Calculate real dimensions

## Frontend

### Admin (Command Center)
- **Screen:** `app/components/screens/LuxeForgePage.tsx`
- **Features:** User management (edit/delete), project review, send to workroom, quote generation

### Client Portal
- **Pages:** `/intake/*` (landing, login, signup, dashboard, new project, project detail, account)
- **Components:** `IntakeNav.tsx`, `PhotoUploader.tsx`, `MeasurementInput.tsx`, `ProjectCard.tsx`
- **Public URL:** `http://localhost:3009/intake`
