"""
RAG (Retrieval-Augmented Generation) orchestration service.

Flow:
1. User asks a question in a chat session
2. Retrieve top-k relevant chunks from vector store
3. Build prompt with context + chat history + question
4. Stream LLM response via SSE
5. Save assistant message + RAG references
"""

import json
import logging
from typing import AsyncGenerator, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode, error_response, error_response
from app.core.metrics import record_rag_cache_hit, record_rag_cache_miss, record_rag_retrieval
from app.core.redis import get_redis
from app.models import ChatMessage, ChatSession, Document, DocumentStatus, MessageRole, RagReference
from app.rag.fusion import reciprocal_rank_fusion
from app.services.cache_service import CacheService, build_rag_cache_key
from app.services.keyword_search_service import KeywordSearchService
from app.services.reranker_service import RerankerFactory
from app.services.vector_service import VectorServiceFactory
from app.services.llm_service import get_llm_service

settings = get_settings()
logger = logging.getLogger(__name__)

# RAG prompt templates — language-aware
RAG_SYSTEM_PROMPT_ZH = """你是 KnowFlow AI 的知识库问答助手。
请严格基于给定的知识库资料回答用户问题。
如果资料不足，请明确说明"当前知识库中没有找到足够依据"。

回答要求：
- 优先使用用户提问的语言回答。如果用户使用中文，请用简体中文回答；如果用户使用英文，请用英文回答。
- 基于提供的知识库资料，给出清晰、准确、有条理的回答
- 如果引用了某个来源，可以在句末标注来源编号，如[1]、[2]
- 不要编造不存在的引用
- 如果资料不足以回答问题，请诚实说明"""

RAG_SYSTEM_PROMPT_EN = """You are KnowFlow AI, a knowledge base Q&A assistant.
Answer strictly based on the provided knowledge base materials.
If the materials are insufficient, clearly state that you could not find enough evidence in the knowledge base.

Requirements:
- Reply in the same language as the user's question (Chinese or English).
- Give clear, accurate, and well-structured answers based on the provided materials.
- Cite source numbers like [1], [2] when referencing a source.
- Do not invent citations.
- Be honest when the materials are insufficient."""


