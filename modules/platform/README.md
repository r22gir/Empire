# PlatformForge

> Infrastructure monitoring — servers, Docker containers, Ollama, module health.

## Status: Active

## Overview
Monitors and manages Empire infrastructure: Docker containers, Ollama models, module connectivity, backups, and server health.

## Backend
- **Routers:** `docker_manager.py`, `ollama_manager.py`, `system_monitor.py`
- **Prefix:** `/api/v1`

### Key Endpoints
- `GET /api/v1/system/stats` — CPU, RAM, disk, temp sensors
- `GET /api/v1/ollama/models` — Installed AI models
- `POST /api/v1/ollama/pull` — Pull new model
- Docker container start/stop/status for 13 Empire products

## Frontend
- **Screen:** `app/components/screens/PlatformPage.tsx`
- **Features:** Server health, module status, connectivity checks, Ollama management, backup status
- **Color:** #2563eb (blue)
- **Default Tab:** `dashboard`
