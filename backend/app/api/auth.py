"""
Authentication API routes:
- POST /api/auth/register
- POST /api/auth/login
- POST /api/auth/refresh
- POST /api/auth/logout
- GET  /api/auth/me
- POST /api/auth/change-password
"""

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from jose import JWTError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cookies import clear_auth_cookies, set_auth_cookies
from app.core.csrf import set_csrf_cookie, generate_csrf_token
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models import User, UserRole
from app.services.user_activity import record_login
from app.schemas.auth import (
    ChangePasswordRequest,
    CsrfResponse,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/api/auth", tags=["Auth"])
settings = get_settings()


def _issue_tokens(response: Response, user_id: int) -> TokenResponse:
    access_token = create_access_token(subject=user_id)
    refresh_token = create_refresh_token(subject=user_id)
    set_auth_cookies(response, access_token, refresh_token)
    if settings.AUTH_RETURN_TOKENS_IN_BODY:
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)
    return TokenResponse()


def _resolve_refresh_token(request: Request, req: RefreshRequest | None) -> str:
    cookie_token = request.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
    if cookie_token:
        return cookie_token
    if req and req.refresh_token:
        return req.refresh_token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token.",
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    req: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user account. Sets HttpOnly auth cookies."""
    if settings.APP_ENV == "production" and not settings.ALLOW_OPEN_REGISTRATION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration is disabled.",
        )
    result = await db.execute(select(User).where(User.email == req.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered.",
        )

    count_result = await db.execute(select(func.count()).select_from(User))
    is_first_user = (count_result.scalar_one() or 0) == 0

    user = User(
        email=req.email,
        hashed_password=hash_password(req.password),
        username=req.username,
        role=UserRole.SUPER_ADMIN if (is_first_user and settings.FIRST_USER_SUPER_ADMIN) else UserRole.USER,
    )
    try:
        db.add(user)
        await db.flush()
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered.",
        )
    record_login(user)
    return _issue_tokens(response, user.id)


@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate with email & password. Sets HttpOnly auth cookies."""
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    record_login(user)
    return _issue_tokens(response, user.id)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    req: RefreshRequest = Body(default_factory=RefreshRequest),
):
    """Rotate tokens using refresh cookie (or JSON body for API clients)."""
    raw_refresh = _resolve_refresh_token(request, req)
    try:
        payload = decode_token(raw_refresh)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type.")
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )

    return _issue_tokens(response, user.id)


@router.post("/logout", response_model=MessageResponse)
async def logout(response: Response):
    """Clear auth cookies."""
    clear_auth_cookies(response)
    return MessageResponse(message="Logged out successfully.")


@router.get("/csrf", response_model=CsrfResponse)
async def get_csrf_token(response: Response):
    """Issue a CSRF token cookie for double-submit protection."""
    token = set_csrf_cookie(response, generate_csrf_token())
    return CsrfResponse(csrf_token=token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        role=current_user.role.value if hasattr(current_user.role, 'value') else current_user.role,
        created_at=current_user.created_at.isoformat(),
    )


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change password for the authenticated user."""
    if not verify_password(req.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect.",
        )
    if req.current_password == req.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password.",
        )

    current_user.hashed_password = hash_password(req.new_password)
    await db.flush()

    return MessageResponse(message="Password updated successfully.")
