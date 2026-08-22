# OPERATING REGISTRY — DRAFT ENTRIES FOR FOUNDER REVIEW
**Date:** 2026-08-22 · **Source:** `R6_NAV_SWEEP_2026-08-22.md` (evidence),
`R5_FIXES_2026-08-22.md` (four corrections)
**Target:** `backend/app/services/max/operating_registry.json`
**Current state:** 7 products · `updated_at: 2026-04-19` · file mtime 2026-05-15

> **This is a draft, not a patch.** Nothing gets written until you rule on it.
> Every `max_can_act` value below is a **judgment call I cannot make for you** —
> it decides what MAX is allowed to change without asking.

---

## BEFORE ANYTHING: VERIFY THE SCHEMA

I inferred the field set from R6's table, not from reading the file. The real
schema may have fields I don't know about. First step of any dispatch that
applies this:

```
~/empire-repo-main/backend/venv/bin/python -m json.tool \
  ~/empire-repo-main/backend/app/services/max/operating_registry.json | head -60
grep -rn 'operating_registry' ~/empire-repo-main/backend/app --include='*.py' | head -20
```

**Also required:** find what *reads* this file and what it does when a module is
absent. If MAX refuses on absence, adding entries changes behaviour immediately.
If it merely omits them from a list, the effect is smaller. That determines how
carefully this is staged.

---

## THE DEFAULT I APPLIED, AND WHY

For every new entry: **`max_can_query: true`, `max_can_act: false`.**

Reading is safe. Acting is not, and three of your standing rules bear on it —
founder sends, no client email automation, no invented dimensions. A module
where MAX can *act* is a module where MAX can change your business without you.

So the draft lets MAX **see** all 37 and **change** none. You promote
individual modules to `max_can_act: true` deliberately, one at a time, when you
want that. That is the safe direction to be wrong in.

---

## TIER 1 — THE 7 EXISTING ENTRIES (corrections only)

| product | current | proposed | why |
|---|---|---|---|
| `max` | active_partial | **unchanged** | correct |
| `relistapp` | active_partial | **unchanged** | R6: LIVE, 37 routes, `ra_listings`=18 |
| `finance` | active_partial | **unchanged** | R6: LIVE, corridor confirmed |
| `openclaw` | active_partial | **`dormant`** | R6 + R7 evidence: 7,390 tasks, 5,945 failed, **+27 tasks in 57 days**. Brief prints `Tasks: 0 open` daily. `active_partial` overstates it. |
| `email` | partial, `truthful_ctas: false` | **split — see note** | Outbound is proven (quotes, briefs, one real analysis). **Inbound has never worked** — you replied to MAX twice on 8/16 asking "Can you read this?" and got no reply. `check_inbox` untested per STATE.md. |
| `workroom_creations` | broken_quarantined | **unchanged** | accurate |
| `supportforge` | partial, `truthful_ctas: false` | **unchanged** | R5 §B1 confirms empty is truthful — `sf_tickets` in the DB the app reads has 0 rows |

**Note on `email`:** the single entry hides the asymmetry. Consider splitting
into `email_outbound` (working, `truthful_ctas: true`) and `email_inbound`
(**never functional**, `max_can_query: false`). Today MAX may believe it can
read mail it cannot read — which is the exact class of overclaim H68 is about.

---

## TIER 2 — THE REVENUE CORE (add first, highest value)

These run the two real businesses. If you add nothing else, add these.

