"""
Upload file validation: extension, size, MIME sniffing, filename sanitization.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings
from app.core.errors import ErrorCode, error_response

def _settings():
    return get_settings()

from app.services.file_types import (
    IMAGE_TYPES,
    TEXT_EXTRACTABLE_TYPES,
)

EXTENSION_MIME: dict[str, set[str]] = {
    "pdf": {
        "application/pdf",
        "application/x-pdf",
        "application/vnd.pdf",
        "application/octet-stream",
        "binary/octet-stream",
    },
    "docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
        "application/octet-stream",
        "binary/octet-stream",
    },
    "xlsx": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/zip",
        "application/octet-stream",
        "binary/octet-stream",
    },
    "xls": {
        "application/vnd.ms-excel",
        "application/vnd.ms-office",
        "application/octet-stream",
        "binary/octet-stream",
    },
    "md": {"text/markdown", "text/plain", "application/octet-stream", "binary/octet-stream"},
    "txt": {"text/plain", "application/octet-stream", "binary/octet-stream"},
    "png": {"image/png", "application/octet-stream", "binary/octet-stream"},
    "jpg": {"image/jpeg", "application/octet-stream", "binary/octet-stream"},
    "jpeg": {"image/jpeg", "application/octet-stream", "binary/octet-stream"},
    "webp": {"image/webp", "application/octet-stream", "binary/octet-stream"},
    "gif": {"image/gif", "application/octet-stream", "binary/octet-stream"},
    "bmp": {"image/bmp", "image/x-ms-bmp", "application/octet-stream", "binary/octet-stream"},
}

ZIP_SIGNATURE = b"PK\x03\x04"
OLE_SIGNATURE = b"\xd0\xcf\x11\xe0"

# Some PDF generators prepend whitespace/BOM before %PDF
_PDF_SCAN_BYTES = 8192


def sanitize_filename(filename: str) -> str:
    """Strip paths, dangerous chars, and limit length."""
    name = filename.replace("\\", "/")
    name = PurePosixPath(name).name
    name = name.strip().strip(".")
    if not name:
        name = "upload"

    name = re.sub(r'[<>:"|?*\x00-\x1f]', "_", name)
    if len(name) > _settings().MAX_FILENAME_LENGTH:
        max_len = _settings().MAX_FILENAME_LENGTH
        base, dot, ext = name.rpartition(".")
        if dot and len(ext) < 10:
            keep = max_len - len(ext) - 1
            name = f"{base[:keep]}.{ext}"
        else:
            name = name[:max_len]
    return name


def _has_pdf_signature(content: bytes) -> bool:
    return b"%PDF" in content[:_PDF_SCAN_BYTES]


def _detect_image_type(content: bytes) -> str | None:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if content[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if content[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "webp"
    if content.startswith(b"BM"):
        return "bmp"
    return None


def _detect_extension_from_magic(content: bytes) -> str | None:
    if _has_pdf_signature(content):
        return "pdf"
    image = _detect_image_type(content)
    if image:
        return image
    if content.startswith(OLE_SIGNATURE):
        return "xls"
    if content.startswith(ZIP_SIGNATURE):
        return "zip"
    return None


def _validate_magic(ext: str, content: bytes) -> None:
    if ext == "pdf" and not _has_pdf_signature(content):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response(ErrorCode.UNSUPPORTED_FILE_TYPE),
        )
    if ext == "docx" and not content.startswith(ZIP_SIGNATURE):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response(ErrorCode.UNSUPPORTED_FILE_TYPE),
        )
    if ext == "xlsx" and not content.startswith(ZIP_SIGNATURE):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response(ErrorCode.UNSUPPORTED_FILE_TYPE),
        )
    if ext == "xls" and not content.startswith(OLE_SIGNATURE):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response(ErrorCode.UNSUPPORTED_FILE_TYPE),
        )
    if ext in IMAGE_TYPES:
        detected = _detect_image_type(content)
        if detected is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_response(ErrorCode.UNSUPPORTED_FILE_TYPE),
            )
        if ext in ("jpg", "jpeg") and detected != "jpeg":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_response(ErrorCode.UNSUPPORTED_FILE_TYPE),
            )
        if ext not in ("jpg", "jpeg") and detected != ext:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_response(ErrorCode.UNSUPPORTED_FILE_TYPE),
            )


async def validate_upload_file(file: UploadFile) -> tuple[str, bytes, str]:
    """Validate and return (extension, content, safe_filename)."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response(ErrorCode.UNSUPPORTED_FILE_TYPE),
        )

    safe_name = sanitize_filename(file.filename)
    if ".." in safe_name or safe_name.startswith("/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response(ErrorCode.UNSUPPORTED_FILE_TYPE),
        )

    ext = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""

    content = await file.read()
    size = len(content)

    if size > _settings().max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=error_response(ErrorCode.FILE_TOO_LARGE),
        )

    if size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response(ErrorCode.DOCUMENT_EMPTY_CONTENT),
        )

    magic_ext = _detect_extension_from_magic(content)

    if magic_ext == "pdf" and ext != "pdf":
        if ext in ("md", "txt"):
            ext = "pdf"
            if not safe_name.lower().endswith(".pdf"):
                safe_name = f"{safe_name.rsplit('.', 1)[0]}.pdf" if "." in safe_name else f"{safe_name}.pdf"
        elif ext not in TEXT_EXTRACTABLE_TYPES and ext not in IMAGE_TYPES:
            ext = "pdf"
            safe_name = f"{safe_name.rsplit('.', 1)[0]}.pdf" if "." in safe_name else f"{safe_name}.pdf"

    if magic_ext in ("jpeg", "jpg", "png", "webp", "gif", "bmp") and ext in ("jpg", "jpeg", "png", "webp", "gif", "bmp"):
        if ext in ("jpg", "jpeg") and magic_ext not in ("jpeg", "jpg"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_response(ErrorCode.UNSUPPORTED_FILE_TYPE),
            )
        if ext not in ("jpg", "jpeg") and magic_ext != ext:
            ext = magic_ext

    if ext not in _settings().ALLOWED_EXTENSIONS_SET:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response(ErrorCode.UNSUPPORTED_FILE_TYPE),
        )

    if magic_ext == "zip" and ext in ("docx", "xlsx"):
        pass
    elif magic_ext == "xls" and ext != "xls":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response(ErrorCode.UNSUPPORTED_FILE_TYPE),
        )
    elif magic_ext and magic_ext not in ("zip",) and magic_ext != ext:
        if ext in ("jpg", "jpeg") and magic_ext in ("jpeg", "jpg"):
            pass
        elif ext not in ("md", "txt"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_response(ErrorCode.UNSUPPORTED_FILE_TYPE),
            )

    if ext in ("pdf", "docx", "xlsx", "xls") or ext in IMAGE_TYPES:
        _validate_magic(ext, content)

    declared = (file.content_type or "").split(";")[0].strip().lower()
    magic_ok = (
        (ext == "pdf" and _has_pdf_signature(content))
        or (ext in ("docx", "xlsx") and content.startswith(ZIP_SIGNATURE))
        or (ext == "xls" and content.startswith(OLE_SIGNATURE))
        or (ext in IMAGE_TYPES and _detect_image_type(content) is not None)
    )
    if declared and declared != "application/octet-stream" and not magic_ok:
        allowed = EXTENSION_MIME.get(ext, set())
        if allowed and declared not in allowed:
            if ext not in ("md", "txt") or declared not in ("text/plain", "text/markdown"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_response(ErrorCode.UNSUPPORTED_FILE_TYPE),
                )

    await file.seek(0)
    return ext, content, safe_name
