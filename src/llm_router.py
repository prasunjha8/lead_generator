"""
LLM provider abstraction layer.
Priority: Gemini 2.5 Flash → Groq → OpenRouter (free models)
Implements exponential backoff and automatic failover.
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)


# ── Base ──────────────────────────────────────────────────────────────────────

class BaseLLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def complete(self, prompt: str, max_tokens: int = 2000, response_format: Optional[str] = None) -> Optional[str]:
        ...

    async def complete_json(self, prompt: str, max_tokens: int = 2000) -> Optional[dict]:
        """Call complete() and parse the result as JSON."""
        raw = await self.complete(prompt, max_tokens, response_format="json")
        if not raw:
            return None
        try:
            cleaned = raw.strip()
            # Strip reasoning think blocks
            import re
            cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL).strip()

            # Strip markdown code fences if present
            if cleaned.startswith("```"):
                parts = cleaned.split("```")
                if len(parts) > 1:
                    cleaned = parts[1]
                    if cleaned.startswith("json"):
                        cleaned = cleaned[4:]
            return json.loads(cleaned.strip())
        except json.JSONDecodeError as e:
            logger.warning(f"[{self.name}] JSON parse error: {e} | raw: {raw[:200]}")
            return None


# ── Retry decorator ───────────────────────────────────────────────────────────

async def _with_backoff(coro_fn, max_retries: int = 4):
    """Run coro_fn() with exponential backoff on failure."""
    delay = 2
    for attempt in range(1, max_retries + 1):
        try:
            result = await coro_fn()
            return result
        except Exception as e:
            logger.warning(f"Attempt {attempt}/{max_retries} failed: {e}")
            if attempt < max_retries:
                await asyncio.sleep(delay)
                delay *= 2
    return None


# ── Gemini ────────────────────────────────────────────────────────────────────

class GeminiProvider(BaseLLMProvider):
    name = "Gemini"

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.model   = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def complete(self, prompt: str, max_tokens: int = 2000, response_format: Optional[str] = None) -> Optional[str]:
        if not self.api_key:
            return None

        url  = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": 0.3,
            }
        }
        if response_format == "json":
            body["generationConfig"]["responseMimeType"] = "application/json"

        async def _call():
            connector = aiohttp.TCPConnector(ssl=True)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(url, json=body,
                                        timeout=aiohttp.ClientTimeout(total=90)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["candidates"][0]["content"]["parts"][0]["text"]
                    elif resp.status in (429, 503):
                        raise Exception(f"Rate limited: {resp.status}")
                    else:
                        text = await resp.text()
                        raise Exception(f"Gemini {resp.status}: {text[:200]}")

        result = await _with_backoff(_call)
        if result:
            logger.info(f"[Gemini] ✓ response received")
        return result


# ── Groq ──────────────────────────────────────────────────────────────────────

class GroqProvider(BaseLLMProvider):
    name = "Groq"

    def __init__(self, api_key: str, models: list[str] = None):
        self.api_key = api_key
        self.models  = models or ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
        self.base_url = "https://api.groq.com/openai/v1"

    async def complete(self, prompt: str, max_tokens: int = 2000, response_format: Optional[str] = None) -> Optional[str]:
        if not self.api_key:
            return None

        # Cap max_tokens for Groq to prevent exceeding organization TPM limits (e.g. 6000 TPM)
        max_tokens = min(max_tokens, 1024)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        for model in self.models:
            body = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.3,
            }
            if response_format == "json":
                body["response_format"] = {"type": "json_object"}

            async def _call(m=model, b=body):
                connector = aiohttp.TCPConnector(ssl=True)
                async with aiohttp.ClientSession(
                    headers=headers, connector=connector
                ) as session:
                    async with session.post(
                        f"{self.base_url}/chat/completions",
                        json=b,
                        timeout=aiohttp.ClientTimeout(total=90)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            return data["choices"][0]["message"]["content"]
                        elif resp.status in (429, 503):
                            raise Exception(f"Rate limited on {m}: {resp.status}")
                        else:
                            text = await resp.text()
                            raise Exception(f"Groq {resp.status} ({m}): {text[:200]}")

            result = await _with_backoff(_call)
            if result:
                logger.info(f"[Groq:{model}] ✓ response received")
                return result

        return None


# ── OpenRouter ────────────────────────────────────────────────────────────────

class OpenRouterProvider(BaseLLMProvider):
    name = "OpenRouter"

    def __init__(self, api_key: str, models: list[str] = None):
        self.api_key = api_key
        self.models  = models or [
            "meta-llama/llama-3.1-8b-instruct:free",
            "qwen/qwen-2.5-7b-instruct:free",
            "google/gemini-2.5-flash",
        ]
        self.base_url = "https://openrouter.ai/api/v1"

    async def complete(self, prompt: str, max_tokens: int = 2000, response_format: Optional[str] = None) -> Optional[str]:
        if not self.api_key:
            return None

        # Cap max_tokens for OpenRouter to prevent token limits
        max_tokens = min(max_tokens, 2000)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://robolution.bitmesra.ac.in",
            "X-Title": "Robolution Sponsorship Intelligence",
        }

        for model in self.models:
            body = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.3,
            }
            if response_format == "json":
                body["response_format"] = {"type": "json_object"}

            async def _call(m=model, b=body):
                connector = aiohttp.TCPConnector(ssl=True)
                async with aiohttp.ClientSession(
                    headers=headers, connector=connector
                ) as session:
                    async with session.post(
                        f"{self.base_url}/chat/completions",
                        json=b,
                        timeout=aiohttp.ClientTimeout(total=120)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            return data["choices"][0]["message"]["content"]
                        elif resp.status in (429, 503):
                            raise Exception(f"Rate limited on {m}: {resp.status}")
                        else:
                            text = await resp.text()
                            raise Exception(f"OpenRouter {resp.status} ({m}): {text[:200]}")

            result = await _with_backoff(_call)
            if result:
                logger.info(f"[OpenRouter:{model}] ✓ response received")
                return result

        return None


# ── Router (failover logic) ───────────────────────────────────────────────────

class LLMRouter:
    """
    Tries providers in order: Gemini → Groq → OpenRouter.
    Falls back automatically on any failure.
    """

    def __init__(self, gemini_key: str, groq_key: str, openrouter_key: str,
                 gemini_model: str, groq_models: list, openrouter_models: list):
        self.providers: list[BaseLLMProvider] = []

        if gemini_key:
            self.providers.append(GeminiProvider(gemini_key, gemini_model))
        if groq_key:
            self.providers.append(GroqProvider(groq_key, groq_models))
        if openrouter_key:
            self.providers.append(OpenRouterProvider(openrouter_key, openrouter_models))

        if not self.providers:
            raise RuntimeError("No LLM provider configured. Set at least one API key in .env")

        logger.info(f"LLMRouter initialised with providers: {[p.name for p in self.providers]}")

    async def complete_json(self, prompt: str, max_tokens: int = 2000) -> Optional[dict]:
        for provider in self.providers:
            result = await provider.complete_json(prompt, max_tokens)
            if result:
                return result
            logger.warning(f"Provider {provider.name} failed, trying next...")
        logger.error("All LLM providers failed.")
        return None

    async def complete(self, prompt: str, max_tokens: int = 2000, response_format: Optional[str] = None) -> Optional[str]:
        for provider in self.providers:
            result = await provider.complete(prompt, max_tokens, response_format=response_format)
            if result:
                return result
        return None
