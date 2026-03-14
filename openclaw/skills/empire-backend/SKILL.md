---
name: empire-backend
description: Execute backend tasks — database cleanup, API testing, data management, service health checks. Use when tasks involve the FastAPI backend, database operations, or API endpoints.
version: 1.0.0
metadata:
  openclaw:
    emoji: "⚙️"
    requires:
      bins:
        - python3
        - curl
---

# Empire Backend Operations

## Setup (always run first)
```bash
cd ~/empire-repo
source backend/venv/bin/activate
```

## Database Location
- SQLite databases: ~/empire-repo/backend/data/
- Main DB files: empire.db, costs.db, memories.db

## Common Operations

### Health Check
```bash
curl -s http://localhost:8000/api/v1/health | python3 -m json.tool
```

### List All API Routes
```bash
curl -s http://localhost:8000/openapi.json | python3 -c "import sys,json; [print(f'{m.upper()} {p}') for p,v in json.load(sys.stdin)['paths'].items() for m in v.keys()]"
```

### Database Cleanup — Remove Test/Fake Data
When asked to clean data:
1. ALWAYS back up first: `cp data/empire.db data/empire.db.bak.$(date +%s)`
2. List what will be deleted BEFORE deleting
3. Report what was removed

### Wipe Test Customers
```bash
cd ~/empire-repo/backend
source venv/bin/activate
python3 -c "
import sqlite3
conn = sqlite3.connect('data/empire.db')
c = conn.cursor()
# List test entries first
c.execute('SELECT id, name, email FROM customers')
rows = c.fetchall()
print('Current customers:')
for r in rows: print(f'  {r}')
# Only delete after confirmation
conn.close()
"
```

### Test an Endpoint
```bash
# GET
curl -s http://localhost:8000/api/v1/{endpoint} | python3 -m json.tool

# POST
curl -s -X POST http://localhost:8000/api/v1/{endpoint} \
  -H "Content-Type: application/json" \
  -d '{"key": "value"}' | python3 -m json.tool
```

### Restart Backend
```bash
cd ~/empire-repo/backend
source venv/bin/activate
# Find and kill existing
lsof -ti:8000 | xargs kill -9 2>/dev/null
# Start fresh
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/backend.log 2>&1 &
echo "Backend restarting on :8000"
```

## Rules
- NEVER delete data without backing up first
- NEVER modify .env files
- Always report what changed with counts and specifics
- If a migration is needed, create it as a new file, don't edit existing ones
