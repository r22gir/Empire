# STATE.md — EmpireBox Live Snapshot (v2)
As of: 2026-07-26 · Maintainer: founder + Claude (strategic) · M3 updates per report
Replaces v1. Paste into any new Claude chat / auto-read by Claude Code sessions.

## PROJECT / CONTEXT SYSTEM (new)
- claude.ai/Cowork project "Workroom" exists with CLAUDE.md + STATE.md attached.
  RULE: repo copies are CANONICAL; re-upload to the project when state changes.
- Cross-surface gotcha (bit us twice): files created in a chat/Cowork sandbox do
  NOT appear on EmpireDell — download from that session's outputs and place them.
- Clipboard mystery SOLVED: Claude Code's TUI captures mouse selection — that's
  why every "copy from Claude" paste arrived empty all week. Workarounds:
  Shift+drag to select, /export, and the reports/ rule below. Firefox was also
  de-snapped to Mozilla deb 153 (fine; keep). ODT/screenshot protocol retired
  once reports/ rule is confirmed active.
- REPORTS RULE (being added to CLAUDE.md): every 🛑 report is ALSO written to
  reports/<date>_<item>.md + PNGs in-repo. Terminal display is a courtesy.

## INFRASTRUCTURE — HEALTHY
- SSD migration complete + reboot-proven: empire-data, empire-repo-main, swap on
  /ssd (ext4, LITEON 238G). Perf verified: db reads 400MB/s, git status 61ms.
  Rollbacks at ~/empire-data.spinner-old + ~/empire-repo-main.spinner-old.
- Windows/Vectric abandoned; SSD wiped (Users rescued → /data/windows-rescue/).
  CNC path is Linux-native. KVM installed, unused.
- tmux NOT yet installed (apt install tmux when convenient).

## CODE STATE (branch feature/drawing-standard)
- Commit chain: f97d808/b804db3 (parser) → 7dcacdf (4.0 B1 wiring) → 2f5b64f
  (4.1 PIN bypass) → 82ff07b (4.0b router) → 39a2106 (4.0b2 chat/stream dedupe +
  TestDoctrineGuard) → 7e7df25 (B2b coords + geometric gates) → f08db99 (B2c
  sheet layout + side section) → side-section correction (stack-at-top +
  dim-witness-borrow gate) → b258c1e (CLAUDE.md/STATE.md) → 1c1ec66 (B2d:
  Empire sheet style + fabric_registry.py + re-authored gates, +861/−169).
- B2d verified by M3: gates re-authored, 3/3 negative fixtures still fail
  correctly; 206/207 drawing tests green (1 pre-existing failure:
  test_theater_detector_warning_only — broken on HEAD before B2d; backlog).
- Two verification renders produced post-restart: R1-via-UI (TBC fabric
  treatment, honest empty CLIENT) and direct call with BP10814-2 (emerald +
  floral motif). 🛑 AWAITING FOUNDER VERDICT — the drawing lane's gate.
- fabric_registry.py seeded: BP10814-2 Nympheus (floral, #123a2a), SVI001
  Vintage Ale (solid), R357 Natural (texture), D3967 Pigeon, 5937 Oxford.
  Unknown SKU → "FABRIC: TBC — CONFIRM BEFORE CUT".

## M3 DIRECTIVE QUEUE (single-lane; announce-loop session replaced — launch
  from ~/empire-repo-main, check /model = M3)
0. ACTIVE/BLOCKED — Label Station deployment: founder-inserted task. M3 blocked
   correctly: /home/rg/label-station/ missing. RESOLUTION: the three files
   (DEPLOY_LABEL_STATION.md, label_station.py, weigh-and-label.html) were built
   in the founder's "web app" chat (Jul 26) — download from that chat's outputs
   → ~/label-station/ → tell M3 proceed. What it is: Weigh & Label PWA — phone
   renders label PNG → Katasymbol printer app; business-scoped catalog in
   empire.db via FastAPI module; NO printer drivers on server (scope trap noted
   in doc). Founder override on doc step 6: label.empirebox.store PUBLIC, no
   Cloudflare Access. ⚠️ Public = internet-reachable — must expose only the
   label page/catalog, nothing that leaks customer/quote data. Repo trap the
   doc flags: three module registries disagree.
