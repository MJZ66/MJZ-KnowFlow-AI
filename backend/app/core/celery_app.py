"""
Celery application — broker and result backend use Redis.
"""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    imports=("app.tasks.document_tasks",),
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    task_soft_time_limit=max(60, settings.CELERY_TASK_TIME_LIMIT - 60),
    worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,
)

# Import task modules so worker registers tasks
import app.tasks.document_tasks  # noqa: F401

from celery.signals import worker_ready


@worker_ready.connect
def _on_worker_ready(**_kwargs):
    """Mark worker alive in Redis for /api/health/ready."""
    import asyncio
    from app.core.health import touch_celery_heartbeat

    try:
        asyncio.run(touch_celery_heartbeat())
    except Exception:
        pass
