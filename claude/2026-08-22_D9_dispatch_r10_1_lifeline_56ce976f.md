# DISPATCH R10.1 — SECURE THE REMOTE LIFELINE

Jumps ahead of R9 (committed `7a8a23e`, still waiting). R10's map is
`reports/2026-08-22_183440_R10_hermes_map_db65dd93.md`.

Three verified defects, all on the founder's break-glass path:

1. **`opencode-remote` is unsecured on `0.0.0.0:8787`.** Its own startup log:
   `OPENCODE_SERVER_PASSWORD is not set; server is unsecured`. A coding agent
   that can edit and execute, on every interface, no auth, up 5 days.
2. **It works in the wrong repo.** Session worktrees and the `project.worktree`
   field point at frozen `b7dcb6b` on `lane/source-holding-v10-root` — **275
   commits behind** canonical. Remote fixes land in the frozen lane and look
   like they succeeded.
3. **`backend/app/routers/qr.py:_start_acp_server` respawns it with
   `OPENCODE_SERVER_PASSWORD=""`.** Setting a password on the unit alone does
   not hold — the respawn path resets it.

**THE HAZARD THIS DISPATCH MUST NOT CAUSE.** Every change here touches the
thing the founder would use to fix things remotely. A wrong step locks him out
of his own lifeline from a client site. **Auth is proven working from the phone
BEFORE the bind is narrowed — never the reverse.** Terminal access to
EmpireDell is the fallback throughout; do not create a state where both are
gone at once.

---

## PASTE INTO M3 (fresh session)

