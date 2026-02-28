"""
Builds MAX's context for each conversation.
Loads relevant memories, customer data, and operational state
into the system prompt before every cloud LLM call.
"""
import logging
from .memory_store import MemoryStore
from .embeddings import EmbeddingEngine
from .brain_config import MAX_CONTEXT_MEMORIES, MAX_CONTEXT_TOKENS

logger = logging.getLogger("max.brain.context")


class ContextBuilder:
    def __init__(self):
        self.memory = MemoryStore()
        self.embeddings = EmbeddingEngine()

    async def build_context(
        self,
        user_message: str,
        conversation_history: list = None,
        customer_name: str = None,
    ) -> str:
        """Build enriched context string to prepend to MAX's system prompt."""
        sections: list[str] = []

        # 1. Founder profile (always loaded)
        founder = self.memory.search_memories(category="founder", limit=5)
        if founder:
            sections.append("## Founder Context")
            for m in founder:
                sections.append(f"- {m['content']}")

        # 2. Relevant memories via semantic search
        try:
            all_memories = self.memory.search_memories(limit=100, min_importance=3)
            if all_memories:
                relevant = await self.embeddings.semantic_search(
                    user_message, all_memories, top_k=10
                )
                if relevant:
                    sections.append("\n## Relevant Memory")
                    for m in relevant[:MAX_CONTEXT_MEMORIES]:
                        sections.append(f"- [{m.get('category', '')}] {m['content']}")
        except Exception:
            # Embeddings might not be available — fall back to keyword search
            first_word = user_message.split()[0] if user_message.strip() else None
            keyword_results = self.memory.search_memories(query=first_word, limit=5)
            if keyword_results:
                sections.append("\n## Related Memory")
                for m in keyword_results:
                    sections.append(f"- {m['content']}")

        # 3. Customer context (if discussing a specific customer)
        if customer_name:
            customer_memories = self.memory.search_memories(
                query=customer_name, category="customer", limit=10
            )
            if customer_memories:
                sections.append(f"\n## Customer: {customer_name}")
                for m in customer_memories:
                    sections.append(f"- {m['content']}")

        # 4. Recent conversation summaries
        recent_convos = self.memory.get_recent(category="conversation", limit=3)
        if recent_convos:
            sections.append("\n## Recent Conversations")
            for c in recent_convos:
                sections.append(f"- [{c.get('created_at', 'recent')}] {c['content'][:200]}")

        # 5. Active tasks
        active_tasks = self.memory.search_memories(category="task", limit=10)
        pending = [t for t in active_tasks if "done" not in t.get("content", "").lower()]
        if pending:
            sections.append("\n## Active Tasks")
            for t in pending:
                sections.append(f"- {t['content']}")

        # 6. Operational state
        ops = self.memory.get_recent(category="operational", limit=5)
        if ops:
            sections.append("\n## Current Operations")
            for o in ops:
                sections.append(f"- {o['content']}")

        # Assemble and truncate to token limit
        context = "\n".join(sections)
        # Rough token estimation (4 chars per token)
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
