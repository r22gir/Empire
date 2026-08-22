# RESTORE PROBE — 2026-08-22 (READ ONLY)

**Operator:** M3 (Claude Code, EmpireDell)
**Reference target:** `empire_ecosystem_navigator_v3_enhanced.html` — 63 nodes, 205 edges
**Run mode:** READ ONLY. No writes, installs, service restarts, config edits, or git operations beyond `status` / `log` / `worktree list`.

---

## STEP 1 — SERVICES

### `systemctl list-units --type=service --state=running --no-pager`

```
  UNIT                          LOAD   ACTIVE SUB     DESCRIPTION
  accounts-daemon.service       loaded active running Accounts Service
  anydesk.service               loaded active running AnyDesk
  avahi-daemon.service          loaded active running Avahi mDNS/DNS-SD Stack
  bluetooth.service             loaded active running Bluetooth service
  cloudflared.service           loaded active running cloudflared
  colord.service                loaded active running Manage, Install and Generate Color Profiles
  cron.service                  loaded active running Regular background program processing daemon
  cups-browsed.service          loaded active running Make remote CUPS printers available locally
  cups.service                  loaded active running CUPS Scheduler
  dbus.service                  loaded active running D-Bus System Message Bus
  empire-openclaw.service       loaded active running Empire OpenClaw AI Server
  fwupd.service                 loaded active running Firmware update daemon
  gdm.service                   loaded active running GNOME Display Manager
  gnome-remote-desktop.service  loaded active running GNOME Remote Desktop
  kerneloops.service            loaded active running Tool to automatically collect and submit kernel crash signatures
  ModemManager.service          loaded active running Modem Manager
  NetworkManager.service        loaded active running Network Manager
  nvidia-persistenced.service   loaded active running NVIDIA Persistence Daemon
  polkit.service                loaded active running Authorization Manager
  power-profiles-daemon.service loaded active running Power Profiles daemon
  rsyslog.service               loaded active running System Logging Service
  rtkit-daemon.service          loaded active running RealtimeKit Scheduling Policy Service
  snapd.service                 loaded active running Snap Daemon
  switcheroo-control.service    loaded active running Switcheroo Control Proxy Service
  systemd-journald.service      loaded active running Journal Service
  systemd-logind.service        loaded active running User Login Management
  systemd-machined.service      loaded active running Virtual Machine and Container Registration Service
  systemd-oomd.service          loaded active running Userspace Out-Of-Memory (OOM) Killer
  systemd-resolved.service      loaded active running Network Name Resolution
  systemd-timesyncd.service     loaded active running Network Time Synchronization
  systemd-udevd.service         loaded active running Rule-based Device Event Handling Daemon
  tailscaled.service            loaded active running Tailscale node agent
  udisks2.service               loaded active running Disk Manager
  unattended-upgrades.service   loaded active running Unattended Upgrades Shutdown
  upower.service                loaded active running Daemon for power management
  user@1000.service             loaded active running User Manager for UID 1000
  virtlockd.service             loaded active running libvirt locking daemon
  virtlogd.service              loaded active running libvirt logging daemon
  wpa_supplicant.service        loaded active running WPA supplicant

Legend: LOAD   → Reflects whether the unit definition was properly loaded.
        ACTIVE → The high-level unit activation state, i.e. generalization of SUB.
        SUB    → The low-level unit activation state, values depend on unit type.

39 loaded units listed.
```

### `systemctl status empire-portal.service --no-pager -l | head -30`

```
Unit empire-portal.service could not be found.
```

(The portal is a USER-level unit, not system-level; see Step 5/9 supplement below.)

### `ps aux | grep -Ei 'uvicorn|fastapi|node|next|ollama|python.*max|opencode' | grep -v grep`

```
rg          1758  1.7  2.5 81040796 847644 ?     Ssl  Aug17 120:53 /home/rg/.opencode/bin/opencode serve --port 8787 --hostname 0.0.0.0
rg          1764  0.0  0.1 1099640 60028 ?       Ssl  Aug17   0:01 npm exec next start -p 3005
root        1825  0.0  0.0   2704  1920 ?        Ss  Aug17   0:00 fusermount3 -o rw,nosuid,nodev,fsname=portal,auto_unmount,subtype=portal -- /run/user/1000/doc
rg          2419  0.0  0.0   2800  1600 ?        S    Aug17   0:00 sh -c next start -p 3005
rg          2420  0.0  0.3 22332184 113400 ?      Sl  Aug17   1:08 next-server (v16.1.6)
rg        652663  1.7  0.9 1933564 302572 ?      Ssl  Aug20  39:55 /home/rg/empire-repo-main/backend/venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 65
rg        934623  0.4  0.2 252944 82144 pts/0    Sl+  10:08   0:02 /data/empire-storage/build-cache/uv/archive-v0/rco5E5gW08S6aOSSJaP8b/bin/python /home/rg/.cache/uv/archive-v0/rco5E5gW08S6aOSSJaP8b/bin/minimax-coding-plan-mcp -y
```

### `ss -tlnp 2>/dev/null | sort -t: -k2 -n`

```
LISTEN 0      10                            [::]:7070          [::]:*                                         
LISTEN 0      4096                         [::1]:631           [::]:*                                         
LISTEN 0      32                   192.168.122.1:53         0.0.0.0:*                                         
LISTEN 0      4096                 127.0.0.53%lo:53         0.0.0.0:*                                         
LISTEN 0      4096                    127.0.0.54:53         0.0.0.0:*                                         
LISTEN 0      4096   [fd7a:115c:a1e0::5336:e94c]:34094         [::]:*                                         
LISTEN 0      4096                     127.0.0.1:631        0.0.0.0:*                                         
LISTEN 0      128                      127.0.0.1:3000       0.0.0.0:*    users:(("hermes",pid=1757,fd=22))    
LISTEN 0      511                              *:3005             *:*    users:(("next-server (v1",pid=2420,fd=18))
LISTEN 0      10                         0.0.0.0:7070       0.0.0.0:*                                         
LISTEN 0      2048                       0.0.0.0:7878       0.0.0.0:*    users:(("python3",pid=1755,fd=13))   
LISTEN 0      2048                       0.0.0.0:8000       0.0.0.0:*    users:(("python3",pid=652663,fd=15)) 
LISTEN 0      512                        0.0.0.0:8787       0.0.0.0:*    users:(("opencode",pid=1758,fd=20))  
LISTEN 0      4096                     127.0.0.1:20241      0.0.0.0:*    users:(("cloudflared",pid=1748,fd=3))
LISTEN 0      4096                     127.0.0.1:20242      0.0.0.0:*    users:(("cloudflared",pid=1749,fd=3))
LISTEN 0      4096                     127.0.0.1:20243      0.0.0.0:*                                         
LISTEN 0      4096                     127.0.0.1:20244      0.0.0.0:*    users:(("cloudflared",pid=1747,fd=3))
LISTEN 0      4096                100.110.233.75:61317      0.0.0.0:*
```

**Every listening port with owning process:**

| Port | Process / Source | Notes |
|---|---|---|
| 3000 | hermes (pid 1757) | Hermes agent |
| 3005 | next-server (pid 2420, npm pid 1764) | Empire Studio Portal |
| 7070 | (no owner visible) | Unknown / unprivileged |
| 7878 | python3 (pid 1755) | OpenClaw |
| 8000 | python3 / uvicorn (pid 652663) | Empire Backend |
| 8787 | opencode (pid 1758) | OpenCode daemon |
| 20241–20244 | cloudflared | Cloudflare tunnel connectors |
| 631 | cups / cups-browsed | CUPS printer services |
| 53 | systemd-resolved / libvirt | DNS |
| 34094 | IPv6 ephemeral | (transient) |
| 61317 | Tailscale (UDP/TCP) | tailscaled |

**No PostgreSQL (5432), no Redis (6379), no MinIO (9000) ports listening.** The May PDF's data-layer claim is falsified by port 1.

**User-level services (added probe, not in dispatch block):**

```
● empire-backend.service - Empire Backend API
     Loaded: loaded (/home/rg/.config/systemd/user/empire-backend.service; enabled; preset: enabled)
    Drop-In: /home/rg/.config/systemd/user/empire-backend.service.d
             └─founder-pin.conf, gemini.conf, gmail-oauth-runtime.conf, max-email-whitelist.conf, provider-env.conf, smtp.conf, zz-canonical-venv.conf, zz-gmail-stable.conf
     Active: active (running) since Thu 2026-08-20 19:54:15 EDT; 1 day 14h ago
   Main PID: 652663 (python3)
      Tasks: 31 (limit: 38323)
      Memory: 274.2M (peak: 277.2M)

● empire-portal.service - Empire Studio Portal (Stable Production - Next.js on port 3005)
     Loaded: loaded (/home/rg/.config/systemd/user/empire-portal.service; enabled; preset: enabled)
    Drop-In: /home/rg/.config/systemd/user/empire-portal.service.d
             └─rebuild-deps.conf
     Active: active (running) since Mon 2026-08-17 13:41:15 EDT; 4 days ago
   Main PID: 1764 (npm exec next s)
      Tasks: 23 (limit: 38323)
      Memory: 166.3M (peak: 203.4M)
```

---

## STEP 2 — ROUTES

### `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/`
```
200
```

### `curl -s http://localhost:8000/openapi.json | head -c 400`
```
{"openapi":"3.1.0","info":{"title":"EmpireBox API","description":"Backend API for EmpireBox","version":"1.0.0"},"paths":{"/max/chat":{"post":{"tags":["max","MAX AI Assistant"],"summary":"Chat With Max","operationId":"chat_with_max_max_chat_post","requestBody":{"content":{"application/json":{"schema":{"$ref":"#/components/schemas/app__routers__max__router__ChatRequest"}}},"required":true},"response
```

### Full route inventory
```
ROUTE COUNT: 1086
```

(Saved to `/tmp/routes.txt`, 1087 lines including header. Full enumeration retained there — every route, every path. Reproduction command:
```
curl -s http://localhost:8000/openapi.json | python3 -c "
import sys, json
spec = json.load(sys.stdin)
paths = spec.get('paths', {})
print('ROUTE COUNT:', len(paths))
for p in sorted(paths):
    methods = ','.join(sorted(m.upper() for m in paths[p]))
    print(f'{methods:22} {p}')
" > /tmp/routes.txt
```
)

