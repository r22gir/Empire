# Sunrise smoke — Workroom cash loop

Probe window: **2026-09-28 02:35–02:42 UTC**  
Probe source: cloud agent VM (not on the EmpireDell tailnet, no Cloudflare Access session)  
Method: anonymous `GET` only. No checkout, no webhook POST, no form submit, no deploy.  
Runtime behind the one host that answered as an app: backend `GET /api/v1/max/status` reported commit `00b98ec` on `feature/drawing-standard` (that SHA is `origin/feature/drawing-standard`). This report’s branch is cut from `main` (`69a6643f`). Public behavior below is the live edge, not this checkout.

Context: `uploads/EMPIRE_MODULE_SYNC_PLAN.md` (Workroom loop: proof → capture → quote → cash). Stage 0 does **not** require public self-serve. Do not send designer traffic at a red or yellow row.

## Legend

| Color | Meaning |
| --- | --- |
| **GREEN** | Anonymous probe received the intended app body (right page or JSON from the app). |
| **YELLOW** | Edge answered, but the cash step is not usable anonymously: Access login, wrong page, empty pipeline, or page shell only. A `200` whose body is the Access sign-in page is yellow, not green. |
| **RED** | `521` / `502`, DNS-level failure, or a public door that dumps operator cash data. |
| **UNKNOWN** | Not observable from this VM. Tailscale / localhost CC is always UNKNOWN here. |

HTTP status is the **first hop** (redirects not followed), unless noted.

## Tailscale / Command Center — UNKNOWN

This VM is not on the tailnet. `http://100.110.233.75:8000/health` and `:3005/` (the Tailscale address in older repo audits) **timed out after 4s**. That does not prove EmpireDell is down. It proves this VM cannot see it.

No row below is green for Tailscale. Founder check, on EmpireDell:

```bash
tailscale status
tailscale ip -4

curl -sS -D - -o /dev/null http://127.0.0.1:8000/health
curl -sS -D - -o /dev/null http://127.0.0.1:3005/
curl -sS -D - -o /dev/null "http://127.0.0.1:3005/?screen=pricing-studio"
curl -sS -D - -o /dev/null http://127.0.0.1:3005/workroom
curl -sS -D - -o /dev/null http://127.0.0.1:3005/intake
curl -sS http://127.0.0.1:8000/api/v1/pricing/canonical/status
curl -sS -o /dev/null -w "quotes %{http_code}\n" "http://127.0.0.1:8000/api/v1/quotes?limit=1"
curl -sS -o /dev/null -w "invoices %{http_code}\n" "http://127.0.0.1:8000/api/v1/finance/invoices?limit=1"
curl -sS -o /dev/null -w "max %{http_code}\n" http://127.0.0.1:8000/api/v1/max/health
```

Then from the phone **on the same tailnet**, open `http://<tailscale-ip>:3005/` and `http://<tailscale-ip>:3005/?screen=pricing-studio`. Replace the IP with the output of `tailscale ip -4` that day. Do not reuse `100.110.233.75` unless `tailscale ip -4` still prints it.

Ports in repo docs: API **8000**, Command Center **3005**. Quote builder and LeadForge are in-app screens on `/`, not separate URLs (see matrix).

## What the edge actually did

Every name below resolved to Cloudflare (`104.21.4.9`, `172.67.131.113`). `521` means Cloudflare reached a dead origin (“error code: 521”), not a missing DNS name.

| Host | First hop | What the body was |
| --- | --- | --- |
| `workroom.` `woodcraft.` `cc.` `leadforge.` `pricing.` `pay.` `quotes.` | **521** | `error code: 521` |
| `test-luxe.empirebox.store` | **521** | `error code: 521` |
| `test-studio.empirebox.store` | **502** | `error code: 502` |
| `studio.` `api.` `forge.` `hermes.` | **302** | `Location` is `https://empirebox.cloudflareaccess.com/cdn-cgi/access/login/<host>` |
| `empirebox.store` `/` and `www` | **200** | Landing title `EmpireBox — practical service tools…` (`build_1790214364313`) |
| `luxe.empirebox.store` pages outside the intake allowlist | **307** | `Location: /intake` |
| `luxe.empirebox.store/intake` | **200** | Intake copy is in the HTML (see LuxeForge) |
| `luxe.empirebox.store/api/v1/…` | **200 / 405** | FastAPI JSON. Next middleware never saw these paths. |

