"""
LLM Service for answer generation using Qwen3 / OpenAI-Compatible API.

Supports:
- Streaming chat completion via SSE
- Non-streaming chat completion (fallback)
- Provider abstraction (qwen, openai_compatible, ollama)
"""

import json
import logging
from typing import AsyncGenerator, Optional

import httpx

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class LLMService:
    """Unified interface for LLM chat completion with streaming support.

    Configured via environment variables:
    - LLM_PROVIDER: qwen, openai_compatible, ollama
    - LLM_API_BASE: API endpoint base URL
    - LLM_API_KEY: API key
    - LLM_MODEL: Model name
    """

    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.api_base = settings.LLM_API_BASE.rstrip("/")
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.api_base,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(120.0, connect=10.0),
            )
        return self._client

    def _build_url(self) -> str:
        """Build the chat completions endpoint URL based on provider."""
        # Most OpenAI-compatible APIs use /chat/completions
        return f"{self.api_base}/chat/completions"

    async def stream_chat(
        self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 2048
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion responses.

        Yields content delta strings as they arrive.

        Args:
            messages: List of {"role": "...", "content": "..."}
            temperature: Generation temperature
            max_tokens: Max tokens to generate

        Yields:
            Content string tokens as they arrive from the API.
        """
        client = await self._get_client()
        url = self._build_url()

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        logger.info(f"Streaming chat: model={self.model}, messages={len(messages)}")

        async with client.stream("POST", url, json=payload) as response:
            if response.status_code != 200:
                error_text = await response.aread()
                logger.error(f"LLM API error ({response.status_code}): {error_text}")
                raise RuntimeError(f"LLM API error: {response.status_code}")

            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue

                data_str = line[6:]  # Remove "data: " prefix

                if data_str.strip() == "[DONE]":
                    break

                try:
                    data = json.loads(data_str)
                    choices = data.get("choices", [])

                    if not choices:
                        continue

                    delta = choices[0].get("delta", {})
                    content = delta.get("content", "")

                    if content:
                        yield content

                except json.JSONDecodeError:
                    continue

    async def chat(
        self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 2048
    ) -> str:
        """Non-streaming chat completion.

        Args:
            messages: List of {"role": "...", "content": "..."}
            temperature: Generation temperature
            max_tokens: Max tokens to generate

        Returns:
            Complete response text.
        """
        client = await self._get_client()
        url = self._build_url()

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        response = await client.post(url, json=payload)

        if response.status_code != 200:
            error_text = response.text
            logger.error(f"LLM API error ({response.status_code}): {error_text}")
            raise RuntimeError(f"LLM API error: {response.status_code}")

        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            return ""

        return choices[0].get("message", {}).get("content", "")

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Global instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create the global LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
