"""
Admin API routes:
- GET /api/admin/users          — List all users
- GET /api/admin/logs           — View operation logs
- GET /api/admin/system/status  — System health & stats
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_admin_user
from app.models import (
    User,
    KnowledgeBase,
    Document,
    ChatSession,
    OperationLog,
    BackgroundTask,
)

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get("/users")
async def list_users(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """List all registered users (admin only)."""
    result = await db.execute(
        select(User).offset(skip).limit(limit).order_by(User.created_at.desc())
    )
    users = result.scalars().all()

    return [
        {
            "id": u.id,
            "email": u.email,
            "username": u.username,
            "role": u.role.value if hasattr(u.role, 'value') else str(u.role),
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]


@router.get("/logs")
async def get_logs(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """View operation logs (admin only)."""
    result = await db.execute(
        select(OperationLog)
        .offset(skip)
        .limit(limit)
        .order_by(OperationLog.created_at.desc())
    )
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "action": log.action,
            "target_type": log.target_type,
            "target_id": log.target_id,
            "detail_json": log.detail_json,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]


@router.get("/system/status")
async def system_status(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """Get system statistics (admin only)."""
    user_count = (await db.execute(select(func.count()).select_from(User))).scalar()
    kb_count = (await db.execute(select(func.count()).select_from(KnowledgeBase))).scalar()
    doc_count = (await db.execute(select(func.count()).select_from(Document))).scalar()
    session_count = (await db.execute(select(func.count()).select_from(ChatSession))).scalar()
    task_count = (await db.execute(
        select(func.count()).select_from(BackgroundTask).where(BackgroundTask.status == "running")
    )).scalar()

    return {
        "users": user_count,
        "knowledge_bases": kb_count,
        "documents": doc_count,
        "chat_sessions": session_count,
        "active_tasks": task_count,
    }
