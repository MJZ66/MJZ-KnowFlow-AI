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

EXTENSION_MIME: dict[str, set[str]] = {
    "pdf": {"application/pdf"},
    "docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
        "application/octet-stream",
    },
    "md": {"text/markdown", "text/plain", "application/octet-stream"},
    "txt": {"text/plain", "application/octet-stream"},
}

MAGIC_SIGNATURES: dict[str, bytes] = {
    "pdf": b"%PDF",
    "docx": b"PK\x03\x04",
}


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


def _detect_extension_from_magic(content: bytes) -> str | None:
    if content.startswith(MAGIC_SIGNATURES["pdf"]):
        return "pdf"
    if content.startswith(MAGIC_SIGNATURES["docx"]):
        return "docx"
    return None


def _validate_magic(ext: str, content: bytes) -> None:
    if ext == "pdf" and not content.startswith(MAGIC_SIGNATURES["pdf"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response(ErrorCode.UNSUPPORTED_FILE_TYPE),
        )
    if ext == "docx" and not content.startswith(MAGIC_SIGNATURES["docx"]):
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
    if ext not in _settings().ALLOWED_EXTENSIONS_SET:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response(ErrorCode.UNSUPPORTED_FILE_TYPE),
        )

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
    if magic_ext and magic_ext != ext and ext not in ("md", "txt"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response(ErrorCode.UNSUPPORTED_FILE_TYPE),
        )

    if ext in ("pdf", "docx"):
        _validate_magic(ext, content)

    declared = (file.content_type or "").split(";")[0].strip().lower()
    if declared and declared != "application/octet-stream":
        allowed = EXTENSION_MIME.get(ext, set())
        if allowed and declared not in allowed:
            if ext not in ("md", "txt") or declared not in ("text/plain", "text/markdown"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_response(ErrorCode.UNSUPPORTED_FILE_TYPE),
                )

    await file.seek(0)
    return ext, content, safe_name
