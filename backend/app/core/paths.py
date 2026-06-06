"""Safe path resolution for uploaded files."""

from pathlib import Path

from fastapi import HTTPException, status

from app.core.config import get_settings


def resolve_upload_path(file_path: str) -> Path:
    """Resolve a stored file path and ensure it stays under UPLOAD_DIR."""
    upload_root = Path(get_settings().UPLOAD_DIR).resolve()
    resolved = Path(file_path).resolve()
    try:
        resolved.relative_to(upload_root)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid file path.",
        )
    return resolved
