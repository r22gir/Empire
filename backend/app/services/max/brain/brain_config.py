"""
Brain configuration — paths, models, limits.

Canonical brain path is resolved at runtime via `EMPIRE_BRAIN_DIR` (preferred)
or a canonical default (`~/empire-data/brain`). No legacy fallback to
`~/empire-repo/backend/data/brain` — the old lane is being retired.
"""
import os
from pathlib import Path


def _brain_root() -> Path:
    """Canonical brain root. Honors EMPIRE_BRAIN_DIR; default is canonical."""
    root = Path(
        os.environ.get(
            "EMPIRE_BRAIN_DIR", os.path.expanduser("~/empire-data/brain")
        )
    )
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_brain_path() -> Path:
    """Get brain storage path."""
    return _brain_root()


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
