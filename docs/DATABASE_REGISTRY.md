# EmpireBox Database Source-of-Truth Registry

> **Status**: Audited 2026-05-02 — No changes made. Read-only record.

---

## 1. Executive Verdict

**Empire currently has dual SQLite DB usage.** The runtime architecture splits data across two SQLite files per backend instance:

| DB | Role | SQLAlchemy-managed |
|----|------|--------------------|
| `backend/empirebox.db` | SQLAlchemy default; contains licenses, shipments, preorders, listings, marketplace, chat_sessions, chat_messages, crypto_payments | Yes |
| `backend/data/empire.db` | MAX/OpenClaw/business runtime; task queues, desk configs, CRM data, campaign data, MAX response audit/evaluations, OpenClaw task queue | No (direct sqlite3) |

Both backends (live port 8000, v10 port 8010) open `empirebox.db` via SQLAlchemy at runtime. However, all active business/MAX/OpenClaw writes use direct sqlite3 connections to hardcoded `backend/data/empire.db` absolute paths.

---

## 2. Live Backend DB Map

**Backend root**: `~/empire-repo/backend/`

### Primary Runtime DBs

| Path | Size | Last Modified | Purpose |
|------|------|---------------|---------|
| `empirebox.db` | 304 KB | 2026-04-25 (7 days stale) | SQLAlchemy ORM — licenses, shipments, preorders, listings, marketplace, chat backup tables |
| `data/empire.db` | 5.0 MB | 2026-05-02 20:10 (today) | **Canonical runtime** — MAX/OpenClaw/task queue, business data, CRM, campaigns, MAX response audit |

### Secondary DBs

| Path | Size | Last Modified | Purpose |
|------|------|---------------|---------|
| `data/intake.db` | 69 KB | 2026-04-29 | Client intake flow data |
| `data/amp.db` | 131 KB | 2026-03-22 | AMP (Agent Management Platform) data |
| `data/token_usage.db` | 32 KB | 2026-03-08 | Token usage tracking |
| `data/tool_audit.db` | 144 KB | 2026-05-01 | Tool audit logs |
| `data/brain/memories.db` | 0 KB | 2026-04-02 | Brain/memory system (empty) |
| `data/brain/unified_messages.db` | — | — | Brain unified messages (if present) |

### Backup DBs (in `data/backups/`)

- `empire_backup_prelaunch_20260322.db` (1.2 MB)
- `empire_backup_launch_eve_20260323_2254.db` (1.3 MB)
- `empire_backup_20260324_1322.db` (1.4 MB)
- `empire_backup_20260324_1347.db` (1.4 MB)
- `empire_pre_unified_20260404_1746.db` (3.0 MB)
- `empire.db.bak.20260318_151258` (1.0 MB)

### Live empirebox.db — Table Inventory (20 tables)

All tables have 0 rows except:
- `crypto_payments`: 2 rows
- `luxeforge_image_measurements`: 1 row
- `shipments`: 1 row

**Conclusion**: `empirebox.db` is stale — last active writes ~Apr 25. Active data lives in `data/empire.db`.

### Live data/empire.db — Key Tables (125 tables, 67 non-empty)

| Table | Rows | Purpose |
|-------|------|---------|
| `openclaw_tasks` | 62 | OpenClaw task queue |
| `tasks` | 667 | Task system |
| `task_activity` | 349 | Task event log |
| `max_response_audit` | 1,217 | MAX response audit trail |
| `max_response_evaluations` | 140 | MAX quality evaluations |
| `atlas_tasks` | 22 | Atlas task desk |
| `prospects` | 322 | Prospect pipeline |
| `customers` | 146 | CRM customers |
| `inventory_items` | 155 | Inventory |
| `quotes_v2` | 28 | Quotes system |
| `quotes_line_items` | 83 | Quote line items |
| `desk_configs` | 15 | MAX desk configurations |
| `campaigns`, `campaign_steps`, `campaign_activity` | 3/13/20 | Campaign system |
| `business_profiles` | 2 | Business config |
| `access_users` | 5 | Access control |

---

## 3. V10 Backend DB Map

**Backend root**: `~/empire-repo-v10/backend/`

| Path | Size | Last Modified | Purpose |
|------|------|---------------|---------|
| `empirebox.db` | 88 KB | 2026-04-30 (2 days stale) | SQLAlchemy ORM — chat backup, luxeforge measurements; all tables empty |
| `data/empire.db` | 700 KB | 2026-05-02 22:24 (today) | **Canonical runtime** — desk_configs, campaign data, MAX audit |

