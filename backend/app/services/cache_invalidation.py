"""RAG cache invalidation helpers."""

from __future__ import annotations

import logging

from app.core.config import get_settings
from app.core.redis import get_redis
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)


async def invalidate_kb_rag_cache(kb_id: int) -> int:
    """Invalidate all RAG cache entries for a knowledge base. Returns deleted count."""
    settings = get_settings()
    if not settings.RAG_CACHE_ENABLED:
        return 0

    try:
        redis = get_redis()
        cache = CacheService(redis)
        deleted = await cache.invalidate_kb_cache(kb_id)
        logger.info("rag_cache_invalidated kb_id=%s deleted=%s", kb_id, deleted)
        return deleted
    except Exception as e:
        logger.warning("rag_cache_invalidation_failed kb_id=%s error=%s", kb_id, e)
        return 0
