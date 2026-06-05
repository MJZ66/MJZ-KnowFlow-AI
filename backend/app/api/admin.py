"""
Admin API routes:
- GET  /api/admin/users
- GET  /api/admin/analytics
- PATCH /api/admin/users/{user_id}/role
- GET  /api/admin/logs
- GET  /api/admin/system/status
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, nulls_last, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_admin_user, get_super_admin
from app.models import (
    User,
    UserRole,
    KnowledgeBase,
    Document,
    ChatSession,
    OperationLog,
    BackgroundTask,
)
from app.models import PublishStatus
from app.schemas.admin import (
    AdminAnalyticsResponse,
    AdminSystemStatusResponse,
    AdminUserItem,
    AdminUserListResponse,
    DailyActivePoint,
    UpdateUserRoleRequest,
)
from app.schemas.kb import KBPublishRequestItem, PublishReviewRequest
from app.services.kb_publish import approve_publish, reject_publish
from app.services.test_account import is_test_account, test_account_sql_clause
from app.services.user_activity import is_user_online, online_threshold_minutes, utcnow

router = APIRouter(prefix="/api/admin", tags=["Admin"])


def _role_value(role) -> str:
    return role.value if hasattr(role, "value") else str(role)


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _user_item(user: User, *, now: datetime) -> AdminUserItem:
    return AdminUserItem(
        id=user.id,
        email=user.email,
        username=user.username,
        role=_role_value(user.role),
        created_at=_iso(user.created_at) or "",
        last_login_at=_iso(user.last_login_at),
        last_active_at=_iso(user.last_active_at),
        is_online=is_user_online(user, now=now),
        is_test_account=is_test_account(email=user.email, username=user.username),
    )


def _real_user_clause():
    return ~test_account_sql_clause()


async def _count_users(db: AsyncSession, *, exclude_test: bool) -> int:
    stmt = select(func.count()).select_from(User)
    if exclude_test:
        stmt = stmt.where(_real_user_clause())
    return int((await db.execute(stmt)).scalar() or 0)


async def _count_test_users(db: AsyncSession) -> int:
    return int(
        (await db.execute(
            select(func.count()).select_from(User).where(test_account_sql_clause())
        )).scalar()
        or 0
    )


async def _online_count(db: AsyncSession, *, now: datetime, exclude_test: bool = False) -> int:
    threshold = now - timedelta(minutes=online_threshold_minutes())
    stmt = select(func.count()).select_from(User).where(User.last_active_at >= threshold)
    if exclude_test:
        stmt = stmt.where(_real_user_clause())
    result = await db.execute(stmt)
    return int(result.scalar() or 0)


async def _dau_today(db: AsyncSession, *, now: datetime, exclude_test: bool = False) -> int:
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    stmt = select(func.count()).select_from(User).where(User.last_active_at >= start)
    if exclude_test:
        stmt = stmt.where(_real_user_clause())
    result = await db.execute(stmt)
    return int(result.scalar() or 0)


async def _daily_active_series(
    db: AsyncSession, *, days: int = 7, exclude_test: bool = False
) -> list[DailyActivePoint]:
    now = utcnow()
    series: list[DailyActivePoint] = []
    for offset in range(days - 1, -1, -1):
        day_start = (now - timedelta(days=offset)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        day_end = day_start + timedelta(days=1)
        stmt = (
            select(func.count())
            .select_from(User)
            .where(User.last_active_at >= day_start, User.last_active_at < day_end)
        )
        if exclude_test:
            stmt = stmt.where(_real_user_clause())
        result = await db.execute(stmt)
        series.append(
            DailyActivePoint(
                date=day_start.strftime("%Y-%m-%d"),
                count=int(result.scalar() or 0),
            )
        )
    return series


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    exclude_test: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """List users with login/activity and online status."""
    now = utcnow()
    test_account_count = await _count_test_users(db)
    total = await _count_users(db, exclude_test=exclude_test)
    online_count = await _online_count(db, now=now, exclude_test=exclude_test)

    stmt = select(User).order_by(
        nulls_last(User.last_active_at.desc()), User.created_at.desc()
    )
    if exclude_test:
        stmt = stmt.where(_real_user_clause())
    result = await db.execute(stmt.offset(skip).limit(limit))
    users = result.scalars().all()

    return AdminUserListResponse(
        items=[_user_item(u, now=now) for u in users],
        total=total,
        online_count=online_count,
        test_account_count=test_account_count,
    )


@router.get("/analytics", response_model=AdminAnalyticsResponse)
async def admin_analytics(
    days: int = Query(default=7, ge=1, le=30),
    exclude_test: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """Daily active users and online presence summary."""
    now = utcnow()
    total_users = await _count_users(db, exclude_test=exclude_test)
    return AdminAnalyticsResponse(
        total_users=total_users,
        online_count=await _online_count(db, now=now, exclude_test=exclude_test),
        dau_today=await _dau_today(db, now=now, exclude_test=exclude_test),
        daily_active=await _daily_active_series(db, days=days, exclude_test=exclude_test),
        online_threshold_minutes=online_threshold_minutes(),
    )


@router.get("/kb-publish-requests", response_model=list[KBPublishRequestItem])
async def list_publish_requests(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """List knowledge bases pending public catalog approval."""
    result = await db.execute(
        select(KnowledgeBase, User)
        .join(User, User.id == KnowledgeBase.user_id)
        .where(KnowledgeBase.publish_status == PublishStatus.PENDING)
        .order_by(KnowledgeBase.publish_requested_at.desc().nullslast())
    )
    rows = result.all()
    return [
        KBPublishRequestItem(
            id=kb.id,
            user_id=kb.user_id,
            owner_username=owner.username,
            owner_email=owner.email,
            name=kb.name,
            description=kb.description or "",
            publish_requested_at=_iso(kb.publish_requested_at),
            created_at=_iso(kb.created_at) or "",
        )
        for kb, owner in rows
    ]


@router.post("/kb-publish-requests/{kb_id}/approve")
async def approve_kb_publish(
    kb_id: int,
    req: PublishReviewRequest | None = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    kb = await approve_publish(db, kb_id, admin, note=req.note if req else None)
    return {"id": kb.id, "visibility": _role_value(kb.visibility), "publish_status": "approved"}


@router.post("/kb-publish-requests/{kb_id}/reject")
async def reject_kb_publish(
    kb_id: int,
    req: PublishReviewRequest | None = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    kb = await reject_publish(db, kb_id, admin, note=req.note if req else None)
    return {"id": kb.id, "visibility": _role_value(kb.visibility), "publish_status": "rejected"}


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    req: UpdateUserRoleRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_super_admin),
):
    """Promote/demote user role (super_admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if target.id == admin.id and req.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot demote your own super admin account.",
        )

    new_role = UserRole(req.role)
    if target.role == UserRole.SUPER_ADMIN and new_role != UserRole.SUPER_ADMIN:
        super_count = await db.execute(
            select(func.count()).select_from(User).where(User.role == UserRole.SUPER_ADMIN)
        )
        if int(super_count.scalar() or 0) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last super admin.",
            )

    target.role = new_role
    await db.flush()
    return {"id": target.id, "role": _role_value(target.role)}


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


