"""Tests for hybrid search behavior."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.rag.fusion import reciprocal_rank_fusion
from app.services.keyword_search_service import KeywordSearchService, _tokenize_query


def test_tokenize_includes_english_keywords():
    tokens = _tokenize_query("PostgreSQL Redis ChromaDB 数据库")
    lowered = [t.lower() for t in tokens]
    assert "postgresql" in lowered
    assert "redis" in lowered
    assert "chromadb" in lowered


def test_keyword_search_matches_postgresql():
    from app.models import DocumentChunk

    chunk = MagicMock(spec=DocumentChunk)
    chunk.id = 1
    chunk.document_id = 10
    chunk.knowledge_base_id = 1
    chunk.chunk_index = 0
    chunk.content = "数据库使用 PostgreSQL 存储业务数据。"
    chunk.page_number = None
    chunk.section_title = None

    row = (chunk, "中文测试文档.txt")
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(all=lambda: [row]))

    async def _run():
        svc = KeywordSearchService()
        return await svc.search_chunks(db, 1, "数据库使用什么？", top_k=5)

    results = asyncio.run(_run())
    assert results
    assert "PostgreSQL" in results[0]["content"]


def test_rrf_no_duplicate_chunks():
    vector = [
        {"content": "a", "score": 0.9, "metadata": {"document_id": 1, "chunk_index": 0}},
        {"content": "b", "score": 0.8, "metadata": {"document_id": 1, "chunk_index": 1}},
    ]
    keyword = [
        {"content": "a", "score": 0.7, "metadata": {"document_id": 1, "chunk_index": 0}},
    ]
    fused = reciprocal_rank_fusion(vector, keyword)
    keys = {f"{c['metadata']['document_id']}_{c['metadata']['chunk_index']}" for c in fused}
    assert len(keys) == len(fused)


def test_hybrid_disabled_uses_vector_only():
    from app.rag.rag_service import RAGService

    async def _run():
        rag = RAGService()
        db = AsyncMock()

        with patch("app.rag.rag_service.settings") as mock_settings:
            mock_settings.HYBRID_SEARCH_ENABLED = False
            mock_settings.RETRIEVAL_OVERSAMPLE = 2
            mock_settings.RERANKER_ENABLED = False
            mock_settings.RERANKER_TOP_N = 5

            rag.vector_service.search = AsyncMock(return_value=[{"content": "v", "score": 0.5, "metadata": {}}])
            rag.keyword_service.search_chunks = AsyncMock(return_value=[{"content": "k", "score": 0.5, "metadata": {}}])

            results = await rag._retrieve_raw(db, 1, "test", top_k=5)

            rag.vector_service.search.assert_awaited_once()
            rag.keyword_service.search_chunks.assert_not_awaited()
            assert len(results) == 1

    asyncio.run(_run())


def test_hybrid_enabled_calls_keyword_search():
    from app.rag.rag_service import RAGService

    async def _run():
        rag = RAGService()
        db = AsyncMock()

        vector_hit = {"content": "vector", "score": 0.9, "metadata": {"document_id": 1, "chunk_index": 0}}
        keyword_hit = {"content": "keyword", "score": 0.8, "metadata": {"document_id": 2, "chunk_index": 0}}

        with patch("app.rag.rag_service.settings") as mock_settings:
            mock_settings.HYBRID_SEARCH_ENABLED = True
            mock_settings.VECTOR_TOP_K = 20
            mock_settings.KEYWORD_TOP_K = 20
            mock_settings.HYBRID_VECTOR_WEIGHT = 0.7
            mock_settings.HYBRID_KEYWORD_WEIGHT = 0.3
            mock_settings.RETRIEVAL_OVERSAMPLE = 4
            mock_settings.RERANKER_ENABLED = False

            rag.vector_service.search = AsyncMock(return_value=[vector_hit])
            rag.keyword_service.search_chunks = AsyncMock(return_value=[keyword_hit])

            results = await rag._retrieve_raw(db, 1, "PostgreSQL", top_k=5)

            rag.keyword_service.search_chunks.assert_awaited_once()
            assert len(results) >= 1

    asyncio.run(_run())
