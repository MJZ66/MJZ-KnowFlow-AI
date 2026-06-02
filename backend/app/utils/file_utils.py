"""
File handling utilities: validation, storage, path management.
"""

import os
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings

settings = get_settings()

ALLOWED_EXTENSIONS = {"pdf", "docx", "md", "txt"}
MAX_FILE_SIZE = settings.MAX_FILE_SIZE_MB * 1024 * 1024  # Convert MB to bytes


def validate_file(file: UploadFile) -> str:
    """Validate uploaded file type and size.

    Returns the file extension (lowercase).

    Raises HTTPException(400) if invalid.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided.",
        )

    # Check extension
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: .{ext}. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    return ext


async def validate_file_size(file: UploadFile) -> int:
    """Read file content and validate size.

    Returns the file size in bytes.
    Raises HTTPException(413) if file exceeds max size.
    """
    content = await file.read()
    size = len(content)

    if size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large: {size / 1024 / 1024:.1f}MB. Maximum: {settings.MAX_FILE_SIZE_MB}MB.",
        )

    # Reset file pointer for subsequent reads
    await file.seek(0)
    return size


def get_upload_path(kb_id: int, filename: str) -> str:
    """Generate a unique storage path for an uploaded file.

    Returns the relative path from UPLOAD_DIR.
    """
    upload_dir = Path(settings.UPLOAD_DIR) / str(kb_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Use UUID to avoid filename collisions
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    return str(upload_dir / unique_name)


async def save_upload_file(file: UploadFile, kb_id: int) -> tuple[str, int]:
    """Save an uploaded file to disk.

    Returns (file_path, file_size).
    """
    content = await file.read()
    file_size = len(content)

    upload_dir = Path(settings.UPLOAD_DIR) / str(kb_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    unique_name = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = str(upload_dir / unique_name)

    with open(file_path, "wb") as f:
        f.write(content)

    return file_path, file_size
