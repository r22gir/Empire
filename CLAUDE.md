# CLAUDE.md — EmpireBox Repository Brief
Read this fully before acting. It is the permanent context for every session.

## WHAT THIS IS
EmpireBox: self-hosted AI business platform on EmpireDell (Ubuntu, Xeon E5-2650v3,
31GB RAM). Serves two real businesses: **Empire Workroom** (custom drapery &
upholstery, Hyattsville MD) and **WoodCraft by Empire** (CNC custom woodwork).
MAX is the in-house AI assistant (portal at localhost:3005, backend FastAPI at
localhost:8000). The founder ("rg") is the only human operator.

## CANONICAL PATHS
- `~/empire-repo-main` and `~/empire-repo-data` are both bind mounts off the
  SSD (`/dev/sdb1`); the active repo branch is `feature/drawing-standard`.
- `~/empire-repo` is the main worktree (not a stale fork). It owns the shared
  git object store at `~/empire-repo/.git`, the live venv at
  `~/empire-repo/backend/venv/`, and the live OpenClaw service on port 7878 —
  all of which still receive data writes. The sibling checkout
  `~/empire-repo-main` is on the same branch. **Acting on `~/empire-repo` as
  if it were a stale tree destroys every local branch, lane and stash on the
  box.**
- Database: `/home/rg/empire-data/empire.db` (SQLite, table quotes_v2 is the
  quote source of truth; `financial_audit_log` records all quote mutations).
- Drawings output: `~/empire-repo-main/backend/data/drawings/`
- `~/empire-repo` sits on the **root disk** (`/dev/sda1`), not the SSD. The
  correct remedy for any data-leak finding is migrating the data writes off
  `/dev/sda1`, not removing the tree.
- **OPEN HAZARD (H73) — canonical-path enforcement is currently UNSAFE.**
  `backend/app/services/max/canonical_path.py:133-152` hardcodes
  `home/"empire-repo"` as a "bad_roots" entry and refuses every sub-path of
  the tree that owns the object store. Live hazard, code lane, NOT this
  dispatch. Until H73 closes, do not lean on RuntimeError-on-stale-path
  behaviour as a correctness check — its stated rationale is wrong even
  where its enforcement is right.
- Never write to `/media/*` or absolute `/home/romeo/*` (a past copied-code bug).

## SERVICES
- Backend: `systemctl --user restart empire-backend` (FastAPI :8000; env incl.
  FOUNDER_PIN comes from systemd drop-ins — never hardcode, never default).
- Portal: `~/empire-repo-main/empire-command-center`, Next.js :3005;
  rebuild = `npm run build` then `systemctl --user restart empire-portal`.

## HARD RULES (violations are defects regardless of intent)
1. **No client-facing email automation.** MAX/agents never send email to clients or
   customers. All client sends are founder-manual. Internal notifications to the
   founder only, via the executor whitelist.
2. **FOUNDER_PIN is fail-closed.** No default value. Unset env → dangerous tools
   (shell_execute, env_set, db_query) refuse + CRITICAL log. The PIN never appears
   in chat, code, or commits.
3. **No invented dimensions, ever.** Drawing/doc generators refuse with the exact
   missing-field list; never fill defaults. Assumptions that ARE made must print in
   an assumptions block ("ASSUMED — CONFIRM BEFORE FABRICATION").
4. **Every business row carries the `business` column.** Workroom vs WoodCraft is
   data, never hardcoded.
5. **Truth gate:** fails OPEN at infrastructure level (enforcement exception →
   logged warning surfaced to founder, never silent, never pipeline-breaking) and
   CLOSED on claims (no success claims without a real tool result / proof object).

## CODE DOCTRINE (learned the hard way; each rule has a bug behind it)
- **Chat/stream duality:** any logic in a chat handler lives in ONE shared function
  called by BOTH `/api/v1/max/chat` and `/api/v1/max/chat/stream`. Three separate
  bugs came from divergent copies. TestDoctrineGuard enforces this for the drawing
  seam — extend the pattern, don't fight it.
- **E2E tests enter through production doors** (the real routes the UI hits, both
  endpoints). A test that simulates the seam it exists to verify is a defect class.
- **Tests assert the REQUIREMENT, not a weaker proxy.** Counts/strings pass on
  broken output; geometry needs geometric gates (see `b2_qc.py`: element spread,
  zone gates, text-collision, text-over-geometry, dim-witness-borrow).
