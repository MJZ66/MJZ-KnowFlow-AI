"""Image OCR via Tesseract (optional)."""

from __future__ import annotations

import logging
import shutil
from functools import lru_cache

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def ocr_available() -> bool:
    if shutil.which("tesseract") is None:
        return False
    try:
        import pytesseract  # noqa: F401

        return True
    except ImportError:
        return False


def extract_text_from_image(file_path: str) -> str | None:
    """Run OCR on an image file. Returns None when disabled or unavailable."""
    settings = get_settings()
    if not settings.OCR_ENABLED:
        return None
    if not ocr_available():
        logger.warning("OCR enabled but tesseract/pytesseract unavailable")
        return None

    import pytesseract
    from PIL import Image

    try:
        with Image.open(file_path) as img:
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            text = pytesseract.image_to_string(img, lang=settings.OCR_LANGUAGES)
            cleaned = text.strip()
            return cleaned or None
    except Exception as exc:
        logger.warning("OCR failed for %s: %s", file_path, exc)
        return None
