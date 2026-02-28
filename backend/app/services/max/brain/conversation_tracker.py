"""
Tracks active conversations and triggers summarization.
"""
import logging
from .brain_config import CONVERSATION_SUMMARY_THRESHOLD
from .context_builder import ContextBuilder

logger = logging.getLogger("max.brain.tracker")


class ConversationTracker:
    def __init__(self):
        self.active_conversations: dict[str, list[dict]] = {}
        self.context_builder = ContextBuilder()

    def add_message(self, conversation_id: str, role: str, content: str):
        """Track a message in the active conversation."""
        if conversation_id not in self.active_conversations:
            self.active_conversations[conversation_id] = []
        self.active_conversations[conversation_id].append(
            {"role": role, "content": content}
        )

    def get_message_count(self, conversation_id: str) -> int:
        return len(self.active_conversations.get(conversation_id, []))

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
