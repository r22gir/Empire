"""
Brain configuration — paths, models, limits.
Local NVMe is primary. External drive is backup-only (no live I/O).
"""
import os
from pathlib import Path

# Brain location — local NVMe is primary (fast, reliable, no USB power issues)
LOCAL_BRAIN = Path.home() / "Empire" / "backend" / "data" / "brain"


def get_brain_path() -> Path:
    """Get brain storage path — always local NVMe."""
    LOCAL_BRAIN.mkdir(parents=True, exist_ok=True)
    return LOCAL_BRAIN


def get_db_path() -> str:
    return str(get_brain_path() / "memories.db")


def get_embeddings_db_path() -> str:
    return str(get_brain_path() / "embeddings.db")


# Ollama configuration
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
EMBEDDING_MODEL = "nomic-embed-text"
REASONING_MODEL = "mistral:7b"
FALLBACK_MODEL = "llama3:latest"

# Memory limits
MAX_CONTEXT_MEMORIES = 20           # max memories to inject into context
MAX_CONTEXT_TOKENS = 4000           # max tokens of memory in context
CONVERSATION_SUMMARY_THRESHOLD = 6  # summarize after N messages (lowered from 10)
MEMORY_IMPORTANCE_DECAY = 0.95      # importance decays over time if not accessed
REALTIME_LEARNING_ENABLED = True    # enabled — uses cloud AI (Grok) for extraction
BATCH_LEARNING_ENABLED = False      # DISABLED — not needed with realtime on
BATCH_LEARNING_INTERVAL = 5         # (inactive — batch learning disabled)
