"""
Tracks active conversations and triggers learning + summarization.
Real-time learning: extracts facts from EVERY exchange (not just at threshold).
Periodic summarization: full conversation summary at threshold intervals.
"""
import logging
from .brain_config import CONVERSATION_SUMMARY_THRESHOLD
from .context_builder import ContextBuilder
from .memory_store import MemoryStore
from .local_llm import LocalLLM

logger = logging.getLogger("max.brain.tracker")


class ConversationTracker:
    def __init__(self):
        self.active_conversations: dict[str, list[dict]] = {}
        self.context_builder = ContextBuilder()
        self.memory = MemoryStore()
        self._llm = None

    def _get_llm(self) -> LocalLLM:
        if self._llm is None:
            self._llm = LocalLLM()
        return self._llm

    def add_message(self, conversation_id: str, role: str, content: str):
        """Track a message in the active conversation."""
        if conversation_id not in self.active_conversations:
            self.active_conversations[conversation_id] = []
        self.active_conversations[conversation_id].append(
            {"role": role, "content": content}
        )

    def get_message_count(self, conversation_id: str) -> int:
        return len(self.active_conversations.get(conversation_id, []))

    async def learn_from_exchange(
        self, conversation_id: str, user_message: str, assistant_response: str
    ):
        """Extract and store learnings from a single user+assistant exchange.

        This runs after EVERY response, making MAX smarter from day 1.
        Uses local LLM (mistral:7b) to extract facts, detect customers,
        and classify intent — all stored as persistent memories.
        """
        llm = self._get_llm()
        if not await llm.is_available():
            logger.debug("Local LLM unavailable — skipping real-time learning")
            return

        # 1. Extract facts from this exchange
        try:
            exchange_text = f"User: {user_message}\nAssistant: {assistant_response}"
            facts = await llm.extract_facts(exchange_text)
            for fact in facts:
                if len(fact.strip()) > 10:  # skip trivial facts
                    self.memory.add_memory(
                        category="conversation",
                        content=fact,
                        subject="exchange_fact",
                        importance=6,
                        source="auto_realtime",
                        conversation_id=conversation_id,
                        tags=["realtime", "exchange"],
                    )
            if facts:
                logger.info(f"Learned {len(facts)} facts from exchange in {conversation_id}")
        except Exception as e:
            logger.warning(f"Fact extraction failed: {e}")

        # 2. Classify user intent and store if notable
        try:
            intent_data = await llm.classify_intent(user_message)
            intent = intent_data.get("intent", "note")
            priority = intent_data.get("priority", "medium")

            # Store high-priority or customer-related intents
            if priority in ("high", "urgent") or intent == "customer":
                self.memory.add_memory(
                    category="intent",
                    content=f"[{priority}] {intent}: {intent_data.get('summary', user_message[:100])}",
                    subject=intent,
                    importance=7 if priority == "urgent" else 6,
                    source="auto_realtime",
                    conversation_id=conversation_id,
                )

            # Auto-detect and store customer mentions
            customer_name = intent_data.get("customer_name")
            if customer_name:
                self.memory.add_memory(
                    category="customer",
                    content=f"Customer '{customer_name}' mentioned: {user_message[:200]}",
                    subject=customer_name,
                    importance=7,
                    source="auto_realtime",
                    conversation_id=conversation_id,
                    tags=["customer_mention"],
                )
                logger.info(f"Detected customer mention: {customer_name}")

        except Exception as e:
            logger.warning(f"Intent classification failed: {e}")

    async def check_and_summarize(self, conversation_id: str):
        """Summarize if conversation reached threshold."""
        messages = self.active_conversations.get(conversation_id, [])
        if len(messages) >= CONVERSATION_SUMMARY_THRESHOLD:
            logger.info(
                f"Conversation {conversation_id} reached {len(messages)} messages, summarizing..."
            )
            await self.context_builder.post_conversation_process(
                conversation_id, messages
            )
            # Keep last 4 messages, summarize the rest
            self.active_conversations[conversation_id] = messages[-4:]

    async def end_conversation(self, conversation_id: str):
        """Summarize and archive when conversation ends."""
        messages = self.active_conversations.get(conversation_id, [])
        if messages:
            logger.info(f"Ending conversation {conversation_id} with {len(messages)} messages")
            await self.context_builder.post_conversation_process(
                conversation_id, messages
            )
            del self.active_conversations[conversation_id]

    def get_active_count(self) -> int:
        return len(self.active_conversations)