```
Check /model first — confirm M3. Read CLAUDE.md fully. Repo ~/empire-repo-main,
branch feature/drawing-standard (HEAD 3eb84f3 or later).

READ FIRST: reports/2026-08-22_183440_R10_hermes_map_db65dd93.md — the trace
this acts on. Verify its claims as you go; if one has moved or is wrong, stop
and say so.

PATH DOCTRINE — SUPERSEDES CLAUDE.md: ~/empire-repo is NOT a stale fork. It is
the FROZEN main worktree holding the shared git object store at
~/empire-repo/.git; ~/empire-repo-main is a LINKED worktree. Deleting
~/empire-repo destroys both. Never write to it. CLAUDE.md also wrongly states
that opencode-remote IS Hermes — R10 verified they are separate services. Do
not act on either stale claim; the doc sweep is a separate round.

HARD RULES — ALL PHASES:
- NEVER leave opencode-remote stopped. If any step stops it, the SAME step
  brings it back and verifies it is listening before you proceed. If you
  cannot bring it back, STOP IMMEDIATELY and say so in plain words at the top
  of your report — that is a founder-lockout condition and outranks finishing
  the task.
- Do NOT narrow the bind address until PHASE 3 confirms the founder reached it
  from his phone WITH the password. Order is not negotiable.
- Never print the password, tokens, or API keys. PRESENT/ABSENT, lengths as
  "N chars", and variable names only. Tailscale node names and ports ARE
  reportable.
- Do not touch hermes-gateway. It is loopback-only and out of scope.
- Do not restart empire-backend except where PHASE 2 says so.
- sqlite3 CLI is NOT installed — use ~/empire-repo-main/backend/venv/bin/python3.
- Back up every file before editing it, to ~/backups/20260822/ with a
  timestamped suffix. Report the path and byte count of each backup.
- Say VERIFIED vs INFERRED for every claim.

--- PHASE 1 · AUTH ONLY. NO BIND CHANGE. NO WORKTREE CHANGE. ---

The goal of this phase is exactly one thing: 8787 requires a password, and the
founder can still reach it.

1. Read the opencode-remote unit and any drop-ins. Report how
   OPENCODE_SERVER_PASSWORD would be supplied, and confirm it is currently
   absent. Report the exact drop-in path you will create.

2. Generate a strong password and write it to a drop-in that loads LAST in
   alphabetical merge order — the R7 shadow bug was caused by a drop-in being
   overridden by a later EnvironmentFile, so verify your file wins the merge
   and say how you verified it. Restrict the file to mode 600.
   Print the password ONCE and ONLY as an explicit block the founder must copy
   now, clearly marked, then never echo it again. The founder needs it on his
   phone; there is no other way to hand it over. Do not write it into the
   report file.

3. Reload and restart opencode-remote. Confirm: new PID, active, still
   listening on 8787, and that the startup log NO LONGER says "server is
   unsecured". Quote the new startup line.

4. Prove auth is enforced from this box: an unauthenticated request to
   http://127.0.0.1:8787 must now be REJECTED. Report the status code. If it
   still answers without auth, the password did not take — revert to the
   pre-change state, confirm the service is back up and reachable, and STOP.

5. Do NOT change the bind address. Do NOT touch the worktree. Do NOT touch
   qr.py yet.
🛑 STOP. Report: found / changed / verified vs inferred / backup paths / new
PID / the status code from step 4. Tell the founder to test from his phone.

--- PHASE 2 · THE RESPAWN PATH + THE WORKTREE (founder go, after phone test) ---

Only after the founder confirms he reached 8787 from his phone with the
password.

6. qr.py:_start_acp_server — it launches opencode with
   OPENCODE_SERVER_PASSWORD="". Fix it to read the real password from the
   environment and REFUSE TO START if that variable is absent or empty. Do not
   substitute a default. An empty password must be an error, not a fallback —
   make the wrong thing unreachable, not discouraged.

7. Regression guard, structural: a test that FAILS if any code path in the
   backend spawns an opencode server with an empty or missing
   OPENCODE_SERVER_PASSWORD. Guard the class, not the one line.

8. The worktree. opencode's sessions and its DB project.worktree point at the
   frozen lane. Determine FIRST, and report before changing anything:
     - where the worktree is configured (unit WorkingDirectory, opencode
       config file, the DB row, or all three)
     - what breaks if it changes: do existing session histories become
       unreadable? Is the DB field per-session or global?
     - whether repointing is a config change or a DB edit
   If it is a DB edit, back up ~/.local/share/opencode/opencode.db first and
   report the backup path and byte count.
   Then repoint to ~/empire-repo-main. Restart opencode-remote and confirm it
   is listening.

9. Full test suite, not a scoped subset. Report total pass/fail. Report any
   pre-existing failures separately from ones you caused.
10. One commit for qr.py + the guard. Config/DB changes reported, not
    committed (they are outside the repo).
🛑 STOP and report.

--- PHASE 3 · NARROW THE BIND (founder go, LAST) ---

Only after Phase 2 reports clean AND the founder has again confirmed phone
access still works.

11. Change the bind from 0.0.0.0 to the Tailscale interface address
    (100.110.233.75) so 8787 is no longer exposed to the LAN. Restart and
    confirm listening on the new address only — `ss -tlnp` output quoted.
12. Confirm from this box that the LAN address no longer answers and the
    tailscale address does.
13. If anything fails, revert to 0.0.0.0 immediately and confirm reachable.
    An exposed-but-password-protected server beats an unreachable one.
🛑 STOP and report.

REPORT: reports/<YYYY-MM-DD>_<HHMMSS>_R10_1_lifeline.md using the REAL clock
time you start — never a date supplied in this dispatch. All three phases in
ONE file under separate headings. When final, `sha256sum <file> | cut -c1-8`
and rename to ..._R10_1_lifeline_<h8>.md. Report the hash.
```

---

## NOTES FOR THE FOUNDER

- **Phase 1 is the only urgent part.** An unauthenticated coding agent that can
  edit and execute, reachable from any device on your LAN, is the finding.
  The wrong worktree is bad, but it fails visibly the moment you check a diff.
  This one fails silently and in someone else's favour.
- **You must copy the password when M3 prints it.** It gets printed once, into
  the terminal, deliberately not into the committed report. Put it in your
  password manager before you close that session.
- **Test from the phone between every phase.** Not as a formality — Phase 3
  narrows the interface your phone uses, and the only proof it still works is
  your phone. Off wifi, `http://100.110.233.75:8787`.
- **Phase 2 step 8 could be bigger than it looks.** If `project.worktree` is
  per-session in the DB, repointing may orphan your existing session history.
  M3 reports before changing — read that before ruling.
- **If M3 ever reports it cannot bring opencode-remote back up, stop
  everything and fix that first.** Terminal access is your fallback, and you
  should not run Phase 3 while away from the machine.