`feature/drawing-standard` middleware hard-scopes `luxe.empirebox.store` to `/intake`, `/intake/*`, `/api/v1/intake`, `/api/v1/fabrics/intake-project`, and Next assets. Anything else should **307 to `/intake`**. Page probes match that (`/workroom`, `/pricing`, `/max`, `/quote/probe`, `/workroom/finance`, `/health` all 307).

`/api/v1/*` does **not**. Docs in `docs/RUNTIME_ROUTING_STABLE.md` send `luxe` `/api/v1/*` straight to `localhost:8000`, so the Next allowlist never runs. Anonymous GETs of quotes, invoices, payments, jobs, and MAX health returned app JSON. Customer names, invoice numbers, and dollar amounts are omitted here on purpose. Counts only:

- `GET /api/v1/quotes?limit=1` → 200, `total: 11`
- `GET /api/v1/finance/invoices?limit=1` and `GET /api/v1/invoices?limit=1` → 200, `total: 38`
- `GET /api/v1/finance/dashboard` → 200, revenue / expenses / net / AR aging / recent invoices present
- `GET /api/v1/payments/history` → 200, 4 payments; one record `status=succeeded`, `currency=usd`
- `GET /api/v1/payments/overdue` → 200, 2 overdue invoices
- `GET /api/v1/payments/subscriptions` → 200, `count: 0`
- `GET /api/v1/jobs/dashboard` → 200, `total: 12`, `total_paid: 0`
- `GET /api/v1/leads/leadforge/prospects/stats` → 200, `total_prospects: 322`, `outreach_ready: 149`, `in_pipeline: 6`
- `GET /api/v1/leads/pipeline` → 200, **empty** pipeline list
- `GET /api/v1/leads/leadforge/providers` → 200, `configured_count: 3`
- `GET /api/v1/pricing/canonical/status` → 200, `status: available`, engine `empire-pricing-engine-v1`, formula `pricing-formulas-2026.05`, rate tables for workroom and woodcraft
- `GET /api/v1/pricing/labor-rates` and `GET /api/v1/quotes/pricing-tables` → 200 JSON rate cards
- `GET /api/v1/max/health` → 200, `status: healthy`, `service: MAX AI Assistant Manager`, `desks_online: 17`, `telegram_configured: true`
- `GET /api/v1/payments/webhook` → **405** `{"detail":"Method Not Allowed"}` (route exists; no signature was sent)

That API reachability is real. It is also the wrong public door. Treat it as **RED** for ads, designers, and “the cash loop is safely on the internet.”

## Matrix

Tailscale column is **UNKNOWN** on every row. “Expected on CC” is what the code is built to serve on EmpireDell `:3005` / `:8000`, not a live pass.

### Workroom quote UI

There is no public URL that opens the quote builder. In Command Center, quotes are in-app state (`product=workroom`, section `quotes` / screen `quote`). The only cash-loop deep link in `app/page.tsx` is `?screen=pricing-studio`.

| Surface | URL | Public | Evidence |
| --- | --- | --- | --- |
| CC quote builder | `https://studio.empirebox.store/` | **YELLOW** | 302 Access login. App HTML not observed. |
| Quote by id | `https://studio.empirebox.store/quote/probe` | **YELLOW** | 302 Access. |
| Workroom marketing page | `https://studio.empirebox.store/workroom` | **YELLOW** | 302 Access. Repo page is a brochure, not the builder. |
| Workroom finance / ops / production | `https://studio.empirebox.store/workroom/finance` (also `/ops`, `/production`) | **YELLOW** | 302 Access. |
| Dedicated workroom host | `https://workroom.empirebox.store/` | **RED** | 521. |
| Same paths on luxe | `https://luxe.empirebox.store/workroom`, `/quote/probe`, `/workroom/finance` | **YELLOW** | 307 → `/intake`. Not the quote UI. |
| Apex | `https://empirebox.store/workroom` | **RED** | 404 `Not Found` (apex allowlist). |

**Quote UI public verdict: not green.** No anonymous response contained the quote builder.

### Pricing

