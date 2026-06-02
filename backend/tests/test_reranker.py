"""Tests for reranker service."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

from app.services.reranker_service import LocalBGEReranker, NoopReranker, RerankerFactory


def _sample_chunks():
    return [
        {"content": "low", "score": 0.2, "metadata": {"document_id": 1, "chunk_index": 0}},
        {"content": "high", "score": 0.9, "metadata": {"document_id": 1, "chunk_index": 1}},
        {"content": "mid", "score": 0.5, "metadata": {"document_id": 2, "chunk_index": 0}},
    ]


def test_noop_reranker_sorts_by_score():
    chunks = _sample_chunks()
    result = asyncio.run(NoopReranker().rerank("q", chunks, top_n=2))
    assert len(result) == 2
    assert result[0]["content"] == "high"


def test_reranker_disabled_returns_noop():
    with patch("app.services.reranker_service.get_settings") as mock_settings:
        mock_settings.return_value.RERANKER_ENABLED = False
        mock_settings.return_value.RERANKER_PROVIDER = "none"
        RerankerFactory.reset()
        svc = RerankerFactory.get_service()
        assert isinstance(svc, NoopReranker)


def test_reranker_noop_provider():
    with patch("app.services.reranker_service.get_settings") as mock_settings:
        mock_settings.return_value.RERANKER_ENABLED = True
        mock_settings.return_value.RERANKER_PROVIDER = "noop"
        RerankerFactory.reset()
        svc = RerankerFactory.get_service()
        assert isinstance(svc, NoopReranker)


def test_local_bge_fallback_to_noop_when_unavailable():
    reranker = LocalBGEReranker.__new__(LocalBGEReranker)
    reranker._noop = NoopReranker()
    reranker._available = False
    result = asyncio.run(reranker.rerank("query", _sample_chunks(), top_n=2))
    assert len(result) == 2
    assert result[0]["content"] == "high"


def test_reranker_top_n_limit():
    chunks = _sample_chunks()
    result = asyncio.run(NoopReranker().rerank("q", chunks, top_n=1))
    assert len(result) == 1
