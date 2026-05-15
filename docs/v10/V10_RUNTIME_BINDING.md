# EmpireBox v10.0 — Runtime Binding

## Purpose

v10 runs on **separate ports** from stable Empire to prevent accidental cross-contamination. This document specifies the binding rules, verification procedures, and restart protocols.

---

## Port & Path Registry

| Process | Port | Path | Service Unit |
|---------|------|------|--------------|
| Backend API | **8010** | `~/empire-repo-v10/backend/` | `empire-backend-v10.service` |
| Portal (Next.js) | **3010** | `~/empire-repo-v10/empire-command-center/` | `empire-portal-v10.service` |

---

## Binding Rules

### Backend — Port 8010

- **MUST** serve from `~/empire-repo-v10/backend/`
- **MUST NOT** serve from `~/empire-repo/backend/` (stable)
- Process working directory verified via: `readlink /proc/[pid]/cwd`
- If working directory is `empire-repo/backend` (no `-v10`): **STALE PROCESS — KILL AND RESTART**

```bash
# Check which repo is serving 8010
readlink /proc$(pgrep -f "uvicorn.*8010")/cwd
```

### Portal — Port 3010

- **MUST** serve from `~/empire-repo-v10/empire-command-center/`
- **MUST NOT** serve from `~/empire-repo/empire-command-center/` (stable)
- Same verification method applies

---

## Service Units

### empire-backend-v10.service

```ini
[Unit]
Description=EmpireBox v10.0 Test Backend API (port 8010)
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/rg/empire-repo-v10/backend
ExecStart=/home/rg/empire-repo-v10/backend/venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8010 --timeout-keep-alive 65
Restart=always
RestartSec=5
Environment=PATH=/home/rg/empire-repo-v10/backend/venv/bin:/home/rg/.local/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=/home/rg/empire-repo-v10/backend

[Install]
WantedBy=default.target
```

### empire-portal-v10.service

```ini
[Unit]
Description=EmpireBox v10.0 Command Center Portal (port 3010)
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/rg/empire-repo-v10/empire-command-center
ExecStart=/bin/bash -c "cd /home/rg/empire-repo-v10/empire-command-center && npm run dev -- -p 3010"
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
```

---

## Restart Procedures

### Full v10 restart (after config or code changes)

```bash
systemctl --user restart empire-backend-v10.service empire-portal-v10.service
sleep 3 && systemctl --user status empire-backend-v10.service --no-pager
```

### Verify healthy

```bash
# Backend health
curl -s http://localhost:8010/health

# Correct commit on 8010
curl -s http://localhost:8010/api/v1/max/status 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('commit','?'))"

# Correct provider (must be minimax, NOT groq)
curl -s -X POST http://localhost:8010/api/v1/max/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "what is 2+2?", "desk": "test"}' 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('model_used','?'))"
```

---

## Troubleshooting

### Stale stable process on 8010

Symptoms: Groq provider label, wrong commit hash, stable feature bleeding into v10.

```bash
# Identify stale process
lsof -i :8010

# Kill by PID
kill -9 <PID>

# Restart via systemd
systemctl --user start empire-backend-v10.service
```

### Portal serving wrong repo

```bash
# Check working directory
readlink /proc$(pgrep -f "next.*3010")/cwd

# Restart
systemctl --user restart empire-portal-v10.service
```

---

## Git Commit Verification

v10 backend commit must match the active `feature/v10.0-test-lane` HEAD for the running worktree.

```bash
cd ~/empire-repo-v10/backend && git log -1 --oneline
```

Cross-check lane metadata endpoints:

```bash
curl -s http://localhost:8010/api/v1/max/status | python3 -m json.tool
curl -s http://localhost:8010/api/v1/git | python3 -m json.tool
curl -s http://localhost:8010/api/v1/dev/git | python3 -m json.tool
```

`/api/v1/max/status` and `/api/v1/git` must agree on:
- lane: `v10-test`
- branch: `feature/v10.0-test-lane`
- worktree: `~/empire-repo-v10`
- commit hash

---

## Last Updated

2026-05-15
