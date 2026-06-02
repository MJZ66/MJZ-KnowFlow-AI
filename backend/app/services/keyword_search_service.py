"""
Lightweight keyword search over document_chunks via PostgreSQL ILIKE.
"""

from __future__ import annotations

import logging
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, DocumentChunk, DocumentStatus

logger = logging.getLogger(__name__)


def _tokenize_query(query: str) -> list[str]:
    """Extract search tokens for Chinese and English."""
    tokens: list[str] = []
    query = query.strip()
    if not query:
        return tokens

    # English words
    for word in re.findall(r"[A-Za-z0-9_]+", query):
        if len(word) >= 2:
            tokens.append(word.lower())

    # Chinese continuous substrings + char bigrams
    cjk = re.sub(r"[^\u4e00-\u9fff]", "", query)
    if cjk:
        if len(cjk) >= 2:
            tokens.append(cjk)
        for i in range(len(cjk) - 1):
            tokens.append(cjk[i:i + 2])

    # Deduplicate preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique[:12]


class KeywordSearchService:
    async def search_chunks(
        self,
        db: AsyncSession,
        knowledge_base_id: int,
        query: str,
        top_k: int = 20,
    ) -> list[dict]:
        tokens = _tokenize_query(query)
        if not tokens:
            return []

        # Only chunks from COMPLETED documents
        stmt = (
            select(DocumentChunk, Document.original_filename)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(
                DocumentChunk.knowledge_base_id == knowledge_base_id,
                Document.status == DocumentStatus.COMPLETED,
            )
        )
        result = await db.execute(stmt)
        rows = result.all()

        scored: dict[str, dict] = {}
        for chunk, filename in rows:
            content = chunk.content or ""
            content_lower = content.lower()
            hit = 0
            for token in tokens:
                if token.lower() in content_lower or token in content:
                    hit += 1
            if hit == 0:
                continue

            key = f"{chunk.document_id}_{chunk.chunk_index}"
            score = hit / len(tokens)
            item = {
                "chunk_id": chunk.id,
                "content": content,
                "score": round(score, 4),
                "metadata": {
                    "document_id": chunk.document_id,
                    "knowledge_base_id": chunk.knowledge_base_id,
                    "filename": filename,
                    "page_number": chunk.page_number,
                    "section_title": chunk.section_title,
                    "chunk_index": chunk.chunk_index,
                },
            }
            if key not in scored or scored[key]["score"] < score:
                scored[key] = item

        results = sorted(scored.values(), key=lambda x: x["score"], reverse=True)
        logger.info(f"Keyword search kb={knowledge_base_id} tokens={tokens} hits={len(results)}")
        return results[:top_k]
