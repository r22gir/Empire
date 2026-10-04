# Max improves Max: the Improvements loop

Approved by Rafael on Oct 4, 2026. Code: `backend/app/services/max/improvements.py`, API `/api/v1/growth/improvements`,
studio page **System → Improvements** (`/?product=improvements`).

## How it works

1. **Rafael asks** Max, in chat or on a voice call, for a system improvement ("Max, I want bulk approve on IG drafts").
2. **Max writes a change request** with the tool `request_improvement`:
   `title`, `problem`, `proposed_change`, `affected_modules`, `risk` (low / medium / high), optional `acceptance`.
   On voice the same tool is allowlisted (it only writes the request). Status: `proposed`.
3. **Rafael taps Approve build** on the Improvements page (`POST .../{id}/approve` with `confirm: true`).
   * If `CURSOR_API_KEY` is set on the Dell: a Cursor cloud agent starts on `https://github.com/r22gir/Empire`
     (base `main`, override with `MAX_IMPROVE_REPO` / `MAX_IMPROVE_BASE_REF`) with `autoCreatePR: true`.
     It works on its own branch (`max-improve/imp-<id>-<slug>`) and opens a PR. Status `building`, then `pr_open`
     ("Check for PR" polls the agent read-only).
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

## Blocked today

No `CURSOR_API_KEY` on the Dell (Oct 4, 2026), so approved requests stop at `awaiting_build` with a spec file.
Add a Cloud Agents API key (Cursor dashboard → Cloud Agents → API keys) to
`~/.config/empirebox/empire-backend.env` as `CURSOR_API_KEY=...` and restart `empire-backend.service`
to turn on automatic PRs.
