# EmpireBox API Endpoint Test Results

**Date:** 2026-03-20
**Server:** EmpireDell (localhost:8000)
**Tester:** rg (manual curl tests)

## Summary

| Metric | Count |
|---|---|
| **Total Endpoints Tested** | 35 |
| **PASS** | 29 |
| **FAIL** | 1 |
| **DEGRADED** | 1 |
| **Needs Testing** | 4 |
| **Not Exercised (exist in spec)** | 12 groups |

**Overall Health:** 29/30 exercised endpoints passing (96.7%). One routing bug found (trailing slash on `/api/v1/jobs`). External dependency Ollama offline, causing OpenClaw degradation.

---

## Health & Core

| Method | Path | HTTP Status | Response Time | Result | Notes |
|---|---|---|---|---|---|
| GET | `/health` | 200 | <0.01s | PASS | `{"status":"healthy"}` |
| GET | `/docs` | 200 | — | PASS | Swagger HTML returned |
| GET | `/` | 200 | — | PASS | `{"message":"EmpireBox API","version":"1.0.0"}` |

## MAX AI

| Method | Path | HTTP Status | Response Time | Result | Notes |
|---|---|---|---|---|---|
| POST | `/max/chat` | 200 | ~6s | PASS | Response via Grok |
| POST | `/max/chat/stream` | 200 | — | PASS | SSE stream working |
| GET | `/max/health` | 200 | — | PASS | |
| GET | `/max/models` | 200 | — | PASS | 7 models listed (grok primary) |
| GET | `/max/desks` | 200 | — | PASS | Desk list returned |
| GET | `/max/desks/status` | 200 | — | PASS | |
| GET | `/max/telegram/status` | 200 | — | PASS | `{"configured":true,"bot_token_set":true,"chat_id_set":true}` |
| GET | `/max/stats` | 200 | — | PASS | Stats returned |

## CRM

| Method | Path | HTTP Status | Response Time | Result | Notes |
|---|---|---|---|---|---|
| GET | `/api/v1/crm/customers` | 200 | — | PASS | 114 customers returned |
| GET | `/api/v1/crm/customers?search=...` | 200 | — | PASS | Search working |

## Quotes

| Method | Path | HTTP Status | Response Time | Result | Notes |
|---|---|---|---|---|---|
| GET | `/api/v1/quotes` | 200 | — | PASS | 45 quotes returned |
| POST | `/api/v1/quotes` | 200 | — | PASS | Quote creation works |
| — | `data/quotes/pdf/` | — | — | PASS | 10+ PDFs verified on disk |

## Finance

| Method | Path | HTTP Status | Response Time | Result | Notes |
|---|---|---|---|---|---|
| GET | `/api/v1/finance/dashboard` | 200 | — | PASS | Revenue $0, Expenses $5,380, Net -$5,380 |
| GET | `/api/v1/finance/transactions` | — | — | NEEDS TEST | |

## Jobs

| Method | Path | HTTP Status | Response Time | Result | Notes |
|---|---|---|---|---|---|
| GET | `/api/v1/jobs/` | 200 | — | PASS | 5 jobs returned (requires trailing slash) |
| GET | `/api/v1/jobs` | — | — | **FAIL** | Empty response — trailing slash routing bug |
| GET | `/api/v1/jobs/calendar` | — | — | NEEDS TEST | |
| GET | `/api/v1/jobs/dashboard` | — | — | NEEDS TEST | |

## Inventory

| Method | Path | HTTP Status | Response Time | Result | Notes |
|---|---|---|---|---|---|
| GET | `/api/v1/inventory/items` | 200 | — | PASS | 156 items returned |

## Costs / Token Tracking

| Method | Path | HTTP Status | Response Time | Result | Notes |
|---|---|---|---|---|---|
| GET | `/api/v1/costs/overview` | 200 | — | PASS | 30-day: $69.01, 1582 requests |
| GET | `/api/v1/costs/today` | 200 | — | PASS | Today: $0.62, 15 requests |

## CraftForge

| Method | Path | HTTP Status | Response Time | Result | Notes |
|---|---|---|---|---|---|
| GET | `/api/v1/craftforge/dashboard` | 200 | — | PASS | 3 designs, $6,648 pipeline |

