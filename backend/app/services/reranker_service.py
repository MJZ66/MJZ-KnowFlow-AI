"""
Reranker service abstraction.

Default: NoopReranker (pass-through sorted by score).
Optional: LocalBGEReranker (reserved, falls back to noop).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class BaseReranker(ABC):
    @abstractmethod
    async def rerank(self, query: str, chunks: list[dict], top_n: int) -> list[dict]:
        ...


class NoopReranker(BaseReranker):
    """Sort by existing score and return top_n."""

    async def rerank(self, query: str, chunks: list[dict], top_n: int) -> list[dict]:
        sorted_chunks = sorted(chunks, key=lambda c: c.get("score", 0), reverse=True)
        return sorted_chunks[:top_n]


class LocalBGEReranker(BaseReranker):
    """Local cross-encoder reranker — optional, falls back to noop."""

    def __init__(self):
        settings = get_settings()
        self._model_id = settings.RERANKER_MODEL
        self._noop = NoopReranker()
        self._model = None
        self._available = False
        self._try_load()

    def _try_load(self) -> None:
        try:
            from sentence_transformers import CrossEncoder  # noqa: F401

            self._model = CrossEncoder(self._model_id)
            self._available = True
            logger.info(f"Reranker model loaded: {self._model_id}")
        except Exception as e:
            logger.warning(f"Reranker unavailable ({self._model_id}), using noop: {e}")

    async def rerank(self, query: str, chunks: list[dict], top_n: int) -> list[dict]:
        if not self._available or not chunks:
            return await self._noop.rerank(query, chunks, top_n)

        import asyncio

        pairs = [[query, c.get("content", "")] for c in chunks]

        def _score():
            scores = self._model.predict(pairs)
            return scores.tolist() if hasattr(scores, "tolist") else list(scores)

        scores = await asyncio.to_thread(_score)
        ranked = []
        for chunk, score in zip(chunks, scores):
            item = dict(chunk)
            item["score"] = round(float(score), 4)
            ranked.append(item)
        ranked.sort(key=lambda c: c.get("score", 0), reverse=True)
        return ranked[:top_n]


class RerankerFactory:
    _instance: BaseReranker | None = None

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    @classmethod
    def get_service(cls) -> BaseReranker:
        settings = get_settings()
        if not settings.RERANKER_ENABLED or settings.RERANKER_PROVIDER in ("none", "noop"):
            return NoopReranker()

        if cls._instance is None:
            if settings.RERANKER_PROVIDER == "local_bge":
                cls._instance = LocalBGEReranker()
            else:
                cls._instance = NoopReranker()
        return cls._instance
