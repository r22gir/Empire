# Empire API Endpoint Map

**Date:** 2026-03-18
**Base URL:** `http://localhost:8000/api/v1`
**Total endpoint groups:** 14
**Status:** 9 WORKING, 2 PARTIAL, 3 ERROR

---

## Endpoint Groups

### /max/* — WORKING
| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/max/chat` | POST | WORKING | Main AI chat, routes through xAI -> Claude -> Groq -> OpenClaw -> Ollama |
| `/max/desks` | GET | WORKING | Returns all 18 desks with metadata |
| `/max/desks/{desk_id}/chat` | POST | WORKING | Desk-specific chat with model routing |
| `/max/tasks` | GET/POST | WORKING | Task creation and listing |
| `/max/health` | GET | WORKING | Health check with uptime and version |

### /quotes/* — WORKING
| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/quotes/` | GET | WORKING | List all quotes |
| `/quotes/` | POST | WORKING | Create new quote |
| `/quotes/{id}` | GET | WORKING | Get quote by ID |
| `/quotes/{id}` | PUT | WORKING | Update quote |
| `/quotes/{id}/pdf` | GET | WORKING | Generate PDF via WeasyPrint |
| `/quotes/{id}/send` | POST | WORKING | Send quote via SendGrid |
| `/quotes/{id}/verify` | POST | WORKING | 10-point quality verification |
| `/quotes/phase-pipeline` | POST | WORKING | 4-phase approval flow |

### /crm/customers — WORKING
| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/crm/customers` | GET | WORKING | List customers with search/filter |
| `/crm/customers` | POST | WORKING | Create customer |
| `/crm/customers/{id}` | GET | WORKING | Get customer detail |

### /jobs/* — WORKING
| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/jobs/` | GET | WORKING | Returns empty list — no jobs created yet |
| `/jobs/` | POST | WORKING | Create job endpoint responds |
| `/jobs/{id}` | GET | WORKING | Would return job detail |
| `/jobs/{id}/status` | PUT | WORKING | Update job status for Kanban |

### /finance/* — WORKING
| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/finance/dashboard` | GET | WORKING | KPIs: $2,555 MTD revenue, $5,380 expenses, 6 outstanding |
| `/finance/invoices` | GET | WORKING | 11 real invoices |
| `/finance/invoices` | POST | WORKING | Create invoice |
| `/finance/invoices/{id}/pdf` | GET | WORKING | Generate invoice PDF |
| `/finance/payments` | GET | WORKING | Payment records |

### /inventory/* — WORKING
| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/inventory/` | GET | WORKING | Full inventory with 15+ categories |
| `/inventory/` | POST | WORKING | Add inventory item |
| `/inventory/categories` | GET | WORKING | List categories from QuickBooks import |

### /vision/* — WORKING
| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/vision/measure` | POST | WORKING | Upload photo -> AI measurement extraction |
| `/vision/upholstery` | POST | WORKING | Upholstery-specific analysis |
| `/vision/mockup` | POST | WORKING | Visual mockup generation |
| `/vision/outline` | POST | WORKING | Edge detection / outline extraction |

### /socialforge/* — WORKING
| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/socialforge/accounts` | GET | WORKING | 16 accounts, all at not_started |
| `/socialforge/posts` | GET/POST | WORKING | Post scheduling (no actual publishing) |
| `/socialforge/dashboard` | GET | WORKING | Overview stats |
| `/socialforge/guide` | POST | WORKING | AI content guide generation |

### /analysis-sessions/* — WORKING
| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/analysis-sessions/` | GET | WORKING | List sessions (currently 0) |
| `/analysis-sessions/` | POST | WORKING | Save analysis session |

### /intake/* — WORKING
| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/intake/` | GET | WORKING | List intake projects |
| `/intake/` | POST | WORKING | Create intake project |
| `/intake/{id}` | GET | WORKING | Get intake detail |

### /costs/* — PARTIAL
| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/costs/today` | GET | WORKING | Today's AI token costs |
| `/costs/summary` | GET | **404** | Route not registered or handler missing |
| `/costs/by-model` | GET | WORKING | Breakdown by AI model |
| `/costs/by-desk` | GET | WORKING | Breakdown by desk |

### /emails/* — PARTIAL
| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/emails/send` | POST | WORKING | Send email via SendGrid |
| `/emails/preview` | GET | **405** | Method not allowed — may need POST |

### /chat-backup/* — ERROR
| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/chat-backup/` | GET | **500** | Internal server error — likely DB or file path issue |
| `/chat-backup/save` | POST | **500** | Same error |

### /notes/* — ERROR
| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/notes/` | GET | **404** | Route not registered |
| `/notes/extract` | POST | **404** | Notes-to-Quote extraction endpoint missing |

### /payments/checkout/* — ERROR
| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/payments/checkout/create` | POST | **404** | Route not included in FastAPI router |
| `/payments/checkout/session/{id}` | GET | **404** | Same — entire checkout group missing |

---

## Summary

| Status | Count | Percentage |
|--------|-------|------------|
| WORKING | 9 groups | 64% |
| PARTIAL | 2 groups | 14% |
| ERROR | 3 groups | 21% |

**Priority fixes:** `/payments/checkout/*` (blocks revenue), `/chat-backup/*` (500 errors), `/notes/*` (404, route registration).