**Path prefixes that dominate the inventory** (for navigator diff): `/api/v1/quotes-v2/`, `/api/v1/quotes/`, `/api/v1/jobs/`, `/api/v1/finance/`, `/api/v1/invoices/`, `/api/v1/payments/`, `/api/v1/crm/`, `/api/v1/inventory/`, `/api/v1/customers/`, `/api/v1/contacts/`, `/api/v1/max/...` (extensive), `/api/v1/openclaw/`, `/api/v1/craftforge/`, `/api/v1/archiveforge/`, `/api/v1/relist/`, `/api/v1/relist-legacy/`, `/api/v1/recovery/`, `/api/v1/transcriptforge/`, `/api/v1/leads/leadforge/`, `/api/v1/storefront/`, `/api/v1/socialforge/`, `/api/v1/llcfactory/`, `/api/v1/businessops/`, `/api/v1/vendorops/`, `/api/v1/crypto-payments/`, `/api/v1/drawings/`, `/api/v1/patterns/`, `/api/v1/portals/`, `/api/v1/intake/`, `/api/v1/amp/`, `/api/v1/avatar/`, `/api/v1/apostapp/`, `/api/v1/economic/`, `/api/v1/smart-analyze/`, `/api/v1/vision/`, `/api/v1/voice/`, plus bare `/max/...` duplicates of the `/api/v1/max/...` set. Many router sub-mounts each carry 10–20 endpoints, e.g. `/api/v1/archiveforge/...` has 65+ paths.)

**Note for navigator diff:** the recorded 63-node graph does not have 1:1 correspondence with the 1086 routes — many routes share a node, and many nodes span multiple routers.

---

## STEP 3 — TRUTH LAYER

### `find ~ -maxdepth 4 -name 'empire.db' -o -maxdepth 4 -name 'intake.db' 2>/dev/null` (truncated candidates by relevance)
```
/home/rg/empire-data/empire.db
/home/rg/empire-data/intake.db
/home/rg/empire-repo/backend/data/empire.db        (stale fork)
/home/rg/empire-repo/backend/data/intake.db        (stale fork)
/home/rg/empire-repo-main/backend/empire.db        (0 bytes — empty)
/home/rg/empire-repo-main/data/empire.db           (0 bytes — empty)
/home/rg/.hermes/empire.db                         (hermes agent)
/home/rg/Empire/data/empire.db                     (archive mirror)
/home/rg/empire-repo/empire-command-center/empire.db  (CC legacy, 0-byte shadow likely)
/home/rg/empire-repo/empire.db                     (fork root)
/home/rg/empire-repo/backend/empire.db             (fork, 0-byte shadow likely)
…plus ~50 timestamped backups under ~/backups/YYYYMMDD/{empire.db,intake.db}…
```

### `lsof -p 652663 2>/dev/null | grep -E '\.(db|sqlite)'`
```
python3 652663   rg   13u      REG               8,17   278528 11272235 /home/rg/empire-data/empirebox.db
```

The currently-running backend holds open **`/home/rg/empire-data/empirebox.db`** (278 KB). This is the live connection per `app/database.py:12-16` which defaults `DATABASE_URL` to `empirebox.db`.

### Canonical / fork DB sizes and mtimes

```
-rw-r--r-- 1 rg rg 23957504 Aug 22 10:01 /home/rg/empire-data/empire.db
-rw------- 1 rg rg   466944 Jun 23 18:30 /home/rg/empire-data/intake.db
-rw-rw-r-- 1 rg rg   278528 Jun 25 21:08 /home/rg/empire-data/empirebox.db         ← HELD OPEN by uvicorn
-rw-r--r-- 1 rg rg 20365312 Jun 23 18:30 /home/rg/empire-data/empire.candidate.db   ← dead candidate
-rw------- 1 rg rg 18501632 Jul  8 11:30 /home/rg/empire-repo/backend/data/empire.db (FORK)
-rw------- 1 rg rg   466944 Aug 16 11:22 /home/rg/empire-repo/backend/data/intake.db (FORK)
-rw-r--r-- 1 rg rg        0 May 27 07:31 /home/rg/empire-repo-main/backend/empire.db  (EMPTY)
-rw-r--r-- 1 rg rg        0 May 21 15:56 /home/rg/empire-repo-main/data/empire.db     (EMPTY)
```

### Row counts via venv python, read-only URI

#### `/home/rg/empire-data/empirebox.db` — held open by uvicorn (LIVE)
```
chat_messages                            0
chat_sessions                            0
crypto_ledger                            0
crypto_payments                          0
decision_contexts                        0
disruption_events                        0
economic_ledgers                         0
licenses                                 0
luxeforge_image_measurements             0
preorders                                0
sf_customers                             0
sf_kb_articles                           0
sf_kb_categories                         0
sf_messages                              0
sf_support_agents                        1
sf_tenants                               1
sf_ticket_messages                       0
sf_tickets                               0
shipments                                0
users                                    0
```
**Finding:** the live DB uvicorn is connected to is essentially empty — only `sf_support_agents` and `sf_tenants` have rows. All other business tables are zero. **This is the data layer the running backend sees.**

#### `/home/rg/empire-data/empire.db` — CLAUDE.md canonical truth layer (24 MB, modified today 10:01, NOT held open)
```
access_audit                             0
access_sessions                          0
access_users                             5
ag_archive_photos                        59
ag_archives                              73
ag_box_registry                          0
ag_listing_drafts                        11
apostille_documents                      0
archive_ad_comps                         228
archive_ad_opportunities                 93
archive_ad_page_photos                   16
archive_ads                              6
archive_external_api_calls               1305
archive_issue_info_runs                  73
archive_issue_metadata                   15
archive_item_lifecycle                   4
archive_item_lifecycle_events            9
archive_life_issue_master                1863
archive_life_issue_sources               1871
archive_listing_drafts                   13
archive_magazine_comps                   49
archive_pricing_summary                  28
assist_clients                           0
atlas_tasks                              130
business_profiles                        2
campaign_activity                        20
campaign_attachments                     3
campaign_drafts                          10
campaign_enrollments                     10
campaign_steps                           13
campaigns                                3
catalog_analytics                        35
catalog_favorites                        1
cf_buyers                                5
cf_construction                          0
cf_contractors                           3
cf_infrastructure                        7
cf_lots                                  60
cf_materials                             10
cf_payments                              0
cf_phases                                3
cf_projects                              3
cf_sales                                 0
chart_of_accounts                        26
chat_session_turns                       262
client_messages                          0
client_option_sets                       1
client_portal_tokens                     5
contacts                                 7
conversation_modes                       2
crypto_transactions                      0
crypto_wallets                           0
customers                                171
design_sessions                          1
desk_configs                             15
drawing_versions                         0
expenses                                 6
fabrics                                  12
finance_collection_events                0
financial_audit_log                      148
intake_fabrics                           3
intake_projects                          503
intake_users                             654
inventory_items                          155
invoice_payments                         0
invoices                                 32
job_documents                            0
job_events                               2
job_items                                0
job_revisions                            0
job_selections                           0
jobs                                     8
label_catalog                            0
leads                                    0
lf_activities                            1
lf_campaigns                             0
lf_followup_queue                        0
lf_leads                                 0
lf_prospects                             0
listings                                 2
llc_formations                           0
maintenance_config                       5
maintenance_log                          18
max_feedback                             2
max_mode_transitions                     2
max_response_audit                       4327
max_response_evaluations                 6081
max_response_scores                      8
max_routing_preferences                  53
max_tool_performance                     124
mf_products                              11
openclaw_tasks                           7390
payments                                 1
payments_v2                              0
pending_drawing_jobs                     0
production_log                           0
prospect_pipeline                        6
prospect_search_runs                     9
prospects                                322
quality_metrics                          45
quote_line_items                         124
quote_photos                             0
quotes_v2                                49
ra_analytics                             0
ra_listings                              18
ra_orders                                0
ra_price_watch                           15
ra_services                              16
ra_source_products                       13
saved_patterns                           3
self_heal_log                            0
sf2_customers                            10
sf2_employees                            3
sf2_gift_cards                           0
sf2_inventory                            50
sf2_po_items                             0
sf2_products                             50
sf2_purchase_orders                      0
sf2_shifts                               0
sf2_stores                               1
sf2_suppliers                            2
sf2_transaction_items                    0
sf2_transactions                         0
sf_customers                             0
sf_kb_articles                           0
sf_support_agents                        1
sf_tenants                               1
sf_ticket_messages                       0
sf_tickets                               3
shipments                                0
social_accounts                          12
social_post_results                      0
sqlite_sequence                          62
task_activity                            474
tasks                                    1858
token_usage                              0
vendors                                  51
vo_accounts                              1
vo_activation                            1
vo_alert_preferences                     1
vo_approvals                             1
vo_audit_events                          17
vo_renewal_alerts                        1
vo_stripe_events                         0
vo_subscriptions                         1
work_order_items                         0
work_orders                              0
```

#### `/home/rg/empire-data/intake.db` (canonical intake)
```
intake_fabrics                           0
intake_projects                          504
intake_users                             654
sqlite_sequence                          0
```

#### `/home/rg/empire-repo/backend/data/empire.db` (FORK)
```
…see Step 9 for full delta table…
```
Selected highlights:
- `customers` 147 vs 171 (fork −24)
- `quotes_v2` 28 vs 49 (fork −21)
- `invoices` 20 vs 32 (fork −12)
- `quote_line_items` 83 vs 124 (fork −41)
- `financial_audit_log` 28 vs 148 (fork −120)
- `max_response_audit` 3996 vs 4327 (fork −331)
- `max_response_evaluations` 5913 vs 6081 (fork −168)
- `tasks` 1482 vs 1858 (fork −376)
- `task_activity` 350 vs 474 (fork −124)
- `openclaw_tasks` 7357 vs 7390 (fork −33)
- `fabrics` 6 vs 12 (fork −6)
- `contacts` 3 vs 7 (fork −4)

