"""Central registry of supported upload file types and preview behavior."""

from __future__ import annotations

# Text extracted into chunks for RAG + text preview
TEXT_EXTRACTABLE_TYPES: frozenset[str] = frozenset({
    "pdf", "docx", "md", "txt", "xlsx", "xls",
})

# Visual preview via original file download (also get minimal text for RAG)
IMAGE_TYPES: frozenset[str] = frozenset({
    "png", "jpg", "jpeg", "webp", "gif", "bmp",
})

DEFAULT_ALLOWED_EXTENSIONS: frozenset[str] = TEXT_EXTRACTABLE_TYPES | IMAGE_TYPES

CONTENT_TYPES: dict[str, str] = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "md": "text/markdown; charset=utf-8",
    "txt": "text/plain; charset=utf-8",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xls": "application/vnd.ms-excel",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "gif": "image/gif",
    "bmp": "image/bmp",
}


def preview_kind(file_type: str) -> str:
    """Return preview mode: image, pdf, or text (chunk-based)."""
    ext = file_type.lower()
    if ext in IMAGE_TYPES:
        return "image"
    if ext == "pdf":
        return "pdf"
    return "text"


def content_type_for(file_type: str) -> str:
    return CONTENT_TYPES.get(file_type.lower(), "application/octet-stream")


def human_labels_zh() -> str:
    return "PDF、Word(DOCX)、Excel(XLS/XLSX)、Markdown、TXT、图片(PNG/JPG/WEBP/GIF/BMP)"
