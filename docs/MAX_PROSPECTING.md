# Max: client acquisition (LeadForge, SocialForge, pipeline)

Max runs prospecting; Rafael approves. **All outreach is draft-only.** No tool in
this pack can send an email, DM, SMS or post. Max shows the draft and asks before
any send; sending stays the existing founder-gated step (Gmail send in LeadForge
campaigns, SocialForge posting), which these tools never call.

Code: `backend/app/services/max/tools_acquisition.py` (tools),
`backend/app/services/leadforge/{prospect_engine,contact_enrich,prospect_ops,acquisition}.py`.
Tests: `backend/tests/test_leadforge_prospecting.py`.

## Daily loop Max can run

1. `prospect_search` {location, target_type, business_unit}: Brave + Google Places + Yelp (whichever keys are set). Dedupes against the DB.
2. `prospect_enrich` {top_n | prospect_ids, discover_websites?}: free contact lookup (below).
3. `prospect_rank` {limit, exclude_pipeline}: `outreach_score` = listing score (rating, reviews, relevance, DMV, keywords)
   + reachability: named contact +8, email +8, Instagram +4, phone +3, own website +3, workroom fit +5; directory pages -25.
4. `prospect_add_to_pipeline` {prospect_ids | top_n}: adds to `prospect_pipeline` **and** creates the LeadForge lead
   (`lf_leads.prospect_id`), so it shows on the Pipeline board, with a 2-day "First contact" reminder. Idempotent.
5. `prospect_draft_outreach` {prospect_id, channel: email | instagram_dm}: saves a row in `prospect_outreach_drafts` (status `draft`).
6. `prospect_daily_brief` {limit 5-10, days}: top new prospects not yet in the pipeline: **who** (name, city, type, category,
   contact or "unknown", phone, site, Instagram, Maps link), **why** (rating/reviews, fit, contact found), and a **suggested
   first message**, plus today's pipeline reminders and quotes waiting. If there are not enough brand-new rows it widens to
   the best not-yet-contacted backlog and says so (`widened_to_backlog`).
7. `pipeline_followups` / `set_followup` {lead_id, when | in_days, action}: overdue / today / upcoming lead follow-ups,
   leads never contacted, sent quotes with no answer.
8. `reactivation_list` {months_quiet}: past paying clients (paid invoices, revenue on file, QuickBooks history),
   accepted-quote clients and designers / trade partners with no quote or invoice in the window. Suggested text only.
   Test and mock records are filtered out.
9. `prospect_segments` {segment: designers | contractors | hospitality | has_email | has_instagram | named_contact |
   phone_only | high_score | in_pipeline, combine with `+`, in_pipeline_only}: target lists for campaigns.
10. `prospect_social_targets`: prospects whose sites link Instagram / Facebook / LinkedIn (SocialForge engage list;
    also `GET /api/v1/socialforge/prospect-targets`).
11. `socialforge_draft_post` {platform, content, hashtags, media_url}: saves a SocialForge post with status forced to `draft`
    (social proof from finished jobs). Publishing stays manual in SocialForge.
12. Growth tools: `approval_queue`, `draft_followup`, `reconcile_deposits`, `roi_report`, `social_proof_drafts`,
    `place_details_enrich`, `request_improvement`, `improvements_list` (see "Growth layer" below).
13. `module_catalog` / `module_call`: read-only bridge to **every** backend module from the live OpenAPI
    (e.g. `/socialforge/dashboard`, `/vendorops/...`, `/storefront/...`, `/finance/...`). GET only; paths with
    send / sync / pay / checkout / token / secret / env / shell / delete / connect / login / pin are refused.

Rules for Max: run the loop, summarise, then ask: "Add these N to the pipeline? Draft emails or DMs?" Never send.
Never invent a contact: if `contact` is `"unknown"`, say so and offer `prospect_enrich` or the Maps link.

## Free contact lookup (`contact_enrich.py`)

* Reads only the business's **own** website: home page, the exact page search found, and up to 4 same-site
  contact / about / team / meet / staff pages (fallback `/contact`, `/about`, `/team`). Max 5 pages per site.
* `robots.txt` is fetched and honoured per URL (user agent `EmpireLeadForgeBot/1.0`); 401/403 on robots = treat as disallow.
* Rate limits: one request at a time per domain, 2 s spacing; 2 sites in parallel; 10 s / 1.5 MB per page; 25 prospects per call.
* Never scrapes directories or social sites (Yelp, Houzz, Facebook, Instagram, LinkedIn, Angi, Thumbtack, BBB...).
* Extracts: owner / principal name + title (JSON-LD founder/employee, "Name, Principal Designer", "Founder: Name", "Meet Name"),
  email (mailto + text; personal address beats info@/hello@, which beat press@/orders@; junk like logo@2x.png filtered),
  phone (tel: + text), Instagram / Facebook / LinkedIn links.
* Stores on `prospects`: `contact_name, contact_title, contact_email, contact_phone, instagram, facebook, linkedin,
  enrichment_status (found | nothing_found | no_website | skipped_directory | blocked_by_robots | unreachable),
  enrichment_pages, enrichment_note, enriched_at`. Never overwrites a value with a blank.
