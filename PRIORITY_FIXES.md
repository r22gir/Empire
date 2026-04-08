# PRIORITY_FIXES.md — Credential & Integration Gaps

Ranked by **business impact** × **implementation effort**.

---

## Tier 1: Do Now — Low Effort, High Impact

### 1. Stripe: Switch from TEST to LIVE mode
- **Verified repo fact**: `app/routers/payments.py:45-54` checks for `STRIPE_SECRET_KEY` and gracefully degrades if missing. Keys start with `sk_test_` in current config.
- **Owner action needed**: Get live keys from dashboard.stripe.com/apikeys, update `.env`
- **Verification**: Code does not expose verification steps

### 2. CORS: Lock down from wildcard
- **Verified repo fact**: `app/main.py:30-34` reads `CORS_ORIGINS` from env, defaults to `*`
- **Owner action needed**: Determine allowed origins, update `.env`
- **Verification**: Code does not expose verification steps

---

## Tier 2: Schedule This Week — Medium Effort, High Impact

### 3. RelistApp: Enable eBay API
- **Verified repo fact**: `backend/.env.example` has empty placeholders for `EBAY_APP_ID`, `EBAY_CERT_ID`, `EBAY_DEV_ID`. No code found that actually uses these.
- **Owner action needed**: Apply for eBay Developers Program, get API keys
- **Verification**: Code area not yet verified

### 4. Shipping: Enable EasyPost
- **Verified repo fact**: `app/routers/shipping.py:4-5` has TODO comment: "To activate: set EASYPOST_API_KEY". `app/services/shipping_service.py:12` reads the key.
- **Owner action needed**: Get key from easypost.com/console, update `.env`
- **Verification**: Code does not expose verification steps

---

## Tier 3: Needs Owner Action — High Effort

### 5. Instagram: Full manual setup
- **Verified repo fact**: `SERVICE_MAP.md` notes "Linked, not fully configured". `.env` has `INSTAGRAM_BUSINESS_ID` but no publishing capability yet.
- **Owner action needed**: Create @empire_workroom Instagram → Switch to Business → Link to Facebook Page
- **Verification**: Code does not expose verification steps

### 6. Meta Token: Refresh before expiry
- **Verified repo fact**: `SECRETS_MAP.md` shows "Active 60-day token" — expires ~June 2026
- **Owner action needed**: Regenerate at developers.facebook.com before expiry
- **Verification**: Code does not expose verification steps

---

## Tier 4: Low Priority / Local Only

### 7. Ollama: Local LLM for RecoveryForge
- **Verified repo fact**: `app/services/max/ai_router.py:1033` has `_ollama_chat` method. `SERVICE_MAP.md` notes Ollama runs locally on port 11434.
- **Owner action needed**: Install locally (not a credential)
- **Verification**: Code does not expose verification steps

---

## Summary Table

| Priority | Fix | Impact | Effort | Owner Action |
|----------|-----|--------|--------|--------------|
| 1 | Stripe LIVE | High | Low | Get live keys |
| 2 | CORS lockdown | Medium | Low | Determine origins |
| 3 | eBay API | High | Medium | Apply for API |
| 4 | EasyPost | Medium | Low | Get key |
| 5 | Instagram | High | High | Manual setup |
| 6 | Meta token | High (June) | Low | Refresh token |
| 7 | Ollama | Low | High | Local install |

---

## Notes

- No verification steps found in repo code — all graceful degradation or TODO comments only
- All file paths verified from grep searches, not assumptions
- After `.env` changes: service restart required (command not verified)