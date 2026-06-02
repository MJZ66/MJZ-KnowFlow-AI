"""
Health check helpers for liveness/readiness probes.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

CELERY_HEARTBEAT_KEY = "knowflow:celery:worker:heartbeat"


async def check_postgres() -> dict:
    try:
        import psycopg2

        settings = get_settings()
        url = settings.DATABASE_URL_SYNC or settings.DATABASE_URL
        for old, new in [
            ("postgresql+asyncpg://", "postgresql://"),
            ("postgresql+psycopg2://", "postgresql://"),
        ]:
            url = url.replace(old, new)
        conn = psycopg2.connect(url)
        conn.close()
        return {"status": "ok"}
    except Exception as e:
        logger.warning("postgres health check failed: %s", e)
        return {"status": "error", "detail": str(e)}


async def check_redis() -> dict:
    try:
        from app.core.redis import get_redis

        redis = get_redis()
        pong = await redis.ping()
        return {"status": "ok" if pong else "error"}
    except Exception as e:
        logger.warning("redis health check failed: %s", e)
        return {"status": "error", "detail": str(e)}


async def check_chroma() -> dict:
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            url = f"http://{settings.CHROMA_HOST}:{settings.CHROMA_PORT}/api/v1/heartbeat"
            resp = await client.get(url)
            if resp.status_code == 200:
                return {"status": "ok"}
            return {"status": "error", "detail": f"HTTP {resp.status_code}"}
    except Exception as e:
        logger.warning("chroma health check failed: %s", e)
        return {"status": "error", "detail": str(e)}


async def check_celery_worker() -> dict:
    """Check Celery worker heartbeat key in Redis (written by workers)."""
    settings = get_settings()
    if settings.TASK_BACKEND != "celery":
        return {"status": "skipped", "detail": "TASK_BACKEND is not celery"}

    try:
        from app.core.redis import get_redis

        redis = get_redis()
        ts = await redis.get(CELERY_HEARTBEAT_KEY)
        if not ts:
            return {"status": "unknown", "detail": "no heartbeat yet"}
        try:
            beat = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            age = (datetime.now(timezone.utc) - beat).total_seconds()
            if age > 120:
                return {"status": "stale", "detail": f"heartbeat age {int(age)}s"}
        except ValueError:
            pass
        return {"status": "ok", "last_heartbeat": ts}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


async def touch_celery_heartbeat() -> None:
    """Update Redis key used by readiness probe."""
    settings = get_settings()
    if settings.TASK_BACKEND != "celery":
        return
    try:
        from app.core.redis import get_redis

        redis = get_redis()
        await redis.set(
            CELERY_HEARTBEAT_KEY,
            datetime.now(timezone.utc).isoformat(),
            ex=120,
        )
    except Exception as e:
        logger.debug("celery heartbeat update skipped: %s", e)


async def readiness_report() -> dict:
    postgres = await check_postgres()
    redis = await check_redis()
    chroma = await check_chroma()
    celery = await check_celery_worker()

    checks = {
        "postgres": postgres,
        "redis": redis,
        "chromadb": chroma,
        "celery": celery,
    }
    required_ok = all(
        checks[name]["status"] == "ok"
        for name in ("postgres", "redis", "chromadb")
    )
    return {
        "status": "ok" if required_ok else "degraded",
        "checks": checks,
    }
