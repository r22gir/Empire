# Empire Port Registry
> Master list of all ports used by Empire services. DO NOT change ports without updating this file.
> Last updated: 2026-03-09

## Backend & Infrastructure

| Port | Service | Directory | Status |
|------|---------|-----------|--------|
| **8000** | FastAPI Backend API | `~/empire-repo/backend/` | Active |
| **8080** | Static Homepage | `~/empire-repo/homepage/` | Active |
| **11434** | Ollama (local AI) | System service | Active |
| **7878** | OpenClaw AI | `~/Empire/openclaw/` | Active |

## Frontend Apps (Next.js)

| Port | Service | Directory | Status |
|------|---------|-----------|--------|
| **3000** | Empire App (unified) | `~/empire-repo/empire-app/` | Active |
| **3001** | WorkroomForge (QuoteBuilder) | `~/empire-repo/workroomforge/` | Active |
| **3002** | LuxeForge (Designer Portal) | `~/empire-repo/luxeforge_web/` | Active |
| **3003** | AMP (Affiliate Marketing) | `~/empire-repo/amp/` | Active |
| **3004** | LuxeForge Intake Portal | `~/empire-repo/empire-command-center/` (intake route) | Active |
| **3005** | Empire Command Center | `~/empire-repo/empire-command-center/` | Active |
| **3006** | *RESERVED — do not use* | (often grabbed by CC dev overflow) | Reserved |
| **3007** | RelistApp | `~/empire-repo/relistapp/` | Active |
| **3008** | *Available* | — | Free |
| **3009** | Founder Dashboard (legacy) | `~/empire-repo/founder_dashboard/` | Active |
| **3010** | *Available — RecoveryForge* | `~/recoveryforge/` | Planned |
| **3011** | *Available — SocialForge* | — | Planned |
| **3012** | *Available — MarketForge Mobile* | `~/empire-repo/market_forge_app/` | Planned |
| **3013-3019** | *Available — Future products* | — | Reserved |

## External Services

| Port | Service | Notes |
|------|---------|-------|
| **443** | Cloudflare Tunnel | studio.empirebox.store, api.empirebox.store |
| **5432** | PostgreSQL | If running locally |
| **6379** | Redis | If running locally |

## Rules
1. **Always check this file** before assigning a port to a new service
2. **Update this file** when adding or changing a port
3. **Port 3006 is cursed** — the Command Center dev server grabs it when 3005 is busy. Leave it reserved.
4. **Range 3000-3019** — All Next.js frontend apps
5. **Range 8000-8099** — Backend services and static sites
6. **Range 7800-7899** — AI services (OpenClaw, future)

## Quick Reference Command
```bash
# See all active Empire ports
ss -tlnp | grep -E "300[0-9]|301[0-9]|800[0-9]|787[0-9]|1143[0-9]" | sort -t: -k2 -n
```
