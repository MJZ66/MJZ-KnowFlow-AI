"""HttpOnly JWT cookie helpers."""

from fastapi import Response

from app.core.config import get_settings
from app.core.csrf import clear_csrf_cookie, set_csrf_cookie

settings = get_settings()


def _cookie_secure() -> bool:
    if settings.COOKIE_SECURE:
        return True
    return settings.APP_ENV == "production"


def _cookie_samesite() -> str:
    return settings.COOKIE_SAMESITE


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> str:
    """Attach access + refresh tokens as HttpOnly cookies; rotate CSRF token."""
    common = {
        "httponly": True,
        "secure": _cookie_secure(),
        "samesite": _cookie_samesite(),
        "path": "/",
    }
    if settings.COOKIE_DOMAIN:
        common["domain"] = settings.COOKIE_DOMAIN

    response.set_cookie(
        key=settings.ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **common,
    )
    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        **common,
    )
    return set_csrf_cookie(response)


def clear_auth_cookies(response: Response) -> None:
    """Remove auth and CSRF cookies (logout)."""
    kwargs = {
        "path": "/",
        "secure": _cookie_secure(),
        "samesite": _cookie_samesite(),
    }
    if settings.COOKIE_DOMAIN:
        kwargs["domain"] = settings.COOKIE_DOMAIN

    response.delete_cookie(key=settings.ACCESS_TOKEN_COOKIE_NAME, **kwargs)
    response.delete_cookie(key=settings.REFRESH_TOKEN_COOKIE_NAME, **kwargs)
    clear_csrf_cookie(response)