| id | status | routes | data | act? |
|---|---|---|---|---|
| `workroom` | active | `/quotes-v2`, `/crm/customers`, `/jobs/`, `/finance/dashboard`, `/inventory/dashboard`, `/tasks/` | quotes 49, customers 171, jobs 8 | **false** |
| `craftforge` | active | `/craftforge/dashboard\|jobs\|designs\|quotes` | cf_projects 3, cf_lots 60 | **false** |
| `quotes` | active | `/quotes-v2`, `/quotes-v2/stats` | quotes_v2 49, $84,888 | **false** |
| `crm` | active | `/crm/pipeline`, `/crm/customers` | customers 171 | **false** |
| `inventory` | active | `/inventory/items`, `/inventory/dashboard` | 155 items | **false** |
| `drawings` | active | `/drawings/bench\|general\|generate\|analyze-furniture\|analyze-sketch` (POST) | Roman shades live | **false** |
| `vision` | active | `/vision/measure\|upholstery\|mockup\|outline\|status` | 10 routes, 5 frontend callers | **false** |
| `pricing_studio` | active | `/pricing/canonical/status\|labor-rates\|workroom/calculate\|woodcraft/calculate` | — | **false** |
| **`fabrics`** | **active** | `/api/v1/fabrics` (8 routes) | **12 fabric rows** | **false** |
| `luxe_intake` | active | `/intake/admin/projects\|users\|archived\|to-quote` | **503 projects, 654 users** | **false** |

**`fabrics` is the headline.** 8 working routes, 12 rows of drapery fabric with
suppliers and costs — **in no registry, no catalog, and no nav entry.** Adding
it is the difference between MAX saying "I don't know" and MAX answering a
question about your own fabric inventory.

**`luxe_intake` is auth-gated** (401 without a token). R5 §E1 found the cause:
`LuxeForgePage` calls raw `fetch()` with no Authorization header while
`intakeFetch()` — which attaches the Bearer token — sits unused in the same
codebase. One-file fix, not yet applied.

---

## TIER 3 — THE CAMPAIGN PATH (what you actually asked for)

The prospects → campaign workflow. **This is the tier that unblocks the thing
you named.**

| id | status | routes | data | act? |
|---|---|---|---|---|
| `leadforge` | active | `/leads/`, `/leads/leadforge/prospects`, `/prospect-pipeline`, `/campaigns`, `/drafts`, `/enroll`, `/execute`, `/followups` | **prospects 322**, lf_leads 0, lf_prospects 0 | **false — see warning** |

**Correction carried from R5 §A1:** the empty `/leads/` is **not a bug.** Three
tables, three lifecycle stages — `prospects` (322, cold scout pool),
`lf_prospects` (0, campaign-enrolled), `lf_leads` (0, active outreach). The
router is correct. Nobody has run the promotion flow, which exists in code at
`leadforge.py:355` and `leadforge.py:540`.

**`max_can_act` must stay false here, and it is not a formality.** The
LeadForge router contains `send`, `enroll`, and `execute` endpoints. An agent
with act permission on this module could contact 322 real businesses. Your
standing rule — **founder sends; agents prepare** — is the whole reason this
stays false until you have run the flow manually at least once.

Suggested shape when you do want MAX involved:
```
"max_can_query": true,      // read prospects, score, segment, draft
"max_can_act": false,       // may not enroll, send, or execute
"founder_gate": ["send", "enroll", "execute"]
```
If the registry schema has no `founder_gate` concept, that is worth adding —
per-action gating is more useful than a single module-wide boolean.

---

## TIER 4 — THE REST OF LIVE (add in bulk, all read-only)

R6 verified these as LIVE. Grouped for brevity; each needs its own entry.

`storefront` · `construction` · `contractor` · `vendorops` · `archiveforge` ·
`recoveryforge` · `transcriptforge` · `socialforge` · `apostapp` ·
`business_profile` · `platform` · `system` · `tokens_costs` · `max_continuity` ·
`daily_summary` · `dev_panel` · `empire_assist` · `hardware`

All: `status: active`, `max_can_query: true`, `max_can_act: false`.

**Three were under-claimed in the nav** (`dev`, `assist`, `hardware` say `dev`,
observed LIVE). Registry should say active — the nav was over-cautious, which
hides working capability from you.

---

## TIER 5 — TRUTHFUL NEGATIVES (add so MAX stops guessing)

An entry saying "not built" is more useful than absence. Absence makes MAX
uncertain; a truthful negative makes it correct.