1. B2d founder re-verify (two PNGs) — then B2d follow-ups (paused, preserved).
2. GP1/GP2 LuxeForge intake audit → fix (sequential, break map first with
   evidence, 🛑 after map). Clients currently cannot submit work.
3. Family rollout inheriting B2d: Drapery → Bench/Banquette → Valance →
   Cornice → Headboard. One family/commit, PNG per report.
4. Drawing/file delivery (REQUIRED): GET /api/v1/drawings/{filename}
   traversal-safe; clickable link/card in chat (both endpoints); quote PDFs
   same; portal Documents surface.
5. Ledger: 4.3 portal route sweep (PDF button 404) · 4.4 one-quote-one-source ·
   4.5 stream display + truth-gate false-positive on offers · 4.6 import
   honesty · Items 5/6/7/1e · theater-detector test fix · "4.2 FOUNDER_PIN"
   checkbox is STALE — done + live-verified; close, don't re-implement.

## PARALLEL LANE — P1 PRESENTATION ENGINE (STILL UNFIRED)
Fresh Claude Code session (auto-reads CLAUDE.md). Dispatch: STEP 0 self-writes
EMPIRE_CLIENT_DOC_STANDARD.md (authentic md5 e6fde3cd1150260834987d760fdf8417)
+ architecture (spec.py/derived.py/sheets//mesh3d.py/qc.py/assemble.py) +
Willard ONE-PIECE acceptance fixture (fringe ≈2.0 YD front-only, ONE outside
back, chord ≈88", mixed-rev refusal) + board mode (Bozzuto sofa #825 second
fixture) + P1e dashboard integration (quote↔board bidirectional, presentations
table, portal buttons share service layer with MAX tool). Full text in the main
Claude conversation; Claude regenerates on request.

## CLIENT-FACING PENDING (founder actions)
- Bozzuto (Emma Boris): EST-2026-111 $8,599.60 APPROVED, package ready, send
  HELD by founder. Sofa Estimate #825 $4,098.70 mirrored as board; quotes_v2
  entry pending (good native-quote retest). Deposit ask $4,299.80.
- Willard (Maggie O'Neil): EST-2026-110 $2,900 sent; $1,450 deposit unpaid;
  flammability FF&E confirm pending; ONE-PIECE final — B0–B5 regen pending (P1
  produces it); site-envelope check (≈83.5"×28"×53") OPEN.
- DC-metro prospect: drapery/romans proposal ready; needs client name + send.
- Pricing intel: #825 is mid-market vs high-end DC ($1,400/module labor vs
  premium $1,800–2,800/module); itemize delivery/fabric on future estimates if
  repositioning. Founder's call; no action queued.

## CNC LANE (delivered, Claude-side)
Empire Slot Bench (half-sheet) + X-Carve Series v1 (5 designs, 700×700 safe
envelope, mm SVG+DXF, welded dogbones, multi-setup nesting) in founder's
downloads. Future: cnc/ module (spec→geometry→toolpath→grbl G-code) — sibling
of drawing engine, not yet dispatched. Open: current G-code sender? X-Controller
stock grbl 1.1?

## STANDING BACKLOG
Morning-brief "0 tasks" bug · OpenClaw 7,363 queue · duplicate-invoice (GP3
maps it) · quotes_v2.id NULL default · ~/package-lock.json stray ·
/ollama/models 503 loop · mobile image upload broken · web_read HTTP 400 ·
ask-permission→execute gap (4.7) · theater-detector test · tmux install ·
snap remove firefox (after deb proves) · apt autoremove leftovers.
