"""
Text chunking strategy:
- Preserves section/title/paragraph boundaries where possible
- Falls back to token-based splitting for long segments
- Chunk size: 800-1200 tokens (approximate)
- Overlap: 100-200 tokens (approximate)
- Filters low-quality chunks: command lines, paths, very short text
"""

import logging
import re

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Approximate: 1 token ≈ 4 characters for Chinese, ~0.75 words for English
CHARS_PER_TOKEN_ESTIMATE = 2.5

# Patterns for detecting command-line / noise text
_RE_CMD_PREFIX = re.compile(
    r"^\s*(cd|docker|docker compose|docker-compose|psql|curl|wget|npm|pip|python|"
    r"git|ssh|scp|Get-Content|Select-Object|Remove-Item|New-Item|"
    r"Set-|Write-|Copy-Item|Invoke-|Start-|Stop-|"
    r"PS\s|@['\"]|['\"]@|@\{|@\(|"
    r"uvicorn|alembic)",
    re.IGNORECASE,
)
_RE_WIN_PATH = re.compile(r"^[A-Z]:[\\/]", re.IGNORECASE)
_RE_PURE_SYMBOLS = re.compile(r"^[\s\W\d_]+$")
_MIN_CHUNK_LENGTH = 20


def estimate_tokens(text: str) -> int:
    """Rough token count estimation without a heavy tokenizer."""
    return max(1, int(len(text) / CHARS_PER_TOKEN_ESTIMATE))


def should_keep_chunk(text: str) -> bool:
    """Check if a chunk contains meaningful content worth indexing.

    Filters out:
    - Very short text (< 20 meaningful characters)
    - Shell/PowerShell/CLI commands
    - Windows file paths as the main content
    - Pure symbol/garbage text
    """
    stripped = text.strip()
    if not stripped:
        return False

    # Too short
    meaningful = re.sub(r"\s+", "", stripped)
    if len(meaningful) < _MIN_CHUNK_LENGTH:
        return False

    # Pure symbols / numbers only
    if _RE_PURE_SYMBOLS.match(meaningful):
        return False

    # Looks like a shell command or PowerShell snippet
    if _RE_CMD_PREFIX.match(stripped):
        return False

    # Main content is just a Windows path
    if _RE_WIN_PATH.match(stripped) and len(stripped) < 200:
        return False

    return True


def chunk_segments(segments: list[dict]) -> list[dict]:
    """Split parsed segments into embedding-size chunks.

    Strategy:
    1. If a segment fits within max chunk size, keep it as one chunk
    2. If too large, split by paragraph boundaries first, then by sentence
    3. Apply overlap between chunks

    Args:
        segments: List from document_parser.parse_file()

    Returns:
        List of chunk dicts: {"content", "page_number", "section_title", "token_count"}
    """
    chunk_size = settings.CHUNK_SIZE
    chunk_overlap = settings.CHUNK_OVERLAP

    chunks = []

    for seg in segments:
        text = seg["content"]
        tokens = estimate_tokens(text)

        if tokens <= chunk_size:
            # Segment fits in one chunk
            chunks.append({
                "content": text,
                "page_number": seg.get("page_number"),
                "section_title": seg.get("section_title"),
                "token_count": tokens,
            })
        else:
            # Split long segment
            sub_chunks = _split_long_text(
                text,
                chunk_size=chunk_size,
                overlap=chunk_overlap,
            )
            for sc in sub_chunks:
                chunks.append({
                    "content": sc,
                    "page_number": seg.get("page_number"),
                    "section_title": seg.get("section_title"),
                    "token_count": estimate_tokens(sc),
                })

    # Filter low-quality chunks
    kept = []
    dropped = 0
    for c in chunks:
        if should_keep_chunk(c["content"]):
            kept.append(c)
        else:
            dropped += 1

    if dropped:
        logger.info(f"Dropped {dropped} low-quality chunks out of {len(chunks)}")
    logger.info(f"Chunked {len(segments)} segments into {len(kept)} chunks")
    return kept


def _split_long_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split a long text into overlapping chunks.

    Tries paragraph boundaries first, then sentence boundaries, then character window.
    """
    # Try splitting by paragraphs first
    paragraphs = re.split(r"\n\s*\n", text)

    if len(paragraphs) == 1:
        # Single paragraph — split by sentences
        return _split_by_sentences(text, chunk_size, overlap)

    # Greedy paragraph packing
    chunks = []
    current = ""
    current_tokens = 0

    for para in paragraphs:
        para_tokens = estimate_tokens(para)

        if current_tokens + para_tokens <= chunk_size:
            if current:
                current += "\n\n" + para
            else:
                current = para
            current_tokens = estimate_tokens(current)
        else:
            if current:
                chunks.append(current)

            if para_tokens > chunk_size:
                # Paragraph itself is too large — split by sentences
                sub_chunks = _split_by_sentences(para, chunk_size, overlap)
                chunks.extend(sub_chunks)
                current = ""
                current_tokens = 0
            else:
                current = para
                current_tokens = para_tokens

    if current:
        chunks.append(current)

    # Apply overlap: prepend last few chars of previous chunk to next chunk
    if len(chunks) > 1 and overlap > 0:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            prev = chunks[i - 1]
            overlap_chars = min(len(prev), int(overlap * CHARS_PER_TOKEN_ESTIMATE))
            prefix = prev[-overlap_chars:] if overlap_chars > 0 else ""
            overlapped.append(prefix + "\n" + chunks[i] if prefix else chunks[i])
        chunks = overlapped

    return chunks


def _split_by_sentences(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text by sentence boundaries into chunk-sized pieces."""
    # Sentence-aware splitting
    sentences = re.split(r"(?<=[.!?。！？])\s+", text)

    if len(sentences) <= 1:
        # Fallback: character window
        return _split_by_char_window(text, chunk_size, overlap)

    chunks = []
    current = ""
    current_tokens = 0

    for sent in sentences:
        sent_tokens = estimate_tokens(sent)

        if current_tokens + sent_tokens <= chunk_size:
            current = (current + " " + sent).strip() if current else sent
            current_tokens = estimate_tokens(current)
        else:
            if current:
                chunks.append(current)

            if sent_tokens > chunk_size:
                # Sentence too long — force split by character window
                sub_chunks = _split_by_char_window(sent, chunk_size, overlap)
                chunks.extend(sub_chunks)
                current = ""
                current_tokens = 0
            else:
                current = sent
                current_tokens = sent_tokens

    if current:
        chunks.append(current)

    return chunks


def _split_by_char_window(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Last-resort split: character window with overlap."""
    chunk_chars = int(chunk_size * CHARS_PER_TOKEN_ESTIMATE)
    overlap_chars = int(overlap * CHARS_PER_TOKEN_ESTIMATE)
    step = max(1, chunk_chars - overlap_chars)

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_chars, len(text))
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start += step
    return chunks
