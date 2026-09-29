# DISPATCH R10 — THE REMOTE LIFELINE: WHAT IS HERMES, ACTUALLY?

Founder ruled 2026-08-22: this goes ahead of R9. R9 is committed at `7a8a23e`
and waits.

**Why this round exists.** At least three names — HERMES, Harry,
opencode-remote — map to at most two running services, and standing doctrine
records "never stop opencode-remote (HERMES)" as though those are one thing.
Two services are confirmed running:

```
opencode-remote.service   PID 1758, up since 2026-08-17, port 8787, 0.0.0.0
                          "OpenCode remote coding server (Tailscale phone access)"
hermes-gateway.service    running
                          "Hermes Agent Gateway - Messaging Platform Integration"
```

This is the founder's break-glass path for diagnosing EmpireDell from a phone
while away from the machine. A naming ambiguity in a break-glass path is what
gets you locked out at the worst possible moment. **Map only. No fixes.**

---

## PASTE INTO M3 (fresh session)

```
Check /model first — confirm M3. Read CLAUDE.md fully. Repo ~/empire-repo-main,
branch feature/drawing-standard (HEAD 7a8a23e or later).

PATH DOCTRINE — SUPERSEDES CLAUDE.md: ~/empire-repo is NOT a stale fork. It is
the MAIN WORKTREE — it owns the shared object store and still receives data writes under backend/data/ holding the shared git object store at
~/empire-repo/.git; ~/empire-repo-main is a LINKED worktree. Deleting
~/empire-repo destroys both. Never write to it.

RULES — ALL PARTS:
- READ ONLY. No edits, no restarts, no unit changes, no DB writes.
- NEVER STOP OR RESTART opencode-remote OR hermes-gateway. These are the
  founder's remote access path. If any step would interrupt either, stop and
  report instead. This overrides every other instruction in this dispatch.
- No email of any kind. No task submission to OpenClaw.
- Never print API keys, tokens, or auth secrets — PRESENT/ABSENT and variable
  names only. Tailscale node names and ports ARE reportable; auth keys are not.
- sqlite3 CLI is NOT installed — use ~/empire-repo-main/backend/venv/bin/python3.
- Say VERIFIED vs INFERRED for every claim. Recent rounds overturned their own
  premise six times. Do it again if the evidence says so.

--- PART 1 · THE SERVICE CENSUS (read-only, 🛑) ---

1. ENUMERATE. List EVERY systemd user unit whose name, description, ExecStart,
   or drop-ins mention hermes, harry, opencode, remote, gateway, or tailscale.
   For each: unit file path, Description, ExecStart line, enabled/disabled,
   active state, MainPID, uptime, listening port(s), bind address. Include
   masked and inactive units — a masked unit with a familiar name is exactly
   how a wrong reach happens.

2. WHAT DOES EACH ACTUALLY DO? For each service found, locate its code and
   report what it is:
     - opencode-remote: what binary, what does `opencode serve` expose? Is it
       a coding agent that can EDIT AND RUN THINGS on this box, or a read-only
       viewer? Answer precisely — this determines whether it is a diagnosis
       tool or an execution layer.
     - hermes-gateway: find its ExecStart target and read it. Is it a message
       RELAY (passes text between a chat platform and something else), or does
       it EXECUTE anything? Which messaging platform(s)? Name them.
   For each, state VERIFIED from what file:line, or INFERRED.

3. THE NAMING QUESTION — this is the point of the round. Produce one table:
   every name in use (HERMES, Harry, opencode-remote, hermes-gateway, and any
   others you find) mapped to the ONE service it actually denotes, with
   evidence. grep the repo, all docs in claude/ and reports/ and docs/, and
   CLAUDE.md for each name and report where each is used and what it appears
   to mean there. WHERE DOCS CONFLICT, SAY SO AND QUOTE BOTH. Do not
   reconcile them by picking a winner — report the conflict.

4. IS EITHER ONE WIRED TO MAX? Search the backend for calls into either
   service — by port (8787 and whatever hermes-gateway listens on), by
   hostname, by service name, by env var. Report file:line for every call
   site, or state plainly that there are none. Specifically: does MAX's agent
   hierarchy delegate to either of these, or are they standalone? Do NOT
   assume they are part of the agent team because the name sounds like one.

5. THE REMOTE PATH — how does the founder actually reach this from a phone?
     - Is Tailscale installed and running? `tailscale status` (report node
       names and online/offline; NEVER report auth keys).
     - What is this machine's Tailscale name/IP?
     - Does opencode-remote require auth on 8787, or is it open to anything on
       the tailnet? Read the config — do not test by connecting.
     - Is there ANY second path in (Cloudflare tunnel, ssh, VPN)? Earlier
       notes claimed Cloudflare Zero Trust; determine whether that applies to
       these services or to something else entirely.
   State the exact URL or command the founder would use from a phone. If you
   cannot determine it, say so — do not guess a URL.

6. THE 8/21 ERRORS. journalctl shows a dispatch/cors stack-trace chain from
   opencode-remote on 2026-08-21 10:30:32. Pull the full context around it.
   Was that a failed request, a crash-and-recover, or routine noise? Also
   report: 1.2G resident / 3.6G peak on a five-day-old idle coding server —
   normal for this binary, or a leak shape? Say which, and how you can tell.

7. THE REPO ISSUE. The founder believes a repo-related issue was recently
   fixed in one of these services. Search git log, the units, and any config
   for a repo path either service points at. Report which repo path each uses
   and whether it is the canonical ~/empire-repo-main, the frozen
   ~/empire-repo, or something else. A remote tool pointed at the frozen lane
   would be a live landmine.

🛑 STOP. Report: found / changed ("none — read only") / verified vs inferred /
report hash.

REPORT: reports/<YYYY-MM-DD>_<HHMMSS>_R10_hermes_map.md using the REAL clock
time you start — do not use a date supplied in this dispatch. When final,
`sha256sum <file> | cut -c1-8` and rename to
..._R10_hermes_map_<h8>.md. Report that hash. One round, one file.
```

---

## NOTES FOR THE FOUNDER

- **Step 5 is the deliverable.** Everything else is context. What you need out
  of this round is one line: the exact thing you type into a phone to reach
  this box. If M3 can't produce it from config, that is itself the finding —
  it means the path works because it was set up once and remembered, which is
  not a path you can rely on under pressure.
- **Step 2 answers your execution-layer question.** `opencode serve` is a
  coding agent, so it very likely CAN edit and run — but "very likely" is what
  I've been wrong about twice today (Cloudflare vs Tailscale, HERMES vs
  opencode-remote). It gets verified from the binary, not from the name.
- **Step 7 is the one that could bite.** If either service points at the
  frozen `~/empire-repo`, then remote work lands in the wrong lane and looks
  like it succeeded. That is the same class as the 5,504 May failures.
- **Nothing gets fixed this round**, including the memory growth and the 8/21
  traces. Map first. If step 7 finds a wrong repo path, that becomes R10.1 and
  jumps the queue ahead of R9.
- **The real test is still the phone.** Off wifi, reach it, confirm. No amount
  of config reading substitutes for that, and it takes sixty seconds.
