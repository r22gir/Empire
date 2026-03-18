"""
Vector embeddings for semantic memory search.
Uses Ollama nomic-embed-text locally.
Fast-fails when Ollama is offline (no 30s timeout).
"""
import time
import httpx
import logging
from .brain_config import OLLAMA_BASE_URL, EMBEDDING_MODEL

logger = logging.getLogger("max.brain.embeddings")

# ── Fast Ollama availability cache (avoids hitting Ollama on every request) ──
_ollama_cache = {"available": False, "checked_at": 0.0}
_OLLAMA_CHECK_INTERVAL = 15.0  # Re-check every 15 seconds


def _is_ollama_available() -> bool:
    """Quick 1-second sync check. Cached for 15s to avoid spamming."""
    now = time.time()
    if now - _ollama_cache["checked_at"] < _OLLAMA_CHECK_INTERVAL:
        return _ollama_cache["available"]
    try:
        resp = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=1.0)
        _ollama_cache["available"] = resp.status_code == 200
    except Exception:
        _ollama_cache["available"] = False
    _ollama_cache["checked_at"] = now
    return _ollama_cache["available"]


class EmbeddingEngine:
    def __init__(self):
        self.base_url = OLLAMA_BASE_URL
        self.model = EMBEDDING_MODEL

    async def embed(self, text: str) -> list[float]:
        """Generate embedding vector for text. Returns [] instantly if Ollama is offline."""
        if not _is_ollama_available():
            return []
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()["embedding"]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts. Returns [] instantly if Ollama is offline."""
        if not _is_ollama_available():
            return [[] for _ in texts]
        embeddings = []
        for text in texts:
            emb = await self.embed(text)
            embeddings.append(emb)
        return embeddings

    async def semantic_search(
        self, query: str, memories: list[dict], top_k: int = 10
    ) -> list[dict]:
        """Find semantically similar memories to query.
        Returns [] instantly when Ollama is offline — no timeout, no error log.
        """
        if not _is_ollama_available():
            return []
        try:
            query_embedding = await self.embed(query)
            if not query_embedding:
                return []
        except Exception:
            return []

        scored = []
        for memory in memories:
            if "embedding" in memory and memory["embedding"]:
                score = self._cosine_similarity(query_embedding, memory["embedding"])
                scored.append((score, memory))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:top_k]]

    async def is_available(self) -> bool:
        """Check if the embedding model is loaded and ready."""
        if not _is_ollama_available():
            return False
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/api/tags", timeout=2.0)
                models = resp.json().get("models", [])
                return any(self.model in m.get("name", "") for m in models)
        except Exception:
            return False

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
