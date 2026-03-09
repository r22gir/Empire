# System

> Real-time system health monitoring — CPU, RAM, disk, temperature, services.

## Status: Active

## Overview
Live system monitoring dashboard showing hardware metrics, service status, and recent system changes.

## Backend
- **Router:** `backend/app/routers/system_monitor.py`
- **Prefix:** `/api/v1`

### Key Endpoints
- `GET /api/v1/system/stats` — CPU, RAM, disk usage, temperature sensors
- `POST /api/v1/system/brain-sync` — Sync brain data

## Frontend
- **Screen:** `app/components/screens/SystemReportScreen.tsx`
- **Features:** CPU/RAM/disk gauges, module status, recent changes log
- **Color:** #16a34a (green)
- **Default Tab:** `report`

## Warning
- DO NOT run `sensors-detect` — crashes the machine
