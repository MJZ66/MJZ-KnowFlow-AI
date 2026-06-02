"""Unit tests for embedding and fusion modules."""

from app.rag.fusion import reciprocal_rank_fusion
from app.services.embedding_service import HashEmbeddingService, hash_embedding


def test_hash_embedding_dimension():
    import asyncio
    svc = HashEmbeddingService(dim=384)
    vec = asyncio.run(svc.embed_query("KnowFlow AI 测试"))
    assert len(vec) == 384
    assert abs(sum(x * x for x in vec) - 1.0) < 0.01


def test_hash_embedding_deterministic():
    a = hash_embedding("hello world", 384)
    b = hash_embedding("hello world", 384)
    assert a == b


def test_rrf_deduplication():
    vector = [{"content": "a", "score": 0.9, "metadata": {"document_id": 1, "chunk_index": 0}}]
    keyword = [{"content": "a", "score": 0.8, "metadata": {"document_id": 1, "chunk_index": 0}}]
    fused = reciprocal_rank_fusion(vector, keyword)
    assert len(fused) == 1
    assert fused[0]["score"] > 0