## SocialForge

| Method | Path | HTTP Status | Response Time | Result | Notes |
|---|---|---|---|---|---|
| GET | `/api/v1/socialforge/dashboard` | 200 | — | PASS | All zeros (0 posts, 0 engagement) — functional but empty |
| GET | `/api/v1/socialforge/accounts` | 200 | — | PASS | Account definitions exist, not connected to live platforms |

## Payments

| Method | Path | HTTP Status | Response Time | Result | Notes |
|---|---|---|---|---|---|
| GET | `/api/v1/payments/history` | 200 | — | PASS | `{"payments":[],"count":0}` — functional but empty |

## RecoveryForge

| Method | Path | HTTP Status | Response Time | Result | Notes |
|---|---|---|---|---|---|
| GET | `/api/v1/recovery/status` | 200 | — | PASS | 18,472 images, 1,075 processed (5.8%), not running |

## System

| Method | Path | HTTP Status | Response Time | Result | Notes |
|---|---|---|---|---|---|
| GET | `/api/v1/system/stats` | 200 | — | PASS | CPU/RAM/disk stats returned |

## Email

| Method | Path | HTTP Status | Response Time | Result | Notes |
|---|---|---|---|---|---|
| POST | `/api/v1/emails/send-quote` | — | — | NEEDS TEST | Endpoint exists, needs real email test |
| POST | `/api/v1/emails/send-invoice` | — | — | NEEDS TEST | Endpoint exists, needs real email test |

## Auth

| Method | Path | HTTP Status | Response Time | Result | Notes |
|---|---|---|---|---|---|
| POST | `/auth/login` | — | — | NEEDS TEST | Exists, needs real credentials |
| POST | `/auth/signup` | — | — | NEEDS TEST | Exists |

## LuxeForge Intake

| Method | Path | HTTP Status | Response Time | Result | Notes |
|---|---|---|---|---|---|
| — | Intake system | — | — | PASS | 3 users, 6 projects with photos |

## External Services

| Method | Path | HTTP Status | Response Time | Result | Notes |
|---|---|---|---|---|---|
| GET | `localhost:7878/health` | 200 | — | PASS | OpenClaw: `{"status":"ok"}` |
| POST | `localhost:7878/chat` | 200 | — | **DEGRADED** | Returns "Ollama not reachable" — Ollama offline |
| GET | `localhost:11434` | — | — | **OFFLINE** | Ollama: connection refused |

---

## Endpoints Not Tested

The following endpoint groups exist in the OpenAPI spec but were not exercised:

| Group | Path Prefix | Notes |
|---|---|---|
| Shipping | `/shipping/*` | 0 records |
| Listings | `/listings/*` | 0 records |
| Preorders | `/preorders/*` | 0 records |
| Marketplace | `/marketplaces/*` | 0 records |
| Crypto Payments | `/api/v1/crypto-payments/*` | |
| Economic Intelligence | `/api/v1/economic/*` | |
| LLC Factory | `/api/v1/llcfactory/*` | |
| ApostApp | `/api/v1/apostapp/*` | |
| Docker | `/api/v1/docker/*` | |
| Chat Backup | `/api/v1/chat-backup/*` | |
| Memory | `/api/v1/memory/*` | |
| Dev Panel | `/api/v1/dev/*` | |
| AMP Admin | `/api/v1/amp/admin/stats` | |
| AMP Journal | `/api/v1/amp/journal` | |
| AMP Moods | `/api/v1/amp/moods` | |

---

## Known Issues

1. **Trailing slash bug on Jobs endpoint** — `GET /api/v1/jobs` returns empty; `GET /api/v1/jobs/` works. Likely a FastAPI router config issue.
2. **Ollama offline** — `localhost:11434` refusing connections. OpenClaw chat degrades gracefully but cannot process LLM requests.
3. **SocialForge empty** — Dashboard returns all zeros. Accounts defined but not connected to live platforms.
4. **Payments empty** — Stripe integration exists (test keys) but no payment history yet.
5. **Finance shows negative** — Revenue $0 vs Expenses $5,380. No income transactions recorded.
