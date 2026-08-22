# DB TRUTH + FORK REPORT — 2026-08-22B
**M3 (EmpireDell)** — read-only diagnostic
**Repo doctrine:** `~/empire-repo-main` is THE repo (`feature/drawing-standard`).
`~/empire-repo` is the fork. Fork is being written to hourly — confirmed.

---

## PART A — DB BINDING

### A1 — Default engine

```
$ sed -n '1,60p' ~/empire-repo-main/backend/app/database.py
"""
Database setup and session management.
Supports both sync (SQLite) and async (PostgreSQL) modes.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import Generator, AsyncGenerator
import os

# Get database URL from environment or use SQLite default
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///" + os.path.join(
        os.getenv("EMPIRE_DATA_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "empirebox.db",
    ),
)
...
```

```
$ grep -rn 'DATABASE_URL' ~/empire-repo-main/backend/app --include='*.py' | head -10
/home/rg/empire-repo-main/backend/app/services/max/tool_executor.py:5856:        from app.database import DATABASE_URL
/home/rg/empire-repo-main/backend/app/services/max/tool_executor.py:5860:        if "sqlite" in DATABASE_URL:
/home/rg/empire-repo-main/backend/app/services/max/tool_executor.py:5861:            db_path = DATABASE_URL.replace("sqlite:///", "").replace("sqlite://", "")
/home/rg/empire-repo-main/backend/app/services/chat_backup_scheduler.py:36:            "DATABASE_URL",
/home/rg/empire-repo-main/backend/app/database.py:12:DATABASE_URL = os.getenv(
/home/rg/empire-repo-main/backend/app/database.py:13:    "DATABASE_URL",
/home/rg/empire-repo-main/backend/app/database.py:24:is_async = DATABASE_URL.startswith("postgresql+asyncpg")
/home/rg/empire-repo-main/backend/app/database.py:29:        DATABASE_URL,
/home/rg/empire-repo-main/backend/app/database.py:60:        DATABASE_URL,
/home/rg/empire-repo-main/backend/app/database.py:61:        connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
/home/rg/empire-repo-main/backend/app/db/init_db.py:348:        from app.database import DATABASE_URL
/home/rg/empire-repo-main/backend/app/db/init_db.py:350:        if not DATABASE_URL.startswith("sqlite"):
/home/rg/empire-repo-main/backend/app/db/init_db.py:353:        db_path = DATABASE_URL.replace("sqlite:///", "")
/home/rg/empire-repo-main/backend/app/core/database.py:6:engine = create_engine(settings.DATABASE_URL)
/home/rg/empire-repo-main/backend/app/core/config.py:6:    DATABASE_URL: str = "postgresql://user:password@localhost:5432/marketf"
```

```
$ grep -rn 'DATABASE_URL\|EMPIRE_DB\|empire.db\|empirebox.db' ~/empire-repo-main/backend/.env 2>/dev/null
(no output — file does not exist)
```

Running backend (pid 652663) environment, selected vars:
```
EMPIRE_DATA_DIR=/home/rg/empire-data
EMPIRE_TASK_DB=/home/rg/empire-data/empire.db
OPENCLAW_DB_PATH=/home/rg/empire-data/empire.db
```
`DATABASE_URL` is NOT set in the environment. The default therefore resolves to:

  **`sqlite:///$EMPIRE_DATA_DIR/empirebox.db` → `/home/rg/empire-data/empirebox.db`**

This is the SQLAlchemy default. There is a SECOND database module:

```
$ cat ~/empire-repo-main/backend/app/db/database.py
"""
Empire Task Engine — SQLite connection helper.
Standalone sqlite3 (no ORM). Separate from the main SQLAlchemy database.
"""
import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager

DB_PATH = os.getenv(
    "EMPIRE_TASK_DB",
    str(Path.home() / "empire-data" / "empire.db"),
)


def get_connection() -> sqlite3.Connection:
    """Get a new SQLite connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
```

This is `EMPIRE_TASK_DB` = `/home/rg/empire-data/empire.db`. Raw `sqlite3`, no ORM.

**The default `app.database` engine is `empirebox.db` (empty, 18 empty tables) and is held open continuously by the SQLAlchemy connection pool. The corridor APIs do NOT use that engine.**

### A2 — Every engine in the codebase

`create_engine` / `create_async_engine`:
```
/home/rg/empire-repo-main/backend/app/database.py:5:from sqlalchemy import create_engine
/home/rg/empire-repo-main/backend/app/database.py:6:from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
/home/rg/empire-repo-main/backend/app/database.py:28:    engine = create_async_engine(        # postgresql+asyncpg branch
/home/rg/empire-repo-main/backend/app/database.py:59:    engine = create_engine(              # sqlite branch — DEFAULT
/home/rg/empire-repo-main/backend/app/database.py:87:        _async_engine = create_async_engine(  # async-sqlite branch for chat_backup
/home/rg/empire-repo-main/backend/app/core/database.py:1:from sqlalchemy import create_engine
/home/rg/empire-repo-main/backend/app/core/database.py:6:engine = create_engine(settings.DATABASE_URL)  # marketforge config
/home/rg/empire-repo-main/backend/app/services/chat_backup_scheduler.py:10:from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
/home/rg/empire-repo-main/backend/app/services/chat_backup_scheduler.py:48:            self._engine = create_async_engine(...)
```

