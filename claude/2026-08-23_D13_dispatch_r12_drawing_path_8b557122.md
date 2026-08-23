# DISPATCH R12 — THE DRAWING PATH

**This one is on the founder's critical path.** Stated 2026-08-23: MAX's
communication layer is finished — dashboard, phone, Telegram, email, intake, all
working. The gap is on the output side. **MAX must produce the document types
and formats the founder produces today, and must use the drawing tools.** He
currently produces a more basic format, and he freezes when the drawing tool or
router is invoked.

R9 and R11 are closed. HEAD `b074daf`, backend PID 1113389.

**What is already known — verify, do not inherit:**

- **H57** — the drawing router intercepts on a **literal substring, pre-model**.
  "what is a drawing" never reached MAX. Phases 1–3 done, Phase 2 closed
  `62c4741`. **"Retire the drawing router" is still on the open list.**
- A verified `openclaw_tasks` error row: *"Incorrect executor routing: CodeForge
  source-grounding task was routed to drawing generator because task text
  mentioned drawing. Requested code fix was not attempted."* The router hijacks
  on substring regardless of intent.
- `TestDoctrineGuard` **structurally forbids mock-patching the drawing seam.**
- **The standard exists and MAX has never been tested against it.**
  `EMPIRE_DRAWING_STANDARD.md` codifies: no invented dimensions; every
  assumption in the NOTES block; layout math must close on the sheet; curved
  items require plan views; geometric QC gates with negative fixtures that must
  still fail after re-authoring.
- Golden-reference artifacts: `reports/GOLDEN_flat_fold_empire.pdf`,
  `golden_flatfold.py`. The method that worked: iterate on a reference PDF
  directly with Claude, then hand M3 a **mechanical port** task.
  **Style-by-prose through M3 did not converge** — do not attempt it.
- **Pixels are truth for fabric geometry.** Vector inspection couples to how the
  renderer draws; raster scanning checks what actually got drawn, which is what
  the founder judges. H70/H71: the chrome `T()` y-bbox over-estimates glyph
  height by ~7pt and **invents overlaps**; the 8pt tolerance is a documented
  workaround, not a design value.
- 7/31: woodwork generators were ~40 revisions stale (109" vs REV G 114 1/2",
  no plinth). Unknown whether still true.

---

## PASTE INTO M3 (fresh session)

