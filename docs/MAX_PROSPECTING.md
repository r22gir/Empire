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
12. `module_catalog` / `module_call`: read-only bridge to **every** backend module from the live OpenAPI
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
