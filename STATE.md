# STATE.md — EmpireBox Live Snapshot (v7)
As of: 2026-08-19 (late) · Maintainer: founder + strategic Claude · M3 executes
Replaces v6 (8/19 morning). Read `HANDOFF.md` first if you are a new session.
`claude/BACKLOG.md` is the master register · `claude/DOCTRINE.md` is how work is
done · this is the orientation page.
⚠️ v6 was never committed to the repo. Commit this one.

## THE GOAL — stated by the founder 2026-08-19

**MAX is to take strategic Claude's place.** Not assist it — replace it. He
already has the part that is expensive to build: the honesty layer, proven
under real pressure tonight (four consecutive refusals to fabricate, and an
honest "I don't know where that belief came from" when challenged on a wrong
repo path). What he lacks is not intelligence. It is SIGHT:

- **He cannot read the repo** → H57 Phase 3 (canonical root, structural)
- **He cannot trust his own context** → H53 (injected replay frame)
- **Messages do not reach him** → H57 Phases 1–2 (router intercept)
- **He cannot code** → cause still unknown, founder question unanswered

Every failure observed tonight was a SENSORY failure. None was a character
failure. Build order follows from that, and it is in BACKLOG §RECOMMENDED
ORDER.

**What must transfer with the tools is the JUDGEMENT.** That is why
`claude/DOCTRINE.md` now exists. An orchestrator with the tools and without
the discipline is worse than no orchestrator.

## HOW THIS SYSTEM WORKS
Strategic Claude writes paste-ready dispatches → founder pastes into
MiniMax-M3 Claude Code sessions on EmpireDell → M3 reports
found/changed/tests/commit → strategic audits, founder eyeballs, board
updates. Single lane. Map before fix. Founder verdicts are doctrine.
Sessions are disposable; the repo + this project are the memory.

## INFRASTRUCTURE — GREEN
- Reboot proof PASSED 8/17. Cold boot → everything up unattended.
- Backend :8000 = user unit `empire-backend` (enabled+linger).
  Restart = `systemctl --user restart empire-backend` ONLY.
- Legacy system unit MASKED. All 4 cloudflared tunnels supervised.
  Hermes = `opencode-remote` :8787 — founder remote access, NEVER stop it.
  Portal :3005 supervised.
- Kernel pinned to 6.8.0-31 (Quadro K600 / NVIDIA 470 exists only there).
- Disk 72%. Residuals: stale-fork eradication (~/empire-repo, 8G),
  `.hermes/state.db` 2.8G and growing.
- ✅ **I13 CLOSED 8/19 — Gmail OAuth restored.** ✅ **I14 CLOSED 8/19 —
  founder authorization working.** Both resolved together with the browser
  lockout: the single-root-cause hypothesis (a Google account security event)
  is CONFIRMED. **E1 two-way email is unblocked** — design already locked
  (Gmail-poller, no DNS change, one service layer, PIN never via email,
  structural CC). `check_inbox` has still never been tested live.

## REVENUE — INTAKE OPEN (reopened 8/16 after 72 days down)
luxe.empirebox.store: anonymous → signup → submit with photos + 3D files →
canonical empire.db → founder LuxeForge view. Golden-path E2E encoded.

## ⚠️ THE PORTAL SURFACE IS DRIFTING — found 8/19 from founder screenshots
The register tracked infrastructure while the surface the business runs on
decayed. Seven faults, none previously known. V1/V2 dispatched; V3–V7 mapped
only, unverified against the DB.

- **V1 currency truncates everywhere** — `$8,599.6`, `$1,312.4`, `$362.7`.
  One formatter, all surfaces. Client-facing.
- **V2 test junk in the live quote list** — `1cfix-rej`, `1cfix-pin`,
  `1cfix-reject`, `Bulk1` ×2. Five of twenty. Inflates the $22,066.94
  pipeline headline. **Recurrence** — `d5402aa` purged 14 rows and added
  teardown; establish re-created vs never-purged before deleting.
