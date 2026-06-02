"""Unit tests for RAG cache service."""

import asyncio
import json
from unittest.mock import AsyncMock

from app.services.cache_service import CacheService, build_rag_cache_key


def test_build_rag_cache_key_format():
    key = build_rag_cache_key(1, 42, "hello", "en")
    assert key.startswith("rag:1:42:")
    assert len(key.split(":")[-1]) == 64


def test_build_rag_cache_key_stable():
    a = build_rag_cache_key(1, 1, "测试", "zh")
    b = build_rag_cache_key(1, 1, "测试", "zh")
    assert a == b
    c = build_rag_cache_key(1, 1, "测试", "en")
    assert a != c


def test_cache_service_get_set():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()

    svc = CacheService(redis)

    async def _run():
        await svc.set("k", "v", 60)
        redis.set.assert_called_once_with("k", "v", ex=60)

        payload = {"answer": "ok", "references": []}
        redis.get.return_value = json.dumps(payload)
        result = await svc.get_rag_result("k")
        assert result == payload

    asyncio.run(_run())
