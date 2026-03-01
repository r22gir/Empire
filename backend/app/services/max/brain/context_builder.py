"""
Builds MAX's context for each conversation.
Loads relevant memories, customer data, and operational state
into the system prompt before every cloud LLM call.
"""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from .memory_store import MemoryStore
from .embeddings import EmbeddingEngine
from .brain_config import MAX_CONTEXT_MEMORIES, MAX_CONTEXT_TOKENS

logger = logging.getLogger("max.brain.context")

# Shared thread pool for DB queries (sync → async bridge)
_db_pool = ThreadPoolExecutor(max_workers=4)


class ContextBuilder:
    def __init__(self):
        self.memory = MemoryStore()
        self.embeddings = EmbeddingEngine()

    def _sync_search(self, **kwargs):
        """Wrapper for sync memory.search_memories to run in thread pool."""
        return self.memory.search_memories(**kwargs)

    def _sync_recent(self, **kwargs):
        """Wrapper for sync memory.get_recent to run in thread pool."""
        return self.memory.get_recent(**kwargs)

    async def build_context(
        self,
        user_message: str,
        conversation_history: list = None,
        customer_name: str = None,
    ) -> str:
        """Build enriched context string to prepend to MAX's system prompt.
        All DB queries run in parallel via thread pool for speed."""
        loop = asyncio.get_event_loop()

        # Launch all DB queries in parallel
        founder_fut = loop.run_in_executor(_db_pool, lambda: self._sync_search(category="founder", limit=5))
        all_mem_fut = loop.run_in_executor(_db_pool, lambda: self._sync_search(limit=100, min_importance=3))
        convos_fut = loop.run_in_executor(_db_pool, lambda: self._sync_recent(category="conversation", limit=3))
        tasks_fut = loop.run_in_executor(_db_pool, lambda: self._sync_search(category="task", limit=10))
        ops_fut = loop.run_in_executor(_db_pool, lambda: self._sync_recent(category="operational", limit=5))

        customer_fut = None
        if customer_name:
            customer_fut = loop.run_in_executor(
                _db_pool, lambda: self._sync_search(query=customer_name, category="customer", limit=10)
            )

        # Await all at once
        founder, all_memories, recent_convos, active_tasks, ops = await asyncio.gather(
            founder_fut, all_mem_fut, convos_fut, tasks_fut, ops_fut
        )
        customer_memories = await customer_fut if customer_fut else []

        sections: list[str] = []

        # 1. Founder profile
        if founder:
            sections.append("## Founder Context")
            for m in founder:
                sections.append(f"- {m['content']}")

        # 2. Relevant memories via semantic search
        try:
            if all_memories:
                relevant = await self.embeddings.semantic_search(
                    user_message, all_memories, top_k=10
                )
                if relevant:
                    sections.append("\n## Relevant Memory")
                    for m in relevant[:MAX_CONTEXT_MEMORIES]:
                        sections.append(f"- [{m.get('category', '')}] {m['content']}")
        except Exception:
            first_word = user_message.split()[0] if user_message.strip() else None
            keyword_results = self.memory.search_memories(query=first_word, limit=5)
            if keyword_results:
                sections.append("\n## Related Memory")
                for m in keyword_results:
                    sections.append(f"- {m['content']}")

        # 3. Customer context
        if customer_memories:
            sections.append(f"\n## Customer: {customer_name}")
            for m in customer_memories:
                sections.append(f"- {m['content']}")

        # 4. Recent conversation summaries
        if recent_convos:
            sections.append("\n## Recent Conversations")
            for c in recent_convos:
                sections.append(f"- [{c.get('created_at', 'recent')}] {c['content'][:200]}")

        # 5. Active tasks
        pending = [t for t in active_tasks if "done" not in t.get("content", "").lower()]
        if pending:
            sections.append("\n## Active Tasks")
            for t in pending:
                sections.append(f"- {t['content']}")

        # 6. Operational state
        if ops:
            sections.append("\n## Current Operations")
            for o in ops:
                sections.append(f"- {o['content']}")

        # Assemble and truncate to token limit
        context = "\n".join(sections)
        max_chars = MAX_CONTEXT_TOKENS * 4
        if len(context) > max_chars:
            context = context[:max_chars] + "\n... [memory truncated]"

        return context

    async def post_conversation_process(
        self, conversation_id: str, messages: list[dict]
    ):
        """Run after conversation ends — summarize, extract facts, create tasks."""
        from .local_llm import LocalLLM

        llm = LocalLLM()

        # Check if local LLM is available
        if not await llm.is_available():
            logger.warning("Local LLM not available — skipping post-conversation processing")
            return

        # Summarize the conversation
        summary_data = await llm.summarize_conversation(messages)

        # Save conversation summary
        self.memory.save_conversation_summary(
            conversation_id=conversation_id,
            summary=summary_data.get("summary", ""),
            key_decisions=summary_data.get("key_decisions", []),
            tasks_created=summary_data.get("tasks", []),
            customers_mentioned=summary_data.get("customers", []),
            topics=summary_data.get("topics", []),
            mood=summary_data.get("mood", "productive"),
            message_count=len(messages),
        )

        # Save key facts as individual memories
        for fact in summary_data.get("key_facts", []):
            topics = summary_data.get("topics", ["general"])
            self.memory.add_memory(
                category="conversation",
                content=fact,
                subject=topics[0] if topics else "general",
                importance=6,
                source="auto",
                conversation_id=conversation_id,
            )

        # Create tasks from extracted action items
        for task in summary_data.get("tasks", []):
            self.memory.add_memory(
                category="task",
                content=task,
                importance=7,
                source="auto",
                conversation_id=conversation_id,
            )

        logger.info(
            f"Post-conversation processed: {len(summary_data.get('key_facts', []))} facts, "
            f"{len(summary_data.get('tasks', []))} tasks"
        )
