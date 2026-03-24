# EmpireBox v4.0 — Launch Day Briefing
**Last updated:** 2026-03-24 02:00 AM
**Last commit:** `7db4ec0` (pushed to main)

## System State

### Running Services
| Service | Port | Status | Process |
|---------|------|--------|---------|
| Backend (FastAPI, 4 workers) | 8000 | Healthy | uvicorn |
| Command Center (Next.js 16 dev) | 3005 | Running | next dev |
| Cloudflare Tunnel | — | Running | cloudflared (pid 1742) |

### Tunnel Domains
- `studio.empirebox.store` → localhost:3005 (Command Center)
- `api.empirebox.store` → localhost:8000 (Backend API)

### AI Models Active (10/11)
Gemini 2.5 Flash, GPT-4.1 Nano, GPT-4o Mini, GPT-4o, Claude Sonnet 4.6, Claude Opus, Grok 3 Fast, Groq Llama 70B. Only Ollama offline (local service, not needed).

### Test Status
55/55 launch tests passing as of session 5 (2026-03-22).

## What's Working

1. **Quote Pipeline** — Full lifecycle: intake → photos → rooms → pricing engine (3-tier) → PDF → email → accept → job → invoice → payment
2. **Quote Builder** — Multi-step wizard with: customer info, photo upload (+ intake loading), 3D scan upload (ZIP supported), room/item management with catalog, options, preview pricing, full quote generation
3. **Pricing Engine (QIS)** — Yardage calculator, tier generator, 70+ item type normalization, line items with fabric/labor/upgrades/installation/lining
4. **Pattern Templates** — Generate + save + browse + PDF for sphere, cylinder, box cushion, knife edge
5. **Crypto Payments** — Real wallet addresses from .env, QR codes, live CoinGecko prices
6. **Stripe Payments** — Working in test mode, ready for live key swap
7. **CraftForge (WoodCraft)** — Designs, quotes, invoices, expenses, CRM, finance dashboard
8. **Mobile Access** — Quotes list now paginated (7KB vs 20MB), works through tunnel
9. **MAX AI** — Chat, streaming, 17 desks, 38 tools, Telegram bot
10. **AMP** — Content library, course player, mood recommendations

## What Needs Attention

### Owner Actions (Manual)
1. **Stripe live keys** — Swap `sk_test_*` → `sk_live_*` in `backend/.env`
2. **Phone browser cache** — Hard-refresh `studio.empirebox.store` or clear site data
3. **Social media accounts** — Create accounts for SocialForge integration

### Technical (Next Claude Session)
1. **Production build** — CC running `next dev`. For production: `cd empire-command-center && next build && next start -p 3005`
2. **Old quotes missing data** — Quotes created before 7db4ec0 have empty photos/rooms/options. Only affects editing, not viewing.
3. **Console.log cleanup** — 3D upload handler has debug logging (non-critical)
4. **Grok investigation** — XAI_API_KEY present but may be failing silently
5. **SendGrid verification** — Verify workroom@empirebox.store email deliverability
6. **Notes endpoint** — Still 404, route not registered

## How to Pick Up Where We Left Off

### Key Files Changed in Last Session
```
backend/app/routers/crypto_checkout.py      — GET /addresses endpoint
backend/app/routers/photos.py               — ZIP extraction support
backend/app/routers/quotes.py               — Pagination + summary mode
backend/app/services/quote_engine/pricing_tables.py — _normalize_item_type()
backend/app/services/quote_engine/quote_assembler.py — Removed premature save
empire-command-center/app/components/screens/QuoteBuilderScreen.tsx — Major: photos, 3D, intake, edit restore
empire-command-center/app/components/screens/QuoteReviewScreen.tsx — Photo format handling
empire-command-center/app/components/business/payments/PaymentModule.tsx — Dynamic crypto addresses
empire-command-center/app/components/business/craftforge/CRMModule.tsx — Clickable invoice badge
empire-command-center/app/tools/patterns/page.tsx — Save handler
```

### To Restart Services
```bash
# Backend
fuser -k 8000/tcp; sleep 2
cd ~/empire-repo/backend && source venv/bin/activate
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 65 --workers 4 &

# Command Center
fuser -k 3005/tcp; sleep 2
cd ~/empire-repo/empire-command-center && npm run dev -- -p 3005 &

# Cloudflare tunnel (if not running)
cloudflared tunnel run empire-studio &
```

### Database Locations
- `backend/data/empire.db` — Main database (invoices, jobs, finances, chat)
- `backend/data/intake.db` — Intake projects, users, photos
- `backend/data/patterns.db` — Saved pattern templates
- `backend/data/quotes/*.json` — Quote JSON files (137 total)
- Backups: `*_backup_launch_eve_*.db`

### Context Files
- `~/.claude-context/last_chat_summary.md` — Session summaries (most recent first)
- `~/.claude-context/sessions/session_20260323_launch_eve.md` — Detailed session log
- `~/empire-repo/docs/audit/master-launch-checklist-2026-03-23.md` — 80+ item checklist
- `~/empire-repo/docs/audit/launch-readiness-2026-03-22.md` — 55/55 test results
