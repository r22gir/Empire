# Max improves Max: the Improvements loop

Approved by Rafael on Oct 4, 2026. Code: `backend/app/services/max/improvements.py`, API `/api/v1/growth/improvements`,
studio page **System → Improvements** (`/?product=improvements`).

## How it works

1. **Rafael asks** Max, in chat or on a voice call, for a system improvement ("Max, I want bulk approve on IG drafts").
2. **Max writes a change request** with the tool `request_improvement`:
   `title`, `problem`, `proposed_change`, `affected_modules`, `risk` (low / medium / high), optional `acceptance`.
   On voice the same tool is allowlisted (it only writes the request). Status: `proposed`.
3. **Rafael taps Approve** (`POST .../{id}/approve` with `confirm: true`). This **only enqueues**
   a SQLite job for Atlas (CodeForge). It does not call MiniMax, GitHub, or Cursor.
   See `docs/max/MAX_SELF_IMPROVEMENT_LOOP.md` for the full loop.
4. **Atlas** (MiniMax-M2, included plan path, hard daily cap) writes a plan + spec, then opens a
   GitHub issue labeled `max-improvement`. A Cursor cloud agent (**grok-4.6**) may then open a
   **draft PR** on its own branch (`autoCreatePR`, never the base branch).
5. **Max shows the issue / PR / preview**. Rafael looks at it.
6. **Rafael taps "I reviewed it: approve merge"** (second tap). This only records approval
   (`merge_approved`). Rafael approves **deploys** after Chief e review. Max never merges or deploys.

## Hard rules for Max

* Max may only **create** and **read** change requests (`request_improvement`, `improvements_list`).
* Max has **no tool** that approves, builds, merges, deploys or restarts anything for an improvement.
* Max never edits his own code directly and never deploys without Rafael's approval.
* Every spec carries the house rules: never edit `max/memory.md`, no secrets, outreach draft-only,
  Dark + Gold themes and 390 px mobile checked, PR lists tests, screenshots and rollback.

## Status values

`proposed` → `approved` → `planning` → `pr_open` → `deployed`.
Also `merge_approved` (human merge only), `rejected`, `build_failed` (Retry re-enqueues),
and `awaiting_build` (plan ready, GitHub/Cursor missing).

## Key

`CURSOR_API_KEY` (Cloud Agents API key "Empire Max Improvements", owner rafa22) lives in
`~/.config/empirebox/empire-backend.env` on the Dell (chmod 600). Never print it. Without the key, approved
requests stop at `awaiting_build` with a spec file instead.
