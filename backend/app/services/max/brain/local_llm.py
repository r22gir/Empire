"""
Local LLM client for MAX Brain operations.
Uses Ollama Mistral for summarization, classification, triage.
"""
import json
import httpx
import logging
from .brain_config import OLLAMA_BASE_URL, REASONING_MODEL, FALLBACK_MODEL

logger = logging.getLogger("max.brain.llm")


class LocalLLM:
    def __init__(self):
        self.base_url = OLLAMA_BASE_URL
        self.model = REASONING_MODEL
        self.fallback = FALLBACK_MODEL

    async def generate(self, prompt: str, system: str = "", max_tokens: int = 500) -> str:
        """Generate a response from local LLM."""
        for model in [self.model, self.fallback]:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.base_url}/api/generate",
                        json={
                            "model": model,
                            "prompt": prompt,
                            "system": system,
                            "stream": False,
                            "options": {"num_predict": max_tokens},
                        },
                        timeout=60.0,
                    )
                    response.raise_for_status()
                    return response.json()["response"]
            except Exception as e:
                logger.warning(f"Local LLM ({model}) failed: {e}")
                continue
        return ""

    async def is_available(self) -> bool:
        """Check if any local model is available."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/api/tags", timeout=5.0)
                models = [m.get("name", "") for m in resp.json().get("models", [])]
                return any(self.model in m or self.fallback in m for m in models)
        except Exception:
            return False

    async def summarize_conversation(self, messages: list[dict]) -> dict:
        """Summarize a conversation and extract key information."""
        conversation_text = "\n".join(
            f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages
        )

        prompt = f"""Summarize this conversation concisely. Extract:
1. SUMMARY: 2-3 sentence overview
2. KEY_DECISIONS: any decisions made (as JSON array)
3. TASKS: any action items or tasks mentioned (as JSON array)
4. CUSTOMERS: any customer names mentioned (as JSON array)
5. TOPICS: main topics discussed (as JSON array)
6. MOOD: overall tone (productive/planning/urgent/casual)
7. KEY_FACTS: important facts to remember (as JSON array)

Respond in JSON format only.

Conversation:
{conversation_text}"""

        response = await self.generate(
            prompt, system="You are a conversation analyzer. Respond only in valid JSON."
        )

        try:
            return json.loads(response)
        except (json.JSONDecodeError, TypeError):
            return {
                "summary": response,
                "key_decisions": [],
                "tasks": [],
                "customers": [],
                "topics": [],
                "mood": "productive",
                "key_facts": [],
            }

    async def classify_intent(self, message: str) -> dict:
        """Classify the intent of an incoming message."""
        prompt = f"""Classify this message:
"{message}"

Categories:
- task: an action item or reminder
- question: asking for information
- instruction: telling MAX to do something
- note: an idea or thought to save for later
- urgent: needs immediate attention
- customer: about a specific customer

Respond in JSON: {{"intent": "...", "priority": "low/medium/high/urgent", "customer_name": null or "Name", "summary": "brief summary"}}"""

        response = await self.generate(
            prompt, system="You are an intent classifier. Respond only in valid JSON."
        )

        try:
            return json.loads(response)
        except (json.JSONDecodeError, TypeError):
            return {
                "intent": "note",
                "priority": "medium",
                "customer_name": None,
                "summary": message[:100],
            }

    async def extract_facts(self, text: str) -> list[str]:
        """Extract memorable facts from text."""
        prompt = f"""Extract the key facts worth remembering from this text.
Return as a JSON array of short fact strings.
Only include facts that would be useful to recall later.

Text: {text}"""

        response = await self.generate(
            prompt, system="Extract facts as JSON array of strings."
        )

        try:
            return json.loads(response)
        except (json.JSONDecodeError, TypeError):
            return []