* Google Places rows carry no website (Text Search does not return it). First we borrow one from a web-search row of the same
  business already in the DB (free). Optional `discover_websites=true` spends **one query per prospect on the Brave key
  already used by Prospect Finder** (max 10 per call, serialised at the free-tier rate). The in-app "Find contact" button uses it.

## API (prefix `/api/v1/leads`)

| Method | Path | What |
|---|---|---|
| POST | `/leadforge/prospects/{id}/pipeline` | pipeline + lead (returns `lead_id`), 404 if unknown |
| POST | `/leadforge/prospects/{id}/enrich` | free lookup for one prospect |
| POST | `/leadforge/prospects/enrich` | batch {prospect_ids or top_n, discover_websites} |
| POST/GET | `/leadforge/prospects/{id}/drafts` | save / list drafts (never sends) |
| GET | `/leadforge/brief` | daily brief |
| GET | `/leadforge/segments`, `/leadforge/segments/{name}` | segments |
| GET | `/leadforge/social-targets` | social feed (also `/api/v1/socialforge/prospect-targets`) |
| GET | `/followups/due` · POST `/{lead_id}/followup` | reminders |
| GET | `/reactivation` · `/reports/referral-sources` | reactivation, referral sources |

## Paid or bigger options (not wired; need Rafael's OK)

See `docs/leadforge/CLIENT_ACQUISITION_GAPS.md` for the full list with rough costs (Google Place Details,
Hunter.io, Apollo, Snov, Clearbit-style enrichment, Meta Graph API for IG DMs, an email-sending domain, call tracking).


## Growth layer (Oct 4, 2026, approved by Rafael)

Code: `backend/app/services/leadforge/growth.py`, `place_details.py`, router `/api/v1/growth/*`,
studio pages LeadForge → **Approvals** and **ROI**, System → **Improvements**. Scheduled jobs: `backend/scripts/growth_jobs.py`
with systemd user timers in `deploy/systemd/`.

1. **Deposit paid → lead won.** When a payment is recorded (Stripe webhook `_update_invoice_status` or a manual
   payment on `/invoices/{id}/payments`), the matching LeadForge lead (by quote id, customer id, email or phone)
   is set to `won` with `won_value` (quote total), `won_invoice_id`, a `deposit_paid` activity, and its
   `prospect_pipeline` row is set to `won`. `reconcile_deposits` (tool) / `POST /growth/deposits/reconcile`
   sweeps all paid invoices (idempotent; also runs before every morning brief).
2. **One approval queue.** Every draft lands in `approval_queue`: prospect emails / IG DMs (`prospect_draft_outreach`),
   SocialForge posts (`socialforge_draft_post`, `social_proof_drafts`), follow-ups (`draft_followup`) and pending
   LeadForge campaign drafts. Rafael taps:
   * **Email → "Approve & send email"**: goes through the existing LeadForge send path
     (`campaign_service.send_draft` → `EmailService`, Gmail SMTP). Requires `confirm: true` from the studio.
   * **IG DM / social / SMS → "Copy & open"**: copies the text and opens Instagram / Facebook. Empire never posts or DMs.
   * Max can read the queue (`approval_queue`) but has no tool to approve or send.
3. **ROI** (`roi_report`, `/growth/roi`): per channel leads → won → quotes ($) → paid invoices → revenue, with spend
   entered by hand per month (`/growth/spend`). Test/mock records are excluded.
4. **Social proof from finished jobs.** When a job is marked completed (PUT `/jobs/{id}` or PATCH status), or on the
   morning sweep, Max drafts an Instagram and a Facebook before/after post in SocialForge (status `draft`) using the
   job's photos (quote intake photos = before; job photos after production start or named after/install = after),
   and puts both in the approval queue. Jobs with no photos are skipped; test/mock jobs are skipped.
5. **Weekly search + morning brief.** `empire-growth-weekly.timer` (Mondays 6:00 AM ET): prospect searches for interior
   designers, remodelers, home stagers and boutique hotels in the DMV, Place Details (free tier) and free contact lookup.
   `empire-growth-brief.timer` (weekdays 7:15 AM ET): reconcile deposits, social-proof sweep, then a Telegram message
   to Rafael's chat only (`TELEGRAM_FOUNDER_CHAT_ID`) with top prospects, due follow-ups and quotes waiting.
   Preview without sending: `GET /growth/brief/preview` or `scripts/growth_jobs.py brief --dry-run`.
6. **Google Place Details** (`place_details_enrich`, `/growth/place-details/*`): website + phone for Google prospects.
   1,000 free calls / month; hard cap 1,500 calls = $10 / month at about $0.02 per call. Batch runs and Max stay in the free
   tier; only an explicit `allow_paid` run may use the paid 500. Calls are counted in `google_api_usage` before each call.
   `LEADFORGE_PLACE_DETAILS=0` turns it off.
7. **Max improves Max**: see `docs/max/MAX_IMPROVES_MAX.md`.

Workroom phone documents follow `docs/workroom/PHONE_DOC_FORMAT.md`.