@router.get("/system/status", response_model=AdminSystemStatusResponse)
async def system_status(
    exclude_test: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """Get system statistics (admin only)."""
    now = utcnow()
    test_users = await _count_test_users(db)
    user_count = await _count_users(db, exclude_test=exclude_test)

    real_owner_ids = select(User.id).where(_real_user_clause())
    if exclude_test:
        kb_count = (
            await db.execute(
                select(func.count())
                .select_from(KnowledgeBase)
                .where(KnowledgeBase.user_id.in_(real_owner_ids))
            )
        ).scalar()
        doc_count = (
            await db.execute(
                select(func.count())
                .select_from(Document)
                .join(KnowledgeBase, KnowledgeBase.id == Document.knowledge_base_id)
                .where(KnowledgeBase.user_id.in_(real_owner_ids))
            )
        ).scalar()
        session_count = (
            await db.execute(
                select(func.count())
                .select_from(ChatSession)
                .where(ChatSession.user_id.in_(real_owner_ids))
            )
        ).scalar()
    else:
        kb_count = (await db.execute(select(func.count()).select_from(KnowledgeBase))).scalar()
        doc_count = (await db.execute(select(func.count()).select_from(Document))).scalar()
        session_count = (
            await db.execute(select(func.count()).select_from(ChatSession))
        ).scalar()

    task_count = (await db.execute(
        select(func.count()).select_from(BackgroundTask).where(BackgroundTask.status == "running")
    )).scalar()

    return AdminSystemStatusResponse(
        users=int(user_count or 0),
        knowledge_bases=int(kb_count or 0),
        documents=int(doc_count or 0),
        chat_sessions=int(session_count or 0),
        active_tasks=int(task_count or 0),
        online_count=await _online_count(db, now=now, exclude_test=exclude_test),
        dau_today=await _dau_today(db, now=now, exclude_test=exclude_test),
        test_users=test_users,
    )
