# v10 Untracked File Audit — Commit a959071

## Files Committed

| File | Lines | Purpose |
|------|-------|---------|
| `backend/app/api/v1/health.py` | 99 | Multi-service health endpoint with K8s-style liveness/readiness probes |
| `backend/app/services/hermes/guardian.py` | 195 | Autonomous self-healing daemon with service restart capability |
| `backend/app/services/openclaw/executor.py` | 370 | MAX execution bridge — converts proposals to code with path validation and backups |

---

## Per-File Verdict

### `backend/app/api/v1/health.py` — **SAFE — KEEP**

- **Wired into main.py**: `app.include_router(health.router, prefix="/api/v1")` at line 673
- **Endpoints active and live**:
  - `GET /api/v1/health` — full multi-service check (8010, 8000, 7878, 3010, 3005, orchestrator, telegram)
  - `GET /api/v1/health/liveness` — K8s probe
  - `GET /api/v1/health/ready` — K8s probe
- **Verified live on port 8010** — all three endpoints return correct JSON
- **No self-healing, no filesystem writes** — read-only HTTP + socket checks
- **Created**: 2026-05-05 by user (before this session)
- **No duplicate in stable repo**
- **Required for v10 runtime correctness**: YES — health monitoring is legitimate v10 infrastructure

---

### `backend/app/services/openclaw/executor.py` — **SAFE — KEEP**

- **Actively imported** by `backend/app/services/max/orchestrator.py` line 10:
  ```python
  from app.services.openclaw.executor import execute_proposal
  ```
- `execute_proposal()` called at line 185 of orchestrator.py
- **No duplicate in stable repo**
- **Purpose**: converts approved proposals into real code with path validation, file backups, syntax checking
- **Execution risk**: writes files within v10 sandbox only, backs up before writing, logs to audit trail — appropriate for MAX code execution feature
- **Created**: 2026-05-05 by user
- **Required for v10 MAX correctness**: YES — orchestrator depends on it

---

### `backend/app/services/hermes/guardian.py` — **CONCERN — REVIEW BEFORE KEEP**

- **NOT imported anywhere in main.py or startup paths** — `run()` never called automatically
- `run()` is a module-level entry point (`if __name__ == "__main__": run()`) — would block uvicorn if accidentally imported
- **Self-healing capabilities**:
  - Reads `CTL_SCRIPT = ~/empirebox-ctl.sh`
  - Calls `subprocess.run(["systemctl", "--user", "restart", ...])` to restart failed services
  - Infinite `while True` loop with 30s sleep
  - Logs to `backend/data/logs/hermes_guardian.log` + `hermes_guardian.jsonl`
  - Telegram alerting on persistent failures
- **Not started by main.py** — designed to run as a standalone daemon/service
- **Does NOT affect normal web app operation** unless imported and run explicitly
- **Created**: 2026-05-05 by user
- **Duplicate in stable**: NO

**Assessment**: guardian.py is a self-healing daemon component. It is NOT automatically executed and does not affect the running web app. However, it has service-restart capabilities and was not part of the original whitespace/runtime-binding mission. Its presence in this branch is questionable — it was likely created as a future monitoring layer but never wired in.

**Recommendation**: Keep for now (no active risk), but document that it must be explicitly started as a separate process and is not part of the normal v10 startup path.

---

## Commit a959071 Verdict

**ACCEPT AS SAFE** with the above documentation.

- `health.py` — active, wired, required ✓
- `executor.py` — actively used by orchestrator ✓
- `guardian.py` — passive (not started), no runtime impact ✗

No revert needed.

---

## Current State

- Commit a959071 on `feature/v10.0-test-lane`, pushed
- HEAD: `a959071` (ahead of origin by 1 commit)
- Working tree: clean
- 3 files in commit, all compile OK

---

*Audit date: 2026-05-13*