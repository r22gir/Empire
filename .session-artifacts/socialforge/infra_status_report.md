# SocialForge Infrastructure Status Report
## Generated: 2026-04-03

## Platform Status

| Business | Platform | Status | Token | Can Publish |
|----------|----------|--------|-------|-------------|
| Workroom | Facebook | active | valid (expires ~Jun 2) | NO — missing pages_manage_posts permission |
| Workroom | Instagram | pending_setup | N/A | NO — account not created |
| Workroom | TikTok | not_configured | N/A | NO |
| Workroom | LinkedIn | not_configured | N/A | NO |
| Workroom | Pinterest | not_configured | N/A | NO |
| Workroom | Google Business | not_configured | N/A | NO |
| WoodCraft | Facebook | pending_setup | N/A | NO |
| WoodCraft | Instagram | pending_setup | N/A | NO |
| WoodCraft | TikTok | not_configured | N/A | NO |
| WoodCraft | LinkedIn | not_configured | N/A | NO |
| WoodCraft | Pinterest | not_configured | N/A | NO |
| WoodCraft | Google Business | not_configured | N/A | NO |

## Token Details

- META_ACCESS_TOKEN: SET (194 chars), validates as user "Hi Fi"
- Token type: User token (NOT page token)
- Token generated: ~April 3, 2026
- Token expires: ~June 2, 2026 (60-day token)
- FACEBOOK_PAGE_ID: 1013347598533893 (Empire Workroom)
- INSTAGRAM_BUSINESS_ID: NOT SET (Instagram not linked to FB page)

## Facebook Publishing Test

- Endpoint: POST graph.facebook.com/v21.0/{page_id}/feed
- Result: HTTP 403 — OAuthException code 200
- Error: Missing `pages_manage_posts` permission
- Fix required: Regenerate token with pages_read_engagement + pages_manage_posts permissions
- How: Go to developers.facebook.com → Graph API Explorer → select Empire Workroom page → add permissions → Generate Access Token

## Infrastructure Components

- social_service.py: EXISTS — updated to fall back to META_ACCESS_TOKEN
- socialforge.py router: EXISTS — 15 endpoints (posts CRUD, campaigns, generate, publish)
- social_accounts table: CREATED — 12 rows (6 platforms × 2 businesses)
- social_post_results table: CREATED
- socialforge/posts/ storage: EXISTS — 6 draft posts
- Publisher modules: INLINE in social_service.py (not separate per-platform)
- Auto-publish scheduler: NOT IMPLEMENTED
- SocialForge frontend: EXISTS — functional UI

## Missing Items

1. pages_manage_posts permission on Meta token (OWNER ACTION)
2. Instagram account creation (OWNER ACTION)
3. Per-platform publisher modules (enhancement — currently inline)
4. Auto-publish scheduler for scheduled posts
5. WoodCraft Facebook page (OWNER ACTION)
6. All other platform accounts (TikTok, LinkedIn, Pinterest, GBP)
