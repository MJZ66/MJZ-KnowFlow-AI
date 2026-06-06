"""
Embedding service abstraction.

Providers:
- hash: deterministic local hash (default, no external deps)
- local_bge: reserved — falls back to hash if model unavailable
- dashscope / openai_compatible: remote embedding API
"""

from __future__ import annotations

import hashlib
import logging
import math
from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def hash_embedding(text: str, dim: int = 384) -> list[float]:
    """Deterministic local embedding for Chinese/English mixed text."""
    vec = [0.0] * dim
    if not text:
        return vec

    normalized = text.lower().strip()
    grams: list[str] = []
    for i in range(len(normalized)):
        grams.append(normalized[i])
        if i + 2 <= len(normalized):
            grams.append(normalized[i:i + 2])
        if i + 3 <= len(normalized):
            grams.append(normalized[i:i + 3])

    for gram in grams:
        h = hashlib.md5(gram.encode("utf-8")).hexdigest()
        idx = int(h[:8], 16) % dim
        sign = 1.0 if int(h[8:10], 16) % 2 == 0 else -1.0
        vec[idx] += sign

    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec


class BaseEmbeddingService(ABC):
    """Abstract embedding provider."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        ...

    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...

    @abstractmethod
    async def embed_query(self, query: str) -> list[float]:
        ...

    def metadata_fields(self) -> dict[str, Any]:
        return {
            "embedding_provider": self.provider_name,
            "embedding_model": self.model_name,
            "embedding_dim": self.dimension,
        }


class HashEmbeddingService(BaseEmbeddingService):
    """Local hash embedding — stable fallback, no model download."""

    def __init__(self, dim: int | None = None):
        settings = get_settings()
        self._dim = dim or (384 if settings.EMBEDDING_PROVIDER == "hash" else settings.EMBEDDING_DIM)

    @property
    def provider_name(self) -> str:
        return "hash"

    @property
    def model_name(self) -> str:
        return "hash-ngram-v1"

    @property
    def dimension(self) -> int:
        return self._dim

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [hash_embedding(t, self._dim) for t in texts]

    async def embed_query(self, query: str) -> list[float]:
        return hash_embedding(query, self._dim)


class LocalBGEEmbeddingService(BaseEmbeddingService):
    """Local BGE model — optional in dev; required when production sets local_bge."""

    def __init__(self):
        settings = get_settings()
        self._model_id = settings.EMBEDDING_MODEL
        self._dim = settings.EMBEDDING_DIM
        self._device = settings.EMBEDDING_DEVICE
        self._fallback = HashEmbeddingService(dim=384)
        self._model = None
        self._available = False
        self._try_load()

    @property
    def is_available(self) -> bool:
        return self._available

    def _try_load(self) -> None:
        try:
            # Optional dependency — not required at install time
            from sentence_transformers import SentenceTransformer  # noqa: F401

            self._model = SentenceTransformer(self._model_id, device=self._device)
            self._available = True
            logger.info(f"Local BGE model loaded: {self._model_id}")
        except Exception as e:
            logger.warning(f"Local BGE unavailable ({self._model_id}), using hash fallback: {e}")
            self._available = False

    @property
    def provider_name(self) -> str:
        return "local_bge" if self._available else "hash"

    @property
    def model_name(self) -> str:
        return self._model_id if self._available else self._fallback.model_name

    @property
    def dimension(self) -> int:
        return self._dim if self._available else self._fallback.dimension

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not self._available:
            return await self._fallback.embed_documents(texts)
        import asyncio

        def _encode():
            return self._model.encode(texts, normalize_embeddings=True).tolist()

        return await asyncio.to_thread(_encode)

    async def embed_query(self, query: str) -> list[float]:
        if not self._available:
            return await self._fallback.embed_query(query)
        rows = await self.embed_documents([query])
        return rows[0]


class OpenAICompatibleEmbeddingService(BaseEmbeddingService):
    """OpenAI-compatible / DashScope embedding API."""

    def __init__(self, provider_label: str = "openai_compatible"):
        settings = get_settings()
        self._provider_label = provider_label
        self._api_base = settings.EMBEDDING_API_BASE or settings.LLM_API_BASE
        self._api_key = settings.EMBEDDING_API_KEY or settings.LLM_API_KEY
        self._model = settings.EMBEDDING_MODEL
        self._dim = settings.EMBEDDING_DIM
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._api_base.rstrip("/"),
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=60.0,
            )
        return self._client

    async def _embed(self, texts: list[str]) -> list[list[float]]:
        client = await self._get_client()
        response = await client.post(
            "/embeddings",
            json={"model": self._model, "input": texts},
        )
        if response.status_code != 200:
            raise RuntimeError(f"Embedding API failed: {response.status_code} {response.text}")
        data = response.json()
        return [item["embedding"] for item in data["data"]]

    @property
    def provider_name(self) -> str:
        return self._provider_label

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return self._dim

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._embed(texts)

    async def embed_query(self, query: str) -> list[float]:
        rows = await self._embed([query])
        return rows[0]


class EmbeddingServiceFactory:
    _instance: BaseEmbeddingService | None = None
    _provider: str | None = None

    @classmethod
    def get_service(cls) -> BaseEmbeddingService:
        settings = get_settings()
        provider = settings.EMBEDDING_PROVIDER

        if cls._instance is None or cls._provider != provider:
            if provider == "hash":
                cls._instance = HashEmbeddingService()
            elif provider == "local_bge":
                cls._instance = LocalBGEEmbeddingService()
            elif provider in ("dashscope", "openai_compatible"):
                cls._instance = OpenAICompatibleEmbeddingService(provider_label=provider)
            else:
                raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {provider}")
            cls._provider = provider
            logger.info(
                f"Embedding service: {cls._instance.provider_name} "
                f"model={cls._instance.model_name} dim={cls._instance.dimension}"
            )
        return cls._instance
