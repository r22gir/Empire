# OpenClaw Split-Brain Fix — Sprint 1d Item 3 (2026-07-08)

## Why this file exists

The systemd unit file `/home/rg/.config/systemd/user/empire-openclaw.service`
lives OUTSIDE the git repo (under `~/.config/`, not in `backend/`). When
the unit was changed for the split-brain fix, the change has to be
documented in the repo so future operators can reproduce it. This
file is the trace.

## What was wrong

- Port `0.0.0.0:7878` was held by a **zombie** process PID 1490
  (`/home/rg/empire-repo/backend/venv/bin/python3 server.py`,
  cwd=`/home/rg/empire-repo/openclaw`, started 2026-06-21).
- The systemd unit `empire-openclaw.service` was crash-looping
  (`NRestarts=246,509`) because every restart tried to bind 7878,
  got `EADDRINUSE`, died, retried in 5s.
- PID 1490 had **no API keys** in its env (no `DEEPSEEK_API_KEY`,
  no `OPENCLAW_PROVIDER`). It was answering health checks but
  every task failed with "CodeTaskRunner completed without tool/action
  evidence" — matching the 5,922 failed-task backlog rows.
- This caused MAX desk tasks dispatched via the bridge to fail ~80%
  of the time, masquerading as a "CodeTaskRunner" bug.

## What the systemd unit now points at

| Field | Old (broken) | New (canonical) |
|---|---|---|
| `WorkingDirectory=` | `/home/rg/empire-repo/openclaw` (stale mirror) | `/home/rg/empire-repo-main/openclaw` |
| `ExecStart=` | `/home/rg/empire-repo/backend/venv/bin/python3 server.py` (stale venv, also has `(deleted)` exe on the zombie) | `/home/rg/empire-repo-main/backend/venv/bin/python3 server.py` |

The drop-in `empire-openclaw.service.d/deepseek.conf` (which adds
`EnvironmentFile=/home/rg/.config/empirebox/openclaw-deepseek.env`
and overrides `WorkingDirectory` to the canonical path) was
unchanged — its `WorkingDirectory` override is now redundant with
the unit's but harmless.

## What was killed

PID 1490 — `kill -TERM 1490` (it died on TERM; did not need KILL).
The systemd unit immediately bound the port with a fresh worker
(PID 2835627 in the verified run; the new PID will differ on
subsequent restarts).

## Verification

1. New worker env (`/proc/<PID>/environ`):
   - `DEEPSEEK_API_KEY=sk-30b26...` ✓
   - `DEEPSEEK_BASE_URL=https://api.deepseek.com/v1` ✓
   - `DEEPSEEK_MODEL=deepseek-v4-flash` ✓
   - `OPENCLAW_PROVIDER=deepseek` ✓
2. New worker cwd: `/home/rg/empire-repo-main/openclaw` ✓
3. New worker cmdline: `/home/rg/empire-repo-main/backend/venv/bin/python3 server.py` ✓
4. `curl http://localhost:7878/health` → 200 `{"status":"ok",...}` ✓
5. End-to-end bridge probe via `dispatch_desk_task_to_openclaw`:
   returned `status: completed` with a real DeepSeek response in 7.6s
   (task_id `oc-desk-orchestrator-20260708-233857`).
6. 60s stability watch: NRestarts delta = 0, port-holder PID stable.

## How to reproduce this fix on a fresh install

```bash
# 1. .bak the unit + drop-in
TS=$(date +%Y%m%d_%H%M%S)
cp -p /home/rg/.config/systemd/user/empire-openclaw.service \
      /home/rg/.config/systemd/user/empire-openclaw.service.bak.${TS}
cp -p /home/rg/.config/systemd/user/empire-openclaw.service.d/deepseek.conf \
      /home/rg/.config/systemd/user/empire-openclaw.service.d/deepseek.conf.bak.${TS}

# 2. Edit the unit: WorkingDirectory= and ExecStart= must point at
#    /home/rg/empire-repo-main/* (NOT /home/rg/empire-repo/* — that's
#    the stale mirror).

# 3. Ensure the env file exists (mode 600):
ls -la /home/rg/.config/empirebox/openclaw-deepseek.env
# should contain: DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL,
# OPENCLAW_PROVIDER

# 4. Confirm server.py imports in the canonical venv
timeout 5 /home/rg/empire-repo-main/backend/venv/bin/python3 -c "
import sys; sys.path.insert(0, '/home/rg/empire-repo-main/openclaw')
import server
print('server.py OK:', server.__name__)
"

# 5. Reload + restart
systemctl --user daemon-reload
systemctl --user restart empire-openclaw
sleep 5

# 6. Verify
ss -ltnp 'sport = :7878'
curl http://localhost:7878/health
# /proc/<PID>/environ should contain DEEPSEEK_API_KEY

# 7. Bridge smoke test
/home/rg/empire-repo-main/backend/venv/bin/python3 -c "
import asyncio, sys; sys.path.insert(0, '/home/rg/empire-repo-main/backend')
from app.routers.openclaw_bridge import dispatch_desk_task_to_openclaw
print(asyncio.run(dispatch_desk_task_to_openclaw(
    desk_id='orchestrator',
    task_title='install probe',
    task_description='bridge smoke test on fresh install',
    timeout=60,
)))
"
```

## Backlog — left untouched per founder decision

The 5,922 `failed` rows in `openclaw_tasks` are a historical Atlas-era
dump. **NOT purged, NOT retried.** Retrying them would flood the new
worker with 5,922 obsolete jobs.

Founder's separate decision (deferred): the dashboard badge
"OpenClaw online · 7,363 queued" currently counts total rows
including dead history. Display-honesty fix: count only actionable
tasks (e.g. `status NOT IN ('done','cancelled') AND created_at > ...`).
Filed for a future item.

## Side note: the `/api/v1/orchestration/dashboard` `openclaw_up: false`

`check_service` in `routers/orchestration.py` uses `r.ok` which is the
**`requests` library** attribute, not **httpx** (which the function
imports). httpx exposes `r.is_success` instead. So `check_service`
returns `False` for ALL services (backend, frontend, openclaw, ollama)
regardless of their actual state. This is a pre-existing bug; OpenClaw
is in fact healthy (verified directly via `curl http://localhost:7878/health`).
Fix: change `r.ok` → `r.is_success` in `check_service`. Filed for a
follow-up (not in Item 3).