| id | status | why |
|---|---|---|
| `empirepay` | `partial` | crypto tables 0 rows; `/finance/invoices` side works (32 invoices) |
| `shipforge` | `not_implemented` | `shipping.py` is **self-declared placeholder** — EasyPost stub, fake tracking |
| `llcfactory` | `partial` | services/packages data exists; `llc_formations`=0, partner integration unwired |
| `marketforge` | `unknown_auth` | 401; `listings`=2, `mf_products`=11 behind auth |
| `amp` | `built_unlaunched` | **5 courses, 91 lessons, 100 content items, own JWT, own DB — `amp_users`=0.** Finished, never opened. |
| `vetforge` | `planned` | 83-line placeholder, no backend |
| `petforge` | `planned` | 83-line placeholder, no backend |
| `measurements` | **`broken`** | `/api/luxeforge/measurements/*` — 4 routes registered in OpenAPI, **all 404/422.** API advertises capability the backend does not implement. |

**`measurements` matters most in this tier.** An agent reading OpenAPI would
believe measurement calculation exists. It does not. That is a route to a
confident wrong answer, and marking it broken is cheap insurance.

---

## TIER 6 — THE ORPHANS (working, invisible to every inventory)

14 capabilities with routes and in some cases data, in no registry, no catalog,
no nav.

| id | routes | data | note |
|---|---|---|---|
| `fabrics` | 8 | **12 rows** | listed in Tier 2 — belongs there, not here |
| `maintenance` | 11 | **17 pending tasks**, maintenance_log 18 | scheduler nobody can see |
| `notifications` | 7 | 1 active | **this is where the frozen "194 inbox items" lives** |
| `orchestration` | 9 | 30 KB role/entrypoint config | the system's own wiring map |
| `recovery_core` | 9 | cloudflare tunnel status | companion to RecoveryForge |
| `work_orders` | 5 | 0 rows | latent — workroom vocabulary |
| `patterns` | 14 | POST-only | drawing primitives |
| `finance_legacy` | 8 | dashboard data | **phantom duplicate** of `/finance` |
| `qr` | 9 | cookie-policy | — |
| `portal` | — | — | under `/payments/portal` |
| `lifecycle` | — | 4 rows | reachable via archiveforge |
| `ai` / `avatar` | 22 | POST-only | text/avatar helpers |
| `emails` | 4 | POST-only | template renderer |

**`notifications` is worth its own line.** The frozen `194 inbox items` in your
morning brief is a real notification from this router that stopped updating. The
brief isn't hardcoded — it's reading a stale row from a module nothing else can
reach.

**`finance_legacy` needs a ruling:** kept warm as a rollback target, or dead
code? It duplicates `/finance` and could confuse an agent choosing a route.

---

## WHAT I NEED FROM YOU

Four rulings. Everything else I can draft.

**1. `max_can_act` — the real question.** Draft says false everywhere. Which
modules, if any, should MAX be allowed to change without asking? My read: none
today. Earn it one module at a time after the automation layer exists.

**2. Does the schema support per-action gating?** A module-wide boolean is too
coarse for LeadForge, where "read prospects" and "send to 322 businesses" are
worlds apart. If `founder_gate` doesn't exist, adding it is worth doing before
populating the file.

**3. Split `email` into inbound and outbound?** They have opposite truth values
and one entry hides that.

**4. Status vocabulary.** I invented `dormant`, `built_unlaunched`,
`not_implemented`, `broken`, `unknown_auth`. Existing values are
`active_partial`, `partial`, `broken_quarantined`. Extend, or map mine onto
yours?

---

## HOW THIS SHOULD LAND

Not as one commit. Suggested staging:

1. **Verify schema + find what reads it.** Read-only. Knowing what happens on
   absence-vs-presence decides everything downstream.
2. **Tier 1 corrections only** — 7 entries, mostly status changes. Small, and
   tests whether the file is live-reloaded or needs a restart.
3. **Tier 2 + 3** — revenue core plus the campaign path. This is where MAX
   starts being able to answer real questions.
4. **Tiers 4–6** — bulk, low risk, all read-only.

After each stage, one live check: ask MAX something it should now be able to
answer and couldn't before. *"What fabrics do I have in stock?"* is the cleanest
test — it fails today and should succeed after Tier 2.

**That question is the acceptance test for this whole exercise.**