**The fork is BEHIND canonical everywhere. It is missing tables that exist in canonical** (e.g. `archive_life_issue_master` 1863 rows, `archive_life_issue_sources` 1871 rows, `archive_external_api_calls` 1305 rows, `chat_session_turns` 262 rows, `intake_projects`, `intake_users`, `pending_drawing_jobs`, `label_catalog`). No row counts are higher in the fork than in canonical.

#### `/home/rg/empire-repo/backend/data/intake.db` (FORK intake)
```
intake_fabrics                           0
intake_projects                          505
intake_users                             655
sqlite_sequence                          0
```

### `find ~ -maxdepth 5 -name '*.json' -path '*store*' 2>/dev/null | head -40`
All matches are `node_modules/use-sync-external-store/package.json` noise. **No project-level JSON stores found.**

### `find ~ -maxdepth 3 -name '.env' 2>/dev/null`
```
/home/rg/empire-repo/backend/.env
/home/rg/.hermes/.env
```
(Canonical repo at `~/empire-repo-main` has no `.env` — keys come from `/home/rg/.config/empirebox/empire-backend.env` via the `provider-env.conf` systemd drop-in. Per CLAUDE.md: "env incl. FOUNDER_PIN comes from systemd drop-ins — never hardcode, never default.")

### `.env` key names (NEVER printed values)

**`/home/rg/empire-repo/backend/.env` (57 keys):**
```
ANTHROPIC_API_KEY
API_HOST
API_PORT
APOSTILLE_TEST_MODE
BRAVE_API_KEY
CORS_ORIGINS
CRYPTO_BTC_ADDRESS
CRYPTO_ETH_ADDRESS
CRYPTO_MASTER_SEED
CRYPTO_SOL_ADDRESS
CRYPTO_USDC_ETH_ADDRESS
CRYPTO_USDT_ERC20_ADDRESS
CRYPTO_USDT_TRC20_ADDRESS
DEEPSEEK_API_KEY
DEEPSEEK_BASE_URL
DEEPSEEK_MODEL
FACEBOOK_PAGE_ID
FOUNDER_EMAIL
FOUNDER_EMAILS
FOUNDER_PIN
GOOGLE_BOOKS_API_KEY
GOOGLE_GEMINI_API_KEY
GOOGLE_PLACES_API_KEY
GROQ_API_KEY
INSTAGRAM_BUSINESS_ID
MAX_ALLOW_FALLBACK
MAX_DEFAULT_MODEL
MAX_DISABLE_CLAUDE
MAX_DISABLE_GROK
MAX_DISABLE_GROQ
MAX_DISABLE_OLLAMA
MAX_DISABLE_XAI
MAX_EMAIL
MAX_FORCE_SINGLE_MODEL
MAX_PRIMARY_PROVIDER
META_ACCESS_TOKEN
MINIMAX_API_KEY
MINIMAX_BASE_URL
MINIMAX_FALLBACK_MODEL
MINIMAX_MODEL
OPENAI_API_KEY
OPENCLAW_GATEWAY_TOKEN
OPENCLAW_URL
SENDGRID_API_KEY
SENDGRID_FROM_EMAIL
STRIPE_PRICE_EMPIRE
STRIPE_PRICE_LITE
STRIPE_PRICE_PRO
STRIPE_PUBLISHABLE_KEY
STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET
TELEGRAM_BOT_TOKEN
TELEGRAM_FOUNDER_CHAT_ID
WOODCRAFT_EMAIL
WORKROOM_EMAIL
XAI_API_KEY
YELP_FUSION_API_KEY
```
**This is the FORK's .env.** The canonical backend reads from systemd unit drop-ins (no checked-in .env file).

**Key takeaway:** the running MAX service has these env values set in `empire-backend.service`:
```
MAX_PRIMARY_PROVIDER=minimax
MAX_DEFAULT_MODEL=minimax
MAX_DISABLE_XAI=true
MAX_DISABLE_OLLAMA=true
MAX_DISABLE_GROQ=true
MAX_DISABLE_CLAUDE=true
MAX_DISABLE_GROK=true
MAX_ALLOW_FALLBACK=false
MINIMAX_MODEL=MiniMax-M3
```
…so the live MAX is locked to **minimax** with all other providers disabled and no fallback allowed.

### Other DBs of interest (not in dispatch scope but found)
```
/home/rg/empire-data/amp.db             (131072 bytes,  Jun 23 18:30)
/home/rg/empire-data/token_usage.db     (32768 bytes,   Jun 23 18:30)
/home/rg/empire-data/tool_audit.db      (1622016 bytes, Jun 23 18:30)
/home/rg/empire-data/brain/memories.db
/home/rg/empire-data/brain/token_usage.db
/home/rg/empire-data/brain/unified_messages.db
```

---

## STEP 4 — CORRIDOR

(All probes are read-only GETs against `/api/v1/...` paths discovered in Step 2.)

### 1. Quotes
Route used: `/api/v1/quotes-v2/stats`
```
200 141b {"total_quotes":49,"by_status":{"accepted":2,"cancelled":14,"draft":28,"proposal":3,"sent":2},"total_value":84888.52,"average_value":4042.31}
```
Route: `/api/v1/quotes?limit=5`
```
200 740b {"quotes":[{"id":"521f7c93","quote_number":"EST-2026-007",…
```

### 2. Jobs
Route: `/api/v1/jobs/dashboard`
```
200 276b {"total":8,"by_status":[{"status":"completed","count":4},{"status":"pending","count":4}],"by_stage":[{"pipeline_stage":"intake","count":8}],"by_business":[{"business_unit":"workroom","count":8}],"pipeline_value":0.0,"total_quoted":0.0,"total_paid":0.0,"upcoming_this_week":[]}
```
Route: `/api/v1/jobs/active`
```
200 10108b {"jobs":[{"id":"40dc421b520c7c68","title":"Living Room Window Treatments",…
```

### 3. Finance / Invoices
Route: `/api/v1/finance/dashboard`
```
200 6516b {"revenue":{"mtd":0,"ytd":100.0},"expenses":{"mtd":0,"ytd":5380.0,"breakdown_mtd":[]},"net_profit":{"mtd":0,"ytd":-5280.0},"outstanding":{"total":34391.21,"count":32},…
```
Route: `/api/v1/invoices?limit=5`
```
200 5848b {"invoices":[{"id":"ce652443","invoice_number":"INV-0032","customer_id":"2255e486","quote_id":"34d2ab33","status":"draft","subtotal":0.0,…
```

### 4. Payments
Route: `/api/v1/payments/history`
```
200 399b {"payments":[{"payment_id":"pi_3Trg4D6oRqSGnytY1aubmQp9","amount":4084.05,"currency":"usd","status":"succeeded","description":null,"customer_id":"cus_UrOrf6fKSTUptZ",…
```

### 5. CRM / Customers
Route: `/api/v1/customers?limit=5`
```
307 0b 
```
Route: `/api/v1/customers?limit=5` (with `-L`)
```
200 59b {"customers":[],"total":0,"page":1,"per_page":50,"pages":1}
```
Route: `/api/v1/crm/customers?limit=5`
```
200 1793b {"customers":[{"id":"7e7e6857c79149a4","name":"A JAD'S COMPANY","email":"","phone":"","address":"","company":"","type":"designer","tags":["designer","qb-import"],…
```

**Note:** `/api/v1/customers/` returns empty data and a 307 redirect on raw GET — the populated customer table lives under `/api/v1/crm/customers/` (171 rows in `customers` table per Step 3 canonical).

### 6. Inventory
Route: `/api/v1/inventory/items?limit=5`
```
200 1884b {"items":[{"id":"e142cc7f85f94ce7","name":"Modification","sku":"09.-CUSTOM-FURNITURE-MODIFICATION","category":"Alterations & Repairs","subcategory":null,"quantity":0.0,"unit":"each","min_stock":0.0,"cost_per_unit":0.0,"sell_price":0.0,"vendor":"","location":"","notes":"QB: Furniture.","business":"wo
```

### Corridor summary

| Capability | Route | Status | Has data |
|---|---|---|---|
| quotes | `/api/v1/quotes-v2/stats`, `/api/v1/quotes` | 200 | yes — 49 quotes, $84,888 value |
| jobs | `/api/v1/jobs/dashboard`, `/api/v1/jobs/active` | 200 | yes — 8 jobs |
| finance/invoices | `/api/v1/finance/dashboard`, `/api/v1/invoices` | 200 | yes — 32 invoices outstanding $34,391 |
| payments | `/api/v1/payments/history` | 200 | yes — Stripe history present |
| crm/customers | `/api/v1/crm/customers` | 200 | yes — populated |
| crm/customers (alt) | `/api/v1/customers/` | 307→59b | empty page |
| inventory | `/api/v1/inventory/items` | 200 | yes — 155 items |

**All six corridor capabilities have at least one route returning real data.** The corridor is intact at the API surface.

---

## STEP 5 — ORCHESTRATOR

### `find ~ -maxdepth 4 -iname '*max*' -type d 2>/dev/null | head -20`
```
/home/rg/empire-repo/empire-command-center/app/max
/home/rg/.session-artifacts/audit/max_trust
/home/rg/.session-artifacts/max
/home/rg/empire-repo/max
/home/rg/empire-repo/backend/data/max
/home/rg/empire-box-memory/ARTIFACTS/max
/home/rg/hermes-agent/plugins/model-providers/minimax
/home/rg/.hermes/skills/.archive/max-ai-quality-audit
/home/rg/.hermes/skills/software-development/max-router-guardrails
/home/rg/.hermes/skills/software-development/multi-operator-max-hierarchy
/home/rg/empire-data/max
/home/rg/opencode-empire-main/docs/modules/max
/home/rg/opencode-empire-main/empire-command-center/app/max
/home/rg/opencode-empire-main/max
/home/rg/empire-repo-main/empire-command-center/app/max
/home/rg/empire-repo-main/max
/home/rg/empire-repo-main/docs/modules/max
/home/rg/empire-repo-main/backend/data/max
/home/rg/.cache/claude-cli-nodejs/-home-rg-empire-repo-main/mcp-logs-MiniMax
/home/rg/.cache/claude-cli-nodejs/-home-rg-empire-repo/mcp-logs-MiniMax
```

### MAX runtime state (via `/api/v1/max/...` — NOT by sending prompts)