| Surface | URL | Public | Evidence |
| --- | --- | --- | --- |
| Pricing Studio deep link | `https://studio.empirebox.store/?screen=pricing-studio` | **YELLOW** | 302 Access. |
| `/pricing` page | `https://studio.empirebox.store/pricing` | **YELLOW** | 302 Access. |
| Dedicated host | `https://pricing.empirebox.store/` | **RED** | 521. |
| Luxe page | `https://luxe.empirebox.store/pricing` | **YELLOW** | 307 → `/intake`. |
| Apex | `https://empirebox.store/pricing` | **RED** | 404. |
| Canonical rates API | `https://luxe.empirebox.store/api/v1/pricing/canonical/status` | **RED** as a public door | 200 app JSON (engine available). Tunnel bypass of the luxe allowlist. Same path on `api.` and `studio.` is **YELLOW** (302 Access). |
| Labor rates / pricing tables | `https://luxe.empirebox.store/api/v1/pricing/labor-rates` and `/api/v1/quotes/pricing-tables` | **RED** as a public door | 200 JSON. Not probed on a tailnet. |

Pricing **math is live on the luxe tunnel**. Pricing **UI is not anonymously reachable**. `POST /api/v1/pricing/workroom/calculate` was not called.

### LeadForge

No `app/leadforge/page.tsx`. UI is Command Center product id `lead` (left nav). No `?screen=lead` deep link.

| Surface | URL | Public | Evidence |
| --- | --- | --- | --- |
| CC LeadForge | `https://studio.empirebox.store/` (in-app only) | **YELLOW** | 302 Access. Screen itself not rendered. |
| Dedicated host | `https://leadforge.empirebox.store/` | **RED** | 521. |
| Prospect stats | `https://luxe.empirebox.store/api/v1/leads/leadforge/prospects/stats` | **RED** as a public door | 200, 322 prospects. Proves data exists. Not an intake form. |
| Pipeline | `https://luxe.empirebox.store/api/v1/leads/pipeline` | **YELLOW** | 200 and **empty**. Stats say `in_pipeline: 6`. Those two reads disagree; do not call the pipeline UI green. |
| Same paths on `api.` / `studio.` | `https://api.empirebox.store/api/v1/leads/pipeline` | **YELLOW** | 302 Access. |

**Do not use LeadForge as an ad destination.** Public host is 521. The read API on luxe is an open operator pipe, not a capture form. Submit → CRM → quote was not run.

### LuxeForge

| Surface | URL | Public | Evidence |
| --- | --- | --- | --- |
| Public intake | `https://luxe.empirebox.store/` | **GREEN** (page shell) | 307 to `/intake`, then 200. HTML contains `Submit Your Project`, `Get a Quote`, `LuxeForge`, `Start Your Project`, `Custom Drapery`. Title is still `Empire Command Center`. |
| Signup / login shells | `https://luxe.empirebox.store/intake/signup` and `/intake/login` | **YELLOW** | 200, body mentions LuxeForge. No account was created. |
| Studio intake | `https://studio.empirebox.store/intake` and `/intake/signup` | **YELLOW** | 302 Access. |
| CC copies | `https://studio.empirebox.store/luxeforge` and `/luxe` | **YELLOW** | 302 Access. |
| Apex | `https://empirebox.store/intake` | **RED** | 404. |

**Loop verdict: yellow.** The intake brochure loads on `luxe` without Access. A project was not submitted, and no quote id came back. Signup/login were not exercised.

### Invoices / Stripe

Code paths (not all probed): `GET/POST /api/v1/finance/invoices`, `GET /api/v1/invoices`, `POST /api/v1/payments/checkout`, `POST /api/v1/payments/invoice-link`, `POST /api/v1/payments/webhook`. Checklist still names `https://api.empirebox.store/api/v1/payments/webhook`.

