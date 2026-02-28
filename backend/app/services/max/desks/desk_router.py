"""
DeskRouter — routes incoming tasks to the appropriate AI desk.
Uses local LLM (Ollama Mistral) to analyze task intent and select the best desk.
Falls back to keyword matching if LLM is unavailable.
"""
import json
import logging
from .base_desk import BaseDesk, DeskTask, TaskPriority

logger = logging.getLogger("max.desks.router")

# DB desk_ids that should route to a different AI desk for execution.
# These desks keep their own UI layouts in the frontend but their tasks
# are handled by the target desk's handle_task().
DESK_ALIASES = {
    "operations": "forge",   # job tracking → ForgeDesk
    "design": "forge",       # treatment selection → ForgeDesk
    "estimating": "forge",   # quote building → ForgeDesk
}

# Keyword → desk_id mapping for fallback routing
KEYWORD_MAP = {
    "forge": {
        "keywords": [
            "quote", "estimate", "price", "pricing", "drape", "shade", "cornice",
            "valance", "bedding", "upholstery", "fabric", "window treatment",
            "workroom", "measurement", "install", "customer follow",
            "production", "job queue", "job status", "yardage", "design consult",
        ],
    },
    "sales": {
        "keywords": [
            "lead", "prospect", "pipeline", "proposal", "follow up",
            "consultation", "referral", "close", "deposit", "new customer",
        ],
    },
    "support": {
        "keywords": [
            "ticket", "complaint", "refund", "return", "warranty",
            "service request", "issue", "unhappy", "help desk", "faq",
        ],
    },
    "marketing": {
        "keywords": [
            "social media", "post", "instagram", "content", "hashtag",
            "campaign", "before after", "pinterest", "facebook post",
            "engagement", "seo", "blog",
        ],
    },
    "market": {
        "keywords": [
            "listing", "marketplace", "ebay", "inventory", "shipping",
            "relist", "fulfillment", "tracking", "facebook marketplace",
            "sell online", "competitor",
        ],
    },
    "finance": {
        "keywords": [
            "invoice", "payment", "expense", "revenue", "profit",
            "billing", "subscription", "p&l", "overdue", "cost",
        ],
    },
}


class DeskRouter:
    """Routes tasks to the appropriate desk using LLM analysis or keyword fallback."""

    def __init__(self):
        self._desks: dict[str, BaseDesk] = {}
        self._local_llm = None
        self._memory_store = None

    @property
    def local_llm(self):
        if self._local_llm is None:
            try:
                from app.services.max.brain.local_llm import LocalLLM
                self._local_llm = LocalLLM()
            except Exception:
                pass
        return self._local_llm

    @property
    def memory_store(self):
        if self._memory_store is None:
            try:
                from app.services.max.brain.memory_store import MemoryStore
                self._memory_store = MemoryStore()
            except Exception:
                pass
        return self._memory_store

    def register_desk(self, desk: BaseDesk):
        """Register a desk for routing."""
        self._desks[desk.desk_id] = desk
        logger.info(f"Registered desk: {desk.desk_name}")

    def unregister_desk(self, desk_id: str):
        """Remove a desk from routing."""
        if desk_id in self._desks:
            del self._desks[desk_id]
            logger.info(f"Unregistered desk: {desk_id}")

    def get_desk(self, desk_id: str) -> BaseDesk | None:
        return self._desks.get(desk_id)

    @property
    def desk_ids(self) -> list[str]:
        return list(self._desks.keys())

    async def route_task(self, task: DeskTask, source_desk_id: str | None = None) -> tuple[str | None, str]:
        """Determine which desk should handle a task.

        Returns (desk_id, reasoning). desk_id is None if no desk matches (→ founder inbox).
        If source_desk_id is given (e.g. from a UI desk), check aliases first.
        """
        # Check desk aliases (e.g. operations → forge)
        if source_desk_id and source_desk_id in DESK_ALIASES:
            target = DESK_ALIASES[source_desk_id]
            if target in self._desks:
                reason = f"Alias: {source_desk_id} → {target}"
                self._log_routing(task, target, reason, method="alias")
                return target, reason

        # Try LLM-based routing first
        desk_id, reason = await self._route_with_llm(task)
        if desk_id:
            self._log_routing(task, desk_id, reason, method="llm")
            return desk_id, reason

        # Fall back to keyword matching
        desk_id, reason = self._route_with_keywords(task)
        if desk_id:
            self._log_routing(task, desk_id, reason, method="keyword")
            return desk_id, reason

        # No match — founder inbox
        reason = f"No desk matched task '{task.title}' — routing to founder inbox"
        self._log_routing(task, None, reason, method="unmatched")
        return None, reason

    async def _route_with_llm(self, task: DeskTask) -> tuple[str | None, str]:
        """Use local LLM to classify which desk should handle the task."""
        if not self.local_llm:
            return None, "LLM unavailable"

        desk_descriptions = "\n".join(
            f"- {d.desk_id}: {d.desk_name} — {d.desk_description}"
            for d in self._desks.values()
        )

        prompt = f"""Classify which desk should handle this task.

Available desks:
{desk_descriptions}

Task title: {task.title}
Task description: {task.description}
Customer: {task.customer_name or 'Not specified'}
Priority: {task.priority.value}

Respond in JSON only:
{{"desk_id": "desk_id_here or null if none match", "confidence": 0.0-1.0, "reasoning": "brief explanation"}}"""

        try:
            response = await self.local_llm.generate(
                prompt,
                system="You are a task router. Classify tasks to the correct desk. Respond only in valid JSON.",
                max_tokens=200,
            )
            result = json.loads(response)
            desk_id = result.get("desk_id")
            confidence = result.get("confidence", 0)
            reasoning = result.get("reasoning", "LLM classification")

            # Only accept high-confidence matches to registered desks
            if desk_id and desk_id in self._desks and confidence >= 0.6:
                return desk_id, reasoning
            elif desk_id and desk_id not in self._desks:
                return None, f"LLM suggested '{desk_id}' but desk not registered"
            else:
                return None, f"LLM confidence too low ({confidence})"

        except (json.JSONDecodeError, TypeError):
            logger.debug("LLM routing returned non-JSON, falling back to keywords")
            return None, "LLM response unparseable"
        except Exception as e:
            logger.warning(f"LLM routing failed: {e}")
            return None, f"LLM error: {e}"

    def _route_with_keywords(self, task: DeskTask) -> tuple[str | None, str]:
        """Keyword-based fallback routing."""
        combined = f"{task.title} {task.description}".lower()

        best_desk = None
        best_score = 0

        for desk_id, config in KEYWORD_MAP.items():
            if desk_id not in self._desks:
                continue
            score = sum(1 for kw in config["keywords"] if kw in combined)
            if score > best_score:
                best_score = score
                best_desk = desk_id

        if best_desk and best_score > 0:
            return best_desk, f"Keyword match ({best_score} hits) → {best_desk}"
        return None, "No keyword matches"

    def _log_routing(self, task: DeskTask, desk_id: str | None, reason: str, method: str):
        """Log routing decision to brain memory."""
        dest = desk_id or "founder_inbox"
        logger.info(f"[Router] {task.title} → {dest} ({method}: {reason})")

        if self.memory_store:
            try:
                self.memory_store.add_memory(
                    category="desk_action",
                    subcategory="routing",
                    content=f"Routed '{task.title}' → {dest} via {method}: {reason}",
                    subject="DeskRouter",
                    importance=4,
                    source="desk",
                    tags=["desk", "routing", method, dest],
                )
            except Exception:
                pass
