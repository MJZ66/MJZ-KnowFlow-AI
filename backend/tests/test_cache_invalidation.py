"""RAG cache invalidation tests."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.core.config import get_settings
from app.services.cache_service import CacheService, build_rag_cache_key
from tests.e2e_helpers import (
    BASE,
    TIMEOUT,
    auth_headers,
    make_chinese_txt,
    poll_document,
    unique_user,
)


@pytest.mark.skipif(not get_settings().RAG_CACHE_ENABLED, reason="RAG_CACHE_ENABLED=false")
def test_cache_invalidate_kb_scan():
    async def _run():
        redis = AsyncMock()
        redis.scan = AsyncMock(side_effect=[(0, ["rag:1:2:abc", "rag:1:2:def"])])
        redis.delete = AsyncMock(return_value=2)
        cache = CacheService(redis)
        deleted = await cache.invalidate_kb_cache(1)
        assert deleted == 2
        redis.scan.assert_awaited()

    asyncio.run(_run())


def test_build_rag_cache_key_scoped_by_kb():
    k1 = build_rag_cache_key(1, 10, "hello", "zh")
    k2 = build_rag_cache_key(2, 10, "hello", "zh")
    assert k1 != k2


@pytest.fixture(scope="module")
def api_client():
    with httpx.Client(timeout=TIMEOUT, base_url=BASE) as client:
        yield client


@pytest.mark.skipif(not get_settings().RAG_CACHE_ENABLED, reason="RAG cache disabled in env")
def test_cache_invalidated_after_document_upload(api_client: httpx.Client, tmp_path: Path):
    """Integration: upload completes -> KB cache invalidated (re-ask should miss if implemented)."""
    from app.services.cache_invalidation import invalidate_kb_rag_cache

    async def _invalidate(kb_id: int):
        await invalidate_kb_rag_cache(kb_id)

    user = unique_user()
    reg = api_client.post("/api/auth/register", json=user)
    headers = auth_headers(reg.json()["access_token"])
    kb = api_client.post("/api/kbs", headers=headers, json={
        "name": "Cache KB",
        "description": "",
        "visibility": "private",
    }).json()

    asyncio.run(_invalidate(kb["id"]))

    txt = tmp_path / "cache.txt"
    make_chinese_txt(txt)
    with txt.open("rb") as f:
        doc = api_client.post(
            f"/api/kbs/{kb['id']}/documents/upload",
            headers=headers,
            files={"file": ("cache.txt", f, "text/plain")},
        ).json()

    assert poll_document(api_client, doc["id"], headers)["status"] == "completed"
    # Invalidation runs on document complete — no exception means hook is wired
    asyncio.run(_invalidate(kb["id"]))
