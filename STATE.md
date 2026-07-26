# STATE.md — EmpireBox Live Snapshot
As of: 2026-07-25 (late evening) · Maintainer: founder + Claude (strategic layer)
Purpose: paste into any new Claude chat or Claude Code session for full context.
M3: update this file as part of every per-item report (add commit hashes, flip
statuses); keep it under two pages.

## INFRASTRUCTURE — HEALTHY
- SSD migration COMPLETE and reboot-proven: empire-data + empire-repo-main + swap
  on /ssd (LITEON 238G, ext4). Spinner keeps OS + /data. Rollback copies at
  ~/empire-data.spinner-old + ~/empire-repo-main.spinner-old (delete when ready).
- Perf verified: empire.db reads 400MB/s · repo-wide git status 61ms · desktop
  memory leak (xdg-desktop-portal-gnome 2.1G) cleared by reboot · swappiness 10.
- Windows/Vectric ABANDONED by decision: SSD wiped (Users rescued to
  /data/windows-rescue/, 28G). CNC path is Linux-native (see CNC section).
  KVM stack installed but unused; harmless.
- Known founder-side bug: clipboard pastes into Claude chat arrive EMPTY
  intermittently. Protocol: .odt files or screenshots for all text handoffs.

## CODE STATE (branch feature/drawing-standard)
- Commits this arc: f97d808/b804db3 (NDJSON parser), 7dcacdf (HOTFIX 4.0 B1
  wiring), 2f5b64f (4.1 PIN bypass killed), 82ff07b (4.0b router), 39a2106
  (4.0b2 chat/stream dedupe + TestDoctrineGuard), 7e7df25 (B2b coord fix +
  geometric QC gates), f08db99 (B2c sheet layout + side section), then B2c
  side-section correction (stack-at-top + dim-witness-borrow gate). ~209 tests
  green at last report.
- Working: full drawing pipeline UI→router→B1/B2 engine→PDF at canonical path;
  PIN approval flow (EST-2026-111 approved via modal); FOUNDER_PIN fail-closed
  live (systemd drop-in set).
- M3 SESSION NOTE: last session (30MB) hit an ANNOUNCE-LOOP after being asked to
  run B2d + GP1 audit in parallel — six "launching" turns, zero tool calls, no
  code changes (nothing corrupted). Resolution: fresh session, single-lane rule
  (now in CLAUDE.md). Session launches from ~ (not repo dir); check /model = M3.

## ACTIVE DIRECTIVES FOR M3 (in order)
1. **B2d — Empire sheet style** for Roman Shades: black header/footer bands, cream
   paper, framed viewports, uppercase letterspaced type, FABRIC ZONES RENDERED
   (color + stylized motif from fabric registry; "TBC — CONFIRM BEFORE CUT" when
   absent), info trim (drop ITEM/SHEET/STATUS/DRAWN BY), SCALE/REV/DATE kept.
   Reference = Willard CST-23 "Elevation & Section" sheet. 🛑 founder re-verify
   (this verify also covers the stack-at-top correction).
2. **GP1/GP2 — LuxeForge intake audit then fix** (sequential, after B2d verify):
   walk client intake as a real client (/intake vs /luxe vs /luxeforge — identify
   the real surface), signup→project→dashboard, then project→quotes_v2. Break map
   FIRST with evidence, then fixes one commit each. 🛑 after the map+fixes report.
3. **Family rollout** inheriting B2d: Drapery → Bench/Banquette → Valance →
   Cornice → Headboard. One family per commit, no stop-gates, PNG per report.
4. **Drawing/file delivery (REQUIRED)**: GET /api/v1/drawings/{filename}
   (traversal-safe), clickable link/card in chat (both endpoints), same for quote
   PDFs, portal Documents surface. E2E asserts link works.
5. Remaining ledger: Hotfixes 4.3 (portal route sweep incl. PDF-button 404),
   4.4 (one quote one source), 4.5 (stream display + truth-gate false-positive on
   conversational offers), 4.6 (import honesty); Items 5 (customer table
   unification), 6 (MarketForge endpoint), 7 (catalog authority plan), 1e (mockup
   assessment). NOTE: task list shows "4.2 FOUNDER_PIN" open — STALE, it is done
   and live-verified; close without re-implementing.

## PARALLEL LANE — P1 PRESENTATION ENGINE (STILL UNFIRED)
Fresh Claude Code session, separate terminal. Dispatch = STEP 0 (self-writes
EMPIRE_CLIENT_DOC_STANDARD.md into repo; founder's paste got corrupted, md5 of
authentic file e6fde3cd1150260834987d760fdf8417) + P1 architecture (spec.py /
derived.py / sheets/ / mesh3d.py / qc.py / assemble.py) + Willard one-piece
acceptance fixture (fringe ≈2.0 YD front-only, ONE outside back, chord ≈88",
mixed-rev refusal) + P1e (dashboard integration: quote↔board bidirectional,
presentations table, portal buttons share service layer with MAX tool) + board
mode (single-sheet, Bozzuto sofa #825 as second fixture: two ±62" modules,
R357 Natural 26yd @ $49.95, $2,800 labor, $4,098.70 total).
Full dispatch text lives in the prior Claude conversation; ask Claude to
regenerate if lost.

## CLIENT-FACING PENDING (founder actions)
- **Bozzuto (Emma Boris)**: EST-2026-111 ($8,599.60) APPROVED; boards + quote PDF
  ready; email HELD by founder choice. Sofa job: external Estimate #825
  ($4,098.70) mirrored as board (EST-2026-xxx pending quote creation — good
  native-quote retest); deposit ask $4,299.80 on 111.
- **Willard (Maggie O'Neil)**: EST-2026-110 sent ($2,900); deposit $1,450 unpaid;
  GP&J Baker flammability FF&E confirmation pending; ONE-PIECE build is final —
  B0–B5 regeneration from one-piece spec pending (P1 acceptance produces it);
  site-envelope check (≈83.5"×28"×53" through Willard doors/elevator) OPEN.
- **DC-metro prospect**: drapery/romans proposal PDF ready, awaiting client name
  + founder send; field-measure visit converts to quote.
- Pricing intel (founder decision, no action queued): #825 sits mid-market vs
  high-end DC (premium would be $1,800–2,800/module labor vs $1,400); itemize
  delivery/fabric on future estimates if repositioning.

## CNC LANE (Claude-side, delivered)
- Empire Slot Bench (half-sheet 3/4" ply) + X-Carve Series v1 (5 designs, 700×700
  safe envelope, mm-native SVG+DXF, welded dogbones, multi-setup nesting) — all in
  founder's downloads. Parametric: re-cut on measured ply thickness on request.
- Future MAX module: cnc/ (spec→geometry→toolpath→grbl G-code→QC) — sibling of the
  drawing engine; not yet dispatched. Open questions: current G-code sender
  (UGS/bCNC vs Easel), X-Controller firmware = stock grbl 1.1?

## STANDING BACKLOG (registered, not urgent)
Morning-brief upgrade ("0 tasks" bug) · OpenClaw 7,363 queue · duplicate-invoice
bug (GP3 will map it) · quotes_v2.id NULL default · ~/package-lock.json stray ·
/ollama/models 503 loop · mobile image upload broken end-to-end · web_read HTTP
400 · ask-permission→execute gap (4.7 findings) · delta-mem for Hermes (idea).
