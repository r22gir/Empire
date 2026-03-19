"""
WebsiteDesk — Website management, SEO, portfolio, and online presence.
Source: DB desk config (website) — no legacy bot equivalent.
"""
import logging
from datetime import datetime
from .base_desk import BaseDesk, DeskTask, DeskAction

logger = logging.getLogger("max.desks.website")


class WebsiteDesk(BaseDesk):
    desk_id = "website"
    desk_name = "WebsiteDesk"
    agent_name = "Zara"
    desk_description = (
        "Manages the company's online presence: LuxeForge storefront, homepage updates, "
        "SEO optimization, Google Business Profile, portfolio management, review responses, "
        "and web copy. Target local keywords like 'custom drapes [city]'."
    )
    capabilities = [
        "content_updates",
        "seo_optimization",
        "portfolio_management",
        "google_business",
        "review_management",
        "meta_descriptions",
        "web_copy_drafting",
    ]

    def __init__(self):
        super().__init__()
        self.content_updates: list[dict] = []

    async def _handle_task(self, task: DeskTask) -> DeskTask:
        await self.accept_task(task)
        combined = f"{task.title} {task.description}".lower()

        try:
            if any(w in combined for w in ["seo", "keyword", "meta", "search engine", "google rank"]):
                return await self._handle_seo(task)
            elif any(w in combined for w in ["portfolio", "gallery", "project photo", "showcase"]):
                return await self._handle_portfolio(task)
            elif any(w in combined for w in ["review", "testimonial", "google review", "yelp"]):
                return await self._handle_reviews(task)
            elif any(w in combined for w in ["update", "edit", "change", "content", "copy"]):
                return await self._handle_content_update(task)
            elif any(w in combined for w in ["google business", "gbp", "maps", "local"]):
                return await self._handle_google_business(task)
            else:
                return await self._handle_general(task)
        except Exception as e:
            logger.error(f"WebsiteDesk task failed: {e}")
            return await self.fail_task(task, str(e))

    async def _handle_seo(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="seo_analysis", detail="Processing SEO task"))

        result = (
            f"SEO task: {task.title}. "
            f"Key strategies: Target 'custom drapes [city]', 'window treatments [city]'. "
            f"Optimize meta descriptions (under 160 chars), add alt tags to portfolio images, "
            f"ensure mobile responsiveness, improve page load speed. "
            f"Details: {task.description[:200]}."
        )
        return await self.complete_task(task, result)

    async def _handle_portfolio(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="portfolio_update", detail="Updating portfolio"))

        self.content_updates.append({"type": "portfolio", "task_id": task.id, "date": datetime.utcnow().isoformat()})

        result = (
            f"Portfolio update: {task.title}. "
            f"Best practices: High-res photos (before/after pairs), include treatment type "
            f"and fabric name, tag room type (living room, bedroom, dining). "
            f"Add alt text for SEO."
        )

        self._log_to_brain(
            f"Portfolio updated: {task.title}",
            importance=5,
            tags=["desk", "website", "portfolio"],
        )
        return await self.complete_task(task, result)

    async def _handle_reviews(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="review_management", detail="Processing review task"))

        result = (
            f"Review task: {task.title}. "
            f"Response guidelines: Thank the reviewer, mention specific project details, "
            f"keep it professional and warm. For negative reviews: acknowledge, apologize, "
            f"offer to resolve offline. Always respond within 24 hours."
        )
        return await self.complete_task(task, result)

    async def _handle_content_update(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="content_update", detail="Processing content update"))

        self.content_updates.append({"type": "content", "task_id": task.id, "date": datetime.utcnow().isoformat()})

        result = (
            f"Content update: {task.title}. "
            f"LuxeForge site (port 3002) and Homepage (port 8080). "
            f"Details: {task.description[:200]}. Status: queued for implementation."
        )
        return await self.complete_task(task, result)

    async def _handle_google_business(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="google_business", detail="Processing Google Business task"))

        result = (
            f"Google Business Profile: {task.title}. "
            f"Keep updated: hours, photos, services, posts (weekly), Q&A. "
            f"Respond to all reviews. Add new project photos monthly. "
            f"Details: {task.description[:200]}."
        )
        return await self.complete_task(task, result)

    async def _handle_general(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="general_website", detail="Processing website task"))
        result = f"Website task processed: {task.title}. {task.description[:200]}"
        return await self.complete_task(task, result)

    async def report_status(self) -> dict:
        base = await super().report_status()
        base["content_updates"] = len(self.content_updates)
        return base
