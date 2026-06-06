"""CSRF protection — double-submit cookie + Origin validation."""

from __future__ import annotations

import secrets
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp

from app.core.config import get_settings
from app.core.errors import ErrorCode, error_response

settings = get_settings()

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
EXEMPT_PATHS = frozenset({
    "/api/health",
    "/api/health/live",
    "/api/health/ready",
    "/api/metrics",
    "/api/auth/csrf",
    "/docs",
    "/openapi.json",
    "/redoc",
})


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def _cookie_kwargs() -> dict:
    kwargs = {
        "path": "/",
        "secure": settings.COOKIE_SECURE or settings.APP_ENV == "production",
        "samesite": settings.COOKIE_SAMESITE,
    }
    if settings.COOKIE_DOMAIN:
        kwargs["domain"] = settings.COOKIE_DOMAIN
    return kwargs


def set_csrf_cookie(response: Response, token: str | None = None) -> str:
    """Set readable CSRF cookie (double-submit pattern). Returns the token."""
    value = token or generate_csrf_token()
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=value,
        httponly=False,
        max_age=settings.CSRF_COOKIE_MAX_AGE,
        **_cookie_kwargs(),
    )
    return value


def clear_csrf_cookie(response: Response) -> None:
    response.delete_cookie(key=settings.CSRF_COOKIE_NAME, **_cookie_kwargs())


def _uses_bearer_auth(request: Request) -> bool:
    auth = request.headers.get("Authorization", "")
    return auth.startswith("Bearer ") and len(auth) > 7


def _origin_allowed(request: Request) -> bool:
    allowed = settings.ALLOWED_ORIGINS_LIST
    origin = request.headers.get("origin")
    if origin:
        return origin in allowed

    referer = request.headers.get("referer")
    if referer:
        from urllib.parse import urlparse

        parsed = urlparse(referer)
        ref_origin = f"{parsed.scheme}://{parsed.netloc}"
        return ref_origin in allowed

    return settings.APP_ENV != "production"


def validate_csrf(request: Request) -> JSONResponse | None:
    """Return error response when CSRF validation fails, else None."""
    if not settings.CSRF_ENABLED:
        return None

    if request.method in SAFE_METHODS:
        return None

    path = request.url.path
    if path in EXEMPT_PATHS:
        return None

    if _uses_bearer_auth(request):
        return None

    cookie_token = request.cookies.get(settings.CSRF_COOKIE_NAME)
    header_token = request.headers.get(settings.CSRF_HEADER_NAME)

    if (
        not cookie_token
        or not header_token
        or not secrets.compare_digest(cookie_token, header_token)
    ):
        return JSONResponse(
            status_code=403,
            content=error_response(ErrorCode.CSRF_INVALID),
        )

    if not _origin_allowed(request):
        return JSONResponse(
            status_code=403,
            content=error_response(ErrorCode.CSRF_ORIGIN_DENIED),
        )

    return None


class CSRFMiddleware:
    """ASGI middleware enforcing CSRF on state-changing cookie-authenticated requests."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        error = validate_csrf(request)
        if error is not None:
            await error(scope, receive, send)
            return

        await self.app(scope, receive, send)


async def csrf_middleware_dispatch(request: Request, call_next: Callable):
    """Starlette BaseHTTPMiddleware-compatible CSRF guard."""
    error = validate_csrf(request)
    if error is not None:
        return error
    return await call_next(request)
