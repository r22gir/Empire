# Max self-improvement loop (Atlas / MiniMax-M2)

Approve used to only flip a status (or, on an older path, launch Cursor immediately).
Approve now **enqueues a persistent SQLite job**. Atlas on the CodeForge desk
plans with MiniMax-M2 (included plan path) and opens a GitHub issue labeled
`max-improvement` so a Cursor cloud agent (**grok-4.6**) can open a **draft PR**.

**Never merge. Never deploy.** Rafael approves deploys after Chief e review.

Studio: `/?screen=improvements` · API: `/api/v1/growth/improvements`

## Status pipeline

`proposed` → `approved` → `planning` → `pr_open` → `deployed`

| Status | Meaning |
|---|---|
| `proposed` | Max filed the request. Waiting for Rafael. |
| `approved` | Founder tapped Approve. Job is in `max_improvement_jobs`. |
| `planning` | Atlas is calling MiniMax-M2 or Cursor is opening a draft PR. |
| `pr_open` | GitHub issue and/or draft PR exists. Review it. |
| `merge_approved` | Rafael recorded merge approval. A human merges. Max does not. |
| `deployed` | Rafael recorded a deploy after Chief e review. Max does not deploy. |
| `build_failed` | See the build note. **Retry** re-enqueues Atlas. |
| `awaiting_build` | Plan/spec written; GitHub token or Cursor key missing. Retry. |
| `rejected` | Closed. |

## What happens on Approve

`POST /api/v1/growth/improvements/{id}/approve` with `{"confirm": true}`:

1. Atomically sets status `approved` (double-tap cannot enqueue twice).
2. Inserts `max_improvement_jobs` (`queued`).
3. Returns. **No MiniMax, GitHub, or Cursor call on this request.**

The primary-worker **Atlas Improvement Worker** (started from `backend/app/main.py`)
claims the job, calls CodeForge / Atlas, then:

1. Checks the hard MiniMax daily cap (default **40 calls / 200k tokens UTC day**).
2. Stops at the cap. **No auto-credits.** Gift credits are never treated as room.
3. Family editions (Max-e / Maxine) do **not** run this loop and keep their **20%**
   text share (`INSTANCE_USAGE_CAP_PCT` / `MINIMAX_EDITION_TEXT_SHARE_PCT`).
4. Calls MiniMax (`MINIMAX_API_KEY`, model `MiniMax-M2`) for a plan + proposed patch/spec.
5. Writes the spec under `MAX_IMPROVE_SPEC_DIR` (default `~/empire-data/improvements`).
6. Opens a GitHub issue labeled `max-improvement`.
7. If `CURSOR_API_KEY` is set, starts a grok-4.6 cloud agent (`autoCreatePR`, new branch).
8. Never merges, never deploys, never sends email / WhatsApp / SMS.

`POST .../retry` with `{"confirm": true}` re-enqueues `build_failed` / `awaiting_build`.

## Nightly isolated tests (2:30 AM ET)

Documented timer, **not auto-installed**:

- `deploy/systemd/empire-nightly-improvements.timer` — `*-*-* 02:30:00 America/New_York`
- `deploy/systemd/empire-nightly-improvements.service`
- Script: `backend/scripts/nightly_improvement_tests.py`

The suite runs in a **temp data tree**. Outbound keys are cleared. Failures are
filed as `kind=fix` improvements (`requested_via=nightly`). They are **not**
auto-approved.

## Studio frozen-suite gate

Night Lab / Atlas / self-heal / maintenance auto-fix must pass
`tests/test_studio_frozen_gate.py` **twice** before a change is kept.
One fail → reject (and revert if a change was applied). Clear log line:

```
STUDIO_FROZEN_GATE: YES  passes=2/2  frozen suite green twice — change may be kept
STUDIO_FROZEN_GATE: NO   passes=0/2  frozen suite failed on first pass — change rejected
```

The suite is small, strict, and mock-only: quotes, drawings (fractions;
wood/foam vs fabric cuts labeled separately; fabric codes not brands),
and invoices. Nothing is emailed or sent on WhatsApp / SMS / Telegram.

Default backend targets (override with `MAX_IMPROVE_NIGHTLY_PYTEST` or `--full`):

```
tests/test_growth.py
tests/test_improvement_loop.py
tests/test_minimax_meter.py
tests/test_live_data_firewall.py
tests/test_studio_frozen_gate.py
```

Frontend: `node --experimental-strip-types --test` over `app/lib` and `app/components`.

### Enable on the Dell (manual)

```bash
mkdir -p ~/.config/systemd/user
cp deploy/systemd/empire-nightly-improvements.{service,timer} ~/.config/systemd/user/
# Review ExecStart paths. Do not enable until the box has python3 + node.
systemctl --user daemon-reload
systemctl --user enable --now empire-nightly-improvements.timer
systemctl --user list-timers | grep nightly
```

Dry-run (no cards filed):

```bash
cd backend
python3 scripts/nightly_improvement_tests.py --dry-run
```

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `MINIMAX_API_KEY` | — | Included-plan MiniMax key. Required for LLM plans. |
| `MINIMAX_BASE_URL` | `https://api.minimax.io/v1` | Chat completions host. |
| `MAX_IMPROVE_MINIMAX_MODEL` | `MiniMax-M2` | Planner model (included plan path). |
| `MAX_IMPROVE_MINIMAX_DAILY_CALLS` | `40` | Hard daily call cap. Stops. No auto-credits. |
| `MAX_IMPROVE_MINIMAX_DAILY_TOKENS` | `200000` | Hard daily token cap. |
| `MAX_IMPROVE_GITHUB_TOKEN` / `GITHUB_TOKEN` | — | Opens the `max-improvement` issue. |
| `CURSOR_API_KEY` | — | Optional grok-4.6 draft-PR agent after the issue. |
| `MAX_IMPROVE_REPO` | `https://github.com/r22gir/Empire` | Issue + agent repo. |
| `MAX_IMPROVE_BASE_REF` | `main` | Base ref (never pushed). |
| `MAX_IMPROVE_SPEC_DIR` | `~/empire-data/improvements` | Written specs. |
| `MAX_IMPROVE_WORKER_POLL` | `12` | Atlas poll seconds. |
| `MAX_IMPROVE_NIGHTLY_PYTEST` | (see above) | Nightly backend targets. |
| `MAX_IMPROVE_NIGHTLY_FULL` | unset | `1` = entire `backend/tests`. |
| `MINIMAX_EDITION_TEXT_SHARE_PCT` | `20` | Family edition text share. |
| `INSTANCE_USAGE_CAP_PCT` | `20` | Family instance cap (unchanged). |

Never commit `.env`, `client_aliases.json`, or `business.json`.

## API

- `GET /api/v1/growth/improvements` — cards + `minimax` usage + `pipeline`
- `GET /api/v1/growth/improvements/usage` — planner budget counter
- `POST /api/v1/growth/improvements/{id}/approve` `{confirm:true}` — enqueue
- `POST /api/v1/growth/improvements/{id}/retry` `{confirm:true}` — re-enqueue
- `POST /api/v1/growth/improvements/{id}/refresh` — poll Cursor agent (read-only)
- `POST /api/v1/growth/improvements/{id}/approve-merge` `{confirm:true}` — record only
- `POST /api/v1/growth/improvements/{id}/mark-deployed` `{confirm:true}` — record only

Max tools remain `request_improvement` and `improvements_list` only.
