"""Tests for retrieval quality pipeline."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.models import DocumentStatus
from app.rag.rag_service import RAGService, _dedupe_chunks, _chunks_to_references


def test_dedupe_chunks():
    chunks = [
        {"content": "a", "metadata": {"document_id": 1, "chunk_index": 0}},
        {"content": "a-dup", "metadata": {"document_id": 1, "chunk_index": 0}},
        {"content": "b", "metadata": {"document_id": 1, "chunk_index": 1}},
    ]
    assert len(_dedupe_chunks(chunks)) == 2


def test_chunks_to_references_shape():
    refs = _chunks_to_references([
        {"content": "hello world", "score": 0.8, "metadata": {"filename": "t.txt", "document_id": 1, "chunk_index": 0}},
    ])
    assert refs[0]["source_filename"] == "t.txt"
    assert refs[0]["score"] == 0.8
    assert "hello" in refs[0]["content_preview"]


def test_filter_excludes_non_completed_documents():
    async def _run():
        rag = RAGService()
        db = AsyncMock()

        completed_chunk = {
            "content": "ok",
            "metadata": {"document_id": 1, "chunk_index": 0},
        }
        failed_chunk = {
            "content": "bad",
            "metadata": {"document_id": 2, "chunk_index": 0},
        }

        mock_result = MagicMock()
        mock_result.all.return_value = [(1, DocumentStatus.COMPLETED), (2, DocumentStatus.FAILED)]
        db.execute = AsyncMock(return_value=mock_result)

        valid = await rag._filter_valid_chunks(db, [completed_chunk, failed_chunk])
        assert len(valid) == 1
        assert valid[0]["content"] == "ok"

    asyncio.run(_run())


def test_retrieve_with_stats_counts():
    async def _run():
        rag = RAGService()
        db = AsyncMock()

        raw = [
            {"content": "a", "score": 0.9, "metadata": {"document_id": 1, "chunk_index": 0}},
            {"content": "b", "score": 0.8, "metadata": {"document_id": 1, "chunk_index": 1}},
        ]

        with patch.object(rag, "_retrieve_raw", AsyncMock(return_value=raw)):
            with patch.object(rag, "_filter_valid_chunks", AsyncMock(return_value=raw)):
                with patch.object(rag.reranker, "rerank", AsyncMock(return_value=raw)):
                    with patch("app.rag.rag_service.settings") as mock_settings:
                        mock_settings.HYBRID_SEARCH_ENABLED = True
                        mock_settings.RERANKER_ENABLED = True
                        mock_settings.RERANKER_TOP_N = 5

                        stats = await rag.retrieve_with_stats(db, 1, "PostgreSQL", top_k=5)

        assert stats["mode"] == "hybrid"
        assert stats["raw_count"] == 2
        assert stats["valid_count"] == 2
        assert stats["reranked_count"] == 2
        assert len(stats["references"]) == 2

    asyncio.run(_run())


def test_vector_dimension_mismatch_error_code():
    from app.core.errors import ErrorCode, error_response

    body = error_response(ErrorCode.VECTOR_DIMENSION_MISMATCH)
    assert body["code"] == "VECTOR_DIMENSION_MISMATCH"
    assert "维度" in body["message"]
    assert "dimension mismatch" in body["message_en"].lower()