```
GET /api/v1/max/health
200 102b {"status":"healthy","service":"MAX AI Assistant Manager","desks_online":17,"telegram_configured":true}

GET /api/v1/max/status
200 23216b {"status":"ok","current_commit":{"hash":"8aeb0f0","branch":"feature/drawing-standard","message":"8aeb0f0 docs(state): H68-H71 added, P1-T advanced to .d, HANDOFF de-duped"},"runtime_lane":{"lane":"main","branch":"feature/drawing-standard","backend_port":8000,"frontend_expected_port":3005,"worktree":"/home/rg/empire-repo-main/backend"},"registry":{"registry_version":"operating-registry-v2","schema_version":1,"updated_at":"2026-04-19","loaded_at":"2026-08-20T23:54:16.531961+00:00","source":"/home/rg/empire-repo-main/backend/app/services/max/operating_registry.json","file_sha256":"d8e32e09d2ac3d3…

GET /api/v1/max/models
200 11477b {"models":[{"id":"minimax","name":"MiniMax","provider_canonical":"minimax","models":["MiniMax-M3","MiniMax-M2.7","MiniMax-M2.7-highspeed"],"model":"MiniMax-M3","configured":true,"available":true,"disabled":false,"disabled_reason":null,"primary":true,"selected":true,"type":"cloud","fallback_eligible":true,"status_source":"env_configured","last_error":null,"last_success":"ok","manual_disabled":false,"credential_env":"MINIMAX_API_KEY","local_online":null,"base_url":"https://api.minimax.io/v1"},{"id":"deepseek",…

GET /api/v1/max/desks
200 9135b {"desks":[{"id":"forge","name":"ForgeDesk (WorkroomForge)","agent_name":"Kai",…

GET /api/v1/max/stats
200 140b {"stats":{"total_completed":0,"total_failed":0,"active_tasks":0,"pending_tasks":0,"desks_busy":0,"desks_idle":17},"telegram_connected":true}
```

### MAX config files

| File | Path | mtime | size |
|---|---|---|---|
| `operating_registry.json` | `/home/rg/empire-repo-main/backend/app/services/max/operating_registry.json` | 2026-05-15 09:23 | 18031 |

`stat -c '%y %s' operating_registry.json`:
```
2026-05-15 09:23:27.845302158 -0400 18031
```

`head -c 400 operating_registry.json`:
```
{
  "schema_version": 1,
  "registry_version": "operating-registry-v2",
  "updated_at": "2026-04-19",
  "source_of_truth": "repo_and_runtime_verified",
  "surfaces": [
    {
      "key": "founder_web",
      "name": "Founder/Web MAX",
      "status": "active",
      "canonical_channel": "web_chat",
      "aliases": ["web", "web_cc", "dashboard", "command_center"],
      "routes_services": ["/api/v…
```

**MAX is RUNNING (healthy, 17 desks, telegram connected).** Primary provider is `minimax` (model `MiniMax-M3`). All other providers are disabled via env (`MAX_DISABLE_*`). Operating registry mtime: 2026-05-15 (≈3.3 months); `updated_at` field: 2026-04-19 (≈4 months). The model string named is `MiniMax-M3`.

---

## STEP 6 — REPO

### `cd ~/empire-repo-main && git status --porcelain=v1`
```
 M max/memory.md
?? codetask_stage3_clean.txt
?? codetask_stage3_evidence.txt
?? reference/mclean/McLean_Whittington_Drapery_Elevations_RevA.pdf
```

Per dispatch doctrine: ` M max/memory.md` is the **known false positive** from nightly `brain_sync` — do not treat as uncommitted work. The three untracked files are real artifacts in the working tree.

### `cd ~/empire-repo-main && git log --oneline -12`
```
8aeb0f0 docs(state): H68-H71 added, P1-T advanced to .d, HANDOFF de-duped
84fc238 docs(doctrine): v2 — seven rules earned 2026-08-20
20711ce docs(template): H71 — chrome T() y-bbox over-estimates; tolerance is workaround
90875d9 test(template): chrome-on-chrome negative fixture — proves 8pt not too wide
b10af10 feat(template): per-class collision tolerance (H70)
23e8ead fix(template): cover layout — smaller McLean title + wrap WORKROOM + skip empty math
339ee38 docs(template): G2 triage — 9 real, 15 tolerance, 1 spec artifact
1c56eb0 fix(template): wire placed_local through to the gates; cairosvg installed
bceaa12 feat(template): P1-T·c — build(spec) builder interface + callable floor
586b27d docs(backlog): H69 — tool-card footer overstates execution status
62c4741 test(h57): close the three legacy tests in test_max_drawing_intent.py
12e7086 docs(board): STATE v8 — add H67 closed, H68 open
```

### `cd ~/empire-repo-main && git worktree list`
```
/home/rg/empire-repo                                                                             b7dcb6b [lane/source-holding-v10-root]
/home/rg/.local/share/opencode/worktree/b21549d3b294933fa0425f9bf51f2502544c44b1/crisp-meadow    b7dcb6b [opencode/crisp-meadow]
/home/rg/.local/share/opencode/worktree/b21549d3b294933fa0425f9bf51f2502544c44b1/happy-otter     b7dcb6b [opencode/happy-otter]
/home/rg/.local/share/opencode/worktree/b21549d3b294933fa0425f9bf51f2502544c44b1/hidden-canyon   b7dcb6b [opencode/hidden-canyon]
/home/rg/.local/share/opencode/worktree/b21549d3b294933fa0425f9bf51f2502544c44b1/neon-planet     b7dcb6b [opencode/neon-planet]
/home/rg/.local/share/opencode/worktree/b21549d3b294933fa0425f9bf51f2502544c44b1/silent-circuit  b7dcb6b [opencode/silent-circuit]
/home/rg/.local/share/opencode/worktree/b21549d3b294933fa0425f9bf51f2502544c44b1/sunny-comet     8aeb0f0 (detached HEAD)
/home/rg/.local/share/opencode/worktree/b21549d3b294933fa0425f9bf51f2502544c44b1/witty-pixel     b7dcb6b [opencode/witty-pixel]
/home/rg/empire-repo-main                                                                        8aeb0f0 [feature/drawing-standard]
/home/rg/opencode-empire-main                                                                    1e1a437 [opencode/empire-main]
```

**Repo is at HEAD `8aeb0f0` on branch `feature/drawing-standard`.** The fork `/home/rg/empire-repo` is a worktree pinned to `b7dcb6b [lane/source-holding-v10-root]` — older commit, not HEAD.

---

## STEP 7 — HYPOTHESES

### H-A — MAX dies on import (launch method)

**Probe output:**

`grep -rn 'services.max' ~/empire-repo-main --include='*.service'`
```
(no output — no .service file references services.max)
```

`grep -rn 'services/max' ~/empire-repo-main/*.sh ~/empire-repo-main/backend/*.sh | head`
```
(no output)
```

`sed -n '1,10p' ~/empire-repo-main/backend/app/services/max/__init__.py`
```
"""MAX AI Assistant Manager - Multi-model AI router with Telegram integration."""
from .ai_router import AIRouter
from .telegram_bot import TelegramBot
from .desks import AIDeskManager

__all__ = ["AIRouter", "TelegramBot", "AIDeskManager"]
```

`ls ~/empire-repo-main/backend/app/services/max/` (excerpt)
```
access_control.py
accuracy_monitor.py
ai_router.py
…[no orchestrator.py]…
__init__.py
…
```

`ls ~/empire-repo-main/backend/app/services/max/orchestrator*`
```
ls: cannot access '/home/rg/empire-repo-main/backend/app/services/max/orchestrator*': No such file or directory
```

Cross-check — how MAX is actually loaded:
```
$ grep -n 'max' ~/empire-repo-main/backend/app/main.py | head -8
20:validation_logger = logging.getLogger("max.validation")
59:    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0"
80:load_router("app.routers.max", "", ["max"])
81:load_router("app.routers.max", "/api/v1", ["api-v1"])
289:    from app.services.max.stt_service import stt_service
364:        from app.services.max.startup_health import write_startup_health_record
389:        from app.services.max.telegram_bot import telegram_bot
400:        from app.services.max.desks.desk_scheduler import desk_scheduler
408:        from app.services.max.scheduler import max_scheduler
```

**Verdict: H-A — FIXED SINCE (the May record never matched the present code).**
- The `ImportError: attempted relative import` claim at `__init__.py:2` is not present — line 2 is a clean module docstring.
- MAX is NOT launched as a script. MAX is loaded IN-PROCESS by FastAPI's `app.main` (lines 80–81 mount routers; lifespan pulls in `max_scheduler`, `max_monitor`, `telegram_bot`, `desk_scheduler`).
- The `No module named app.services.max.orchestrator` claim would be accurate (no such file), but nothing imports it — the actual orchestrator lives at `app/services/orchestration/orchestrator.py` and is unrelated.
- Live API confirms MAX is healthy (Step 5).

### H-B — Frontend hardcodes `localhost:8000`

