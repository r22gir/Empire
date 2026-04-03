# SocialForge Live Posting Handoff — 2026-04-03

## What Was Completed Automatically
1. Social presence plans for Workroom + WoodCraft (3 docs)
2. Infrastructure audit with structured status report
3. 6 draft posts created (3 Workroom, 3 WoodCraft) — visible in SocialForge UI
4. Facebook publisher tested — token lacks pages_manage_posts permission
5. Social account registry: 12 accounts across 6 platforms × 2 businesses
6. Instagram setup checklist for owner
7. Post preview cards for all 6 drafts

## Current Social Account State
| Business | Platform | Status | Can Publish |
|----------|----------|--------|-------------|
| Workroom | Facebook | active | NO — needs token permission fix |
| Workroom | Instagram | pending_setup | NO — account not created |
| WoodCraft | Facebook | pending_setup | NO — page not created |
| WoodCraft | Instagram | pending_setup | NO — account not created |
| All | TikTok/LinkedIn/Pinterest/GBP | not_configured | NO |

## Facebook Token Permission Fix
The current META_ACCESS_TOKEN validates but is missing `pages_manage_posts` permission.

To fix:
1. Go to https://developers.facebook.com/tools/explorer/
2. Select your app
3. Select "Empire Workroom" page in the dropdown
4. Add permissions: `pages_read_engagement`, `pages_manage_posts`
5. Click "Generate Access Token"
6. Copy the new token to backend/.env as META_ACCESS_TOKEN
7. Restart backend: `sudo systemctl restart empire-backend`

## Where Drafts Are Stored
- JSON files: ~/empire-repo/backend/data/socialforge/posts/
- API: GET /api/v1/socialforge/posts (returns all 6)
- Preview cards: ~/.session-artifacts/socialforge/previews/

## Owner Next Steps (in order)
1. Fix Facebook token permissions (see above)
2. Create Instagram @empire_workroom (see checklist below)
3. Link Instagram to Facebook Page
4. Tell MAX: "verify Instagram connection"
5. Review drafts in SocialForge → approve → publish
6. Create WoodCraft Facebook page + Instagram when ready

## Instagram Setup Checklist
See: ~/.session-artifacts/socialforge/instagram_manual_setup_checklist.md

## Token Expiry Warning
Current token expires ~June 2, 2026. Set a reminder to refresh before May 26.