### V10 data/empire.db — Key Tables (60 tables, 13 non-empty)

| Table | Rows | Purpose |
|-------|------|---------|
| `desk_configs` | 15 | MAX desk configs |
| `campaign_steps` | 13 | Campaign steps |
| `campaigns` | 3 | Campaigns |
| `max_response_audit` | 50 | MAX audit |
| `max_response_evaluations` | 34 | MAX evaluations |
| `max_routing_preferences` | 5 | Routing prefs |
| `access_users` | 1 | Access users |
| `business_profiles` | 2 | Business profiles |
| `ra_services` | 16 | Services registry |
| `fabrics` | 6 | Fabric data |

### V10 empirebox.db — All tables empty (0 rows)

5 tables: `chat_messages`, `chat_sessions`, `decision_contexts`, `disruption_events`, `luxeforge_image_measurements` — all 0 rows.

---

## 4. Current Source-of-Truth Finding

### Canonical Runtime DB

**`backend/data/empire.db`** is the active runtime database for both live and v10.

Evidence:
- Last modified: **today** (2026-05-02) for both live and v10
- Contains all active business data: task queues, OpenClaw tasks, MAX response audit, CRM, campaigns, desk configs
- Live `data/empire.db` openclaw_tasks: **62 rows** — confirmed by `GET /api/v1/openclaw/tasks/stats` returning `total: 62`
- V10 `data/empire.db` openclaw_tasks: **0 rows** — confirmed by v10 endpoint returning `total: 0`

### SQLAlchemy Default DB

**`backend/empirebox.db`** is the SQLAlchemy-managed default (`DATABASE_URL = "sqlite:///./empirebox.db"`) but appears stale:

- Live: last modified Apr 25 (7 days ago), all tables near-empty
- V10: last modified Apr 30 (2 days ago), all tables empty
- No active writes occurring despite being the SQLAlchemy default

### Dual-DB Architecture

The codebase has a split-personality DB design:

1. **SQLAlchemy ORM** (via `DATABASE_URL` / `app/database.py`) → `empirebox.db`
   - Uses: FastAPI routers that use SQLAlchemy models (licenses, shipments, preorders, listings, marketplace, chat backup)
   - Relative path `sqlite:///./empirebox.db` → resolves to `backend/empirebox.db` at runtime

2. **Direct sqlite3** (via hardcoded absolute paths) → `data/empire.db`
   - Uses: OpenClaw worker, MAX router, MAX desk manager, MAX tool executor, construction router, storefront router, MAX maintenance manager, self-heal
   - Hardcoded: `os.path.expanduser("~/empire-repo/backend/data/empire.db")`

---

## 5. Code/Config References

### DATABASE_URL / SQLAlchemy (→ empirebox.db)

**`backend/app/database.py:12`**
```python
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./empirebox.db")
```
Default is relative path `empirebox.db`, resolved from process CWD.

**`backend/.env.example:6`**
```
DATABASE_URL=sqlite:///./empirebox.db
```

### Direct sqlite3 Hardcoded Paths (→ data/empire.db)

| File | Line | Path |
|------|------|------|
| `app/services/openclaw_worker.py` | 26 | `DB_PATH = os.path.expanduser("~/empire-repo/backend/data/empire.db")` |
| `app/routers/max/router.py` | 110 | `db_path = os.path.expanduser("~/empire-repo/backend/data/empire.db")` |
| `app/routers/max/router.py` | 3444 | `db_path = os.path.expanduser("~/empire-repo/backend/data/empire.db")` |
| `app/services/max/desks/desk_manager.py` | 144 | `db_path = os.path.expanduser("~/empire-repo/backend/data/empire.db")` |
| `app/services/max/tool_executor.py` | 3084 | `db_path = os.path.expanduser("~/empire-repo/backend/data/empire.db")` |
| `app/services/max/tool_executor.py` | 4341 | `db_path = os.path.expanduser("~/empire-repo/backend/data/empire.db")` |
| `app/services/max/conversation_mode.py` | 9 | `DB_PATH = os.path.expanduser("~/empire-repo/backend/data/empire.db")` |
| `app/services/max/maintenance_manager.py` | 20 | `DB_PATH = os.path.expanduser("~/empire-repo/backend/data/empire.db")` |
| `app/services/max/self_heal.py` | 8 | `DB_PATH = os.path.expanduser("~/empire-repo/backend/data/empire.db")` |
| `app/routers/construction.py` | 20 | `DB_PATH = os.path.expanduser("~/empire-repo/backend/data/empire.db")` |
| `app/routers/storefront.py` | 21 | `DB_PATH = os.path.expanduser("~/empire-repo/backend/data/empire.db")` |
| `app/routers/presentations.py` | 13 | `DB_PATH = os.path.expanduser("~/empire-repo/backend/data/empire.db")` |

