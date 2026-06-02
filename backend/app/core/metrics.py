"""
Prometheus metrics — optional via METRICS_ENABLED.
"""

from __future__ import annotations

import time
from typing import Callable

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

RAG_CACHE_HIT = Counter("rag_cache_hit_total", "RAG cache hits")
RAG_CACHE_MISS = Counter("rag_cache_miss_total", "RAG cache misses")
RAG_RETRIEVAL = Counter("rag_retrieval_total", "RAG retrieval operations")

DOCUMENT_PROCESS_SUCCESS = Counter(
    "document_process_success_total",
    "Documents processed successfully",
)
DOCUMENT_PROCESS_FAILED = Counter(
    "document_process_failed_total",
    "Document processing failures",
)
DOCUMENT_PROCESS_DURATION = Histogram(
    "document_process_duration_seconds",
    "Document processing duration in seconds",
    buckets=(1.0, 5.0, 15.0, 30.0, 60.0, 120.0, 300.0, 600.0),
)

CELERY_TASK_SUCCESS = Counter("celery_task_success_total", "Celery tasks completed")
CELERY_TASK_FAILED = Counter("celery_task_failed_total", "Celery tasks failed")


def record_rag_cache_hit() -> None:
    RAG_CACHE_HIT.inc()


def record_rag_cache_miss() -> None:
    RAG_CACHE_MISS.inc()


def record_rag_retrieval() -> None:
    RAG_RETRIEVAL.inc()


def record_document_success(duration_sec: float) -> None:
    DOCUMENT_PROCESS_SUCCESS.inc()
    DOCUMENT_PROCESS_DURATION.observe(duration_sec)


def record_document_failure(duration_sec: float) -> None:
    DOCUMENT_PROCESS_FAILED.inc()
    DOCUMENT_PROCESS_DURATION.observe(duration_sec)


def record_celery_success() -> None:
    CELERY_TASK_SUCCESS.inc()


def record_celery_failure() -> None:
    CELERY_TASK_FAILED.inc()


def metrics_payload() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST


def _normalize_endpoint(path: str) -> str:
    """Reduce label cardinality by replacing numeric path segments."""
    parts = path.split("/")
    normalized = []
    for part in parts:
        if part.isdigit():
            normalized.append("{id}")
        else:
            normalized.append(part)
    return "/".join(normalized) or "/"


def prometheus_http_middleware(enabled: bool) -> Callable:
    """Starlette-compatible HTTP middleware factory."""

    async def middleware(request, call_next):
        if not enabled:
            return await call_next(request)

        path = request.url.path
        if path == "/api/metrics":
            return await call_next(request)

        route = request.scope.get("route")
        endpoint = route.path if route else _normalize_endpoint(path)
        method = request.method
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        status = str(response.status_code)
        HTTP_REQUESTS.labels(method=method, endpoint=endpoint, status=status).inc()
        HTTP_REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(elapsed)
        return response

    return middleware
