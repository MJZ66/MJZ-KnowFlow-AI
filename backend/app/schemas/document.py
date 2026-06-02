"""Document schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: int
    knowledge_base_id: int
    user_id: Optional[int]
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    status: str
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = dict(from_attributes=True)


class DocumentStatusResponse(BaseModel):
    id: int
    status: str
    progress: int = 0
    error_message: Optional[str] = None


class PaginatedDocumentList(BaseModel):
    items: list[DocumentResponse]
    total: int
    skip: int
    limit: int


class ChunkPreviewItem(BaseModel):
    id: int
    chunk_index: int
    content: str
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    metadata: dict = {}


class DocumentChunksResponse(BaseModel):
    document_id: int
    filename: str
    status: str
    chunks: list[ChunkPreviewItem]
