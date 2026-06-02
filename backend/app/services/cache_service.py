"""
RAG query result cache backed by Redis.

Cache key: rag:{kb_id}:{user_id}:{sha256(query+lang)}
TTL: RAG_CACHE_TTL_SECONDS (default 300s)

Do not cache:
- retrieval / LLM errors
- empty results (no valid chunks / insufficient evidence)
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def build_rag_cache_key(kb_id: int, user_id: int, query: str, lang: str) -> str:
    """Build deterministic cache key from kb, user, query and language."""
    payload = f"{query.strip()}{lang}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"rag:{kb_id}:{user_id}:{digest}"


class CacheService:
    """Thin async wrapper around Redis for RAG answer caching."""

    def __init__(self, redis):
        self.redis = redis

    async def get(self, key: str) -> str | None:
        return await self.redis.get(key)

    async def set(self, key: str, value: str, ttl: int) -> None:
        await self.redis.set(key, value, ex=ttl)

    async def get_rag_result(self, key: str) -> dict[str, Any] | None:
        raw = await self.get(key)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Invalid RAG cache payload for key=%s", key)
            return None

    async def set_rag_result(self, key: str, payload: dict[str, Any]) -> None:
        settings = get_settings()
        if not settings.RAG_CACHE_ENABLED:
            return
        ttl = settings.RAG_CACHE_TTL_SECONDS
        await self.set(key, json.dumps(payload, ensure_ascii=False), ttl)
        logger.debug("RAG cache set key=%s ttl=%ss", key, ttl)

    async def invalidate_kb_cache(self, kb_id: int) -> int:
        """Delete all RAG cache keys for a knowledge base using SCAN (not KEYS)."""
        pattern = f"rag:{kb_id}:*"
        deleted = 0
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                deleted += await self.redis.delete(*keys)
            if cursor == 0:
                break
        return deleted
