# Test isolation: the live-data firewall (2026-10-04)

Tests must never touch Rafael's live data. The pytest suite in `backend/tests/`
enforces this every time it runs. There's no opt-out marker.

## Why
Shells that had the backend env loaded (`set -a; . ~/.config/empirebox/empire-backend.env`)
exported `EMPIRE_DATA_DIR` / `EMPIRE_TASK_DB` / `EMPIRE_DB_PATH` = `~/empire-data/...`.
The old `tests/conftest.py` used `os.environ.setdefault(...)`, so the live value won.
`EMPIRE_DATA_DIR` and `EMPIRE_BRAIN_DIR` were never redirected at all, and
`unified_message_store` defaults to `~/empire-data/brain`. Test chats leaked into
`unified_messages`, chat JSON files and the journals.

`~/.bashrc` / `~/.profile` don't export these variables. Only the backend's
systemd units (via their env file) and shells that sourced that file have them.
The units are unchanged and keep using live data.

## What runs on every pytest invocation (`backend/tests/conftest.py` + `_live_data_guard.py`)
1. **Forced temp env** (never `setdefault`). These all go to a per-run `mkdtemp` tree:
   `EMPIRE_DATA_DIR` (so everything resolved through `data_paths.data_root()` lands in temp),
   `EMPIRE_BRAIN_DIR`, `EMPIRE_TASK_DB`, `EMPIRE_DB_PATH`, `EMPIRE_DB`, `EMPIRE_PHOTOS_DIR`,
   `EMPIRE_MAX_JOURNAL_DB`, `EMPIRE_MAX_JOURNAL_ARCHIVE`, `MAX_MEMORY_PATH`, `OPENCLAW_DB_PATH`,
   `COST_TRACKER_DB`, `MAX_IMPROVE_SPEC_DIR`, `VOICE_DOC_SESSIONS_PATH` and `CHAT_BACKUP_DIR`.
   Any other env var whose value points into a live root goes there too. A live
   `EMPIRE_E2E_BASE_URL` is unset.
2. **Fail fast**: `assert_isolated()` refuses to collect a single test if any
   `EMPIRE_*` / `MAX_*` / `OPENCLAW_*` path still resolves live.
3. **Audit-hook firewall** (`sys.addaudithook`, also loaded in Python subprocesses
   through a generated `sitecustomize` on `PYTHONPATH`):
   - HARD roots, where any open/sqlite/mkdir/remove/rename/chmod is refused: `~/empire-data`, `/data/amp`, `/data/maxine`.
   - SOFT roots, where reads are allowed and writes/new dirs/sqlite are refused:
     `<repo>/backend/data`, `~/empire-repo/backend/data`, `<repo>/max/memory.md`.
   A file/sqlite refusal raises `PermissionError("LIVE_DATA_VIOLATION ...")`. It also fails
   the test (even if the code under test swallowed the error) and fails the session.
   - TCP connects to the live services on localhost ports 8000/8011/8012/3005/3011/3012/7878
     (backend, portal, family editions, OpenClaw) are blocked too. The code under test gets an
     ordinary `ConnectionRefusedError` ("LIVE_SERVICE_BLOCKED"), so it acts as if the service
     were down. The same goes for this host's own LAN/Tailscale addresses on 80/443/8443, and
     for DNS lookups of `*.empirebox.store`, `*.empirebox.com` and `*.ts.net` (public tunnel /
     tailnet routes into the live services). These blocks are logged and summarised at session
     end. On their own they don't fail a test, because they're mostly harmless health probes.
   - **Live journal watch**: the live `~/empire-data/brain/max_session_journal.db` (+ `-wal`) is
     fingerprinted with `stat` (size, mtime, inode; the file is never opened) at conftest load and
     again at session end. Any change marks the run failed and names the file, even if another
     process (e.g. the live backend serving real traffic) wrote it.
4. **Temp mirrors** for paths captured at import time: UPPER_CASE module constants and
   function default arguments in `app.*` and test modules that hold live paths are
   rewritten to `<tmp>/mirror/<hash>/<name>`. This also covers lazy imports, through a `meta_path` shim.
   `sqlite3.connect` / `os.chmod` targets under live roots are translated to the same mirrors.
   Soft-root files (e.g. the frozen `~/empire-repo/backend/data/empire.db` snapshot
   the journey tests read) are **copied** into the mirror. Hard-root paths are never read, not even to copy.
5. After every test, the isolated data env vars and `app.db.database.DB_PATH` are put
   back, then re-checked with `assert_isolated()`. Some tests set `EMPIRE_TASK_DB` or
   reload the DB module against their own tmp DB and never restore it, which used to
   leave later tests on a stale DB.
6. The temp tree is deleted at session end. Set `EMPIRE_TEST_KEEP_TMP=1` to keep it.

Self-tests: `backend/tests/test_live_data_firewall.py`.

## Limits
- Non-Python subprocesses (node, sqlite3 CLI, curl) aren't hooked. They do inherit the
  redirected env.
- `live_db` / `e2e_live` tests can no longer reach live data or live ports. Run those
  checks by hand against a staging copy if needed.
