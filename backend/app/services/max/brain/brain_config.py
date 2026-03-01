"""
Brain configuration — paths, models, limits.
Detects external drive (BACKUP11) or falls back to local storage.
"""
import os
from pathlib import Path

# Brain location — defaults to external drive, falls back to local
BRAIN_DRIVE = os.environ.get("MAX_BRAIN_PATH", "/media/rg/BACKUP11/ollama/brain")
LOCAL_FALLBACK = Path.home() / "Empire" / "backend" / "data" / "brain"


def get_brain_path() -> Path:
    """Get brain storage path — external drive preferred, local fallback."""
    brain_path = Path(BRAIN_DRIVE)
    if brain_path.exists():
        return brain_path
    # Fallback to local if drive not mounted
    LOCAL_FALLBACK.mkdir(parents=True, exist_ok=True)
    return LOCAL_FALLBACK


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
REALTIME_LEARNING_ENABLED = False   # disabled for performance — use batch learning instead
BATCH_LEARNING_ENABLED = True       # learn every N exchanges instead of every exchange
BATCH_LEARNING_INTERVAL = 5         # trigger learning every 5 messages (background Ollama call)
