"""
Celery tasks for document processing.
"""

from __future__ import annotations

import asyncio
import logging

from app.core.celery_app import celery_app
from app.core.database import engine
from app.core.health import touch_celery_heartbeat
from app.core.metrics import record_celery_failure, record_celery_success
from app.workers.document_processor import process_document_by_id

logger = logging.getLogger(__name__)


async def _run_document_task(document_id: int, task_id: int) -> None:
    """Dispose pooled DB connections before running in a fresh event loop."""
    await engine.dispose()
    await process_document_by_id(document_id, task_id)
    await touch_celery_heartbeat()


@celery_app.task(bind=True, max_retries=3)
def process_document_task(self, document_id: int, task_id: int):
    """Run the async document pipeline inside a Celery worker."""
    try:
        asyncio.run(_run_document_task(document_id, task_id))
        record_celery_success()
    except Exception as exc:
        record_celery_failure()
        logger.exception(
            "Document task failed document_id=%s task_id=%s retry=%s",
            document_id,
            task_id,
            self.request.retries,
        )
        raise self.retry(exc=exc, countdown=60)
