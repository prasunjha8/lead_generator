"""
Anthropic Claude provider — bonus provider that uses the claude-sonnet-4-6 model.
Useful when running inside a Claude-powered environment or if you have an Anthropic key.
Add ANTHROPIC_API_KEY to .env to enable.
"""

import logging
from typing import Optional

import aiohttp

from src.llm_router import BaseLLMProvider, _with_backoff

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseLLMProvider):
    name = "Anthropic"

    def __init__(self, api_key: str = "", model: str = "claude-sonnet-4-6"):
        self.api_key = api_key
        self.model   = model
        self.base_url = "https://api.anthropic.com/v1"

    async def complete(self, prompt: str, max_tokens: int = 2000) -> Optional[str]:
        # If no key provided, try without one (works in Anthropic sandbox)
        headers = {
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key

        body = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }

        async def _call():
            connector = aiohttp.TCPConnector(ssl=True)
            async with aiohttp.ClientSession(
                headers=headers, connector=connector
            ) as session:
                async with session.post(
                    f"{self.base_url}/messages",
                    json=body,
                    timeout=aiohttp.ClientTimeout(total=90),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["content"][0]["text"]
                    elif resp.status in (429, 503):
                        raise Exception(f"Rate limited: {resp.status}")
                    else:
                        text = await resp.text()
                        raise Exception(f"Anthropic {resp.status}: {text[:200]}")

        result = await _with_backoff(_call)
        if result:
            logger.info("[Anthropic] ✓ response received")
        return result
