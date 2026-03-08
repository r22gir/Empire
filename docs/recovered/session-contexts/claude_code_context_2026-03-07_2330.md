# EMPIRE SESSION CONTEXT — 2026-03-07 (Updated 11:30 PM)
## For Claude Code — Read this before starting work

---

## UI REDESIGN — ALL DECISIONS FINALIZED

### Architecture: Single Next.js App (replaces 4 separate servers)
- One app with tab routing instead of :3000, :3001, :3002, :3009 separate processes
- Saves RAM, faster switching, shared state

### 4 Business Tabs (top bar, always visible)
1. **MAX** (gold) — Personal AI assistant, GOD VIEW (sees all data, can query any business)
2. **Empire Workroom** (green) — Drapery & upholstery business, FILTERED (only Workroom data)
3. **CraftForge** (yellow) — Woodwork & CNC business, FILTERED (only CraftForge data)
4. **Empire Platform** (blue) — SaaS ecosystem, FILTERED (only Platform data)

### Conversation History — Filtered per tab
- MAX tab: Shows ALL conversations grouped by Personal / Workroom / CraftForge (god view)
- Workroom tab: Only Workroom conversations
- CraftForge tab: Only CraftForge conversations
- Platform tab: Only Platform conversations
- One MAX brain behind the scenes, messages tagged by business

### Notifications vs Inbox
- **Notifications** (🔔 bell, global, top bar): Real-time alerts grouped by business. "FYI this happened." Visible from any tab.
- **Inbox** (inside each business tab): Action items specific to that business. "You need to do something." Filtered per business tab.

### Center Canvas — Dynamic, 6 Modes
1. **Chat** — Default MAX conversation with quick actions
2. **Quote Review** — Full proposal view with A/B/C cards, AI mockups, confirm/send buttons
3. **Document Viewer** — PDF/image preview + metadata + actions (send, print, share)
4. **Research** — Split: search results (web + memory) on left, notes panel on right
5. **Video Call** — Full-screen dark mode, self-view PIP, doc share panel, controls
6. **Dashboard** — Business metrics cards + charts (default when entering a business tab)

### Sidebar Structure
- **Global sidebar** (left icon strip, always visible): Chat, Dashboard, Desks, Inbox, Files, Search, Voice, Settings
- **Business sidebar** (inside business tabs only): Quotes, Customers, Inventory, Finance, Shipping, AI Tools, SocialForge, Support, Reports
- Inventory, Customers, Finance are NOT standalone — they live inside each business tab

### Voice / TTS
- **Dashboard mic** (🎤) = Send voice message to MAX (speech-to-text)
- **Grok TTS API** = Convert MAX responses to audio (text-to-speech)
  - Endpoint: POST https://api.x.ai/v1/tts
  - Voices: Ara, Rex, Sal, Eve, Leo (5 options)
  - Uses existing XAI_API_KEY — no new signup
  - Supports 100+ languages including Spanish
  - $0.05/minute
- **Telegram** = Auto-send voice note with every MAX text reply (for driving)
- **Video calls** = Grok TTS for MAX voice during client calls
- Replace edge-tts with Grok TTS (better quality, same API key)

### Additional Features
- **Ctrl+K Quick Switch** — Spotlight search to jump anywhere instantly
- **Client View Mode** (👁) — Hides internal data, shows clean client-safe screen
- **EN/ES Language Toggle** — Switch UI and quote PDFs between English and Spanish
- **Collapsible Ticker Bar** (bottom) — Crypto (BTC/ETH/SOL), Weather (DC + Bogotá), News, Sports, Empire system status
- **Pop-up Video Call** — Floating window, share documents during call
- **Active Desks** — Show top 6 most active, expand to see all 12
- **Touch-friendly** — All buttons min 40-44px height for tablet use

### Color Theme
- Lighter warm off-white (#f5f3ef) background
- White panels (#fff)
- Gold accents (#b8960c) for Empire branding
- Lighter buttons with subtle borders
- Dark top bar (#1a1a1a) for business tabs
- Dark ticker bar at bottom

### SocialForge
- Built into both Empire Workroom and CraftForge (not standalone)
- Also sold to subscribers on Platform
- CRITICAL for monetization — gateway to revenue
- Was discussed at length in previous sessions — search copilotforge archives
- Next priority after system setup

### File Naming Convention
- All files: `Name_YYYY-MM-DD_HHMM.ext` (include time to distinguish)

---

## MOCKUP FILES (latest)
- `Empire_Command_Center_v3_MultiScreen_2026-03-07.html` — CURRENT mockup with all features
- `Empire_Command_Center_v2_Mockup_2026-03-07.html` — Previous version (tab switching)
- `Empire_Command_Center_Full_Mockup_2026-03-07.html` — First version

## ARCHITECTURE FILES
- `Empire_v4_Architecture_FINAL_2026-03-07.pdf` — Corrected 4-page PDF

---

## SYSTEM STATE (unchanged from earlier)

### Running on Empire Dell
- Backend :8000, WorkroomForge :3001, LuxeForge :3002, Founder Dashboard :3009, Telegram Bot
- Start: `bash ~/empire-repo/start-empire.sh`
- Venv: `~/empire-repo/backend/venv/bin/activate`

### Latest Commits
- Vision router + Telegram auto-measure + PDF fixes (uncommitted — need to commit)
- ae4b39c (desk personas), ebcf869 (measurement fixes), 4226196 (photo upload fix)

### API Keys
- XAI_API_KEY ✓ (works for chat, vision, AND TTS)
- ANTHROPIC_API_KEY ✓
- TELEGRAM tokens ✓
- BRAVE_API_KEY ❌ (still missing)

---

## NEXT SESSION PRIORITIES
1. **Commit all uncommitted changes** (vision router, PDF fixes, quote enhancements)
2. **Zero to Hero interview** — Where are Workroom + CraftForge in the pipeline?
3. **SocialForge** — Find specs, plan MVP, start building
4. **Build unified Next.js app** from mockup (single app replaces 4 servers)
5. **Wire Grok TTS** into Telegram bot (replace edge-tts)
6. **Brave Search API key**
7. **Test Grok TTS** on dashboard (voice responses)

---

## CRITICAL BANS — EMPIRE DELL
1. pkill node — use fuser -k PORT/tcp
2. Max 3-4 Next.js dev servers simultaneously
3. USB external drive for backup only, not live I/O
