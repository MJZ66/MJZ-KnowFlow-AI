"""
Async Redis client singleton.

Uses redis.asyncio (redis>=5.x). The legacy aioredis package is merged into redis-py.
"""

from __future__ import annotations

from redis.asyncio import Redis
from redis.asyncio import from_url as redis_from_url

from app.core.config import get_settings

_redis: Redis | None = None


def get_redis() -> Redis:
    """Return a shared async Redis connection."""
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = redis_from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def close_redis() -> None:
    """Close the shared Redis connection on application shutdown."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