- **V3** Overview says 5 customers; Customers page says 100 (filters sum to
  100, so 100 is truth).
- **V4** Outstanding $34,391 vs AR aging $5,965 — ~$28.5k unexplained
  between two tiles on one screen.
- **V5** Accepted Quotes reads 0, but Bozzuto EST-2026-111 was approved
  through the PIN modal.
- **V6** Collections carries "Unknown customer · no email · $4,175 overdue"
  — an orphaned receivable. **This is I9 made visible**
  (`PRAGMA foreign_keys = 0`); orphans are possible platform-wide.
- **V7** EST-2026-113 (Hudson & Crane drapery) exists as a generated PDF but
  never entered the canonical store.

## MAX — HONESTY STRUCTURAL, SENSES BROKEN
Working: tool-result replay across turns, runtime-issued badges, fabricated
and present-tense action claims blocked, PIN solicitation blocked both ways,
outbound email live with structural CC and founder-only allowlist.

**Observed live 2026-08-19, founder session:**
- 🔴 **H57 — the drawing router eats his door.** `any(keyword in lowered)` —
  literal SUBSTRING match, PRE-MODEL, at `drawing_intent.py:335`. "what is a
  drawing" never reached MAX. A long document paste never reached MAX.
  Also catches *withdrawing*, *redrawing*. **And `pending_drawing_jobs`
  (SQLite) persists a half-formed spec across turns with no release** —
  that is the reported "freeze". Phase 1 map `994cf75`; Phase 2 WIP
  `13119fc`.
- 🔴 **H53 escalated — it now makes AUTHORIZATION IMPOSSIBLE.** MAX reported
  a `[SYSTEM]` block in founder messages the founder never typed (F1 replay
  scaffolding reading as injection). He then could not distinguish the
  founder's real authorization from the injection and refused repeatedly.
  Combined with H55 there is no path through.
- 🟡 **MAX's context carries the STALE FORK path** — proposed reading from
  `~/empire-repo` unprompted; asked why, honestly did not know. → H57 Phase 3.
- 🟡 **A second `DRAWING_KEYWORDS` list** exists at
  `openclaw_worker.py:1277`, different contents. Duplicated routing outside
  the canonical layer.

**DESIGN VERDICT (strategic, 2026-08-19): the drawing router should be
RETIRED, not tuned.** Anything deciding before the model runs is guessing
with strictly less information than the model has. Correct shape: MAX
receives every message and CALLS the drawing tool; missing dimensions return
`SpecIncomplete(missing=[...])` and he asks conversationally. That is the
same interface P1-T·c is building. `pending_drawing_jobs` then disappears
because the conversation IS the state. Sequenced after P1-T·c proves the
interface on documents.

## DOCUMENT TEMPLATE ENGINE (P1-T) — ROLLING
Supersedes P1's architecture; P1 fixtures survive. Reference implementation
is the McLean 11-sheet set, founder-approved.

- **Standard pin `1813c59043b7b05f87626dd4e66a3487`** (`e0035b4`).
  **8 amendments, all founder rulings 8/19:** (1) full address
  `5124 Frolich Ln, Hyattsville MD 20781`, footer only · (2) CONFLICT RULE:
  parts sum wins, conflicted dims print APPROX., build continues · (3)
  APPROX. scope = derived + conflicted only · (4) counts derive once · (5)
  text metrics captured at DRAW TIME, retire pdfplumber parse-back · (6)
  dimension numbers always horizontal, no rotated type · (7) people in site
  photos blurred, baked into pixels · (8) fabric swatch from `source_url`,
  fetched once, labelled reference-not-colour-match.
- **Commits:** `b55a9f6` amendments · `948a1fc` rules in place + McLean
  source tracked · `e0035b4` Amendment 8 + PROVENANCE · `938131a` layer
  separation · `75a3ac8` tests + G3 + dim duplication · `efdcbcf` data-row
  derivation + G4/G5 implemented.
