"""
Document API routes:
- POST   /api/kbs/{kb_id}/documents/upload     — Upload document
- GET    /api/kbs/{kb_id}/documents            — List documents
- GET    /api/kbs/{kb_id}/documents/{doc_id}   — Document detail
- DELETE /api/kbs/{kb_id}/documents/{doc_id}   — Delete document
- GET    /api/documents/{doc_id}/status        — Document processing status
- GET    /api/documents/{document_id}/chunks   — Document chunks for preview
- GET    /api/documents/{document_id}/chunks/{chunk_id} — Single chunk
"""

import json
import os
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import KBAccessLevel, require_kb_access
from app.core.config import get_settings
from app.core.paths import resolve_upload_path
from app.models import Document, DocumentChunk, DocumentStatus, User, BackgroundTask, TaskStatus
from app.schemas.document import (
    DocumentResponse,
    DocumentStatusResponse,
    DocumentChunksResponse,
    ChunkPreviewItem,
    PaginatedDocumentList,
)
from app.services.file_validation import validate_upload_file
from app.services.file_types import content_type_for, preview_kind
from app.services.cache_invalidation import invalidate_kb_rag_cache
from app.services.vector_service import VectorServiceFactory

router = APIRouter(tags=["Documents"])
settings = get_settings()


def _save_upload_content(kb_id: int, filename: str, content: bytes) -> tuple[str, int]:
    upload_dir = Path(settings.UPLOAD_DIR) / str(kb_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    import uuid

    unique_name = f"{uuid.uuid4().hex}_{filename}"
    file_path = str(upload_dir / unique_name)
    with open(file_path, "wb") as f:
        f.write(content)
    return file_path, len(content)


@router.post("/api/kbs/{kb_id}/documents/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    kb_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    file: UploadFile = File(...),
):
    """Upload a document to a knowledge base. Triggers background processing."""
    kb = await require_kb_access(db, kb_id, current_user, KBAccessLevel.EDITOR)

    ext, content, safe_name = await validate_upload_file(file)

    # Check document count limit
    count_result = await db.execute(
        select(func.count()).select_from(Document).where(
            Document.knowledge_base_id == kb_id
        )
    )
    doc_count = count_result.scalar()
    if doc_count >= settings.MAX_DOCS_PER_KB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {settings.MAX_DOCS_PER_KB} documents per knowledge base.",
        )

    file_path, file_size = _save_upload_content(kb_id, safe_name, content)

    document = Document(
        knowledge_base_id=kb_id,
        user_id=current_user.id,
        filename=safe_name,
        original_filename=safe_name,
        file_path=file_path,
        file_type=ext,
        file_size=file_size,
        status=DocumentStatus.UPLOADED,
    )
    db.add(document)
    await db.flush()

    task = BackgroundTask(
        task_type="document_process",
        status=TaskStatus.PENDING,
        related_document_id=document.id,
        user_id=current_user.id,
        progress=0,
    )
    db.add(task)
    await db.flush()

    _schedule_document_processing(document.id, task.id, background_tasks)

    return document


def _schedule_document_processing(
    document_id: int,
    task_id: int,
    background_tasks: BackgroundTasks | None = None,
) -> None:
    """Dispatch document processing via Celery or FastAPI BackgroundTasks."""
    if settings.TASK_BACKEND == "celery":
        from app.tasks.document_tasks import process_document_task

        process_document_task.delay(document_id, task_id)
        return

    if background_tasks is None:
        raise RuntimeError("background_tasks required when TASK_BACKEND=background")

    from app.workers.document_processor import process_document

    background_tasks.add_task(process_document, document_id, task_id)


