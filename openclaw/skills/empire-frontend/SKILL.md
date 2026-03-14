---
name: empire-frontend
description: Execute frontend tasks — wire pages, fix navigation, build components, run dev servers. Use for any Next.js, React, or UI work across Empire apps.
version: 1.0.0
metadata:
  openclaw:
    emoji: "🎨"
    requires:
      bins:
        - node
        - npm
---

# Empire Frontend Operations

## Apps & Ports
| App | Path | Port | Framework |
|-----|------|------|-----------|
| Empire App | ~/empire-repo/empire-app/ | 3000 | Next.js |
| Command Center | ~/empire-repo/empire-command-center/ | 3005 | Next.js |
| WorkroomForge | ~/empire-repo/workroomforge/ | 3001 | Next.js |
| LuxeForge | ~/empire-repo/luxeforge_web/ | 3002 | Next.js |
| AMP | ~/empire-repo/amp/ | 3003 | Next.js |
| RelistApp | ~/empire-repo/relistapp/ | 3007 | Next.js |
| Founder Dashboard | ~/empire-repo/founder_dashboard/ | 3009 | Next.js |

## Design System
- Background: #f5f3ef (warm off-white)
- Gold accent: #b8960c
- All buttons: min 44px height (tablet-friendly)
- Tab colors: MAX=gold, Workroom=green, CraftForge=yellow, Platform=blue

## Common Operations

### Check if app builds clean
```bash
cd ~/empire-repo/{app-folder}
npm run build 2>&1 | tail -20
```

### Find dead routes / placeholder pages
```bash
# Find all page.tsx files
find ~/empire-repo/{app-folder}/app -name "page.tsx" | sort

# Find placeholder/stub content
grep -rl "coming soon\|placeholder\|todo\|TODO" ~/empire-repo/{app-folder}/app/ --include="*.tsx" --include="*.ts"
```

### Find broken imports
```bash
cd ~/empire-repo/{app-folder}
npx tsc --noEmit 2>&1 | head -50
```

### Wire a page to backend API
When connecting a frontend page to the backend:
1. Check the API endpoint exists: `curl -s http://localhost:8000/api/v1/{endpoint}`
2. Create/update the page component with proper fetch calls
3. Use `fetch('http://localhost:8000/api/v1/{endpoint}')` for server-side
4. Use relative `/api/v1/{endpoint}` if proxied
5. Handle loading, error, and empty states

### Start a dev server
```bash
cd ~/empire-repo/{app-folder}
PORT={port} npm run dev > /tmp/{app}.log 2>&1 &
```

## CraftForge — Biggest Gap
CraftForge has 15 backend endpoints but ZERO frontend. It mirrors Workroom structure.
Backend endpoints exist at /api/v1/craftforge/*
Frontend needs: Dashboard, Quote Builder, Job Tracker, Inventory, Customer List
Base it on WorkroomForge components but adapt for woodwork/CNC terminology.

## Rules
- Keep components under 300 lines — split if larger
- Always use TypeScript (.tsx)
- Test builds after changes
- Don't install new packages without noting it in commit message
