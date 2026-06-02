"""Score fusion utilities for hybrid retrieval."""

from __future__ import annotations


def _chunk_key(chunk: dict) -> str:
    meta = chunk.get("metadata") or {}
    doc_id = meta.get("document_id")
    chunk_index = meta.get("chunk_index", chunk.get("chunk_id"))
    if doc_id is not None and chunk_index is not None:
        return f"{doc_id}_{chunk_index}"
    return str(chunk.get("chunk_id") or id(chunk))


def reciprocal_rank_fusion(
    vector_results: list[dict],
    keyword_results: list[dict],
    k: int = 60,
    vector_weight: float = 0.7,
    keyword_weight: float = 0.3,
) -> list[dict]:
    """Reciprocal Rank Fusion with optional source weighting."""
    scores: dict[str, float] = {}
    items: dict[str, dict] = {}

    for rank, chunk in enumerate(vector_results):
        key = _chunk_key(chunk)
        scores[key] = scores.get(key, 0.0) + vector_weight / (k + rank + 1)
        items[key] = chunk

    for rank, chunk in enumerate(keyword_results):
        key = _chunk_key(chunk)
        scores[key] = scores.get(key, 0.0) + keyword_weight / (k + rank + 1)
        if key not in items:
            items[key] = chunk

    fused = []
    for key, rrf_score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        item = dict(items[key])
        item["score"] = round(rrf_score, 6)
        fused.append(item)
    return fused
