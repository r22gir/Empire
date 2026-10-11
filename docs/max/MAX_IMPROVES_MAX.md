# Max improves Max: the Improvements loop

Approved by Rafael on Oct 4, 2026. Code: `backend/app/services/max/improvements.py`, API `/api/v1/growth/improvements`,
studio page **System → Improvements** (`/?product=improvements`).

## How it works

1. **Rafael asks** Max, in chat or on a voice call, for a system improvement ("Max, I want bulk approve on IG drafts").
2. **Max writes a change request** with the tool `request_improvement`:
   `title`, `problem`, `proposed_change`, `affected_modules`, `risk` (low / medium / high), optional `acceptance`.
   On voice the same tool is allowlisted (it only writes the request). Status: `proposed`.
3. **Rafael taps Approve build** on the Improvements page (`POST .../{id}/approve` with `confirm: true`).
   * If `CURSOR_API_KEY` is set on the Dell (it is, since Oct 4, 2026): a Cursor cloud agent starts on
     `https://github.com/r22gir/Empire` (base `main`, override with `MAX_IMPROVE_REPO` / `MAX_IMPROVE_BASE_REF`)
     via `POST /v1/agents` with `autoCreatePR: true` and `workOnCurrentBranch: false`, so it works on its own
     `cursor/...` branch and opens a PR. Status `building`, then `pr_open` ("Check for PR" polls the agent and
     its latest run read-only). A double tap cannot start two agents (the request is claimed atomically).
   * Model (Rafael's defaults): **Muse Spark 1.3, effort medium**. Small fixes (risk low and at most two
     affected modules) use **Gemini 3.8 Flash, reasoning effort medium**. If the API refuses a model the launch
     retries with the account default. Overrides: `MAX_IMPROVE_MODEL`, `MAX_IMPROVE_EFFORT`,
     `MAX_IMPROVE_SMALL_MODEL`, `MAX_IMPROVE_SMALL_EFFORT`.
   * If there is no key: a ready-to-run spec file is written to `~/empire-data/improvements/IMP-<id>-<slug>.md`
     and the status is `awaiting_build`. Paste the spec into a Cursor cloud agent, then save the PR / preview link
     on the card (status becomes `pr_open`).
4. **Max shows the PR or preview** (`improvements_list` returns the links). Rafael looks at it.
5. **Rafael taps "I reviewed it: approve merge"** (second tap). This only records approval
   (`merge_approved`). The merge and any deploy are done by a human in GitHub / on the Dell.

## Hard rules for Max

* Max may only **create** and **read** change requests (`request_improvement`, `improvements_list`).
* Max has **no tool** that approves, builds, merges, deploys or restarts anything for an improvement.
* Max never edits his own code directly and never deploys without Rafael's approval.
* Every spec carries the house rules: never edit `max/memory.md`, no secrets, outreach draft-only,
  Dark + Gold themes and 390 px mobile checked, PR lists tests, screenshots and rollback.

## Status values

`proposed` → `awaiting_build` (no key) or `building` → `pr_open` → `merge_approved` (→ `done` when merged).
Also `rejected` and `build_failed` (the build note says why; Approve again retries).

## Key

`CURSOR_API_KEY` (Cloud Agents API key "Empire Max Improvements", owner rafa22) lives in
`~/.config/empirebox/empire-backend.env` on the Dell (chmod 600). Never print it. Without the key, approved
requests stop at `awaiting_build` with a spec file instead.