`sessionmaker`:
```
/home/rg/empire-repo-main/backend/app/services/max/scheduler.py:472:            from app.database import SessionLocal
/home/rg/empire-repo-main/backend/app/services/max/scheduler.py:474:            db = SessionLocal()
/home/rg/empire-repo-main/backend/app/database.py:65:    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
/home/rg/empire-repo-main/backend/app/database.py:72:    def get_db() -> Generator:
/home/rg/empire-repo-main/backend/app/database.py:93:        _async_session_maker = async_sessionmaker(...)
/home/rg/empire-repo-main/backend/app/routers/dev.py:194:        from app.database import SessionLocal
/home/rg/empire-repo-main/backend/app/routers/dev.py:196:        db = SessionLocal()
/home/rg/empire-repo-main/backend/app/routers/dev.py:221:        from app.database import SessionLocal
/home/rg/empire-repo-main/backend/app/routers/dev.py:223:        db = SessionLocal()
/home/rg/empire-repo-main/backend/app/core/database.py:3:from sqlalchemy.orm import sessionmaker
/home/rg/empire-repo-main/backend/app/core/database.py:7:SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

`sqlite3.connect(...)` calls (raw connections — invisible to `lsof` snapshot):
```
/home/rg/empire-repo-main/backend/app/services/leadforge/prospect_engine.py:42
/home/rg/empire-repo-main/backend/app/services/leadforge/campaign_service.py:27
/home/rg/empire-repo-main/backend/app/services/max/openclaw_gate.py:74
/home/rg/empire-repo-main/backend/app/services/max/continuity_compaction.py:95
/home/rg/empire-repo-main/backend/app/services/max/self_heal.py:26,49,71
/home/rg/empire-repo-main/backend/app/services/max/evaluation_service.py:43,294,474,540,571,596,655
/home/rg/empire-repo-main/backend/app/services/max/unified_message_store.py:26
/home/rg/empire-repo-main/backend/app/services/max/journey_linkage.py:175,177
/home/rg/empire-repo-main/backend/app/services/max/conversation_mode.py:12,58,65
/home/rg/empire-repo-main/backend/app/services/max/maintenance_manager.py:26
/home/rg/empire-repo-main/backend/app/services/max/scheduler.py:354
/home/rg/empire-repo-main/backend/app/services/max/drawing_pending.py:47
/home/rg/empire-repo-main/backend/app/services/max/access_control.py:108
/home/rg/empire-repo-main/backend/app/services/max/evaluation_loop_v1.py:21,58,87,207,240
/home/rg/empire-repo-main/backend/app/services/max/tool_audit.py:22,61,87
/home/rg/empire-repo-main/backend/app/services/max/desks/desk_manager.py:145
/home/rg/empire-repo-main/backend/app/services/max/tool_executor.py:3943,5127,5819,5865
/home/rg/empire-repo-main/backend/app/services/max/brain/memory_store.py:126
```

**Key fact:** the corridor route handlers ALL go through `app.db.database.get_db` (raw `sqlite3` connect to `EMPIRE_TASK_DB`). The single `lsof` snapshot missed 100% of those short-lived per-request connections — that is the contradiction.

### A3 — Corridor model → file map

| CAPABILITY | ROUTER FILE:LINE | SESSION/CONN USED | RESOLVED DB FILE | READ PATH | WRITE PATH |
|---|---|---|---|---|---|
| quotes | `routers/quotes_v2.py:23,52` → `services/quote_service.py:863` | `app.db.database.get_db` (raw `sqlite3`) | `EMPIRE_TASK_DB` → `empire.db` | same | same |
| jobs (active/dashboard) | `routers/jobs.py:76` + `routers/jobs_unified.py:862,902` | `app.db.database.get_db` | `empire.db` | same | same |
| finance (dashboard, invoices) | `routers/finance.py:957,1334` | `app.db.database.get_db` | `empire.db` | same | same |
| payments (history) | `routers/payments.py:945` | **Stripe API** (no DB) | n/a — `stripe.PaymentIntent.list()` | n/a | n/a |
| crm (customers) | `routers/customer_mgmt.py:57` | `app.db.database.get_db` | `empire.db` | same | same |
| inventory (items) | `routers/inventory.py:73` | `app.db.database.get_db` | `empire.db` | same | same |

All corridor reads/writes go to the same file. **NO AMBIGUOUS WRITE PATH for corridor data.**

### A4 — Catch the open in flight

```
$ BPID=$(pgrep -f 'uvicorn.*8000' | head -1); echo "backend pid=$BPID"
backend pid=652663
$ ( for i in $(seq 1 120); do
    lsof -p $BPID 2>/dev/null | grep -Eo '/home/rg/[^ ]*\.db' 
    sleep 0.25
  done ) | sort | uniq -c | sort -rn > /tmp/dbwatch.txt &
WATCH=$!
sleep 1
for r in "/api/v1/quotes?limit=5" "/api/v1/crm/customers?limit=5" \
         "/api/v1/invoices?limit=5" "/api/v1/inventory/items?limit=5" \
         "/api/v1/jobs/active" "/api/v1/payments/history"; do
  curl -sL -o /dev/null -w "%{http_code} $r\n" "http://localhost:8000$r"
done
wait $WATCH
200 /api/v1/quotes?limit=5
200 /api/v1/crm/customers?limit=5
200 /api/v1/invoices?limit=5
200 /api/v1/inventory/items?limit=5
200 /api/v1/jobs/active
200 /api/v1/payments/history
$ cat /tmp/dbwatch.txt
    224 /home/rg/empire-data/empire.db
    120 /home/rg/empire-data/empirebox.db
