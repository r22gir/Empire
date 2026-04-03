# Empire — Remaining TODO (Post v5.0)

**Current Completion: 91%** | Updated: 2026-04-02

---

## API Keys Needed (Blocking — Owner Action)

| Service | Purpose | Signup Guide |
|---------|---------|-------------|
| SendGrid | Email delivery (invoices, quotes, notifications) | `docs/account-signup-prep.md` |
| ShipStation | Carrier rates, label generation, tracking | `docs/account-signup-prep.md` |
| eBay Developer | Marketplace listings, OAuth flow | `docs/account-signup-prep.md` |
| Instagram/Facebook | SocialForge posting | `docs/account-signup-prep.md` |
| Brave Search | MAX web search tool | Get key at brave.com/search/api |

---

## Frontend Issues

- [x] **CraftForge frontend routing** — FIXED (2026-04-02): module routing now context-aware, 6 sub-modules reachable via right panel
- [x] **Discount display bug** — FIXED (2026-04-02): discount_type (% vs $) now displayed correctly in quotes and PDFs
- [ ] **SupportForge multi-tenant auth** — JWT integration needed (currently hardcoded fallback)
- [ ] **PetForge** — Coming Soon placeholder, needs full build (v6.0)
- [ ] **VetForge** — Coming Soon placeholder, needs full build (v6.0)

---

## Backend Items

- [x] **/system/health endpoint** — FIXED (2026-04-02): was documented but never created, now returns service status
- [x] **Ollama service** — FIXED (2026-04-02): started, nomic-embed-text model pulled
- [x] **Gmail OAuth2** — DONE (2026-04-02): check_email tool working
- [ ] **SMTP configuration** — endpoint ready at /api/v1/email/send, needs SendGrid API key in .env
- [ ] **Carrier integration** — ShipForge endpoints exist in test mode, need ShipStation key
- [ ] **eBay OAuth** — OAuth flow structure built, needs eBay developer keys
- [ ] **Brave API key** — Missing from backend/.env, needed for MAX web search tool

---

## Data Issues (Owner Action)

- [ ] **OSTERIA MARZANO** — address still "123 Main St, Hyattsville MD" (placeholder). Founder must provide correct address.
- [ ] **OSTERIA MAZZARO** — duplicate entry (typo). Should be merged or deleted.
- [ ] **Lauren Bassett** — drawing never delivered. Re-request via CC web chat.

---

## Nice to Have (v6.0+)

- [ ] GPU driver fix (nouveau → proprietary NVIDIA for Quadro K600)
- [ ] Cloudflare Tunnel production config verification
- [ ] Load testing on EmpireDell (20 cores available)
- [ ] Database migration from SQLite → PostgreSQL for production scale
- [x] **Automated backup schedule** — DONE: cron runs daily at 3 AM
- [ ] Stripe live keys (currently test mode)
- [ ] Session recovery after backend crashes

---

*Updated during continuous self-heal session — 2026-04-02*