- **Reports SHOW renders** — any report about visual output includes a rasterized
  PNG. "Tests green" without pixels has shipped blank pages before.
- **One family/feature per commit**, per-item reports: found / changed / tests /
  commit hash.
- **Stop-gates:** when the founder directive says 🛑 STOP, stop and await
  live-verify. Founder's eyeball is the final QC gate.
- **Stop-gate reports persist:** every 🛑 stop-gate report is ALSO written to
  `reports/<date>_<item>.md` in the repo — full text, commit hashes, test
  results — with rendered PNGs saved alongside. The terminal display is a
  courtesy; the file is the record.
- **Single lane.** Do not launch parallel sub-agents or announce multi-lane plans;
  a prior session announce-looped doing this. One concrete action at a time; if
  you catch yourself describing intent twice without a tool call, make the tool
  call.

## DRAWING / DOCUMENT SYSTEM
- B1 = parametric data layer + templates (46 product types), tool
  `render_shop_drawing`; `sketch_to_drawing` refuses text+dims requests (backstop).
- B2 = vector renderer (Roman Shades live; families queued: Drapery →
  Bench/Banquette → Valance → Cornice → Headboard). Sheet standard: landscape,
  elevation + side section + notes zones, title column, SCALE/REV/DATE, fabric row
  (from quote/handoff; else "TBC — CONFIRM BEFORE CUT"). Roman shades stack AT THE
  TOP (bottom-up shades); dims reference features, never another dim's line.
  Empire sheet STYLE (B2d): black header/footer bands, cream paper #f7f3ea, ink
  #20241f, gold #b8912f, uppercase letterspaced type, framed viewports, fabric
  zones rendered with color + stylized motif.
- B2 sheet standard = the golden reference. As of 2026-08-16 G1.3
  founder PASS, the binding gold is **`reports/2026-08-16_golden_port_r3.{pdf,png}`
  (REFERENCE v11)** — supersedes v10. v10 remains in `reports/` as history
  (`reports/GOLDEN_flat_fold_empire.pdf`, `reports/2026-07-26_golden_reference_v10.pdf`)
  and is NEVER edited or regenerated. The lineage source (`reports/golden-lineage/
  golden_flatfold1.py` + iterations 8/9/10 PDFs + `reference_photo_flatfold_raised.png`)
  is the founding evidence for v11 (continuous-fabric stack anatomy, zone-based
  footer). All family rollouts from this point compare against v11 + the photo.
  The ten drafting doctrine rules (R1–R10, see reports/2026-07-26 port dispatch)
  govern every family renderer. Style disputes resolve against the golden, not
  against prose.
- Presentation/board engine (`presentation/` package) = client-facing documents,
  governed by `EMPIRE_CLIENT_DOC_STANDARD.md`: ONE spec object drives every sheet,
  quantities are derived never typed, QC gates before emit, docs are records in a
  presentations table (not loose PDFs), portal buttons + MAX tool share one
  service layer.
- Quote flow: quotes_v2 → founder review → PIN approve ("Approve & Send" modal).
  Status can NEVER be mutated via generic PATCH.

## ENVIRONMENT NOTES
- MiniMax M3 via Claude Code; model can silently downgrade — check `/model` on
  session start. Founder pastes from terminal are unreliable (clipboard bug):
  founder uses .odt files or screenshots; write reports accordingly (self-contained,
  PNG-embedded).
- OpenClaw (localhost:7878) exists but has a 7k+ item queue backlog — do not
  depend on it.
- opencode-remote.service (user unit, opencode serve :8787 over Tailscale) is
  HERMES — the founder's remote-desktop access path from Harry. KEEP ALIVE;
  never stop it from a dispatch. HARD RULE for any session running inside it:
  never hand-start uvicorn or bind :8000 — an opencode-spawned uvicorn squatted
  the port and crash-looped empire-backend 85k+ times (Jul–Aug 2026). To restart
  the backend, use systemctl --user restart empire-backend only.

## WHEN IN DOUBT
Map before fixing (break-map deliverables). Refuse loudly rather than guess
silently. The founder prefers an honest "not done, blocked on X" over a confident
wrong answer — that preference is the platform's entire design philosophy.