```
Check /model first — confirm M3. Read CLAUDE.md fully. Repo ~/empire-repo-main,
branch feature/drawing-standard (HEAD b074daf or later).

PATH DOCTRINE — SUPERSEDES CLAUDE.md: ~/empire-repo is NOT a stale fork. It is
the FROZEN main worktree holding the shared git object store at
~/empire-repo/.git; ~/empire-repo-main is a LINKED worktree. Deleting
~/empire-repo destroys both. Never write to it. CLAUDE.md is also incomplete on
Hermes: the hierarchy is founder → External Hermes ("Harry", opencode-remote on
Tailscale) → MAX → Empire Hermes (hermes-gateway) + OpenClaw. Three services,
not two. Do not act on either stale claim; the doc sweep is its own round.

INFRA: backend restart = `systemctl --user restart empire-backend` ONLY, and
only where a phase says so. Never bind :8000 by hand. Never stop
opencode-remote or hermes-gateway. sqlite3 CLI is NOT installed — use
~/empire-repo-main/backend/venv/bin/python3. Never commit max/memory.md. Never
print API key values or lengths. No email in any phase.

READ FIRST: EMPIRE_DRAWING_STANDARD.md in full. It is the specification this
round exists to serve.

--- PHASE 1 · MAP (read-only, 🛑) ---

No edits, no retirements, no fixes. This phase decides what R12 actually is.

1. THE FREEZE — reproduce it before theorising. The founder reports MAX freezing
   whenever the drawing tool or router is invoked. Trigger it in a controlled
   way and capture WHERE it hangs: py-spy dump or faulthandler against the
   backend PID, plus the last log lines before the hang. Report the actual
   stack. If you cannot reproduce it, say so plainly — "could not reproduce" is
   a legitimate and important finding, not a failure.
   Distinguish precisely between: (a) a true hang/deadlock, (b) a very slow
   synchronous render blocking the request, (c) a misroute that returns the
   wrong thing quickly and looks like a hang in the UI. These have different
   fixes and are easy to confuse.

2. THE ROUTER. Find every drawing-intercept site. For each: file:line, the
   exact match condition, whether it fires pre-model or post-model, and what it
   does with the request. H57 closed Phase 2 at 62c4741 — report what that fix
   actually changed and what it left in place. Quote the current matching code.

3. THE GENERATOR — the founder does not know whether MAX drives an existing
   generator or produces artifacts himself. Answer it. Inventory every drawing
   or document generator in the backend: file, what it renders (drapery,
   woodwork, elevations), what library, what it outputs, and whether MAX can
   invoke it as a tool. Include the woodwork generators; report whether the
   7/31 staleness (109" vs REV G 114 1/2", missing plinth) is still present.

4. THE SEAM. TestDoctrineGuard structurally forbids mock-patching the drawing
   seam. Quote that guard and explain what it protects. Anything Phase 2 does
   must not weaken it — if a fix would require weakening it, that is a finding
   to report, not a step to take.

5. THE STANDARD vs REALITY. Read EMPIRE_DRAWING_STANDARD.md and
   golden_flatfold.py. Report which of the standard's requirements the current
   generators actually enforce in code — no invented dimensions, NOTES block
   assumptions, layout math closing on the sheet, plan views for curved items,
   QC gates with negative fixtures. For each: ENFORCED (file:line) / PARTIAL /
   ABSENT. This gap list is the round's real deliverable.

6. WHAT MAX CAN REACH. Which of these generators is actually wired to a MAX
   tool the founder can invoke from chat, and which are scripts only a
   developer can run? If the answer is "MAX cannot invoke any of them," say so
   — that would reframe the whole round.

🛑 STOP. Report: found / changed ("none — map only") / verified vs inferred /
report hash. Recommend the smallest correct fix and state its risk.

--- PHASE 2 · FIX (founder go only) ---

Scope set by Phase 1. Constraints that hold regardless:
7. Do NOT weaken TestDoctrineGuard.
8. Do NOT attempt style-by-prose. If output fidelity is the issue, the method is
   the golden-reference one: the founder iterates a reference PDF with Claude,
   and M3 receives a MECHANICAL PORT task. Say so rather than improvising.
9. Geometry verification is RASTER, not vector. Rasterise and pixel-sample.
   Vector inspection couples to how the renderer draws; the founder judges what
   got drawn.
10. Full test suite, pre-change baseline first (1205 passed / 103 failed / 13
    errors after R11), then post-change, failures you caused named separately.
11. One commit per family. 🛑 after.

--- PHASE 3 · ACCEPTANCE TEST (founder go only) ---

12. ONE real item, end to end, invoked the way the founder would invoke it —
    from MAX, not from a script. Produce the drawing/document.
13. Rasterise the output and check it against EMPIRE_DRAWING_STANDARD.md
    point by point. Report each requirement PASS/FAIL with the pixel evidence.
14. **You do not decide whether it is good enough.** Produce the artifact,
    report your own QC honestly including anything you think is wrong with it,
    and hand it to the founder. He judges format and fidelity. Do not describe
    the output as matching his standard — show it and let him say.
🛑 STOP.

REPORT: reports/<YYYY-MM-DD>_<HHMMSS>_R12_drawing_path.md using the REAL clock
time you start. All phases in ONE file. Hash LAST with
`sha256sum <file> | cut -c1-8`, rename to include it, report the value, and
COMMIT it — uncommitted reports have been lost before.
```

---

## NOTES FOR THE FOUNDER

- **Step 1 is the one I'd watch.** "Froze" could be a real deadlock, a slow
  synchronous render, or a fast misroute that looks like a hang. I've told M3 to
  distinguish them and to accept "could not reproduce" as an answer rather than
  inventing a mechanism — that's the failure mode R7 hit.
- **Step 5 is the deliverable.** A gap list between the standard you wrote and
  what the generators actually enforce is the concrete answer to "what does MAX
  need." Everything after it is scoped by that list.
- **Step 6 could reframe the round.** If no generator is reachable as a MAX
  tool, then MAX isn't failing at drawings — he was never wired to them, and
  the work is integration rather than repair.
- **Phase 3 hands judgment to you, explicitly.** M3 produces the artifact and
  reports its own QC; it does not get to declare the output matches your
  standard. That distinction matters here more than anywhere — this is the
  acceptance test for the thing you said MAX was close to.
- **Not in this lane:** the tools-accuracy pass (frozen 194, pairing card, disk
  figure), the registry, token rotation, the seven-week-stale Drive backup, the
  doc sweep.
