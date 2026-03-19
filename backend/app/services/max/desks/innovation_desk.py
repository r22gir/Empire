"""
InnovationDesk — Market scanning, competitor monitoring, monetization suggestions.
v6.0 desk #13. AI-first — every task goes through ai_call().
"""
import logging
from datetime import datetime
from .base_desk import BaseDesk, DeskTask, DeskAction

logger = logging.getLogger("max.desks.innovation")


class InnovationDesk(BaseDesk):
    desk_id = "lab"  # NOTE: shares lab desk_id for routing; see below
    # Actually use a distinct ID
    desk_id = "innovation"
    desk_name = "InnovationDesk"
    agent_name = "Spark"
    desk_description = (
        "Proactive intelligence: market scanning, competitor monitoring, trend analysis, "
        "and monetization suggestions. Covers drapery/upholstery, woodwork/CNC (CraftForge), "
        "and SaaS platform opportunities. AI-first — every response is AI-generated."
    )
    capabilities = [
        "market_scanning",
        "competitor_monitoring",
        "trend_analysis",
        "monetization_suggestions",
        "product_ideation",
        "pricing_intelligence",
        "backlog_prioritization",
    ]

    def __init__(self):
        super().__init__()
        self.scans: list[dict] = []
        self.suggestions: list[dict] = []

    async def _handle_task(self, task: DeskTask) -> DeskTask:
        """All innovation tasks are AI-driven."""
        await self.accept_task(task)

        combined = f"{task.title} {task.description}".lower()

        try:
            if any(w in combined for w in ["competitor", "competition", "rival", "compare"]):
                return await self._handle_competitor_scan(task)
            elif any(w in combined for w in ["trend", "market", "industry", "demand"]):
                return await self._handle_market_scan(task)
            elif any(w in combined for w in ["monetize", "revenue", "pricing", "upsell", "profit"]):
                return await self._handle_monetization(task)
            elif any(w in combined for w in ["idea", "product", "feature", "build", "launch"]):
                return await self._handle_ideation(task)
            elif any(w in combined for w in ["backlog", "priority", "roadmap", "next"]):
                return await self._handle_backlog(task)
            else:
                return await self._handle_general_innovation(task)
        except Exception as e:
            logger.error(f"InnovationDesk task failed: {e}")
            return await self.fail_task(task, str(e))

    async def _handle_competitor_scan(self, task: DeskTask) -> DeskTask:
        """AI-powered competitor analysis."""
        task.actions.append(DeskAction(
            action="competitor_scan",
            detail="Running AI competitor analysis",
        ))

        result = await self.ai_call(
            f"Competitor analysis for Empire businesses:\n\n"
            f"Request: {task.title}\n"
            f"Details: {task.description[:500]}\n\n"
            f"Empire operates:\n"
            f"1. Empire Workroom (Washington DC) — custom drapery & upholstery\n"
            f"2. CraftForge (woodwork/CNC) — custom furniture and CNC projects\n"
            f"3. EmpireBox SaaS Platform (Lite $29, Pro $79, Empire $199)\n\n"
            f"Analyze: key competitors, their pricing, their weaknesses, "
            f"Empire's competitive advantages, and 3 specific actions to gain market share."
        )

        self.scans.append({
            "type": "competitor",
            "title": task.title,
            "date": datetime.utcnow().isoformat(),
        })

        if not result:
            result = f"Competitor scan queued: {task.title}. AI analysis unavailable — retry later."

        return await self.complete_task(task, result)

    async def _handle_market_scan(self, task: DeskTask) -> DeskTask:
        """AI-powered market trend analysis."""
        task.actions.append(DeskAction(
            action="market_scan",
            detail="Running AI market trend analysis",
        ))

        result = await self.ai_call(
            f"Market trend analysis:\n\n"
            f"Focus: {task.title}\n"
            f"Details: {task.description[:500]}\n\n"
            f"Industries: custom drapery/upholstery, woodwork/CNC, AI SaaS tools\n"
            f"Location: Washington DC metro area\n\n"
            f"Analyze: current trends, emerging demand, seasonal patterns, "
            f"technology disruptions, and 3 specific opportunities Empire should pursue."
        )

        self.scans.append({
            "type": "market",
            "title": task.title,
            "date": datetime.utcnow().isoformat(),
        })

        if not result:
            result = f"Market scan queued: {task.title}. AI analysis unavailable — retry later."

        return await self.complete_task(task, result)

    async def _handle_monetization(self, task: DeskTask) -> DeskTask:
        """AI-powered monetization suggestions."""
        task.actions.append(DeskAction(
            action="monetization_analysis",
            detail="Generating monetization strategies",
        ))

        result = await self.ai_call(
            f"Monetization strategy for Empire ecosystem:\n\n"
            f"Request: {task.title}\n"
            f"Details: {task.description[:500]}\n\n"
            f"Current products:\n"
            f"- WorkroomForge (drapery management) — dogfooding, SaaS potential\n"
            f"- CraftForge (woodwork/CNC management) — 15 endpoints, no frontend yet\n"
            f"- LuxeForge (designer intake portal) — free tier = dumb form, paid = tools\n"
            f"- SocialForge (social media management)\n"
            f"- MarketForge (marketplace listings)\n"
            f"- EmpireBox Platform (Lite $29, Pro $79, Empire $199)\n\n"
            f"Suggest: 5 specific monetization actions ranked by effort vs. revenue potential. "
            f"Include pricing recommendations and target customer segments."
        )

        self.suggestions.append({
            "type": "monetization",
            "title": task.title,
            "date": datetime.utcnow().isoformat(),
        })

        if not result:
            result = f"Monetization analysis queued: {task.title}."

        return await self.complete_task(task, result)

    async def _handle_ideation(self, task: DeskTask) -> DeskTask:
        """AI-powered product/feature ideation."""
        task.actions.append(DeskAction(
            action="product_ideation",
            detail="Generating product ideas",
        ))

        result = await self.ai_call(
            f"Product/feature ideation for Empire:\n\n"
            f"Request: {task.title}\n"
            f"Details: {task.description[:500]}\n\n"
            f"Existing ecosystem: WorkroomForge, CraftForge, LuxeForge, SocialForge, "
            f"MarketForge, RecoveryForge, RelistApp, AMP, MAX AI assistant\n"
            f"Potential new verticals: VetForge, PetForge, ContractorForge\n\n"
            f"Generate 3-5 product ideas with: name, target customer, revenue model, "
            f"build effort (days), and competitive moat."
        )

        if not result:
            result = f"Ideation queued: {task.title}."

        return await self.complete_task(task, result)

    async def _handle_backlog(self, task: DeskTask) -> DeskTask:
        """AI-powered backlog prioritization."""
        task.actions.append(DeskAction(
            action="backlog_priority",
            detail="Analyzing and prioritizing backlog",
        ))

        # Get ecosystem audit data
        audit_context = ""
        try:
            from app.services.max.pipeline import pipeline_engine
            audit = await pipeline_engine.audit_ecosystem()
            findings = audit.get("findings", [])[:10]
            audit_context = "\n".join(
                f"- {f['type']}: {f['name']} — {f.get('description', f.get('endpoint_count', ''))}"
                for f in findings
            )
        except Exception:
            pass

        result = await self.ai_call(
            f"Prioritize the Empire development backlog:\n\n"
            f"Request: {task.title}\n"
            f"Details: {task.description[:500]}\n\n"
            f"Known gaps and audit findings:\n{audit_context or 'No audit data available.'}\n\n"
            f"Key priorities:\n"
            f"1. CraftForge frontend (15 backend endpoints, zero frontend — biggest gap)\n"
            f"2. Wire remaining Forge products to Command Center\n"
            f"3. LuxeForge paid tier features\n"
            f"4. AMP placeholder audit\n"
            f"5. RelistApp Smart Lister completion\n\n"
            f"Rank by: revenue impact, build effort, dependencies. "
            f"Suggest an execution order for the next 2 weeks."
        )

        if not result:
            result = f"Backlog analysis queued: {task.title}."

        return await self.complete_task(task, result)

    async def _handle_general_innovation(self, task: DeskTask) -> DeskTask:
        """General innovation task — always AI-driven."""
        task.actions.append(DeskAction(
            action="innovation_general",
            detail="Processing innovation task with AI",
        ))

        result = await self.ai_call(
            f"Innovation/strategy task for Empire ecosystem:\n\n"
            f"Title: {task.title}\n"
            f"Details: {task.description[:500]}\n\n"
            f"Provide strategic analysis and actionable recommendations."
        )

        if not result:
            result = f"Innovation task processed: {task.title}. {task.description[:200]}"

        return await self.complete_task(task, result)

    async def report_status(self) -> dict:
        base = await super().report_status()
        base["total_scans"] = len(self.scans)
        base["total_suggestions"] = len(self.suggestions)
        return base
