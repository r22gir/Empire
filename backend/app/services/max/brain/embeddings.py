"""
Vector embeddings for semantic memory search.
Uses Ollama nomic-embed-text locally.
"""
import httpx
import logging
from .brain_config import OLLAMA_BASE_URL, EMBEDDING_MODEL

logger = logging.getLogger("max.brain.embeddings")


class EmbeddingEngine:
    def __init__(self):
        self.base_url = OLLAMA_BASE_URL
        self.model = EMBEDDING_MODEL

    async def embed(self, text: str) -> list[float]:
        """Generate embedding vector for text."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()["embedding"]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        embeddings = []
        for text in texts:
            emb = await self.embed(text)
            embeddings.append(emb)
        return embeddings

    async def semantic_search(
        self, query: str, memories: list[dict], top_k: int = 10
    ) -> list[dict]:
        """Find semantically similar memories to query.

        For MVP: uses cosine similarity in Python.
        Future: use sqlite-vec for faster vector search.
        """
        try:
            query_embedding = await self.embed(query)
        except Exception as e:
            logger.warning(f"Embedding failed, returning empty results: {e}")
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
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/api/tags", timeout=5.0)
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
