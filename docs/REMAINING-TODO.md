# Empire — Remaining TODO (Post v5.0)

**Current Completion: 88%** | Updated: 2026-03-16

---

## API Keys Needed (Blocking)

| Service | Purpose | Signup Guide |
|---------|---------|-------------|
| SendGrid | Email delivery (invoices, quotes, notifications) | `docs/account-signup-prep.md` |
| ShipStation | Carrier rates, label generation, tracking | `docs/account-signup-prep.md` |
| eBay Developer | Marketplace listings, OAuth flow | `docs/account-signup-prep.md` |
| Instagram/Facebook | SocialForge posting | `docs/account-signup-prep.md` |
| Brave Search | MAX web search tool | Get key at brave.com/search/api |

---

## Frontend Issues

- [ ] **CraftForge frontend routing** — 404s on built modules (6 modules built but not routable)
- [ ] **SupportForge multi-tenant auth** — JWT integration needed (currently hardcoded fallback)
- [ ] **PetForge** — Coming Soon placeholder, needs full build
- [ ] **VetForge** — Coming Soon placeholder, needs full build

---

## Backend Items

- [ ] **SMTP configuration** — endpoint ready at /api/v1/email/send, needs SendGrid API key in .env
- [ ] **Carrier integration** — ShipForge endpoints exist in test mode, need ShipStation key
- [ ] **eBay OAuth** — OAuth flow structure built, needs eBay developer keys
- [ ] **Brave API key** — Missing from backend/.env, needed for MAX web search tool

---

## Nice to Have (v6.0+)

- [ ] GPU driver fix (nouveau → proprietary NVIDIA for Quadro K600)
- [ ] Cloudflare Tunnel production config verification
- [ ] Load testing on EmpireDell (20 cores available)
- [ ] Database migration from SQLite → PostgreSQL for production scale
- [ ] Automated backup schedule for empire.db + empirebox.db

---

*Generated during v5.0 Final session*
