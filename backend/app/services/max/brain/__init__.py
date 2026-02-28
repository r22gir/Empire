"""
MAX Brain — Portable persistent memory system.
Ollama is the memory. Grok/Claude is the intelligence. The external drive is the portable brain.
"""

from .brain_config import get_brain_path, get_db_path, get_embeddings_db_path
from .memory_store import MemoryStore
from .embeddings import EmbeddingEngine
from .local_llm import LocalLLM
from .context_builder import ContextBuilder
from .conversation_tracker import ConversationTracker

__all__ = [
    "get_brain_path", "get_db_path", "get_embeddings_db_path",
    "MemoryStore", "EmbeddingEngine", "LocalLLM",
    "ContextBuilder", "ConversationTracker",
]