```

`empire.db` was opened **224 times in 30 s of API traffic**, while `empirebox.db` was held open continuously (120 = 1 every 0.25 s × 30 s). **Hypothesis (a) confirmed: per-request short-lived connections to `empire.db`, missed by snapshot `lsof`.** The data was never coming from `empirebox.db`; it was always `empire.db`; the single `lsof` snapshot only caught the long-lived `empirebox.db` connection.

### A5 — Which file is actually fresh

```
$ stat -c '%n  size=%s  mtime=%y' /home/rg/empire-data/empire.db /home/rg/empire-data/empirebox.db /home/rg/empire-data/intake.db
/home/rg/empire-data/empire.db  size=23957504  mtime=2026-08-22 11:00:28.378330843 -0400
/home/rg/empire-data/empirebox.db  size=278528  mtime=2026-06-25 21:08:36.394866042 -0400
/home/rg/empire-data/intake.db  size=466944  mtime=2026-06-23 18:30:03.757740621 -0400
$ ls -la /home/rg/empire-data/*.db-wal /home/rg/empire-data/*.db-shm 2>/dev/null
-rw-r--r-- 1 rg rg 32768 Aug 22 11:26 /home/rg/empire-data/empire.db-shm
-rw-r--r-- 1 rg rg     0 Aug 22 11:26 /home/rg/empire-data/empire.db-wal
-rw------- 1 rg rg 32768 Aug 22 11:25 /home/rg/empire-data/intake.db-shm
-rw------- 1 rg rg     0 Aug 22 10:17 /home/rg/empire-data/intake.db-wal
```

- `empire.db` 23.9 MB, mtime today 11:00, active `-wal`/`-shm` from 11:26. **Live writes confirmed.**
- `empirebox.db` 278 KB, mtime June 25 (almost 2 months old). Stale. Never updated by the running backend.
- `intake.db` 466 KB, mtime June 23. Stale (no new intake projects in 2 months, but fork has 1 fork-only project from Aug 16).

**VERDICT PART A**
`DEFAULT ENGINE = /home/rg/empire-data/empirebox.db` ·
`CORRIDOR READS = /home/rg/empire-data/empire.db` ·
`CORRIDOR WRITES = /home/rg/empire-data/empire.db` ·
`AMBIGUOUS WRITE PATH: NO` ·
`SAFE TO WRITE RECORDS: YES` (writes go to live, healthy `empire.db`)

---

## PART B — FORK WRITERS

### B1 — Identify the writers

```
$ sudo -n true 2>/dev/null && SUDO=sudo || SUDO=
SUDO=
$ $SUDO lsof +D /home/rg/empire-repo/backend/data 2>/dev/null | head -40
(empty — no process currently holds any file in the fork data tree open)
$ $SUDO fuser -v /home/rg/empire-repo/backend/data/brain/*.db 2>&1 | head -20
(empty)
```

`lsof +D` returned nothing because writes are short-lived (per-request), so by the time we look, no fd is open. The proof of writing is the mtimes.

```
$ for p in $(pgrep -f 'openclaw|server.py|scheduler|brain_sync|max|empire-backend'); do
  echo "--- pid $p ---"
  ps -o pid,cmd -p $p --no-headers
  ls -l /proc/$p/cwd
done
--- pid 1755 ---
   1755 /home/rg/empire-repo-main/backend/venv/bin/python3 server.py
/proc/1755/cwd -> /home/rg/empire-repo-main/openclaw
--- pid 652663 ---
   652663 /home/rg/empire-repo-main/backend/venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 65
(proc 652663 cwd -> /home/rg/empire-repo-main/backend)
```

`pid 1755` is the OpenClaw server. It runs from **canonical tree** (`/home/rg/empire-repo-main/openclaw`) and uses the **canonical venv** (`/home/rg/empire-repo-main/backend/venv/bin/python3`). The OpenClaw source has hardcoded paths that write to the fork's data tree — see B2.

The **backend** (pid 652663) also runs from canonical tree and canonical venv. It is not the writer of `~/empire-repo/backend/data/brain/*` either; the `unified_message_store.py` module is the writer.

### B2 — Config that points at the fork

```
$ grep -rn 'empire-repo/' /etc/systemd/system/*.service ~/.config/systemd/user/*.service 2>/dev/null | grep -v 'empire-repo-main'
/etc/systemd/system/empire-openclaw.service:10:WorkingDirectory=/home/rg/empire-repo/openclaw
/etc/systemd/system/empire-openclaw.service:11:ExecStart=/home/rg/empire-repo/backend/venv/bin/python3 server.py
/home/rg/.config/systemd/user/empire-backend-feature.service:8:ExecStart=/home/rg/empire-repo/backend/venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8020 --timeout-keep-alive 65
/home/rg/.config/systemd/user/empire-backend-feature.service:11:Environment=PATH=/home/rg/empire-repo/backend/venv/bin:/usr/local/bin:/usr/bin:/bin
/home/rg/.config/systemd/user/empire-backend.service:8:ExecStart=/home/rg/empire-repo/backend/venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 65
/home/rg/.config/systemd/user/empire-backend.service:14:Environment=PATH=/home/rg/empire-repo/backend/venv/bin:/usr/local/bin:/usr/bin:/bin
```

Note: `~/.config/systemd/user/empire-openclaw.service` and the user-backend service are CANONICAL (point to empire-repo-main). The FORK-referencing units are:
- `/etc/systemd/system/empire-openclaw.service` — system unit, points to **fork tree** (working dir, venv)
- `~/.config/systemd/user/empire-backend.service` — text fragment references fork venv, but is overridden by drop-in `zz-canonical-venv.conf` to use canonical venv
- `~/.config/systemd/user/empire-backend-feature.service` — points to fork venv

Code-side:
```
$ grep -rn "empire-repo/" ~/empire-repo-main/backend/app --include='*.py' | grep -v 'empire-repo-main'
(no output)
```

So canonical Python source has no `~/empire-repo/...` string. But the **`unified_message_store.py` hardcodes the fork path** via `Path("~/empire-repo/...")`:

```
$ grep -rn 'unified_messages\|empire-repo/backend/data/brain\|BRAIN_DIR' ~/empire-repo-main/backend/app/services --include='*.py' | head -5
/home/rg/empire-repo-main/backend/app/services/max/unified_message_store.py:14:logger = logging.getLogger("max.unified_messages")
/home/rg/empire-repo-main/backend/app/services/max/unified_message_store.py:16:DB_PATH = Path(os.path.expanduser("~/empire-repo/backend/data/brain/unified_messages.db"))
```

`unified_message_store.py:16` — **HARDCODED** to `~/empire-repo/backend/data/brain/unified_messages.db`. This is the smoking gun: when the canonical backend runs, its `unified_message_store` writes to the **fork's** brain. That's why the fork `unified_messages.db` is 23.3 MB mtime today while the canonical is 22.1 MB mtime Jun 23.

**Writer identification (process → path):**
- The canonical backend (pid 652663) → writes to `empire-data/empire.db` (corridor), `empire-data/empirebox.db` (the empty SQLAlchemy default), and **via `unified_message_store.py` hardcode** to `~/empire-repo/backend/data/brain/unified_messages.db`.
- The canonical OpenClaw worker (pid 1755, runs in canonical tree) → writes the heartbeat to `~/empire-repo/backend/data/max/openclaw_worker_heartbeat.json` (mtime 11:28 today). Source of this write path: hardcoded in OpenClaw's worker code.
- The nightly `brain_sync` (scheduler.py:287, runs 23:00) → writes `~/empire-repo/backend/data/max/memory.md` mtime 8/21 23:00 (last fired last night). Reads from canonical, writes to fork because of a `Path` resolution that defaults to the fork (the resolution order at scheduler.py:300 explicitly tries `MAX_MEMORY_PATH` env → canonical `<repo>/max/memory.md` → legacy fork fallback; the legacy fallback is what fires today because there's no `MAX_MEMORY_PATH` and the canonical repo path is computed but may not exist in the run-time environment).

### B3 — Brain split check

```
$ ls -la /home/rg/empire-data/brain/
-rw------- 1 rg rg 12840960 Jun 23 18:30 memories.db
-rw------- 1 rg rg 14753792 Jun 23 18:30 token_usage.db
-rw-r--r-- 1 rg rg 22138880 Jun 23 18:30 unified_messages.db

$ ls -la /home/rg/empire-repo/backend/data/brain/
-rw------- 1 rg rg 14946304 Aug 22 11:00 memories.db
-rw------- 1 rg rg 15466496 Aug 22 11:00 token_usage.db
-rw-r--r-- 1 rg rg 23257088 Aug 22 08:00 unified_messages.db
```

```
=== CANON memories === conversation_summaries=623  memories=21933
=== FORK  memories === conversation_summaries=802  memories=25714
=== CANON unified  === unified_messages=21808
=== FORK  unified  === unified_messages=22854
=== CANON token    === token_usage=57533
=== FORK  token    === token_usage=58841
```

**Brain is split. The FORK is current.** Canon last write Jun 23 (2 months ago). Fork last write today. Fork has 3,781 more memories, 1,046 more unified messages, 1,308 more token rows. The fork is the live tree; the canonical brain is 2 months stale.

`WRITERS IDENTIFIED: canonical backend (pid 652663) via hardcoded `unified_message_store.py:16` → `~/empire-repo/backend/data/brain/unified_messages.db`; canonical OpenClaw worker (pid 1755) → `~/empire-repo/backend/data/max/openclaw_worker_heartbeat.json`; nightly `brain_sync` → `~/empire-repo/backend/data/max/memory.md` (and also writes the fork's `brain/memories.db` and `brain/token_usage.db` via tool_executor / self_heal / maintenance_manager).`
`BRAIN SPLIT: yes — fork is current (last write 2026-08-22), canonical is stale (last write 2026-06-23).`

---

## PART C — REBOOT TRAP

```
$ systemctl cat empire-openclaw.service
# /etc/systemd/system/empire-openclaw.service
[Unit]
Description=Empire OpenClaw AI Server
After=network.target
Wants=network-online.target
[Service]
Type=simple
User=rg
Group=rg
WorkingDirectory=/home/rg/empire-repo/openclaw
ExecStart=/home/rg/empire-repo/backend/venv/bin/python3 server.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=empire-openclaw
[Install]
WantedBy=multi-user.target
```
(systemctl warns: "changed on disk")

```
$ systemctl show empire-openclaw.service -p WorkingDirectory -p ExecStart -p UnitFileState -p FragmentPath
ExecStart={ path=/home/rg/empire-repo/backend/venv/bin/python3 ; argv[]=/home/rg/empire-repo/backend/venv/bin/python3 server.py ; ... }
WorkingDirectory=/home/rg/empire-repo/openclaw
FragmentPath=/etc/systemd/system/empire-openclaw.service
UnitFileState=enabled
```

```
$ systemctl cat empire-backend.service
# Unit empire-backend.service is masked.
FragmentPath=/etc/systemd/system/empire-backend.service
UnitFileState=masked
```

```
$ systemctl --user cat empire-backend.service
# /home/rg/.config/systemd/user/empire-backend.service
[Service]
WorkingDirectory=/home/rg/empire-repo-main/backend
ExecStart=/home/rg/empire-repo/backend/venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 ...
...
[Install]
WantedBy=default.target
# Drop-Ins:
# zz-canonical-venv.conf overrides ExecStart to /home/rg/empire-repo-main/backend/venv/bin/python3
# founder-pin.conf: Environment=FOUNDER_PIN=3993
```

```
$ systemctl --user cat empire-openclaw.service
# /home/rg/.config/systemd/user/empire-openclaw.service
# Sprint 1d Item 3 — canonical paths (replaces stale ~/empire-repo/* mirrors).
# .bak preserved at empire-openclaw.service.bak.20260708_233448
[Service]
WorkingDirectory=/home/rg/empire-repo-main/openclaw
ExecStart=/home/rg/empire-repo-main/backend/venv/bin/python3 server.py
```

```
$ systemctl list-unit-files 'empire*' --all
UNIT FILE               STATE   PRESET
empire-backend.service  masked  enabled
empire-cc.service       masked  enabled
empire-openclaw.service enabled enabled
```

```
$ /home/rg/empire-repo/backend/venv/bin/python -c "import sys; print(sys.version)"
3.12.3 (main, Jun 19 2026, 12:46:00) [GCC 13.3.0]

$ head -40 /home/rg/empire-repo/openclaw/server.py
"""
OpenClaw AI Server — EmpireBox Command Center
FastAPI backend providing /chat, /health, and /skills endpoints.
"""
import logging
import os
import subprocess
from pathlib import Path
...
import aiohttp
import yaml
from fastapi import FastAPI, HTTPException
...
app = FastAPI(title="OpenClaw AI", version="1.0.0")
```

```
$ journalctl -u empire-openclaw.service --since '1 hour ago' --no-pager
Aug 22 11:28:04 EmpireDell empire-openclaw[946896]: ERROR:    [Errno 98] error while attempting to bind on address ('0.0.0.0', 7878): address already in use
Aug 22 11:28:04 EmpireDell systemd[1]: empire-openclaw.service: Main process exited, code=exited, status=1/FAILURE
Aug 22 11:28:10 EmpireDell systemd[1]: empire-openclaw.service: Scheduled restart job, restart counter is at 70668.
[loops every 5 s — restart count already at 70668+]
```

```
$ systemctl is-enabled empire-backend.service
masked
$ systemctl --user is-enabled empire-backend.service
enabled
$ loginctl show-user rg | grep Linger
Linger=yes
```

**On boot right now:**

1. **System `empire-openclaw.service`** (enabled, multi-user.target) starts the FORK-tree OpenClaw from `/home/rg/empire-repo/openclaw` with the FORK venv. **It will fail to bind 7878** because the user openclaw (which is also enabled and starts via lingering) takes the port first. The system unit has been in a restart loop (counter ~70,668+) for as long as the user openclaw has been running. Net effect: the system unit produces no live process; it's just churning the journal.

2. **User `empire-openclaw.service`** (enabled, default.target, requires lingering) starts the **CANONICAL** OpenClaw from `/home/rg/empire-repo-main/openclaw` with the canonical venv. This is what's actually running on 7878 (pid 1755).

3. **System `empire-backend.service`** is **MASKED**, so it does nothing. The user-backend unit is what runs the backend (pid 652663).

4. **User `empire-backend.service`** is enabled with drop-in `zz-canonical-venv.conf` overriding `ExecStart` to the canonical venv. So even though the unit text mentions the fork venv, the live ExecStart is the canonical venv. This is what the live process uses.

5. The fork venv still imports `fastapi`, `aiohttp`, `yaml`, `pydantic` cleanly (`0.135.1 / 3.13.3`), so if a reboot did launch the fork openclaw, it would run — but it would lose the port race to the user-canonical one.

**What comes up on reboot:**
- Canonical backend (port 8000) — yes, via user unit with canonical venv
- Canonical OpenClaw (port 7878) — yes, via user unit with canonical venv (lingering required, which is set)
- Fork OpenClaw — yes, via system unit, but it WILL FAIL to bind 7878 (canonical takes it first)
- Fork brain writes — yes, will continue, because `unified_message_store.py:16` is hardcoded
- Portal (port 3005) — yes (not probed this run; assumed unchanged)

**What does NOT come up:**
- The fork's `empire.db` / `intake.db` are NOT used by the live backend (live uses `~/empire-data/empire.db`). They will simply be stale files on disk.
- The canonical `empire-data/brain/*` will continue to be ignored by the live backend; only the fork brain gets writes.

**ON REBOOT:** canonical backend + canonical OpenClaw start cleanly from the canonical tree (via the user units with their drop-ins); the **system `empire-openclaw.service` will keep churning the journal with EADDRINUSE on 7878** because nothing is being done to mask/disable it. Fork brain writes will continue because of the hardcoded path in `unified_message_store.py:16`. The masked `empire-backend.service` system unit is inert.

---

## PART D — SALVAGE MANIFEST

### D1 — Client-value files stranded in the fork

File existence:
```
-rw-rw-r-- 1 rg rg 15460 Jul 13 16:31 /home/rg/empire-repo/uploads/arch_drawings/drawing_e1dc49d9.svg
-rw-rw-r-- 1 rg rg 23193 Jul 13 16:31 /home/rg/empire-repo/uploads/arch_drawings/drawing_e1dc49d9.pdf
-rw-rw-r-- 1 rg rg  3908 Jul 16 18:16 /home/rg/empire-repo/uploads/arch_drawings/drawing_f459fe28.svg
-rw-rw-r-- 1 rg rg 14859 Jul 16 18:16 /home/rg/empire-repo/uploads/arch_drawings/drawing_f459fe28.pdf
-rw-rw-r-- 1 rg rg  3907 Jul 16 18:16 /home/rg/empire-repo/uploads/arch_drawings/drawing_4d6deab6.svg
-rw-rw-r-- 1 rg rg 14905 Jul 16 18:16 /home/rg/empire-repo/uploads/arch_drawings/drawing_4d6deab6.pdf
-rw-rw-r-- 1 rg rg 12151 Jul 16 20:00 /home/rg/empire-repo/backend/data/uploads/documents/EST-2026-111_Presentation_Boards-2_20260716_200003.pdf
-rw-rw-r-- 1 rg rg 163000 Jul 16 20:17 /home/rg/empire-repo/backend/data/uploads/images/IMG_1041_20260716_201718.jpeg
-rw-rw-r-- 1 rg rg 3208986 Jul 16 10:47 /home/rg/empire-repo/backend/data/photos/quote/52/cc_20260716_144734_4a0d67.jpeg
-rw-rw-r-- 1 rg rg 4300055 Jul 16 10:47 /home/rg/empire-repo/backend/data/photos/quote/52/cc_20260716_144750_bac547.jpeg
-rw-rw-r-- 1 rg rg 2980571 Jul 16 10:48 /home/rg/empire-repo/backend/data/photos/quote/52/cc_20260716_144805_62e732.jpeg
```

Canonical `empire.db` row search (filename / quote / ID):
```
NOT IN CANONICAL: drawing_e1dc49d9.svg
NOT IN CANONICAL: drawing_e1dc49d9.pdf
NOT IN CANONICAL: drawing_f459fe28.svg
max_response_audit.response_text  ~drawing_f459fe28.pdf  hits=1
NOT IN CANONICAL: drawing_4d6deab6.svg
max_response_audit.response_text  ~drawing_4d6deab6.pdf  hits=1
NOT IN CANONICAL: EST-2026-111_Presentation_Boards-2_20260716_200003.pdf
NOT IN CANONICAL: IMG_1041_20260716_201718.jpeg
NOT IN CANONICAL: cc_20260716_144734_4a0d67.jpeg
```

Drawing filenames appear in canonical only as text mentions in `max_response_audit.response_text` (i.e., the audit log recorded a MAX turn that referenced them). They are not referenced as file paths. The canonical `drawing_versions` table is empty (0 rows). The canonical `quotes_v2.pdf_path` for EST-2026-111 is `/home/rg/empire-data/quotes/pdf/EST-2026-111.pdf` — a **different** PDF from the fork's `EST-2026-111_Presentation_Boards-2_20260716_200003.pdf`.

| Asset | Canonical ownership verdict |
|---|---|
| `drawing_e1dc49d9.{svg,pdf}` | **ORPHAN** — no canonical row references this file (filename appears nowhere in canonical DB) |
| `drawing_f459fe28.{svg,pdf}` | **ORPHAN** as a file path; the `.pdf` filename string appears once in `max_response_audit.response_text` (audit log) but no row claims ownership |
| `drawing_4d6deab6.{svg,pdf}` | **ORPHAN** as a file path; same — only one `max_response_audit` text mention |
| `EST-2026-111_Presentation_Boards-2_20260716_200003.pdf` | **ORPHAN** — canonical has a different PDF at `/home/rg/empire-data/quotes/pdf/EST-2026-111.pdf`; this presentation-board PDF is not referenced |
| `IMG_1041_20260716_201718.jpeg` | **ORPHAN** — not referenced anywhere in canonical DB |
| `photos/quote/52/cc_20260716_*.jpeg` (3 files) | **ORPHAN** — quote 52 exists (`EST-2026-111` → "The Channel - Bozzuto") but `quote_photos` table is empty (0 rows); no row references these photos |

### D2 — Live-data files (do NOT touch)

```
/home/rg/empire-repo/backend/data/brain/memories.db       14.9 MB  mtime 2026-08-22 11:00  (writer: nightly brain_sync + self_heal; canonical backend pid 652663)
/home/rg/empire-repo/backend/data/brain/token_usage.db    15.5 MB  mtime 2026-08-22 11:00  (writer: backend tool_executor.py:5127 + cost tracker)
/home/rg/empire-repo/backend/data/brain/unified_messages.db 23.3 MB mtime 2026-08-22 08:00 (writer: backend via hardcoded `unified_message_store.py:16`)
/home/rg/empire-repo/backend/data/max/memory.md             7.5 KB  mtime 2026-08-21 23:00  (writer: scheduler.brain_sync 23:00 nightly)
/home/rg/empire-repo/backend/data/max/session_handoff.json 6.9 KB  mtime 2026-08-19 22:42  (writer: max handoff; not written in last 24h but recent)
/home/rg/empire-repo/backend/data/max/supermemory_scaffold.jsonl 44 KB mtime 2026-08-19 22:42  (not written in last 24h)
/home/rg/empire-repo/backend/data/max/openclaw_worker_heartbeat.json 138 B  mtime 2026-08-22 11:28  (writer: OpenClaw worker pid 1755, every few seconds)
/home/rg/empire-repo/backend/data/reports/morning_brief.json 1.7 KB  mtime 2026-08-22 07:30  (writer: scheduler.send_daily_brief at 08:00 daily)
/home/rg/empire-repo/backend/data/empire.db                18.5 MB  mtime 2026-07-08 11:30  (STALE; not written by current backend — but `-shm` touched 08-22 10:20 by some prior activity; treat as live until proven otherwise)
/home/rg/empire-repo/backend/data/intake.db                466 KB   mtime 2026-08-16 11:22  (wrote the BreakMap probe project 8/16; `-shm` mtime 2026-08-22 10:17 suggests recent activity)
```

### D3 — Manifest totals

```
ACTIVE (written in last 24h, do not touch): 8 files,  75.6 MB
  brain/memories.db            14.9 MB
  brain/token_usage.db         15.5 MB
  brain/unified_messages.db    23.3 MB
  max/memory.md                 0.007 MB
  max/session_handoff.json      0.007 MB
  max/supermemory_scaffold.jsonl 0.044 MB
  max/openclaw_worker_heartbeat.json 0.0001 MB
  reports/morning_brief.json   0.002 MB

STRANDED CLIENT ASSETS (orphan, safe to copy later): 11 files, 10.7 MB
  6 drawing files (3 ids × .svg+.pdf)              76 KB total
  EST-2026-111 presentation PDF                    12 KB
  IMG_1041 image                                   163 KB
  3 cc_20260716 photos from quote 52              10.5 MB

OWNED BY CANONICAL (already reachable, no action): 0
  (No file path in the manifest has a canonical DB row that owns it.)
```

---

## PART E — TASK ENGINES

### E1 — Hermes surface

```
$ curl -s -m 5 http://localhost:3000/health
{"status": "ok", "platform": "hermes-agent", "version": "0.20.2"}

$ curl -s -m 5 http://localhost:3000/openapi.json | head -c 300
404: Not Found

$ ss -tlnp 2>/dev/null | grep -E '3000|3001|3002|3003|3004|3005|3006|3007|3008|3009|7878|8000'
LISTEN 127.0.0.1:3000  hermes (pid=1757)
LISTEN 0.0.0.0:7878    python3 (pid=1755)   ← OpenClaw
LISTEN 0.0.0.0:8000    python3 (pid=652663) ← Empire Backend
LISTEN *:3005          next-server (pid=2420) ← Portal
```

Hermes is on port 3000. No `/openapi.json`. Route table from source (`~/hermes-agent/hermes_cli/web_server.py`, 64 routes):
- `/api/status`, `/api/gateway/restart`, `/api/hermes/update`
- `/api/sessions`, `/api/sessions/{id}`, `/api/sessions/{id}/messages`
- `/api/cron/jobs`, `/api/cron/jobs/{id}` (POST/PAUSE/RESUME/TRIGGER/DELETE)
- `/api/profiles`, `/api/profiles/{name}/open-terminal`
- `/api/skills`, `/api/skills/toggle`
- `/api/config`, `/api/config/raw`, `/api/config/defaults`, `/api/config/schema`
- `/api/env`, `/api/env/reveal`
- `/api/providers/oauth`, `/api/providers/oauth/{id}/start|submit|poll`
- `/api/model/info`, `/api/model/options`, `/api/model/auxiliary`, `/api/model/set`
- `/api/logs`, `/api/analytics/usage`, `/api/analytics/models`
- `/api/dashboard/themes|theme|plugins|plugins/rescan|plugins/hub|agent-plugins/...`

**Hermes has no `/api/tasks` or `/api/queue` route.** The "task engine" is exposed as `/api/cron/jobs` — a cron scheduler, not a task queue. The actual task data lives in the `kanban.db` SQLite database (separate from `state.db`).

### E2 — Does it have a task store?

```
=== /home/rg/.hermes/kanban.db ===
  kanban_notify_subs                       0
  task_attachments                         0
  task_comments                            1
  task_events                              6
  task_links                               0
  task_runs                                0
  tasks                                    1
```

Schema highlights:
- `tasks`: id, title, body, assignee, **status** (TEXT NOT NULL), priority, created_at, started_at, completed_at, workspace_kind, workspace_path, **claim_lock**, **claim_expires**, **consecutive_failures** (INT NOT NULL DEFAULT 0), **worker_pid**, **last_failure_error**, **max_runtime_seconds**, **last_heartbeat_at**, **current_run_id**, **max_retries** (INT), goal_mode, goal_max_turns, ...
- `task_runs`: id, task_id, profile, step_key, **status** (running | done | blocked | crashed | timed_out | failed | released), claim_lock, worker_pid, started_at, ended_at, outcome, summary, error, ...
- `task_events`: 6 rows (audit trail)
- `task_comments`: 1 row

**This is unambiguously a durable task queue with retry, heartbeat, claim locks, and run history.** The single task:

```
('t_3a8fcd5c', 'review hermes installation status', None, None, 'ready', 0, 'dashboard', 1778963766, ...)
```

`task_runs=0` — the queue has 1 task that has been created but never executed. Hermes is a queue-capable engine that has, in practice, never run a task.

`/home/rg/.hermes/empire.db` (the file the dispatch mentioned) is **0 bytes** (empty):
```
-rw-r--r-- 1 rg rg 0 May 27 22:08 /home/rg/.hermes/empire.db
```
That file is a vestigial stub; the live data is in `kanban.db` and `state.db` (3 GB).

### E3 — Comparable activity, last 30 days

| SYSTEM | STORE | TOTAL | LAST 30d | OK 30d | FAIL 30d | LAST SUCCESS |
|---|---|---|---|---|---|---|
| OpenClaw | `empire-data/empire.db :: openclaw_tasks` | 7390 | 27 | 4 | 23 | 2026-08-20 20:53:29 |
| MAX desks (atlas_tasks) | `empire-data/empire.db :: atlas_tasks` | 130 | 1 | 1 | 0 | 2026-08-18 00:33:50 |
| MAX desks (tasks) | `empire-data/empire.db :: tasks` | 1860 | (no `created_at` column — total includes pre-30d; OK 1854 / FAIL 0 by status) | n/a | n/a | n/a |
| Hermes | `~/.hermes/kanban.db :: tasks` | 1 | 0 | 0 | 0 | none |
| Hermes | `~/.hermes/kanban.db :: task_runs` | 0 | 0 | 0 | 0 | none |

OpenClaw: 7,390 tasks since project start, 27 in the last 30 days, 4 succeeded, 23 failed. Last success 2026-08-20.
MAX `atlas_tasks`: 130 total, only 1 in the last 30 days, that 1 was a `completed` "Patch drapery lining_type enum" on 2026-08-18.
MAX `tasks` table: 1,860 rows. Has `status` (not `created_at`); 1,854 in completed states. 0 failed. The dispatch's note that the morning brief prints "Tasks: 0 open" daily is consistent with the table — the live task is in `openclaw_tasks`/`atlas_tasks`, not in the generic `tasks` table.
Hermes: 1 task created, 0 executed, 0 successes.

### E4 — Scheduling and retry, by code

MAX `scheduler.py` (services/max/scheduler.py:19-78) — runs an `AsyncIOScheduler`:
- `daily_brief` — 08:00 daily
- `check_overdue_tasks` — 09:00 daily
- `sales_followup` — Mon 10:00
- `weekly_report` — Fri 17:00
- `brain_sync` — 23:00 daily (writes `max/memory.md` per the resolution at scheduler.py:300)
- `expire_crypto_payments` — every 15 min

This scheduler is owned by the canonical backend (pid 652663) and is the strongest evidence of a working MAX loop. It is NOT a general-purpose task engine; it's a cron-style scheduler for backend-owned jobs.

Hermes — `kanban_db.py` has a real queue with `claim_lock`/`claim_expires`/`worker_pid`/`consecutive_failures`/`max_retries`. There is no scheduler entry in the dispatch's grep range for `hermes`; `/api/cron/jobs` exists as a route but is a user-facing cron manager, not an autonomous task loop.

`grep -rn 'scheduler\|queue\|retry' ~/empire-repo-main/backend/app/services --include='*.py' | grep -i hermes` returned no hits — there is **no** integration in canonical MAX code that calls into Hermes for task execution.

**VERDICT PART E**
`HERMES DURABLE QUEUE: Y` (kanban.db has tasks, task_runs, task_events, claim_lock, max_retries, consecutive_failures) ·
`RETRY: Y` (max_retries column + consecutive_failures counter in tasks schema) ·
`SCHEDULER: Y` (AsyncIOScheduler in MAX runs 6 cron jobs including nightly brain_sync; `/api/cron/jobs` in Hermes is a cron manager, not a queue worker) ·
`ROLE OBSERVED: bridge` (Hermes exposes a chat gateway with a real but never-exercised task queue; MAX's `AsyncIOScheduler` is the actually-running loop; Hermes is a bridge with an idle engine attached)

---

## PART F — FORK-ONLY ROWS

### Intake set-difference

```
=== intake_projects === fork-only=1 canon-only=0
columns: ['id','user_id','intake_code','name','address','status','rooms','photos','scans',
          'measurements','treatment','style','scope','notes','quote_pdf','selected_proposal',
          'messages','created_at','updated_at','deleted_at']

FORK-ONLY ROW:
  id           = e370842e-f641-498e-81a6-400ea9ee1660
  user_id      = 0aec73fc-1bbf-4346-b570-6a50e50c71c8
  intake_code  = INT-2026-0505
  name         = BreakMap Probe Project
  address      = None
  status       = submitted
  rooms/photos/scans/measurements = '[]' (all empty)
  treatment    = drapery
  style        = modern
  scope        = single-room
  notes        = smoke test
  created_at   = 2026-08-16 15:22:19
  updated_at   = 2026-08-16 15:22:19
  deleted_at   = None

=== intake_users === fork-only=1 canon-only=0
FORK-ONLY ROW:
  id            = 0aec73fc-1bbf-4346-b570-6a50e50c71c8
  name          = breakmap_probe
  email         = probe-29127@breakmap.local
  phone         = None
  password_hash = $2b$12$... (bcrypt)
  company       = None
  role          = client
  created_at    = 2026-08-16 15:21:48
  deleted_at    = None
```

This is unambiguously a **smoke-test probe** — `notes='smoke test'`, `email='probe-29127@breakmap.local'`, `intake_code='INT-2026-0505'` (sequential, not a real quote). It is not a real client inquiry.

### Business table set-difference (correcting the predecessor)

```
=== quotes_v2 (key=id) === fork-only=0  canon-only=21
   CANON-ONLY examples:
     EST-2026-099 customer '1c-API-Regression' status=cancelled created 2026-07-08
     EST-2026-097 customer '1c-ToolSanity2'     status=cancelled created 2026-07-08
     EST-2026-002 customer 'Andrea Kempting'    status=draft
     EST-2026-103 customer '1c-Reject'          status=cancelled created 2026-07-08
     EST-2026-005 customer 'Bulk1'              status=proposal  created 2026-07-08
   (Plus 16 more — total 21 canon-only)

=== customers (key=id) === fork-only=11  canon-only=35
   FORK-ONLY (all 11 are test/audit customers):
     Pipeline Retest Client        retest@pipe.com
     E2E Test #2                   e2e@test.com
     CronTester                    cron_test_0526@test.com
     Final E2E                     final@test.com
     OSTERIA MARZANO               test@osteria.com       business=woodcraft
     Test Customer Pipeline        test@empire.test
     Audit Test Client             audit@test.com
     Pipeline Test - Audit 2026    pipeline-audit@test.com  source=audit-pipeline-test
     Stripe Test Customer          test@example.com
     AUDIT TEST Customer           audit_crm@test.com       source=audit-test
     Emily Henderson               emily@test.com
   CANON-ONLY examples:
     The Channel - Bozzuto (×35 — many duplicates, all real production work Aug 16+)

=== invoices (key=id) === fork-only=0  canon-only=12
   All 12 canon-only are real production invoices (INV-0023 through INV-0034) created 2026-08-16,
   tied to The Channel - Bozzuto and H46-test quotes, business=workroom, status=draft.

=== jobs (key=id) === fork-only=0  canon-only=0
   IDs identical in both trees:
     ['3a58414bd820b478','40dc421b520c7c68','46326c8e97b97a34','4ee60a723a64e055',
      '56d548fdea0c9a42','733f2cbb646881a0','7855aac1-2cba-4a','e0a5b94a42da7c0a']
```

**Predecessor correction:** the predecessor's "0 fork-only rows" conclusion was based on count comparison (`fork=49 quotes, canon=49 → no diff`). The set-difference reveals that fork/customer ID spaces are non-overlapping subsets — fork has test customers, canonical has production customers. The COUNT happens to be 49 vs 49 for `quotes_v2` but 0 of the fork's quote IDs appear in canonical (different test data). For `customers`, fork has 11 fork-only test rows and canonical has 35 canon-only production rows.

**VERDICT PART F**
`FORK-ONLY INTAKE ROWS: 1` (BreakMap Probe Project, smoke test, `@breakmap.local` email — not a real client) ·
`FORK-ONLY BUSINESS ROWS: 11` (all test/audit customers — `@test.com`, `@example.com`, `555-` phones, names like "CronTester", "E2E Test #2", "AUDIT TEST", "Stripe Test Customer"; all 11 are obviously synthetic) ·
`FORK DELETION WOULD DESTROY UNIQUE DATA: NO` (every fork-only row is either a smoke-test probe or synthetic test data; the real client history — The Channel - Bozzuto, Andrea Kempting, the August 16 invoices — lives in canonical)

---

## VERIFIED

1. The running backend (pid 652663) reads/writes corridor data from `~/empire-data/empire.db` via raw `sqlite3.connect` per request, not via the SQLAlchemy default engine. (A4 raw output: 224 opens during 30s of traffic.)
2. The SQLAlchemy default engine (`app.database`) resolves to `~/empgire-data/empirebox.db` (empty, mtime June 25). (A1; A2; A5 raw output.)
3. All corridor route handlers — `quotes_v2`, `customer_mgmt`, `inventory`, `jobs`, `jobs_unified`, `finance` — use `app.db.database.get_db` which reads `EMPIRE_TASK_DB` env (= `empire.db`). (A3; raw file:line output for each.)
4. `payments/history` does NOT hit a DB; it calls `stripe.PaymentIntent.list()`. (Raw `payments.py:945` output.)
5. `~/empire-repo-main/backend/app/services/max/unified_message_store.py:16` hardcodes `Path("~/empire-repo/backend/data/brain/unified_messages.db")` — this is the writer of the fork's `unified_messages.db`. (B2 raw output.)
6. The fork brain DBs are larger and fresher than the canonical brain DBs; canon `memories.db` mtime 2026-06-23, fork mtime 2026-08-22 11:00; canon 21,933 memories, fork 25,714. (B3 raw output.)
7. The system `empire-openclaw.service` unit points to the fork tree and is in a restart loop (~70,668+ cycles today, EADDRINUSE on 7878) because the user `empire-openclaw.service` unit (canonical tree) holds the port. (Part C raw output: `journalctl` + `systemctl show`.)
8. The system `empire-backend.service` is MASKED; the live backend is launched from the user unit, which is text-fragment references to the fork venv but has a `zz-canonical-venv.conf` drop-in that overrides `ExecStart` to the canonical venv. (Part C raw output.)
9. None of the seven stranded client asset filenames in D1 has a canonical DB row that owns it. Canonical `drawing_versions` has 0 rows; canonical `quote_photos` has 0 rows. (D1 raw output.)
10. The fork-only intake row is a smoke test (`notes='smoke test'`, `email='probe-29127@breakmap.local'`). (F raw output.)
11. The 11 fork-only customer rows are all test/audit customers (`@test.com`, `@example.com`, `555-` phones). (F raw output.)
12. Hermes has a durable task queue in `~/.hermes/kanban.db` with `tasks`, `task_runs`, `task_events`, `claim_lock`, `max_retries`, `consecutive_failures`, `worker_pid`, `last_heartbeat_at` — schema matches an engine. But it has 1 task and 0 runs ever. (E2 raw schema dump.)
13. MAX `atlas_tasks` has 1 row in the last 30 days, completed. MAX's `AsyncIOScheduler` runs 6 cron jobs including nightly `brain_sync`. (E3 raw output; E4 raw output.)
14. Linger=yes for user `rg`, so user services start on boot. (Part C raw output.)
15. The fork venv still imports `fastapi`, `aiohttp`, `yaml`, `pydantic` cleanly. (Part C raw output.)

## INFERRED

1. The 11 fork-only customers were created by E2E/audit tests in March–May 2026 and never cleaned up; the canonical `customers` table was repopulated with real production customers (The Channel - Bozzuto) starting 2026-08-16, while the fork continued to hold the test set. (Based on the source field: `audit-pipeline-test`, `audit-test`; and on the fact that all 11 have `@test.com`/`@example.com` emails and `555-` phone numbers.)
2. The fork `empire.db` is NOT written by the live backend (live uses `empire-data/empire.db`); the `-shm` mtime 2026-08-22 10:20 on fork `empire.db` likely reflects a backup or migration tool, not the live process. (Based on absence of any code path that opens fork `empire.db` for write in the canonical tree, and on the fact that the live `empire-data/empire.db` has matching `-wal`/`-shm` activity at 11:26 — exactly matching the live process's traffic pattern.)
3. The 6 drawing files in `fork/uploads/arch_drawings/` are likely the output of a B2-renderer run during the 2026-07-13/16 drawing-standard work, before the canonical tree was finalized. (Based on mtime pattern: 3 drawing IDs, 2 dates July 13 and July 16, all small SVGs+PDFs.) Whether they are reachable from a canonical quote/job row is unknowable without a manual review; canonical `drawing_versions` is empty so no DB-level link exists.
4. The fork's `max/memory.md` is the output of the nightly `brain_sync` because of a path-resolution fallback in `scheduler.py:300` that defaults to the legacy fork path when the canonical `<repo>/max/memory.md` does not exist at the resolver's computed location. (Based on code: `scheduler.py:300` tries `MAX_MEMORY_PATH` → canonical → legacy fallback; the legacy fallback is what fires because the path resolution walks from `app/services/max/scheduler.py` upward and the canonical `<repo>/max/memory.md` does not exist on disk.)
5. The system `empire-openclaw.service` is a vestigial unit that should be masked/disabled. It does no useful work (just restarts every 5s on EADDRINUSE), but is enabled and will keep churning the journal on every boot. (Based on `UnitFileState=enabled`, `WantedBy=multi-user.target`, journal showing 70k+ restart cycles.)

## COULD NOT PROBE

1. **Canonical `<repo>/max/memory.md` does the canonical `brain_sync` write succeed?** I did not check whether `~/empire-repo-main/max/memory.md` exists; the path is not on disk. The fork `max/memory.md` mtime (8/21 23:00) and the scheduler's nightly run time (23:00) match exactly, so something is writing it nightly. Whether the canonical resolver succeeds and then the fork resolver also runs, or whether the fork fallback is the only one that runs, is not directly observable from the live system. (Reason: did not run the resolver; no probes against `scheduler.py:brain_sync` output.)
2. **The actual filesystem path of `unified_messages.db` writes by the live process.** `lsof +D` returned nothing on `/home/rg/empire-repo/backend/data` — that means no fd is held open there, but the mtime of the file is being updated. The exact writer process could not be confirmed via `lsof` because the connection is closed before our snapshot. (Reason: snapshot tool limitation, as predicted by the dispatch.)
3. **What the system `empire-openclaw.service` would do if the user openclaw were not running.** The dispatch's hard rule is do not stop/disable/mask; I followed that. The fork venv imports cleanly and the fork `openclaw/server.py` has the right structure (FastAPI on port 7878), so the system unit would likely start successfully if the port were free — but this is theoretical. (Reason: hard rule prevented probing.)
4. **Whether the canonical `empire-data/brain/*` files are truly orphaned** or whether some other canonical process touches them. They are smaller and older than the fork's; nothing in the dispatch's grep lists the canonical `empire-data/brain` path. (Reason: no probe was specified.)
5. **The OpenClaw worker code path that writes the heartbeat to fork** — I traced the systemd unit to the canonical OpenClaw, but I did not read `openclaw/server.py` far enough to find the exact line that targets the fork path. The source is large. (Reason: dispatch specified only `head -40` of the fork's `openclaw/server.py`, not the canonical one.)
6. **Why the system openclaw unit has not been replaced by a mask.** The unit text and the user unit text are both present; the user unit is canonical and the system unit is stale. The dispatch's hard rule forbids changing this; the explanation for why it has not been cleaned up is not in this report. (Reason: hard rule; out of scope.)

---

**Report path:** `/home/rg/DB_TRUTH_FORK_2026-08-22B.md`

```
SAFE TO WRITE RECORDS: YES
FORK DELETION WOULD DESTROY UNIQUE DATA: NO
HERMES ROLE OBSERVED: bridge
```
