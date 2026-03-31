# OpenClaw Autonomous Dev Engine — Owner's Guide

## What's New

OpenClaw is no longer just a dispatch-and-return system. It now runs as a **persistent autonomous execution engine** inside your backend. You can queue tasks from MAX chat, the API, or the new dashboard — and OpenClaw will pick them up, execute them, and notify you via Telegram when done.

## Quick Start

### Queue a task from MAX chat
Just tell MAX:
- "Queue an openclaw task: check the backend logs for errors"
- "Queue an openclaw task for the IT desk: report disk usage"
- "Queue an openclaw task for ForgeDesk: generate a 96 inch straight bench drawing"

### Queue a task from the Dashboard
1. Go to **studio.empirebox.store** → sidebar → **OpenClaw**
2. Click **New Task**, fill in title/description/desk/priority
3. Watch it move from queued → running → done

### Queue a task from the API
```bash
curl -X POST http://localhost:8000/api/v1/openclaw/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Check system health","description":"Report CPU, RAM, disk","desk":"ITDesk","priority":5}'
```

## Task Lifecycle

```
queued → running → done
                 → failed (can retry)
                 → paused (needs your approval)
                 → cancelled
```

- **queued**: waiting for worker pickup (within 30 seconds)
- **running**: OpenClaw is executing the task
- **done**: completed successfully, result stored
- **failed**: something went wrong — you can retry from the dashboard
- **paused**: OpenClaw flagged something as NEEDS_APPROVAL — review and approve/reject
- **cancelled**: you cancelled it manually

## Dashboard

**URL:** studio.empirebox.store → OpenClaw (sidebar)
**Local:** localhost:3005 → OpenClaw

Features:
- Live task list with color-coded status badges
- Stats bar: total, queued, running, done, failed counts
- Click any task to see full result or error
- Action buttons: Retry, Cancel, Approve, Reject
- New Task form with desk dropdown (18 desks) and priority (1-10)
- Auto-refreshes every 30 seconds
- Works on mobile

## Notifications

| Event | Channel | When |
|-------|---------|------|
| Task completed | Telegram | Immediately |
| Task failed | Telegram | Immediately |
| Task needs approval | Telegram | Immediately (with question) |
| Morning report | Telegram + Email | 7:30 AM EST daily |

The morning report includes: service health (backend, CC, OpenClaw, Ollama), disk/RAM/uptime, and task stats from the last 24 hours.

## Safety Guarantees

1. **One task at a time** — worker never runs tasks in parallel, preventing conflicts
2. **Auto-revert** — if a git commit breaks services (backend or CC health check fails), it auto-reverts the commit
3. **Critical file protection** — OpenClaw cannot modify: `.env`, `.git/`, `node_modules/`, `empire.db`, `main.py`, `start-empire.sh`
4. **Max 20 files per commit** — refuses commits touching more than 20 files
5. **Python syntax validation** — runs `ast.parse()` on all .py files before committing
6. **Zombie protection** — tasks running longer than 10 minutes are auto-marked as failed
7. **NEEDS_APPROVAL** — if OpenClaw is unsure, it pauses the task and asks you via Telegram
8. **Drawing shortcut** — bench drawing tasks skip OpenClaw entirely and use the fast renderer (0.2s)

## Example Commands

```
"Queue an openclaw task: review the backend error logs from today"
"Queue an openclaw task for MarketingDesk: draft a social media post about our new bench designs"
"Queue an openclaw task for ITDesk: check if all API endpoints are responding"
"Queue an openclaw task for ForgeDesk: generate shop drawings for a 120 inch L-shaped bench"
"Queue an openclaw task: run git status and report any uncommitted changes"
```

## Current Limitations

1. **Sequential only** — one task at a time (next task waits for current to finish)
2. **No Telegram reply** — can't approve/reject by replying to Telegram; must use dashboard or API
3. **No scheduled tasks** — can't set recurring tasks like "check logs every hour"
4. **No task chaining** — can't say "after task A finishes, run task B"

## Next 3 Improvements

1. **Scheduled tasks** — cron-style recurring tasks (e.g., "check disk every 6 hours", "post social media every Monday at 9 AM"). Add a `schedule` column to `openclaw_tasks` with cron expressions, and a scheduler loop that creates new task instances on schedule.

2. **Parallel execution** — configurable worker concurrency (e.g., 3 tasks at once). Non-conflicting desks can run in parallel while same-desk tasks stay sequential. Requires task locking and resource tracking.

3. **Telegram reply approval** — reply "approve" or "reject" directly to the Telegram notification message. The Telegram bot webhook parses reply-to-message context and calls the approve/reject API endpoint automatically.

## Key Files

| File | Purpose |
|------|---------|
| `backend/app/routers/openclaw_tasks.py` | Task queue API (10 endpoints) |
| `backend/app/services/openclaw_worker.py` | Background worker loop |
| `backend/app/services/max/tool_executor.py` | queue_openclaw_task tool |
| `empire-command-center/app/components/screens/OpenClawTasksPage.tsx` | Dashboard UI |
| `scripts/morning_openclaw_check.sh` | 7:30 AM daily cron script |
| `backend/app/routers/openclaw_bridge.py` | Legacy dispatch (still works) |
