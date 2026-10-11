# Max desk orchestration — manual test checklist + DB queries

Draft PR only. Do not merge or deploy.

Max is the orchestrator / chief of staff of the **17 registered desks**
(`backend/app/services/max/desks`). He classifies, delegates, tracks,
verifies, reports, and escalates. He does not do the desks' work himself.

## Manual test checklist (Studio, after a local apply)

1. Restart **backend only** on port 8000. Leave the frontend as-is if it is already up.
2. New Max chat: `How many desks do you have?` — Max answers himself; live count is 17 (not 18).
3. `Pull today's analytics metrics and forecast` — Max does **not** answer the work. He creates a tracked task on Analytics (Raven) and reports the task id + status.
4. `Run the AI quality audit` — routes to Quality (Phoenix).
5. `New LuxeForge intake submission just arrived` — routes to Intake (Zara).
6. `Email the client this invoice` — held for founder tap; no send.
7. `What's the latest quote for Dahlia?` — existing lookup shortcut / prelookup still runs (Max answers).
8. `give me a link here...` — **no** document search (`find_files` must not run). (PR #105: `show me wall unit led docs` still searches and must stay clickable.)
9. File an improvement (`Max, add a visible Improvements button`). Reply must include
   `https://studio.empirebox.store/?screen=improvements&id=N` (or the configured public base).
10. Open that deep link — Improvements page highlights IMP-NNNN. Approve still requires the founder tap. Max has no approve tool.
11. Home screen (`/`) shows a visible **Improvements** chip/button.
12. Presentation status bar shows the live desk count from `/api/v1/max/desks` (`desk_count`), not "18 desks".
13. Cloud-agent launch (Approve tap only) includes `model.id = grok-4.6`. If Cursor returns `usage_limit_exceeded`, the build note says so plainly. Max never retries without a model and never tries to raise the limit.
14. Time out a desk task three times — status becomes `failed` (not an endless `todo` reset).
15. Unrouted work lands in `founder_inbox` (survives process restart).

## DB queries to inspect desk usage

Use the task DB (`EMPIRE_TASK_DB`, usually `~/empire-data/empire.db` on the Dell).

```sql
-- Live desk volume
SELECT desk, status, COUNT(*) AS n
FROM tasks
GROUP BY desk, status
ORDER BY desk, status;

-- Open work Max is tracking
SELECT id, desk, status, priority, title, retry_count, next_retry_at, updated_at
FROM tasks
WHERE status IN ('todo','in_progress','waiting','escalated')
ORDER BY
  CASE priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1
               WHEN 'normal' THEN 2 ELSE 3 END,
  created_at;

-- Failures that used to vanish (CHECK blocked these)
SELECT id, desk, title, result_summary, retry_count, completed_at
FROM tasks
WHERE status IN ('failed','escalated')
ORDER BY updated_at DESC
LIMIT 50;

-- Founder inbox (persisted)
SELECT id, title, reason, desk, created_at
FROM founder_inbox
WHERE status = 'open'
ORDER BY created_at DESC;

-- Delegate-first tasks Max created
SELECT id, desk, status, title, created_at
FROM tasks
WHERE created_by = 'max'
ORDER BY created_at DESC
LIMIT 50;

-- Retry cap in action
SELECT id, title, retry_count, max_retries, next_retry_at, status
FROM tasks
WHERE retry_count > 0
ORDER BY retry_count DESC;
```

## What changed (for reviewers)

| Area | Change |
|---|---|
| `/max/chat` | Delegate-first step after existing shortcuts. Model answers only orchestration/status/trivial lookups. |
| Desk router | Keywords first (analytics/quality/intake added). LLM via active provider only; never Ollama. |
| Tasks CHECK | `failed` / `escalated` allowed. Retry cap (3) + backoff. |
| Founder inbox | SQLite table, not process memory. |
| Async `run_desk_task` | Honors `desk=`; Atlas only when CodeForge owns the work. |
| Review | Template output is reported `draft only`. Second pass uses the active model. |
| Sweeper | Every 10 min + 07:45 daily digest (desk, task, state, next step). |
| Improvements | Deep link `?screen=improvements&id=N`. Cloud agent model `grok-4.6`. |
| Document search | No search without document words. Coordinates with PR #105. |
