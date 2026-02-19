"""OpenClaw API client for forwarding natural-language messages."""

import logging

import aiohttp

logger = logging.getLogger(__name__)


class OpenClawClient:
    """Sends messages to the OpenClaw AI agent and returns its response."""

    def __init__(self, host: str, timeout: int = 30):
        self._host = host.rstrip("/")
        self._timeout = aiohttp.ClientTimeout(total=timeout)

    async def chat(self, message: str) -> str:
        """Forward *message* to OpenClaw and return the text reply."""
        url = f"{self._host}/chat"
        payload = {"message": message}
        try:
            async with aiohttp.ClientSession(timeout=self._timeout) as session:
                async with session.post(url, json=payload) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    return data.get("response", "No response from OpenClaw.")
        except aiohttp.ClientError as exc:
            logger.error("OpenClaw request failed: %s", exc)
            return "⚠️ OpenClaw is not reachable right now. Please try again later."