def _is_mostly_english(text: str) -> bool:
    """Heuristic: true if the question is primarily English/Latin."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    latin = sum(1 for c in letters if ord(c) < 128)
    return latin / len(letters) >= 0.7


def _retrieval_mode() -> str:
    if settings.HYBRID_SEARCH_ENABLED:
        return "hybrid"
    return "vector"


def _chunks_to_references(chunks: list[dict]) -> list[dict]:
    references = []
    for chunk in chunks:
        meta = chunk.get("metadata", {})
        references.append({
            "source_filename": meta.get("filename"),
            "document_id": meta.get("document_id"),
            "chunk_id": chunk.get("chunk_id"),
            "chunk_index": meta.get("chunk_index"),
            "page_number": meta.get("page_number"),
            "section_title": meta.get("section_title"),
            "content_preview": chunk["content"][:200] if chunk.get("content") else "",
            "score": chunk.get("score"),
        })
    return references


def _dedupe_chunks(chunks: list[dict]) -> list[dict]:
    seen: set[str] = set()
    unique: list[dict] = []
    for chunk in chunks:
        meta = chunk.get("metadata") or {}
        key = f"{meta.get('document_id')}_{meta.get('chunk_index', chunk.get('chunk_id'))}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(chunk)
    return unique


async def _kb_doc_stats(db: AsyncSession, knowledge_base_id: int) -> dict[str, int]:
    """Count documents by coarse processing state for user-facing RAG hints."""
    result = await db.execute(
        select(Document.status, func.count())
        .where(Document.knowledge_base_id == knowledge_base_id)
        .group_by(Document.status)
    )
    stats = {"pending": 0, "completed": 0, "failed": 0, "total": 0}
    for status, count in result.all():
        stats["total"] += count
        val = status.value if hasattr(status, "value") else str(status)
        if val == DocumentStatus.COMPLETED.value:
            stats["completed"] += count
        elif val == DocumentStatus.FAILED.value:
            stats["failed"] += count
        else:
            stats["pending"] += count
    return stats


def _empty_retrieval_message(
    lang: str,
    *,
    pending: int,
    completed: int,
    raw_count: int,
    valid_count: int,
) -> tuple[str, str]:
    """Return (message, reason_code) when no chunks are available for RAG."""
    if pending > 0 and completed == 0:
        msg = (
            "Documents are still being processed. Please wait until processing completes before asking questions."
            if lang == "en"
            else "文档正在处理中，请等待处理完成后再提问。"
        )
        return msg, "processing"

    if completed == 0:
        msg = (
            "No processed documents are available in this knowledge base. Please upload documents and wait for processing to finish."
            if lang == "en"
            else "知识库中还没有可用于问答的文档，请先上传并等待处理完成。"
        )
        return msg, "no_documents"

    if pending > 0 and valid_count == 0 and raw_count == 0:
        msg = (
            "Some documents are still processing and no relevant content was retrieved yet. Please try again shortly."
            if lang == "en"
            else "部分文档仍在处理中，暂未检索到可用内容，请稍后再试。"
        )
        return msg, "processing_partial"

    msg = (
        "No relevant content was found in the knowledge base for this question. Try rephrasing or uploading more related documents."
        if lang == "en"
        else "未找到与问题相关的知识库内容，请尝试换一种问法，或上传更多相关文档。"
    )
    return msg, "no_match"


def build_rag_prompt(
    context_chunks: list[dict],
    chat_history: list[dict],
    question: str,
) -> list[dict]:
    """Build the message list for the LLM with RAG context.

    Args:
        context_chunks: Top-K retrieved chunks with content and metadata
        chat_history: Recent messages (user + assistant) from current session
        question: Current user question

    Returns:
        List of message dicts ready for LLM API call.
    """
    use_en = _is_mostly_english(question)

    # Format context with source markers
    context_parts = []
    for i, chunk in enumerate(context_chunks, start=1):
        meta = chunk.get("metadata", {})
        if use_en:
            source = f"[{i}] Source: {meta.get('filename', 'Unknown document')}"
            if meta.get("page_number"):
                source += f", page {meta.get('page_number')}"
        else:
            source = f"[{i}] 来源: {meta.get('filename', '未知文档')}"
            if meta.get("page_number"):
                source += f", 第{meta.get('page_number')}页"
        if meta.get("section_title"):
            source += f", {meta.get('section_title')}"
        context_parts.append(f"{source}\n{chunk['content']}")

    context_text = "\n\n---\n\n".join(context_parts)

    # Format chat history
    history_text = ""
    if chat_history:
        history_lines = []
        for msg in chat_history:
            if use_en:
                role_label = "User" if msg["role"] == "user" else "Assistant"
            else:
                role_label = "用户" if msg["role"] == "user" else "助手"
            history_lines.append(f"{role_label}: {msg['content']}")
        history_text = "\n".join(history_lines)

    system_prompt = RAG_SYSTEM_PROMPT_EN if use_en else RAG_SYSTEM_PROMPT_ZH
    if use_en:
        user_content = f"""【Knowledge Base Materials】
{context_text}

【Recent Chat History】
{history_text if history_text else "(No history)"}

【User Question】
{question}

Please provide a clear, accurate, and well-structured answer."""
    else:
        user_content = f"""【知识库资料】
{context_text}

【最近对话历史】
{history_text if history_text else "（无历史记录）"}

【用户问题】
{question}

请给出清晰、准确、有条理的回答。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    return messages


