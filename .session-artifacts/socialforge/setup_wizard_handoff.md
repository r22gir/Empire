# SocialForge Account Setup Wizard — Handoff

## What Was Built

### Backend (social_setup.py — 984 lines, 9 endpoints)
- business_profiles table: single source of truth (2 businesses seeded)
- Setup wizard API: prefill data, progress tracking, platform capabilities
- Verify connection: checks Meta Graph API, updates .env + DB
- Token harvest: discovers all pages + Instagram links from Meta
- Test publish: real publish test per platform
- Draft publishing: publishes all draft posts to active platforms
- Status: full account matrix with publish readiness

### Frontend (AccountSetupWizard.tsx)
- Per-platform cards with status badges
- Copy-to-clipboard for all prefill values
- "Open Signup" links to platform registration pages
- "Verify" button calls API and updates status
- Progress bar per business
- Wired into SocialForge "Setup Wizard" tab

### Scripts
- social-setup-launch.sh: displays prefill values, opens browser tabs
- social-verify-all.sh: verifies all platform connections via API
- stripe-go-live.sh: safe key swap with backup + confirmation

### Current Account State
| Business | Platform | Status |
|----------|----------|--------|
| Workroom | Facebook | active (token exists, needs pages_manage_posts perm) |
| Workroom | Instagram | pending_setup (account not created) |
| WoodCraft | Facebook | pending_setup (page not created) |
| WoodCraft | Instagram | pending_setup (account not created) |
| All | TikTok/LinkedIn/Pinterest/GBP | not_configured |

## Owner Next Steps (in order)
1. Fix FB token: developers.facebook.com/tools/explorer → Empire Workroom page → add pages_manage_posts → Generate Token → copy to .env
2. Create Instagram @empire_workroom (see workroom_setup_checklist.md)
3. Link Instagram to Facebook Page
4. Run: ~/empire-repo/scripts/social-verify-all.sh workroom
5. Create WoodCraft Facebook Page + Instagram when ready
6. Stripe go-live: ~/empire-repo/scripts/stripe-go-live.sh
