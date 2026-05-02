"""
LLM client for MAX Brain operations.
Tries Ollama first (local), then MiniMax cloud (when MAX_PRIMARY_PROVIDER=minimax
and MINIMAX_API_KEY is set), then stops — xAI Grok is only used when MAX_DISABLE_XAI
is NOT true and no other provider succeeds.

MAX_DISABLE_XAI=true means: never call xAI/Grok anywhere in Empire.
"""
import os
import json
import httpx
import logging
from .brain_config import OLLAMA_BASE_URL, REASONING_MODEL, FALLBACK_MODEL

logger = logging.getLogger("max.brain.llm")

XAI_BASE_URL = os.getenv("XAI_BASE_URL", "https://api.x.ai/v1").rstrip("/")
XAI_API_URL = f"{XAI_BASE_URL}/chat/completions"
XAI_BRAIN_MODEL = os.getenv("XAI_BRAIN_MODEL") or os.getenv("XAI_MODEL", "grok-4-fast-non-reasoning")

# Empire-wide provider policy — read once at import time
MAX_DISABLE_XAI = os.getenv("MAX_DISABLE_XAI", "").lower() in ("true", "1", "yes")
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")
MINIMAX_BASE_URL = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1").rstrip("/")
MINIMAX_MODEL = os.getenv("MINIMAX_MODEL", "MiniMax-M2.7")


class LocalLLM:
    def __init__(self):
        self.base_url = OLLAMA_BASE_URL
        self.model = REASONING_MODEL
        self.fallback = FALLBACK_MODEL
        self._xai_key = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY", "")
        self._xai_url = XAI_API_URL
        self._xai_model = XAI_BRAIN_MODEL
        self._minimax_key = MINIMAX_API_KEY
        self._minimax_url = f"{MINIMAX_BASE_URL}/chat/completions"
        self._minimax_model = MINIMAX_MODEL
        self._max_disable_xai = MAX_DISABLE_XAI
        self._ollama_available: bool | None = None

    async def generate(self, prompt: str, system: str = "", max_tokens: int = 500) -> str:
        """Generate a response — Ollama -> MiniMax (if policy allows) -> stop.

        xAI Grok is only used when MAX_DISABLE_XAI is false and all other
        providers have failed. This function never calls xAI when disabled.
        """
        # Try Ollama first (always allowed — local, no external dependency)
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
                        timeout=15.0,
                    )
                    response.raise_for_status()
                    return response.json()["response"]
            except Exception:
                continue

        # MiniMax cloud — primary when configured and xAI is disabled
        if self._minimax_key:
            try:
                return await self._minimax_generate(prompt, system, max_tokens)
            except Exception as e:
                logger.warning(f"MiniMax brain fallback failed: {e}")

        # xAI Grok — ONLY when not disabled by MAX_DISABLE_XAI policy
        if self._xai_key and not self._max_disable_xai:
            try:
                return await self._grok_generate(prompt, system, max_tokens)
            except Exception as e:
                logger.warning(f"Grok brain fallback failed: {e}")

        # No provider succeeded — return empty, do NOT fake a response
        logger.error("[brain] All LLM providers failed: Ollama unavailable, MiniMax key=%s, xAI disabled=%s",
                     bool(self._minimax_key), self._max_disable_xai)
        return ""

    async def _minimax_generate(self, prompt: str, system: str = "", max_tokens: int = 500) -> str:
        """Call MiniMax API for brain operations."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self._minimax_url,
                headers={
                    "Authorization": f"Bearer {self._minimax_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._minimax_model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                },
                timeout=30.0,
            )
            if resp.status_code != 200:
                raise Exception(f"MiniMax HTTP {resp.status_code} model={self._minimax_model}: {resp.text[:200]}")
            return resp.json()["choices"][0]["message"]["content"]

    async def _grok_generate(self, prompt: str, system: str = "", max_tokens: int = 500) -> str:
        """Call xAI Grok API for brain operations — ONLY when MAX_DISABLE_XAI=false."""
        if self._max_disable_xai:
            raise Exception("xAI/Grok called despite MAX_DISABLE_XAI=true — this should never happen")
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self._xai_url,
                headers={
                    "Authorization": f"Bearer {self._xai_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._xai_model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                },
                timeout=30.0,
            )
            if resp.status_code != 200:
                raise Exception(f"xAI HTTP {resp.status_code} model={self._xai_model} base_url={XAI_BASE_URL}: {resp.text[:200]}")
            return resp.json()["choices"][0]["message"]["content"]

    async def is_available(self) -> bool:
        """Check if any LLM is available (Ollama, or MiniMax if xAI is disabled)."""
        # Check Ollama first
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/api/tags", timeout=3.0)
                models = [m.get("name", "") for m in resp.json().get("models", [])]
                if any(self.model in m or self.fallback in m for m in models):
                    return True
        except Exception:
            pass

        # MiniMax is available if key is set (regardless of xAI disable — it's an alternative)
        if self._minimax_key:
            return True

        # xAI Grok only counts when not disabled
        if self._xai_key and not self._max_disable_xai:
            return True

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

        return self._parse_json_dict(response, {
            "summary": response[:200] if response else "",
            "key_decisions": [],
            "tasks": [],
            "customers": [],
            "topics": [],
            "mood": "productive",
            "key_facts": [],
        })

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

        return self._parse_json_dict(response, {
            "intent": "note",
            "priority": "medium",
            "customer_name": None,
            "summary": message[:100],
        })

    @staticmethod
    def _parse_json_dict(text: str, fallback: dict) -> dict:
        """Robustly parse a JSON object from LLM output."""
        if not text:
            return fallback
        text = text.strip()
        try:
            result = json.loads(text)
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, TypeError):
            pass
        import re
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
                if isinstance(result, dict):
                    return result
            except (json.JSONDecodeError, TypeError):
                pass
        return fallback

    async def extract_facts(self, text: str) -> list[str]:
        """Extract memorable facts from text."""
        prompt = f"""Extract the key facts worth remembering from this text.
Return as a JSON array of short fact strings.
Only include facts that would be useful to recall later.

Text: {text}"""

        response = await self.generate(
            prompt, system="Extract facts as JSON array of strings."
        )

        return self._parse_json_list(response)

    @staticmethod
    def _parse_json_list(text: str) -> list:
        """Robustly parse a JSON array from LLM output."""
        if not text:
            return []
        text = text.strip()
        # Try direct parse
        try:
            result = json.loads(text)
            if isinstance(result, list):
                return result
        except (json.JSONDecodeError, TypeError):
            pass
        # Try extracting JSON array from surrounding text
        import re
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
                if isinstance(result, list):
                    return result
            except (json.JSONDecodeError, TypeError):
                pass
        return []