### Tool Executor Dual Path Logic

`app/services/max/tool_executor.py` (lines ~4940) has fallback logic:
```python
from app.database import DATABASE_URL
if "sqlite" in DATABASE_URL:
    db_path = DATABASE_URL.replace("sqlite:///", "").replace("sqlite://", "")
```
This uses SQLAlchemy's DATABASE_URL when available, otherwise falls back to the hardcoded path.

---

## 6. Backup Record

**Backup location**: `~/empire-db-backups/20260502_223356/`

**Files backed up** (2026-05-02 22:33:56 UTC):
- `live-data-empire.db` — 5.0 MB (live canonical runtime DB)
- `live-empirebox.db` — 304 KB (live SQLAlchemy default DB)
- `v10-data-empire.db` — 700 KB (v10 canonical runtime DB)
- `v10-empirebox.db` — 88 KB (v10 SQLAlchemy default DB)

**No DB changes were made** during the audit. All investigation was read-only sqlite3 queries.

---

## 7. Risk

### Active Risks

1. **Write split**: Future code that uses SQLAlchemy models will write to `empirebox.db`. If empirebox.db continues to be stale, these writes may be lost or create orphaned data.

2. **Wrong DB in migrations**: Migrations targeting `DATABASE_URL` will hit `empirebox.db`, not the active runtime data in `data/empire.db`.

3. **Live/v10 separation**: V10 `data/empire.db` has 700KB / 13 non-empty tables vs live's 5.0MB / 67 non-empty tables. V10 is a development/test lane with its own subset of data.

4. **empirebox.db is not a backup**: It is a secondary SQLAlchemy-managed DB, not a snapshot of the canonical DB.

### Do NOT

- Do NOT delete `backend/empirebox.db` yet — it may contain data for some SQLAlchemy-managed features not yet audited
- Do NOT change `DATABASE_URL` env var yet — this could break SQLAlchemy-managed features that do write
- Do NOT assume `data/empire.db` and `empirebox.db` will stay in sync — they are independent SQLite files

---

## 8. Recommendation

**No DB path changes until formal consolidation plan is approved.**

The canonical runtime DB is `backend/data/empire.db` (verified by live openclaw/tasks/stats API returning 62 tasks matching the 62 rows in `data/empire.db`). The SQLAlchemy default `empirebox.db` appears to be legacy/stale.

Before any changes:
1. Audit which SQLAlchemy models actually write data
2. Determine if empirebox.db has any non-empty tables that matter
3. Decide consolidation target (should everything go to `data/empire.db`? Should SQLAlchemy migrate to `data/empire.db`?)

---

## 9. Future Consolidation Plan

### Phase A — Inventory SQLAlchemy Routes/Models
- Find all SQLAlchemy ORM models (files using `Base`, ` declarative_base`)
- Identify which models write data to empirebox.db
- Confirm if empirebox.db's non-empty tables (licenses, shipments, preorders, crypto_payments) need to remain accessible

### Phase B — Inventory Direct sqlite3 Users
- Audit all direct `sqlite3.connect()` calls that use hardcoded paths
- Check if any should migrate to SQLAlchemy ORM for consistency
- Identify any DB paths that could be parameterized instead of hardcoded

### Phase C — Decide Canonical DB
- Option 1: Consolidate all to `data/empire.db` (move SQLAlchemy there, deprecate empirebox.db)
- Option 2: Keep dual-DB but document clearly, ensure empirebox.db is actively maintained
- Option 3: Migrate direct sqlite3 users to SQLAlchemy, deprecate direct connections

### Phase D — Full Backup
- Already done at `~/empire-db-backups/20260502_223356/`
- Additional full backup before any migration

### Phase E — Test Migration in V10 Only
- Update v10 DATABASE_URL to point to v10 `data/empire.db` path
- Run v10 test suite and manual validation
- Verify all v10 endpoints work with consolidated DB

### Phase F — Verify Endpoints
- `GET /api/v1/openclaw/tasks/stats` → should return same as v10 `data/empire.db` openclaw_tasks count
- `GET /api/v1/max/status` → should return healthy
- `GET /health` → should return healthy
- Other critical endpoints per feature team

### Phase G — Then Consider Live
- Apply same consolidation to live after v10 validation
- No live changes until v10 proves the pattern