class RAGService:
    """Orchestrates retrieval + generation for RAG Q&A.

    Strategy:
    1. Retrieve top_k * 2 candidates from vector store (oversampling)
    2. Filter: keep only chunks from COMPLETED documents
    3. Take the top N results for the LLM
    4. Build prompt and stream answer
    """

    def __init__(self):
        self.vector_service = VectorServiceFactory.get_service()
        self.llm_service = get_llm_service()
        self.keyword_service = KeywordSearchService()
        self.reranker = RerankerFactory.get_service()

    async def _retrieve_raw(
        self,
        db: AsyncSession,
        knowledge_base_id: int,
        query: str,
        top_k: int,
    ) -> list[dict]:
        """Vector-only or hybrid retrieval before filtering/reranking."""
        oversample = settings.RETRIEVAL_OVERSAMPLE if settings.RERANKER_ENABLED else 2
        fetch_k = min(top_k * oversample, 20)

        if settings.HYBRID_SEARCH_ENABLED:
            vector_results = await self.vector_service.search(
                knowledge_base_id, query, settings.VECTOR_TOP_K
            )
            keyword_results = await self.keyword_service.search_chunks(
                db, knowledge_base_id, query, settings.KEYWORD_TOP_K
            )
            fused = reciprocal_rank_fusion(
                vector_results,
                keyword_results,
                vector_weight=settings.HYBRID_VECTOR_WEIGHT,
                keyword_weight=settings.HYBRID_KEYWORD_WEIGHT,
            )
            logger.info(
                f"Hybrid search kb={knowledge_base_id}: "
                f"vector={len(vector_results)} keyword={len(keyword_results)} fused={len(fused)}"
            )
            return fused[:fetch_k]

        results = await self.vector_service.search(knowledge_base_id, query, fetch_k)
        logger.info(f"Vector search kb={knowledge_base_id}: retrieved={len(results)}")
        return results

    async def retrieve(
        self, knowledge_base_id: int, query: str, top_k: int = 10, db: AsyncSession | None = None
    ) -> list[dict]:
        """Retrieve with filter + rerank pipeline."""
        if db is None:
            return await self.vector_service.search(knowledge_base_id, query, top_k)

        raw_chunks = await self._retrieve_raw(db, knowledge_base_id, query, top_k)
        valid_chunks = await self._filter_valid_chunks(db, raw_chunks)
        rerank_top = settings.RERANKER_TOP_N if settings.RERANKER_ENABLED else top_k
        reranked = await self.reranker.rerank(query, valid_chunks, top_n=rerank_top)
        logger.info(
            f"Retrieval pipeline kb={knowledge_base_id}: "
            f"raw_retrieved_count={len(raw_chunks)} valid_count={len(valid_chunks)} "
            f"reranked_count={len(reranked)}"
        )
        return reranked[:top_k]

    async def retrieve_with_stats(
        self,
        db: AsyncSession,
        knowledge_base_id: int,
        query: str,
        top_k: int = 5,
    ) -> dict:
        """Run retrieval pipeline and return debug stats for quality checks."""
        mode = _retrieval_mode()
        try:
            raw_chunks = await self._retrieve_raw(db, knowledge_base_id, query, top_k)
        except AppError:
            raise
        except Exception as e:
            logger.exception("Retrieval failed")
            raise

        record_rag_retrieval()

        valid_chunks = await self._filter_valid_chunks(db, raw_chunks)
        rerank_n = settings.RERANKER_TOP_N if settings.RERANKER_ENABLED else top_k
        try:
            reranked = await self.reranker.rerank(query, valid_chunks, top_n=rerank_n)
        except Exception as e:
            logger.warning(f"Rerank failed (non-fatal): {e}")
            reranked = valid_chunks[:top_k]

        final_chunks = _dedupe_chunks(reranked[:top_k])
        references = _chunks_to_references(final_chunks)

        logger.info(
            f"Retrieval stats kb={knowledge_base_id} mode={mode} "
            f"raw_retrieved_count={len(raw_chunks)} valid_count={len(valid_chunks)} "
            f"reranked_count={len(reranked)}"
        )

        return {
            "query": query,
            "mode": mode,
            "raw_count": len(raw_chunks),
            "valid_count": len(valid_chunks),
            "reranked_count": len(reranked),
            "references": references,
            "chunks": final_chunks,
        }

    async def _filter_valid_chunks(
        self, db: AsyncSession, chunks: list[dict]
    ) -> list[dict]:
        """Filter chunks: only keep those from COMPLETED documents.

        Also skips chunks with obviously low-quality metadata (e.g. empty filenames
        that look like noise, or section_titles that look like shell commands).
        """
        if not chunks:
            return []

        # Collect unique document_ids from chunks
        doc_ids = set()
        for c in chunks:
            meta = c.get("metadata", {})
            did = meta.get("document_id")
            if did is not None:
                doc_ids.add(int(did))

        if not doc_ids:
            return chunks  # No doc_id in metadata, can't filter — pass through

        # Batch query document statuses
        result = await db.execute(
            select(Document.id, Document.status).where(
                Document.id.in_(list(doc_ids))
            )
        )
        doc_status = {row[0]: row[1] for row in result.all()}

        # Filter: keep only COMPLETED
        valid = []
        filtered_count = 0
        for c in chunks:
            meta = c.get("metadata", {})
            did = meta.get("document_id")
            if did is not None:
                sid = int(did)
                st = doc_status.get(sid)
                if st is not None:
                    # Convert enum to string for comparison
                    st_val = st.value if hasattr(st, 'value') else str(st)
                    if st_val != "completed":
                        filtered_count += 1
                        continue
            valid.append(c)

        if filtered_count:
            logger.info(f"Filtered out {filtered_count} chunks from non-COMPLETED documents")
        return valid

    async def stream_answer(
        self,
        knowledge_base_id: int,
        question: str,
        chat_history: list[dict],
        db: AsyncSession,
        top_k: int = 5,
        user_id: int | None = None,
    ) -> AsyncGenerator[dict, None]:
        """Full RAG pipeline: retrieve → filter → build prompt → stream answer.

        Args:
            knowledge_base_id: KB to search in
            question: User's question
            chat_history: Recent messages for context
            db: Database session for document status verification
            top_k: Number of chunks to pass to LLM (default 5)
            user_id: Current user — used for RAG cache key scoping

        Yields SSE event dicts.
        """
        logger.info(f"RAG stream: kb={knowledge_base_id}, question={question[:50]}...")

        lang = "en" if _is_mostly_english(question) else "zh"
        cache_key: str | None = None
        cache_service: CacheService | None = None

        if settings.RAG_CACHE_ENABLED and user_id is not None:
            cache_key = build_rag_cache_key(knowledge_base_id, user_id, question, lang)
            cache_hit = False
            try:
                cache_service = CacheService(get_redis())
                cached = await cache_service.get_rag_result(cache_key)
                if cached and cached.get("answer") and cached.get("references") is not None:
                    cache_hit = True
                    record_rag_cache_hit()
                    logger.info(
                        "rag_cache_hit kb=%s user=%s key=%s",
                        knowledge_base_id,
                        user_id,
                        cache_key,
                    )
                    yield {"event": "retrieval_start", "data": {}}
                    yield {
                        "event": "retrieval_done",
                        "data": {"count": cached.get("chunk_count", len(cached.get("references", [])))},
                    }
                    yield {"event": "token", "data": {"content": cached["answer"]}}
                    yield {"event": "references", "data": cached["references"]}
                    yield {
                        "event": "done",
                        "data": {
                            "content": cached["answer"],
                            "references": cached["references"],
                            "cached": True,
                        },
                    }
                    return
            except Exception as e:
                logger.warning("RAG cache lookup failed (non-fatal): %s", e)
            if not cache_hit:
                record_rag_cache_miss()
                logger.info(
                    "rag_cache_miss kb=%s user=%s key=%s",
                    knowledge_base_id,
                    user_id,
                    cache_key,
                )

        # Step 1: Retrieve → filter → rerank
        yield {"event": "retrieval_start", "data": {}}

        try:
            raw_chunks = await self._retrieve_raw(db, knowledge_base_id, question, top_k)
        except AppError as e:
            if e.code == ErrorCode.VECTOR_DIMENSION_MISMATCH:
                yield {"event": "error", "data": error_response(ErrorCode.VECTOR_DIMENSION_MISMATCH)}
                return
            raise
        except Exception as e:
            logger.exception("Retrieval failed")
            yield {"event": "error", "data": {"message": "检索失败，请稍后重试。"}}
            return

        record_rag_retrieval()

        try:
            valid_chunks = await self._filter_valid_chunks(db, raw_chunks)
        except Exception as e:
            logger.warning(f"Chunk filtering failed (non-fatal): {e}")
            valid_chunks = raw_chunks

        rerank_n = settings.RERANKER_TOP_N if settings.RERANKER_ENABLED else top_k
        try:
            reranked_chunks = await self.reranker.rerank(question, valid_chunks, top_n=rerank_n)
        except Exception as e:
            logger.warning(f"Rerank failed (non-fatal): {e}")
            reranked_chunks = valid_chunks[:top_k]

        reranked_count = len(reranked_chunks)
        chunks = _dedupe_chunks(reranked_chunks[:top_k])

        logger.info(
            f"RAG pipeline kb={knowledge_base_id}: mode={_retrieval_mode()} "
            f"raw_retrieved_count={len(raw_chunks)} valid_count={len(valid_chunks)} "
            f"reranked_count={reranked_count}"
        )

        if not chunks:
            doc_stats = await _kb_doc_stats(db, knowledge_base_id)
            no_evidence, empty_reason = _empty_retrieval_message(
                lang,
                pending=doc_stats["pending"],
                completed=doc_stats["completed"],
                raw_count=len(raw_chunks),
                valid_count=len(valid_chunks),
            )
            yield {
                "event": "retrieval_done",
                "data": {
                    "count": 0,
                    "mode": _retrieval_mode(),
                    "raw_count": len(raw_chunks),
                    "valid_count": len(valid_chunks),
                    "reranked_count": reranked_count,
                    "empty_reason": empty_reason,
                    "pending_docs": doc_stats["pending"],
                    "completed_docs": doc_stats["completed"],
                },
            }
            yield {"event": "token", "data": {"content": no_evidence}}
            yield {"event": "references", "data": []}
            yield {"event": "done", "data": {"empty_reason": empty_reason}}
            return

        yield {
            "event": "retrieval_done",
            "data": {
                "count": len(chunks),
                "mode": _retrieval_mode(),
                "raw_count": len(raw_chunks),
                "valid_count": len(valid_chunks),
                "reranked_count": reranked_count,
            },
        }

        if not (settings.LLM_API_KEY or "").strip():
            yield {
                "event": "error",
                "data": error_response(
                    ErrorCode.LLM_GENERATION_FAILED,
                    "LLM API key is not configured. Set LLM_API_KEY in environment.",
                ),
            }
            return

        # Step 4: Build prompt
        messages = build_rag_prompt(chunks, chat_history, question)

        # Step 5: Stream LLM response
        full_answer = ""
        try:
            async for token in self.llm_service.stream_chat(messages):
                full_answer += token
                yield {"event": "token", "data": {"content": token}}
        except Exception as e:
            logger.exception("LLM streaming failed")
            yield {"event": "error", "data": {"message": "生成回答失败，请稍后重试。"}}
            return

        # Step 6: Yield references and done
        references = _chunks_to_references(chunks)

        yield {"event": "references", "data": references}
        yield {
            "event": "done",
            "data": {
                "content": full_answer,
                "references": references,
            },
        }

        if cache_key and cache_service and full_answer and references:
            try:
                await cache_service.set_rag_result(
                    cache_key,
                    {
                        "answer": full_answer,
                        "references": references,
                        "chunk_count": len(chunks),
                    },
                )
            except Exception as e:
                logger.warning("RAG cache write failed (non-fatal): %s", e)

    async def save_rag_results(
        self,
        db: AsyncSession,
        session_id: int,
        user_id: int,
        question: str,
        answer: str,
        references: list[dict],
    ) -> tuple[ChatMessage, ChatMessage]:
        """Save the user question, assistant answer, and RAG references to DB.

        Returns (user_message, assistant_message).
        """
        # Save user message
        user_msg = ChatMessage(
            session_id=session_id,
            user_id=user_id,
            role=MessageRole.USER,
            content=question,
        )
        db.add(user_msg)
        await db.flush()

        # Save assistant message
        assistant_msg = ChatMessage(
            session_id=session_id,
            user_id=user_id,
            role=MessageRole.ASSISTANT,
            content=answer,
        )
        db.add(assistant_msg)
        await db.flush()

        # Save RAG references
        for ref in references:
            rag_ref = RagReference(
                message_id=assistant_msg.id,
                document_id=ref.get("document_id"),
                chunk_id=ref.get("chunk_id"),
                source_filename=ref.get("source_filename"),
                page_number=ref.get("page_number"),
                section_title=ref.get("section_title"),
                content_preview=ref.get("content_preview"),
                score=ref.get("score"),
            )
            db.add(rag_ref)

        await db.commit()
        logger.info(f"Saved RAG results: session={session_id}, answer_len={len(answer)}, refs={len(references)}")

        return user_msg, assistant_msg
