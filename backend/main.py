"""
KnowFlow AI — FastAPI Application Entry Point.

Run with:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.auth import router as auth_router
from app.core.errors import AppError, error_response, from_http_detail, ErrorCode
from app.core.redis import close_redis
from app.api.kb import router as kb_router
from app.api.documents import router as documents_router
from app.api.tasks import router as tasks_router
from app.api.chat import router as chat_router
from app.api.admin import router as admin_router
from app.core.config import get_settings, validate_production_settings
from app.core.health import readiness_report
from app.core.metrics import metrics_payload, prometheus_http_middleware

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    validate_production_settings(settings)
    yield
    await close_redis()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="AI-powered private knowledge base platform with RAG Q&A.",
    lifespan=lifespan,
)

# ============================================
# Standardized error handlers
# ============================================

@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError):
    return JSONResponse(
        status_code=400,
        content=error_response(exc.code, exc.detail),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=from_http_detail(exc.detail),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(x) for x in first.get("loc", []))
    msg = first.get("msg", "Validation error")
    detail = f"{field}: {msg}" if field else msg
    return JSONResponse(
        status_code=422,
        content=error_response(ErrorCode.VALIDATION_ERROR, detail),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=error_response(ErrorCode.INTERNAL_ERROR),
    )


if settings.METRICS_ENABLED:
    app.add_middleware(
        BaseHTTPMiddleware,
        dispatch=prometheus_http_middleware(True),
    )

# CORS — configurable via ALLOWED_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS_LIST,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# Register API routers
# ============================================
app.include_router(auth_router)
app.include_router(kb_router)
app.include_router(documents_router)
app.include_router(tasks_router)
app.include_router(chat_router)
app.include_router(admin_router)


@app.get("/api/health")
async def health_check():
    """Basic health — always returns 200 if process is up."""
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "env": settings.APP_ENV,
    }


@app.get("/api/health/live")
async def liveness():
    """Kubernetes liveness probe."""
    return {"status": "alive"}


@app.get("/api/health/ready")
async def readiness():
    """Kubernetes readiness probe — checks dependencies."""
    report = await readiness_report()
    status_code = 200 if report["status"] == "ok" else 503
    return JSONResponse(status_code=status_code, content=report)


@app.get("/api/metrics")
async def prometheus_metrics():
    """Prometheus scrape endpoint (text/plain)."""
    if not settings.METRICS_ENABLED:
        raise HTTPException(status_code=404, detail="Metrics disabled")
    body, content_type = metrics_payload()
    return Response(content=body, media_type=content_type)