| Surface | URL | Public | Evidence |
| --- | --- | --- | --- |
| Pay host | `https://pay.empirebox.store/` | **RED** | 521. `PaymentModule.tsx` builds links on this host. |
| Invoice lists | `https://luxe.empirebox.store/api/v1/finance/invoices?limit=1` and `/api/v1/invoices?limit=1` | **RED** as a public door | 200, 38 invoices. |
| Finance dashboard | `https://luxe.empirebox.store/api/v1/finance/dashboard` | **RED** as a public door | 200 with live P&L fields. |
| Payment history / overdue | `https://luxe.empirebox.store/api/v1/payments/history` and `/overdue` | **RED** as a public door | 200. History includes succeeded USD rows. |
| Subscriptions | `https://luxe.empirebox.store/api/v1/payments/subscriptions` | **YELLOW** | 200, zero subscriptions. |
| Webhook on documented API host | `https://api.empirebox.store/api/v1/payments/webhook` | **RED** | 302 Access. A Stripe server with no Access service token will not reach the app. Signed POST was **not** sent. |
| Webhook on studio | `https://studio.empirebox.store/api/v1/payments/webhook` | **RED** | 302 Access. |
| Webhook route on luxe | `https://luxe.empirebox.store/api/v1/payments/webhook` | **YELLOW** | GET 405, so the route is mounted and not behind Access. Delivery still unproven. |
| Checkout / invoice-link | `POST /api/v1/payments/checkout`, `POST /api/v1/payments/invoice-link` | **UNKNOWN** | Not called. Would create a Stripe session. |
| CC finance page | `https://studio.empirebox.store/workroom/finance` | **YELLOW** | 302 Access. |

**Deposit path is not green.** Reads show historical invoices and succeeded payments. A new Workroom deposit was not created. The documented webhook URL is behind Access.

### MAX / Command Center entrypoints

| Surface | URL | Public | Evidence |
| --- | --- | --- | --- |
| CC home | `https://studio.empirebox.store/` | **YELLOW** | 302 Access. |
| MAX marketing page | `https://studio.empirebox.store/max` | **YELLOW** | 302 Access. |
| `cc` host | `https://cc.empirebox.store/` | **RED** | 521. |
| Woodcraft host | `https://woodcraft.empirebox.store/` | **RED** | 521. |
| Woodcraft page on studio | `https://studio.empirebox.store/woodcraft` | **YELLOW** | 302 Access. |
| Forge / Hermes | `https://forge.empirebox.store/`, `https://hermes.empirebox.store/` | **YELLOW** | 302 Access. `forge` `/api/v1/max/health` is also 302. |
| API health | `https://api.empirebox.store/health`, `/healthz`, `/api/v1/max/health` | **YELLOW** | 302 Access. `/healthz` is not a backend route in this checkout (`/health` is). Access hides both. |
| Luxe MAX page | `https://luxe.empirebox.store/max` | **YELLOW** | 307 → `/intake`. |
| Luxe MAX health | `https://luxe.empirebox.store/api/v1/max/health` | **RED** as a public door | 200 healthy, 17 desks, Telegram configured. Not an intended public route. |
| Test lanes | `https://test-studio.empirebox.store/`, `https://test-luxe.empirebox.store/` | **RED** | 502 and 521. |

## Apex landing (not the cash loop)

`https://empirebox.store/` and `https://www.empirebox.store/` are **GREEN as a landing page**: 200, title above, build `build_1790214364313`.

They are **not** a Workroom door. Absolute links in that HTML are only `https://apostapp.empirebox.store/apostille` and `/apostille/status` (ApostApp `/apostille` returned 200 with title `ApostApp — Apostille & Document Legalization Support`). The same HTML still **names** Workroom, LeadForge, LuxeForge, Pricing Studio, and Stripe. Those names are copy. `/workroom`, `/pricing`, and `/intake` on the apex return 404.

## Stage 0 vs this probe

From the sync plan, Stage 0 needs Workroom ops on CC, pricing rates, a human CTA, and a quote-to-cash path the founder can run. It does **not** need public LeadForge or Pricing Studio.

| Stage 0 need | This probe |
| --- | --- |
| Founder CC on Tailscale | **UNKNOWN** — verify on EmpireDell |
| Pricing rates exist | Live read on luxe API only (**exposed**) |
| Public landing | Apex **green**; Workroom-specific landing **not** public (studio Access, `workroom.` 521, apex 404) |
| Public LeadForge / Luxe form as the ad URL | **Do not.** LeadForge host 521. Luxe intake page loads; the loop was not completed. |
| Stripe deposit boring and done | **Not shown.** History has succeeded USD payments; checkout and the documented webhook were not proven. |

## Not done

- No production deploy, tunnel edit, Access change, or service restart.
- No Tailscale session, so localhost CC was not opened.
- No `POST` to checkout, webhook, quote create, or intake signup.
- `/healthz` was not added. It would not change the 521 hosts or the Access wall, and luxe `/api/v1/max/health` already answers.
