"""
Cleanup script: remove FAILED test documents, their chunks, and ChromaDB vectors.

Usage (inside backend container):
    python scripts/cleanup_test_data.py

Or via docker:
    docker compose exec backend python scripts/cleanup_test_data.py

Safe: only deletes documents with status='failed'.
"""

import asyncio
import logging
import os
import sys

# Ensure backend package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, delete
from app.core.database import async_session
from app.models import Document, DocumentChunk, DocumentStatus
from app.services.vector_service import VectorServiceFactory

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def cleanup_failed_documents():
    """Delete all FAILED documents, their chunks, and ChromaDB vectors."""
    async with async_session() as db:
        # Find failed documents
        result = await db.execute(
            select(Document).where(Document.status == DocumentStatus.FAILED)
        )
        failed_docs = result.scalars().all()

        if not failed_docs:
            logger.info("No FAILED documents found. Nothing to clean up.")
            return

        logger.info(f"Found {len(failed_docs)} FAILED document(s):")

        vector_service = VectorServiceFactory.get_service()

        for doc in failed_docs:
            logger.info(
                f"  doc_id={doc.id}  file={doc.original_filename}  "
                f"error={doc.error_message[:80] if doc.error_message else 'N/A'}"
            )

            # Delete vectors from ChromaDB
            try:
                await vector_service.delete_document_vectors(
                    doc.knowledge_base_id, doc.id
                )
                logger.info(f"    → Deleted vectors from ChromaDB")
            except Exception as e:
                logger.warning(f"    → Failed to delete vectors: {e}")

            # Delete chunks
            chunk_result = await db.execute(
                delete(DocumentChunk).where(DocumentChunk.document_id == doc.id)
            )
            logger.info(f"    → Deleted {chunk_result.rowcount} chunk(s) from DB")

            # Delete file on disk
            if os.path.exists(doc.file_path):
                os.remove(doc.file_path)
                logger.info(f"    → Deleted file: {doc.file_path}")

            # Delete document record
            await db.delete(doc)
            logger.info(f"    → Deleted document record")

        await db.commit()
        logger.info(f"\nCleanup complete: removed {len(failed_docs)} failed document(s).")


async def show_status():
    """Show current document status summary."""
    async with async_session() as db:
        from sqlalchemy import func

        result = await db.execute(
            select(Document.status, func.count(Document.id))
            .group_by(Document.status)
        )
        logger.info("Current document status summary:")
        for status, count in result.all():
            st_val = status.value if hasattr(status, 'value') else str(status)
            logger.info(f"  {st_val}: {count}")


async def main():
    logger.info("=" * 60)
    logger.info("KnowFlow AI — Test Data Cleanup")
    logger.info("=" * 60)
    await show_status()
    print()
    await cleanup_failed_documents()
    print()
    await show_status()


if __name__ == "__main__":
    asyncio.run(main())