@router.get("/api/kbs/{kb_id}/documents", response_model=PaginatedDocumentList)
async def list_documents(
    kb_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    q: str | None = Query(default=None, max_length=200),
    status_filter: str | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List documents in a knowledge base with pagination and optional search."""
    await require_kb_access(db, kb_id, current_user, KBAccessLevel.VIEWER)

    filters = [Document.knowledge_base_id == kb_id]
    if q and q.strip():
        filters.append(Document.original_filename.ilike(f"%{q.strip()}%"))
    if status_filter and status_filter.strip():
        try:
            filters.append(Document.status == DocumentStatus(status_filter.strip()))
        except ValueError:
            pass

    total_result = await db.execute(
        select(func.count()).select_from(Document).where(*filters)
    )
    total = total_result.scalar() or 0

    result = await db.execute(
        select(Document)
        .where(*filters)
        .order_by(Document.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    items = result.scalars().all()
    return PaginatedDocumentList(items=items, total=total, skip=skip, limit=limit)


@router.get("/api/kbs/{kb_id}/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    kb_id: int,
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get document details."""
    await require_kb_access(db, kb_id, current_user, KBAccessLevel.VIEWER)

    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.knowledge_base_id == kb_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return doc


@router.delete("/api/kbs/{kb_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    kb_id: int,
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a document and its chunks/vectors."""
    await require_kb_access(db, kb_id, current_user, KBAccessLevel.EDITOR)

    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.knowledge_base_id == kb_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    # Clean up file on disk
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    try:
        vector_service = VectorServiceFactory.get_service()
        await vector_service.delete_document_vectors(kb_id, document_id)
    except Exception:
        pass

    kb_id_for_cache = doc.knowledge_base_id
    await db.delete(doc)
    await db.flush()
    await invalidate_kb_rag_cache(kb_id_for_cache)


@router.get("/api/documents/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the processing status of a document."""
    doc = await _get_document_with_access(db, document_id, current_user)

    task_result = await db.execute(
        select(BackgroundTask)
        .where(BackgroundTask.related_document_id == document_id)
        .order_by(BackgroundTask.created_at.desc())
        .limit(1)
    )
    task = task_result.scalar_one_or_none()

    return DocumentStatusResponse(
        id=doc.id,
        status=doc.status.value if hasattr(doc.status, 'value') else str(doc.status),
        progress=task.progress if task else 0,
        error_message=doc.error_message,
    )


async def _get_document_with_access(
    db: AsyncSession,
    document_id: int,
    current_user: User,
) -> Document:
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    await require_kb_access(db, doc.knowledge_base_id, current_user, KBAccessLevel.VIEWER)
    return doc


def _chunk_to_preview(chunk: DocumentChunk) -> ChunkPreviewItem:
    metadata: dict = {}
    if chunk.metadata_json:
        try:
            metadata = json.loads(chunk.metadata_json)
        except json.JSONDecodeError:
            metadata = {}
    return ChunkPreviewItem(
        id=chunk.id,
        chunk_index=chunk.chunk_index,
        content=chunk.content,
        page_number=chunk.page_number,
        section_title=chunk.section_title,
        metadata=metadata,
    )


@router.get("/api/documents/{document_id}/chunks", response_model=DocumentChunksResponse)
async def list_document_chunks(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List document chunks for preview. Returns status/progress while processing."""
    doc = await _get_document_with_access(db, document_id, current_user)

    status_val = doc.status.value if hasattr(doc.status, "value") else str(doc.status)

    task_result = await db.execute(
        select(BackgroundTask)
        .where(BackgroundTask.related_document_id == document_id)
        .order_by(BackgroundTask.created_at.desc())
        .limit(1)
    )
    task = task_result.scalar_one_or_none()
    progress = task.progress if task else 0

    if status_val != DocumentStatus.COMPLETED.value:
        return DocumentChunksResponse(
            document_id=doc.id,
            filename=doc.original_filename,
            file_type=doc.file_type,
            preview_kind=preview_kind(doc.file_type),
            status=status_val,
            progress=progress,
            error_message=doc.error_message,
            chunks=[],
        )

    result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index.asc())
    )
    chunks = result.scalars().all()

    return DocumentChunksResponse(
        document_id=doc.id,
        filename=doc.original_filename,
        file_type=doc.file_type,
        preview_kind=preview_kind(doc.file_type),
        status=status_val,
        progress=100,
        error_message=doc.error_message,
        chunks=[_chunk_to_preview(c) for c in chunks],
    )


@router.get("/api/documents/{document_id}/file")
async def get_document_file(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download original uploaded file for inline preview (PDF, images)."""
    doc = await _get_document_with_access(db, document_id, current_user)

    file_path = resolve_upload_path(doc.file_path)
    if not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk.")

    media_type = content_type_for(doc.file_type)
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=doc.original_filename,
        headers={"Content-Disposition": f'inline; filename="{doc.original_filename}"'},
    )


@router.get("/api/documents/{document_id}/chunks/{chunk_id}", response_model=ChunkPreviewItem)
async def get_document_chunk(
    document_id: int,
    chunk_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single document chunk for preview."""
    doc = await _get_document_with_access(db, document_id, current_user)

    status_val = doc.status.value if hasattr(doc.status, "value") else str(doc.status)
    if status_val != DocumentStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document is not ready for preview.",
        )

    result = await db.execute(
        select(DocumentChunk).where(
            DocumentChunk.id == chunk_id,
            DocumentChunk.document_id == document_id,
        )
    )
    chunk = result.scalar_one_or_none()
    if not chunk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chunk not found.")
    return _chunk_to_preview(chunk)