- **Layers:** `chrome` · `spec` · `band` · `body/{measurement_set + 4
  scaffolds}` · `content/window_openings` · `gates` · `assemble`.
  Two axes kept independent: DOCUMENT TYPE × CONTENT FAMILY.
- **G5 now catches the McLean 21-vs-22 split with a committed fixture** —
  the defect cannot return silently.
- **Currently at P1-T·c** (builder interface: `build(spec) -> BuildResult`,
  `SpecIncomplete` the only refusal, `sys.exit(1)` gone, no global state).

**⚠️ CORRECTION RECORDED (founder 8/19): MAX is ONE DOOR AMONG SEVERAL.**
Not the system. The template engine is a SERVICE LAYER — MAX, the portal,
the CRM, the quoting system and future modules all call the same
`build(spec)`. No door gets its own copy. Same doctrine as E1's one-service-
layer rule and H44's shared `resolve_quote()`.

**⚠️ JOB MEDIA (founder 8/19): the camera icon on quote rows uploads photos,
videos and 3D scans of the item quoted, and that media CARRIES FORWARD —
intake → quote → invoice → other documents.** Media belongs to the JOB, not
to any one document. This corrects P1-T·b, which has photos entering as
per-document spec input. Amendment 7's blur moves to MEDIA INGEST; Amendment
8's swatch collapses into the same store. Whether the camera writes to the
SAME canonical store as LuxeForge intake is UNVERIFIED — if it is a second
store, that is another registry-drift instance and outranks the rest.

## DRAWING LANE — PAUSED BEHIND THE TEMPLATE
Reference **v11** = `reports/2026-08-16_golden_port_r3.png`, founder-passed
against the real photo. **Photo beats drawing when they disagree.**
Drapery R3 (`fc42fe3`) — the eyeball was never given and may now be MOOT if
drapery re-renders through the template engine. Two real defects found in it
by the P1-T·a map: grommet/rod_pocket constants NOT printed as ASSUMED
(honesty failure), and the fabric model half-built (pattern stored but not
rendered, repeat direction not flipped for railroaded, no hex override).
Both fold into D-R4. Next families: Bench/Banquette → Valance → Cornice →
Headboard.

## LIVE CLIENT WORK — founder set aside 8/19, none dispatched
- **Bozzuto EST-2026-111 $8,599.60 APPROVED** — unsent since 7/31. One email.
- **McLean / Whittington Design (C7, NEW)** — 11 sheets, 22→24 openings,
  field-measured 1 July, RevA issued 19 Aug. Centre wall ruled as THREE
  windows (77½ / 69¼ / 78¼). Re-render through the template engine as the
  P1-T·f acceptance test, then send. Unknown whether RevA already went out
  (decides REV A reissue vs REV B).
- **INOUYE / Hudson & Crane** — reply to Jaye drafted; blocked on drapery
  rod/opening width, the Fabricut call, and the rate card.
- **R6 / WoodCraft** — 3 gates before cutting: COM leg height, wall-to-wall
  126"+6", baseboard under 6"; plus how the COM legs mount.
- **Willard EST-2026-110** — $1,450 deposit unpaid.
- **C3 "DC-metro drapery/romans prospect"** — may be Hudson & Crane OR
  Whittington. Settle or retire.

## GOTCHAS THAT KEEP BITING
- Stale fork `~/empire-repo`: any reference is drift (5 incidents, plus
  MAX's own context).
- Cloudflare: empire-main ingress is in the Zero Trust DASHBOARD, not YAML.
- Files born in chat must reach EmpireDell by DOWNLOAD, never paste.
- Gmail dedupes same-account mail.
- **`FOUNDER_PIN env var is UNSET` prints at import in ANY non-unit context**
  (tests, ad-hoc scripts). The PIN IS set in the unit (I10). This false
  alarm cost M3 a dozen probes on 8/19 — a defect in its own right.
- A negative fixture that fails for the wrong reason proves nothing.
- The task list is not evidence; the live system is.
