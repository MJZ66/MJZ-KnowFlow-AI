"""
Document processing worker.
Handles the full pipeline: parse → chunk → embed.
Runs as a FastAPI BackgroundTask.
"""

import asyncio
import json
import logging
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import async_session
from app.core.errors import AppError
from app.core.metrics import record_document_failure, record_document_success
from app.models import BackgroundTask, Document, DocumentChunk, DocumentStatus, TaskStatus

settings = get_settings()

logger = logging.getLogger(__name__)


async def process_document_by_id(document_id: int, task_id: int):
    """Main document processing pipeline.

    Steps:
    1. Parse document → extract text with structure
    2. Chunk text → split into semantic segments
    3. Embed chunks → vectorize via DeepSeek API
    """
    started = time.perf_counter()
    async with async_session() as db:
        try:
            # Load document and task
            doc = await _get_document(db, document_id)
            task = await _get_task(db, task_id)

            # Step 1: Parse
            await _update_status(db, doc, task, DocumentStatus.PARSING, 10)
            parsed = await _parse_document(doc.file_path, doc.file_type)

            # Step 2: Chunk
            await _update_status(db, doc, task, DocumentStatus.CHUNKING, 30)
            chunks = await _chunk_text(parsed, doc)

            # Save chunks to DB
            for i, chunk_data in enumerate(chunks):
                chunk = DocumentChunk(
                    document_id=doc.id,
                    knowledge_base_id=doc.knowledge_base_id,
                    chunk_index=i,
                    content=chunk_data["content"],
                    token_count=chunk_data.get("token_count", 0),
                    page_number=chunk_data.get("page_number"),
                    section_title=chunk_data.get("section_title"),
                    metadata_json=json.dumps({
                        "document_id": doc.id,
                        "knowledge_base_id": doc.knowledge_base_id,
                        "filename": doc.original_filename,
                        "page_number": chunk_data.get("page_number"),
                        "section_title": chunk_data.get("section_title"),
                        "chunk_index": i,
                    }, ensure_ascii=False),
                )
                db.add(chunk)

            progress = 60
            await _update_status(db, doc, task, DocumentStatus.EMBEDDING, progress)

            # Step 3: Embed — call vector service
            await _embed_chunks(db, doc, doc.knowledge_base_id)

            # Done — clear any stale error messages from previous runs
            await _update_status(db, doc, task, DocumentStatus.COMPLETED, 100)
            doc.error_message = None
            task.error_message = None
            await db.commit()
            from app.services.cache_invalidation import invalidate_kb_rag_cache
            await invalidate_kb_rag_cache(doc.knowledge_base_id)
            logger.info(f"Document {document_id} processed successfully: {len(chunks)} chunks")
            record_document_success(time.perf_counter() - started)

        except Exception as e:
            logger.exception(f"Document processing failed for document {document_id}")
            record_document_failure(time.perf_counter() - started)
            async with async_session() as err_db:
                doc = await _get_document(err_db, document_id)
                task = await _get_task(err_db, task_id)
                if doc:
                    doc.status = DocumentStatus.FAILED
                    doc.error_message = str(e)
                if task:
                    task.status = TaskStatus.FAILED
                    task.error_message = str(e)
                await err_db.commit()


async def _get_document(db: AsyncSession, document_id: int) -> Document:
    result = await db.execute(select(Document).where(Document.id == document_id))
    return result.scalar_one()


async def _get_task(db: AsyncSession, task_id: int) -> BackgroundTask:
    result = await db.execute(select(BackgroundTask).where(BackgroundTask.id == task_id))
    return result.scalar_one()


async def _update_status(
    db: AsyncSession,
    doc: Document,
    task: BackgroundTask,
    status: DocumentStatus,
    progress: int,
):
    doc.status = status
    task.progress = progress

    # Sync task status with document status for terminal states
    if status == DocumentStatus.COMPLETED:
        task.status = TaskStatus.COMPLETED
    elif status == DocumentStatus.FAILED:
        task.status = TaskStatus.FAILED
    else:
        task.status = TaskStatus.RUNNING

    await db.commit()


# ============================================
# Parsing (full implementation in step 4)
# ============================================

async def _parse_document(file_path: str, file_type: str) -> list[dict]:
    """Parse a document file and return list of text segments with metadata.

    Each segment: {"content": str, "page_number": int|None, "section_title": str|None}
    """
    # Delegate to document parser — full implementation in step 4
    from app.workers.document_parser import parse_file
    return await asyncio.to_thread(parse_file, file_path, file_type)


# ============================================
# Chunking (full implementation in step 4)
# ============================================

async def _chunk_text(parsed: list[dict], doc: Document) -> list[dict]:
    """Split parsed text segments into chunks suitable for embedding."""
    from app.workers.document_chunker import chunk_segments
    return chunk_segments(parsed)


# ============================================
# Embedding (full implementation in step 4)
# ============================================

async def _embed_chunks(db: AsyncSession, doc: Document, kb_id: int):
    """Vectorize chunks via the configured vector service."""
    from app.services.vector_service import VectorServiceFactory

    # Load saved chunks
    result = await db.execute(
        select(DocumentChunk).where(
            DocumentChunk.document_id == doc.id,
            DocumentChunk.knowledge_base_id == kb_id,
        ).order_by(DocumentChunk.chunk_index)
    )
    chunks = result.scalars().all()

    if not chunks:
        logger.warning(f"No chunks found for document {doc.id}")
        return

    # Prepare chunk data for vector service
    chunk_dicts = []
    for chunk in chunks:
        metadata = {}
        if chunk.metadata_json:
            try:
                metadata = json.loads(chunk.metadata_json)
            except json.JSONDecodeError:
                pass

        chunk_dicts.append({
            "content": chunk.content,
            "document_id": doc.id,
            "metadata": {
                "document_id": doc.id,
                "knowledge_base_id": kb_id,
                "filename": doc.original_filename,
                "page_number": chunk.page_number,
                "section_title": chunk.section_title,
                "chunk_index": chunk.chunk_index,
            },
        })

    # Send to vector service
    vector_service = VectorServiceFactory.get_service()
    embedding_meta = vector_service.embedding_service.metadata_fields()
    try:
        vector_ids = await vector_service.add_chunks(kb_id, chunk_dicts)
    except AppError as e:
        if e.code == ErrorCode.VECTOR_DIMENSION_MISMATCH:
            raise RuntimeError(e.detail) from e
        raise

    # Save external vector IDs back to chunks
    for chunk, vector_id in zip(chunks, vector_ids):
        chunk.external_vector_id = vector_id
        chunk.vector_provider = settings.VECTOR_PROVIDER
        if chunk.metadata_json:
            try:
                meta = json.loads(chunk.metadata_json)
            except json.JSONDecodeError:
                meta = {}
        else:
            meta = {}
        meta.update(embedding_meta)
        chunk.metadata_json = json.dumps(meta, ensure_ascii=False)

    await db.commit()
    logger.info(f"Embedded {len(chunks)} chunks for document {doc.id}, kb {kb_id}")


# Backward-compatible alias for FastAPI BackgroundTasks
process_document = process_document_by_id
