---
name: empire-social
description: Manage social media presence for Empire businesses. Create content plans, generate posts, schedule content, manage profiles. Use for any social media or marketing task.
version: 1.0.0
metadata:
  openclaw:
    emoji: "📱"
---

# Empire Social Media Operations

## Businesses
1. **RG's Drapery & Upholstery** (Empire Workroom)
   - Services: Custom drapery, upholstery, window treatments, cushions
   - Target: Homeowners, interior designers, luxury market
   - Tone: Professional, luxurious, craftsmanship-focused

2. **RG's Woodwork & CNC** (CraftForge)
   - Services: Custom woodworking, CNC cutting, furniture, cabinetry
   - Target: Homeowners, contractors, designers
   - Tone: Skilled trades, precision, custom craftsmanship

## Social Channels to Manage
- Instagram (visual portfolio — HIGHEST priority for both businesses)
- Facebook (business page + local community)
- TikTok (process videos, before/after)
- Google Business Profile (local SEO, reviews)

## SocialForge Backend
- Router: ~/empire-repo/backend/app/routers/social.py
- API base: /api/v1/social/
- Content calendar endpoint: /api/v1/social/calendar
- Post scheduler: /api/v1/social/schedule

## Content Strategy

### Weekly Content Plan (per business)
- Monday: Before/After transformation
- Tuesday: Process/behind-the-scenes video
- Wednesday: Tip or educational post
- Thursday: Client testimonial or review
- Friday: Finished project showcase
- Weekend: Story content, polls, engagement

### Post Templates
When generating posts:
- Keep captions under 150 words
- Include 3-5 relevant hashtags
- Include call-to-action (DM for quote, link in bio, etc.)
- Reference location (for local SEO)
- Tag relevant accounts when applicable

### Hashtag Sets
**Drapery/Upholstery:**
#customdrapery #upholstery #windowtreatments #interiordesign #homedecor #luxuryliving #customcurtains #fabricdesign #homeimprovement #designerlife

**Woodwork/CNC:**
#customwoodwork #cnc #woodworking #customfurniture #cabinetry #carpentry #handcrafted #woodshop #cncrouter #madeinusa

## Operations

### Generate a content calendar
1. Check existing calendar: `curl -s http://localhost:8000/api/v1/social/calendar`
2. Generate 2-week plan with post types, captions, and hashtags
3. Save via POST to /api/v1/social/calendar

### Create a post draft
POST to /api/v1/social/posts with:
```json
{
  "business": "workroom|craftforge",
  "platform": "instagram|facebook|tiktok",
  "content": "caption text",
  "hashtags": ["tag1", "tag2"],
  "media_type": "image|video|carousel",
  "scheduled_date": "YYYY-MM-DD",
  "status": "draft"
}
```

## Rules
- Never post without founder approval (save as draft)
- All content must be professional and on-brand
- No stock photos — flag if real project photos are needed
- Track what performs well and adjust strategy
