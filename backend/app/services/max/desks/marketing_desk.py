"""
MarketingDesk — Social media, content creation, and campaigns.
Replaces: SocialDesk (placeholder). Absorbs: legacy ContentBot (domains).
"""
import logging
from datetime import datetime
from .base_desk import BaseDesk, DeskTask, DeskAction

logger = logging.getLogger("max.desks.marketing")

# Supported platforms
PLATFORMS = ["Instagram", "Facebook", "Pinterest", "LinkedIn", "Google Business"]


class MarketingDesk(BaseDesk):
    desk_id = "marketing"
    desk_name = "MarketingDesk"
    agent_name = "Nova"
    desk_description = (
        "Manages marketing and social media: content creation, post scheduling, "
        "Instagram/Facebook/Pinterest campaigns, hashtag strategy, before/after showcases, "
        "engagement tracking, and audience analytics. Target audience: homeowners, interior "
        "designers, real estate stagers, and commercial property managers."
    )
    capabilities = [
        "content_creation",
        "post_scheduling",
        "hashtag_optimization",
        "campaign_management",
        "engagement_tracking",
        "audience_analytics",
        "before_after_showcases",
        "seo_content",
        "cross_platform_sync",
    ]

    # Popular hashtags for drapery/interior design (from ContentBot domain knowledge)
    HASHTAG_SETS = {
        "general": ["#customdrapes", "#windowtreatments", "#interiordesign",
                     "#homedecor", "#luxuryliving", "#drapery", "#curtains"],
        "before_after": ["#beforeandafter", "#transformation", "#homerenovation",
                         "#roomreveal", "#designmakeover"],
        "fabric": ["#fabriclove", "#textiles", "#custommade", "#handcrafted",
                    "#luxuryfabrics"],
    }

    def __init__(self):
        super().__init__()
        self.content_calendar: list[dict] = []
        self.draft_posts: list[dict] = []
        self.active_campaigns: list[dict] = []

    async def handle_task(self, task: DeskTask) -> DeskTask:
        """Route marketing task to appropriate handler."""
        await self.accept_task(task)

        combined = f"{task.title} {task.description}".lower()

        try:
            if any(w in combined for w in ["post", "caption", "draft", "write"]):
                return await self._handle_post_creation(task)
            elif any(w in combined for w in ["schedule", "calendar", "plan"]):
                return await self._handle_scheduling(task)
            elif any(w in combined for w in ["hashtag", "tags", "#"]):
                return await self._handle_hashtags(task)
            elif any(w in combined for w in ["campaign", "promotion", "ad", "boost"]):
                return await self._handle_campaign(task)
            elif any(w in combined for w in ["before after", "before and after", "reveal", "transformation"]):
                return await self._handle_before_after(task)
            elif any(w in combined for w in ["analytics", "engagement", "insights", "performance", "metrics"]):
                return await self._handle_analytics(task)
            elif any(w in combined for w in ["seo", "blog", "article", "web copy", "meta"]):
                return await self._handle_seo_content(task)
            else:
                return await self._handle_general(task)
        except Exception as e:
            logger.error(f"MarketingDesk task failed: {e}")
            return await self.fail_task(task, str(e))

    async def _handle_post_creation(self, task: DeskTask) -> DeskTask:
        """Draft a social media post using AI."""
        task.actions.append(DeskAction(
            action="post_draft",
            detail="Drafting social media post with AI",
        ))

        # Determine platform
        combined = f"{task.title} {task.description}".lower()
        platform = "Instagram"  # default
        for p in PLATFORMS:
            if p.lower() in combined:
                platform = p
                break

        # Use AI to generate the actual post
        try:
            result = await self.ai_execute_task(task)
        except Exception:
            # Fallback to template
            hashtags = self.HASHTAG_SETS["general"]
            result = (
                f"Post drafted for {platform}. Topic: {task.title}. "
                f"Suggested hashtags: {' '.join(hashtags[:5])}. "
                f"Status: draft — ready for review and scheduling."
            )

        # Track draft
        self.draft_posts.append({
            "task_id": task.id,
            "platform": platform,
            "topic": task.title,
            "status": "draft",
            "created": datetime.utcnow().isoformat(),
        })

        return await self.complete_task(task, result)

    async def _handle_scheduling(self, task: DeskTask) -> DeskTask:
        """Handle content scheduling."""
        task.actions.append(DeskAction(
            action="content_scheduling",
            detail="Processing scheduling request",
        ))

        self.content_calendar.append({
            "task_id": task.id,
            "content": task.title,
            "status": "scheduled",
            "created": datetime.utcnow().isoformat(),
        })

        result = (
            f"Content scheduled: {task.title}. "
            f"Added to content calendar. "
            f"Best posting times: Instagram (Tu/Th 10am), Facebook (W/F 1pm), "
            f"Pinterest (Sa 8pm). Calendar items: {len(self.content_calendar)}."
        )

        return await self.complete_task(task, result)

    async def _handle_hashtags(self, task: DeskTask) -> DeskTask:
        """Generate hashtag recommendations."""
        task.actions.append(DeskAction(
            action="hashtag_research",
            detail="Generating hashtag recommendations",
        ))

        all_tags = []
        for tag_set in self.HASHTAG_SETS.values():
            all_tags.extend(tag_set)

        result = (
            f"Hashtag recommendations for: {task.title}.\n"
            f"General: {' '.join(self.HASHTAG_SETS['general'])}\n"
            f"Before/After: {' '.join(self.HASHTAG_SETS['before_after'])}\n"
            f"Fabric: {' '.join(self.HASHTAG_SETS['fabric'])}\n"
            f"Tip: Use 20-25 hashtags per Instagram post, mix popular and niche."
        )

        return await self.complete_task(task, result)

    async def _handle_campaign(self, task: DeskTask) -> DeskTask:
        """Handle marketing campaign management."""
        task.actions.append(DeskAction(
            action="campaign_setup",
            detail="Processing campaign request",
        ))

        campaign = {
            "task_id": task.id,
            "name": task.title,
            "status": "planning",
            "platforms": PLATFORMS[:3],
            "created": datetime.utcnow().isoformat(),
        }
        self.active_campaigns.append(campaign)

        result = (
            f"Campaign created: {task.title}. "
            f"Platforms: {', '.join(PLATFORMS[:3])}. "
            f"Status: planning. "
            f"Next: Define target audience, set budget, create content assets."
        )

        self._log_to_brain(
            f"New campaign: {task.title}",
            importance=6,
            tags=["desk", "marketing", "campaign"],
        )

        return await self.complete_task(task, result)

    async def _handle_before_after(self, task: DeskTask) -> DeskTask:
        """Handle before/after showcase content."""
        task.actions.append(DeskAction(
            action="before_after_showcase",
            detail="Creating before/after content",
        ))

        hashtags = self.HASHTAG_SETS["before_after"] + self.HASHTAG_SETS["general"][:3]

        result = (
            f"Before/after showcase prepared: {task.title}. "
            f"Recommended format: Side-by-side or swipe carousel. "
            f"Platforms: Instagram (carousel), Pinterest (split image), Facebook (album). "
            f"Hashtags: {' '.join(hashtags[:8])}. "
            f"Tip: Include treatment details and fabric name in caption."
        )

        return await self.complete_task(task, result)

    async def _handle_analytics(self, task: DeskTask) -> DeskTask:
        """Handle analytics and engagement reports."""
        task.actions.append(DeskAction(
            action="analytics_report",
            detail="Generating marketing analytics",
        ))

        result = (
            f"Marketing report: {len(self.draft_posts)} draft post(s), "
            f"{len(self.content_calendar)} scheduled item(s), "
            f"{len(self.active_campaigns)} active campaign(s). "
            f"Platforms tracked: {', '.join(PLATFORMS)}."
        )

        return await self.complete_task(task, result)

    async def _handle_seo_content(self, task: DeskTask) -> DeskTask:
        """Handle SEO and web content creation."""
        task.actions.append(DeskAction(
            action="seo_content",
            detail="Processing SEO/web content request",
        ))

        result = (
            f"SEO content task: {task.title}. "
            f"Key strategies: Target local keywords ('custom drapes [city]'), "
            f"update Google Business Profile, add portfolio images with alt tags, "
            f"write blog posts about treatment types and care tips. "
            f"Details: {task.description[:200]}."
        )

        return await self.complete_task(task, result)

    async def _handle_general(self, task: DeskTask) -> DeskTask:
        """Handle general marketing tasks."""
        task.actions.append(DeskAction(
            action="general_marketing",
            detail="Processing general marketing task",
        ))

        result = f"Marketing task processed: {task.title}. {task.description[:200]}"
        return await self.complete_task(task, result)

    async def report_status(self) -> dict:
        base = await super().report_status()
        base["draft_posts"] = len(self.draft_posts)
        base["scheduled_content"] = len(self.content_calendar)
        base["active_campaigns"] = len(self.active_campaigns)
        return base

    def get_briefing_section(self) -> str:
        base = super().get_briefing_section()
        extras = []
        if self.draft_posts:
            extras.append(f"- {len(self.draft_posts)} draft post(s) to review")
        if self.content_calendar:
            extras.append(f"- {len(self.content_calendar)} scheduled item(s)")
        if self.active_campaigns:
            extras.append(f"- {len(self.active_campaigns)} active campaign(s)")
        if extras:
            base += "\n" + "\n".join(extras)
        return base