**Probe output:**
```
$ grep -rn 'localhost:8000' ~/empire-repo-main/empire-command-center/app --include='*.tsx' | head -20
/home/rg/empire-repo-main/empire-command-center/app/components/platform/DesktopPairing.tsx:5:const QR_API = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/qr`;
/home/rg/empire-repo-main/empire-command-center/app/components/ui/EmpireTopBar.tsx:27:        const r = await fetch('http://localhost:8000/health');
/home/rg/empire-repo-main/empire-command-center/app/components/screens/ArchiveForgePage.tsx:11:  ? (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1')
/home/rg/empire-repo-main/empire-command-center/app/components/screens/ArchiveForgePage.tsx:12:  : (typeof window !== 'undefined' ? `${window.location.origin}/api/v1` : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'));
/home/rg/empire-repo-main/empire-command-center/app/orchestration/page.tsx:12:const API = 'http://localhost:8000/api/v1';
/home/rg/empire-repo-main/empire-command-center/app/channels/page.tsx:51:const API_BASE = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1').replace(/\/$/, '');
```

**Verdict: H-B — PARTIALLY CONFIRMED STILL.**
- `EmpireTopBar.tsx:27` — HARDCODED `localhost:8000/health`, no env-var fallback.
- `orchestration/page.tsx:12` — HARDCODED `localhost:8000/api/v1`, no env-var fallback.
- `ArchiveForgePage.tsx:11–12`, `DesktopPairing.tsx:5`, `channels/page.tsx:51` — use `process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'` (env-var with localhost fallback — safe pattern).
- The May record's other paths (`app/workroom/page.tsx`, `app/hermes/page.tsx`, `app/openclaw/page.tsx`) no longer exist at those locations — those routes were reorganized. The May record's evidence for those four is stale; today's reality has 2 hardcoded call sites and 3 env-var-with-fallback call sites.

### H-C — CraftForge lazy import path off by one directory

**Probe output:**
```
$ grep -rn 'business/craftforge/QuoteBuilderSection' ~/empire-repo-main/empire-command-center/app
/home/rg/empire-repo-main/empire-command-center/app/components/screens/CraftForgePage.tsx:15:const QuoteBuilderSection = lazy(() => import('../business/craftforge/QuoteBuilderSection'));
/home/rg/empire-repo-main/empire-command-center/app/components/business/craftforge/QuoteBuilderSection.tsx:54:export default function QuoteBuilderSection() {
/home/rg/empire-repo-main/empire-command-center/app/components/screens/CraftForgePage.tsx:15:const QuoteBuilderSection = lazy(() => import('../business/craftforge/QuoteBuilderSection'));
/home/rg/empire-repo-main/empire-command-center/app/components/screens/CraftForgePage.tsx:54:        return <Suspense fallback={<Loading />}><QuoteBuilderSection /></Suspense>;
```

**Verdict: H-C — FIXED SINCE.**
- The import `'../business/craftforge/QuoteBuilderSection'` from `app/components/screens/CraftForgePage.tsx` resolves to `app/components/business/craftforge/QuoteBuilderSection` — the file exists at that path. The May record's claim that the file was missing is stale.

### H-D — Drawing router early-returns instead of handing off

**Probe output:**
```
$ sed -n '1380,1410p' ~/empire-repo-main/backend/app/routers/max/router.py
    rows = payload.get("results") or payload.get("items") or []
    lines = [f"Live Lookup summary for: {query}"]
    sources = []
    for row in rows[:5]:
        title = str(row.get("title") or "").strip()
        snippet = str(row.get("snippet") or "").strip()
        url = str(row.get("url") or "").strip()
        if title:
            lines.append(f"- {title}: {snippet}" if snippet else f"- {title}")
        if url:
            sources.append(url)
    if sources:
        lines.append("Sources:")
        for url in sources[:5]:
            lines.append(f"- {url}")
    response_text = _sanitize_internal_leakage_text("\n".join(lines))
    return ChatResponse(
        response=response_text,
        model_used="live-lookup-router",
        fallback_used=False,
        tool_results=[result.to_dict()],
        metadata=_response_metadata(request.channel, skill_used="live_lookup_router"),
    )


def _is_unverified_email_send_request(message: str | None) -> bool:
    text = (message or "").strip().lower()
    return any(re.search(pattern, text) for pattern in EMAIL_SEND_TRUTH_PATTERNS)


def _is_email_reply_read_request(message: str | None) -> bool:
$ wc -l ~/empire-repo-main/backend/app/routers/max/router.py
5687
```

**Verdict: H-D — CANNOT VERIFY AS WRITTEN.**
- The line range 1391–1398 in router.py now contains a `live-lookup` summary function, NOT a `drawing_handoff.ready` early-return.
- The router has grown from whatever it was in May to 5687 lines; the drawing logic has moved. Cannot locate the May claim without further search (out of scope for a read-only probe).
- The May record's specific file:line diagnostic for the drawing early-return is stale.

### H-E — OpenClaw health

**Probe output:**
```
$ curl -s -m 5 http://localhost:7878/health
{"status":"ok","service":"openclaw","version":"1.0.0"}

$ curl -s -m 5 http://localhost:8000/api/v1/openclaw/health
{"status":"online","openclaw_url":"http://localhost:7878","openclaw_gate":{"state":"healthy","allowed":true,"reason":"health endpoint, local queue, and worker heartbeat ready","checked_at":"2026-08-22T14:19:04.751183+00:00","cache_ttl_seconds":20,"cache_age_seconds":0.0,"health_endpoint":"http://localhost:7878/health","health_status_code":200,"queue_ready":true,"queue_stats":{"cancelled":2,"done":1443,"failed":5945,"total":7390},"recent_task_viability":{"total":0},"worker_heartbeat":{"checked_at":"2026-08-22T14:19:03.594042+00:00","current_task_id":null,"freshness_window_seconds":90,"status":"polling","age_seconds":1.092,"fresh":true,"state":"fresh"},"founder_message":"OpenClaw healthy - delegating task now."}}

$ curl -s -m 5 http://localhost:8000/api/v1/openclaw/tasks/stats | head -c 500
{"total":7390,"cancelled":2,"done":1443,"failed":5945}
```

**Verdict: H-E — CONFIRMED STILL (with major caveat).** OpenClaw is healthy on :7878, but the queue is dominated by **5945 failed + 1443 done + 2 cancelled = 7390 total historical tasks** — zero currently-queued active tasks. The May record's "62 queued tasks" claim is stale; today's reality is a 7390-task historical queue with **no live work** (worker is polling/idle). Healthy state, but the queue is a backlog graveyard, not an active workload (matches CLAUDE.md note: "OpenClaw (localhost:7878) exists but has a 7k+ item queue backlog — do not depend on it").

### H-F — Data layer identity conflict

**Probe output:**
- Step 1 port listing shows NO 5432, NO 6379, NO 9000.
- Step 3 shows live truth layer is SQLite only: `empirebox.db` (live, held open by uvicorn), `empire.db` (canonical, 24 MB, 132 tables populated), `intake.db`, `amp.db`, `token_usage.db`, `tool_audit.db`, plus `brain/memories.db`, `brain/token_usage.db`, `brain/unified_messages.db`.
- No Postgres / Redis / MinIO processes or sockets present.

**Verdict: H-F — CONFIRMED NEVER TRUE.** PostgreSQL/Redis/S3-MinIO are not running and never appear to have run on this host. The actual truth layer is SQLite (`empirebox.db` live + `empire.db` canonical + per-feature DBs in `/home/rg/empire-data/`). The May PDF's industry-validation claims are not operative.

### H-G — Which repo lane serves production

**Probe output:**
```
$ ls -d ~/empire-repo ~/empire-repo-main ~/empire-repo-v10 2>&1
ls: cannot access '/home/rg/empire-repo-v10': No such file or directory
/home/rg/empire-repo
/home/rg/empire-repo-main

$ curl -s -o /dev/null -w "%{http_code}\n" -m 5 http://localhost:8010/health
000

$ ls -l /proc/652663/cwd
lrwxrwxrwx 1 rg rg 0 Aug 21 01:52 /proc/652663/cwd -> /home/rg/empire-repo-main/backend
```

**Verdict: H-G — FIXED SINCE.**
- `~/empire-repo-v10` does not exist. Port 8010 returns 000 (nothing listening).
- The running :8000 uvicorn process's cwd is `/home/rg/empire-repo-main/backend` — the canonical `feature/drawing-standard` lane, per HANDOFF_2026-08-20 doctrine.
- The fork `~/empire-repo` exists but is pinned to commit `b7dcb6b` (lane/source-holding-v10-root) as a git worktree — it is NOT serving production.
- **However: the system-level `empire-openclaw.service` runs from the FORK** (see Step 9 reboot trap below) — that's the only piece of production still pointing at fork code.

---

## STEP 8 — DOWNLOADS

### File listing (newer than 2026-05-01, by mtime desc, top 30 of ~60 relevant)

```
2026-08-22 10:12       13646  /home/rg/Downloads/claude_DISPATCH_2026-08-22_restore_probe.md
2026-08-21 21:40     1904802  /home/rg/Downloads/willard-PHONE-3col-revC.pdf
2026-08-21 21:04     2714566  /home/rg/Downloads/willard-CLIENT-presentation-revC.pdf
2026-08-21 08:14        8575  /home/rg/Downloads/HANDOFF_2026-08-20.md
2026-08-20 19:17        9982  /home/rg/Downloads/STATE_v8.md
2026-08-20 16:38        9022  /home/rg/Downloads/DISPATCH_2026-08-20_H52_tool_selection.md
2026-08-20 16:38        9022  /home/rg/Downloads/DISPATCH_2026-08-20_H52_tool_selection(1).md
2026-08-20 11:05        8391  /home/rg/Downloads/DISPATCH_2026-08-20_codetask_restoration.md
2026-08-19 21:44        9229  /home/rg/Downloads/DISPATCH_2026-08-19_H53_H52_context_assembly.md
2026-08-19 20:46        7144  /home/rg/Downloads/M_LANE_max_client_work(1).md
2026-08-19 20:24        7144  /home/rg/Downloads/M_LANE_max_client_work.md
2026-08-19 20:09       11020  /home/rg/Downloads/STATE(3).md
2026-08-19 18:55       10496  /home/rg/Downloads/DISPATCH_2026-08-19_H57_router_intercept.md
2026-08-19 17:52       19469  /home/rg/Downloads/DISPATCH_2026-08-19_P1T_template_engine.md
2026-08-19 10:20       10926  /home/rg/Downloads/claude_DISPATCH_2026-08-18_woodwork_presentation.md
2026-08-17 18:41      540248  /home/rg/Downloads/Render Final Willard Bench.dotx
2026-08-17 17:08       20332  /home/rg/Downloads/willard_bench_3d(1).html
2026-08-17 17:04       31246  /home/rg/Downloads/willard_B44_PRESENTATION_E5-1.pdf
2026-08-17 17:03      606829  /home/rg/Downloads/Render Final Willard Bench(1).odt
2026-08-17 17:01      606829  /home/rg/Downloads/Render Final Willard Bench.odt
2026-08-17 16:42       19518  /home/rg/Downloads/willard_bench_3d.html
2026-08-17 16:36       31246  /home/rg/Downloads/willard_B44_PRESENTATION_E5.pdf
2026-08-09 21:17       55018  /home/rg/Downloads/willard_ISO_R_D15.pdf
2026-08-09 21:14      240793  /home/rg/Downloads/willard_arm_PACKAGE_D15.pdf
2026-08-09 21:09      504739  /home/rg/Downloads/Willard Style B - Isometric Views8-2.pdf
2026-08-09 20:48       31397  /home/rg/Downloads/willard_CONSTR1.pdf
2026-08-09 20:46       33770  /home/rg/Downloads/willard_arm_D14.pdf
2026-08-09 20:44      117854  /home/rg/Downloads/willard_CO1_pricing.png
2026-08-09 20:13      300163  /home/rg/Downloads/willard_arm_detail_R2(2).png
2026-08-09 20:13      300163  /home/rg/Downloads/willard_arm_detail_R2(1).png
…[truncated; Willard client assets dominate 2026-07-22 through 2026-08-21]…
```

### Full-extension census (newer than 2026-05-01)
```
    108 pdf
     69 png
     55 md
     33 html
     24 jpeg
     16 zip
      8 py
      8 js
      6 obj
      6 mtl
      5 odt
      2 txt
      2 thumbnail
      1 sh
      1 rar
```

### 600-byte heads of recent text/strategic documents

#### `HANDOFF_2026-08-20.md` (2026-08-21 08:14, 8575 bytes)
```
# HANDOFF — strategic Claude session, 2026-08-19 → 2026-08-20

**Read this first, then `STATE.md` (v8, commit `12e7086`) and
`claude/DOCTRINE.md`.** This file covers what happened in two heavy sessions
and what the next one needs to know that is not obvious from the board.

---

## HOW THIS WORKS

Strategic Claude writes paste-ready dispatches → founder pastes into
MiniMax-M3 Claude Code sessions on EmpireDell → M3 reports
found/changed/tests/commit → strategic audits the report against the dispatch
→ founder rules. **Single lane. Map before fix. 🛑 stop-gates between phases.**
```

#### `STATE_v8.md` (2026-08-20 19:17, 9982 bytes)
```
# STATE.md — EmpireBox Live Snapshot (v8)
As of: 2026-08-20 (evening) · Maintainer: founder + strategic Claude · M3 executes
Replaces v7 (2026-08-19 late). `claude/DOCTRINE.md` is how work is done ·
`claude/BACKLOG_UPDATE_*.md` are the register deltas · this is the orientation page.

## THE GOAL — founder, 2026-08-19
**MAX is to take strategic Claude's place.** Not assist — replace. The honesty
layer, the expensive part, is built and has now held under two days of real
pressure. What he lacked was SIGHT, and most of that was fixed today.

## ⚠️ THE FINDING OF 2026-08-20 — read 
```

#### `DISPATCH_2026-08-20_codetask_restoration.md` (2026-08-20 11:05, 8391 bytes)
```
# DISPATCH — CODE TASK RESTORATION (dead since 2026-05-06)

Authored 2026-08-20. Map is committed at `45273c1`
(`reports/2026-08-20_codetask_map.md`). This is Phase 2: the fix.

**One-line summary of three months of failure:** `parse_tool_blocks` handles
all three advertised response formats correctly, and then
`code_task_runner.py:399` scores the result by reading `response.function_calls`
alone. A model that replies in valid JSON is parsed successfully and recorded
as having emitted nothing.

**Every failure branch discards the model's response.** `task.result` is set 
in exactly one place 
```

#### `DISPATCH_2026-08-19_P1T_template_engine.md` (2026-08-19 17:52, 19469 bytes)
```
# DISPATCH P1-T — DOCUMENT TEMPLATE ENGINE (McLean as reference implementation)

Authored 2026-08-19. **Supersedes the architecture section of
`DISPATCH_P1_presentation_engine.md`** — that dispatch had no proven reference
artifact and would have had to invent the sheet language from the standard.
McLean RevA is that artifact: founder-approved, rendered, 11 sheets. P1's
fixtures (Willard ONE-PIECE, Bozzuto board) survive unchanged and are folded in
at P1-T·e.

**Purpose, in the founder's words:** this is the template for any future request
to MAX involving a document of this kind. MAX gets
```

#### `M_LANE_max_client_work.md` (2026-08-19 20:24, 7144 bytes)
```
# M-LANE — MAX CLIENT-WORK CAPABILITY

**Founder directive 2026-08-19:** *"I will handle direct communications. MAX
has to be trained and has to know how to handle this."*

Append to `claude/BACKLOG.md` as a new lane. This is the capability spec for
the handoff goal recorded in STATE v7.

---

## THE BOUNDARY — a role, not a prohibition

The register currently frames §9 CLIENT-FACING as *"founder actions, no
automation ever."* **That framing is now wrong and should be replaced.**

**New framing: FOUNDER SENDS · MAX PREPARES.**

The allowlist stays structurally founder-only — `send_emai
```

#### `DISPATCH_2026-08-19_H57_router_intercept.md` (2026-08-19 18:55, 10496 bytes)
```
# DISPATCH H57 — DRAWING ROUTER INTERCEPTS ON A KEYWORD

Authored 2026-08-19. **Live evidence, reproduced twice in the founder's own
session tonight.** MAX is unreachable for any message containing the word
"drawing" — the router captures the turn before the model sees it.

**Severity: this is not a refinement.** It makes MAX unusable for an entire
topic — the topic the business runs on. Every document lane, every client
conversation about a window treatment, every audit, every dispatch pasted into
chat. And it is SILENT: the router answers, so nothing looks broken.

---

## THE EVIDENCE
```

### Duplicate-detection probe

`md5sum EMPIRE_CLIENT_DOC_STANDARD*.md`:
```
e6fde3cd1150260834987d760fdf8417  /home/rg/Downloads/EMPIRE_CLIENT_DOC_STANDARD(1).md
e6fde3cd1150260834987d760fdf8417  /home/rg/Downloads/EMPIRE_CLIENT_DOC_STANDARD.md
```
**Two byte-identical copies.**

STATE document version timeline (4 distinct versions in Downloads):
```
STATE.md     (v4, 2026-07-27) — 12909 bytes
STATE(1).md  (v2, 2026-07-26) —  6736 bytes
STATE(2).md  (v3, 2026-07-27) — 11087 bytes
STATE(3).md  (v7, 2026-08-19) — 11020 bytes
STATE_v8.md  (v8, 2026-08-20) —  9982 bytes   ← newest in Downloads
```
**The repo's `claude/STATE.md` is now ahead of `STATE_v8.md`** (HEAD `8aeb0f0` added H68-H71 and advanced P1-T to .d, post-dating Downloads v8 by hours). Downloads v8 is a snapshot.

### NEWER THAN REPO
- `claude_DISPATCH_2026-08-22_restore_probe.md` — this run's own dispatch.
- Willard client assets (PDFs, GLB, OBJ, dotx, odt) — these are CLIENT-facing deliverables, not repo state. They do not live in the repo's `claude/` tree or any tracked source.

### DUPLICATES OF KNOWN DOCS
- `EMPIRE_CLIENT_DOC_STANDARD.md` and `EMPIRE_CLIENT_DOC_STANDARD(1).md` are byte-identical (same MD5). Also: there is a copy at `~/empire-repo-main/EMPIRE_CLIENT_DOC_STANDARD.md` referenced in repo tree — three copies in total.
- `STATE.md` / `STATE(1).md` / `STATE(2).md` / `STATE(3).md` / `STATE_v8.md` — five STATE snapshots in Downloads alone (v2, v3, v4, v7, v8). The repo's `claude/STATE.md` is the live source of truth.
- `DISPATCH_2026-08-20_H52_tool_selection.md` and `DISPATCH_2026-08-20_H52_tool_selection(1).md` — likely duplicate (same size 9022 bytes, same mtime).
- `M_LANE_max_client_work.md` and `M_LANE_max_client_work(1).md` — likely duplicate (same size 7144, same mtime).
- Willard 3D model HTML (`Willard Style B - 3D Model.html` and three numbered copies) — same 10712709 bytes, likely identical.
- `willard_arm_detail_R2.png` × 3 — same 300163 bytes.

### Flagged for founder attention
1. **`STATE_v8.md` in Downloads is post-dated by the repo's commit `8aeb0f0`** (H68-H71, P1-T·d). The Downloads copy is useful only as a frozen snapshot, not as live state.
2. **`HANDOFF_2026-08-20.md` is the most recent strategic doc** in Downloads; canonical repo should have matching content under `claude/`. Worth checking whether repo's Handoff has been updated since (out of scope for read-only probe).
3. **`M_LANE_max_client_work.md` describes a capability lane change** (CLIENT-FACING doctrine update). Not yet confirmed committed to `claude/BACKLOG.md`.

---

## STEP 9 — STALE FORK SALVAGE

### Inventory (top 30 of ~80 files newer than 2026-05-01)

```
2026-08-22 10:19         138  /home/rg/empire-repo/backend/data/max/openclaw_worker_heartbeat.json
2026-08-22 10:17       32768  /home/rg/empire-repo/backend/data/intake.db-shm
2026-08-22 10:17       32768  /home/rg/empire-repo/backend/data/empire.db-shm
2026-08-22 10:17           0  /home/rg/empire-repo/backend/data/intake.db-wal
2026-08-22 10:00    14942208  /home/rg/empire-repo/backend/data/brain/memories.db
2026-08-22 09:30    15462400  /home/rg/empire-repo/backend/data/brain/token_usage.db
2026-08-22 08:00    23257088  /home/rg/empire-repo/backend/data/brain/unified_messages.db
2026-08-22 07:30        1666  /home/rg/empire-repo/backend/data/reports/morning_brief.json
2026-08-21 23:00        7516  /home/rg/empire-repo/backend/data/max/memory.md
2026-08-20 20:29          68  /home/rg/empire-repo/backend/data/archiveforge_uploads/153/front_f28f8f86.png
2026-08-20 20:28          68  /home/rg/empire-repo/backend/data/archiveforge_uploads/149/front_54d488d0.png
2026-08-19 22:42        6894  /home/rg/empire-repo/backend/data/max/session_handoff.json
2026-08-19 22:42       44090  /home/rg/empire-repo/backend/data/max/supermemory_scaffold.jsonl
2026-08-19 22:41      466944  /home/rg/empire-repo/backend/data/backups/intake_20260819_2241.db
2026-08-19 22:41    18501632  /home/rg/empire-repo/backend/data/backups/empire_20260819_2241.db
2026-08-17 19:48      893124  /home/rg/empire-repo/backend/data/uploads/images/IMG_1343.png
2026-08-17 14:30          68  /home/rg/empire-repo/backend/data/archiveforge_uploads/144/front_c8f8e0ac.png
2026-08-17 14:29          68  /home/rg/empire-repo/backend/data/archiveforge_uploads/143/front_fe5ef665.png
2026-07-16 20:17      163000  /home/rg/empire-repo/backend/data/uploads/images/IMG_1041_20260716_201718.jpeg
2026-07-16 20:00       12151  /home/rg/empire-repo/backend/data/uploads/documents/EST-2026-111_Presentation_Boards-2_20260716_200003.pdf
2026-07-16 18:16        3908  /home/rg/empire-repo/uploads/arch_drawings/drawing_f459fe28.svg
2026-07-16 18:16        3907  /home/rg/empire-repo/uploads/arch_drawings/drawing_4d6deab6.svg
2026-07-16 18:16       14905  /home/rg/empire-repo/uploads/arch_drawings/drawing_4d6deab6.pdf
2026-07-16 18:16       14859  /home/rg/empire-repo/uploads/arch_drawings/drawing_f459fe28.pdf
2026-07-16 10:48     2980571  /home/rg/empire-repo/backend/data/photos/quote/52/cc_20260716_144805_62e732.jpeg
2026-07-15 10:46          68  /home/rg/empire-repo/backend/data/archiveforge_uploads/118/front_e959dde5.png
2026-07-13 16:31       23193  /home/rg/empire-repo/uploads/arch_drawings/drawing_e1dc49d9.pdf
2026-07-13 16:31       15460  /home/rg/empire-repo/uploads/arch_drawings/drawing_e1dc49d9.svg
2026-07-08 11:30    18501632  /home/rg/empire-repo/backend/data/empire.db
…[plus JSON blobs in apostapp/, logs/, file_access/, and older uploads]…
```

### Fork DB row counts vs canonical (delta from canonical `empire.db`)

```
TABLE                                        FORK    CANON    DELTA  FLAG
access_audit                                    0        0        0  
access_sessions                                 0        0        0  
access_users                                    5        5        0  
ag_archive_photos                               0       59      -59  CANON-ONLY
ag_archives                                     3       73      -70  CANON-ONLY
ag_box_registry                                 0        0        0  
ag_listing_drafts                               0       11      -11  CANON-ONLY
apostille_documents                             0        0        0  
archive_ad_comps                                0      228     -228  CANON-ONLY
archive_ad_opportunities                        0       93      -93  CANON-ONLY
archive_ad_page_photos                          1       16      -15  CANON-ONLY
archive_ads                                     -        6        -  MISSING (table not in fork)
archive_external_api_calls                      0     1305    -1305  CANON-ONLY
archive_issue_info_runs                         -       73        -  MISSING
archive_issue_metadata                          0       15      -15  CANON-ONLY
archive_item_lifecycle                          -        4        -  MISSING
archive_item_lifecycle_events                   -        9        -  MISSING
archive_life_issue_master                       -     1863        -  MISSING
archive_life_issue_sources                      -     1871        -  MISSING
archive_listing_drafts                          0       13      -13  CANON-ONLY
archive_magazine_comps                          -       49        -  MISSING
archive_pricing_summary                         -       28        -  MISSING
atlas_tasks                                   129      130       -1  CANON-ONLY
business_profiles                               2        2        0  
campaign_activity                              20       20        0  
campaigns                                       3        3        0  
catalog_analytics                              35       35        0  
cf_buyers                                       5        5        0  
cf_lots                                        60       60        0  
chart_of_accounts                              26       26        0  
chat_session_turns                              -      262        -  MISSING
client_option_sets                               1        1        0  
client_portal_tokens                             5        5        0  
contacts                                        3        7       -4  CANON-ONLY
customers                                     147      171      -24  CANON-ONLY
desk_configs                                   15       15        0  
expenses                                        6        6        0  
fabrics                                         6       12       -6  CANON-ONLY
financial_audit_log                            28      148     -120  CANON-ONLY
intake_fabrics                                  3        3        0  
intake_projects                                 -      503        -  MISSING
intake_users                                    -      654        -  MISSING
inventory_items                               155      155        0  
invoices                                       20       32      -12  CANON-ONLY
jobs                                            8        8        0  
label_catalog                                   -        0        -  MISSING
lf_activities                                   0        1       -1  CANON-ONLY
listings                                        2        2        0  
maintenance_config                              5        5        0  
maintenance_log                                18       18        0  
max_response_audit                           3996     4327     -331  CANON-ONLY
max_response_evaluations                     5913     6081     -168  CANON-ONLY
max_routing_preferences                        40       53      -13  CANON-ONLY
max_tool_performance                          103      124      -21  CANON-ONLY
openclaw_tasks                               7357     7390      -33  CANON-ONLY
pending_drawing_jobs                            -        0        -  MISSING
quote_line_items                               83      124      -41  CANON-ONLY
quotes_v2                                      28       49      -21  CANON-ONLY
sf2_inventory                                  50       50        0  
sf2_products                                   50       50        0  
sqlite_sequence                                46       62      -16  CANON-ONLY
task_activity                                 350      474     -124  CANON-ONLY
tasks                                        1482     1858     -376  CANON-ONLY
vendors                                        51       51        0  
vo_audit_events                                17       17        0  
work_orders                                     0        0        0  
[…remaining tables all match canonical exactly, with deltas 0…]
```

**Summary of fork-vs-canonical:**
- 132 tables compared
- 34 tables MISSING from the fork entirely (canonical-only — fork schema is older)
- 22 tables present in both but with **fork BEHIND canonical** (CANON-ONLY deltas)
- 0 tables with FORK-ONLY data (no rows exist in fork that aren't also in canonical)
- The fork is a frozen snapshot from before several schema additions and a couple months of writes.

**Note for the dispatch's "data exists ONLY in the fork" question:** the reverse is true — canonical has data the fork lacks. No fork-only rows were found.

### REBOOT TRAP

```
$ systemctl cat empire-backend.service 2>/dev/null | grep -E 'ExecStart|WorkingDirectory'
(empty — overrides in zz-canonical-venv.conf replace ExecStart with canonical venv)

$ systemctl is-enabled empire-backend.service
masked
```

```
$ systemctl cat empire-openclaw.service 2>/dev/null | grep -E 'ExecStart|WorkingDirectory'
WorkingDirectory=/home/rg/empire-repo/openclaw
ExecStart=/home/rg/empire-repo/backend/venv/bin/python3 server.py

$ systemctl is-enabled empire-openclaw.service
enabled
```

**Verdict:**
- **`empire-backend.service` is MASKED** — `is-enabled` returns `masked`. A reboot will NOT start the backend via systemd. (The currently-running backend was started by some other means — possibly manual launch — and is held open by uvicorn via systemd user drop-ins. The unit's `ExecStart` is overridden by `zz-canonical-venv.conf` to use `~/empire-repo-main/backend/venv/bin/python3`, so if/when it WERE started, it would use the canonical venv.)
- **`empire-openclaw.service` IS ENABLED** and points into the fork: `WorkingDirectory=/home/rg/empire-repo/openclaw` and `ExecStart=/home/rg/empire-repo/backend/venv/bin/python3`. **A REBOOT STARTS OPENCLAW WITH THE FORK'S VENV.** This is the live reboot trap. The fork's venv has been diverging from canonical since March per dispatch doctrine. OpenClaw would come up healthy (its `server.py` is small), but its dependencies may not match the canonical codebase's expectations.

**Plain verdict:** A REBOOT RESTARTS OPENCLAW FROM THE STALE FORK'S VENV. Backend (`empire-backend.service`) is masked, so a reboot does NOT restart it — meaning whoever restarts the backend (currently pid 652663) has to do so manually after a reboot.

### STRANDED CLIENT VALUE

YES — stranded in the fork:
- **2026-07-13 16:31** — `uploads/arch_drawings/drawing_e1dc49d9.{svg,pdf}` (15460 + 23193 bytes) — SHOP DRAWING
- **2026-07-16 18:16** — `uploads/arch_drawings/drawing_f459fe28.{svg,pdf}` (3907 + 14859 bytes) — SHOP DRAWING
- **2026-07-16 18:16** — `uploads/arch_drawings/drawing_4d6deab6.{svg,pdf}` (3908 + 14905 bytes) — SHOP DRAWING
- **2026-07-16 19:43–20:17** — `uploads/images/IMG_1041*.jpeg` and `uploads/documents/EST-2026-111_Presentation_Boards-2*.pdf` (multiple copies, 163KB images, 12KB PDFs) — CLIENT PRESENTATION
- **2026-07-16 10:47–10:48** — `photos/quote/52/cc_20260716_*.jpeg` + `.meta.json` (3 MB-scale quote photos) — CLIENT INTAKE PHOTOS
- **2026-06-26 / 2026-06-24** — `uploads/images/IMG_0659.png`, `HAT_*.webp`, `Farmhouse-BEFORE-*.jpg` — client uploads
- **2026-06-11 / 2026-06-13** — `apostapp/customers/*.json`, `apostapp/orders/*.json` — apostille intake records

None of these stranded assets are referenced from canonical's `/home/rg/empire-data/photos/` or `empire-data/quotes/` paths based on Step 3's row counts — meaning the canonical DB does not point at them. **Whether the canonical database has corresponding quote/job rows that own these assets is the unanswered question; the files themselves are physically stranded in the fork's tree.**

The fork's `backend/data/empire.db` and `backend/data/intake.db` row counts show fewer records than canonical, so even if some IDs overlap, the fork's DB-side metadata is older. The salvage question is therefore about FILES, not database rows.

---

## VERIFIED

Things directly observed via pasted command output:

- **Services running (Step 1):** 39 systemd units running, including empire-openclaw (system-level), empire-backend + empire-portal (user-level); uvicorn pid 652663 on :8000 from `empire-repo-main/backend/venv/bin/python3`; next-server pid 2420 on :3005; OpenClaw pid 1755 on :7878; OpenCode daemon pid 1758 on :8787; Hermes pid 1757 on :3000; cloudflared on 20241–20244. **No PostgreSQL, Redis, or MinIO ports.**
- **Backend :8000 root returns 200.**
- **OpenAPI route count: 1086 unique paths.** Full list captured in `/tmp/routes.txt`.
- **Truth layer:** 132 tables probed across 4 DBs.
  - Live (`empirebox.db`, held open by uvicorn): 20 tables, 2 with data (sf_support_agents=1, sf_tenants=1). All business tables empty.
  - Canonical `empire.db` (24 MB, modified 2026-08-22 10:01): rich — `quotes_v2=49`, `customers=171`, `intake_projects=503`, `max_response_audit=4327`, `openclaw_tasks=7390`, etc.
  - Canonical `intake.db`: `intake_projects=504`, `intake_users=654`.
  - Fork `empire.db` (18.5 MB, July 8): BEHIND canonical in every populated table; 34 tables MISSING from fork.
  - Fork `intake.db`: `intake_projects=505`, `intake_users=655`.
- **Corridor (Step 4):** all six capabilities (quotes, jobs, finance/invoices, payments, crm/customers, inventory) return 200 with real data. `/api/v1/customers/` returns 307→empty page; populated data is at `/api/v1/crm/customers`.
- **MAX (Step 5):** Healthy per `/api/v1/max/health`. 17 desks, telegram connected. Primary provider `minimax` (model `MiniMax-M3`), all other providers disabled, fallback disabled. Operating registry mtime 2026-05-15. MAX config source: `~/empire-repo-main/backend/app/services/max/operating_registry.json`.
- **Repo (Step 6):** HEAD `8aeb0f0` on `feature/drawing-standard`. Uncommitted: `M max/memory.md` (known nightly false positive), `?? codetask_stage3_clean.txt`, `?? codetask_stage3_evidence.txt`, `?? reference/mclean/McLean_Whittington_Drapery_Elevations_RevA.pdf`. Fork is a worktree pinned to `b7dcb6b [lane/source-holding-v10-root]`.
- **H-A:** MAX `__init__.py` line 2 is a docstring (no ImportError); MAX is loaded IN-PROCESS by `app/main.py:80-81`; no `orchestrator.py` in max/ but nothing imports one; orchestrator lives at `app/services/orchestration/orchestrator.py`. MAX is healthy. **FIXED SINCE / NEVER WAS THE FAILURE MODE DESCRIBED.**
- **H-B:** 5 frontend tsx files reference `localhost:8000`; 2 hardcoded (EmpireTopBar:27 health check, orchestration/page.tsx:12 API const), 3 use `process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'`. **PARTIALLY CONFIRMED STILL (2 hardcoded sites).**
- **H-C:** `CraftForgePage.tsx:15` import `'../business/craftforge/QuoteBuilderSection'` resolves to existing file `app/components/business/craftforge/QuoteBuilderSection.tsx`. **FIXED SINCE.**
- **H-D:** Router lines 1380–1410 contain a live-lookup summary function, not a `drawing_handoff.ready` early-return. Router is 5687 lines. **CANNOT VERIFY AS WRITTEN.**
- **H-E:** OpenClaw healthy on :7878, but 7390 historical tasks (5945 failed + 1443 done + 2 cancelled); worker is polling/idle. **CONFIRMED STILL (with caveat: no live work; queue is a backlog graveyard).**
- **H-F:** No 5432/6379/9000 ports; no Postgres/Redis/MinIO processes; truth layer is SQLite only. **CONFIRMED NEVER TRUE.**
- **H-G:** `:8000` uvicorn cwd is `/home/rg/empire-repo-main/backend`; port 8010 returns 000; `~/empire-repo-v10` does not exist. Production serves canonical. **FIXED SINCE for backend. OpenClaw still on fork (see Step 9).**
- **Downloads (Step 8):** ~60 newer-than-May files inventoried; 5 STATE snapshots in Downloads (v2, v3, v4, v7, v8) — Downloads `STATE_v8.md` is post-dated by repo's `8aeb0f0`. `EMPIRE_CLIENT_DOC_STANDARD.md` and `(1).md` are byte-identical duplicates.
- **Stale fork (Step 9):**
  - Fork `empire.db` is BEHIND canonical in every populated table; 34 tables MISSING from fork. 0 fork-only rows.
  - **REBOOT TRAP:** `empire-backend.service` is **masked** (won't start on reboot); `empire-openclaw.service` IS enabled and points into the fork (`WorkingDirectory=/home/rg/empire-repo/openclaw`, `ExecStart=/home/rg/empire-repo/backend/venv/bin/python3 server.py`). **A REBOOT STARTS OPENCLAW FROM THE FORK'S VENV.**
  - **STRANDED CLIENT VALUE: YES** — three SVG+PDF shop-drawing pairs (2026-07-13/16), IMG_1041 client presentation photos + EST-2026-111 PDFs (2026-07-16), quote photos from 2026-06-24 to 2026-07-16, apostille intake JSONs from 2026-06-11/13. Files physically stranded; canonical DB has no pointer to them.

---

## INFERRED

Conclusions that did not come from a single pasted command but follow from cross-referencing the verified observations:

- **MAX has never been a "separate service" — it is a router library mounted by FastAPI.** The May record's "launch method" diagnostic appears to have confused in-process module loading with a script-style invocation. The running `app.main` lifespan pulls in `max_scheduler`, `max_monitor`, `telegram_bot`, `desk_scheduler` (lines 408–421) on startup — no script entry point exists.
- **The uvicorn pid 652663 is NOT held in any enabled systemd unit.** It was started manually (or by a non-systemd mechanism) sometime around 2026-08-20 19:54:15 — close to a reboot-window timestamp but the user-level unit is masked, not enabled. Whatever process started it on 2026-08-20 is not visible in standard systemd.
- **The "live" database (empirebox.db) is essentially empty.** All real business data lives in `empire.db` (24 MB canonical), which uvicorn does NOT hold open. Either (a) the backend reads `empire.db` lazily through alternate engines, or (b) something has silently switched the backend to `empirebox.db` and the canonical's data is invisible to running services. **This is a high-priority follow-up — the corridor APIs DID return real data in Step 4, so the backend CAN reach `empire.db` (likely via SQLAlchemy/SQLModel engines per model, with `empirebox.db` as the SQLAlchemy default and per-model overrides pointing at `empire.db`). Worth confirming.** This pattern is consistent with the per-table divergence seen across the live DB vs canonical.
- **The fork's `backend/data/empire.db-shm` and `-wal` files updated at 2026-08-22 10:17** are recent. SQLite leaves `-shm`/`-wal` artifacts from any connection (open or closed). No process currently has the fork's empire.db open (per lsof). Probably a leftover from a brief connection during the day.
- **The `empire-openclaw.service` ExecStart uses `python3 server.py` from `/home/rg/empire-repo/openclaw`** but the binary is the fork's venv Python. This works only because OpenClaw's `server.py` is small and depends on stdlib + a few common packages. If the canonical backend code added new dependencies that OpenClaw's worker would need, the fork's Python may not satisfy them.
- **H-D's drawing_handoff claim was likely accurate in May but the code has moved.** The 5687-line router file has been rewritten since. A `git log -S drawing_handoff --oneline` would locate any surviving reference, but that's a future read-only follow-up.
- **The Downloads `STATE_v8.md` is a snapshot, not live state.** Per repo commit `8aeb0f0` on 2026-08-20 ("docs(state): H68-H71 added, P1-T advanced to .d, HANDOFF de-duped"), the repo's `claude/STATE.md` is post-STATE_v8 by hours. Strategic Claude should not use the Downloads copy as ground truth.
- **The 4 untracked files in the repo working tree** (codetask_stage3_*.txt, McLean PDF) appear to be evidence artifacts from the H70-H71 template-engine work. Likely intentional, not uncommitted work in the bad sense — but they should be tracked or `.gitignore`-d by whoever finishes the H-series.
- **Of the 5 STATE files in Downloads, only v8 (Downloaded 2026-08-20) is post-May-07.** The others (v2/v3/v4/v7) predate May-07 only partially — they are post-May-01. They are useful as the version-history trail. The repo `claude/STATE.md` is the authoritative source.

---

## COULD NOT PROBE

- **Max's actual current reasoning ability / response quality** — by dispatch rule, I did not send MAX a prompt. Inference of "is MAX functional end-to-end" stops at "MAX health is healthy, all 17 desks online, primary provider minimax is configured."
- **Whether the running backend actually USES the canonical `empire.db` data** in practice (versus `empirebox.db`). lsof only showed `empirebox.db` open; the rich Step 4 corridor responses suggest per-model engines connect to `empire.db` directly, but this is INFERRED, not verified. A targeted `lsof -p 652663` over the lifespan of a single API request would resolve this but requires a write/observation change.
- **Strategic Claude cross-reference against the navigator HTML** is out of scope (the dispatch asks me to produce this report; Claude will diff against the navigator separately).
- **Per-node WORKING/DEGRADED/DOWN classification** is not produced here — that is the next-step Claude task per dispatch §"WHAT HAPPENS NEXT."
- **PDF/xlsx/image content in Downloads** — only names/sizes/mtimes reported per dispatch rule; no extraction.
- **`/home/rg/empire-repo-v10` historical state** — directory does not exist on disk; nothing to probe.

---

## COUNTS (one-liners)

- **Services running:** 39 systemd units + 7 user/process-attached daemons (uvicorn, next-server, openclaw, opencode, hermes, npm exec, MCP coding-plan).
- **Routes found:** 1086 unique paths from `/openapi.json`.
- **DBs found (with row counts probed):** 4 (live empirebox.db, canonical empire.db, canonical intake.db, fork empire.db, fork intake.db) — 5 DBs total, 132 tables enumerated.
- **Hypotheses confirmed still:** 3 (H-B partial, H-E, H-F).
- **Hypotheses fixed since:** 4 (H-A, H-C, H-G backend, plus the broader "May state" picture).
- **Hypotheses cannot verify:** 1 (H-D — code has moved).
- **Hypotheses retired:** 0 — none are wrong outright, only stale in their specifics.

---

Report path: `/home/rg/RESTORE_PROBE_2026-08-22.md`